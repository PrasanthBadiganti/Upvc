from __future__ import annotations

import os
import sqlite3
import sys
from pathlib import Path
from collections.abc import Generator
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

# Check if running as frozen executable (PyInstaller)
IS_FROZEN = getattr(sys, "frozen", False)

def _get_data_dir() -> Path:
    """Get data directory (where database and settings live)."""
    if getenv := os.getenv("UPVC_DATA_DIR"):
        path = Path(getenv)
    elif IS_FROZEN:
        # Writable data lives next to the .exe (easy to find + back up), the
        # same layout BROMS uses: dist/UPVC Pro/data/upvc_pro.db
        path = Path(sys.executable).resolve().parent / "data"
    else:
        path = Path(__file__).resolve().parents[1]

    path.mkdir(parents=True, exist_ok=True)
    return path

DATA_DIR = _get_data_dir()
BACKEND_DIR = DATA_DIR
DB_PATH = DATA_DIR / "upvc_pro.db"

DEFAULT_DB_PATH = DB_PATH
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


def get_connection() -> sqlite3.Connection:
    """Get a raw SQLite connection (for backup/restore operations)."""
    return sqlite3.connect(str(DB_PATH))


@contextmanager
def db_cursor():
    """Context manager for SQLite cursor operations."""
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    try:
        yield cursor
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()
