from fastapi import FastAPI, Request, Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel, EmailStr
from typing import List, Optional
import requests
import sqlite3
import secrets
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()
security = HTTPBasic()

# Config
HOXTON_API_URL = os.getenv("HOXTON_API_URL")
HOXTON_API_KEY = os.getenv("HOXTON_API_KEY")
BASIC_AUTH_USER = os.getenv("BASIC_AUTH_USER")
BASIC_AUTH_PASS = os.getenv("BASIC_AUTH_PASS")

# Pydantic Models
class Customer(BaseModel):
    first_name: str
    middle_name: Optional[str]
    last_name: str
    email: EmailStr
    telephone: str

class Address(BaseModel):
    address_line_1: str
    address_line_2: Optional[str]
    city: str
    postcode: str
    country: str

class Company(BaseModel):
    name: str
    trading_name: Optional[str]
    number: Optional[str]
    organization_type: str

class Member(BaseModel):
    name: str
    date_of_birth: str
    proof_of_address_url: Optional[str]
    proof_of_id_url: Optional[str]
    aml_report_url: Optional[str]

class SubscriptionRequest(BaseModel):
    product_id: int
    customer: Customer
    shipping_address: Address
    company: Company
    members: List[Member]

# Auth check
def verify_basic_auth(credentials: HTTPBasicCredentials = Depends(security)):
    if not (secrets.compare_digest(credentials.username, BASIC_AUTH_USER) and 
            secrets.compare_digest(credentials.password, BASIC_AUTH_PASS)):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

# Webhook endpoint
@app.post("/webhook")
async def receive_webhook(request: Request, credentials: HTTPBasicCredentials = Depends(verify_basic_auth)):
    payload = await request.json()
    try:
        conn = sqlite3.connect("scanned_mail.db")
        c = conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS scanned_mail (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                external_id TEXT,
                title TEXT,
                sender TEXT,
                file_urls TEXT
            )
        """)
        c.execute("""
            INSERT INTO scanned_mail (external_id, title, sender, file_urls)
            VALUES (?, ?, ?, ?)
        """, (
            payload.get("external_id"),
            payload.get("document_title"),
            payload.get("sender_name"),
            ",".join(payload.get("document_urls", []))
        ))
        conn.commit()
        conn.close()
        return {"message": "Webhook data saved successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {e}")

# Subscription endpoint
@app.post("/api/create-subscription")
def create_subscription(data: SubscriptionRequest):
    headers = {
        "Authorization": f"Bearer {HOXTON_API_KEY}",
        "Content-Type": "application/json"
    }
    try:
        response = requests.post(HOXTON_API_URL, json=data.dict(), headers=headers)
        if response.status_code == 201:
            return {"message": "Subscription created.", "data": response.json()}
        else:
            raise HTTPException(status_code=response.status_code, detail=response.text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Subscription creation error: {e}")
