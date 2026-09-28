"""enrollment self source

Revision ID: c3d9e2f41a07
Revises: e96ea1766a73
Create Date: 2026-09-26 16:10:00

Employees can enroll themselves in a path of their department ("Explore paths"): assignment source `self`.
"""
from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'c3d9e2f41a07'
down_revision: str | Sequence[str] | None = 'e96ea1766a73'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _source_check(values: tuple[str, ...]) -> None:
    with op.batch_alter_table('enrollments', schema=None) as batch_op:
        batch_op.drop_constraint(op.f('ck_enrollments_assignment_source'), type_='check')
        batch_op.create_check_constraint(op.f('ck_enrollments_assignment_source'),
                                         f"source IN ({', '.join(repr(v) for v in values)})")


def upgrade() -> None:
    _source_check(('auto_department', 'auto_position', 'manual', 'self'))


def downgrade() -> None:
    op.execute("DELETE FROM enrollments WHERE source = 'self'")
    _source_check(('auto_department', 'auto_position', 'manual'))
