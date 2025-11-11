"""Test thumbnail endpoint with Railway database."""
from dotenv import load_dotenv
load_dotenv()

from cloud.api.database import get_db, Capture
import requests

# Query database for a capture with image
db = next(get_db())
captures = db.query(Capture).filter(
    Capture.s3_image_key.isnot(None),
    Capture.image_stored == True
).limit(10).all()

print(f"\nFound {len(captures)} captures with images in Railway database\n")

for c in captures:
    print(f"Testing: {c.record_id}")
    print(f"  image_path: {c.s3_image_key}")
    print(f"  thumbnail_stored: {c.thumbnail_stored}")

    # Test thumbnail endpoint
    url = f"http://localhost:8000/ui/captures/{c.record_id}/thumbnail"
    response = requests.get(url)

    print(f"  Thumbnail endpoint: {response.status_code}")
    if response.status_code == 200:
        print(f"  Content-Type: {response.headers.get('Content-Type')}")
        print(f"  Content-Length: {len(response.content)} bytes")
        print(f"  Cache-Control: {response.headers.get('Cache-Control')}")
        print(f"  ✓ SUCCESS - Thumbnail generated!\n")
        break
    else:
        print(f"  Error: {response.text[:100]}\n")

db.close()
