from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from .base import Base



class KycToken(Base):
    __tablename__ = "kyc_tokens"

    token = Column(String, primary_key=True, index=True)
    date_created = Column(DateTime, default=datetime.utcnow)
    email = Column(String, index=True)
    product_id = Column(Integer)
    plan_name = Column(String)
    expires_at = Column(DateTime)
    kyc_submitted = Column(Integer, default=0)
    session_id = Column(String, index=True, nullable=True)  # ✅ Add this line

class Subscription(Base):
    __tablename__ = "subscriptions"

    external_id = Column(String, primary_key=True)
    product_id = Column(Integer)
    customer_first_name = Column(String)
    customer_middle_name = Column(String)
    customer_last_name = Column(String)
    customer_email = Column(String)

    shipping_line_1 = Column(String)
    shipping_line_2 = Column(String)
    shipping_line_3 = Column(String)
    shipping_city = Column(String)
    shipping_postcode = Column(String)
    shipping_state = Column(String)
    shipping_country = Column(String)

    company_name = Column(String)
    company_trading_name = Column(String)
    company_number = Column(String)
    organisation_type = Column(Integer)
    telephone_number = Column(String)

    start_date = Column(DateTime, default=datetime.utcnow)

    review_status = Column(String, default="pending")
    notes = Column(Text, nullable=True)        # 📝 Optional internal notes

    members = relationship("CompanyMember", back_populates="subscription")



class CompanyMember(Base):
    __tablename__ = "company_members"

    id = Column(Integer, primary_key=True, index=True)
    subscription_id = Column(String, ForeignKey("subscriptions.external_id"))
    
    first_name = Column(String)
    middle_name = Column(String)
    last_name = Column(String)
    phone_number = Column(String)
    date_of_birth = Column(DateTime)

    subscription = relationship("Subscription", back_populates="members")


class ScannedMail(Base):
    __tablename__ = "scanned_mails"

    id = Column(Integer, primary_key=True, index=True)
    external_id = Column(String, index=True)
    url = Column(Text)
    url_envelope_front = Column(Text)
    url_envelope_back = Column(Text)
    file_name = Column(String)
    created_at = Column(DateTime)

    sender_name = Column(String)
    document_title = Column(String)
    reference_number = Column(String)
    summary = Column(String)
    industry = Column(String)

    categories = Column(String)         # Stored as comma-separated string
    sub_categories = Column(String)     # Stored as comma-separated string
    key_information = Column(Text)      # Store JSON string if needed


