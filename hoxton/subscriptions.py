import os
import requests
from dotenv import load_dotenv

load_dotenv()  # Loads variables from .env

API_BASE_URL = os.getenv("HOXTON_API_BASE")  # Should be: https://api.hoxtonmix.com/v2
API_KEY = os.getenv("HOXTON_API_KEY")  # Your API key as username in Basic Auth


def create_subscription(data: dict):
    url = f"{API_BASE_URL}/subscription"

    try:
        response = requests.post(
            url,
            json=data,
            auth=(API_KEY, ""),  # Basic Auth with no password
            timeout=10
        )
        response.raise_for_status()
        return response.json() if response.content else {"message": "Subscription created successfully."}
    
    except requests.exceptions.HTTPError as http_err:
        return {"error": str(http_err), "details": response.text}
    
    except Exception as err:
        return {"error": "An unexpected error occurred", "details": str(err)}
