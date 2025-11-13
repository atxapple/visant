#!/usr/bin/env python
"""Database migration script for Railway deployment."""
import sys
import logging
from alembic.config import Config
from alembic import command

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_migrations():
    """Run all pending database migrations."""
    try:
        logger.info("Starting database migrations...")

        # Create Alembic configuration
        alembic_cfg = Config("alembic.ini")

        # Run migrations to head
        command.upgrade(alembic_cfg, "head")

        logger.info("Database migrations completed successfully!")
        return 0

    except Exception as e:
        logger.error(f"Migration failed: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(run_migrations())
