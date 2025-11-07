"""add_evaluation_status_to_captures

Revision ID: 747d6fbf4733
Revises: 8af79cab0d8d
Create Date: 2025-11-07 00:20:05.313805

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '747d6fbf4733'
down_revision: Union[str, None] = '8af79cab0d8d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add evaluation_status column
    op.add_column('captures', sa.Column('evaluation_status', sa.String(50), nullable=True))

    # Add evaluated_at timestamp
    op.add_column('captures', sa.Column('evaluated_at', sa.DateTime(), nullable=True))

    # Make state column nullable (for pending captures)
    # Note: This varies by database. For SQLite, we need to recreate the table.
    # For PostgreSQL, we can just ALTER COLUMN.
    # Using batch mode for SQLite compatibility
    with op.batch_alter_table('captures') as batch_op:
        batch_op.alter_column('state',
                              existing_type=sa.String(50),
                              nullable=True)

    # Backfill existing records: mark them as completed
    op.execute("""
        UPDATE captures
        SET evaluation_status = 'completed',
            evaluated_at = ingested_at
        WHERE evaluation_status IS NULL
    """)

    # Now make evaluation_status NOT NULL with default
    with op.batch_alter_table('captures') as batch_op:
        batch_op.alter_column('evaluation_status',
                              existing_type=sa.String(50),
                              nullable=False,
                              server_default='pending')


def downgrade() -> None:
    # Remove added columns
    op.drop_column('captures', 'evaluated_at')
    op.drop_column('captures', 'evaluation_status')

    # Revert state column to NOT NULL
    with op.batch_alter_table('captures') as batch_op:
        batch_op.alter_column('state',
                              existing_type=sa.String(50),
                              nullable=False)
