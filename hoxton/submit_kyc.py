from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from scanned_mail.database import SessionLocal
from scanned_mail.models import Subscription, CompanyMember, KycToken
from datetime import datetime
from hoxton.subscriptions import create_subscription, build_hoxton_payload
from hoxton.mail import send_customer_verification_notice
import traceback
import pycountry
import re

router = APIRouter()

@router.post("/api/submit-kyc")
async def submit_kyc(request: Request):
    db: Session = SessionLocal()

    try:
        payload = await request.json()
        payload = {k: v.strip() if isinstance(v, str) else v for k, v in payload.items()}
        token = payload.get("token")
        product_id = payload.get("product_id")
        customer_email = payload.get("email")
        customer_first_name = payload.get("customer_first_name")
        customer_last_name = payload.get("customer_last_name")

        company_name = payload.get("company_name")
        trading_name = payload.get("trading_name", "").strip() or company_name
        organisation_type = payload.get("organisation_type")
        limited_company_number = payload.get("limited_company_number", "")
        telephone_number = payload.get("phone_number", "")

        address_line_1 = payload.get("address_line_1")
        address_line_2 = payload.get("address_line_2", "")
        city = payload.get("city")
        postcode = payload.get("postcode")
        raw_country = payload.get("country", "")
        members = payload.get("members", [])

        # Email format validation
        email_regex = r"[^@]+@[^@]+\.[^@]+"
        if not re.match(email_regex, customer_email):
            raise HTTPException(status_code=400, detail="Invalid customer email format")

        # Validate member emails
        for idx, m in enumerate(members):
            member_email = m.get("email", "")
            if not re.match(email_regex, member_email):
                raise HTTPException(status_code=400, detail=f"Invalid email format for member {idx + 1}")

        # Convert organisation_type to integer
        try:
            organisation_type = int(organisation_type)
        except ValueError:
            raise HTTPException(status_code=400, detail="Organisation type must be an integer.")

        # Convert country to alpha_2 code
        try:
            if len(raw_country) == 2:
                country = raw_country.upper()
            else:
                match = pycountry.countries.get(name=raw_country) or pycountry.countries.search_fuzzy(raw_country)[0]
                country = match.alpha_2
        except Exception:
            raise HTTPException(status_code=400, detail=f"Invalid country: {raw_country}")

        # Required field check
        if not all([token, product_id, customer_email, customer_first_name, customer_last_name,
                    company_name, organisation_type, address_line_1, city, postcode, country]):
            raise HTTPException(status_code=400, detail="Missing required fields.")

        # Token check
        kyc_token = db.query(KycToken).filter(KycToken.token == token).first()
        if not kyc_token:
            raise HTTPException(status_code=404, detail="Invalid KYC token")
        if kyc_token.kyc_submitted:
            raise HTTPException(status_code=409, detail="This KYC token has already been used.")

        external_id = customer_email.split("@")[0] + "-" + datetime.utcnow().strftime("%Y%m%d%H%M%S")

        # Save subscription to DB
        subscription = Subscription(
            external_id=external_id,
            product_id=product_id,
            customer_email=customer_email,
            customer_first_name=customer_first_name,
            customer_last_name=customer_last_name,
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
            telephone_number=telephone_number,
            start_date=datetime.utcnow()
        )
        db.add(subscription)

        # Save UBOs
        for idx, m in enumerate(members):
            member = CompanyMember(
                subscription_id=external_id,
                first_name=m.get("first_name", ""),
                middle_name=m.get("middle_name", ""),
                last_name=m.get("last_name", ""),
                phone_number=m.get("phone_number", ""),
                email=m.get("email"),
                date_of_birth=datetime.strptime(m.get("date_of_birth"), "%Y-%m-%d") if m.get("date_of_birth") else None,
            )
            db.add(member)

        kyc_token.kyc_submitted = 1
        db.commit()
        print("✅ Owners to be contacted:")
        for m in members:
            print("-", m.get("email"))

        # Reload saved members
        saved_members = db.query(CompanyMember).filter(CompanyMember.subscription_id == external_id).all()

        # Build and send to Hoxton
        hoxton_payload = build_hoxton_payload(subscription, saved_members)
        hoxton_response = await create_subscription(hoxton_payload)
        print("✅ Sending to Hoxton Mix:", hoxton_payload)
        print("✅ Hoxton Mix Response:", hoxton_response)
        await send_customer_verification_notice(customer_email, company_name)


        if "error" in hoxton_response:
            return JSONResponse(status_code=502, content={
                "message": "KYC saved but failed to send to Hoxton Mix.",
                "external_id": external_id,
                "hoxton_error": hoxton_response
            })

        
        return {
            "message": "KYC submitted and sent to Hoxton Mix",
            "external_id": external_id,
            "hoxton_response": hoxton_response
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        print("❌ Error submitting KYC:", str(e))
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": str(e)})
    finally:
        db.close()









