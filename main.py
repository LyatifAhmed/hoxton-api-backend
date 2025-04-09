import os
import aiohttp
import requests
from urllib.parse import quote_plus
from fastapi import FastAPI, Request, Depends, HTTPException, Query, UploadFile, File, Form
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from sqlalchemy.orm import Session
from datetime import datetime
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from requests.auth import HTTPBasicAuth

from scanned_mail.database import SessionLocal, engine
from scanned_mail.models import ScannedMail, Base

# Load environment variables
load_dotenv()

# FastAPI app
app = FastAPI()

# Load API keys from env
GETADDRESS_API_KEY = os.getenv("GETADDRESS_API_KEY")
COMPANIES_HOUSE_API_KEY = os.getenv("COMPANIES_HOUSE_API_KEY")
HOXTON_API_KEY = os.getenv("HOXTON_API_KEY")
HOXTON_API_URL = os.getenv("HOXTON_API_URL")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://betaoffice.uk", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Basic Auth
security = HTTPBasic()
WEBHOOK_USER = os.getenv("WEBHOOK_USER")
WEBHOOK_PASS = os.getenv("WEBHOOK_PASS")

# Init DB
Base.metadata.create_all(bind=engine)

SAVE_DIR = "scanned_mail"
os.makedirs(SAVE_DIR, exist_ok=True)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

async def download_file(url, filename):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status == 200:
                    content = await resp.read()
                    with open(os.path.join(SAVE_DIR, filename), 'wb') as f:
                        f.write(content)
    except Exception as e:
        print(f"⚠️ Failed to download {url}: {e}")

@app.post("/api/submit-kyc")
async def submit_kyc_form(request: Request):
    form = await request.form()
    print("✅ KYC form received.")

    # Extract business owner info
    members = []
    index = 0
    while f"owners[{index}][first_name]" in form:
        members.append({
            "first_name": form.get(f"owners[{index}][first_name]", ""),
            "last_name": form.get(f"owners[{index}][last_name]", ""),
            "dob": form.get(f"owners[{index}][dob]", ""),
            "phone": form.get(f"owners[{index}][phone]", ""),
        })
        index += 1

    # Determine product_id from form
    product_id = form.get("product_id")
    if not product_id:
        return JSONResponse(status_code=400, content={"error": "Missing product_id"})

    payload = {
        "external_id": form.get("contact[email]", ""),
        "product_id": int(product_id),  # Make sure it's a number
        "customer": {
            "first_name": form.get("contact[first_name]", ""),
            "last_name": form.get("contact[last_name]", ""),
            "email": form.get("contact[email]", ""),
            "phone": form.get("contact[phone]", ""),
        },
        "shipping_address": {
            "line1": form.get("address[line1]") or form.get("address[address]", ""),
            "line2": form.get("address[line2]", ""),
            "city": form.get("address[city]", ""),
            "postcode": form.get("address[postcode]", ""),
            "country": form.get("address[country]", "United Kingdom"),
        },
        "company": {
            "name": form.get("company[name]") or form.get("company[label]", ""),
            "trading_name": form.get("company[trading_name]", ""),
            "number": form.get("company[number]") or form.get("company[value]", ""),
            "type": form.get("company[type]", ""),
        },
        "members": members
    }

    print("📦 Sending payload to Hoxton Mix:", payload)

    try:
        response = requests.post(
            HOXTON_API_URL,
            json=payload,
            headers={"Authorization": f"Bearer {HOXTON_API_KEY}"}
        )
        response.raise_for_status()
        return JSONResponse(content={"status": "submitted", "response": response.json()})
    except requests.exceptions.RequestException as e:
        print("❌ Failed to send to Hoxton Mix:", e)
        return JSONResponse(status_code=400, content={"error": str(e)})
