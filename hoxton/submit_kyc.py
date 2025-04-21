from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse
from scanned_mail.database import SessionLocal
from scanned_mail.models import Subscription, CompanyMember, KycToken
import os
import shutil
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
import traceback

router = APIRouter()

UPLOAD_DIR = "uploaded_files"
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB
ALLOWED_MIME_TYPES = ["application/pdf", "image/png", "image/jpeg"]

os.makedirs(UPLOAD_DIR, exist_ok=True)

def sanitize_filename(filename: str) -> str:
    return filename.replace(" ", "_").replace(":", "-")

@router.post("/api/submit-kyc")
async def submit_kyc(request: Request):
    form = await request.form()
    db: Session = SessionLocal()

    try:
        token = form.get("token")
        product_id = int(form.get("product_id"))
        company_name = form.get("company_name")
        trading_name = form.get("trading_name")
        organisation_type = int(form.get("organisation_type"))
        limited_company_number = form.get("limited_company_number")
        phone_number = form.get("phone_number")
        email = form.get("email")
        address_line_1 = form.get("address_line_1")
        address_line_2 = form.get("address_line_2")
        city = form.get("city")
        postcode = form.get("postcode")
        country = form.get("country")

        kyc_token = db.query(KycToken).filter(KycToken.token == token).first()
        if not kyc_token:
            raise HTTPException(status_code=404, detail="Invalid KYC token")

        kyc_token.kyc_submitted = 1
        external_id = email.split("@")[0] + "-" + datetime.utcnow().strftime("%Y%m%d%H%M%S")

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

        for i in range(5):
            if f"members[{i}][first_name]" not in form:
                continue

            first_name = form.get(f"members[{i}][first_name]")
            middle_name = form.get(f"members[{i}][middle_name]", "")
            last_name = form.get(f"members[{i}][last_name]")
            phone = form.get(f"members[{i}][phone_number]", "")
            dob_str = form.get(f"members[{i}][date_of_birth]")
            dob = datetime.strptime(dob_str, "%Y-%m-%d")
            age = (datetime.utcnow().date() - dob.date()) // timedelta(days=365)
            if age < 18:
                raise HTTPException(status_code=400, detail=f"Owner {i+1} must be at least 18 years old")

            proof_of_id = form.get(f"members[{i}][proof_of_id]")
            proof_of_address = form.get(f"members[{i}][proof_of_address]")

            if not hasattr(proof_of_id, "file") or not hasattr(proof_of_address, "file"):
                raise HTTPException(status_code=400, detail=f"Missing document for owner {i+1}")

            if proof_of_id.content_type not in ALLOWED_MIME_TYPES:
                raise HTTPException(status_code=400, detail=f"ID file for owner {i+1} must be .pdf, .png, or .jpg")
            if proof_of_address.content_type not in ALLOWED_MIME_TYPES:
                raise HTTPException(status_code=400, detail=f"Address file for owner {i+1} must be .pdf, .png, or .jpg")

            proof_of_id.file.seek(0, 2)
            id_size = proof_of_id.file.tell()
            proof_of_id.file.seek(0)

            proof_of_address.file.seek(0, 2)
            addr_size = proof_of_address.file.tell()
            proof_of_address.file.seek(0)

            if id_size > MAX_FILE_SIZE:
                raise HTTPException(status_code=400, detail=f"ID file for owner {i+1} exceeds 5MB")
            if addr_size > MAX_FILE_SIZE:
                raise HTTPException(status_code=400, detail=f"Address file for owner {i+1} exceeds 5MB")

            id_filename = sanitize_filename(f"{external_id}_member{i}_id_{proof_of_id.filename}")
            addr_filename = sanitize_filename(f"{external_id}_member{i}_addr_{proof_of_address.filename}")

            with open(os.path.join(UPLOAD_DIR, id_filename), "wb") as f:
                shutil.copyfileobj(proof_of_id.file, f)
            with open(os.path.join(UPLOAD_DIR, addr_filename), "wb") as f:
                shutil.copyfileobj(proof_of_address.file, f)

            member = CompanyMember(
                subscription_id=external_id,
                first_name=first_name,
                middle_name=middle_name,
                last_name=last_name,
                phone_number=phone,
                date_of_birth=dob
            )
            db.add(member)

        db.commit()
        return {"message": "KYC submitted successfully", "external_id": external_id}

    except Exception as e:
        db.rollback()
        print("❌ Error submitting KYC:", str(e))
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": str(e)})

    finally:
        db.close()


