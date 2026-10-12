"""Excel parsing for Safaricom reconciliation reports (B-08-02).

Parses a Safaricom daily line-connection xlsx report into normalized rows for
the reconciliation service. Column names are resolved defensively so minor
header drift does not break the import.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal, InvalidOperation

import openpyxl

from simcards_backend.services.reconciliation import ParsedSafaricomRow

MISSING_VALUE = "-"

FIELD_CANDIDATES: dict[str, tuple[str, ...]] = {
    "serial_number": ("sim serial number", "serial number", "serial", "sim serial"),
    "top_up_date": ("top up date", "topup date", "top up day"),
    "top_up_amount": ("top up amount", "topup amount", "topup"),
    "cumulative_commission": ("cumulative commission", "commission"),
    "fraud_flagged": ("fraud flagged", "fraud flag"),
    "fraud_reason": ("fraud reason",),
}


def _normalize_header(value: object) -> str:
    return str(value).strip().lower().replace("  ", " ") if value is not None else ""


def _find_field_columns(header_row: tuple[object, ...]) -> dict[str, int]:
    """Map each known field to its column index based on header names."""
    normalized_headers = [(idx, _normalize_header(cell)) for idx, cell in enumerate(header_row)]
    column_indices: dict[str, int] = {}

    for field, candidates in FIELD_CANDIDATES.items():
        found = None
        for idx, header in normalized_headers:
            if header in candidates:
                found = idx
                break
        if found is None:
            for idx, header in normalized_headers:
                if any(candidate in header for candidate in candidates):
                    found = idx
                    break
        column_indices[field] = found

    if column_indices["serial_number"] is None:
        headers = [header for _, header in normalized_headers]
        raise ValueError(f"Could not find a SIM serial number column in headers: {headers!r}")
    return column_indices


def _parse_date(value: object) -> date | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value).strip()
    if not text or text == MISSING_VALUE:
        return None
    digits = "".join(ch for ch in text if ch.isdigit())
    if len(digits) == 8:
        return datetime.strptime(digits, "%Y%m%d").date()
    try:
        return datetime.fromisoformat(text).date()
    except ValueError:
        return None


def _parse_decimal(value: object) -> Decimal | None:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return value
    text = str(value).strip().replace(" ", "")
    if not text or text == MISSING_VALUE:
        return None
    try:
        return Decimal(text)
    except InvalidOperation:
        return None


def _parse_bool_flag(value: object) -> bool:
    if value is None:
        return False
    return str(value).strip().upper().startswith("Y")


def parse_safaricom_report_file(file_path: str) -> list[ParsedSafaricomRow]:
    """Parse a Safaricom line-connection xlsx report into normalized rows."""
    workbook = openpyxl.load_workbook(file_path, read_only=True, data_only=True)
    try:
        sheet = workbook.active
        rows = sheet.iter_rows(values_only=True)
        try:
            header_row = tuple(next(rows))
        except StopIteration:
            raise ValueError("The xlsx report is empty.")
        column_indices = _find_field_columns(header_row)

        serial_idx = column_indices["serial_number"]
        top_up_date_idx = column_indices["top_up_date"]
        top_up_amount_idx = column_indices["top_up_amount"]
        commission_idx = column_indices["cumulative_commission"]
        fraud_idx = column_indices["fraud_flagged"]
        fraud_reason_idx = column_indices["fraud_reason"]

        parsed: list[ParsedSafaricomRow] = []
        for row in rows:
            if row is None:
                continue
            serial_value = row[serial_idx] if serial_idx < len(row) else None
            serial_number = str(serial_value).strip() if serial_value is not None else ""
            if not serial_number:
                continue

            top_up_amount = _parse_decimal(row[top_up_amount_idx]) if top_up_amount_idx is not None else None
            top_up_date = _parse_date(row[top_up_date_idx]) if top_up_date_idx is not None else None
            cumulative_commission = (
                _parse_decimal(row[commission_idx]) if commission_idx is not None else None
            )
            fraud_flagged = _parse_bool_flag(row[fraud_idx]) if fraud_idx is not None else False
            fraud_value = row[fraud_reason_idx] if fraud_reason_idx is not None else None
            fraud_reason = (
                str(fraud_value).strip() if fraud_value is not None and str(fraud_value).strip() != MISSING_VALUE else None
            )

            parsed.append(
                ParsedSafaricomRow(
                    serial_number=serial_number,
                    top_up_date=top_up_date,
                    top_up_amount=top_up_amount,
                    cumulative_commission=cumulative_commission,
                    fraud_flagged=fraud_flagged,
                    fraud_reason=fraud_reason,
                )
            )
        return parsed
    finally:
        workbook.close()