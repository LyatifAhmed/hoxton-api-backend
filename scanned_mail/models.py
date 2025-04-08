from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class ScannedMail(Base):
    __tablename__ = "scanned_mails"

    id = Column(Integer, primary_key=True, index=True)
    external_id = Column(String, index=True)
    sender_name = Column(String)
    document_title = Column(String)
    summary = Column(String)
    url = Column(String)  # Main document PDF
    url_envelope_front = Column(String)  # Envelope front image
    url_envelope_back = Column(String)  # Envelope back image
    received_at = Column(DateTime, default=datetime.utcnow)
    company_name = Column(String, nullable=True)


