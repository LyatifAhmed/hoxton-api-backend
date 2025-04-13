from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

import os
DATABASE_URL = f"sqlite:///{os.path.dirname(__file__)}/scanned_mail.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()

def init_db():
    from .models import KycToken, Subscription, CompanyMember, ScannedMail
    Base.metadata.create_all(bind=engine)


