from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from scanned_mail.database import SessionLocal
from scanned_mail.models import Subscription, CompanyMember
from sqlalchemy.orm import Session
from datetime import datetime
from urllib.parse import quote
import os
import secrets
import glob
import traceback

router = APIRouter()
security = HTTPBasic()

# ✅ Admin credentials from .env
ADMIN_USER = os.getenv("ADMIN_USER")
ADMIN_PASS = os.getenv("ADMIN_PASS")

UPLOAD_DIR = "uploaded_files"

def verify_basic_auth(credentials: HTTPBasicCredentials = Depends(security)):
    if not (
        secrets.compare_digest(credentials.username, ADMIN_USER)
        and secrets.compare_digest(credentials.password, ADMIN_PASS)
    ):
        raise HTTPException(status_code=401, detail="Unauthorized")


@router.get("/api/admin/submission/{external_id}")
def get_submission_details(external_id: str, credentials: HTTPBasicCredentials = Depends(verify_basic_auth)):
    db: Session = SessionLocal()
    try:
        submission = db.query(Subscription).filter(Subscription.external_id == external_id).first()
        if not submission:
            raise HTTPException(status_code=404, detail="Submission not found")

        members = db.query(CompanyMember).filter(CompanyMember.subscription_id == external_id).all()

        member_data = []
        for idx, m in enumerate(members):
            id_pattern = os.path.join(UPLOAD_DIR, f"{external_id}_member{idx}_id_*")
            addr_pattern = os.path.join(UPLOAD_DIR, f"{external_id}_member{idx}_addr_*")

            proof_id_files = glob.glob(id_pattern)
            proof_addr_files = glob.glob(addr_pattern)

            member_data.append({
                "first_name": m.first_name,
                "last_name": m.last_name,
                "phone_number": m.phone_number,
                "date_of_birth": m.date_of_birth.isoformat(),
                "proof_of_id": proof_id_files[0] if proof_id_files else None,
                "proof_of_address": proof_addr_files[0] if proof_addr_files else None
            })

        return {
            "submission": {
                "external_id": submission.external_id,
                "company_name": submission.company_name,
                "customer_email": submission.customer_email,
                "start_date": submission.start_date.isoformat(),
                "review_status": submission.review_status
            },
            "members": member_data
        }

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")
    finally:
        db.close()

