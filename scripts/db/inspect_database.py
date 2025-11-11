import sqlite3

conn = sqlite3.connect('visant_dev.db')
cursor = conn.cursor()

print("All devices:")
for row in cursor.execute('SELECT device_id, org_id, friendly_name FROM devices').fetchall():
    print(f'  {row}')

print("\nCaptures by device:")
for row in cursor.execute('SELECT device_id, COUNT(*) FROM captures GROUP BY device_id').fetchall():
    print(f'  {row}')

print("\nRecent captures:")
for row in cursor.execute('SELECT record_id, device_id, captured_at, image_stored, thumbnail_stored FROM captures ORDER BY captured_at DESC LIMIT 5').fetchall():
    print(f'  {row}')

conn.close()
