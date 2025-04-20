from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from scanned_mail.database import SessionLocal
from scanned_mail.models import Subscription
from fastapi.security import HTTPBasic, HTTPBasicCredentials
import secrets
import os

router = APIRouter()
security = HTTPBasic()

# Set admin credentials from environment or hardcoded (for dev)
ADMIN_USER = os.getenv("ADMIN_USER")
ADMIN_PASS = os.getenv("ADMIN_PASS")

def verify_admin(credentials: HTTPBasicCredentials = Depends(security)):
    correct_username = secrets.compare_digest(credentials.username, ADMIN_USER)
    correct_password = secrets.compare_digest(credentials.password, ADMIN_PASS)
    if not (correct_username and correct_password):
        raise HTTPException(status_code=401, detail="Unauthorized")
    return True

@router.get("/api/admin/submissions")
def get_submissions(authenticated: bool = Depends(verify_admin)):
    db: Session = SessionLocal()
    try:
        submissions = db.query(Subscription).all()
        return [
            {
                "external_id": s.external_id,
                "company_name": s.company_name,
                "customer_email": s.customer_email,
                "start_date": s.start_date.isoformat() if s.start_date else None,
                "reviewed": False,  # We'll track this later
                "approved": False   # Optional future field
            }
            for s in submissions
        ]
    finally:
        db.close()
