"""Add (dealer_id, top_up_date) index on reconciliation_line_details (B-10-06)."""

from __future__ import annotations

from alembic import op

revision = "20260919_0003"
down_revision = "20260915_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    result = bind.exec_driver_sql(
        "SELECT 1 FROM pg_indexes WHERE indexname = 'ix_recon_detail_dealer_topup_date'"
    ).fetchone()
    if result is None:
        op.create_index(
            "ix_recon_detail_dealer_topup_date",
            "reconciliation_line_details",
            ["dealer_id", "top_up_date"],
            unique=False,
        )


def downgrade() -> None:
    op.drop_index(
        "ix_recon_detail_dealer_topup_date",
        table_name="reconciliation_line_details",
    )
