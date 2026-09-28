"""initial schema

Revision ID: 09503405de6e
Revises: 
Create Date: 2026-09-25 09:48:50.565353

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '09503405de6e'
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('departments',
    sa.Column('code', sa.String(length=64), nullable=False),
    sa.Column('name', sa.String(length=128), nullable=False),
    sa.Column('name_en', sa.String(length=128), nullable=False),
    sa.PrimaryKeyConstraint('code', name=op.f('pk_departments'))
    )
    op.create_table('job_positions',
    sa.Column('id', sa.String(length=64), nullable=False),
    sa.Column('name', sa.String(length=160), nullable=False),
    sa.Column('name_en', sa.String(length=160), nullable=False),
    sa.Column('department_code', sa.String(length=64), nullable=False),
    sa.ForeignKeyConstraint(['department_code'], ['departments.code'], name=op.f('fk_job_positions_department_code_departments')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_job_positions'))
    )
    op.create_table('users',
    sa.Column('id', sa.String(length=32), nullable=False),
    sa.Column('email', sa.String(length=254), nullable=False),
    sa.Column('password_hash', sa.String(length=128), nullable=False),
    sa.Column('name', sa.String(length=128), nullable=False),
    sa.Column('user_role', sa.Enum('admin', 'hr', 'reviewer', 'employee', name='user_role', native_enum=False, length=32), nullable=False),
    sa.Column('job_title', sa.String(length=128), nullable=True),
    sa.Column('department_code', sa.String(length=64), nullable=True),
    sa.Column('job_position_id', sa.String(length=64), nullable=True),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.CheckConstraint("user_role IN ('admin', 'hr', 'reviewer', 'employee')", name=op.f('ck_users_user_role')),
    sa.ForeignKeyConstraint(['department_code'], ['departments.code'], name=op.f('fk_users_department_code_departments')),
    sa.ForeignKeyConstraint(['job_position_id'], ['job_positions.id'], name=op.f('fk_users_job_position_id_job_positions')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_users')),
    sa.UniqueConstraint('email', name=op.f('uq_users_email'))
    )
    op.create_table('audit_logs',
    sa.Column('id', sa.String(length=32), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('actor_id', sa.String(length=32), nullable=False),
    sa.Column('actor_name', sa.String(length=128), nullable=False),
    sa.Column('actor_role', sa.Enum('admin', 'hr', 'reviewer', 'employee', name='actor_role', native_enum=False, length=32), nullable=False),
    sa.Column('action', sa.String(length=32), nullable=False),
    sa.Column('path_id', sa.String(length=32), nullable=True),
    sa.Column('path_title', sa.String(length=255), nullable=True),
    sa.Column('revision', sa.Integer(), nullable=True),
    sa.Column('status_before', sa.Enum('draft', 'in_review', 'changes_requested', 'published', 'archived', name='status_before', native_enum=False, length=32), nullable=True),
    sa.Column('status_after', sa.Enum('draft', 'in_review', 'changes_requested', 'published', 'archived', name='status_after', native_enum=False, length=32), nullable=True),
    sa.Column('final_status', sa.Enum('verified', 'verified_warning', 'manual_review', name='final_status', native_enum=False, length=32), nullable=True),
    sa.Column('reason', sa.Text(), nullable=True),
    sa.Column('details', sa.JSON(), nullable=True),
    sa.CheckConstraint("actor_role IN ('admin', 'hr', 'reviewer', 'employee')", name=op.f('ck_audit_logs_actor_role')),
    sa.CheckConstraint("final_status IN ('verified', 'verified_warning', 'manual_review')", name=op.f('ck_audit_logs_final_status')),
    sa.CheckConstraint("status_after IN ('draft', 'in_review', 'changes_requested', 'published', 'archived')", name=op.f('ck_audit_logs_status_after')),
    sa.CheckConstraint("status_before IN ('draft', 'in_review', 'changes_requested', 'published', 'archived')", name=op.f('ck_audit_logs_status_before')),
    sa.ForeignKeyConstraint(['actor_id'], ['users.id'], name=op.f('fk_audit_logs_actor_id_users')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_audit_logs'))
    )
    with op.batch_alter_table('audit_logs', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_audit_logs_action'), ['action'], unique=False)
        batch_op.create_index(batch_op.f('ix_audit_logs_created_at'), ['created_at'], unique=False)
        batch_op.create_index(batch_op.f('ix_audit_logs_path_id'), ['path_id'], unique=False)

    op.create_table('documents',
    sa.Column('id', sa.String(length=32), nullable=False),
    sa.Column('code', sa.String(length=32), nullable=False),
    sa.Column('family', sa.String(length=96), nullable=False),
    sa.Column('version', sa.String(length=16), nullable=False),
    sa.Column('title', sa.String(length=255), nullable=False),
    sa.Column('title_en', sa.String(length=255), nullable=False),
    sa.Column('category', sa.String(length=32), nullable=False),
    sa.Column('department_code', sa.String(length=64), nullable=False),
    sa.Column('effective_date', sa.Date(), nullable=False),
    sa.Column('expiry_date', sa.Date(), nullable=True),
    sa.Column('file_name', sa.String(length=255), nullable=False),
    sa.Column('ext', sa.String(length=8), nullable=False),
    sa.Column('mime_type', sa.String(length=128), nullable=True),
    sa.Column('size_bytes', sa.Integer(), nullable=False),
    sa.Column('sha256', sa.String(length=64), nullable=False),
    sa.Column('storage_path', sa.String(length=512), nullable=False),
    sa.Column('processing_status', sa.Enum('pending', 'processing', 'ready', 'failed', name='processing_status', native_enum=False, length=32), nullable=False),
    sa.Column('processing_engine', sa.String(length=32), nullable=True),
    sa.Column('processing_error', sa.String(length=64), nullable=True),
    sa.Column('page_count', sa.Integer(), nullable=True),
    sa.Column('char_count', sa.Integer(), nullable=True),
    sa.Column('processed_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('uploaded_by_id', sa.String(length=32), nullable=False),
    sa.Column('uploaded_at', sa.DateTime(timezone=True), nullable=False),
    sa.CheckConstraint("processing_status IN ('pending', 'processing', 'ready', 'failed')", name=op.f('ck_documents_processing_status')),
    sa.ForeignKeyConstraint(['department_code'], ['departments.code'], name=op.f('fk_documents_department_code_departments')),
    sa.ForeignKeyConstraint(['uploaded_by_id'], ['users.id'], name=op.f('fk_documents_uploaded_by_id_users')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_documents')),
    sa.UniqueConstraint('code', 'version', name=op.f('uq_documents_code_version')),
    sa.UniqueConstraint('sha256', name=op.f('uq_documents_sha256'))
    )
    with op.batch_alter_table('documents', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_documents_code'), ['code'], unique=False)
        batch_op.create_index(batch_op.f('ix_documents_family'), ['family'], unique=False)

    op.create_table('learning_paths',
    sa.Column('id', sa.String(length=32), nullable=False),
    sa.Column('title', sa.String(length=255), nullable=False),
    sa.Column('title_en', sa.String(length=255), nullable=False),
    sa.Column('purpose', sa.Enum('onboarding', 'promotion', name='purpose', native_enum=False, length=32), nullable=False),
    sa.Column('level', sa.Enum('Beginner', 'Intermediate', 'Advanced', name='level', native_enum=False, length=32), nullable=False),
    sa.Column('target_job_position_id', sa.String(length=64), nullable=False),
    sa.Column('target_department_code', sa.String(length=64), nullable=False),
    sa.Column('prompt', sa.Text(), nullable=True),
    sa.Column('prompt_version', sa.String(length=16), nullable=False),
    sa.Column('engine', sa.String(length=32), nullable=False),
    sa.Column('model', sa.String(length=64), nullable=True),
    sa.Column('stages', sa.JSON(), nullable=False),
    sa.Column('excluded_chunks', sa.JSON(), nullable=False),
    sa.Column('coverage', sa.JSON(), nullable=True),
    sa.Column('status', sa.Enum('draft', 'in_review', 'changes_requested', 'published', 'archived', name='status', native_enum=False, length=32), nullable=False),
    sa.Column('revision', sa.Integer(), nullable=False),
    sa.Column('created_by_id', sa.String(length=32), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('submitted_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('published_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('archived_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('approved_by_id', sa.String(length=32), nullable=True),
    sa.Column('approval_final_status', sa.Enum('verified', 'verified_warning', 'manual_review', name='approval_final_status', native_enum=False, length=32), nullable=True),
    sa.Column('approval_reason', sa.Text(), nullable=True),
    sa.CheckConstraint("approval_final_status IN ('verified', 'verified_warning', 'manual_review')", name=op.f('ck_learning_paths_approval_final_status')),
    sa.CheckConstraint("level IN ('Beginner', 'Intermediate', 'Advanced')", name=op.f('ck_learning_paths_level')),
    sa.CheckConstraint("purpose IN ('onboarding', 'promotion')", name=op.f('ck_learning_paths_purpose')),
    sa.CheckConstraint("status IN ('draft', 'in_review', 'changes_requested', 'published', 'archived')", name=op.f('ck_learning_paths_status')),
    sa.ForeignKeyConstraint(['approved_by_id'], ['users.id'], name=op.f('fk_learning_paths_approved_by_id_users')),
    sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], name=op.f('fk_learning_paths_created_by_id_users')),
    sa.ForeignKeyConstraint(['target_department_code'], ['departments.code'], name=op.f('fk_learning_paths_target_department_code_departments')),
    sa.ForeignKeyConstraint(['target_job_position_id'], ['job_positions.id'], name=op.f('fk_learning_paths_target_job_position_id_job_positions')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_learning_paths'))
    )
    with op.batch_alter_table('learning_paths', schema=None) as batch_op:
        batch_op.create_index('ix_learning_paths_status_updated', ['status', 'updated_at'], unique=False)

    op.create_table('document_chunks',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('document_id', sa.String(length=32), nullable=False),
    sa.Column('chunk_id', sa.String(length=48), nullable=False),
    sa.Column('section_id', sa.String(length=48), nullable=True),
    sa.Column('heading', sa.String(length=255), nullable=True),
    sa.Column('page', sa.Integer(), nullable=True),
    sa.Column('position', sa.Integer(), nullable=False),
    sa.Column('content', sa.Text(), nullable=False),
    sa.ForeignKeyConstraint(['document_id'], ['documents.id'], name=op.f('fk_document_chunks_document_id_documents'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_document_chunks')),
    sa.UniqueConstraint('document_id', 'chunk_id', name=op.f('uq_document_chunks_document_id_chunk_id'))
    )
    op.create_table('enrollments',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.String(length=32), nullable=False),
    sa.Column('path_id', sa.String(length=32), nullable=False),
    sa.Column('lessons_read', sa.JSON(), nullable=False),
    sa.Column('tasks_done', sa.JSON(), nullable=False),
    sa.Column('started_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['path_id'], ['learning_paths.id'], name=op.f('fk_enrollments_path_id_learning_paths'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_enrollments_user_id_users'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_enrollments')),
    sa.UniqueConstraint('user_id', 'path_id', name=op.f('uq_enrollments_user_id_path_id'))
    )
    with op.batch_alter_table('enrollments', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_enrollments_path_id'), ['path_id'], unique=False)

    op.create_table('injection_flags',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('document_id', sa.String(length=32), nullable=False),
    sa.Column('chunk_id', sa.String(length=48), nullable=False),
    sa.Column('page', sa.Integer(), nullable=True),
    sa.Column('rule_id', sa.String(length=64), nullable=False),
    sa.Column('severity', sa.String(length=16), nullable=False),
    sa.Column('match', sa.Text(), nullable=False),
    sa.Column('excerpt', sa.Text(), nullable=False),
    sa.ForeignKeyConstraint(['document_id'], ['documents.id'], name=op.f('fk_injection_flags_document_id_documents'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_injection_flags'))
    )
    with op.batch_alter_table('injection_flags', schema=None) as batch_op:
        batch_op.create_index('ix_injection_flags_document_chunk', ['document_id', 'chunk_id'], unique=False)

    op.create_table('path_assignments',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('path_id', sa.String(length=32), nullable=False),
    sa.Column('department_code', sa.String(length=64), nullable=True),
    sa.Column('job_position_id', sa.String(length=64), nullable=True),
    sa.CheckConstraint('department_code IS NOT NULL OR job_position_id IS NOT NULL', name=op.f('ck_path_assignments_has_target')),
    sa.ForeignKeyConstraint(['department_code'], ['departments.code'], name=op.f('fk_path_assignments_department_code_departments')),
    sa.ForeignKeyConstraint(['job_position_id'], ['job_positions.id'], name=op.f('fk_path_assignments_job_position_id_job_positions')),
    sa.ForeignKeyConstraint(['path_id'], ['learning_paths.id'], name=op.f('fk_path_assignments_path_id_learning_paths'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_path_assignments'))
    )
    with op.batch_alter_table('path_assignments', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_path_assignments_department_code'), ['department_code'], unique=False)
        batch_op.create_index(batch_op.f('ix_path_assignments_job_position_id'), ['job_position_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_path_assignments_path_id'), ['path_id'], unique=False)

    op.create_table('path_comments',
    sa.Column('id', sa.String(length=32), nullable=False),
    sa.Column('path_id', sa.String(length=32), nullable=False),
    sa.Column('author_id', sa.String(length=32), nullable=False),
    sa.Column('text', sa.Text(), nullable=False),
    sa.Column('item_ref', sa.JSON(), nullable=True),
    sa.Column('reply_to_id', sa.String(length=32), nullable=True),
    sa.Column('resolved', sa.Boolean(), nullable=False),
    sa.Column('resolved_by_id', sa.String(length=32), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['author_id'], ['users.id'], name=op.f('fk_path_comments_author_id_users')),
    sa.ForeignKeyConstraint(['path_id'], ['learning_paths.id'], name=op.f('fk_path_comments_path_id_learning_paths'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['reply_to_id'], ['path_comments.id'], name=op.f('fk_path_comments_reply_to_id_path_comments'), ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['resolved_by_id'], ['users.id'], name=op.f('fk_path_comments_resolved_by_id_users')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_path_comments'))
    )
    with op.batch_alter_table('path_comments', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_path_comments_path_id'), ['path_id'], unique=False)

    op.create_table('path_sources',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('path_id', sa.String(length=32), nullable=False),
    sa.Column('document_id', sa.String(length=32), nullable=True),
    sa.Column('doc_code', sa.String(length=32), nullable=False),
    sa.Column('doc_version', sa.String(length=16), nullable=False),
    sa.Column('position', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['document_id'], ['documents.id'], name=op.f('fk_path_sources_document_id_documents'), ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['path_id'], ['learning_paths.id'], name=op.f('fk_path_sources_path_id_learning_paths'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_path_sources'))
    )
    with op.batch_alter_table('path_sources', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_path_sources_path_id'), ['path_id'], unique=False)

    op.create_table('quiz_attempts',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('enrollment_id', sa.Integer(), nullable=False),
    sa.Column('module_id', sa.String(length=64), nullable=False),
    sa.Column('answers', sa.JSON(), nullable=False),
    sa.Column('score', sa.Integer(), nullable=False),
    sa.Column('total', sa.Integer(), nullable=False),
    sa.Column('submitted_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['enrollment_id'], ['enrollments.id'], name=op.f('fk_quiz_attempts_enrollment_id_enrollments'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_quiz_attempts'))
    )
    with op.batch_alter_table('quiz_attempts', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_quiz_attempts_enrollment_id'), ['enrollment_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('quiz_attempts', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_quiz_attempts_enrollment_id'))

    op.drop_table('quiz_attempts')
    with op.batch_alter_table('path_sources', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_path_sources_path_id'))

    op.drop_table('path_sources')
    with op.batch_alter_table('path_comments', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_path_comments_path_id'))

    op.drop_table('path_comments')
    with op.batch_alter_table('path_assignments', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_path_assignments_path_id'))
        batch_op.drop_index(batch_op.f('ix_path_assignments_job_position_id'))
        batch_op.drop_index(batch_op.f('ix_path_assignments_department_code'))

    op.drop_table('path_assignments')
    with op.batch_alter_table('injection_flags', schema=None) as batch_op:
        batch_op.drop_index('ix_injection_flags_document_chunk')

    op.drop_table('injection_flags')
    with op.batch_alter_table('enrollments', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_enrollments_path_id'))

    op.drop_table('enrollments')
    op.drop_table('document_chunks')
    with op.batch_alter_table('learning_paths', schema=None) as batch_op:
        batch_op.drop_index('ix_learning_paths_status_updated')

    op.drop_table('learning_paths')
    with op.batch_alter_table('documents', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_documents_family'))
        batch_op.drop_index(batch_op.f('ix_documents_code'))

    op.drop_table('documents')
    with op.batch_alter_table('audit_logs', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_audit_logs_path_id'))
        batch_op.drop_index(batch_op.f('ix_audit_logs_created_at'))
        batch_op.drop_index(batch_op.f('ix_audit_logs_action'))

    op.drop_table('audit_logs')
    op.drop_table('users')
    op.drop_table('job_positions')
    op.drop_table('departments')
