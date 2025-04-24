from fastapi import APIRouter, Request, HTTPException, Depends
from sqlalchemy.orm import Session
from scanned_mail.database import get_db
from scanned_mail.models import Subscription, ScannedMail
from hoxton.mail import send_scanned_mail_notification
from datetime import datetime
import uuid

router = APIRouter()

@router.post("/api/webhook/scanned-mail")
async def scanned_mail_webhook(request: Request, db: Session = Depends(get_db)):
    try:
        payload = await request.json()

        # Extract basic fields (ensure your webhook sends these!)
        external_id = payload.get("external_id")
        url = payload.get("url")
        sender_name = payload.get("sender_name", "")
        document_title = payload.get("document_title", "")
        summary = payload.get("summary", "")
        url_envelope_front = payload.get("url_envelope_front")
        url_envelope_back = payload.get("url_envelope_back")
        company_name = payload.get("company_name")
        received_at = payload.get("received_at")

        if not external_id:
            raise HTTPException(status_code=400, detail="Missing external_id")

        mail = ScannedMail(
            id=external_id,
            sender_name=sender_name,
            document_title=document_title,
            summary=summary,
            url=url,
            url_envelope_front=url_envelope_front,
            url_envelope_back=url_envelope_back,
            company_name=company_name,
            received_at=received_at,
        )

        db.add(mail)
        db.commit()

        # 🚀 Send email notification to the customer (modify email logic accordingly)
        await send_mail_notification(company_name, document_title, url)

        return {"message": "Scanned mail saved and notification sent."}

    except Exception as e:
        print("❌ Webhook processing failed:", e)
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Webhook processing failed")
