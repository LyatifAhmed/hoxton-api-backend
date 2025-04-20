from fastapi import FastAPI, Request, Depends, HTTPException, status, Path, UploadFile, Form, Body
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel
from typing import List, Optional
import requests
import sqlite3
import secrets
import os
from dotenv import load_dotenv
from requests.auth import HTTPBasicAuth
import base64
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import stripe
from uuid import uuid4
from datetime import datetime, timedelta
import aiosmtplib
import json
from email.message import EmailMessage
from hoxton.mail import send_kyc_email
from scanned_mail.database import init_db, SessionLocal
from scanned_mail.models import KycToken, Subscription, CompanyMember
from contextlib import asynccontextmanager
from hoxton.create_token import router as token_router
from hoxton.submit_kyc import router as submit_kyc_router
from hoxton.mail import send_kyc_email
import subprocess
from hoxton.admin_dashboard import router as admin_router
from hoxton import admin_review 
from hoxton.admin_routes import router as admin_router 
subprocess.call(["alembic", "upgrade", "head"])


load_dotenv()

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🚀 Initializing DB at startup...")
    init_db()
    yield

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://betaoffice.uk"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(token_router)
app.include_router(submit_kyc_router)
app.include_router(admin_router)
app.include_router(admin_review.router)
app.include_router(admin_router)

security = HTTPBasic()

HOXTON_API_URL = os.getenv("HOXTON_API_URL")
HOXTON_API_KEY = os.getenv("HOXTON_API_KEY")
BASIC_AUTH_USER = os.getenv("BASIC_AUTH_USER")
BASIC_AUTH_PASS = os.getenv("BASIC_AUTH_PASS")

SMTP_HOST = os.getenv("SMTP_HOST")
SMTP_PORT = int(os.getenv("SMTP_PORT", 465))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASS = os.getenv("SMTP_PASS")

class SubscriptionSection(BaseModel):
    start_date: Optional[str]

class Customer(BaseModel):
    first_name: str
    middle_name: Optional[str]
    last_name: str
    email_address: str

class ShippingAddress(BaseModel):
    shipping_address_line_1: str
    shipping_address_line_2: Optional[str] = None
    shipping_address_line_3: Optional[str] = None
    shipping_address_city: str
    shipping_address_postcode: str
    shipping_address_state: Optional[str] = None
    shipping_address_country: str

class Company(BaseModel):
    name: str
    trading_name: Optional[str] = None
    limited_company_number: Optional[str] = None
    abn_number: Optional[str] = None
    acn_number: Optional[str] = None
    organisation_type: int
    telephone_number: str

class Member(BaseModel):
    first_name: str
    middle_name: Optional[str] = None
    last_name: str
    phone_number: str
    date_of_birth: str

class SubscriptionRequest(BaseModel):
    external_id: str
    product_id: Optional[int] = None
    customer: Customer
    shipping_address: ShippingAddress
    subscription: Optional[SubscriptionSection]
    company: Company
    members: List[Member]

def verify_basic_auth(credentials: HTTPBasicCredentials = Depends(security)):
    if not (secrets.compare_digest(credentials.username, BASIC_AUTH_USER) and 
            secrets.compare_digest(credentials.password, BASIC_AUTH_PASS)):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

@app.post("/webhook")
async def receive_webhook(request: Request, credentials: HTTPBasicCredentials = Depends(verify_basic_auth)):
    payload = await request.json()
    try:
        conn = sqlite3.connect("scanned_mail.db")
        c = conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS scanned_mail (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                external_id TEXT,
                title TEXT,
                sender TEXT,
                file_urls TEXT
            )
        """)
        c.execute("""
            INSERT INTO scanned_mail (external_id, title, sender, file_urls)
            VALUES (?, ?, ?, ?)
        """, (
            payload.get("external_id"),
            payload.get("document_title"),
            payload.get("sender_name"),
            ",".join(payload.get("document_urls", []))
        ))
        conn.commit()
        conn.close()
        return {"message": "Webhook data saved successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {e}")

@app.post("/webhook/stripe")
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, STRIPE_WEBHOOK_SECRET)
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Webhook signature verification failed")

    print("✅ Stripe webhook event received")
    print("Event type:", event['type'])

    if event["type"] == "checkout.session.completed":
        session_id = event["data"]["object"]["id"]

        # 🔁 Retrieve full session with expanded customer
        full_session = stripe.checkout.Session.retrieve(
            session_id,
            expand=["customer", "customer_details"]
        )

        # ✅ Try to get email from expanded session
        email = (
            full_session.get("customer_details", {}).get("email") or
            full_session.get("customer", {}).get("email")
        )
        metadata = full_session.get("metadata", {})
        price_id = metadata.get("price_id")
        session_id = full_session["id"]

        print("✅ Session Email:", email)
        print("Session Metadata:", metadata)
        print("Price ID:", price_id)
        print("Session ID:", session_id)

        plan_map = {
            "price_1RBKvBACVQjWBIYus7IRSyEt": ("Monthly Plan", 2736),
            "price_1RBKvlACVQjWBIYuVs4Of01v": ("Annual Plan", 2737)
        }

        if price_id in plan_map and email:
            plan_name, product_id = plan_map[price_id]

            token = str(uuid4())
            expires_at = datetime.utcnow() + timedelta(days=3)

            db = SessionLocal()
            db.query(KycToken).filter(KycToken.email == email, KycToken.kyc_submitted == 0).delete()
            db.add(KycToken(
                token=token,
                date_created=datetime.utcnow(),
                email=email,
                product_id=product_id,
                plan_name=plan_name,
                expires_at=expires_at,
                kyc_submitted=0,
                session_id=session_id
            ))
            db.commit()
            print(f"✅ Token saved to DB: {token}")
            tokens = db.query(KycToken).all()
            print("📦 Current tokens in DB:", [t.token for t in tokens])

            db.close()

            print(f"📩 Attempting to send email to {email} with token: {token}")
            await send_kyc_email(email, token)  # ✅ await added here
            print(f"✅ KYC email sent to {email}")
        else:
            print(f"⚠️ Missing or unrecognized price_id or email. price_id={price_id}, email={email}")
    else:
        print("⚠️ Webhook event was not checkout.session.completed")

    return {"status": "ok"}

@app.post("/api/create-subscription")
def create_subscription(data: SubscriptionRequest):
    print("🔁 Preparing subscription data for Hoxton Mix...")

    try:
        # Convert to dict and begin transforming
        payload = data.dict()

        # Generate unique external_id
        external_id = str(uuid4())
        payload["external_id"] = external_id

        # Ensure start_date is ISO 8601 formatted
        payload.setdefault("subscription", {})
        payload["subscription"]["start_date"] = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

        # Validate country is already ISO 2-letter (assumed correct from frontend)
        country_code = payload["shipping_address"].get("shipping_address_country", "")
        if len(country_code) != 2:
            raise HTTPException(status_code=400, detail=f"Invalid 2-letter country code: {country_code}")

        # Format all member date_of_birth fields
        for m in payload.get("members", []):
            if "date_of_birth" in m and "T" not in m["date_of_birth"]:
                m["date_of_birth"] += "T00:00:00Z"

        print("📦 Outgoing HoxtonMix Payload:")
        print(payload)

        # Make the POST request
        response = requests.post(
            HOXTON_API_URL,
            json=payload,
            auth=HTTPBasicAuth(HOXTON_API_KEY, ''),
            headers={"Content-Type": "application/json"}
        )

        try:
            result = response.json()
        except ValueError:
            result = response.text

        if response.status_code in (200, 201):
            # Mark token as submitted
            db = SessionLocal()
            db.query(KycToken).filter(KycToken.email == data.customer.email_address).update({
                "kyc_submitted": 1
            })
            db.commit()
            db.close()

            return {"message": "Subscription created.", "external_id": external_id, "data": result}
        else:
            raise HTTPException(status_code=response.status_code, detail=result)

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Subscription creation error: {str(e)}")
    
@app.post("/api/update-subscription/{external_id}")
def update_subscription(external_id: str, data: SubscriptionRequest):
    url = f"https://api.hoxtonmix.com/api/v2/subscription/{external_id}"

    try:
        response = requests.post(
            url,
            auth=HTTPBasicAuth(HOXTON_API_KEY, ""),
            json=data.dict(),
            headers={"Content-Type": "application/json"}
        )

        if response.status_code == 200:
            try:
                result = response.json()
            except ValueError:
                result = response.text
            return {"message": "Subscription updated successfully", "data": result}
        else:
            print("Update failed:", response.text)
            raise HTTPException(status_code=response.status_code, detail=response.text)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Update failed: {str(e)}")

    

