"""Add notifications table with tenant RLS policy (Phase 7)."""

from __future__ import annotations

from alembic import op

from simcards_backend.core.database import Base
import simcards_backend.models  # noqa: F401

revision = "20260915_0002"
down_revision = "20260914_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # create_all is idempotent per-table: only adds the new notifications table.
    Base.metadata.create_all(bind=op.get_bind())
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        policy_name = "tenant_isolation_notifications"
        tenant_expr = (
            "dealer_id = NULLIF(current_setting('app.current_dealer_id', true), '')::integer"
        )
        op.execute('ALTER TABLE "notifications" ENABLE ROW LEVEL SECURITY')
        op.execute(
            f'CREATE POLICY "{policy_name}" ON "notifications" '
            f"USING ({tenant_expr}) WITH CHECK ({tenant_expr})"
        )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute('DROP POLICY IF EXISTS "tenant_isolation_notifications" ON "notifications"')
        op.execute('ALTER TABLE "notifications" DISABLE ROW LEVEL SECURITY')
    op.drop_table("notifications")