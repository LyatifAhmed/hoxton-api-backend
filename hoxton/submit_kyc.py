from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from scanned_mail.database import SessionLocal
from scanned_mail.models import Subscription, CompanyMember
from datetime import datetime
import traceback
import pycountry
import re

router = APIRouter()

# 🚀 New Save KYC TEMPORARILY route
@router.post("/api/save-kyc-temp")
async def save_kyc_temp(request: Request):
    db: Session = SessionLocal()
    try:
        payload = await request.json()
        payload = {k: v.strip() if isinstance(v, str) else v for k, v in payload.items()}

        # Extract basic fields
        product_id = payload.get("product_id")
        customer_email = payload.get("email")
        customer_first_name = payload.get("customer_first_name")
        customer_last_name = payload.get("customer_last_name")
        company_name = payload.get("company_name")
        trading_name = payload.get("trading_name", "").strip() or company_name
        organisation_type = payload.get("organisation_type")
        limited_company_number = payload.get("limited_company_number", "")
        telephone_number = payload.get("phone_number", "").strip() or None

        address_line_1 = payload.get("address_line_1")
        address_line_2 = payload.get("address_line_2", "")
        city = payload.get("city")
        postcode = payload.get("postcode")
        raw_country = payload.get("country", "")
        members = payload.get("members", [])

        # Basic validation
        if not re.match(r"[^@]+@[^@]+\.[^@]+", customer_email):
            raise HTTPException(status_code=400, detail="Invalid customer email format")

        try:
            organisation_type = int(organisation_type)
        except ValueError:
            raise HTTPException(status_code=400, detail="Organisation type must be an integer.")

        try:
            if len(raw_country) == 2:
                country = raw_country.upper()
            else:
                match = pycountry.countries.get(name=raw_country) or pycountry.countries.search_fuzzy(raw_country)[0]
                country = match.alpha_2
        except Exception:
            raise HTTPException(status_code=400, detail=f"Invalid country: {raw_country}")

        # Check if already exists
        existing = db.query(Subscription).filter_by(customer_email=customer_email).first()
        if existing:
            raise HTTPException(status_code=409, detail="This email is already linked to a business.")

        # Generate external_id
        external_id = customer_email.split("@")[0] + "-" + datetime.utcnow().strftime("%Y%m%d%H%M%S")

        # Save subscription (but still pending payment)
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
            start_date=datetime.utcnow(),
            review_status="PENDING"
        )
        db.add(subscription)

        # Save owners
        for m in members:
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

        db.commit()

        return {
            "message": "KYC temporarily saved. Proceed to payment.",
            "external_id": external_id,
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": str(e)})
    finally:
        db.close()

# (your existing /api/submit-kyc stays untouched here below ✅)


@router.post("/api/submit-kyc")
async def submit_kyc(request: Request):
    db: Session = SessionLocal()

    try:
        payload = await request.json()
        payload = {k: v.strip() if isinstance(v, str) else v for k, v in payload.items()}

        # Extract required fields
        product_id = payload.get("product_id")
        customer_email = payload.get("email")
        customer_first_name = payload.get("customer_first_name")
        customer_last_name = payload.get("customer_last_name")
        company_name = payload.get("company_name")
        trading_name = payload.get("trading_name", "").strip() or company_name
        organisation_type = payload.get("organisation_type")
        limited_company_number = payload.get("limited_company_number", "")
        telephone_number = payload.get("phone_number", "").strip() or None

        address_line_1 = payload.get("address_line_1")
        address_line_2 = payload.get("address_line_2", "")
        city = payload.get("city")
        postcode = payload.get("postcode")
        raw_country = payload.get("country", "")
        members = payload.get("members", [])

        # Basic validation
        email_regex = r"[^@]+@[^@]+\.[^@]+"
        if not re.match(email_regex, customer_email):
            raise HTTPException(status_code=400, detail="Invalid customer email format")
        if db.query(Subscription).filter_by(customer_email=customer_email).first():
            raise HTTPException(status_code=409, detail="This email is already linked to a business.")

        for idx, m in enumerate(members):
            member_email = m.get("email", "")
            if not re.match(email_regex, member_email):
                raise HTTPException(status_code=400, detail=f"Invalid email format for member {idx + 1}")

        try:
            organisation_type = int(organisation_type)
        except ValueError:
            raise HTTPException(status_code=400, detail="Organisation type must be an integer.")

        try:
            if len(raw_country) == 2:
                country = raw_country.upper()
            else:
                match = pycountry.countries.get(name=raw_country) or pycountry.countries.search_fuzzy(raw_country)[0]
                country = match.alpha_2
        except Exception:
            raise HTTPException(status_code=400, detail=f"Invalid country: {raw_country}")

        required_fields = [product_id, customer_email, customer_first_name, customer_last_name,
                           company_name, organisation_type, address_line_1, city, postcode, country]
        if not all(required_fields):
            raise HTTPException(status_code=400, detail="Missing required fields.")

        # Generate external_id
        external_id = customer_email.split("@")[0] + "-" + datetime.utcnow().strftime("%Y%m%d%H%M%S")

        # Save subscription
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
            start_date=datetime.utcnow(),
            review_status="PENDING"
        )
        db.add(subscription)

        # Save members
        for m in members:
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

        db.commit()

        return {
            "message": "KYC submitted and saved. Proceed to payment.",
            "external_id": external_id,
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": str(e)})
    finally:
        db.close()









