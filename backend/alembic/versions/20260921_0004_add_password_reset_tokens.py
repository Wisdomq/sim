"""add password reset tokens

Revision ID: 20260921_0004
Revises: 20260919_0003
Create Date: 2026-09-21 22:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20260921_0004'
down_revision: Union[str, None] = '20260919_0003'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'password_reset_tokens',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('dealer_id', sa.Integer(), nullable=False),
        sa.Column('token', sa.String(length=255), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['dealer_id'], ['dealers.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('token', name='uq_password_reset_tokens_token')
    )
    op.create_index('ix_password_reset_tokens_expires', 'password_reset_tokens', ['expires_at'])
    op.create_index('ix_password_reset_tokens_user', 'password_reset_tokens', ['user_id'])

    # Enable RLS for password_reset_tokens
    op.execute("""
        ALTER TABLE password_reset_tokens ENABLE ROW LEVEL SECURITY;
        CREATE POLICY password_reset_tokens_tenant_isolation ON password_reset_tokens
            FOR ALL
            USING (dealer_id = current_setting('app.current_dealer_id')::int);
    """)


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS password_reset_tokens_tenant_isolation ON password_reset_tokens")
    op.execute("ALTER TABLE password_reset_tokens DISABLE ROW LEVEL SECURITY")
    op.drop_index('ix_password_reset_tokens_user', table_name='password_reset_tokens')
    op.drop_index('ix_password_reset_tokens_expires', table_name='password_reset_tokens')
    op.drop_table('password_reset_tokens')
