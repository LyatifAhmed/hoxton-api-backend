from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from scanned_mail.database import SessionLocal
from scanned_mail.models import Subscription, CompanyMember
from datetime import datetime
from sqlalchemy.orm import Session
import os
import secrets

router = APIRouter()
security = HTTPBasic()

# Read admin creds from environment
ADMIN_USER = os.getenv("ADMIN_USER", "admin")
ADMIN_PASS = os.getenv("ADMIN_PASS", "adminpass")

def verify_basic_auth(credentials: HTTPBasicCredentials = Depends(security)):
    correct_user = secrets.compare_digest(credentials.username, ADMIN_USER)
    correct_pass = secrets.compare_digest(credentials.password, ADMIN_PASS)
    if not (correct_user and correct_pass):
        raise HTTPException(status_code=401, detail="Unauthorized")

@router.get("/api/admin/submission/{external_id}")
def get_submission_details(external_id: str, credentials: HTTPBasicCredentials = Depends(verify_basic_auth)):
    db: Session = SessionLocal()
    try:
        submission = db.query(Subscription).filter(Subscription.external_id == external_id).first()
        if not submission:
            raise HTTPException(status_code=404, detail="Submission not found")

        members = db.query(CompanyMember).filter(CompanyMember.subscription_id == external_id).all()

        return {
            "submission": {
                "external_id": submission.external_id,
                "company_name": submission.company_name,
                "customer_email": submission.customer_email,
                "start_date": submission.start_date.isoformat(),
                "review_status": submission.review_status,
            },
            "members": [
                {
                    "first_name": m.first_name,
                    "last_name": m.last_name,
                    "phone_number": m.phone_number,
                    "date_of_birth": m.date_of_birth.isoformat(),
                    "proof_of_id": f"/uploaded_files/{external_id}_member{idx}_id_*.jpg",     
                    "proof_of_address": f"/uploaded_files/{external_id}_member{idx}_addr_*.jpg"
                }
                for idx, m in enumerate(members)
            ]
        }
    finally:
        db.close()
