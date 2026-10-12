"""Initial dealer-scoped schema with PostgreSQL RLS policies."""

from __future__ import annotations

from alembic import op

from simcards_backend.core.database import Base
import simcards_backend.models  # noqa: F401

revision = "20260914_0001"
down_revision = None
branch_labels = None
depends_on = None

TENANT_TABLES = [
    "users",
    "branches",
    "brand_ambassadors",
    "targets",
    "performance_snapshots",
    "login_events",
    "account_flags",
    "stock_batches",
    "sim_cards",
    "stock_transfers",
    "sale_events",
    "return_events",
    "commission_rules",
    "safaricom_imports",
    "reconciliation_results",
    "reconciliation_line_details",
    "audit_logs",
    "refresh_tokens",
]


def _enable_rls() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    for table_name in TENANT_TABLES:
        policy_name = f"tenant_isolation_{table_name}"
        tenant_expr = (
            "dealer_id = NULLIF(current_setting('app.current_dealer_id', true), '')::integer"
        )
        op.execute(f'ALTER TABLE "{table_name}" ENABLE ROW LEVEL SECURITY')
        op.execute(
            f'CREATE POLICY "{policy_name}" ON "{table_name}" '
            f"USING ({tenant_expr}) WITH CHECK ({tenant_expr})"
        )


def _disable_rls() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    for table_name in reversed(TENANT_TABLES):
        policy_name = f"tenant_isolation_{table_name}"
        op.execute(f'DROP POLICY IF EXISTS "{policy_name}" ON "{table_name}"')
        op.execute(f'ALTER TABLE "{table_name}" DISABLE ROW LEVEL SECURITY')


def upgrade() -> None:
    Base.metadata.create_all(bind=op.get_bind())
    _enable_rls()


def downgrade() -> None:
    _disable_rls()
    Base.metadata.drop_all(bind=op.get_bind())
