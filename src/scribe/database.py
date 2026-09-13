"""
database.py - SQLAlchemy database setup for scribe project

This module provides database connectivity to the shared PostgreSQL database
used by both the scribe and clerk projects. The database is hosted on AWS RDS.
"""

import os
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get database URL from environment
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError(
        "DATABASE_URL environment variable is not set. "
        "Please configure it in your .env file."
    )

# Create SQLAlchemy engine
# pool_pre_ping helps avoid stale connections to AWS RDS
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
    echo=False,  # Set to True for SQL query logging
)

# Create SessionLocal class for database sessions
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """
    Dependency function that provides a database session.

    Usage example:
        from scribe.database import get_db

        db = next(get_db())
        try:
            # Use db session
            results = db.query(Model).all()
        finally:
            db.close()

    Or in FastAPI/Flask context:
        @app.route("/items")
        def get_items():
            db = next(get_db())
            try:
                items = db.query(Item).all()
                return items
            finally:
                db.close()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_db_session() -> Session:
    """
    Get a database session directly (non-generator version).
    Remember to close the session when done!

    Usage:
        from scribe.database import get_db_session

        db = get_db_session()
        try:
            results = db.query(Model).all()
        finally:
            db.close()
    """
    return SessionLocal()
