"""Database session management and connection pooling."""

import os
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import NullPool

# Get database URL from environment variable
DATABASE_URL = os.getenv("DATABASE_URL")

# Default to SQLite for local development if no DATABASE_URL
if not DATABASE_URL:
    DATABASE_URL = "sqlite:///./visant_dev.db"
    print(f"WARNING: No DATABASE_URL found, using SQLite: {DATABASE_URL}")

# PostgreSQL URLs from Railway sometimes use postgres:// instead of postgresql://
# SQLAlchemy requires postgresql://
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Create engine with connection pooling
# For production PostgreSQL, use connection pooling
# For SQLite, use NullPool (SQLite doesn't support multiple connections well)
if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},  # SQLite specific
        poolclass=NullPool,
    )
else:
    engine = create_engine(
        DATABASE_URL,
        pool_size=20,          # Max connections in pool
        max_overflow=10,       # Max connections beyond pool_size
        pool_pre_ping=True,    # Verify connections before using
        pool_recycle=3600,     # Recycle connections after 1 hour
    )

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """
    Dependency for FastAPI endpoints to get database session.

    Usage:
        @app.get("/endpoint")
        def endpoint(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize database (create tables if they don't exist)."""
    from cloud.api.database.base import Base
    Base.metadata.create_all(bind=engine)
    print("SUCCESS: Database tables created")
