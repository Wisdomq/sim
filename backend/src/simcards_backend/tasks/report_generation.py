"""Report generation tasks for PDF and Excel exports (Phase 9, B-09-02/03)."""

from __future__ import annotations

from datetime import date

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak

from simcards_backend.celery_app import celery_app
from simcards_backend.core.database import SessionLocal, set_tenant_context
from simcards_backend.models import User
from simcards_backend.schemas.reports import (
    BranchReportData,
    ReconciliationHeadlines,
    StockCountsByStatus,
)
from simcards_backend.services.audit import write_audit_log
from simcards_backend.services.reports import generate_report, get_report_context


def generate_pdf_report(
    report_data: dict,
    output_path: str,
) -> None:
    """
    Generate a formatted PDF report from report data.

    Args:
        report_data: Report data dictionary from generate_report service
        output_path: Path where the PDF should be saved
    """
    doc = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        rightMargin=72,
        leftMargin=72,
        topMargin=72,
        bottomMargin=18,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "CustomTitle",
        parent=styles["Heading1"],
        fontSize=18,
        textColor=colors.darkblue,
        spaceAfter=30,
    )
    heading_style = ParagraphStyle(
        "CustomHeading",
        parent=styles["Heading2"],
        fontSize=14,
        textColor=colors.darkblue,
        spaceAfter=12,
    )
    normal_style = styles["Normal"]

    story = []

    # Title
    period_type = report_data["period_type"]
    period_start = report_data["period_start"]
    period_end = report_data["period_end"]
    title = f"{period_type} Report ({period_start} to {period_end})"
    story.append(Paragraph(title, title_style))
    story.append(Spacer(1, 12))

    # Summary Section
    story.append(Paragraph("Executive Summary", heading_style))
    summary_data = [
        ["Metric", "Value"],
        ["Total Sales Count", str(report_data["total_sales_count"])],
        ["Total Commission Owed", f"KES {report_data['total_commission_owed']}"],
        ["Overall Performance %", f"{report_data['overall_performance_percentage']:.1f}%"],
    ]

    # Add stock counts
    stock_counts = report_data["total_stock_counts"]
    # Handle both dict and Pydantic model
    if hasattr(stock_counts, 'model_dump'):
        stock_dict = stock_counts.model_dump()
    else:
        stock_dict = stock_counts
    
    summary_data.extend([
        ["Stock in HQ", str(stock_dict.get("in_hq_stock", 0))],
        ["Stock with Branches", str(stock_dict.get("with_branch", 0))],
        ["Stock with BAs", str(stock_dict.get("with_ba", 0))],
        ["Sold SIMs", str(stock_dict.get("sold", 0))],
        ["Returned to Branch", str(stock_dict.get("returned_to_branch", 0))],
        ["Returned to HQ", str(stock_dict.get("returned_to_hq", 0))],
        ["Expired SIMs", str(stock_dict.get("expired", 0))],
    ])

    summary_table = Table(summary_data, colWidths=[2.5 * inch, 2 * inch])
    summary_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 12),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
        ("BACKGROUND", (0, 1), (-1, -1), colors.beige),
        ("GRID", (0, 0), (-1, -1), 1, colors.black),
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 24))

    # Reconciliation Section (if available)
    reconciliation_headlines = report_data.get("reconciliation_headlines")
    if reconciliation_headlines:
        story.append(Paragraph("Safaricom Reconciliation Summary", heading_style))
        
        # Handle both dict and Pydantic model
        if hasattr(reconciliation_headlines, 'model_dump'):
            recon_dict = reconciliation_headlines.model_dump()
        else:
            recon_dict = reconciliation_headlines
        
        recon_data = [
            ["Metric", "Value"],
            ["Confirmed Activated", str(recon_dict.get("total_confirmed_activated_by_safaricom", 0))],
            ["Cumulative Commission", f"KES {recon_dict.get('total_cumulative_commission', 0)}"],
            ["Fraud Flagged", str(recon_dict.get("total_fraud_flagged", 0))],
            ["Sold Not in Safaricom", str(recon_dict.get("unmatched_sold_not_in_safaricom_count", 0))],
            ["In Safaricom Not Sold", str(recon_dict.get("unmatched_in_safaricom_not_sold_in_app_count", 0))],
        ]

        recon_table = Table(recon_data, colWidths=[2.5 * inch, 2 * inch])
        recon_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
            ("ALIGN", (0, 0), (-1, -1), "LEFT"),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 12),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
            ("BACKGROUND", (0, 1), (-1, -1), colors.beige),
            ("GRID", (0, 0), (-1, -1), 1, colors.black),
        ]))
        story.append(recon_table)
        story.append(Spacer(1, 24))

    # Branch Details Section
    branch_reports = report_data["branch_reports"]
    if branch_reports:
        story.append(Paragraph("Branch Performance Details", heading_style))

        for branch_report in branch_reports:
            # Handle both dict and Pydantic model
            if hasattr(branch_report, 'model_dump'):
                branch_dict = branch_report.model_dump()
            else:
                branch_dict = branch_report
            
            story.append(Paragraph(f"Branch: {branch_dict.get('branch_name', 'Unknown')}", normal_style))
            story.append(Spacer(1, 6))

            branch_data = [
                ["Metric", "Value"],
                ["Sales Count", str(branch_dict.get("total_sales_count", 0))],
                ["Commission Owed", f"KES {branch_dict.get('total_commission_owed', 0)}"],
                ["Performance %", f"{branch_dict.get('performance_percentage', 0):.1f}%"],
            ]

            branch_table = Table(branch_data, colWidths=[2.5 * inch, 2 * inch])
            branch_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 10),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
                ("BACKGROUND", (0, 1), (-1, -1), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ]))
            story.append(branch_table)
            story.append(Spacer(1, 12))

            # BA Summaries for this branch
            ba_summaries = branch_dict.get("ba_summaries", [])
            if ba_summaries:
                story.append(Paragraph("Brand Ambassador Performance", normal_style))
                ba_data = [["BA Name", "Sales", "Commission", "Performance %"]]
                for ba_summary in ba_summaries:
                    # Handle both dict and Pydantic model for BA summary
                    if hasattr(ba_summary, 'model_dump'):
                        ba_dict = ba_summary.model_dump()
                    else:
                        ba_dict = ba_summary
                    
                    ba_data.append([
                        ba_dict.get("ba_name", ""),
                        str(ba_dict.get("sales_count", 0)),
                        f"KES {ba_dict.get('commission_owed', 0)}",
                        f"{ba_dict.get('performance_percentage', 0):.1f}%",
                    ])

                ba_table = Table(ba_data, colWidths=[2 * inch, 1 * inch, 1.5 * inch, 1 * inch])
                ba_table.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, 0), 9),
                    ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
                    ("BACKGROUND", (0, 1), (-1, -1), colors.white),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ]))
                story.append(ba_table)
                story.append(Spacer(1, 18))

            story.append(PageBreak())

    # Build the PDF
    doc.build(story)


def generate_excel_report(
    report_data: dict,
    output_path: str,
) -> None:
    """
    Generate an Excel report from report data.

    Args:
        report_data: Report data dictionary from generate_report service
        output_path: Path where the Excel file should be saved
    """
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Report"

    # Title
    period_type = report_data["period_type"]
    period_start = report_data["period_start"]
    period_end = report_data["period_end"]
    ws["A1"] = f"{period_type} Report ({period_start} to {period_end})"
    ws["A1"].font = Font(bold=True, size=14)
    ws.merge_cells("A1:D1")

    # Summary Section
    row = 3
    ws[f"A{row}"] = "Executive Summary"
    ws[f"A{row}"].font = Font(bold=True, size=12)
    row += 1

    summary_data = [
        ["Metric", "Value"],
        ["Total Sales Count", report_data.get("total_sales_count", 0)],
        ["Total Commission Owed", f"KES {report_data.get('total_commission_owed', 0)}"],
        ["Overall Performance %", f"{report_data.get('overall_performance_percentage', 0):.1f}%"],
    ]

    # Add stock counts
    stock_counts = report_data["total_stock_counts"]
    # Handle both dict and Pydantic model
    if hasattr(stock_counts, 'model_dump'):
        stock_dict = stock_counts.model_dump()
    else:
        stock_dict = stock_counts
    
    summary_data.extend([
        ["Stock in HQ", stock_dict.get("in_hq_stock", 0)],
        ["Stock with Branches", stock_dict.get("with_branch", 0)],
        ["Stock with BAs", stock_dict.get("with_ba", 0)],
        ["Sold SIMs", stock_dict.get("sold", 0)],
        ["Returned to Branch", stock_dict.get("returned_to_branch", 0)],
        ["Returned to HQ", stock_dict.get("returned_to_hq", 0)],
        ["Expired SIMs", stock_dict.get("expired", 0)],
    ])

    for i, (metric, value) in enumerate(summary_data):
        ws[f"A{row}"] = metric
        ws[f"B{row}"] = value
        if i == 0:  # Header row
            ws[f"A{row}"].font = Font(bold=True)
            ws[f"B{row}"].font = Font(bold=True)
            ws[f"A{row}"].fill = PatternFill(start_color="D3D3D3", end_color="D3D3D3", fill_type="solid")
            ws[f"B{row}"].fill = PatternFill(start_color="D3D3D3", end_color="D3D3D3", fill_type="solid")
        row += 1

    row += 1

    # Reconciliation Section (if available)
    reconciliation_headlines = report_data.get("reconciliation_headlines")
    if reconciliation_headlines:
        ws[f"A{row}"] = "Safaricom Reconciliation Summary"
        ws[f"A{row}"].font = Font(bold=True, size=12)
        row += 1

        # Handle both dict and Pydantic model
        if hasattr(reconciliation_headlines, 'model_dump'):
            recon_dict = reconciliation_headlines.model_dump()
        else:
            recon_dict = reconciliation_headlines
        
        recon_data = [
            ["Metric", "Value"],
            ["Confirmed Activated", recon_dict.get("total_confirmed_activated_by_safaricom", 0)],
            ["Cumulative Commission", f"KES {recon_dict.get('total_cumulative_commission', 0)}"],
            ["Fraud Flagged", recon_dict.get("total_fraud_flagged", 0)],
            ["Sold Not in Safaricom", recon_dict.get("unmatched_sold_not_in_safaricom_count", 0)],
            ["In Safaricom Not Sold", recon_dict.get("unmatched_in_safaricom_not_sold_in_app_count", 0)],
        ]

        for i, (metric, value) in enumerate(recon_data):
            ws[f"A{row}"] = metric
            ws[f"B{row}"] = value
            if i == 0:  # Header row
                ws[f"A{row}"].font = Font(bold=True)
                ws[f"B{row}"].font = Font(bold=True)
                ws[f"A{row}"].fill = PatternFill(start_color="D3D3D3", end_color="D3D3D3", fill_type="solid")
                ws[f"B{row}"].fill = PatternFill(start_color="D3D3D3", end_color="D3D3D3", fill_type="solid")
            row += 1

        row += 1

    # Branch Details Section
    branch_reports = report_data["branch_reports"]
    if branch_reports:
        ws[f"A{row}"] = "Branch Performance Details"
        ws[f"A{row}"].font = Font(bold=True, size=12)
        row += 2

        for branch_report in branch_reports:
            # Handle both dict and Pydantic model
            if hasattr(branch_report, 'model_dump'):
                branch_dict = branch_report.model_dump()
            else:
                branch_dict = branch_report
            
            branch_name = branch_dict.get("branch_name", "Unknown")
            ws[f"A{row}"] = f"Branch: {branch_name}"
            ws[f"A{row}"].font = Font(bold=True)
            row += 1

            branch_data = [
                ["Metric", "Value"],
                ["Sales Count", branch_dict.get("total_sales_count", 0)],
                ["Commission Owed", f"KES {branch_dict.get('total_commission_owed', 0)}"],
                ["Performance %", f"{branch_dict.get('performance_percentage', 0):.1f}%"],
            ]

            for i, (metric, value) in enumerate(branch_data):
                ws[f"A{row}"] = metric
                ws[f"B{row}"] = value
                if i == 0:  # Header row
                    ws[f"A{row}"].font = Font(bold=True)
                    ws[f"B{row}"].font = Font(bold=True)
                    ws[f"A{row}"].fill = PatternFill(start_color="E0E0E0", end_color="E0E0E0", fill_type="solid")
                    ws[f"B{row}"].fill = PatternFill(start_color="E0E0E0", end_color="E0E0E0", fill_type="solid")
                row += 1

            row += 1

            # BA Summaries for this branch
            ba_summaries = branch_dict.get("ba_summaries", [])
            if ba_summaries:
                ws[f"A{row}"] = "Brand Ambassador Performance"
                ws[f"A{row}"].font = Font(bold=True)
                row += 1

                ba_data = [["BA Name", "Sales", "Commission", "Performance %"]]
                for ba_summary in ba_summaries:
                    # Handle both dict and Pydantic model for BA summary
                    if hasattr(ba_summary, 'model_dump'):
                        ba_dict = ba_summary.model_dump()
                    else:
                        ba_dict = ba_summary
                    
                    ba_data.append([
                        ba_dict.get("ba_name", ""),
                        ba_dict.get("sales_count", 0),
                        f"KES {ba_dict.get('commission_owed', 0)}",
                        f"{ba_dict.get('performance_percentage', 0):.1f}%",
                    ])

                for i, ba_row in enumerate(ba_data):
                    ws[f"A{row}"] = ba_row[0]
                    ws[f"B{row}"] = ba_row[1]
                    ws[f"C{row}"] = ba_row[2]
                    ws[f"D{row}"] = ba_row[3]
                    if i == 0:  # Header row
                        for col in ["A", "B", "C", "D"]:
                            ws[f"{col}{row}"].font = Font(bold=True)
                            ws[f"{col}{row}"].fill = PatternFill(start_color="E0E0E0", end_color="E0E0E0", fill_type="solid")
                    row += 1

            row += 2

    # Auto-adjust column widths (skip merged cells)
    for column in ws.columns:
        max_length = 0
        column_letter = None
        for cell in column:
            try:
                # Skip merged cells
                if cell.coordinate in ws.merged_cells.ranges:
                    continue
                if column_letter is None:
                    column_letter = cell.column_letter
                if len(str(cell.value)) > max_length:
                    max_length = len(str(cell.value))
            except:
                pass
        if column_letter:
            adjusted_width = min(max_length + 2, 50)
            ws.column_dimensions[column_letter].width = adjusted_width

    # Save the workbook
    wb.save(output_path)


@celery_app.task(bind=True)
def generate_report_export(
    self,
    *,
    dealer_id: int,
    actor_user_id: int,
    branch_filter: int | None,
    period_type: str,
    period_start: str,
    period_end: str,
    export_format: str,
    file_path: str,
) -> dict:
    """
    Generate a PDF/Excel report export asynchronously (B-09-02/03).

    Re-derives the report scope from the actor user for tenant safety and writes
    a REPORT_EXPORT_GENERATED audit log entry on success. Runs as a Celery task;
    callers receive a task id and a destination file path.
    """
    format_key = export_format.upper()

    with SessionLocal() as db:
        try:
            set_tenant_context(db, dealer_id)
            actor = db.get(User, actor_user_id)
            if actor is None:
                raise RuntimeError(f"Actor user {actor_user_id} not found")

            context = get_report_context(actor, branch_filter=branch_filter)
            report_data = generate_report(
                db,
                context=context,
                period_type=period_type,
                period_start=date.fromisoformat(period_start),
                period_end=date.fromisoformat(period_end),
            )

            if format_key == "XLSX":
                generate_excel_report(report_data, file_path)
            else:
                generate_pdf_report(report_data, file_path)

            write_audit_log(
                db,
                dealer_id=dealer_id,
                actor_user_id=actor_user_id,
                action="REPORT_EXPORT_GENERATED",
                entity_type="Report",
                entity_id=None,
                metadata={
                    "period_type": period_type,
                    "period_start": period_start,
                    "period_end": period_end,
                    "export_format": format_key,
                    "file_path": file_path,
                    "branch_filter": branch_filter,
                },
            )
            db.commit()
            return {"status": "completed", "file_path": file_path}
        except Exception as exc:
            db.rollback()
            return {"status": "failed", "message": str(exc)}
