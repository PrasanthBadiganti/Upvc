from __future__ import annotations

from datetime import timedelta
from decimal import Decimal
from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from .database import DEFAULT_DB_PATH
from .models import BusinessSettings, CreditNote, DebitNote, Invoice, Payment, PurchaseBill, Quotation

NAVY = colors.HexColor("#12314f")
BLUE = colors.HexColor("#2563eb")
TEAL = colors.HexColor("#14b8a6")
INK = colors.HexColor("#172033")
MUTED = colors.HexColor("#64748b")
BORDER = colors.HexColor("#d8e1ec")
SOFT = colors.HexColor("#f6f8fb")
PALE_BLUE = colors.HexColor("#eaf2ff")


def _money(value: object) -> str:
    return f"Rs. {Decimal(str(value or 0)):,.2f}"


def _text(value: object) -> str:
    return escape(str(value or ""))


def _business(settings: BusinessSettings | None) -> BusinessSettings:
    return settings or BusinessSettings(id=1)


def _styles() -> dict[str, ParagraphStyle]:
    sample = getSampleStyleSheet()
    sample.add(ParagraphStyle("DocTitle", parent=sample["Heading1"], fontName="Helvetica-Bold", fontSize=20, leading=24, textColor=NAVY, spaceAfter=4))
    sample.add(ParagraphStyle("Section", parent=sample["Heading3"], fontName="Helvetica-Bold", fontSize=9.5, leading=12, textColor=NAVY, spaceBefore=3, spaceAfter=5))
    sample.add(ParagraphStyle("Small", parent=sample["Normal"], fontSize=7.5, leading=10, textColor=MUTED))
    sample.add(ParagraphStyle("BodySmall", parent=sample["Normal"], fontSize=8, leading=10, textColor=INK))
    sample.add(ParagraphStyle("RightSmall", parent=sample["Normal"], fontSize=8, leading=10, textColor=INK, alignment=TA_RIGHT))
    sample.add(ParagraphStyle("Logo", parent=sample["Normal"], fontName="Helvetica-Bold", fontSize=18, leading=22, textColor=colors.white, alignment=TA_CENTER))
    sample.add(ParagraphStyle("Company", parent=sample["Normal"], fontName="Helvetica-Bold", fontSize=16, leading=19, textColor=NAVY))
    sample.add(ParagraphStyle("Total", parent=sample["Normal"], fontName="Helvetica-Bold", fontSize=10, leading=12, textColor=NAVY))
    return sample


def _doc(buffer: BytesIO) -> SimpleDocTemplate:
    return SimpleDocTemplate(buffer, pagesize=A4, rightMargin=12 * mm, leftMargin=12 * mm, topMargin=10 * mm, bottomMargin=11 * mm)


def _logo_path(settings: BusinessSettings) -> str | None:
    if not settings.logo_path:
        return None
    path = DEFAULT_DB_PATH.parent / "uploads" / settings.logo_path.rsplit("/", 1)[-1]
    return str(path) if path.exists() else None


def _logo_flowable(settings: BusinessSettings, styles: dict[str, ParagraphStyle]):
    logo_file = _logo_path(settings)
    if logo_file:
        logo = Image(logo_file, width=22 * mm, height=22 * mm, kind="proportional")
        frame = Table([[logo]], colWidths=[22 * mm], rowHeights=[22 * mm])
        frame.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("BOX", (0, 0), (-1, -1), 0.6, BORDER),
            ("BACKGROUND", (0, 0), (-1, -1), colors.white),
        ]))
        return frame
    logo = Table([[Paragraph(_text((settings.logo_text or "CF")[:4].upper()), styles["Logo"])]], colWidths=[22 * mm], rowHeights=[22 * mm])
    logo.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), BLUE),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BOX", (0, 0), (-1, -1), 0, BLUE),
    ]))
    return logo


def _header(document_title: str, number: str, settings: BusinessSettings | None, styles: dict[str, ParagraphStyle]) -> Table:
    business = _business(settings)
    logo = _logo_flowable(business, styles)
    company = [
        Paragraph(_text(business.company_name), styles["Company"]),
        Paragraph(_text(business.tagline), styles["Small"]),
        Paragraph(f"{_text(business.address)}<br/>GSTIN: {_text(business.gst_number)}<br/>Phone: {_text(business.phone)} | Email: {_text(business.email)}", styles["Small"]),
    ]
    doc_info = [
        Paragraph(document_title.upper(), styles["DocTitle"]),
        Paragraph(_text(number), styles["RightSmall"]),
    ]
    table = Table([[logo, company, doc_info]], colWidths=[26 * mm, 103 * mm, 57 * mm])
    table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BACKGROUND", (2, 0), (2, 0), colors.HexColor("#f8fbff")),
        ("BOX", (2, 0), (2, 0), 0.6, BORDER),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    return table


def _info_card(title: str, rows: list[tuple[str, object]], styles: dict[str, ParagraphStyle]) -> Table:
    body = [[Paragraph(title.upper(), styles["Section"])]]
    for label, value in rows:
        body.append([Paragraph(f"<font color='#64748b'>{_text(label)}</font><br/><b>{_text(value)}</b>", styles["BodySmall"])])
    table = Table(body, colWidths=[90 * mm])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), PALE_BLUE),
        ("BOX", (0, 0), (-1, -1), 0.6, BORDER),
        ("INNERGRID", (0, 1), (-1, -1), 0.3, colors.HexColor("#edf2f7")),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    return table


def _two_cards(left: Table, right: Table) -> Table:
    table = Table([[left, right]], colWidths=[93 * mm, 93 * mm])
    table.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    return table


def _item_table(rows: list[list[object]], widths: list[float], summary_start: int | None = None) -> Table:
    table = Table(rows, colWidths=widths, repeatRows=1)
    style = [
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 7),
        ("GRID", (0, 0), (-1, -1), 0.35, BORDER),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BACKGROUND", (0, 1), (-1, -1), colors.white),
        ("ALIGN", (2, 1), (-1, -1), "RIGHT"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]
    if summary_start is not None:
        style.extend([
            ("BACKGROUND", (0, summary_start), (-1, -1), SOFT),
            ("FONTNAME", (-2, summary_start), (-1, -1), "Helvetica-Bold"),
            ("ALIGN", (-2, summary_start), (-1, -1), "RIGHT"),
        ])
    table.setStyle(TableStyle(style))
    return table


def _footer_blocks(settings: BusinessSettings | None, terms: str, styles: dict[str, ParagraphStyle]) -> Table:
    business = _business(settings)
    bank = _info_card("Bank / Payment Details", [
        ("Bank", business.bank_name),
        ("Account Name", business.account_name),
        ("Account No.", business.account_number),
        ("IFSC", business.ifsc),
        ("UPI", business.upi_id),
    ], styles)
    terms_card = _info_card("Terms & Notes", [("Terms", terms)], styles)
    auth = _info_card("Authorized Signature", [("For", business.company_name), ("Signature", " ")], styles)
    table = Table([[bank, terms_card], [auth, ""]], colWidths=[93 * mm, 93 * mm], rowHeights=[None, 34 * mm])
    table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("SPAN", (1, 1), (1, 1)),
    ]))
    return table


def build_invoice_pdf(invoice: Invoice, settings: BusinessSettings | None = None) -> bytes:
    buffer = BytesIO()
    styles = _styles()
    story = [
        _header("Tax Invoice", invoice.number, settings, styles),
        Spacer(1, 8),
        _two_cards(
            _info_card("Bill To", [
                ("Customer", invoice.customer.name),
                ("GSTIN", invoice.customer.gst_number or "-"),
                ("Address", invoice.customer.address),
                ("Project/Site", invoice.customer.project_site),
            ], styles),
            _info_card("Invoice Details", [
                ("Invoice Date", invoice.invoice_date),
                ("Due Date", invoice.due_date),
                ("Status", invoice.status),
                ("Source Quotation", invoice.quotation.number if invoice.quotation else "-"),
            ], styles),
        ),
        Spacer(1, 10),
    ]
    rows = [["#", "Description", "HSN", "Category", "Qty", "Rate", "GST", "Amount"]]
    for i, item in enumerate(invoice.items, 1):
        rows.append([str(i), Paragraph(_text(item.description), styles["BodySmall"]), item.hsn_code or "-", item.category, f"{item.quantity}", _money(item.rate), f"{item.gst_percent}%", _money(item.amount)])
    gst_rows = [["", "", "", "", "", "", "IGST", _money(invoice.igst)]] if Decimal(invoice.igst or 0) > 0 else [
        ["", "", "", "", "", "", "CGST", _money(invoice.cgst)],
        ["", "", "", "", "", "", "SGST", _money(invoice.sgst)],
    ]
    rows.extend([
        ["", "", "", "", "", "", "Subtotal", _money(invoice.subtotal)],
        *gst_rows,
        ["", "", "", "", "", "", "Grand Total", _money(invoice.grand_total)],
        ["", "", "", "", "", "", "Paid", _money(invoice.paid_amount)],
        ["", "", "", "", "", "", "Balance", _money(invoice.pending_balance)],
    ])
    story.extend([
        _item_table(rows, [8 * mm, 50 * mm, 16 * mm, 20 * mm, 14 * mm, 24 * mm, 20 * mm, 34 * mm], len(rows) - 4 - len(gst_rows)),
        Spacer(1, 10),
        _footer_blocks(settings, _business(settings).invoice_terms, styles),
    ])
    _doc(buffer).build(story)
    return buffer.getvalue()


def build_purchase_bill_pdf(bill: PurchaseBill, settings: BusinessSettings | None = None) -> bytes:
    buffer = BytesIO()
    styles = _styles()
    story = [
        _header("Purchase Bill", bill.number, settings, styles),
        Spacer(1, 8),
        _two_cards(
            _info_card("Vendor", [
                ("Vendor", bill.vendor.name),
                ("GSTIN", bill.vendor.gst_number or "-"),
                ("Address", bill.vendor.address),
                ("Phone", bill.vendor.phone),
            ], styles),
            _info_card("Bill Details", [
                ("Vendor Bill No.", bill.vendor_bill_number or "-"),
                ("Bill Date", bill.bill_date),
                ("Due Date", bill.due_date),
                ("Status", bill.status),
            ], styles),
        ),
        Spacer(1, 10),
    ]
    rows = [["#", "Description", "HSN", "Category", "Qty", "Rate", "GST", "Amount"]]
    for i, item in enumerate(bill.items, 1):
        rows.append([str(i), Paragraph(_text(item.description), styles["BodySmall"]), item.hsn_code or "-", item.category, f"{item.quantity}", _money(item.rate), f"{item.gst_percent}%", _money(item.amount)])
    gst_rows = [["", "", "", "", "", "", "IGST", _money(bill.igst)]] if Decimal(bill.igst or 0) > 0 else [
        ["", "", "", "", "", "", "CGST", _money(bill.cgst)],
        ["", "", "", "", "", "", "SGST", _money(bill.sgst)],
    ]
    rows.extend([
        ["", "", "", "", "", "", "Subtotal", _money(bill.subtotal)],
        *gst_rows,
        ["", "", "", "", "", "", "Grand Total", _money(bill.grand_total)],
        ["", "", "", "", "", "", "Paid", _money(bill.paid_amount)],
        ["", "", "", "", "", "", "Balance", _money(bill.pending_balance)],
    ])
    story.extend([
        _item_table(rows, [8 * mm, 50 * mm, 16 * mm, 20 * mm, 14 * mm, 24 * mm, 20 * mm, 34 * mm], len(rows) - 4 - len(gst_rows)),
        Spacer(1, 10),
        _footer_blocks(settings, "Purchase bill recorded for internal accounts payable tracking.", styles),
    ])
    _doc(buffer).build(story)
    return buffer.getvalue()


def build_quotation_pdf(quotation: Quotation, settings: BusinessSettings | None = None) -> bytes:
    buffer = BytesIO()
    styles = _styles()
    valid_until = quotation.quotation_date + timedelta(days=quotation.validity_days)
    story = [
        _header("Project Quotation", quotation.number, settings, styles),
        Spacer(1, 8),
        _two_cards(
            _info_card("Client & Site", [
                ("Customer", quotation.customer.name),
                ("Phone / Email", f"{quotation.customer.phone} / {quotation.customer.email}"),
                ("GSTIN", quotation.customer.gst_number or "-"),
                ("Site", quotation.site_location or quotation.customer.project_site),
                ("Address", quotation.address or quotation.customer.address),
            ], styles),
            _info_card("Quotation Details", [
                ("Quotation Date", quotation.quotation_date),
                ("Valid Until", valid_until),
                ("Sales Person", quotation.sales_person),
                ("Status", quotation.status),
            ], styles),
        ),
        Spacer(1, 10),
    ]
    rows = [["#", "Product / Specification", "HSN", "Size", "SFT", "Qty", "Total SFT", "Rate", "Amount"]]
    for i, item in enumerate(quotation.items, 1):
        item_name = _text(f"{item.category} {item.style}".strip())
        material = _text(", ".join(filter(None, [item.profile, item.color, item.track, item.glass, item.glass_color, item.hardware, item.reinforcement, item.mesh])))
        rows.append([
            str(i),
            Paragraph(f"<b>{item_name}</b><br/><font size='7' color='#64748b'>{material}</font><br/><font size='7'>Location: {_text(item.location)}</font>", styles["BodySmall"]),
            item.hsn_code or "-",
            f"{item.width_mm} x {item.height_mm} mm",
            f"{item.sft}",
            str(item.quantity),
            f"{item.total_sft}",
            _money(item.rate_per_sft),
            _money(item.amount),
        ])
    rows.extend([
        ["", "", "", "", "", "", "", "Subtotal", _money(quotation.subtotal)],
        ["", "", "", "", "", "", "", "Transport", _money(quotation.transport)],
        ["", "", "", "", "", "", "", "Discount", _money(quotation.discount)],
        ["", "", "", "", "", "", "", "GST", _money(quotation.gst)],
        ["", "", "", "", "", "", "", "Grand Total", _money(quotation.grand_total)],
        ["", "", "", "", "", "", "", "Advance", _money(quotation.advance)],
        ["", "", "", "", "", "", "", "Balance", _money(quotation.balance)],
    ])
    terms = f"{_business(settings).quotation_terms}\n{quotation.notes or ''}".strip()
    story.extend([
        _item_table(rows, [8 * mm, 42 * mm, 14 * mm, 25 * mm, 12 * mm, 10 * mm, 17 * mm, 22 * mm, 36 * mm], len(rows) - 7),
        Spacer(1, 10),
        _footer_blocks(settings, terms, styles),
    ])
    _doc(buffer).build(story)
    return buffer.getvalue()


def build_payment_receipt_pdf(payment: Payment, settings: BusinessSettings | None = None) -> bytes:
    invoice = payment.invoice
    paid_to_date = sum((Decimal(row.amount or 0) for row in invoice.payments if row.created_at <= payment.created_at), Decimal("0"))
    balance_after = Decimal(invoice.grand_total or 0) - paid_to_date

    buffer = BytesIO()
    styles = _styles()
    story = [
        _header("Payment Receipt", f"Receipt #{payment.id}", settings, styles),
        Spacer(1, 8),
        _two_cards(
            _info_card("Received From", [
                ("Customer", invoice.customer.name),
                ("Project/Site", invoice.customer.project_site),
                ("Invoice", invoice.number),
                ("Receipt Date", payment.payment_date),
            ], styles),
            _info_card("Payment Details", [
                ("Mode", payment.mode),
                ("Reference", payment.reference_number or "-"),
                ("Received By", payment.received_by),
                ("Amount Received", _money(payment.amount)),
            ], styles),
        ),
        Spacer(1, 10),
    ]
    rows = [
        ["Invoice Total", _money(invoice.grand_total)],
        ["Paid To Date", _money(paid_to_date)],
        ["Balance After This Payment", _money(balance_after)],
    ]
    summary = Table(rows, colWidths=[96 * mm, 90 * mm])
    summary.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), SOFT),
        ("BOX", (0, 0), (-1, -1), 0.6, BORDER),
        ("INNERGRID", (0, 0), (-1, -1), 0.35, BORDER),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.extend([
        summary,
        Spacer(1, 12),
        _footer_blocks(settings, f"{_business(settings).payment_terms}\n{payment.notes or ''}".strip(), styles),
    ])
    _doc(buffer).build(story)
    return buffer.getvalue()


def _build_note_pdf(document_title: str, note: CreditNote | DebitNote, settings: BusinessSettings | None) -> bytes:
    invoice = note.invoice
    buffer = BytesIO()
    styles = _styles()
    story = [
        _header(document_title, note.number, settings, styles),
        Spacer(1, 8),
        _two_cards(
            _info_card("Bill To", [
                ("Customer", note.customer.name),
                ("GSTIN", note.customer.gst_number or "-"),
                ("Address", note.customer.address),
                ("Project/Site", note.customer.project_site),
            ], styles),
            _info_card("Reference", [
                ("Against Invoice", invoice.number),
                ("Invoice Date", invoice.invoice_date),
                ("Note Date", note.note_date),
                ("Reason", note.reason or "-"),
            ], styles),
        ),
        Spacer(1, 10),
    ]
    rows = [["#", "Description", "HSN", "Category", "Qty", "Rate", "GST", "Amount"]]
    for i, item in enumerate(note.items, 1):
        rows.append([str(i), Paragraph(_text(item.description), styles["BodySmall"]), item.hsn_code or "-", item.category, f"{item.quantity}", _money(item.rate), f"{item.gst_percent}%", _money(item.amount)])
    rows.extend([
        ["", "", "", "", "", "", "Subtotal", _money(note.subtotal)],
        ["", "", "", "", "", "", "GST", _money(note.gst)],
        ["", "", "", "", "", "", "Grand Total", _money(note.grand_total)],
    ])
    story.extend([
        _item_table(rows, [8 * mm, 50 * mm, 16 * mm, 20 * mm, 14 * mm, 24 * mm, 20 * mm, 34 * mm], len(rows) - 3),
        Spacer(1, 10),
        _footer_blocks(settings, _business(settings).invoice_terms, styles),
    ])
    _doc(buffer).build(story)
    return buffer.getvalue()


def build_credit_note_pdf(credit_note: CreditNote, settings: BusinessSettings | None = None) -> bytes:
    return _build_note_pdf("Credit Note", credit_note, settings)


def build_debit_note_pdf(debit_note: DebitNote, settings: BusinessSettings | None = None) -> bytes:
    return _build_note_pdf("Debit Note", debit_note, settings)
