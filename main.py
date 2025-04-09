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

# File download helper
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
async def submit_kyc_form(
    contact_first_name: str = Form(...),
    contact_last_name: str = Form(...),
    contact_email: str = Form(...),
    contact_phone: str = Form(...),
    address_line1: str = Form(None),
    address_line2: str = Form(None),
    address_city: str = Form(None),
    address_postcode: str = Form(None),
    address_country: str = Form(None),
    address_address: str = Form(None),
    company_name: str = Form(None),
    company_trading_name: str = Form(None),
    company_number: str = Form(None),
    company_type: str = Form(None),
    company_label: str = Form(None),
    company_value: str = Form(None),
    owners: list[UploadFile] = File(None),  # Optional to process files now
):
    print("✅ KYC submission received")
    print("Contact:", contact_first_name, contact_last_name, contact_email, contact_phone)
    print("Address:", address_line1 or address_address)
    print("Company:", company_name or company_label)
    return {"status": "received"}

# Webhook
@app.post("/webhook")
async def receive_webhook(
    request: Request,
    credentials: HTTPBasicCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    if credentials.username != WEBHOOK_USER or credentials.password != WEBHOOK_PASS:
        raise HTTPException(status_code=401, detail="Not authenticated")

    data = await request.json()
    print("📬 Webhook received:", data)

    external_id = data.get("external_id")
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")

    for suffix, url in [
        ("pdf", data.get("url")),
        ("front", data.get("url_envelope_front")),
        ("back", data.get("url_envelope_back")),
    ]:
        if url:
            filename = f"{external_id}_{suffix}_{timestamp}.pdf"
            await download_file(url, filename)

    mail = ScannedMail(
        external_id = external_id,
        sender_name = data.get("sender_name", "N/A"),
        document_title = data.get("document_title", "N/A"),
        summary = data.get("summary", "N/A"),
        url = data.get("url"),
        url_envelope_front = data.get("url_envelope_front"),
        url_envelope_back = data.get("url_envelope_back"),
        company_name = data.get("company_name", "Unknown Company"),
    )

    db.add(mail)
    db.commit()
    db.refresh(mail)

    print(f"✅ All files processed for: {external_id}")
    return {"status": "Webhook saved", "id": mail.id}

# Paginated mails
@app.get("/mails")
def get_mails(skip: int = 0, limit: int = 5, db: Session = Depends(get_db)):
    return db.query(ScannedMail)\
             .order_by(ScannedMail.received_at.desc())\
             .offset(skip)\
             .limit(limit)\
             .all()

# UK address lookup
@app.get("/api/address-lookup")
def address_lookup(postcode: str):
    postcode = postcode.strip().upper()
    encoded_postcode = quote_plus(postcode)

    url = f"https://api.getaddress.io/find/{encoded_postcode}?api-key={GETADDRESS_API_KEY}&expand=true"
    print("Requesting GetAddress API:", url)

    try:
        response = requests.get(url)
        print("GetAddress API Status Code:", response.status_code)
        print("GetAddress API Response:", response.text)
        response.raise_for_status()
        data = response.json()
        return JSONResponse(content={"addresses": data.get("addresses", [])})
    except requests.exceptions.RequestException as e:
        print("ERROR calling GetAddress API:", e)
        return JSONResponse(status_code=400, content={"error": str(e)})


# Companies House search
@app.get("/api/company-search")
def company_search(q: str = Query(..., min_length=2)):
    if not COMPANIES_HOUSE_API_KEY:
        raise HTTPException(status_code=500, detail="Missing COMPANIES_HOUSE_API_KEY in environment")

    url = f"https://api.company-information.service.gov.uk/search/companies?q={q}"
    print("Requesting Companies House API:", url)

    try:
        response = requests.get(url, auth=HTTPBasicAuth(COMPANIES_HOUSE_API_KEY, ""))
        print("Companies House API Status Code:", response.status_code)
        print("Companies House API Response:", response.text)
        response.raise_for_status()
        data = response.json()
        return JSONResponse(content={"companies": data.get("items", [])})
    except requests.exceptions.RequestException as e:
        print("ERROR calling Companies House API:", e)
        return JSONResponse(status_code=400, content={"error": str(e)})




