"""path duration

Revision ID: 6feb9c58ab1d
Revises: 7264ebe1a10e
Create Date: 2026-09-26 01:01:58.138763

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '6feb9c58ab1d'
down_revision: str | Sequence[str] | None = '7264ebe1a10e'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table('learning_paths', schema=None) as batch_op:
        batch_op.add_column(sa.Column('duration_days', sa.Integer(), nullable=True))



def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('learning_paths', schema=None) as batch_op:
        batch_op.drop_column('duration_days')

