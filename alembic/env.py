import os
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from alembic import context

# ✅ Load environment variables (e.g., DATABASE_URL)
from dotenv import load_dotenv
load_dotenv()

# ✅ Import your Base metadata from scanned_mail.models
from scanned_mail.models import Base  # 🔄 Update if your path differs

# Alembic Config object (comes from alembic.ini)
config = context.config

# Set the SQLAlchemy URL dynamically from env (Render or local .env)
DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL:
    config.set_main_option("sqlalchemy.url", DATABASE_URL)

# Set up logging if file config is defined
if config.config_file_name:
    fileConfig(config.config_file_name)

# ✅ Autogenerate support via SQLAlchemy models
target_metadata = Base.metadata

def run_migrations_offline() -> None:
    """Run migrations without a DB connection (for generating SQL scripts)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online() -> None:
    """Run migrations with a live DB connection."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True  # ✅ Ensures column type changes are detected
        )

        with context.begin_transaction():
            context.run_migrations()

# ✅ Entry point
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
