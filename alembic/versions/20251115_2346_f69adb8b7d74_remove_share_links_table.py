"""remove_share_links_table

Revision ID: f69adb8b7d74
Revises: db7d78dfcf08
Create Date: 2025-11-15 23:46:37.430729

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f69adb8b7d74'
down_revision: Union[str, None] = 'db7d78dfcf08'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop share_links table (sharing feature removed from application)
    op.drop_table('share_links')


def downgrade() -> None:
    # No downgrade path - table structure available in initial schema migration
    # if recreation is needed
    pass
