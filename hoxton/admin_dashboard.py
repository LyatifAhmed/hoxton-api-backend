from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from scanned_mail.database import SessionLocal
from scanned_mail.models import Subscription
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from hoxton.client import get_hoxton_subscription
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
        result = []
        for s in submissions:
            hoxton_status = "UNKNOWN"
            try:
                hoxton_data = get_hoxton_subscription(s.external_id)
                hoxton_status = hoxton_data.get("subscription", {}).get("status", "UNKNOWN")
            except Exception as e:
                print(f"⚠️ Could not fetch Hoxton status for {s.external_id}: {e}")

            result.append({
                "external_id": s.external_id,
                "company_name": s.company_name,
                "customer_email": s.customer_email,
                "start_date": s.start_date.isoformat() if s.start_date else None,
                "hoxton_status": hoxton_status,
                "review_status": s.review_status if hasattr(s, "review_status") else "N/A"
            })
        return result
    finally:
        db.close()
