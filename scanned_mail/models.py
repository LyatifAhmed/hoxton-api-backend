import os
import aiohttp
from fastapi import FastAPI, Request
from datetime import datetime

app = FastAPI()

SAVE_DIR = "scanned_mail"
os.makedirs(SAVE_DIR, exist_ok=True)

async def download_file(url, filename):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status == 200:
                content = await resp.read()
                with open(os.path.join(SAVE_DIR, filename), 'wb') as f:
                    f.write(content)

@app.post("/webhook")
async def receive_webhook(payload: dict):
    external_id = payload.get("external_id")
    file_name = payload.get("file_name")
    urls = [
        ("pdf", payload.get("url")),
        ("front", payload.get("url_envelope_front")),
        ("back", payload.get("url_envelope_back")),
    ]

    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    for suffix, url in urls:
        if url:
            filename = f"{external_id}_{suffix}_{timestamp}.pdf"
            await download_file(url, filename)

    return {"status": "webhook saved"}

