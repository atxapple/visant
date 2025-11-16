#!/usr/bin/env python3
"""Check AI evaluation status in Railway database."""
import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.environ.get("DATABASE_URL")
engine = create_engine(DATABASE_URL)

with engine.connect() as conn:
    # Check recent captures with correct column names
    result = conn.execute(text("""
        SELECT record_id, device_id, state, score, reason,
               agent_details, evaluation_status, evaluated_at, captured_at
        FROM captures
        ORDER BY captured_at DESC
        LIMIT 5
    """))

    rows = result.fetchall()

    print("=" * 80)
    print("Recent Captures in Railway Database (AI Evaluation Status)")
    print("=" * 80)

    if not rows:
        print("No captures found")
    else:
        for row in rows:
            print(f"\nRecord ID: {row[0]}")
            print(f"Device ID: {row[1]}")
            print(f"State: {row[2]}")
            print(f"Score: {row[3]}")
            reason_preview = row[4][:150] if row[4] else 'None'
            print(f"Reason: {reason_preview}...")
            print(f"Agent Details: {str(row[5])[:100] if row[5] else 'None'}...")
            print(f"Evaluation Status: {row[6]}")
            print(f"Evaluated At: {row[7]}")
            print(f"Captured At: {row[8]}")
            print("-" * 80)
