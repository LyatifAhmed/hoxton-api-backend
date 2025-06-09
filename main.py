from fastapi import FastAPI, Request, Depends, HTTPException, status, Header
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Optional
import stripe
from uuid import uuid4
from datetime import datetime
from sqlalchemy.orm import Session
import secrets
import traceback
import os
import requests
from dotenv import load_dotenv
from requests.auth import HTTPBasicAuth
from contextlib import asynccontextmanager
# Local modules
from scanned_mail.database import init_db, SessionLocal
from scanned_mail.models import Subscription, CompanyMember, ScannedMail
from hoxton.mail import send_customer_verification_notice
from hoxton.subscriptions import create_subscription, build_hoxton_payload
from hoxton.webhook_routes import router as webhook_router
from hoxton.submit_kyc import router as kyc_router
from hoxton.customer import router as customer_router
from hoxton.subscriptions import router as subscriptions_router
from hoxton.cancel_subscription import router as cancel_router
from hoxton import subscriptions




# Load environment variables
load_dotenv()

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")
HOXTON_API_KEY = os.getenv("HOXTON_API_KEY")
BASIC_AUTH_USER = os.getenv("BASIC_AUTH_USER")
BASIC_AUTH_PASS = os.getenv("BASIC_AUTH_PASS")

# Lifespan
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🚀 Initializing DB at startup...")
    init_db()
    yield

app = FastAPI(lifespan=lifespan)

# Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://betaoffice.uk"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Basic Auth check
security = HTTPBasic()
def verify_basic_auth(credentials: HTTPBasicCredentials = Depends(security)):
    if not (secrets.compare_digest(credentials.username, BASIC_AUTH_USER) and
            secrets.compare_digest(credentials.password, BASIC_AUTH_PASS)):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

# ✅ Stripe Webhook
@app.post("/webhook")
async def receive_webhook(
    request: Request,
    credentials: str = Depends(verify_basic_auth),
    stripe_signature: str = Header(None)
):
    db: Session = SessionLocal()
    try:
        raw_body = await request.body()
        json_body = await request.json()

        # ✅ Handle Stripe Payment Confirmation
        if json_body.get("type") == "checkout.session.completed":
            session = json_body["data"]["object"]
            customer_email = session.get("customer_email")

            if not customer_email:
                raise HTTPException(status_code=400, detail="Missing customer email in Stripe event.")

            subscription = db.query(Subscription).filter_by(customer_email=customer_email).first()
            if not subscription:
                raise HTTPException(status_code=404, detail="No matching KYC data found.")

            if subscription.review_status == "SUBMITTED":
                return {"message": "Already submitted to Hoxton."}

            # ✅ Send to Hoxton
            members = db.query(CompanyMember).filter_by(subscription_id=subscription.external_id).all()
            hoxton_payload = build_hoxton_payload(subscription, members)
            hoxton_response = await create_subscription(hoxton_payload)

            subscription.review_status = "SUBMITTED"
            db.commit()

            # ✅ Confirmation Email
            await send_customer_verification_notice(subscription.customer_email, subscription.company_name)

            return {
                "message": "Submitted to Hoxton Mix",
                "external_id": subscription.external_id,
                "hoxton_response": hoxton_response
            }

        # ✅ Handle Scanned Mail
        elif json_body.get("external_id"):
            scanned = ScannedMail(
                external_id=json_body.get("external_id"),
                sender_name=json_body.get("sender_name"),
                document_title=json_body.get("document_title"),
                file_name=json_body.get("file_names", [""])[0] if isinstance(json_body.get("file_names"), list) else "",
                url=json_body.get("document_urls", [""])[0] if isinstance(json_body.get("document_urls"), list) else "",
                url_envelope_front=json_body.get("envelope_front_url", ""),
                url_envelope_back=json_body.get("envelope_back_url", ""),
                reference_number=json_body.get("reference_number"),
                summary=json_body.get("summary"),
                industry=json_body.get("industry"),
                categories=",".join(json_body.get("categories", [])),
                sub_categories=",".join(json_body.get("sub_categories", [])),
                key_information=str(json_body.get("key_information", {})),
                created_at=datetime.utcnow()
            )

            db.add(scanned)
            db.commit()

            return {"message": "✅ Scanned mail saved successfully."}

        else:
            return JSONResponse(status_code=400, content={"message": "Unhandled webhook payload"})

    except Exception as e:
        db.rollback()
        print("❌ Webhook processing failed:", str(e))
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": str(e)})
    finally:
        db.close()

@app.post("/webhook/stripe")
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, STRIPE_WEBHOOK_SECRET)
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Webhook signature verification failed")

    print("✅ Stripe webhook event received")
    print("Event type:", event["type"])

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        metadata = session.get("metadata", {})
        external_id = metadata.get("external_id")

        db: Session = SessionLocal()
        try:
            # ✅ Get subscription
            subscription = db.query(Subscription).filter_by(external_id=external_id).first()
            if not subscription:
                raise HTTPException(status_code=404, detail="Subscription not found")

            # ✅ Prevent duplicates
            if subscription.review_status == "SUBMITTED":
                return {"message": "Already submitted"}

            # ✅ Get company members
            members = db.query(CompanyMember).filter_by(subscription_id=external_id).all()

            # ✅ Send to Hoxton Mix
            from hoxton.subscriptions import build_hoxton_payload, create_subscription
            payload = build_hoxton_payload(subscription, members)
            response = await create_subscription(payload)

            # ✅ Update status
            subscription.review_status = "SUBMITTED"
            db.commit()

            # ✅ Send verification notice
            from hoxton.mail import send_customer_verification_notice
            await send_customer_verification_notice(subscription.customer_email, subscription.company_name)

            return {"message": "Submitted to Hoxton Mix", "external_id": external_id}

        except Exception as e:
            db.rollback()
            print("❌ Error in Stripe webhook:", str(e))
            traceback.print_exc()
            raise HTTPException(status_code=500, detail="Webhook processing error")
        finally:
            db.close()

    return {"status": "ok"}


# Attach scanned mail webhook routes
app.include_router(webhook_router)
app.include_router(kyc_router)
app.include_router(customer_router)
app.include_router(subscriptions_router)
app.include_router(cancel_router)
app.include_router(subscriptions.router)