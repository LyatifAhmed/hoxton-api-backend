import requests
import os
import aiohttp
from fastapi import FastAPI, Request, Depends, HTTPException, Query
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from sqlalchemy.orm import Session
from datetime import datetime
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware
from scanned_mail.database import SessionLocal, engine
from scanned_mail.models import ScannedMail, Base
from fastapi.responses import JSONResponse

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI()

GETADDRESS_API_KEY = os.getenv("GETADDRESS_API_KEY")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://betaoffice.uk", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Basic Auth credentials from .env
security = HTTPBasic()
WEBHOOK_USER = os.getenv("WEBHOOK_USER")
WEBHOOK_PASS = os.getenv("WEBHOOK_PASS")

# Auto-create database tables
Base.metadata.create_all(bind=engine)

# Ensure directory for downloaded files
SAVE_DIR = "scanned_mail"
os.makedirs(SAVE_DIR, exist_ok=True)

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Function to download files from given URL
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

# Webhook endpoint to receive scanned mail from Hoxton Mix
@app.post("/webhook")
async def receive_webhook(
    request: Request,
    credentials: HTTPBasicCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    # BasicAuth check
    if credentials.username != WEBHOOK_USER or credentials.password != WEBHOOK_PASS:
        raise HTTPException(status_code=401, detail="Not authenticated")

    data = await request.json()
    print("📬 Webhook received:", data)

    external_id = data.get("external_id")
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")

    # Download any available files
    for suffix, url in [
        ("pdf", data.get("url")),
        ("front", data.get("url_envelope_front")),
        ("back", data.get("url_envelope_back")),
    ]:
        if url:
            filename = f"{external_id}_{suffix}_{timestamp}.pdf"
            await download_file(url, filename)

    # Save mail metadata to the database
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

# GET endpoint to retrieve paginated mail entries
@app.get("/mails")
def get_mails(skip: int = 0, limit: int = 5, db: Session = Depends(get_db)):
    return db.query(ScannedMail)\
             .order_by(ScannedMail.received_at.desc())\
             .offset(skip)\
             .limit(limit)\
             .all()

@app.get("/api/address-lookup")
def address_lookup(postcode: str):
    from urllib.parse import quote_plus

    # Clean and encode the postcode
    postcode = postcode.strip().upper()
    encoded_postcode = quote_plus(postcode)

    url = f"https://api.getaddress.io/find/{encoded_postcode}?api-key={GETADDRESS_API_KEY}"
    print("Requesting GetAddress API:", url)  # DEBUG: log the URL

    try:
        response = requests.get(url)
        print("GetAddress API Status Code:", response.status_code)  # DEBUG: status
        print("GetAddress API Response:", response.text)  # DEBUG: raw response
        response.raise_for_status()
        data = response.json()
        return JSONResponse(content={"addresses": data.get("addresses", [])})
    except requests.exceptions.RequestException as e:
        print("ERROR calling GetAddress API:", e)
        return JSONResponse(status_code=400, content={"error": str(e)})



