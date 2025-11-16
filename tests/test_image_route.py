#!/usr/bin/env python3
"""Test if image serving route works."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from cloud.api.database import get_db, Capture
from sqlalchemy import desc

def main():
    db = next(get_db())
    try:
        # Get a recent capture
        cap = db.query(Capture).order_by(desc(Capture.captured_at)).first()

        if not cap:
            print("No captures found in database")
            return

        print(f"Testing with capture: {cap.record_id}")
        print(f"Image stored: {cap.image_stored}")
        print(f"S3 image key: {cap.s3_image_key}")

        # Test path construction
        uploads_dir = Path("uploads")
        image_path = uploads_dir / cap.s3_image_key

        print(f"\nConstructed path: {image_path}")
        print(f"Path exists: {image_path.exists()}")
        print(f"Path is file: {image_path.is_file()}")

        if image_path.exists():
            print(f"File size: {image_path.stat().st_size} bytes")

        # Show what the URL would be
        print(f"\nImage URL: /ui/captures/{cap.record_id}/image")
        print(f"Thumbnail URL: /ui/captures/{cap.record_id}/thumbnail")

        # Check what the API would return
        if cap.image_stored:
            api_image_url = f"/ui/captures/{cap.record_id}/image"
            api_thumbnail_url = f"/ui/captures/{cap.record_id}/thumbnail"
            print(f"\nAPI would return:")
            print(f"  image_url: {api_image_url}")
            print(f"  thumbnail_url: {api_thumbnail_url}")
        else:
            print(f"\nAPI would return:")
            print(f"  image_url: None")
            print(f"  thumbnail_url: None")

    finally:
        db.close()

if __name__ == "__main__":
    main()
