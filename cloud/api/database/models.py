"""SQLAlchemy models for Visant multi-tenant architecture."""

import uuid
from datetime import datetime
from typing import Optional, List
from sqlalchemy import (
    Column, String, DateTime, ForeignKey, Integer, Float, Boolean, Text, JSON, TypeDecorator, CHAR
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship
from cloud.api.database.base import Base


# Custom GUID type that works with both PostgreSQL and SQLite
class GUID(TypeDecorator):
    """Platform-independent GUID type.

    Uses PostgreSQL's UUID type when available, otherwise uses CHAR(36) for SQLite.
    """
    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(PG_UUID())
        else:
            return dialect.type_descriptor(CHAR(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        elif dialect.name == 'postgresql':
            return str(value)
        else:
            if isinstance(value, uuid.UUID):
                return str(value)
            return str(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        if not isinstance(value, uuid.UUID):
            return uuid.UUID(value)
        return value


class Organization(Base):
    """Organization (tenant) entity."""
    __tablename__ = "organizations"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Future: billing, quotas, settings
    settings = Column(JSON, default={})

    # Subscription (Phase 7)
    subscription_status = Column(String(50), default="free")  # free, active, past_due, canceled, unpaid
    subscription_plan_id = Column(String(50), nullable=True)  # starter, home, pro
    allowed_devices = Column(Integer, default=0)
    active_devices_count = Column(Integer, default=0)

    # Activation code benefits
    code_benefit_ends_at = Column(DateTime, nullable=True)
    code_granted_devices = Column(Integer, default=0)

    # Relationships
    users = relationship("User", back_populates="organization", cascade="all, delete-orphan")
    devices = relationship("Device", back_populates="organization", cascade="all, delete-orphan")
    captures = relationship("Capture", back_populates="organization", cascade="all, delete-orphan")
    share_links = relationship("ShareLink", back_populates="organization", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Organization(id={self.id}, name={self.name})>"


class User(Base):
    """User account linked to an organization."""
    __tablename__ = "users"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    org_id = Column(GUID, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)

    # Link to Supabase Auth user
    supabase_user_id = Column(GUID, unique=True, nullable=True, index=True)

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    last_login_at = Column(DateTime, nullable=True)

    # Future: role-based access control
    role = Column(String(50), default="member")  # admin, member, viewer

    # Relationships
    organization = relationship("Organization", back_populates="users")
    share_links_created = relationship("ShareLink", back_populates="creator", foreign_keys="ShareLink.created_by")

    def __repr__(self):
        return f"<User(id={self.id}, email={self.email}, org_id={self.org_id})>"


class Device(Base):
    """Camera/device registered to an organization."""
    __tablename__ = "devices"

    device_id = Column(String(255), primary_key=True)
    org_id = Column(GUID, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True, index=True)  # Null until activated

    friendly_name = Column(String(255), nullable=True)
    api_key = Column(String(255), unique=True, nullable=True, index=True)  # Generated on activation

    # Manufacturing tracking
    manufactured_at = Column(DateTime, nullable=True)
    batch_id = Column(String(50), nullable=True)

    # Activation tracking
    activated_by_user_id = Column(GUID, ForeignKey("users.id"), nullable=True)
    activated_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    last_seen_at = Column(DateTime, nullable=True, index=True)
    last_ip = Column(String(45), nullable=True)

    status = Column(String(50), default="manufactured")  # manufactured, activated, active, suspended, inactive

    # Metadata
    device_version = Column(String(50), nullable=True)
    config = Column(JSON, default={})  # Per-device configuration

    # Relationships
    organization = relationship("Organization", back_populates="devices")
    captures = relationship("Capture", back_populates="device", cascade="all, delete-orphan")
    share_links = relationship("ShareLink", back_populates="device", cascade="all, delete-orphan")
    activated_by = relationship("User", foreign_keys=[activated_by_user_id])

    def __repr__(self):
        return f"<Device(device_id={self.device_id}, org_id={self.org_id}, friendly_name={self.friendly_name})>"


class Capture(Base):
    """Capture record with classification results."""
    __tablename__ = "captures"

    record_id = Column(String(255), primary_key=True)
    org_id = Column(GUID, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    device_id = Column(String(255), ForeignKey("devices.device_id", ondelete="CASCADE"), nullable=False, index=True)

    # Timestamps
    captured_at = Column(DateTime, nullable=False, index=True)
    ingested_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)

    # Storage (S3 paths)
    s3_image_key = Column(String(500), nullable=True)
    s3_thumbnail_key = Column(String(500), nullable=True)
    image_stored = Column(Boolean, default=False)
    thumbnail_stored = Column(Boolean, default=False)

    # Classification (Cloud AI evaluation)
    state = Column(String(50), nullable=True, index=True)  # normal, abnormal, uncertain (null until evaluated)
    score = Column(Float, nullable=True)
    reason = Column(Text, nullable=True)
    agent_details = Column(JSON, nullable=True)

    # Evaluation tracking
    evaluation_status = Column(String(50), nullable=False, default="pending", index=True)  # pending, processing, completed, failed
    evaluated_at = Column(DateTime, nullable=True)

    # Metadata
    trigger_label = Column(String(100), nullable=True)
    normal_description_file = Column(String(500), nullable=True)
    capture_metadata = Column(JSON, default={})

    # Relationships
    organization = relationship("Organization", back_populates="captures")
    device = relationship("Device", back_populates="captures")

    def __repr__(self):
        return f"<Capture(record_id={self.record_id}, device_id={self.device_id}, state={self.state})>"


class ShareLink(Base):
    """Public share link for device or captures."""
    __tablename__ = "share_links"

    token = Column(String(32), primary_key=True)
    org_id = Column(GUID, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    device_id = Column(String(255), ForeignKey("devices.device_id", ondelete="CASCADE"), nullable=False, index=True)

    # Sharing scope
    share_type = Column(String(50), default="device")  # device, capture, date_range
    capture_id = Column(String(255), nullable=True)  # If sharing single capture
    start_date = Column(DateTime, nullable=True)     # If sharing date range
    end_date = Column(DateTime, nullable=True)

    # Access control
    created_by = Column(GUID, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    expires_at = Column(DateTime, nullable=False, index=True)

    # Security (optional for MVP)
    password_hash = Column(String(255), nullable=True)
    max_views = Column(Integer, nullable=True)

    # Analytics
    view_count = Column(Integer, default=0)
    last_viewed_at = Column(DateTime, nullable=True)

    # Relationships
    organization = relationship("Organization", back_populates="share_links")
    device = relationship("Device", back_populates="share_links")
    creator = relationship("User", back_populates="share_links_created", foreign_keys=[created_by])

    def __repr__(self):
        return f"<ShareLink(token={self.token}, device_id={self.device_id}, expires_at={self.expires_at})>"


class ActivationCode(Base):
    """Activation code for promotions, trials, and development."""
    __tablename__ = "activation_codes"

    # Code identifier
    code = Column(String(50), primary_key=True)

    # Code metadata
    description = Column(String(255), nullable=True)
    created_by_user_id = Column(GUID, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Code benefits
    benefit_type = Column(String(50), nullable=False)  # free_months, device_slots, discount_percent, trial_extension
    benefit_value = Column(Integer, nullable=False)

    # Usage constraints
    max_uses = Column(Integer, nullable=True)  # null = unlimited
    uses_count = Column(Integer, default=0)

    valid_from = Column(DateTime, default=datetime.utcnow)
    valid_until = Column(DateTime, nullable=True)  # null = no expiration

    # Status
    active = Column(Boolean, default=True, index=True)

    # Restrictions (optional)
    allowed_email_domains = Column(JSON, nullable=True)  # ["@university.edu"]
    min_plan_tier = Column(String(50), nullable=True)  # "starter", "home", "pro"
    one_per_user = Column(Boolean, default=True)

    # Relationships
    creator = relationship("User", foreign_keys=[created_by_user_id])
    redemptions = relationship("CodeRedemption", back_populates="activation_code", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<ActivationCode(code={self.code}, benefit_type={self.benefit_type}, uses={self.uses_count}/{self.max_uses})>"


class CodeRedemption(Base):
    """Record of activation code usage."""
    __tablename__ = "code_redemptions"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)

    # Who used it
    code = Column(String(50), ForeignKey("activation_codes.code", ondelete="CASCADE"), nullable=False, index=True)
    org_id = Column(GUID, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(GUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # When and what device
    redeemed_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    device_id = Column(String(255), ForeignKey("devices.device_id", ondelete="SET NULL"), nullable=True)

    # Benefits applied
    benefit_applied = Column(String(255), nullable=True)
    benefit_expires_at = Column(DateTime, nullable=True)

    # Relationships
    activation_code = relationship("ActivationCode", back_populates="redemptions")
    organization = relationship("Organization")
    user = relationship("User")
    device = relationship("Device")

    def __repr__(self):
        return f"<CodeRedemption(code={self.code}, org_id={self.org_id}, redeemed_at={self.redeemed_at})>"


# Create indexes for common query patterns
# These will be created automatically by SQLAlchemy when tables are created
# Additional composite indexes for performance:
from sqlalchemy import Index

# Captures: org + state + date (for filtering dashboard)
Index('idx_captures_org_state_date', Capture.org_id, Capture.state, Capture.captured_at.desc())

# Captures: device + date (for device-specific views)
Index('idx_captures_device_date', Capture.device_id, Capture.captured_at.desc())

# Devices: org + last_seen (for device status dashboard)
Index('idx_devices_org_last_seen', Device.org_id, Device.last_seen_at.desc())

# Share links: expires_at (for cleanup job)
Index('idx_share_links_expires', ShareLink.expires_at)

# Activation codes: active + valid_until (for validation queries)
Index('idx_activation_codes_active_valid', ActivationCode.active, ActivationCode.valid_until)

# Code redemptions: org (for user code history)
Index('idx_code_redemptions_org', CodeRedemption.org_id, CodeRedemption.redeemed_at.desc())

# Code redemptions: code (for usage tracking)
Index('idx_code_redemptions_code', CodeRedemption.code, CodeRedemption.redeemed_at.desc())
