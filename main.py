from fastapi import FastAPI, HTTPException, Request
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.responses import JSONResponse
from fastapi import Depends
import secrets
from hoxton.subscriptions import create_subscription

import os
import aiohttp
from datetime import datetime

security = HTTPBasic()

USERNAME = "hoxton"
PASSWORD = "secure123"  # Make sure to store in .env in production

def verify_credentials(credentials: HTTPBasicCredentials = Depends(security)):
    correct_username = secrets.compare_digest(credentials.username, USERNAME)
    correct_password = secrets.compare_digest(credentials.password, PASSWORD)
    if not (correct_username and correct_password):
        raise HTTPException(status_code=401, detail="Unauthorized")

app = FastAPI()

SAVE_DIR = "scanned_mail"
os.makedirs(SAVE_DIR, exist_ok=True)

async def download_file(url: str, filename: str):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                content = await response.read()
                path = os.path.join(SAVE_DIR, filename)
                with open(path, "wb") as f:
                    f.write(content)
                print(f"✅ Saved: {path}")
            else:
                print(f"❌ Failed to download: {url} - Status: {response.status}")

# Subscription endpoint
@app.post("/api/create-subscription")
async def create_sub(data: dict):
    try:
        result = await create_subscription(data)
        return {"status": "success", "response": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Webhook endpoint
@app.post("/webhook")
async def receive_webhook(request: Request):
    data = await request.json()
    print("📬 Webhook received:", data)

    external_id = data.get("external_id", "unknown")
    created_at = datetime.utcnow().strftime("%Y%m%d%H%M%S")

    # Prepare URLs for download
    urls = [
        ("main", data.get("url")),
        ("front", data.get("url_envelope_front")),
        ("back", data.get("url_envelope_back")),
    ]

    # Download all files
    for label, url in urls:
        if url:
            filename = f"{external_id}_{label}_{created_at}.pdf"
            await download_file(url, filename)

    return JSONResponse(content={"status": "Webhook files saved"})


