"""SQLAlchemy models for the SIM stock and sales domain."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    JSON,
    Date,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, declared_attr, mapped_column, relationship

from simcards_backend.core.database import Base
from simcards_backend.models.enums import (
    AccountFlagType,
    AccountStatus,
    BranchType,
    NotificationType,
    OwnerType,
    PeriodType,
    ReconciliationMatchStatus,
    ReturnStatus,
    Role,
    SafaricomImportStatus,
    ScannedVia,
    SimStatus,
    StockBatchSource,
    SubjectType,
    TransferType,
)


class TimestampMixin:
    """Created/updated timestamps shared by mutable tables."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class CreatedAtMixin:
    """Creation timestamp for append-only/audit tables."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class TenantMixin:
    """Dealer tenant scope shared by all row-level tenant tables."""

    @declared_attr
    def dealer_id(cls) -> Mapped[int]:
        return mapped_column(
            ForeignKey("dealers.id", ondelete="CASCADE"),
            index=True,
            nullable=False,
        )


class Dealer(CreatedAtMixin, Base):
    __tablename__ = "dealers"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    safaricom_dealer_shortcode: Mapped[str | None] = mapped_column(String(64), unique=True)

    users: Mapped[list[User]] = relationship(back_populates="dealer", cascade="all, delete-orphan")


class User(TenantMixin, TimestampMixin, Base):
    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("email", name="uq_users_email"),
        Index("ix_users_dealer_role", "dealer_id", "role"),
        Index("ix_users_dealer_branch", "dealer_id", "branch_id"),
        Index("ix_users_dealer_ba_profile", "dealer_id", "ba_profile_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    role: Mapped[Role] = mapped_column(
        SAEnum(Role, name="role_enum", native_enum=False, create_constraint=True),
        nullable=False,
    )
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    branch_id: Mapped[int | None] = mapped_column(
        ForeignKey("branches.id", ondelete="SET NULL", use_alter=True, name="fk_users_branch_id"),
        nullable=True,
    )
    ba_profile_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "brand_ambassadors.id",
            ondelete="SET NULL",
            use_alter=True,
            name="fk_users_ba_profile_id",
        ),
        nullable=True,
    )
    status: Mapped[AccountStatus] = mapped_column(
        SAEnum(AccountStatus, name="account_status_enum", native_enum=False, create_constraint=True),
        default=AccountStatus.ACTIVE,
        nullable=False,
    )

    dealer: Mapped[Dealer] = relationship(back_populates="users")
    branch: Mapped[Branch | None] = relationship(foreign_keys=[branch_id])
    ba_profile: Mapped[BrandAmbassador | None] = relationship(foreign_keys=[ba_profile_id])


class Branch(TenantMixin, CreatedAtMixin, Base):
    __tablename__ = "branches"
    __table_args__ = (
        UniqueConstraint("dealer_id", "name", name="uq_branches_dealer_name"),
        Index("ix_branches_dealer_type", "dealer_id", "type"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[BranchType] = mapped_column(
        SAEnum(BranchType, name="branch_type_enum", native_enum=False, create_constraint=True),
        nullable=False,
    )
    id_number: Mapped[str] = mapped_column(String(128), nullable=False)
    photo_url: Mapped[str] = mapped_column(Text, nullable=False)
    created_by_id: Mapped[int | None] = mapped_column(
        "created_by",
        ForeignKey("users.id", ondelete="SET NULL", use_alter=True, name="fk_branches_created_by"),
        nullable=True,
    )

    created_by_user: Mapped[User | None] = relationship(foreign_keys=[created_by_id])


class BrandAmbassador(TenantMixin, TimestampMixin, Base):
    __tablename__ = "brand_ambassadors"
    __table_args__ = (
        UniqueConstraint("user_id", name="uq_brand_ambassadors_user_id"),
        Index("ix_brand_ambassadors_dealer_branch", "dealer_id", "branch_id"),
        Index("ix_brand_ambassadors_dealer_status", "dealer_id", "status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    branch_id: Mapped[int] = mapped_column(
        ForeignKey("branches.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey(
            "users.id",
            ondelete="CASCADE",
            use_alter=True,
            name="fk_brand_ambassadors_user_id",
        ),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    phone_msisdn: Mapped[str | None] = mapped_column(String(32))
    id_number: Mapped[str] = mapped_column(String(128), nullable=False)
    photo_url: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[AccountStatus] = mapped_column(
        SAEnum(AccountStatus, name="ba_status_enum", native_enum=False, create_constraint=True),
        default=AccountStatus.ACTIVE,
        nullable=False,
    )
    created_by_id: Mapped[int | None] = mapped_column(
        "created_by",
        ForeignKey("users.id", ondelete="SET NULL", use_alter=True, name="fk_bas_created_by"),
        nullable=True,
    )

    branch: Mapped[Branch] = relationship(foreign_keys=[branch_id])
    user: Mapped[User] = relationship(foreign_keys=[user_id])
    created_by_user: Mapped[User | None] = relationship(foreign_keys=[created_by_id])


class Target(TenantMixin, CreatedAtMixin, Base):
    __tablename__ = "targets"
    __table_args__ = (
        Index("ix_targets_dealer_branch_period", "dealer_id", "branch_id", "period_type"),
        Index("ix_targets_effective_window", "effective_from", "effective_to"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    branch_id: Mapped[int] = mapped_column(ForeignKey("branches.id", ondelete="CASCADE"))
    period_type: Mapped[PeriodType] = mapped_column(
        SAEnum(PeriodType, name="target_period_type_enum", native_enum=False, create_constraint=True),
        nullable=False,
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    effective_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    effective_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    set_by_id: Mapped[int | None] = mapped_column(
        "set_by", ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )


class PerformanceSnapshot(TenantMixin, Base):
    __tablename__ = "performance_snapshots"
    __table_args__ = (
        UniqueConstraint(
            "dealer_id",
            "subject_type",
            "subject_id",
            "period_type",
            "period_start",
            "period_end",
            name="uq_performance_snapshot_period",
        ),
        Index("ix_perf_dealer_subject", "dealer_id", "subject_type", "subject_id"),
        Index("ix_perf_dealer_period", "dealer_id", "period_type", "period_start", "period_end"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    subject_type: Mapped[SubjectType] = mapped_column(
        SAEnum(
            SubjectType,
            name="performance_subject_type_enum",
            native_enum=False,
            create_constraint=True,
        ),
        nullable=False,
    )
    subject_id: Mapped[int] = mapped_column(Integer, nullable=False)
    period_type: Mapped[PeriodType] = mapped_column(
        SAEnum(
            PeriodType,
            name="performance_period_type_enum",
            native_enum=False,
            create_constraint=True,
        ),
        nullable=False,
    )
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    target_quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    actual_sold_quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    percentage_achieved: Mapped[Decimal] = mapped_column(Numeric(7, 2), nullable=False, default=0)
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class LoginEvent(TenantMixin, Base):
    __tablename__ = "login_events"
    __table_args__ = (
        Index("ix_login_events_dealer_user_time", "dealer_id", "user_id", "logged_in_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    role: Mapped[Role] = mapped_column(
        SAEnum(Role, name="login_role_enum", native_enum=False, create_constraint=True),
        nullable=False,
    )
    logged_in_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    device_info: Mapped[dict[str, Any] | None] = mapped_column(JSON)


class AccountFlag(TenantMixin, Base):
    __tablename__ = "account_flags"
    __table_args__ = (
        Index("ix_account_flags_dealer_user_active", "dealer_id", "user_id", "resolved_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    role: Mapped[Role] = mapped_column(
        SAEnum(Role, name="account_flag_role_enum", native_enum=False, create_constraint=True),
        nullable=False,
    )
    flag_type: Mapped[AccountFlagType] = mapped_column(
        SAEnum(
            AccountFlagType,
            name="account_flag_type_enum",
            native_enum=False,
            create_constraint=True,
        ),
        nullable=False,
    )
    flagged_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    acknowledged_by_id: Mapped[int | None] = mapped_column(
        "acknowledged_by", ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )


class Notification(TenantMixin, Base):
    __tablename__ = "notifications"
    __table_args__ = (
        Index("ix_notifications_dealer_user_unread", "dealer_id", "user_id", "is_read"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    type: Mapped[NotificationType] = mapped_column(
        SAEnum(
            NotificationType,
            name="notification_type_enum",
            native_enum=False,
            create_constraint=True,
        ),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str | None] = mapped_column(Text)
    metadata_json: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, default=dict, nullable=False)
    is_read: Mapped[bool] = mapped_column(default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class StockBatch(TenantMixin, Base):
    __tablename__ = "stock_batches"
    __table_args__ = (
        Index("ix_stock_batches_dealer_source", "dealer_id", "source", "source_reference"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    source: Mapped[StockBatchSource] = mapped_column(
        SAEnum(StockBatchSource, name="stock_batch_source_enum", native_enum=False, create_constraint=True),
        nullable=False,
    )
    source_reference: Mapped[str] = mapped_column(String(255), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    imported_by_id: Mapped[int | None] = mapped_column(
        "imported_by", ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    imported_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class SimCard(TenantMixin, TimestampMixin, Base):
    __tablename__ = "sim_cards"
    __table_args__ = (
        UniqueConstraint("dealer_id", "serial_number", name="uq_sim_cards_dealer_serial"),
        Index("ix_sim_cards_dealer_status", "dealer_id", "status"),
        Index("ix_sim_cards_dealer_branch", "dealer_id", "current_branch_id"),
        Index("ix_sim_cards_dealer_ba", "dealer_id", "current_ba_id"),
        Index("ix_sim_cards_expiry", "dealer_id", "expiry_date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    serial_number: Mapped[str] = mapped_column(String(64), nullable=False)
    stock_batch_id: Mapped[int] = mapped_column(
        ForeignKey("stock_batches.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[SimStatus] = mapped_column(
        SAEnum(SimStatus, name="sim_status_enum", native_enum=False, create_constraint=True),
        default=SimStatus.IN_HQ_STOCK,
        nullable=False,
    )
    current_branch_id: Mapped[int | None] = mapped_column(ForeignKey("branches.id", ondelete="SET NULL"))
    current_ba_id: Mapped[int | None] = mapped_column(
        ForeignKey("brand_ambassadors.id", ondelete="SET NULL")
    )
    expiry_date: Mapped[date | None] = mapped_column(Date)


class StockTransfer(TenantMixin, CreatedAtMixin, Base):
    __tablename__ = "stock_transfers"
    __table_args__ = (
        Index("ix_stock_transfers_dealer_sim", "dealer_id", "sim_card_id"),
        Index("ix_stock_transfers_dealer_created", "dealer_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    sim_card_id: Mapped[int] = mapped_column(
        ForeignKey("sim_cards.id", ondelete="CASCADE"), nullable=False
    )
    from_owner_type: Mapped[OwnerType] = mapped_column(
        SAEnum(OwnerType, name="transfer_from_owner_type_enum", native_enum=False, create_constraint=True),
        nullable=False,
    )
    from_owner_id: Mapped[int | None] = mapped_column(Integer)
    to_owner_type: Mapped[OwnerType] = mapped_column(
        SAEnum(OwnerType, name="transfer_to_owner_type_enum", native_enum=False, create_constraint=True),
        nullable=False,
    )
    to_owner_id: Mapped[int | None] = mapped_column(Integer)
    transfer_type: Mapped[TransferType] = mapped_column(
        SAEnum(TransferType, name="transfer_type_enum", native_enum=False, create_constraint=True),
        nullable=False,
    )
    initiated_by_id: Mapped[int | None] = mapped_column(
        "initiated_by", ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )


class SaleEvent(TenantMixin, Base):
    __tablename__ = "sale_events"
    __table_args__ = (
        UniqueConstraint("sim_card_id", name="uq_sale_events_sim_card_id"),
        UniqueConstraint("dealer_id", "client_event_id", name="uq_sale_events_dealer_client_event"),
        Index("ix_sale_events_dealer_ba_sold", "dealer_id", "ba_id", "sold_at"),
        Index("ix_sale_events_dealer_branch_sold", "dealer_id", "branch_id", "sold_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    sim_card_id: Mapped[int] = mapped_column(
        ForeignKey("sim_cards.id", ondelete="CASCADE"), nullable=False
    )
    ba_id: Mapped[int] = mapped_column(
        ForeignKey("brand_ambassadors.id", ondelete="CASCADE"), nullable=False
    )
    branch_id: Mapped[int] = mapped_column(ForeignKey("branches.id", ondelete="CASCADE"), nullable=False)
    sold_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    scanned_via: Mapped[ScannedVia] = mapped_column(
        SAEnum(ScannedVia, name="scanned_via_enum", native_enum=False, create_constraint=True),
        default=ScannedVia.CAMERA,
        nullable=False,
    )
    synced_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    commission_rule_id: Mapped[int | None] = mapped_column(
        ForeignKey("commission_rules.id", ondelete="SET NULL")
    )
    commission_amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    client_event_id: Mapped[str | None] = mapped_column(String(64))


class ReturnEvent(TenantMixin, Base):
    __tablename__ = "return_events"
    __table_args__ = (
        Index("ix_return_events_dealer_branch_status", "dealer_id", "branch_id", "status"),
        Index("ix_return_events_dealer_sim", "dealer_id", "sim_card_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    sim_card_id: Mapped[int] = mapped_column(
        ForeignKey("sim_cards.id", ondelete="CASCADE"), nullable=False
    )
    requested_by_id: Mapped[int | None] = mapped_column(
        "requested_by", ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    branch_id: Mapped[int] = mapped_column(ForeignKey("branches.id", ondelete="CASCADE"), nullable=False)
    return_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    reason: Mapped[str | None] = mapped_column(Text)
    status: Mapped[ReturnStatus] = mapped_column(
        SAEnum(ReturnStatus, name="return_status_enum", native_enum=False, create_constraint=True),
        default=ReturnStatus.REQUESTED,
        nullable=False,
    )


class CommissionRule(TenantMixin, CreatedAtMixin, Base):
    __tablename__ = "commission_rules"
    __table_args__ = (
        Index("ix_commission_rules_dealer_effective", "dealer_id", "effective_from", "effective_to"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    amount_per_sim: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    effective_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    effective_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_by_id: Mapped[int | None] = mapped_column(
        "created_by", ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )


class SafaricomImport(TenantMixin, Base):
    __tablename__ = "safaricom_imports"
    __table_args__ = (
        Index("ix_safaricom_imports_dealer_report_date", "dealer_id", "report_date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    uploaded_by_id: Mapped[int | None] = mapped_column(
        "uploaded_by", ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    file_reference: Mapped[str] = mapped_column(Text, nullable=False)
    report_date: Mapped[date] = mapped_column(Date, nullable=False)
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    row_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[SafaricomImportStatus] = mapped_column(
        SAEnum(
            SafaricomImportStatus,
            name="safaricom_import_status_enum",
            native_enum=False,
            create_constraint=True,
        ),
        default=SafaricomImportStatus.PROCESSING,
        nullable=False,
    )


class ReconciliationResult(TenantMixin, Base):
    __tablename__ = "reconciliation_results"
    __table_args__ = (
        UniqueConstraint("safaricom_import_id", name="uq_reconciliation_results_import"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    safaricom_import_id: Mapped[int] = mapped_column(
        ForeignKey("safaricom_imports.id", ondelete="CASCADE"), nullable=False
    )
    total_sold_in_app: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_confirmed_activated_by_safaricom: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_topped_up: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_cumulative_commission: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0, nullable=False)
    total_fraud_flagged: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    unmatched_sold_not_in_safaricom_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    unmatched_in_safaricom_not_sold_in_app_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class ReconciliationLineDetail(TenantMixin, Base):
    __tablename__ = "reconciliation_line_details"
    __table_args__ = (
        Index("ix_recon_detail_result_status", "reconciliation_result_id", "match_status"),
        Index("ix_recon_detail_dealer_topup_date", "dealer_id", "top_up_date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    reconciliation_result_id: Mapped[int] = mapped_column(
        ForeignKey("reconciliation_results.id", ondelete="CASCADE"), nullable=False
    )
    sim_card_id: Mapped[int | None] = mapped_column(ForeignKey("sim_cards.id", ondelete="SET NULL"))
    serial_number: Mapped[str | None] = mapped_column(String(64))
    top_up_date: Mapped[date | None] = mapped_column(Date)
    top_up_amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    cumulative_commission: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    fraud_flagged: Mapped[bool] = mapped_column(default=False, nullable=False)
    fraud_reason: Mapped[str | None] = mapped_column(Text)
    match_status: Mapped[ReconciliationMatchStatus] = mapped_column(
        SAEnum(
            ReconciliationMatchStatus,
            name="reconciliation_match_status_enum",
            native_enum=False,
            create_constraint=True,
        ),
        nullable=False,
    )


class AuditLog(TenantMixin, Base):
    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("ix_audit_logs_dealer_entity", "dealer_id", "entity_type", "entity_id"),
        Index("ix_audit_logs_dealer_actor_created", "dealer_id", "actor_user_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    actor_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    action: Mapped[str] = mapped_column(String(128), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(128), nullable=False)
    entity_id: Mapped[int | None] = mapped_column(Integer)
    metadata_json: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class RefreshToken(TenantMixin, Base):
    __tablename__ = "refresh_tokens"
    __table_args__ = (
        UniqueConstraint("token_hash", name="uq_refresh_tokens_hash"),
        Index("ix_refresh_tokens_user_active", "dealer_id", "user_id", "revoked_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    replaced_by_id: Mapped[int | None] = mapped_column(ForeignKey("refresh_tokens.id", ondelete="SET NULL"))


class PasswordResetToken(TenantMixin, Base):
    __tablename__ = "password_reset_tokens"
    __table_args__ = (
        UniqueConstraint("token", name="uq_password_reset_tokens_token"),
        Index("ix_password_reset_tokens_user", "user_id"),
        Index("ix_password_reset_tokens_expires", "expires_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
