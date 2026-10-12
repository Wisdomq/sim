"""Reporting services (Phase 9, FR-RPT-01/02/03, B-09-01/04)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import select, func, and_
from sqlalchemy.orm import Session

from simcards_backend.models import (
    AccountStatus,
    Branch,
    BrandAmbassador,
    PeriodType,
    PerformanceSnapshot,
    ReconciliationResult,
    Role,
    SafaricomImport,
    SaleEvent,
    SimCard,
    SimStatus,
    SubjectType,
    User,
)
from simcards_backend.schemas.reports import (
    BASalesSummary,
    BranchReportData,
    ReconciliationHeadlines,
    StockCountsByStatus,
)


@dataclass(frozen=True)
class ReportContext:
    """Context for report generation based on user role and scope."""

    dealer_id: int
    user_role: Role
    user_branch_id: int | None
    user_ba_profile_id: int | None
    branch_filter: int | None  # HQ-only branch filter


def get_report_context(actor: User, branch_filter: int | None = None) -> ReportContext:
    """Create a report context based on the current user's role and permissions."""
    if actor.role == Role.HQ:
        return ReportContext(
            dealer_id=actor.dealer_id,
            user_role=actor.role,
            user_branch_id=None,
            user_ba_profile_id=None,
            branch_filter=branch_filter,
        )
    elif actor.role == Role.BRANCH:
        if branch_filter is not None and branch_filter != actor.branch_id:
            raise ValueError("Branch users can only view their own branch's data")
        return ReportContext(
            dealer_id=actor.dealer_id,
            user_role=actor.role,
            user_branch_id=actor.branch_id,
            user_ba_profile_id=None,
            branch_filter=actor.branch_id,
        )
    else:
        raise ValueError("BA users do not have reporting access")


def get_stock_counts_by_status(
    db: Session,
    *,
    dealer_id: int,
    branch_id: int | None = None,
) -> StockCountsByStatus:
    """
    Get stock counts broken down by status for a dealer or specific branch.

    Args:
        db: Database session
        dealer_id: The dealer ID
        branch_id: Optional branch ID to filter by

    Returns:
        StockCountsByStatus with counts for each status
    """
    query = select(SimCard.status, func.count(SimCard.id)).where(
        SimCard.dealer_id == dealer_id
    )
    if branch_id is not None:
        query = query.where(SimCard.current_branch_id == branch_id)

    result = db.execute(query.group_by(SimCard.status)).all()

    counts = {status: 0 for status in SimStatus}
    for status, count in result:
        counts[status] = count

    return StockCountsByStatus(
        in_hq_stock=counts.get(SimStatus.IN_HQ_STOCK, 0),
        with_branch=counts.get(SimStatus.WITH_BRANCH, 0),
        with_ba=counts.get(SimStatus.WITH_BA, 0),
        sold=counts.get(SimStatus.SOLD, 0),
        returned_to_branch=counts.get(SimStatus.RETURNED_TO_BRANCH, 0),
        returned_to_hq=counts.get(SimStatus.RETURNED_TO_HQ, 0),
        expired=counts.get(SimStatus.EXPIRED, 0),
    )


def get_sales_summary_for_branch(
    db: Session,
    *,
    dealer_id: int,
    branch_id: int,
    period_start: date,
    period_end: date,
) -> dict:
    """
    Get sales summary for a specific branch within a period.

    Args:
        db: Database session
        dealer_id: The dealer ID
        branch_id: The branch ID
        period_start: Start of the period
        period_end: End of the period

    Returns:
        Dict with sales count and commission total
    """
    sales_count = (
        db.scalar(
            select(func.count(SaleEvent.id))
            .where(
                and_(
                    SaleEvent.dealer_id == dealer_id,
                    SaleEvent.branch_id == branch_id,
                    SaleEvent.sold_at >= datetime.combine(period_start, datetime.min.time()),
                    SaleEvent.sold_at <= datetime.combine(period_end, datetime.max.time()),
                )
            )
        )
        or 0
    )

    commission_total = (
        db.scalar(
            select(func.sum(SaleEvent.commission_amount))
            .where(
                and_(
                    SaleEvent.dealer_id == dealer_id,
                    SaleEvent.branch_id == branch_id,
                    SaleEvent.sold_at >= datetime.combine(period_start, datetime.min.time()),
                    SaleEvent.sold_at <= datetime.combine(period_end, datetime.max.time()),
                )
            )
        )
        or Decimal("0")
    )

    return {
        "sales_count": sales_count,
        "commission_total": commission_total,
    }


def get_ba_sales_summaries(
    db: Session,
    *,
    dealer_id: int,
    branch_id: int,
    period_type: PeriodType,
    period_start: date,
    period_end: date,
) -> list[BASalesSummary]:
    """
    Get sales summaries for all BAs in a branch within a period.

    Args:
        db: Database session
        dealer_id: The dealer ID
        branch_id: The branch ID
        period_type: Snapshot period type (DAILY/WEEKLY/MONTHLY)
        period_start: Start of the period
        period_end: End of the period

    Returns:
        List of BASalesSummary for each BA
    """
    # Get all active BAs in the branch (flagged-inactive accounts still count)
    bas = db.scalars(
        select(BrandAmbassador).where(
            and_(
                BrandAmbassador.dealer_id == dealer_id,
                BrandAmbassador.branch_id == branch_id,
                BrandAmbassador.status != AccountStatus.DISABLED,
            )
        )
    ).all()

    summaries = []
    for ba in bas:
        # Get sales count for this BA
        sales_count = (
            db.scalar(
                select(func.count(SaleEvent.id))
                .where(
                    and_(
                        SaleEvent.dealer_id == dealer_id,
                        SaleEvent.ba_id == ba.id,
                        SaleEvent.sold_at >= datetime.combine(period_start, datetime.min.time()),
                        SaleEvent.sold_at <= datetime.combine(period_end, datetime.max.time()),
                    )
                )
            )
            or 0
        )

        # Get commission total for this BA
        commission_total = (
            db.scalar(
                select(func.sum(SaleEvent.commission_amount))
                .where(
                    and_(
                        SaleEvent.dealer_id == dealer_id,
                        SaleEvent.ba_id == ba.id,
                        SaleEvent.sold_at >= datetime.combine(period_start, datetime.min.time()),
                        SaleEvent.sold_at <= datetime.combine(period_end, datetime.max.time()),
                    )
                )
            )
            or Decimal("0")
        )

        # Get performance percentage from snapshot
        snapshot = db.scalar(
            select(PerformanceSnapshot).where(
                and_(
                    PerformanceSnapshot.dealer_id == dealer_id,
                    PerformanceSnapshot.subject_type == SubjectType.BA,
                    PerformanceSnapshot.subject_id == ba.id,
                    PerformanceSnapshot.period_type == period_type,
                    PerformanceSnapshot.period_start == period_start,
                    PerformanceSnapshot.period_end == period_end,
                )
            )
        )

        performance_percentage = snapshot.percentage_achieved if snapshot else Decimal("0")

        summaries.append(
            BASalesSummary(
                ba_id=ba.id,
                ba_name=ba.name,
                sales_count=sales_count,
                commission_owed=commission_total,
                performance_percentage=performance_percentage,
            )
        )

    return summaries


def get_branch_performance_percentage(
    db: Session,
    *,
    dealer_id: int,
    branch_id: int,
    period_type: PeriodType,
    period_start: date,
    period_end: date,
) -> Decimal:
    """
    Get performance percentage for a branch within a period.

    Args:
        db: Database session
        dealer_id: The dealer ID
        branch_id: The branch ID
        period_type: Snapshot period type (DAILY/WEEKLY/MONTHLY)
        period_start: Start of the period
        period_end: End of the period

    Returns:
        Performance percentage as Decimal
    """
    snapshot = db.scalar(
        select(PerformanceSnapshot).where(
            and_(
                PerformanceSnapshot.dealer_id == dealer_id,
                PerformanceSnapshot.subject_type == SubjectType.BRANCH,
                PerformanceSnapshot.subject_id == branch_id,
                PerformanceSnapshot.period_type == period_type,
                PerformanceSnapshot.period_start == period_start,
                PerformanceSnapshot.period_end == period_end,
            )
        )
    )

    return snapshot.percentage_achieved if snapshot else Decimal("0")


def get_reconciliation_headlines(
    db: Session,
    *,
    dealer_id: int,
    period_start: date,
    period_end: date,
) -> ReconciliationHeadlines | None:
    """
    Get reconciliation headline numbers for a period if imports exist.

    Args:
        db: Database session
        dealer_id: The dealer ID
        period_start: Start of the period
        period_end: End of the period

    Returns:
        ReconciliationHeadlines if imports exist, None otherwise
    """
    # Find Safaricom imports within the period
    imports = db.scalars(
        select(SafaricomImport).where(
            and_(
                SafaricomImport.dealer_id == dealer_id,
                SafaricomImport.report_date >= period_start,
                SafaricomImport.report_date <= period_end,
                SafaricomImport.status == "COMPLETED",
            )
        )
    ).all()

    if not imports:
        return None

    # Aggregate reconciliation results from all imports in the period
    total_confirmed_activated = 0
    total_cumulative_commission = Decimal("0")
    total_fraud_flagged = 0
    unmatched_sold_not_in_safaricom = 0
    unmatched_in_safaricom_not_sold = 0

    for import_record in imports:
        result = db.scalar(
            select(ReconciliationResult).where(
                ReconciliationResult.safaricom_import_id == import_record.id
            )
        )
        if result:
            total_confirmed_activated += result.total_confirmed_activated_by_safaricom
            total_cumulative_commission += result.total_cumulative_commission
            total_fraud_flagged += result.total_fraud_flagged
            unmatched_sold_not_in_safaricom += result.unmatched_sold_not_in_safaricom_count
            unmatched_in_safaricom_not_sold += result.unmatched_in_safaricom_not_sold_in_app_count

    return ReconciliationHeadlines(
        total_confirmed_activated_by_safaricom=total_confirmed_activated,
        total_cumulative_commission=total_cumulative_commission,
        total_fraud_flagged=total_fraud_flagged,
        unmatched_sold_not_in_safaricom_count=unmatched_sold_not_in_safaricom,
        unmatched_in_safaricom_not_sold_in_app_count=unmatched_in_safaricom_not_sold,
    )


def generate_branch_report(
    db: Session,
    *,
    dealer_id: int,
    branch_id: int,
    period_type: str,
    period_start: date,
    period_end: date,
) -> BranchReportData:
    """
    Generate a complete report for a single branch.

    Args:
        db: Database session
        dealer_id: The dealer ID
        branch_id: The branch ID
        period_type: Period type string (DAILY/WEEKLY/MONTHLY)
        period_start: Start of the period
        period_end: End of the period

    Returns:
        BranchReportData with all branch-level metrics
    """
    period_type_enum = PeriodType(period_type)

    branch = db.scalar(
        select(Branch).where(
            and_(
                Branch.dealer_id == dealer_id,
                Branch.id == branch_id,
            )
        )
    )

    if branch is None:
        raise ValueError(f"Branch {branch_id} not found")

    stock_counts = get_stock_counts_by_status(db, dealer_id=dealer_id, branch_id=branch_id)
    sales_summary = get_sales_summary_for_branch(
        db, dealer_id=dealer_id, branch_id=branch_id, period_start=period_start, period_end=period_end
    )
    ba_summaries = get_ba_sales_summaries(
        db, dealer_id=dealer_id, branch_id=branch_id, period_type=period_type_enum, period_start=period_start, period_end=period_end
    )
    performance_percentage = get_branch_performance_percentage(
        db, dealer_id=dealer_id, branch_id=branch_id, period_type=period_type_enum, period_start=period_start, period_end=period_end
    )

    return BranchReportData(
        branch_id=branch.id,
        branch_name=branch.name,
        stock_counts=stock_counts,
        total_sales_count=sales_summary["sales_count"],
        total_commission_owed=sales_summary["commission_total"],
        performance_percentage=performance_percentage,
        ba_summaries=ba_summaries,
    )


def generate_report(
    db: Session,
    *,
    context: ReportContext,
    period_type: str,
    period_start: date,
    period_end: date,
) -> dict:
    """
    Generate a comprehensive report based on user role and permissions.

    Args:
        db: Database session
        context: Report context with user role and scoping
        period_type: DAILY, WEEKLY, or MONTHLY
        period_start: Start of the period
        period_end: End of the period

    Returns:
        Dict with complete report data
    """
    # Determine which branches to include
    if context.user_role == Role.BRANCH:
        branch_ids = [context.user_branch_id]
    elif context.user_role == Role.HQ:
        if context.branch_filter:
            branch_ids = [context.branch_filter]
        else:
            # HQ sees all branches
            branch_ids = [
                branch.id
                for branch in db.scalars(
                    select(Branch).where(Branch.dealer_id == context.dealer_id)
                ).all()
            ]
    else:
        raise ValueError("Invalid user role for reporting")

    # Generate branch reports
    branch_reports = []
    total_sales_count = 0
    total_commission_owed = Decimal("0")

    for branch_id in branch_ids:
        try:
            branch_report = generate_branch_report(
                db,
                dealer_id=context.dealer_id,
                branch_id=branch_id,
                period_type=period_type,
                period_start=period_start,
                period_end=period_end,
            )
            branch_reports.append(branch_report)
            total_sales_count += branch_report.total_sales_count
            total_commission_owed += branch_report.total_commission_owed
        except ValueError:
            # Skip branches that don't exist
            continue

    # Get total stock counts (dealer-wide or branch-specific)
    total_stock_counts = get_stock_counts_by_status(
        db,
        dealer_id=context.dealer_id,
        branch_id=context.branch_filter if context.user_role == Role.HQ else context.user_branch_id,
    )

    # Get overall performance percentage
    overall_performance = Decimal("0")
    if context.user_role == Role.HQ and not context.branch_filter:
        # HQ overall performance
        snapshot = db.scalar(
            select(PerformanceSnapshot).where(
                and_(
                    PerformanceSnapshot.dealer_id == context.dealer_id,
                    PerformanceSnapshot.subject_type == SubjectType.DEALER,
                    PerformanceSnapshot.subject_id == context.dealer_id,
                    PerformanceSnapshot.period_type == PeriodType(period_type),
                    PerformanceSnapshot.period_start == period_start,
                    PerformanceSnapshot.period_end == period_end,
                )
            )
        )
        overall_performance = snapshot.percentage_achieved if snapshot else Decimal("0")
    elif branch_reports:
        # Use the first (and only) branch's performance for Branch users
        overall_performance = branch_reports[0].performance_percentage

    # Get reconciliation headlines if available
    reconciliation_headlines = get_reconciliation_headlines(
        db,
        dealer_id=context.dealer_id,
        period_start=period_start,
        period_end=period_end,
    )

    return {
        "period_type": period_type,
        "period_start": period_start,
        "period_end": period_end,
        "total_stock_counts": total_stock_counts,
        "total_sales_count": total_sales_count,
        "total_commission_owed": total_commission_owed,
        "overall_performance_percentage": overall_performance,
        "branch_reports": branch_reports,
        "reconciliation_headlines": reconciliation_headlines,
        "generated_at": datetime.now().isoformat(),
    }
