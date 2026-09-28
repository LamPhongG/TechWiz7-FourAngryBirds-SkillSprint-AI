"""enrollment assignment

Revision ID: e96ea1766a73
Revises: b7b8556af522
Create Date: 2026-09-26 14:45:14.953040

Enrollments become the record of a path given to an employee (documentation/DESIGN_PATH_ASSIGNMENT.md §4.2).
Employees already covered by a published path's targets get their record here, so nobody loses a path
they could see before; onboarding paths skip employees whose onboarding is completed (decision Q1).
"""
from collections.abc import Sequence
from datetime import UTC, date, datetime, timedelta

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'e96ea1766a73'
down_revision: str | Sequence[str] | None = 'b7b8556af522'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

STATUS = sa.Enum('assigned', 'in_progress', 'completed', 'withdrawn', name='enrollment_status', native_enum=False,
                 create_constraint=True, length=32)
SOURCE = sa.Enum('auto_department', 'auto_position', 'manual', name='assignment_source', native_enum=False,
                 create_constraint=True, length=32)


def upgrade() -> None:
    # Server defaults fill the rows that already exist; they are dropped again below because the ORM sets the values.
    with op.batch_alter_table('enrollments', schema=None) as batch_op:
        batch_op.add_column(sa.Column('status', STATUS, nullable=False, server_default='assigned'))
        batch_op.add_column(sa.Column('source', SOURCE, nullable=False, server_default='auto_department'))
        batch_op.add_column(sa.Column('assigned_by_id', sa.String(length=32), nullable=True))
        batch_op.add_column(sa.Column('assigned_at', sa.DateTime(timezone=True), nullable=False,
                                      server_default=sa.func.current_timestamp()))
        batch_op.add_column(sa.Column('due_date', sa.Date(), nullable=True))
        batch_op.add_column(sa.Column('note', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('withdrawn_at', sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column('withdrawn_reason', sa.String(length=255), nullable=True))
        batch_op.alter_column('started_at', existing_type=sa.DateTime(timezone=True), nullable=True)
        batch_op.drop_index(batch_op.f('ix_enrollments_path_id'))
        batch_op.create_index('ix_enrollments_path_status', ['path_id', 'status'], unique=False)
        batch_op.create_index('ix_enrollments_user_status', ['user_id', 'status'], unique=False)
        batch_op.create_foreign_key(batch_op.f('fk_enrollments_assigned_by_id_users'), 'users', ['assigned_by_id'], ['id'],
                                    ondelete='SET NULL')
    with op.batch_alter_table('enrollments', schema=None) as batch_op:
        batch_op.alter_column('status', existing_type=STATUS, server_default=None)
        batch_op.alter_column('source', existing_type=SOURCE, server_default=None)
        batch_op.alter_column('assigned_at', existing_type=sa.DateTime(timezone=True), server_default=None)
    _backfill()


def _backfill() -> None:
    bind = op.get_bind()
    enrollments = sa.table(
        'enrollments', sa.column('user_id', sa.String), sa.column('path_id', sa.String), sa.column('status', sa.String),
        sa.column('source', sa.String), sa.column('assigned_at', sa.DateTime(timezone=True)),
        sa.column('due_date', sa.Date), sa.column('lessons_read', sa.JSON), sa.column('tasks_done', sa.JSON),
    )
    today, now = date.today(), datetime.now(UTC)
    existing = set(bind.execute(sa.text('SELECT user_id, path_id FROM enrollments')).all())
    employees = bind.execute(sa.text(
        "SELECT id, department_code, job_position_id, joining_date, training_status FROM users "
        "WHERE user_role = 'employee' AND is_active")).all()
    rows = []
    for path_id, purpose, days in bind.execute(sa.text(
            "SELECT id, purpose, duration_days FROM learning_paths WHERE status = 'published'")).all():
        targets = bind.execute(sa.text('SELECT department_code, job_position_id FROM path_assignments WHERE path_id = :p'),
                               {'p': path_id}).all()
        departments = {d for d, _ in targets if d}
        positions = {p for _, p in targets if p}
        for user_id, department, position, joining, training in employees:
            if (user_id, path_id) in existing or (purpose == 'onboarding' and training == 'completed'):
                continue
            if position and position in positions:
                source = 'auto_position'
            elif 'Company-wide' in departments or department in departments:
                source = 'auto_department'
            else:
                continue
            due = None
            if days:
                start = date.fromisoformat(str(joining)) if joining else today
                due = start + timedelta(days=days)
                if due < today:
                    due = today + timedelta(days=days)
            rows.append({'user_id': user_id, 'path_id': path_id, 'status': 'assigned', 'source': source,
                         'assigned_at': now, 'due_date': due, 'lessons_read': [], 'tasks_done': []})
    if rows:
        op.bulk_insert(enrollments, rows)


def downgrade() -> None:
    with op.batch_alter_table('enrollments', schema=None) as batch_op:
        batch_op.drop_constraint(batch_op.f('fk_enrollments_assigned_by_id_users'), type_='foreignkey')
        batch_op.drop_constraint(op.f('ck_enrollments_enrollment_status'), type_='check')
        batch_op.drop_constraint(op.f('ck_enrollments_assignment_source'), type_='check')
        batch_op.drop_index('ix_enrollments_user_status')
        batch_op.drop_index('ix_enrollments_path_status')
        batch_op.create_index(batch_op.f('ix_enrollments_path_id'), ['path_id'], unique=False)
        batch_op.drop_column('withdrawn_reason')
        batch_op.drop_column('withdrawn_at')
        batch_op.drop_column('note')
        batch_op.drop_column('due_date')
        batch_op.drop_column('assigned_at')
        batch_op.drop_column('assigned_by_id')
        batch_op.drop_column('source')
        batch_op.drop_column('status')
    # Rows never started have no start date; the old schema requires one.
    op.execute('UPDATE enrollments SET started_at = CURRENT_TIMESTAMP WHERE started_at IS NULL')
    with op.batch_alter_table('enrollments', schema=None) as batch_op:
        batch_op.alter_column('started_at', existing_type=sa.DateTime(timezone=True), nullable=False)
