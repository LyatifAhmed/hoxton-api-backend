import os
import requests
from dotenv import load_dotenv

load_dotenv()

API_BASE_URL = os.getenv("HOXTON_API_URL")
API_KEY = os.getenv("HOXTON_API_KEY")

def get_hoxton_subscription(external_id: str):
    url = f"{API_BASE_URL}/subscription/{external_id}"
    try:
        response = requests.get(url, auth=(API_KEY, ""))
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"❌ Error fetching subscription {external_id}: {e}")
        raise
