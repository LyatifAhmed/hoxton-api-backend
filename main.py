from fastapi import FastAPI, Request, Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel
from typing import List, Optional
import requests
import sqlite3
import secrets
import os
from dotenv import load_dotenv
from requests.auth import HTTPBasicAuth

load_dotenv()

app = FastAPI()
security = HTTPBasic()

# Config
HOXTON_API_URL = os.getenv("HOXTON_API_URL")
HOXTON_API_KEY = os.getenv("HOXTON_API_KEY")
BASIC_AUTH_USER = os.getenv("BASIC_AUTH_USER")
BASIC_AUTH_PASS = os.getenv("BASIC_AUTH_PASS")

# Pydantic Models (Aligned with Hoxton API Spec)
class SubscriptionSection(BaseModel):
    start_date: Optional[str]

class Customer(BaseModel):
    first_name: str
    middle_name: Optional[str]
    last_name: str
    email_address: str

class ShippingAddress(BaseModel):
    shipping_address_line_1: str
    shipping_address_line_2: Optional[str]
    shipping_address_line_3: Optional[str]
    shipping_address_city: str
    shipping_address_postcode: str
    shipping_address_state: Optional[str]
    shipping_address_country: str

class Company(BaseModel):
    name: str
    trading_name: Optional[str]
    limited_company_number: Optional[str]
    abn_number: Optional[str]
    acn_number: Optional[str]
    organisation_type: int
    telephone_number: str

class Member(BaseModel):
    first_name: str
    middle_name: Optional[str]
    last_name: str
    phone_number: str
    date_of_birth: str

class SubscriptionRequest(BaseModel):
    external_id: str
    product_id: int
    customer: Customer
    shipping_address: ShippingAddress
    subscription: Optional[SubscriptionSection]
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
import base64

@app.post("/api/create-subscription")
def create_subscription(data: SubscriptionRequest):
    print("Sending to HOXTON_API_URL:", HOXTON_API_URL)
    print("Using HOXTON_API_KEY:", HOXTON_API_KEY[:6], "...")
    print("Payload:", data.dict())

    # Encode the API key for Basic Auth (as username, no password)
    encoded_credentials = base64.b64encode(f"{HOXTON_API_KEY}:".encode()).decode()
    
    headers = {
        "Authorization": f"Basic {encoded_credentials}",
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(HOXTON_API_URL, json=data.dict(), headers=headers)
        if response.status_code in (200, 201):
            return {"message": "Subscription created.", "data": response.json()}
        else:
            raise HTTPException(status_code=response.status_code, detail=response.text)
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Subscription creation error: {str(e)}")
