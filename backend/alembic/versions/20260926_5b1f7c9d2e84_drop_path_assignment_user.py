"""drop path_assignments.user_id

Revision ID: 5b1f7c9d2e84
Revises: c3d9e2f41a07
Create Date: 2026-09-26 17:30:00

Giving a path to one employee is an enrollment now (documentation/DESIGN_PATH_ASSIGNMENT.md §4.2);
the per-user publish target was never written.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '5b1f7c9d2e84'
down_revision: str | Sequence[str] | None = 'c3d9e2f41a07'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table('path_assignments', schema=None) as batch_op:
        batch_op.drop_constraint(op.f('ck_path_assignments_has_target'), type_='check')
        batch_op.create_check_constraint(op.f('ck_path_assignments_has_target'),
                                         "department_code IS NOT NULL OR job_position_id IS NOT NULL")
        batch_op.drop_constraint(batch_op.f('fk_path_assignments_user_id_users'), type_='foreignkey')
        batch_op.drop_index(batch_op.f('ix_path_assignments_user_id'))
        batch_op.drop_column('user_id')


def downgrade() -> None:
    with op.batch_alter_table('path_assignments', schema=None) as batch_op:
        batch_op.add_column(sa.Column('user_id', sa.String(length=32), nullable=True))
        batch_op.create_index(batch_op.f('ix_path_assignments_user_id'), ['user_id'], unique=False)
        batch_op.create_foreign_key(batch_op.f('fk_path_assignments_user_id_users'), 'users', ['user_id'], ['id'],
                                    ondelete='CASCADE')
        batch_op.drop_constraint(op.f('ck_path_assignments_has_target'), type_='check')
        batch_op.create_check_constraint(op.f('ck_path_assignments_has_target'),
                                         "department_code IS NOT NULL OR job_position_id IS NOT NULL OR user_id IS NOT NULL")
