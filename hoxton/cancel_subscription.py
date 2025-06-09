from fastapi import APIRouter, Request, HTTPException
import os
import requests

router = APIRouter()

@router.post("/cancel-subscription")
async def cancel_subscription(req: Request):
    body = await req.json()
    external_id = body.get("external_id")

    if not external_id:
        raise HTTPException(status_code=400, detail="Missing external_id")

    api_key = os.getenv("HOXTON_API_KEY")
    hoxton_url = os.getenv("HOXTON_API_URL")

    if not api_key or not hoxton_url:
        raise HTTPException(status_code=500, detail="Server config missing")

    cancel_url = f"{hoxton_url}/subscription/{external_id}/stop/END_OF_TERM/Requested"

    try:
        response = requests.post(cancel_url, auth=(api_key, ""))

        if response.status_code != 200:
            print("Hoxton cancel failed:", response.text)
            raise HTTPException(status_code=500, detail="Cancel request to Hoxton failed")

        return {"success": True}
    except Exception as e:
        print("Cancel error:", str(e))
        raise HTTPException(status_code=500, detail="Unexpected error")
