"""SQLAlchemy models for Brand2Context."""

import uuid
import re
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, Text, Integer, Boolean, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session
import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///data/brand2context.db")

engine = create_engine(
    DATABASE_URL.replace("sqlite:///", "sqlite:///"),
    connect_args={"check_same_thread": False},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class Brand(Base):
    __tablename__ = "brands"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=True)
    url = Column(String, nullable=False)
    status = Column(String, default="pending")
    progress_step = Column(String, default="pending")
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    logo_url = Column(String, nullable=True)
    category = Column(String, nullable=True)
    slug = Column(String, unique=True, nullable=True)
    description = Column(Text, nullable=True)
    is_public = Column(Boolean, default=True)
    last_refreshed = Column(DateTime, nullable=True)


class ApiCallLog(Base):
    __tablename__ = "api_call_logs"

    brand_id = Column(String, primary_key=True)
    call_count = Column(Integer, default=0)
    last_accessed = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    name = Column(String, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    is_admin = Column(Boolean, default=False)


def init_db():
    try:
        Base.metadata.create_all(bind=engine)
    except Exception:
        pass


def generate_slug(name: str, db: Session) -> str:
    if not name:
        return str(uuid.uuid4())

    slug = name.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = re.sub(r"-+", "-", slug)
    slug = slug.strip("-")

    if not slug:
        return str(uuid.uuid4())

    existing = db.query(Brand).filter(Brand.slug == slug).first()
    if not existing:
        return slug

    counter = 1
    while db.query(Brand).filter(Brand.slug == f"{slug}-{counter}").first():
        counter += 1
    return f"{slug}-{counter}"


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
