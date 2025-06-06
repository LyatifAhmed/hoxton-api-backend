import os
import httpx
from fastapi import APIRouter, HTTPException
from sqlalchemy.orm import Session
from dotenv import load_dotenv

from scanned_mail.database import SessionLocal
from scanned_mail.models import Subscription, ScannedMail

load_dotenv()

API_BASE_URL = os.getenv("HOXTON_API_URL")  # Örn: https://api.hoxtonmix.com/v2
API_KEY = os.getenv("HOXTON_API_KEY")       # Basic Auth için sadece username olarak kullanılır

router = APIRouter()

# ✅ GET: /subscription?external_id=... → Abonelik detaylarını döner
@router.get("/subscription")
def get_subscription(external_id: str):
    db: Session = SessionLocal()
    try:
        subscription = db.query(Subscription).filter_by(external_id=external_id).first()
        if not subscription:
            raise HTTPException(status_code=404, detail="Subscription not found")
        return subscription.__dict__
    finally:
        db.close()

# ✅ GET: /mail?external_id=... → Taratılmış mailleri döner
@router.get("/mail")
def get_mail_items(external_id: str):
    db: Session = SessionLocal()
    try:
        mail_items = db.query(ScannedMail).filter_by(external_id=external_id).order_by(ScannedMail.created_at.desc()).all()
        return [item.__dict__ for item in mail_items]
    finally:
        db.close()


# ✅ POST: Hoxton API'ye abonelik gönderme
async def create_subscription(data: dict):
    url = f"{API_BASE_URL}/subscription"

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(
                url,
                json=data,
                auth=(API_KEY, "")  # Basic Auth: API_KEY username, password boş
            )
            response.raise_for_status()
            return response.json() if response.content else {"message": "Subscription created successfully."}

    except httpx.HTTPStatusError as http_err:
        return {
            "error": str(http_err),
            "details": http_err.response.text,
            "status_code": http_err.response.status_code
        }

    except Exception as err:
        return {
            "error": "An unexpected error occurred",
            "details": str(err)
        }


# ✅ Payload inşa edici
def build_hoxton_payload(subscription, members):
    company = {
        "name": subscription.company_name,
        "trading_name": subscription.company_trading_name or subscription.company_name,
        "limited_company_number": subscription.company_number or "",
        "organisation_type": subscription.organisation_type,
    }

    if subscription.telephone_number and subscription.telephone_number.strip():
        company["telephone_number"] = subscription.telephone_number.strip()

    return {
        "external_id": subscription.external_id,
        "product_id": subscription.product_id,
        "customer": {
            "first_name": subscription.customer_first_name,
            "middle_name": subscription.customer_middle_name or "",
            "last_name": subscription.customer_last_name,
            "email_address": subscription.customer_email,
        },
        "shipping_address": {
            "shipping_address_line_1": subscription.shipping_line_1,
            "shipping_address_line_2": subscription.shipping_line_2 or "",
            "shipping_address_city": subscription.shipping_city,
            "shipping_address_postcode": subscription.shipping_postcode,
            "shipping_address_country": subscription.shipping_country,
        },
        "subscription": {
            "start_date": subscription.start_date.isoformat(),
        },
        "company": company,
        "members": [
            {
                "first_name": m.first_name,
                "last_name": m.last_name,
                "email_address": m.email
            }
            for m in members
        ]
    }
