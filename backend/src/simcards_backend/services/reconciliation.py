"""Safaricom reconciliation services (design §6.6, FR-REC-01..05, B-08-02..06).

Matching is performed per SIM serial only (FR-REC-04 / B-08-06): the Safaricom
report's Agent MSISDN / BA columns are intentionally never read.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from simcards_backend.models import (
    ReconciliationLineDetail,
    ReconciliationMatchStatus,
    ReconciliationResult,
    SafaricomImport,
    SaleEvent,
    SimCard,
)
from simcards_backend.services.audit import write_audit_log


@dataclass(frozen=True)
class ParsedSafaricomRow:
    serial_number: str
    top_up_date: date | None
    top_up_amount: Decimal | None
    cumulative_commission: Decimal | None
    fraud_flagged: bool
    fraud_reason: str | None


@dataclass(frozen=True)
class _SerialAggregate:
    top_up_date: date | None
    top_up_amount: Decimal | None
    cumulative_commission: Decimal | None
    fraud_flagged: bool
    fraud_reason: str | None


def _aggregate_file_rows(rows: list[ParsedSafaricomRow]) -> _SerialAggregate:
    """Collapse multiple Safaricom rows for the same serial into one aggregate."""
    top_up_dates = [row.top_up_date for row in rows if row.top_up_date is not None]
    top_up_amounts = [row.top_up_amount for row in rows if row.top_up_amount is not None]
    commissions = [
        row.cumulative_commission for row in rows if row.cumulative_commission is not None
    ]
    fraud_reasons = [row.fraud_reason for row in rows if row.fraud_flagged and row.fraud_reason]
    return _SerialAggregate(
        top_up_date=max(top_up_dates) if top_up_dates else None,
        top_up_amount=sum(top_up_amounts, Decimal("0")) if top_up_amounts else None,
        cumulative_commission=sum(commissions, Decimal("0")) if commissions else None,
        fraud_flagged=any(row.fraud_flagged for row in rows),
        fraud_reason=fraud_reasons[0] if fraud_reasons else None,
    )


def _has_top_up(aggregate: _SerialAggregate) -> bool:
    return aggregate.top_up_date is not None or aggregate.top_up_amount is not None


def list_activated_serials_for_month(
    db: Session,
    *,
    dealer_id: int,
    month_start: date,
    month_end: date,
) -> list[ReconciliationLineDetail]:
    """Return serials activated (top-up dated) within a calendar month across all imports.

    Serials appearing in more than one uploaded file within the same month are
    returned once, using the row with the latest top-up date.
    """
    rows = db.scalars(
        select(ReconciliationLineDetail)
        .where(
            ReconciliationLineDetail.dealer_id == dealer_id,
            ReconciliationLineDetail.top_up_date >= month_start,
            ReconciliationLineDetail.top_up_date < month_end,
        )
        .order_by(ReconciliationLineDetail.top_up_date, ReconciliationLineDetail.id)
    ).all()

    by_serial: dict[str, ReconciliationLineDetail] = {}
    for row in rows:
        if row.serial_number:
            by_serial[row.serial_number] = row
    return list(by_serial.values())


def reconcile_safaricom_import(
    db: Session,
    *,
    safaricom_import: SafaricomImport,
    rows: list[ParsedSafaricomRow],
    as_of: datetime | None = None,
) -> ReconciliationResult:
    """
    Match internal app sales against parsed Safaricom report rows and materialize
    the ReconciliationResult + ReconciliationLineDetail rows.

    Matching per design §6.6:
      - Sold in app and present in the file with a Top Up Date/Amount  -> MATCHED
      - Sold in app but absent from the file, or present without a top-up
                                                                        -> SOLD_NOT_ACTIVATED
      - Present in the file but not sold in app                        -> ACTIVATED_NOT_RECORDED_SOLD

    Headline numbers (FR-REC-02 / AC-4) are placed on the ReconciliationResult;
    per-serial detail is only ever exposed via the drill-down endpoint.
    """
    dealer_id = safaricom_import.dealer_id

    # Idempotent retry: wipe any prior result for this import before re-running.
    existing_result = db.scalar(
        select(ReconciliationResult).where(
            ReconciliationResult.safaricom_import_id == safaricom_import.id
        )
    )
    if existing_result is not None:
        db.execute(
            delete(ReconciliationLineDetail).where(
                ReconciliationLineDetail.reconciliation_result_id == existing_result.id
            )
        )
        db.execute(
            delete(ReconciliationResult).where(ReconciliationResult.id == existing_result.id)
        )

    file_rows_by_serial: dict[str, list[ParsedSafaricomRow]] = {}
    for row in rows:
        file_rows_by_serial.setdefault(row.serial_number, []).append(row)

    sold_serials = {
        serial
        for (serial,) in db.execute(
            select(SimCard.serial_number)
            .join(SaleEvent, SaleEvent.sim_card_id == SimCard.id)
            .where(SimCard.dealer_id == dealer_id)
        ).all()
    }

    all_serials = set(file_rows_by_serial) | sold_serials
    sim_id_by_serial: dict[str, int | None] = {serial: None for serial in sold_serials}
    if all_serials:
        for serial, sim_card_id in db.execute(
            select(SimCard.serial_number, SimCard.id).where(
                SimCard.dealer_id == dealer_id,
                SimCard.serial_number.in_(all_serials),
            )
        ).all():
            sim_id_by_serial[serial] = sim_card_id

    line_specs: list[
        tuple[
            str,
            int | None,
            _SerialAggregate | None,
            ReconciliationMatchStatus,
        ]
    ] = []

    for serial, file_rows in file_rows_by_serial.items():
        aggregate = _aggregate_file_rows(file_rows)
        if serial in sold_serials:
            match_status = (
                ReconciliationMatchStatus.MATCHED
                if _has_top_up(aggregate)
                else ReconciliationMatchStatus.SOLD_NOT_ACTIVATED
            )
        else:
            match_status = ReconciliationMatchStatus.ACTIVATED_NOT_RECORDED_SOLD
        line_specs.append((serial, sim_id_by_serial.get(serial), aggregate, match_status))

    for serial in sold_serials - set(file_rows_by_serial):
        line_specs.append(
            (serial, sim_id_by_serial.get(serial), None, ReconciliationMatchStatus.SOLD_NOT_ACTIVATED)
        )

    matched_count = 0
    sold_not_activated_count = 0
    activated_not_recorded_sold_count = 0
    matched_commission = Decimal("0")
    matched_fraud_count = 0
    topped_up_serial_count = 0

    for serial, sim_card_id, aggregate, match_status in line_specs:
        if match_status == ReconciliationMatchStatus.MATCHED:
            matched_count += 1
            assert aggregate is not None
            if aggregate.cumulative_commission is not None:
                matched_commission += aggregate.cumulative_commission
            if aggregate.fraud_flagged:
                matched_fraud_count += 1
        elif match_status == ReconciliationMatchStatus.SOLD_NOT_ACTIVATED:
            sold_not_activated_count += 1
        else:
            activated_not_recorded_sold_count += 1

    for serial, file_rows in file_rows_by_serial.items():
        aggregate = _aggregate_file_rows(file_rows)
        if _has_top_up(aggregate):
            topped_up_serial_count += 1

    result_kwargs = dict(
        dealer_id=dealer_id,
        safaricom_import_id=safaricom_import.id,
        total_sold_in_app=len(sold_serials),
        total_confirmed_activated_by_safaricom=matched_count,
        total_topped_up=topped_up_serial_count,
        total_cumulative_commission=matched_commission,
        total_fraud_flagged=matched_fraud_count,
        unmatched_sold_not_in_safaricom_count=sold_not_activated_count,
        unmatched_in_safaricom_not_sold_in_app_count=activated_not_recorded_sold_count,
    )
    if as_of is not None:
        result_kwargs["generated_at"] = as_of
    result = ReconciliationResult(**result_kwargs)
    db.add(result)
    db.flush()

    for serial, sim_card_id, aggregate, match_status in line_specs:
        db.add(
            ReconciliationLineDetail(
                dealer_id=dealer_id,
                reconciliation_result_id=result.id,
                sim_card_id=sim_card_id,
                serial_number=serial,
                top_up_date=aggregate.top_up_date if aggregate else None,
                top_up_amount=aggregate.top_up_amount if aggregate else None,
                cumulative_commission=aggregate.cumulative_commission if aggregate else None,
                fraud_flagged=aggregate.fraud_flagged if aggregate else False,
                fraud_reason=aggregate.fraud_reason if aggregate else None,
                match_status=match_status,
            )
        )

    write_audit_log(
        db,
        dealer_id=dealer_id,
        actor_user_id=None,
        action="SAFARICOM_RECONCILIATION",
        entity_type="SafaricomImport",
        entity_id=safaricom_import.id,
        metadata={
            "total_sold_in_app": len(sold_serials),
            "total_confirmed_activated_by_safaricom": matched_count,
            "total_topped_up": topped_up_serial_count,
            "total_cumulative_commission": str(matched_commission),
            "total_fraud_flagged": matched_fraud_count,
            "unmatched_sold_not_in_safaricom_count": sold_not_activated_count,
            "unmatched_in_safaricom_not_sold_in_app_count": activated_not_recorded_sold_count,
        },
    )
    return result