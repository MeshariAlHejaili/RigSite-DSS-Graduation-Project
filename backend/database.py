"""Database configuration for RigLab-AI (SQLite + SQLAlchemy)."""

from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Database file at project root
BASE_DIR = Path(__file__).resolve().parent.parent
SQLALCHEMY_DATABASE_URL = f"sqlite:///{BASE_DIR / 'riglab.db'}"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """Dependency that yields a DB session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Create all tables. Import models here so they are registered with Base."""
    from . import models  # noqa: F401
    Base.metadata.create_all(bind=engine)
