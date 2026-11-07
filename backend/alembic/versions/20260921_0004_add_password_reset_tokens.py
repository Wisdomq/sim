"""add password reset tokens

Revision ID: 20260921_0004
Revises: 20260919_0003
Create Date: 2026-09-21 22:15:00.000000

"""
from typing import Sequence, Union

from alembic import op

from simcards_backend.core.database import Base
import simcards_backend.models  # noqa: F401


# revision identifiers, used by Alembic.
revision: str = '20260921_0004'
down_revision: Union[str, None] = '20260919_0003'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # create_all is idempotent per-table: migration 0001 already reflects the
    # current models, so on a fresh database the table (and its indexes) exist
    # by now and this is a no-op; on older databases it adds the table.
    Base.metadata.create_all(bind=op.get_bind())

    # Enable RLS for password_reset_tokens (idempotent).
    op.execute("""
        ALTER TABLE password_reset_tokens ENABLE ROW LEVEL SECURITY;
        DROP POLICY IF EXISTS password_reset_tokens_tenant_isolation ON password_reset_tokens;
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
