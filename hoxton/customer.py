from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from scanned_mail.database import SessionLocal
from scanned_mail.models import Subscription

router = APIRouter()

@router.get("/customer")
async def get_customer_by_email(email: str):
    db: Session = SessionLocal()
    try:
        sub = db.query(Subscription).filter_by(customer_email=email).first()
        if not sub:
            raise HTTPException(status_code=404, detail="Customer not found")
        return {"external_id": sub.external_id}
    finally:
        db.close()

