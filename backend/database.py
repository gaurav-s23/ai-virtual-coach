from sqlalchemy import create_engine, event
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.pool import StaticPool, QueuePool
from sqlalchemy.exc import SQLAlchemyError, DisconnectionError
import os
import logging
from dotenv import load_dotenv
from typing import Optional

load_dotenv()

# Get database URL from environment, fallback to SQLite for local development
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL") or "sqlite+pysqlite:///./app.db"

logger = logging.getLogger(__name__)

# Database configuration constants
DEFAULT_POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "10"))
DEFAULT_MAX_OVERFLOW = int(os.getenv("DB_MAX_OVERFLOW", "20"))
DEFAULT_POOL_TIMEOUT = int(os.getenv("DB_POOL_TIMEOUT", "30"))
DEFAULT_POOL_RECYCLE = int(os.getenv("DB_POOL_RECYCLE", "3600"))  # 1 hour
DEFAULT_CONNECT_TIMEOUT = int(os.getenv("DB_CONNECT_TIMEOUT", "10"))

def get_database_config() -> dict:
    """Get database configuration based on environment and database type."""
    config = {
        "echo": os.getenv("SQL_DEBUG", "false").lower() == "true",
        "future": True,  # Use SQLAlchemy 2.0 style
    }
    
    if SQLALCHEMY_DATABASE_URL.startswith("sqlite"):
        # SQLite configuration
        connect_args = {"check_same_thread": False}
        if "file:" in SQLALCHEMY_DATABASE_URL:
            connect_args["uri"] = True
        
        config.update({
            "connect_args": connect_args,
            "poolclass": StaticPool if ":memory:" in SQLALCHEMY_DATABASE_URL else None,
            "pool_pre_ping": True,
        })
        
    elif SQLALCHEMY_DATABASE_URL.startswith("postgresql"):
        # PostgreSQL configuration optimized for production
        config.update({
            "poolclass": QueuePool,
            "pool_size": DEFAULT_POOL_SIZE,
            "max_overflow": DEFAULT_MAX_OVERFLOW,
            "pool_timeout": DEFAULT_POOL_TIMEOUT,
            "pool_recycle": DEFAULT_POOL_RECYCLE,
            "pool_pre_ping": True,
            "connect_args": {
                "connect_timeout": DEFAULT_CONNECT_TIMEOUT,
                "command_timeout": 30,
                "options": "-c timezone=utc",
            }
        })
        
    else:
        # Fallback for other database types
        config.update({
            "pool_size": min(DEFAULT_POOL_SIZE, 5),  # Conservative for unknown DBs
            "max_overflow": min(DEFAULT_MAX_OVERFLOW, 10),
            "pool_timeout": DEFAULT_POOL_TIMEOUT,
            "pool_pre_ping": True,
        })
    
    return config

def add_database_event_listeners(engine):
    """Add event listeners for connection monitoring and error handling."""
    
    @event.listens_for(engine, "connect")
    def receive_connect(dbapi_connection, connection_record):
        """Log new database connections."""
        logger.debug(f"New database connection established: {dbapi_connection}")
    
    @event.listens_for(engine, "checkout")
    def receive_checkout(dbapi_connection, connection_record, connection_proxy):
        """Log connection checkout."""
        logger.debug("Database connection checked out from pool")
    
    @event.listens_for(engine, "checkin")
    def receive_checkin(dbapi_connection, connection_record):
        """Log connection checkin."""
        logger.debug("Database connection returned to pool")
    
    @event.listens_for(engine, "invalidate")
    def receive_invalidate(dbapi_connection, connection_record, exception):
        """Handle connection invalidation."""
        logger.warning(f"Database connection invalidated: {exception}")

# Create engine with optimized configuration
try:
    db_config = get_database_config()
    engine = create_engine(SQLALCHEMY_DATABASE_URL, **db_config)
    
    # Add event listeners for monitoring
    add_database_event_listeners(engine)
    
    # Log database connection info
    if SQLALCHEMY_DATABASE_URL.startswith("postgresql"):
        # Extract safe connection info for logging
        safe_url = SQLALCHEMY_DATABASE_URL
        if "@" in safe_url:
            # Hide credentials in logs
            parts = safe_url.split("@")
            safe_url = f"***@{parts[1]}"
        logger.info(f"Connected to PostgreSQL database: {safe_url}")
        logger.info(f"Pool configuration: size={DEFAULT_POOL_SIZE}, max_overflow={DEFAULT_MAX_OVERFLOW}")
    else:
        logger.info(f"Connected to database: {SQLALCHEMY_DATABASE_URL.split('://')[0]}://***")
        
except SQLAlchemyError as e:
    logger.critical(f"Failed to create database engine: {e}")
    raise

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()