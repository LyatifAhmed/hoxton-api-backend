from fastapi import APIRouter, HTTPException, Depends, Request
from sqlalchemy.orm import Session
from scanned_mail.database import SessionLocal
from scanned_mail.models import Subscription
from pydantic import BaseModel
import os

router = APIRouter()

# Admin credentials from environment
ADMIN_USER = os.getenv("ADMIN_USER")
ADMIN_PASS = os.getenv("ADMIN_PASS")

# Pydantic schema for input validation
class ReviewRequest(BaseModel):
    external_id: str
    review_status: str  # "APPROVED" or "REJECTED"
    notes: str | None = None

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ✅ Admin Review Endpoint
@router.post("/api/admin/review-submission")
def review_submission(
    request: Request,
    body: ReviewRequest,
    db: Session = Depends(get_db)
):
    # 🔒 Basic Auth
    auth = request.headers.get("authorization")
    if not auth or not auth.startswith("Basic "):
        raise HTTPException(status_code=401, detail="Unauthorized")

    import base64
    encoded_credentials = auth.split(" ")[1]
    decoded = base64.b64decode(encoded_credentials).decode("utf-8")
    username, password = decoded.split(":")

    if username != ADMIN_USER or password != ADMIN_PASS:
        raise HTTPException(status_code=403, detail="Forbidden")

    # ✅ Fetch subscription by external_id
    sub = db.query(Subscription).filter(Subscription.external_id == body.external_id).first()
    if not sub:
        raise HTTPException(status_code=404, detail="Submission not found")

    # ✅ Update status and notes
    if body.review_status not in ["APPROVED", "REJECTED"]:
        raise HTTPException(status_code=400, detail="Invalid review status")

    sub.review_status = body.review_status
    sub.notes = body.notes
    db.commit()

    return {"message": f"Submission {body.review_status.lower()}."}
