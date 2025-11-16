#!/usr/bin/env python3
"""Check device config in Railway database."""
import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import json

load_dotenv()

DATABASE_URL = os.environ.get("DATABASE_URL")
engine = create_engine(DATABASE_URL)

with engine.connect() as conn:
    result = conn.execute(text("""
        SELECT device_id, friendly_name, config, status
        FROM devices
        LIMIT 5
    """))

    rows = result.fetchall()

    print("=" * 80)
    print("Device Configurations")
    print("=" * 80)

    for row in rows:
        print(f"\nDevice ID: {row[0]}")
        print(f"Friendly Name: {row[1]}")
        print(f"Status: {row[3]}")
        print(f"Config: {json.dumps(row[2], indent=2) if row[2] else 'None'}")
        print("-" * 80)
