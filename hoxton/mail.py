import aiosmtplib
from email.message import EmailMessage
import os
from dotenv import load_dotenv
from datetime import datetime
import traceback

load_dotenv()

SMTP_SERVER = os.getenv("SMTP_HOST")          
SMTP_PORT = int(os.getenv("SMTP_PORT"))       
SMTP_USERNAME = os.getenv("SMTP_USER")        
SMTP_PASSWORD = os.getenv("SMTP_PASS")        

def log_email_error(error: Exception, recipient: str):
    with open("email_error.log", "a") as f:
        f.write(f"\n---\nTime: {datetime.utcnow().isoformat()}\n")
        f.write(f"To: {recipient}\n")
        f.write("Error:\n")
        f.write("".join(traceback.format_exception(type(error), error, error.__traceback__)))

async def send_kyc_email(recipient_email: str, kyc_token: str):
    link = f"https://betaoffice.uk/kyc?token={kyc_token}"

    msg = EmailMessage()
    msg["From"] = SMTP_USERNAME
    msg["To"] = recipient_email
    msg["Subject"] = "Complete Your KYC Form - BetaOffice"
    msg.set_content(f"""
Hello,

Thank you for subscribing to BetaOffice. To complete your account setup, please fill out your KYC form using the link below:

{link}

This link will expire in 3 days.

If you need help, reply to this email.

Best regards,  
BetaOffice Team
""")

    try:
        await aiosmtplib.send(
            msg,
            hostname=SMTP_SERVER,
            port=SMTP_PORT,
            username=SMTP_USERNAME,
            password=SMTP_PASSWORD,
            start_tls=True,
        )
        print(f"✅ KYC email sent to {recipient_email}")
    except Exception as e:
        print(f"❌ Failed to send email to {recipient_email}: {e}")
        log_email_error(e, recipient_email)

