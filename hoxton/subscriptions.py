import os
import requests
import httpx
from dotenv import load_dotenv

load_dotenv()  # Loads variables from .env

API_BASE_URL = os.getenv("HOXTON_API_URL")  # Should be: https://api.hoxtonmix.com/v2
API_KEY = os.getenv("HOXTON_API_KEY")  # Your API key as username in Basic Auth


async def create_subscription(data: dict):
    url = f"{API_BASE_URL}/subscription"

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(
                url,
                json=data,
                auth=(API_KEY, "")  # Basic Auth: API key as username, empty password
            )
            response.raise_for_status()
            return response.json() if response.content else {"message": "Subscription created successfully."}

    except httpx.HTTPStatusError as http_err:
        return {
            "error": str(http_err),
            "details": http_err.response.text,
            "status_code": http_err.response.status_code
        }

    except Exception as err:
        return {
            "error": "An unexpected error occurred",
            "details": str(err)
        }


def build_hoxton_payload(subscription, members):
    return {
        "external_id": subscription.external_id,
        "product_id": subscription.product_id,
        "customer": {
            "first_name": subscription.customer_first_name,
            "middle_name": subscription.customer_middle_name or "",
            "last_name": subscription.customer_last_name,
            "email_address": subscription.customer_email,
        },
        "shipping_address": {
            "shipping_address_line_1": subscription.shipping_line_1,
            "shipping_address_line_2": subscription.shipping_line_2 or "",
            "shipping_address_city": subscription.shipping_city,
            "shipping_address_postcode": subscription.shipping_postcode,
            "shipping_address_country": subscription.shipping_country,
        },
        "subscription": {
            "start_date": subscription.start_date.isoformat(),
        },
        "company": {
            "name": subscription.company_name,
            "trading_name": subscription.company_trading_name or subscription.company_name,
            "limited_company_number": subscription.company_number or "",
            "organisation_type": subscription.organisation_type,
            "telephone_number": subscription.telephone_number or "",
        },
        # NEW simplified structure for UBOs (per HMRC rule)
        "members": [
            {
                "first_name": m.first_name,
                "last_name": m.last_name,
                "email_address": m.email
            }
            for m in members
        ]
    }

