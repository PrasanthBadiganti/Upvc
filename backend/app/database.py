from __future__ import annotations

import os
import sys
from pathlib import Path
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

def _default_db_path() -> Path:
    data_dir = os.getenv("UPVC_DATA_DIR")
    if data_dir:
        path = Path(data_dir)
    elif getattr(sys, "frozen", False):
        path = Path(os.getenv("LOCALAPPDATA", Path.home())) / "UPVC Pro"
    else:
        path = Path(__file__).resolve().parents[1]

    path.mkdir(parents=True, exist_ok=True)
    return path / "upvc_pro.db"


DEFAULT_DB_PATH = _default_db_path()
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DEFAULT_DB_PATH.as_posix()}")
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
