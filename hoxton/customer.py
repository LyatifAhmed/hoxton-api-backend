from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session
from scanned_mail.database import SessionLocal
from scanned_mail.models import Subscription

router = APIRouter()

# ✅ Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/customer", summary="Get external_id by customer email")
async def get_customer_by_email(
    email: str = Query(..., description="Customer's email address"),
    db: Session = Depends(get_db)
):
    sub = db.query(Subscription).filter_by(customer_email=email).first()
    if not sub:
        raise HTTPException(status_code=404, detail="Customer not found")
    return {"external_id": sub.external_id}
