"""add name to users

Revision ID: fead5a235b2a
Revises: 20251109_trigger
Create Date: 2025-11-09 17:03:50.720474

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fead5a235b2a'
down_revision: Union[str, None] = '20251109_trigger'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add name column to users table
    op.add_column('users', sa.Column('name', sa.String(length=255), nullable=True))


def downgrade() -> None:
    # Remove name column from users table
    op.drop_column('users', 'name')
