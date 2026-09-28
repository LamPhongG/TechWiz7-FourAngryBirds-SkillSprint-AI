"""mark accounts that still use a generated password

Revision ID: b91f3d6c2a47
Revises: a4d1c7e93b02
Create Date: 2026-09-28 10:00:00

Accounts created by an Admin from a CV receive a generated password by email. The flag lets the employee dashboard
suggest changing it; existing accounts chose their own password, so they start as False.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'b91f3d6c2a47'
down_revision: str | Sequence[str] | None = 'a4d1c7e93b02'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.add_column(sa.Column('password_is_temporary', sa.Boolean(), server_default=sa.false(), nullable=False))


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_column('password_is_temporary')
