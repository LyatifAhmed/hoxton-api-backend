from fastapi import APIRouter, Request, HTTPException, Depends
from sqlalchemy.orm import Session
from scanned_mail.database import get_db
from scanned_mail.models import Subscription, ScannedMail
from hoxton.mail import send_scanned_mail_notification
from datetime import datetime
import uuid
import traceback

router = APIRouter()

@router.post("/api/webhook/scanned-mail")
async def scanned_mail_webhook(request: Request, db: Session = Depends(get_db)):
    try:
        payload = await request.json()
        external_id = payload.get("external_id")
        if not external_id:
            raise HTTPException(status_code=400, detail="Missing external_id")

        subscription = db.query(Subscription).filter_by(external_id=external_id).first()
        if not subscription:
            raise HTTPException(status_code=404, detail="Subscription not found")

        received_at_str = payload.get("received_at")
        received_at = datetime.fromisoformat(received_at_str.replace("Z", "+00:00")) if received_at_str else None

        mail = ScannedMail(
            external_id=external_id,
            sender_name=payload.get("sender_name", ""),
            document_title=payload.get("document_title", ""),
            summary=payload.get("summary", ""),
            url=payload.get("url"),
            url_envelope_front=payload.get("url_envelope_front"),
            url_envelope_back=payload.get("url_envelope_back"),
            company_name=payload.get("company_name"),
            received_at=received_at,
        )
        db.add(mail)
        db.commit()

        if subscription.customer_email:
            await send_scanned_mail_notification(
                recipient_email=subscription.customer_email,
                company_name=mail.company_name,
                sender_name=mail.sender_name,
                document_title=mail.document_title,
                document_url=mail.url
            )


        return {"success": True, "message": "Mail saved and notification sent."}

    except Exception as e:
        print("❌ Webhook processing failed:", e)
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Webhook processing failed")
