"""employee profile role matrix personal plans

Revision ID: 7264ebe1a10e
Revises: 56977cdd23d0
Create Date: 2026-09-25 12:57:01.179984

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '7264ebe1a10e'
down_revision: str | Sequence[str] | None = '56977cdd23d0'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('role_requirements',
    sa.Column('id', sa.String(length=16), nullable=False),
    sa.Column('job_position_id', sa.String(length=64), nullable=False),
    sa.Column('policy_requirement', sa.Text(), nullable=True),
    sa.Column('process_requirement', sa.Text(), nullable=True),
    sa.Column('competency', sa.String(length=255), nullable=True),
    sa.Column('mandatory', sa.Boolean(), nullable=False),
    sa.Column('priority', sa.Enum('High', 'Medium', 'Low', name='priority', native_enum=False, length=32), nullable=False),
    sa.Column('source_doc_code', sa.String(length=32), nullable=True),
    sa.Column('source_section', sa.String(length=32), nullable=True),
    sa.Column('source_version', sa.String(length=16), nullable=True),
    sa.Column('role_specific', sa.Boolean(), nullable=False),
    sa.Column('assessment_requirement', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.CheckConstraint("priority IN ('High', 'Medium', 'Low')", name=op.f('ck_role_requirements_priority')),
    sa.ForeignKeyConstraint(['job_position_id'], ['job_positions.id'], name=op.f('fk_role_requirements_job_position_id_job_positions'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_role_requirements'))
    )
    with op.batch_alter_table('role_requirements', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_role_requirements_job_position_id'), ['job_position_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_role_requirements_source_doc_code'), ['source_doc_code'], unique=False)

    with op.batch_alter_table('learning_paths', schema=None) as batch_op:
        batch_op.add_column(sa.Column('employee_id', sa.String(length=32), nullable=True))
        batch_op.create_index(batch_op.f('ix_learning_paths_employee_id'), ['employee_id'], unique=False)
        batch_op.create_foreign_key(batch_op.f('fk_learning_paths_employee_id_users'), 'users', ['employee_id'], ['id'], ondelete='SET NULL')

    with op.batch_alter_table('path_assignments', schema=None) as batch_op:
        batch_op.add_column(sa.Column('user_id', sa.String(length=32), nullable=True))
        batch_op.create_index(batch_op.f('ix_path_assignments_user_id'), ['user_id'], unique=False)
        batch_op.create_foreign_key(batch_op.f('fk_path_assignments_user_id_users'), 'users', ['user_id'], ['id'], ondelete='CASCADE')
        batch_op.drop_constraint(op.f('ck_path_assignments_has_target'), type_='check')
        batch_op.create_check_constraint(op.f('ck_path_assignments_has_target'), "department_code IS NOT NULL OR job_position_id IS NOT NULL OR user_id IS NOT NULL")

    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.add_column(sa.Column('employee_code', sa.String(length=32), nullable=True))
        batch_op.add_column(sa.Column('experience_level', sa.Enum('Beginner', 'Intermediate', 'Advanced', name='experience_level', native_enum=False, length=32), nullable=True))
        batch_op.add_column(sa.Column('location', sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column('joining_date', sa.Date(), nullable=True))
        batch_op.add_column(sa.Column('manager_id', sa.String(length=32), nullable=True))
        batch_op.add_column(sa.Column('competencies', sa.JSON(), nullable=False, server_default='[]'))
        batch_op.add_column(sa.Column('previous_experience', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('training_status', sa.Enum('not_started', 'in_progress', 'completed', name='training_status', native_enum=False, length=32), nullable=True))
        batch_op.create_check_constraint(op.f('ck_users_experience_level'), "experience_level IN ('Beginner', 'Intermediate', 'Advanced')")
        batch_op.create_check_constraint(op.f('ck_users_training_status'), "training_status IN ('not_started', 'in_progress', 'completed')")
        batch_op.create_unique_constraint(batch_op.f('uq_users_employee_code'), ['employee_code'])
        batch_op.create_foreign_key(batch_op.f('fk_users_manager_id_users'), 'users', ['manager_id'], ['id'], ondelete='SET NULL')


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_constraint(batch_op.f('fk_users_manager_id_users'), type_='foreignkey')
        batch_op.drop_constraint(batch_op.f('uq_users_employee_code'), type_='unique')
        batch_op.drop_constraint(op.f('ck_users_training_status'), type_='check')
        batch_op.drop_constraint(op.f('ck_users_experience_level'), type_='check')
        batch_op.drop_column('training_status')
        batch_op.drop_column('previous_experience')
        batch_op.drop_column('competencies')
        batch_op.drop_column('manager_id')
        batch_op.drop_column('joining_date')
        batch_op.drop_column('location')
        batch_op.drop_column('experience_level')
        batch_op.drop_column('employee_code')

    with op.batch_alter_table('path_assignments', schema=None) as batch_op:
        batch_op.drop_constraint(op.f('ck_path_assignments_has_target'), type_='check')
        batch_op.create_check_constraint(op.f('ck_path_assignments_has_target'), "department_code IS NOT NULL OR job_position_id IS NOT NULL")
        batch_op.drop_constraint(batch_op.f('fk_path_assignments_user_id_users'), type_='foreignkey')
        batch_op.drop_index(batch_op.f('ix_path_assignments_user_id'))
        batch_op.drop_column('user_id')

    with op.batch_alter_table('learning_paths', schema=None) as batch_op:
        batch_op.drop_constraint(batch_op.f('fk_learning_paths_employee_id_users'), type_='foreignkey')
        batch_op.drop_index(batch_op.f('ix_learning_paths_employee_id'))
        batch_op.drop_column('employee_id')

    with op.batch_alter_table('role_requirements', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_role_requirements_source_doc_code'))
        batch_op.drop_index(batch_op.f('ix_role_requirements_job_position_id'))

    op.drop_table('role_requirements')
