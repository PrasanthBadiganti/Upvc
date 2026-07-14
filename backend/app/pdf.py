from __future__ import annotations

from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from .models import Invoice


def build_invoice_pdf(invoice: Invoice) -> bytes:
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=14 * mm, leftMargin=14 * mm, topMargin=12 * mm, bottomMargin=12 * mm)
    styles = getSampleStyleSheet()
    story = [
        Paragraph("UPVC Pro", styles["Title"]),
        Paragraph("Windows. Doors. Trust.", styles["Normal"]),
        Spacer(1, 8),
        Paragraph(f"Invoice {invoice.number}", styles["Heading1"]),
        Paragraph(f"Customer: {invoice.customer.name}", styles["Normal"]),
        Paragraph(f"Project: {invoice.customer.project_site}", styles["Normal"]),
        Paragraph(f"Invoice date: {invoice.invoice_date} &nbsp;&nbsp; Due date: {invoice.due_date}", styles["Normal"]),
        Spacer(1, 12),
    ]
    rows = [["#", "Description", "Category", "Qty", "Rate", "GST", "Amount"]]
    for i, item in enumerate(invoice.items, 1):
        rows.append([str(i), item.description, item.category, f"{item.quantity}", f"Rs. {item.rate:,.2f}", f"{item.gst_percent}%", f"Rs. {item.amount:,.2f}"])
    rows.extend([
        ["", "", "", "", "", "Subtotal", f"Rs. {invoice.subtotal:,.2f}"],
        ["", "", "", "", "", "CGST", f"Rs. {invoice.cgst:,.2f}"],
        ["", "", "", "", "", "SGST", f"Rs. {invoice.sgst:,.2f}"],
        ["", "", "", "", "", "Grand Total", f"Rs. {invoice.grand_total:,.2f}"],
        ["", "", "", "", "", "Paid", f"Rs. {invoice.paid_amount:,.2f}"],
        ["", "", "", "", "", "Balance", f"Rs. {invoice.pending_balance:,.2f}"],
    ])
    table = Table(rows, colWidths=[10 * mm, 57 * mm, 26 * mm, 18 * mm, 23 * mm, 18 * mm, 28 * mm])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eaf2ff")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#17325c")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#d8e1ec")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (3, 1), (-1, -1), "RIGHT"),
        ("BACKGROUND", (5, -3), (-1, -1), colors.HexColor("#f8fafc")),
        ("FONTNAME", (5, -3), (-1, -1), "Helvetica-Bold"),
    ]))
    story.extend([table, Spacer(1, 14), Paragraph("Payment terms: 50% advance, 40% before delivery, 10% after installation.", styles["Normal"])])
    doc.build(story)
    return buffer.getvalue()
