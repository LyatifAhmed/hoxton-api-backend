# hoxton/customer.py
from fastapi import APIRouter, HTTPException
from sqlalchemy.orm import Session
from scanned_mail.database import SessionLocal
from scanned_mail.models import Subscription

router = APIRouter()

@router.get("/customer")
def get_customer_by_email(email: str):
    db: Session = SessionLocal()
    try:
        subscription = db.query(Subscription).filter_by(customer_email=email).first()
        if not subscription:
            raise HTTPException(status_code=404, detail="Customer not found")
        return {"external_id": subscription.external_id}
    finally:
        db.close()
