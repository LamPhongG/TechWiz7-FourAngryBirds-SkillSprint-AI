"""drop invitation_tokens

Revision ID: 1e792636cd07
Revises: b91f3d6c2a47
Create Date: 2026-09-28 00:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '1e792636cd07'
down_revision: str | Sequence[str] | None = 'b91f3d6c2a47'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema.

    The invite-link flow (HR sends a link, the employee self-registers) is replaced by immediate
    account creation with a generated password emailed to the employee (POST /users/from-cv).
    """
    op.drop_table('invitation_tokens')


def downgrade() -> None:
    """Downgrade schema."""
    op.create_table('invitation_tokens',
    sa.Column('token', sa.String(length=64), nullable=False),
    sa.Column('invited_email', sa.String(length=254), nullable=True),
    sa.Column('job_position_id', sa.String(length=64), nullable=False),
    sa.Column('department_code', sa.String(length=64), nullable=False),
    sa.Column('created_by', sa.String(length=32), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('used_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('registered_user_id', sa.String(length=32), nullable=True),
    sa.Column('note', sa.String(length=500), nullable=True),
    sa.ForeignKeyConstraint(['created_by'], ['users.id'], name=op.f('fk_invitation_tokens_created_by_users')),
    sa.ForeignKeyConstraint(['department_code'], ['departments.code'], name=op.f('fk_invitation_tokens_department_code_departments')),
    sa.ForeignKeyConstraint(['job_position_id'], ['job_positions.id'], name=op.f('fk_invitation_tokens_job_position_id_job_positions')),
    sa.ForeignKeyConstraint(['registered_user_id'], ['users.id'], name=op.f('fk_invitation_tokens_registered_user_id_users'), ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('token', name=op.f('pk_invitation_tokens'))
    )
