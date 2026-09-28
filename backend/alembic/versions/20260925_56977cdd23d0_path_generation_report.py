"""path generation report

Revision ID: 56977cdd23d0
Revises: 09503405de6e
Create Date: 2026-09-25 10:58:51.220923

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '56977cdd23d0'
down_revision: str | Sequence[str] | None = '09503405de6e'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table('learning_paths', schema=None) as batch_op:
        batch_op.add_column(sa.Column('generation', sa.JSON(), nullable=True))

def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('learning_paths', schema=None) as batch_op:
        batch_op.drop_column('generation')
