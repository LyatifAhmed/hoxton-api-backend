from fastapi import APIRouter, HTTPException
from datetime import datetime
import sqlite3

router = APIRouter()

@router.get("/api/recover-token")
def recover_token(token: str):
    conn = sqlite3.connect("scanned_mail.db")
    c = conn.cursor()

    c.execute("""
        SELECT email, product_id, plan_name, expires_at, kyc_submitted 
        FROM kyc_tokens 
        WHERE token = ?
    """, (token,))
    
    row = c.fetchone()
    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="No token found")

    email, product_id, plan_name, expires_at, kyc_submitted = row

    if kyc_submitted:
        raise HTTPException(status_code=409, detail="You’ve already completed your KYC.")

    if datetime.fromisoformat(expires_at) < datetime.utcnow():
        raise HTTPException(status_code=410, detail="This KYC link has expired. You can request a new one.")

    return {
        "email": email,
        "product_id": product_id,
        "plan_name": plan_name
    }
