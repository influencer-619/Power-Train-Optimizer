from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from backend.paths import db_path

_ENGINE = None
_SessionLocal = None


def get_engine():
    global _ENGINE, _SessionLocal
    if _ENGINE is None:
        url = f"sqlite:///{db_path().as_posix()}"
        _ENGINE = create_engine(url, connect_args={"check_same_thread": False})
        _SessionLocal = sessionmaker(bind=_ENGINE, autoflush=False, autocommit=False)
    return _ENGINE


def SessionLocal() -> Session:
    get_engine()
    assert _SessionLocal is not None
    return _SessionLocal()
