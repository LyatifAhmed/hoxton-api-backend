from fastapi import APIRouter, HTTPException
from datetime import datetime, timedelta
import sqlite3
from pydantic import BaseModel
from uuid import uuid4
import stripe
import os
from scanned_mail.database import SessionLocal
from scanned_mail.models import KycToken

router = APIRouter()

# Stripe setup
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

class SessionIdRequest(BaseModel):
    session_id: str

@router.post("/api/create-token")
def create_token(data: SessionIdRequest):
    try:
        session = stripe.checkout.Session.retrieve(
            data.session_id,
            expand=["line_items", "customer_details"]
        )

        customer_email = session.get("customer_details", {}).get("email")
        price_id = session.get("line_items", {}).get("data", [])[0]["price"]["id"]

        if not customer_email or not price_id:
            raise HTTPException(status_code=400, detail="Missing email or price_id from session")

        if price_id == "price_1RBKvBACVQjWBIYus7IRSyEt":
            product_id = 2736
            plan_name = "Monthly"
        elif price_id == "price_1RBKvlACVQjWBIYuVs4Of01v":
            product_id = 2737
            plan_name = "Annual"
        else:
            raise HTTPException(status_code=400, detail="Unknown Stripe price_id")

        token = str(uuid4())
        expires_at = datetime.utcnow() + timedelta(days=3)

        db = SessionLocal()

        # Remove old tokens (if not submitted)
        db.query(KycToken).filter(KycToken.email == customer_email, KycToken.kyc_submitted == 0).delete()

        # Create new token
        new_token = KycToken(
            token=token,
            email=customer_email,
            product_id=product_id,
            plan_name=plan_name,
            expires_at=expires_at
        )
        db.add(new_token)
        db.commit()
        db.close()

        return {
            "token": token,
            "price_id": price_id,
            "link": f"https://betaoffice.uk/kyc?token={token}",
            "expires_at": expires_at.isoformat()
        }

    except Exception as e:
        print("❌ Error in /api/create-token:", e)
        raise HTTPException(status_code=500, detail="Failed to create token")
    
@router.get("/api/recover-token")
def recover_token(token: str):
    db = SessionLocal()
    kyc = db.query(KycToken).filter(KycToken.token == token).first()
    db.close()

    if not kyc:
        raise HTTPException(status_code=404, detail="Token not found")
    if datetime.utcnow() > kyc.expires_at:
        raise HTTPException(status_code=410, detail="Token expired")

    return {
        "email": kyc.email,
        "product_id": kyc.product_id,
        "plan_name": kyc.plan_name,
        "expires_at": kyc.expires_at.isoformat(),
        "kyc_submitted": kyc.kyc_submitted
    }    