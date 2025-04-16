from fastapi import UploadFile, File, Form, APIRouter, HTTPException
from fastapi.responses import JSONResponse
from scanned_mail.database import SessionLocal
from scanned_mail.models import Subscription, CompanyMember, KycToken
import os
import shutil
from datetime import datetime
from sqlalchemy.orm import Session
router = APIRouter()

UPLOAD_DIR = "uploaded_files"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("/api/submit-kyc")
async def submit_kyc(
    token: str = Form(...),  # ✅ Token from frontend
    product_id: int = Form(...),
    company_name: str = Form(...),
    trading_name: str = Form(...),
    organisation_type: int = Form(...),
    limited_company_number: str = Form(None),
    phone_number: str = Form(...),
    email: str = Form(...),
    address_line_1: str = Form(...),
    address_line_2: str = Form(None),
    city: str = Form(...),
    postcode: str = Form(...),
    country: str = Form(...),
    proof_of_address: UploadFile = File(...),
    proof_of_id: UploadFile = File(...),
    **kwargs
):
    db: Session = SessionLocal()
    try:
        # ✅ Look up token and mark as submitted
        kyc_token = db.query(KycToken).filter(KycToken.token == token).first()
        if not kyc_token:
            raise HTTPException(status_code=404, detail="Invalid KYC token")
        kyc_token.kyc_submitted = 1  # ✅ Mark it as submitted

        # External ID
        external_id = email.split("@")[0] + "-" + datetime.utcnow().strftime("%Y%m%d%H%M%S")

        # Save files
        addr_file_path = os.path.join(UPLOAD_DIR, proof_of_address.filename)
        id_file_path = os.path.join(UPLOAD_DIR, proof_of_id.filename)
        with open(addr_file_path, "wb") as f:
            shutil.copyfileobj(proof_of_address.file, f)
        with open(id_file_path, "wb") as f:
            shutil.copyfileobj(proof_of_id.file, f)

        # Save subscription
        subscription = Subscription(
            external_id=external_id,
            product_id=product_id,
            customer_email=email,
            customer_first_name="",
            customer_last_name="",
            customer_middle_name="",
            shipping_line_1=address_line_1,
            shipping_line_2=address_line_2,
            shipping_city=city,
            shipping_postcode=postcode,
            shipping_country=country,
            company_name=company_name,
            company_trading_name=trading_name,
            company_number=limited_company_number,
            organisation_type=organisation_type,
            telephone_number=phone_number
        )
        db.add(subscription)

        # Save company members
        for i in range(5):
            if f"members[{i}][first_name]" in kwargs:
                member = CompanyMember(
                    subscription_id=external_id,
                    first_name=kwargs.get(f"members[{i}][first_name]"),
                    middle_name=kwargs.get(f"members[{i}][middle_name]"),
                    last_name=kwargs.get(f"members[{i}][last_name]"),
                    phone_number=kwargs.get(f"members[{i}][phone_number]"),
                    date_of_birth=datetime.strptime(kwargs.get(f"members[{i}][date_of_birth]"), "%Y-%m-%d")
                )
                db.add(member)

        # ✅ Commit all changes
        db.commit()
        return {"message": "KYC submitted successfully.", "external_id": external_id}

    except Exception as e:
        db.rollback()
        print("❌ ERROR in /submit-kyc:", str(e))  # <--- add this
        return JSONResponse(status_code=500, content={"error": str(e)})

    finally:
        db.close()
