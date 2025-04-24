import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from .base import Base
from .models import KycToken  
# ✅ Use DATABASE_URL from environment (Render will provide this)
DATABASE_URL = os.environ.get("DATABASE_URL")

# ✅ Create the engine without SQLite-specific args
engine = create_engine(DATABASE_URL)

# ✅ Set up the session
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

# ✅ Create tables on startup
def init_db():
    # ❗ WARNING: This will delete all existing data in kyc_tokens table
    try:
        KycToken.__table__.drop(engine)  # Drop existing table
        print("🧨 Dropped old kyc_tokens table")
    except Exception as e:
        print("⚠️ Failed to drop table (maybe doesn't exist yet):", e)

    Base.metadata.create_all(bind=engine)  # Recreate tables from models
    print("✅ Recreated tables")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


