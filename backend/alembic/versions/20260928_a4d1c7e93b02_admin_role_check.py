"""allow the admin role in role CHECK constraints

Revision ID: a4d1c7e93b02
Revises: 5b1f7c9d2e84
Create Date: 2026-09-28 03:00:00

The admin role was added by editing the initial migration after databases had already been created from it, so
those databases still reject 'admin' in users.user_role and audit_logs.actor_role. Rebuilding both constraints here
fixes old databases and is a no-op in effect on new ones, whose constraints already list the four roles.
"""
from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'a4d1c7e93b02'
down_revision: str | Sequence[str] | None = '5b1f7c9d2e84'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_CHECKS = (("users", "user_role"), ("audit_logs", "actor_role"))


def _rebuild(roles: str) -> None:
    for table, column in _CHECKS:
        with op.batch_alter_table(table, schema=None) as batch_op:
            batch_op.drop_constraint(op.f(f"ck_{table}_{column}"), type_="check")
            batch_op.create_check_constraint(op.f(f"ck_{table}_{column}"), f"{column} IN ({roles})")


def upgrade() -> None:
    """Upgrade schema."""
    _rebuild("'admin', 'hr', 'reviewer', 'employee'")


def downgrade() -> None:
    """Downgrade schema. Fails while admin accounts or admin audit entries exist, which is the point of the check."""
    _rebuild("'hr', 'reviewer', 'employee'")
