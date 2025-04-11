# hoxton/create_token.py

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, EmailStr
from uuid import uuid4
from datetime import datetime, timedelta
import sqlite3
from fastapi.responses import JSONResponse

router = APIRouter()

class TokenRequest(BaseModel):
    email: EmailStr
    product_id: int
    plan_name: str

@router.post("/api/create-token")
def create_token(data: TokenRequest):
    token = str(uuid4())
    expires_at = datetime.utcnow() + timedelta(days=3)

    conn = sqlite3.connect("scanned_mail.db")
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS kyc_tokens (
            token TEXT PRIMARY KEY,
            email TEXT,
            product_id INTEGER,
            plan_name TEXT,
            expires_at TEXT,
            kyc_submitted INTEGER DEFAULT 0
        )
    """)
    c.execute("""
        INSERT INTO kyc_tokens (token, email, product_id, plan_name, expires_at, kyc_submitted)
        VALUES (?, ?, ?, ?, ?, 0)
    """, (token, data.email, data.product_id, data.plan_name, expires_at.isoformat()))
    conn.commit()
    conn.close()

    kyc_link = f"https://betaoffice.uk/kyc?token={token}"
    return {
        "token": token,
        "link": kyc_link,
        "expires_at": expires_at.isoformat()
    }

@router.get("/api/recover-token")
def recover_token(token: str):
    conn = sqlite3.connect("scanned_mail.db")
    c = conn.cursor()
    c.execute("SELECT email, product_id, plan_name, expires_at, kyc_submitted FROM kyc_tokens WHERE token = ?", (token,))
    row = c.fetchone()
    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="Token not found")

    email, product_id, plan_name, expires_at, kyc_submitted = row
    if kyc_submitted:
        raise HTTPException(status_code=409, detail="Already submitted")
    
    if datetime.fromisoformat(expires_at) < datetime.utcnow():
        raise HTTPException(status_code=410, detail="Token expired")

    return {
        "email": email,
        "product_id": product_id,
        "plan_name": plan_name,
    }

@router.post("/api/resend-kyc-link")
def resend_kyc_link(data: TokenRequest):
    token = str(uuid4())
    expires_at = datetime.utcnow() + timedelta(days=3)

    conn = sqlite3.connect("scanned_mail.db")
    c = conn.cursor()
    c.execute("""
        INSERT INTO kyc_tokens (token, email, product_id, plan_name, expires_at, kyc_submitted)
        VALUES (?, ?, ?, ?, ?, 0)
    """, (token, data.email, data.product_id, data.plan_name, expires_at.isoformat()))
    conn.commit()
    conn.close()

    return {
        "message": "Resent link",
        "link": f"https://betaoffice.uk/kyc?token={token}"
    }
