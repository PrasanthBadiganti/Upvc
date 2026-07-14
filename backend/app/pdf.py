from __future__ import annotations

from datetime import timedelta
from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from .models import Invoice, Payment, Quotation


def _money(value: object) -> str:
    return f"Rs. {value:,.2f}"


def _text(value: object) -> str:
    return escape(str(value or ""))


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
        rows.append([str(i), item.description, item.category, f"{item.quantity}", _money(item.rate), f"{item.gst_percent}%", _money(item.amount)])
    rows.extend([
        ["", "", "", "", "", "Subtotal", _money(invoice.subtotal)],
        ["", "", "", "", "", "CGST", _money(invoice.cgst)],
        ["", "", "", "", "", "SGST", _money(invoice.sgst)],
        ["", "", "", "", "", "Grand Total", _money(invoice.grand_total)],
        ["", "", "", "", "", "Paid", _money(invoice.paid_amount)],
        ["", "", "", "", "", "Balance", _money(invoice.pending_balance)],
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


def build_quotation_pdf(quotation: Quotation) -> bytes:
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=12 * mm, leftMargin=12 * mm, topMargin=12 * mm, bottomMargin=12 * mm)
    styles = getSampleStyleSheet()
    valid_until = quotation.quotation_date + timedelta(days=quotation.validity_days)
    story = [
        Paragraph("UPVC Pro", styles["Title"]),
        Paragraph("Windows. Doors. Trust.", styles["Normal"]),
        Spacer(1, 8),
        Paragraph(f"Quotation {_text(quotation.number)}", styles["Heading1"]),
        Paragraph(f"Customer: {_text(quotation.customer.name)}", styles["Normal"]),
        Paragraph(f"Phone: {_text(quotation.customer.phone)} &nbsp;&nbsp; Email: {_text(quotation.customer.email)}", styles["Normal"]),
        Paragraph(f"Project/Site: {_text(quotation.site_location or quotation.customer.project_site)}", styles["Normal"]),
        Paragraph(f"Address: {_text(quotation.address or quotation.customer.address)}", styles["Normal"]),
        Paragraph(f"Quotation date: {quotation.quotation_date} &nbsp;&nbsp; Validity: {quotation.validity_days} days &nbsp;&nbsp; Valid until: {valid_until}", styles["Normal"]),
        Paragraph(f"Sales person: {_text(quotation.sales_person)} &nbsp;&nbsp; Status: {_text(quotation.status)}", styles["Normal"]),
        Spacer(1, 12),
    ]
    rows = [["#", "Item", "Size", "SFT", "Qty", "Total SFT", "Rate", "Amount"]]
    for i, item in enumerate(quotation.items, 1):
        item_name = _text(f"{item.category} {item.style}".strip())
        material = _text(", ".join(filter(None, [item.profile, item.color, item.track, item.glass, item.glass_color, item.hardware, item.reinforcement, item.mesh])))
        rows.append([
            str(i),
            Paragraph(f"{item_name}<br/><font size='7'>{material}</font><br/><font size='7'>Location: {_text(item.location)}</font>", styles["BodyText"]),
            f"{item.width_mm} x {item.height_mm} mm",
            f"{item.sft}",
            str(item.quantity),
            f"{item.total_sft}",
            _money(item.rate_per_sft),
            _money(item.amount),
        ])
    rows.extend([
        ["", "", "", "", "", "", "Subtotal", _money(quotation.subtotal)],
        ["", "", "", "", "", "", "Transport", _money(quotation.transport)],
        ["", "", "", "", "", "", "Discount", _money(quotation.discount)],
        ["", "", "", "", "", "", "GST", _money(quotation.gst)],
        ["", "", "", "", "", "", "Grand Total", _money(quotation.grand_total)],
        ["", "", "", "", "", "", "Advance", _money(quotation.advance)],
        ["", "", "", "", "", "", "Balance", _money(quotation.balance)],
    ])
    table = Table(rows, colWidths=[8 * mm, 50 * mm, 29 * mm, 16 * mm, 12 * mm, 20 * mm, 24 * mm, 27 * mm])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eaf2ff")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#17325c")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#d8e1ec")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 7),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ALIGN", (2, 1), (-1, -1), "RIGHT"),
        ("BACKGROUND", (6, -7), (-1, -1), colors.HexColor("#f8fafc")),
        ("FONTNAME", (6, -7), (-1, -1), "Helvetica-Bold"),
    ]))
    story.extend([
        table,
        Spacer(1, 12),
        Paragraph("Terms: 50% advance with order confirmation, 40% before delivery, and 10% after installation.", styles["Normal"]),
        Paragraph("Notes: " + _text(quotation.notes or "Prices are subject to final site measurement and approved specifications."), styles["Normal"]),
    ])
    doc.build(story)
    return buffer.getvalue()


def build_payment_receipt_pdf(payment: Payment) -> bytes:
    invoice = payment.invoice
    paid_to_date = sum((row.amount for row in invoice.payments if row.created_at <= payment.created_at), start=0)
    balance_after = invoice.grand_total - paid_to_date

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=16 * mm, leftMargin=16 * mm, topMargin=14 * mm, bottomMargin=14 * mm)
    styles = getSampleStyleSheet()
    story = [
        Paragraph("UPVC Pro", styles["Title"]),
        Paragraph("Windows. Doors. Trust.", styles["Normal"]),
        Spacer(1, 10),
        Paragraph(f"Payment Receipt #{payment.id}", styles["Heading1"]),
        Paragraph(f"Invoice: {_text(invoice.number)}", styles["Normal"]),
        Paragraph(f"Customer: {_text(invoice.customer.name)}", styles["Normal"]),
        Paragraph(f"Project/Site: {_text(invoice.customer.project_site)}", styles["Normal"]),
        Paragraph(f"Receipt date: {payment.payment_date} &nbsp;&nbsp; Recorded on: {payment.created_at.strftime('%Y-%m-%d %H:%M')}", styles["Normal"]),
        Spacer(1, 12),
    ]
    rows = [
        ["Payment Mode", _text(payment.mode)],
        ["Reference Number", _text(payment.reference_number or "-")],
        ["Received By", _text(payment.received_by)],
        ["Amount Received", _money(payment.amount)],
        ["Invoice Total", _money(invoice.grand_total)],
        ["Paid To Date", _money(paid_to_date)],
        ["Balance After This Payment", _money(balance_after)],
    ]
    table = Table(rows, colWidths=[58 * mm, 112 * mm])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#eaf2ff")),
        ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#17325c")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#d8e1ec")),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (1, 3), (1, -1), "RIGHT"),
    ]))
    story.extend([
        table,
        Spacer(1, 12),
        Paragraph("Notes: " + _text(payment.notes or "Payment received with thanks."), styles["Normal"]),
        Spacer(1, 18),
        Paragraph("This is a system-generated receipt.", styles["Italic"]),
    ])
    doc.build(story)
    return buffer.getvalue()
