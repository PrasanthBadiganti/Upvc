#!/usr/bin/env python
"""Initialize UPVC Pro database with schema"""

import os
import sys
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

from app.database import engine, Base

# Remove old database if it exists
db_path = Path(__file__).parent / "upvc_pro.db"
if db_path.exists():
    db_path.unlink()
    print(f"Removed old database: {db_path}")

# Create all tables
print("Creating database schema...")
Base.metadata.create_all(bind=engine)

# Verify by checking if we can connect
from sqlalchemy import text
with engine.connect() as connection:
    result = connection.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))
    tables = result.fetchall()
    print(f"Created {len(tables)} tables")
    for table in tables[:5]:
        print(f"  - {table[0]}")
    if len(tables) > 5:
        print(f"  ... and {len(tables) - 5} more")

print(f"\nDatabase ready: {db_path}")
print(f"File size: {db_path.stat().st_size} bytes")
