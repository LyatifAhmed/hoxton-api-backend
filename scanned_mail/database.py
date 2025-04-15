import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from .base import Base

# ✅ Use DATABASE_URL from environment (Render will provide this)
DATABASE_URL = os.environ.get("DATABASE_URL")

# ✅ Create the engine without SQLite-specific args
engine = create_engine(DATABASE_URL)

# ✅ Set up the session
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

# ✅ Create tables on startup
def init_db():
    Base.metadata.create_all(bind=engine)



