from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from scanned_mail.database import SessionLocal
from scanned_mail.models import Subscription, CompanyMember, KycToken
from datetime import datetime
import traceback
import httpx
import os
from base64 import b64encode

router = APIRouter()

HOXTON_API_URL = os.getenv("HOXTON_API_URL")
HOXTON_API_KEY = os.getenv("HOXTON_API_KEY")

@router.post("/api/submit-kyc")
async def submit_kyc(request: Request):
    db: Session = SessionLocal()

    try:
        payload = await request.json()
        token = payload.get("token")
        product_id = payload.get("product_id")
        customer_email = payload.get("customer_email")
        customer_first_name = payload.get("customer_first_name")
        customer_last_name = payload.get("customer_last_name")
        company_name = payload.get("company_name")
        trading_name = payload.get("trading_name")
        organisation_type = payload.get("organisation_type")
        limited_company_number = payload.get("limited_company_number")
        telephone_number = payload.get("phone_number")
        address_line_1 = payload.get("address_line_1")
        address_line_2 = payload.get("address_line_2")
        city = payload.get("city")
        postcode = payload.get("postcode")
        country = payload.get("country")
        members = payload.get("members", [])

        if not all([token, product_id, customer_email, company_name, organisation_type, address_line_1, city, postcode, country]):
            raise HTTPException(status_code=400, detail="Missing required fields.")

        kyc_token = db.query(KycToken).filter(KycToken.token == token).first()
        if not kyc_token:
            raise HTTPException(status_code=404, detail="Invalid KYC token")
        if kyc_token.kyc_submitted:
            raise HTTPException(status_code=409, detail="This KYC token has already been used.")

        external_id = customer_email.split("@")[0] + "-" + datetime.utcnow().strftime("%Y%m%d%H%M%S")

        subscription = Subscription(
            external_id=external_id,
            product_id=product_id,
            customer_email=customer_email,
            customer_first_name=customer_first_name or "",
            customer_last_name=customer_last_name or "",
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
            telephone_number=telephone_number
        )
        db.add(subscription)

        member_objects = []
        for idx, m in enumerate(members):
            if not m.get("email"):
                raise HTTPException(status_code=400, detail=f"Missing email for member {idx+1}")
            dob_iso = datetime.strptime(m["date_of_birth"], "%Y-%m-%d").isoformat() + "T00:00:00.000Z"
            member = CompanyMember(
                subscription_id=external_id,
                first_name=m.get("first_name", ""),
                middle_name=m.get("middle_name", ""),
                last_name=m.get("last_name", ""),
                phone_number=m.get("phone_number", ""),
                email=m.get("email"),
                date_of_birth=dob_iso,
            )
            db.add(member)
            member_objects.append({
                "first_name": m.get("first_name", ""),
                "middle_name": m.get("middle_name", ""),
                "last_name": m.get("last_name", ""),
                "phone_number": m.get("phone_number", ""),
                "date_of_birth": dob_iso
            })

        kyc_token.kyc_submitted = 1
        db.commit()

        hoxton_payload = {
            "external_id": external_id,
            "product_id": product_id,
            "customer": {
                "first_name": customer_first_name,
                "middle_name": "",
                "last_name": customer_last_name,
                "email_address": customer_email,
            },
            "shipping_address": {
                "shipping_address_line_1": address_line_1,
                "shipping_address_line_2": address_line_2,
                "shipping_address_city": city,
                "shipping_address_postcode": postcode,
                "shipping_address_country": country
            },
            "subscription": {
                "start_date": datetime.utcnow().isoformat() + "Z"
            },
            "company": {
                "name": company_name,
                "trading_name": trading_name,
                "limited_company_number": limited_company_number,
                "organisation_type": organisation_type,
                "telephone_number": telephone_number,
            },
            "members": member_objects
        }

        async with httpx.AsyncClient() as client:
            auth_header = b64encode(f"{HOXTON_API_KEY}:".encode()).decode()
            response = await client.post(
                HOXTON_API_URL,
                json=hoxton_payload,
                headers={"Authorization": f"Basic {auth_header}"}
            )

        if response.status_code != 200:
            raise HTTPException(status_code=400, detail=f"Error submitting to Hoxton Mix: {response.text}")

        return {"message": "KYC submitted and forwarded successfully", "external_id": external_id}

    except Exception as e:
        db.rollback()
        print("❌ Error submitting or forwarding KYC:", str(e))
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": str(e)})

    finally:
        db.close()



