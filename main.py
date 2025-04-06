import os
import aiohttp
from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from sqlalchemy.orm import Session
from datetime import datetime
from dotenv import load_dotenv

from scanned_mail.database import SessionLocal, engine
from scanned_mail.models import ScannedMail, Base

# Load environment variables
load_dotenv()

# Create app
app = FastAPI()

# Basic Auth setup
security = HTTPBasic()
WEBHOOK_USER = os.getenv("WEBHOOK_USER")
WEBHOOK_PASS = os.getenv("WEBHOOK_PASS")

# Auto-create database tables
Base.metadata.create_all(bind=engine)

# File saving setup
SAVE_DIR = "scanned_mail"
os.makedirs(SAVE_DIR, exist_ok=True)

# DB dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# File downloader
async def download_file(url, filename):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status == 200:
                content = await resp.read()
                with open(os.path.join(SAVE_DIR, filename), 'wb') as f:
                    f.write(content)

# Webhook endpoint
@app.post("/webhook")
async def receive_webhook(
    request: Request,
    credentials: HTTPBasicCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    # Auth check
    if credentials.username != WEBHOOK_USER or credentials.password != WEBHOOK_PASS:
        raise HTTPException(status_code=401, detail="Not authenticated")

    data = await request.json()
    print("📬 Webhook received:", data)

    # Save file URLs
    external_id = data.get("external_id")
    urls = [
        ("pdf", data.get("url")),
        ("front", data.get("url_envelope_front")),
        ("back", data.get("url_envelope_back")),
    ]
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    for suffix, url in urls:
        if url:
            filename = f"{external_id}_{suffix}_{timestamp}.pdf"
            await download_file(url, filename)

    # Save to DB
    mail = ScannedMail(
        external_id = external_id,
        sender_name = data.get("ai_metadata", {}).get("sender_name"),
        document_title = data.get("ai_metadata", {}).get("document_title"),
        summary = data.get("ai_metadata", {}).get("summary"),
        url = data.get("url"),
        url_envelope_front = data.get("url_envelope_front"),
        url_envelope_back = data.get("url_envelope_back"),
    )
    db.add(mail)
    db.commit()
    db.refresh(mail)

    print(f"✅ All files processed for: {external_id}")
    return {"status": "Webhook saved", "id": mail.id}



