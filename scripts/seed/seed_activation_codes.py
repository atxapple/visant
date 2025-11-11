"""Seed development activation codes for testing and development.

Usage:
    python -m scripts.seed_activation_codes
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta, timezone

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from cloud.api.database.session import get_db
from cloud.api.database.models import ActivationCode


DEVELOPMENT_CODES = [
    {
        "code": "DEV2025",
        "description": "Development testing - 99 device slots, unlimited uses",
        "benefit_type": "device_slots",
        "benefit_value": 99,
        "max_uses": None,  # Unlimited
        "valid_until": None,  # Never expires
        "active": True,
        "one_per_user": False,
    },
    {
        "code": "QA100",
        "description": "QA team testing - 12 months free subscription",
        "benefit_type": "free_months",
        "benefit_value": 12,
        "max_uses": 10,
        "valid_until": datetime.now(timezone.utc) + timedelta(days=365),
        "active": True,
        "one_per_user": True,
    },
    {
        "code": "BETA30",
        "description": "Beta tester reward - 30 day trial extension",
        "benefit_type": "trial_extension",
        "benefit_value": 30,
        "max_uses": 100,
        "valid_until": datetime.now(timezone.utc) + timedelta(days=180),
        "active": True,
        "one_per_user": True,
    },
]


def seed_codes():
    """Seed activation codes into database."""
    db = next(get_db())

    try:
        print("Seeding development activation codes...")

        for code_data in DEVELOPMENT_CODES:
            # Check if code already exists
            existing = db.query(ActivationCode).filter(
                ActivationCode.code == code_data["code"]
            ).first()

            if existing:
                print(f"  [SKIP] {code_data['code']} (already exists)")
                continue

            # Create new activation code
            activation_code = ActivationCode(**code_data)
            db.add(activation_code)

            print(f"  [OK] Created {code_data['code']}")
            print(f"       Description: {code_data['description']}")
            print(f"       Benefit: {code_data['benefit_type']} = {code_data['benefit_value']}")
            print(f"       Max uses: {code_data['max_uses'] or 'Unlimited'}")
            print()

        db.commit()
        print("[SUCCESS] Activation codes seeded successfully!")

        # Show summary
        print("\nSummary of Development Codes:")
        print("-" * 60)
        codes = db.query(ActivationCode).all()
        for code in codes:
            print(f"Code: {code.code}")
            print(f"  Benefit: {code.benefit_type} ({code.benefit_value})")
            print(f"  Uses: {code.uses_count}/{code.max_uses or 'unlimited'}")
            print(f"  Status: {'Active' if code.active else 'Inactive'}")
            print()

    except Exception as e:
        print(f"[ERROR] Error seeding codes: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_codes()
