from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from scanned_mail.database import SessionLocal
from scanned_mail.models import Subscription, CompanyMember
from sqlalchemy.orm import Session
from datetime import datetime
import os
import secrets
import glob
import traceback  # Added for logging stack traces

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
        print(f"🔍 Fetching submission for external_id: {external_id}")
        submission = db.query(Subscription).filter(Subscription.external_id == external_id).first()
        if not submission:
            print("❌ Submission not found")
            raise HTTPException(status_code=404, detail="Submission not found")

        members = db.query(CompanyMember).filter(CompanyMember.subscription_id == external_id).all()
        print(f"👥 Found {len(members)} members")

        member_data = []
        for idx, m in enumerate(members):
            id_pattern = os.path.join(UPLOAD_DIR, f"{external_id}_member{idx}_id_*")
            addr_pattern = os.path.join(UPLOAD_DIR, f"{external_id}_member{idx}_addr_*")

            proof_id_files = glob.glob(id_pattern)
            proof_addr_files = glob.glob(addr_pattern)

            print(f"📂 ID files for member {idx}: {proof_id_files}")
            print(f"📂 Address files for member {idx}: {proof_addr_files}")

            member_data.append({
                "first_name": m.first_name,
                "last_name": m.last_name,
                "phone_number": m.phone_number,
                "date_of_birth": m.date_of_birth.isoformat(),
                "proof_of_id": f"https://{os.getenv('RENDER_EXTERNAL_HOSTNAME') or 'your-backend.onrender.com'}/{proof_id_files[0]}" if proof_id_files else None,
                "proof_of_address": f"https://{os.getenv('RENDER_EXTERNAL_HOSTNAME') or 'your-backend.onrender.com'}/{proof_addr_files[0]}" if proof_addr_files else None,
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
        print("❌ Exception occurred while fetching submission:")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

    finally:
        db.close()


