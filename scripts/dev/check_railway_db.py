#!/usr/bin/env python3
"""Check captures in Railway PostgreSQL database."""

import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment first
load_dotenv()

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from cloud.api.database import get_db, Capture
from sqlalchemy import desc

def main():
    print(f"DATABASE_URL: {os.getenv('DATABASE_URL', 'Not set')[:50]}...")

    db = next(get_db())
    try:
        # Count total captures
        total = db.query(Capture).count()
        print(f"\nTotal captures in database: {total}")

        if total == 0:
            print("\nNo captures found in Railway database!")
            print("This explains why images aren't showing - there's no data.")
            return

        # Get recent captures
        captures = db.query(Capture).order_by(desc(Capture.captured_at)).limit(5).all()

        print(f"\nRecent {len(captures)} captures:\n")

        for cap in captures:
            print(f"Record ID: {cap.record_id}")
            print(f"  Device ID: {cap.device_id}")
            print(f"  Captured at: {cap.captured_at}")
            print(f"  State: {cap.state}")
            print(f"  Evaluation status: {cap.evaluation_status}")
            print(f"  Image stored: {cap.image_stored}")
            print(f"  S3 image key: {cap.s3_image_key}")

            # Check if files exist locally
            if cap.s3_image_key:
                image_path = Path("uploads") / cap.s3_image_key
                print(f"  Local file exists: {image_path.exists()}")

            print()

    finally:
        db.close()

if __name__ == "__main__":
    main()
