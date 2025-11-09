"""add scheduled triggers table

Revision ID: 20251109_trigger
Revises: 20251108_1014_abc123
Create Date: 2025-11-09

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '20251109_trigger'
down_revision: Union[str, None] = '20251108_1014_abc123'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create scheduled_triggers table
    op.create_table(
        'scheduled_triggers',
        sa.Column('trigger_id', sa.String(length=255), nullable=False),
        sa.Column('device_id', sa.String(length=255), nullable=False),
        sa.Column('trigger_type', sa.String(length=50), nullable=False),
        sa.Column('scheduled_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('sent_at', sa.DateTime(), nullable=True),
        sa.Column('executed_at', sa.DateTime(), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='pending'),
        sa.Column('capture_id', sa.String(length=255), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('retry_count', sa.Integer(), nullable=False, server_default='0'),
        sa.PrimaryKeyConstraint('trigger_id'),
        sa.ForeignKeyConstraint(['device_id'], ['devices.device_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['capture_id'], ['captures.record_id'], ondelete='SET NULL')
    )

    # Create indexes for common query patterns
    op.create_index('idx_triggers_device', 'scheduled_triggers', ['device_id', 'scheduled_at'], unique=False)
    op.create_index('idx_triggers_status', 'scheduled_triggers', ['status', 'sent_at'], unique=False)
    op.create_index('idx_triggers_type', 'scheduled_triggers', ['trigger_type'], unique=False)


def downgrade() -> None:
    # Drop indexes first
    op.drop_index('idx_triggers_type', table_name='scheduled_triggers')
    op.drop_index('idx_triggers_status', table_name='scheduled_triggers')
    op.drop_index('idx_triggers_device', table_name='scheduled_triggers')

    # Drop table
    op.drop_table('scheduled_triggers')
