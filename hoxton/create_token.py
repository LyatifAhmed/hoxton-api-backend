from fastapi import APIRouter, HTTPException
from datetime import datetime, timedelta
import sqlite3
from pydantic import BaseModel
from uuid import uuid4
router = APIRouter()



class TokenRequest(BaseModel):
    email: str
    product_id: int
    plan_name: str 

@router.post("/api/create-token")

def create_token(data: TokenRequest):
    import os
    print("📁 Writing to DB at:", os.path.abspath("scanned_mail.db"))  # ✅ Debug path
    print("🔧 Creating token...")
    token = str(uuid4())
    expires_at = datetime.utcnow() + timedelta(days=3)

    conn = sqlite3.connect("scanned_mail.db")
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS kyc_tokens (
            token TEXT PRIMARY KEY,
            date_created TEXT,
            email TEXT,
            product_id INTEGER,
            plan_name TEXT,
            expires_at TEXT,
            kyc_submitted INTEGER DEFAULT 0
        )
    """)
    # ✅ DELETE old unsubmitted token for this email
    c.execute("""
        DELETE FROM kyc_tokens WHERE email = ? AND kyc_submitted = 0
    """, (data.email,))

    c.execute("""
        INSERT INTO kyc_tokens (token, date_created, email, product_id, plan_name, expires_at, kyc_submitted)
        VALUES (?, ?, ?, ?, ?, ?, 0)
    """, (
        token,
        datetime.utcnow().isoformat(),
        data.email,
        data.product_id,
        data.plan_name,
        expires_at.isoformat()
    ))
    conn.commit()
    conn.close()

    return {
    "token": token,
    "link": f"https://betaoffice.uk/kyc?token={token}",
    "expires_at": expires_at.isoformat(),
    "price_id": data.product_id  # add this if your frontend needs it
}

    
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
