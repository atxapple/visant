"""Debug script to check routes registration."""

from dotenv import load_dotenv
load_dotenv()

# Import the devices router
from cloud.api.routes.devices import router as devices_router

print("=" * 60)
print("DEVICES ROUTER ROUTES")
print("=" * 60)

for route in devices_router.routes:
    print(f"Path: {route.path}")
    print(f"  Methods: {route.methods}")
    print(f"  Name: {route.name}")
    print()

print("=" * 60)
print(f"Total routes: {len(devices_router.routes)}")
print("=" * 60)

# Check specifically for validate and activate
validate_routes = [r for r in devices_router.routes if 'validate' in r.path]
activate_routes = [r for r in devices_router.routes if 'activate' in r.path]

print(f"\nValidate routes: {len(validate_routes)}")
print(f"Activate routes: {len(activate_routes)}")

if validate_routes:
    print(f"\n✓ VALIDATE route found: {validate_routes[0].path}")
else:
    print("\n✗ VALIDATE route NOT found!")

if activate_routes:
    print(f"✓ ACTIVATE route found: {activate_routes[0].path}")
else:
    print("✗ ACTIVATE route NOT found!")
