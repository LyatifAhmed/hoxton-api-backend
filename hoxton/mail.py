import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from dotenv import load_dotenv
import traceback
from datetime import datetime

load_dotenv()

SMTP_SERVER = os.getenv("SMTP_HOST")          # smtp.zoho.eu
SMTP_PORT = int(os.getenv("SMTP_PORT"))       # 587
SMTP_USERNAME = os.getenv("SMTP_USER")        # no-reply@betaoffice.uk
SMTP_PASSWORD = os.getenv("SMTP_PASS")        # Zoho App Password

def log_email_error(error: Exception, recipient: str):
    with open("email_error.log", "a") as f:
        f.write(f"\n---\nTime: {datetime.utcnow().isoformat()}\n")
        f.write(f"To: {recipient}\n")
        f.write("Error:\n")
        f.write("".join(traceback.format_exception(type(error), error, error.__traceback__)))

def send_kyc_email(recipient_email: str, kyc_token: str):
    link = f"https://betaoffice.uk/kyc?token={kyc_token}"

    subject = "Complete Your KYC Form - BetaOffice"
    body = f"""
Hello,

Thank you for subscribing to BetaOffice. To complete your account setup, please fill out your KYC form using the link below:

{link}

This link will expire in 3 days.

If you need help, reply to this email.

Best regards,  
BetaOffice Team
"""

    msg = MIMEMultipart()
    msg["From"] = SMTP_USERNAME
    msg["To"] = recipient_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
            server.send_message(msg)
        print(f"✅ KYC email sent to {recipient_email}")
    except Exception as e:
        print(f"❌ Failed to send email to {recipient_email}: {e}")
        log_email_error(e, recipient_email)

