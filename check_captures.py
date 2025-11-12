#!/usr/bin/env python3
"""Quick script to check capture data in database."""

from pathlib import Path
import sys

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from cloud.api.database import get_db, Capture
from sqlalchemy import desc

def main():
    db = next(get_db())
    try:
        # Get recent captures
        captures = db.query(Capture).order_by(desc(Capture.captured_at)).limit(5).all()

        print(f"\nFound {len(captures)} recent captures:\n")

        for cap in captures:
            print(f"Record ID: {cap.record_id}")
            print(f"  Device ID: {cap.device_id}")
            print(f"  Captured at: {cap.captured_at}")
            print(f"  State: {cap.state}")
            print(f"  Evaluation status: {cap.evaluation_status}")
            print(f"  Image stored: {cap.image_stored}")
            print(f"  S3 image key: {cap.s3_image_key}")
            print(f"  S3 thumbnail key: {cap.s3_thumbnail_key}")

            # Check if files exist
            if cap.s3_image_key:
                image_path = Path("uploads") / cap.s3_image_key
                print(f"  Image file exists: {image_path.exists()}")
                if image_path.exists():
                    print(f"  Image file size: {image_path.stat().st_size} bytes")

            if cap.s3_thumbnail_key:
                thumb_path = Path("uploads") / cap.s3_thumbnail_key
                print(f"  Thumbnail exists: {thumb_path.exists()}")
                if thumb_path.exists():
                    print(f"  Thumbnail size: {thumb_path.stat().st_size} bytes")

            print()

    finally:
        db.close()

if __name__ == "__main__":
    main()
