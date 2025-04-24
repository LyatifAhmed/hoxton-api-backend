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
        external_id = payload.get("external_id")

        if not external_id:
            raise HTTPException(status_code=400, detail="Missing external_id")

        # Save scanned mail record
        scanned_mail = ScannedMail(
            id=str(uuid.uuid4()),
            external_id=external_id,
            sender_name=payload.get("sender_name"),
            document_title=payload.get("document_title"),
            summary=payload.get("summary"),
            url=payload.get("url"),
            url_envelope_front=payload.get("url_envelope_front"),
            url_envelope_back=payload.get("url_envelope_back"),
            received_at=datetime.utcnow()
        )
        db.add(scanned_mail)
        db.commit()

        # Notify customer via email
        subscription = db.query(Subscription).filter(Subscription.external_id == external_id).first()
        if subscription:
            await send_scanned_mail_notification(
                recipient_email=subscription.customer_email,
                company_name=subscription.company_name,
                sender_name=payload.get("sender_name", ""),
                document_title=payload.get("document_title", "")
            )

        return {"message": "Scanned mail received and saved."}

    except Exception as e:
        print(f"❌ Webhook error: {e}")
        raise HTTPException(status_code=500, detail="Webhook processing failed")
