from fastapi import FastAPI, Request, Depends, HTTPException, status, Path
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel
from typing import List, Optional
import requests
import sqlite3
import secrets
import os
from dotenv import load_dotenv
from requests.auth import HTTPBasicAuth
import base64

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
    shipping_address_line_2: Optional[str] = None
    shipping_address_line_3: Optional[str] = None
    shipping_address_city: str
    shipping_address_postcode: str
    shipping_address_state: Optional[str] = None
    shipping_address_country: str


class Company(BaseModel):
    name: str
    trading_name: Optional[str] = None
    limited_company_number: Optional[str] = None
    abn_number: Optional[str] = None
    acn_number: Optional[str] = None
    organisation_type: int
    telephone_number: str


class Member(BaseModel):
    first_name: str
    middle_name: Optional[str] = None
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

@app.post("/api/create-subscription")
def create_subscription(data: SubscriptionRequest):
    print("Sending to HOXTON_API_URL:", HOXTON_API_URL)
    print("Using HOXTON_API_KEY:", HOXTON_API_KEY[:6], "...")

    try:
        # Send POST with Basic Auth (API key as username, blank password)
        response = requests.post(
            HOXTON_API_URL,
            json=data.dict(),
            auth=HTTPBasicAuth(HOXTON_API_KEY, ''),
            headers={"Content-Type": "application/json"}
        )

        # Try parsing JSON response, fallback to plain text
        try:
            result = response.json()
        except ValueError:
            result = response.text

        # Success
        if response.status_code in (200, 201):
            return {"message": "Subscription created.", "data": result}
        else:
            raise HTTPException(status_code=response.status_code, detail=result)

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Subscription creation error: {str(e)}")

@app.post("/api/update-subscription/{external_id}")
def update_subscription(
    external_id: str = Path(..., description="Customer's external ID"),
    data: SubscriptionRequest = None
):
    url = f"{HOXTON_API_URL}/{external_id}"  # example: https://api.hoxtonmix.com/api/v2/subscription/{external_id}
    headers = {
        "Authorization": f"Bearer {HOXTON_API_KEY}",
        "Content-Type": "application/json"
    }

    # 🚫 Ensure product_id is NOT updated
    payload = data.dict()
    payload.pop("product_id", None)

    print("📤 Updating subscription:", external_id)
    print("🔒 URL:", url)
    print("📦 Payload:", payload)

    try:
        response = requests.post(url, json=payload, headers=headers)
        if response.status_code == 200:
            return {"message": "Subscription updated successfully", "data": response.json()}
        else:
            raise HTTPException(status_code=response.status_code, detail=response.text)
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Update failed: {str(e)}")
