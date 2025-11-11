"""add_composite_index_for_capture_queries

Revision ID: aa246cbd4277
Revises: remove_api_key
Create Date: 2025-11-10 21:29:07.594576

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'aa246cbd4277'
down_revision: Union[str, None] = 'remove_api_key'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create composite index for common query pattern: WHERE org_id AND device_id ORDER BY captured_at
    op.create_index(
        'idx_captures_org_device_captured',
        'captures',
        ['org_id', 'device_id', 'captured_at'],
        unique=False
    )


def downgrade() -> None:
    # Drop composite index
    op.drop_index('idx_captures_org_device_captured', table_name='captures')
