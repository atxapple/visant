from cloud.api.database.session import get_db
from cloud.api.database.models import Capture, Device, User

db = next(get_db())

# Get user
user = db.query(User).filter(User.email == 'yunyoungmokk@gmail.com').first()
print(f"User: {user.email}")
print(f"User Org ID: {user.org_id}")

# Get device
device = db.query(Device).filter(Device.device_id == 'TEST3').first()
print(f"\nDevice TEST3:")
print(f"  Device Org ID: {device.org_id}")
print(f"  Org Match: {device.org_id == user.org_id}")

# Get captures
captures = db.query(Capture).filter(Capture.device_id == 'TEST3').all()
print(f"\nTotal captures for TEST3: {len(captures)}")
for cap in captures:
    print(f"  {cap.record_id}:")
    print(f"    device_id: {cap.device_id}")
    print(f"    state: {cap.state}")
    print(f"    Has org_id field: {hasattr(cap, 'org_id')}")
    if hasattr(cap, 'org_id'):
        print(f"    org_id: {cap.org_id}")
        print(f"    Matches user org: {cap.org_id == user.org_id}")
