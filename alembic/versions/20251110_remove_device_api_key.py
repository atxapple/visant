"""remove device api_key column

Revision ID: remove_api_key
Revises: fead5a235b2a
Create Date: 2025-11-10 01:15:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'remove_api_key'
down_revision: Union[str, None] = 'fead5a235b2a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Remove api_key column from devices table (device-ID-only authentication)
    op.drop_column('devices', 'api_key')


def downgrade() -> None:
    # Re-add api_key column if rollback is needed
    op.add_column('devices', sa.Column('api_key', sa.String(length=255), nullable=True))
    # Note: Index will need to be manually recreated if needed
