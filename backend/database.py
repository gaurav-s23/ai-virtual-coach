from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.pool import StaticPool
import os
from dotenv import load_dotenv

load_dotenv()

SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL") or "sqlite+pysqlite:///./app.db"

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
    )
else:
    # Engine config for Postgres
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL,
        pool_size=10,        # Standard for Postgres to handle concurrent connections
        max_overflow=20      # Limit for peak traffic
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()