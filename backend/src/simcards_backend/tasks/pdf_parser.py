"""PDF parsing tasks for Safaricom pick-list imports."""

from __future__ import annotations

from dataclasses import dataclass
import re

from simcards_backend.celery_app import celery_app
from simcards_backend.core.database import SessionLocal, set_tenant_context
from simcards_backend.models import StockBatchSource
from simcards_backend.services.stock import create_stock_batch_with_serials


@dataclass(frozen=True)
class PickListLot:
    source_reference: str
    serials: list[str]


LOT_MARKER_RE = re.compile(r"<<\s*Lot\s*>>\s*([A-Za-z0-9_-]+)?", re.IGNORECASE)
LOT_CODE_RE = re.compile(r"\b[A-Za-z0-9]+_[A-Za-z0-9_-]+\b")
SERIAL_RE = re.compile(r"(?<!\d)(\d{10,25})(?!\d)")


def parse_pick_list_text(text: str) -> list[PickListLot]:
    """Extract lots and SIM serials from text already extracted from a pick-list PDF."""
    lots: list[tuple[str, list[str]]] = []
    current_reference: str | None = None
    current_serials: list[str] = []
    pending_lot_marker = False

    def flush_current() -> None:
        nonlocal current_reference, current_serials
        if current_reference and current_serials:
            lots.append((current_reference, current_serials))
        current_reference = None
        current_serials = []

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        marker = LOT_MARKER_RE.search(line)
        if marker:
            flush_current()
            marker_reference = marker.group(1)
            current_reference = marker_reference.strip() if marker_reference else None
            pending_lot_marker = current_reference is None
            continue

        if pending_lot_marker:
            code_match = LOT_CODE_RE.search(line)
            if code_match:
                current_reference = code_match.group(0)
            else:
                candidate = line.split()[0].strip(":")
                current_reference = candidate if candidate and not candidate.isdigit() else "UNSPECIFIED_LOT"
            pending_lot_marker = False

        serials = SERIAL_RE.findall(line)
        if serials:
            if current_reference is None:
                current_reference = "UNSPECIFIED_LOT"
            current_serials.extend(serials)

    flush_current()

    deduped_lots: list[PickListLot] = []
    for reference, serials in lots:
        seen: set[str] = set()
        deduped_serials: list[str] = []
        for serial in serials:
            if serial not in seen:
                seen.add(serial)
                deduped_serials.append(serial)
        deduped_lots.append(PickListLot(source_reference=reference, serials=deduped_serials))
    return deduped_lots


def extract_pick_list_lots(file_path: str) -> list[PickListLot]:
    import pdfplumber

    extracted_text: list[str] = []
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            extracted_text.append(page.extract_text() or "")
    return parse_pick_list_text("\n".join(extracted_text))


@celery_app.task(bind=True)
def parse_pick_list_pdf(self, file_path: str, dealer_id: int, imported_by: int) -> dict:
    """
    Parse Safaricom pick-list PDF and extract SIM serial numbers.

    Args:
        file_path: Path to the uploaded PDF file
        dealer_id: ID of the dealer importing the stock
        imported_by: ID of the HQ user performing the import

    Returns:
        Dict with parsing results including stock batch IDs and SIM counts
    """
    lots = extract_pick_list_lots(file_path)
    if not lots:
        return {
            "status": "failed",
            "message": "No <<Lot>> blocks with SIM serials were found in the PDF.",
            "file_path": file_path,
        }

    results: list[dict] = []
    total_inserted = 0
    total_duplicates = 0
    with SessionLocal() as db:
        set_tenant_context(db, dealer_id)
        for lot in lots:
            outcome = create_stock_batch_with_serials(
                db,
                dealer_id=dealer_id,
                source=StockBatchSource.PDF_IMPORT,
                source_reference=lot.source_reference,
                serials=lot.serials,
                imported_by_id=imported_by,
            )
            total_inserted += outcome.inserted_count
            total_duplicates += outcome.duplicate_count
            results.append(
                {
                    "batch_id": outcome.batch_id,
                    "source_reference": outcome.source_reference,
                    "inserted_count": outcome.inserted_count,
                    "duplicate_count": outcome.duplicate_count,
                    "duplicates": outcome.duplicates,
                }
            )
        db.commit()

    return {
        "status": "completed",
        "file_path": file_path,
        "lot_count": len(results),
        "inserted_count": total_inserted,
        "duplicate_count": total_duplicates,
        "lots": results,
    }
