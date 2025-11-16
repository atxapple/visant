#!/usr/bin/env python
"""Database migration script for Railway deployment."""
import sys
import logging
import os
import traceback
from alembic.config import Config
from alembic import command

# Load .env file if it exists (before any other imports)
from dotenv import load_dotenv
load_dotenv()

# Configure logging to be more verbose
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def run_migrations():
    """Run all pending database migrations."""
    try:
        logger.info("=" * 70)
        logger.info("Starting database migrations...")
        logger.info("=" * 70)

        # Check if DATABASE_URL is set
        db_url = os.getenv("DATABASE_URL")
        if db_url:
            # Hide password for logging
            safe_url = db_url.split('@')[1] if '@' in db_url else "local SQLite"
            logger.info(f"Database: {safe_url}")
        else:
            logger.warning("DATABASE_URL not set, will use default from alembic.ini")

        # Check if alembic.ini exists
        if not os.path.exists("alembic.ini"):
            logger.error("alembic.ini not found in current directory")
            logger.error(f"Current directory: {os.getcwd()}")
            logger.error(f"Directory contents: {os.listdir('.')}")
            return 1

        logger.info("Creating Alembic configuration...")
        alembic_cfg = Config("alembic.ini")

        logger.info("Running migrations to head...")
        try:
            command.upgrade(alembic_cfg, "head")
        except Exception as upgrade_error:
            logger.error(f"Error during upgrade command: {upgrade_error}")
            logger.error(f"Error type: {type(upgrade_error).__name__}")
            logger.error("Upgrade traceback:")
            logger.error(traceback.format_exc())
            raise

        logger.info("=" * 70)
        logger.info("✓ Database migrations completed successfully!")
        logger.info("=" * 70)
        return 0

    except Exception as e:
        logger.error("=" * 70)
        logger.error(f"✗ Migration failed: {e}")
        logger.error("=" * 70)
        logger.error("Full traceback:")
        logger.error(traceback.format_exc())
        return 1

if __name__ == "__main__":
    exit_code = run_migrations()
    logger.info(f"Migration script exiting with code {exit_code}")
    sys.exit(exit_code)
