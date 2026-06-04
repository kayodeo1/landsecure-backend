"""Database engine, session factory and declarative Base.

Dialect-agnostic: SQLite for local dev, PostgreSQL+PostGIS for production. The
geometry of each zone is stored as a portable JSON ring (``[[lat,lng], …]`` exactly
like the mockup's ``zones.js``) so the same schema runs on both engines; the
production PostGIS path (see ``services/risk_postgis.py``) adds a real ``GEOMETRY``
column via migration.
"""
from __future__ import annotations

import os
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from .config import settings


class Base(DeclarativeBase):
    pass


def _make_engine():
    if settings.is_sqlite:
        # ensure the sqlite file's directory exists
        path = settings.database_url.replace("sqlite:///", "")
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        return create_engine(
            settings.database_url,
            connect_args={"check_same_thread": False},
            echo=False,
        )
    return create_engine(settings.database_url, pool_pre_ping=True, echo=False)


engine = _make_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_db() -> Generator:
    """FastAPI dependency yielding a scoped session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create tables if they don't exist (dev convenience; prod uses Alembic)."""
    from . import models  # noqa: F401  (register models on Base.metadata)

    Base.metadata.create_all(bind=engine)
