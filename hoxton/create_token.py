from fastapi import APIRouter, HTTPException
from datetime import datetime, timedelta
import sqlite3
from pydantic import BaseModel
from uuid import uuid4
import stripe
import os

router = APIRouter()

# Stripe setup
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

class SessionIdRequest(BaseModel):
    session_id: str

@router.post("/api/create-token")
def create_token(data: SessionIdRequest):
    try:
        # 🔐 Fetch session from Stripe
        session = stripe.checkout.Session.retrieve(
            data.session_id,
            expand=["line_items", "customer_details"]
        )

        customer_email = session.get("customer_details", {}).get("email")
        price_id = session.get("line_items", {}).get("data", [])[0]["price"]["id"]

        if not customer_email or not price_id:
            raise HTTPException(status_code=400, detail="Missing email or price_id from session")

        # 🧠 Map to Hoxton plan
        if price_id == "price_1RBKvBACVQjWBIYus7IRSyEt":
            product_id = 2736
            plan_name = "Monthly"
        elif price_id == "price_1RBKvlACVQjWBIYuVs4Of01v":
            product_id = 2737
            plan_name = "Annual"
        else:
            raise HTTPException(status_code=400, detail="Unknown Stripe price_id")

        # 🎟️ Generate token
        token = str(uuid4())
        expires_at = datetime.utcnow() + timedelta(days=3)

        conn = sqlite3.connect("scanned_mail.db")
        c = conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS kyc_tokens (
                token TEXT PRIMARY KEY,
                date_created TEXT,
                email TEXT,
                product_id INTEGER,
                plan_name TEXT,
                expires_at TEXT,
                kyc_submitted INTEGER DEFAULT 0
            )
        """)

        # 💥 Delete old unfinished tokens
        c.execute("""
            DELETE FROM kyc_tokens WHERE email = ? AND kyc_submitted = 0
        """, (customer_email,))

        # ✅ Insert new token
        c.execute("""
            INSERT INTO kyc_tokens (token, date_created, email, product_id, plan_name, expires_at, kyc_submitted)
            VALUES (?, ?, ?, ?, ?, ?, 0)
        """, (
            token,
            datetime.utcnow().isoformat(),
            customer_email,
            product_id,
            plan_name,
            expires_at.isoformat()
        ))
        conn.commit()
        conn.close()

        return {
            "token": token,
            "price_id": price_id,
            "link": f"https://betaoffice.uk/kyc?token={token}",
            "expires_at": expires_at.isoformat()
        }

    except Exception as e:
        print("❌ Error in /api/create-token:", e)
        raise HTTPException(status_code=500, detail="Failed to create token")
