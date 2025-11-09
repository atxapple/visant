#!/usr/bin/env python3
"""Verify database schema after migration."""

from dotenv import load_dotenv
load_dotenv()

from cloud.api.database import SessionLocal
from sqlalchemy import inspect

db = SessionLocal()
inspector = inspect(db.bind)

# Get all tables
tables = inspector.get_table_names()
print("All tables:")
for table in sorted(tables):
    print(f"  - {table}")

# Check scheduled_triggers table
print("\nScheduled Triggers table columns:")
cols = inspector.get_columns('scheduled_triggers')
for col in cols:
    nullable = "NULL" if col['nullable'] else "NOT NULL"
    print(f"  {col['name']:20} {str(col['type']):30} {nullable}")

# Check indexes
print("\nScheduled Triggers indexes:")
indexes = inspector.get_indexes('scheduled_triggers')
for idx in indexes:
    cols_str = ", ".join(idx['column_names'])
    unique = "UNIQUE" if idx.get('unique') else ""
    print(f"  {idx['name']:40} ({cols_str}) {unique}")

# Check foreign keys
print("\nScheduled Triggers foreign keys:")
fks = inspector.get_foreign_keys('scheduled_triggers')
for fk in fks:
    print(f"  {fk['name']:40} {fk['constrained_columns']} -> {fk['referred_table']}.{fk['referred_columns']}")

db.close()
print("\n✓ Schema verification complete!")
