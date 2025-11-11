import sqlite3

conn = sqlite3.connect('visant_dev.db')
cursor = conn.cursor()

# Get TEST3 device info
print("TEST3 Device Info:")
device = cursor.execute('SELECT device_id, org_id, friendly_name FROM devices WHERE device_id=?', ('TEST3',)).fetchone()
if device:
    device_id, org_id, friendly_name = device
    print(f"  Device ID: {device_id}")
    print(f"  Friendly Name: {friendly_name}")
    print(f"  Org ID: {org_id}")
    print()

    # Get organization info
    print("Organization:")
    org = cursor.execute('SELECT id, name FROM organizations WHERE id=?', (org_id,)).fetchone()
    if org:
        print(f"  Name: {org[1]}")
        print()

    # Get users in this organization
    print("Users in this organization:")
    users = cursor.execute('SELECT id, email, name, role FROM users WHERE org_id=?', (org_id,)).fetchall()
    for user in users:
        user_id, email, name, role = user
        print(f"  Email: {email}")
        print(f"  Name: {name or 'N/A'}")
        print(f"  Role: {role}")
        print()
else:
    print("  Device not found")

conn.close()
