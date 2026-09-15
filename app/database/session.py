"""
Database session and connection management for SQLite.
Configures WAL mode, foreign keys, and connection pooling.
"""

import os
from contextlib import contextmanager
from typing import Generator
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from loguru import logger

from app.config.settings import get_settings
from app.database.models import Base

settings = get_settings()

# Ensure parent directory of sqlite db exists
if settings.database_url.startswith("sqlite:///"):
    db_path = settings.database_url.replace("sqlite:///", "")
    db_dir = os.path.dirname(db_path)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)

# Create engine with connect_args for SQLite
connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}

engine = create_engine(
    settings.database_url,
    connect_args=connect_args,
    echo=False,
    pool_pre_ping=True,
)


@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """Enable WAL mode, synchronous=NORMAL, and foreign keys for high SQLite performance."""
    if settings.database_url.startswith("sqlite"):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA cache_size=-64000")  # 64MB cache
        cursor.close()


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db() -> None:
    """Initialize database schemas and create tables if they do not exist."""
    try:
        Base.metadata.create_all(bind=engine)
        logger.info(f"Database initialized successfully at {settings.database_url}")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise


@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    """Provide a transactional database session scope."""
    session: Session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        logger.error(f"Database transaction error: {e}")
        raise
    finally:
        session.close()
