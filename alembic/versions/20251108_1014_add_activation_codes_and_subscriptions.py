"""add activation codes and subscriptions

Revision ID: 20251108_1014_abc123
Revises: 747d6fbf4733
Create Date: 2025-11-08 10:14:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '20251108_1014_abc123'
down_revision: Union[str, None] = '747d6fbf4733'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add subscription fields to organizations
    op.add_column('organizations', sa.Column('subscription_status', sa.String(length=50), nullable=False, server_default='free'))
    op.add_column('organizations', sa.Column('subscription_plan_id', sa.String(length=50), nullable=True))
    op.add_column('organizations', sa.Column('allowed_devices', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('organizations', sa.Column('active_devices_count', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('organizations', sa.Column('code_benefit_ends_at', sa.DateTime(), nullable=True))
    op.add_column('organizations', sa.Column('code_granted_devices', sa.Integer(), nullable=False, server_default='0'))

    # Update devices table for activation workflow
    # Use batch mode for SQLite compatibility
    with op.batch_alter_table('devices', schema=None) as batch_op:
        batch_op.alter_column('org_id', existing_type=sa.String(), nullable=True)  # Can be null until activated
        batch_op.alter_column('api_key', existing_type=sa.String(), nullable=True)  # Generated on activation
        batch_op.add_column(sa.Column('manufactured_at', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('batch_id', sa.String(length=50), nullable=True))
        batch_op.add_column(sa.Column('activated_by_user_id', postgresql.UUID(), nullable=True))
        batch_op.add_column(sa.Column('activated_at', sa.DateTime(), nullable=True))
        batch_op.alter_column('status', existing_type=sa.String(length=50), server_default='manufactured')
        batch_op.create_foreign_key('fk_devices_activated_by', 'users', ['activated_by_user_id'], ['id'])

    # Create activation_codes table
    op.create_table(
        'activation_codes',
        sa.Column('code', sa.String(length=50), nullable=False),
        sa.Column('description', sa.String(length=255), nullable=True),
        sa.Column('created_by_user_id', postgresql.UUID(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('benefit_type', sa.String(length=50), nullable=False),
        sa.Column('benefit_value', sa.Integer(), nullable=False),
        sa.Column('max_uses', sa.Integer(), nullable=True),
        sa.Column('uses_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('valid_from', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('valid_until', sa.DateTime(), nullable=True),
        sa.Column('active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('allowed_email_domains', sa.JSON(), nullable=True),
        sa.Column('min_plan_tier', sa.String(length=50), nullable=True),
        sa.Column('one_per_user', sa.Boolean(), nullable=False, server_default='true'),
        sa.PrimaryKeyConstraint('code'),
        sa.ForeignKeyConstraint(['created_by_user_id'], ['users.id'], ),
    )
    op.create_index('idx_activation_codes_active', 'activation_codes', ['active'])
    op.create_index('idx_activation_codes_active_valid', 'activation_codes', ['active', 'valid_until'])

    # Create code_redemptions table
    op.create_table(
        'code_redemptions',
        sa.Column('id', postgresql.UUID(), nullable=False),
        sa.Column('code', sa.String(length=50), nullable=False),
        sa.Column('org_id', postgresql.UUID(), nullable=False),
        sa.Column('user_id', postgresql.UUID(), nullable=False),
        sa.Column('redeemed_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('device_id', sa.String(length=255), nullable=True),
        sa.Column('benefit_applied', sa.String(length=255), nullable=True),
        sa.Column('benefit_expires_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['code'], ['activation_codes.code'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['org_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['device_id'], ['devices.device_id'], ondelete='SET NULL'),
    )
    op.create_index('idx_code_redemptions_code', 'code_redemptions', ['code'])
    op.create_index('idx_code_redemptions_org', 'code_redemptions', ['org_id'])
    op.create_index('idx_code_redemptions_user', 'code_redemptions', ['user_id'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('idx_code_redemptions_user', table_name='code_redemptions')
    op.drop_index('idx_code_redemptions_org', table_name='code_redemptions')
    op.drop_index('idx_code_redemptions_code', table_name='code_redemptions')
    op.drop_index('idx_activation_codes_active_valid', table_name='activation_codes')
    op.drop_index('idx_activation_codes_active', table_name='activation_codes')

    # Drop tables
    op.drop_table('code_redemptions')
    op.drop_table('activation_codes')

    # Remove device columns (use batch mode for SQLite)
    with op.batch_alter_table('devices', schema=None) as batch_op:
        batch_op.drop_constraint('fk_devices_activated_by', type_='foreignkey')
        batch_op.drop_column('activated_at')
        batch_op.drop_column('activated_by_user_id')
        batch_op.drop_column('batch_id')
        batch_op.drop_column('manufactured_at')
        batch_op.alter_column('api_key', existing_type=sa.String(), nullable=False)
        batch_op.alter_column('org_id', existing_type=sa.String(), nullable=False)
        batch_op.alter_column('status', existing_type=sa.String(length=50), server_default='active')

    # Remove organization columns
    op.drop_column('organizations', 'code_granted_devices')
    op.drop_column('organizations', 'code_benefit_ends_at')
    op.drop_column('organizations', 'active_devices_count')
    op.drop_column('organizations', 'allowed_devices')
    op.drop_column('organizations', 'subscription_plan_id')
    op.drop_column('organizations', 'subscription_status')
