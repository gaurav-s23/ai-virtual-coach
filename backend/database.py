from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.pool import StaticPool
import os
import logging
from dotenv import load_dotenv

load_dotenv()

# Get database URL from environment, fallback to SQLite for local development
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL") or "sqlite+pysqlite:///./app.db"

logger = logging.getLogger(__name__)

if SQLALCHEMY_DATABASE_URL.startswith("sqlite"):
    # Local/dev/test-friendly default (no DATABASE_URL required).
    connect_args = {"check_same_thread": False}
    if "file:" in SQLALCHEMY_DATABASE_URL:
        # Allows `sqlite+pysqlite:///file::memory:?cache=shared` style URLs
        connect_args["uri"] = True

    poolclass = None
    if ":memory:" in SQLALCHEMY_DATABASE_URL:
        # Ensure in-memory DB survives across connections during tests.
        poolclass = StaticPool

    engine = create_engine(
        SQLALCHEMY_DATABASE_URL,
        connect_args=connect_args,
        poolclass=poolclass,
        echo=os.getenv("SQL_DEBUG", "false").lower() == "true"  # Enable SQL logging if debug mode
    )
elif SQLALCHEMY_DATABASE_URL.startswith("postgresql"):
    # Engine config for local PostgreSQL
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL,
        pool_size=10,        # Standard for Postgres to handle concurrent connections
        max_overflow=20,     # Limit for peak traffic
        echo=os.getenv("SQL_DEBUG", "false").lower() == "true",  # Enable SQL logging if debug mode
        connect_args={"connect_timeout": 10}  # Connection timeout for local dev
    )
    logger.info(f"Connected to PostgreSQL database: {SQLALCHEMY_DATABASE_URL.split('@')[1] if '@' in SQLALCHEMY_DATABASE_URL else 'local'}")
else:
    # Fallback for other database types
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL,
        echo=os.getenv("SQL_DEBUG", "false").lower() == "true"
    )
    logger.info(f"Connected to database: {SQLALCHEMY_DATABASE_URL}")

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()