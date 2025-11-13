"""add_alert_definitions_table

Revision ID: db7d78dfcf08
Revises: aa246cbd4277
Create Date: 2025-11-13 07:22:00.510755

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'db7d78dfcf08'
down_revision: Union[str, None] = 'aa246cbd4277'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create alert_definitions table
    op.create_table('alert_definitions',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('device_id', sa.String(length=255), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('created_by', sa.String(length=255), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(['device_id'], ['devices.device_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_alert_definitions_device_id'), 'alert_definitions', ['device_id'], unique=False)
    op.create_index(op.f('ix_alert_definitions_created_at'), 'alert_definitions', ['created_at'], unique=False)
    op.create_index(op.f('ix_alert_definitions_is_active'), 'alert_definitions', ['is_active'], unique=False)

    # Add alert_definition_id FK column to captures
    op.add_column('captures', sa.Column('alert_definition_id', sa.UUID(), nullable=True))
    op.create_foreign_key('fk_captures_alert_definition', 'captures', 'alert_definitions', ['alert_definition_id'], ['id'], ondelete='SET NULL')

    # Remove old normal_description_file column
    op.drop_column('captures', 'normal_description_file')


def downgrade() -> None:
    # Add back normal_description_file column
    op.add_column('captures', sa.Column('normal_description_file', sa.String(length=500), nullable=True))

    # Remove alert_definition_id FK and column
    op.drop_constraint('fk_captures_alert_definition', 'captures', type_='foreignkey')
    op.drop_column('captures', 'alert_definition_id')

    # Drop alert_definitions table
    op.drop_index(op.f('ix_alert_definitions_is_active'), table_name='alert_definitions')
    op.drop_index(op.f('ix_alert_definitions_created_at'), table_name='alert_definitions')
    op.drop_index(op.f('ix_alert_definitions_device_id'), table_name='alert_definitions')
    op.drop_table('alert_definitions')
