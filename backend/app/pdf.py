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
HEADER_BG = colors.HexColor("#0d47a1")  # Navy blue for table headers (matching HTML template)
HEADER_TEXT = colors.white  # White text for header
CARD_BG = colors.HexColor("#f5f5f5")  # Light gray for info cards


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
    sample.add(ParagraphStyle("CardTitle", parent=sample["Heading3"], fontName="Helvetica-Bold", fontSize=8.5, leading=11, textColor=INK, spaceBefore=0, spaceAfter=3))
    sample.add(ParagraphStyle("Small", parent=sample["Normal"], fontSize=7.5, leading=10, textColor=MUTED))
    sample.add(ParagraphStyle("BodySmall", parent=sample["Normal"], fontSize=8, leading=10, textColor=INK))
    sample.add(ParagraphStyle("RightSmall", parent=sample["Normal"], fontSize=8, leading=10, textColor=INK, alignment=TA_RIGHT))
    sample.add(ParagraphStyle("Logo", parent=sample["Normal"], fontName="Helvetica-Bold", fontSize=18, leading=22, textColor=colors.white, alignment=TA_CENTER))
    sample.add(ParagraphStyle("Company", parent=sample["Normal"], fontName="Helvetica-Bold", fontSize=16, leading=19, textColor=NAVY))
    sample.add(ParagraphStyle("Total", parent=sample["Normal"], fontName="Helvetica-Bold", fontSize=10, leading=12, textColor=NAVY))
    sample.add(ParagraphStyle("SummaryLabel", parent=sample["Normal"], fontSize=8, leading=10, textColor=INK))
    sample.add(ParagraphStyle("SummaryValue", parent=sample["Normal"], fontSize=8, leading=10, textColor=INK, alignment=TA_RIGHT))
    sample.add(ParagraphStyle("DiscountValue", parent=sample["Normal"], fontSize=8, leading=10, textColor=colors.HexColor("#d32f2f"), alignment=TA_RIGHT))
    sample.add(ParagraphStyle("TotalLabel", parent=sample["Normal"], fontName="Helvetica-Bold", fontSize=8, leading=10, textColor=INK))
    sample.add(ParagraphStyle("TotalValue", parent=sample["Normal"], fontName="Helvetica-Bold", fontSize=8, leading=10, textColor=NAVY, alignment=TA_RIGHT))
    sample.add(ParagraphStyle("QuoteTitle", parent=sample["Heading1"], fontName="Helvetica-Bold", fontSize=18, leading=22, textColor=INK, spaceAfter=8))
    sample.add(ParagraphStyle("InfoLabel", parent=sample["Normal"], fontSize=8, leading=10, textColor=MUTED, fontName="Helvetica-Bold"))
    sample.add(ParagraphStyle("InfoValue", parent=sample["Normal"], fontSize=9, leading=11, textColor=INK))
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
    body = [[Paragraph(title.upper(), styles["CardTitle"])]]
    for label, value in rows:
        body.append([Paragraph(f"<font color='#666666' size='8'>{_text(label)}</font><br/><b>{_text(value)}</b>", styles["BodySmall"])])
    table = Table(body, colWidths=[90 * mm])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), CARD_BG),
        ("BOX", (0, 0), (-1, -1), 0.6, BORDER),
        ("INNERGRID", (0, 1), (-1, -1), 0.3, colors.HexColor("#efefef")),
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
        ("BACKGROUND", (0, 0), (-1, 0), HEADER_BG),
        ("TEXTCOLOR", (0, 0), (-1, 0), HEADER_TEXT),
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
    """Build A4 portrait invoice PDF with professional layout"""
    buffer = BytesIO()
    styles = _styles()
    business = _business(settings)


    story = []

    # Header: Logo + Company Info
    logo_placeholder = Table(
        [["COMPANY LOGO"]],
        colWidths=[30 * mm],
        rowHeights=[22 * mm]
    )
    logo_placeholder.setStyle(TableStyle([
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BORDER", (0, 0), (-1, -1), 1.5, colors.HexColor("#0d47a1")),
        ("BORDERPADDING", (0, 0), (-1, -1), 2),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("TEXTCOLOR", (0, 0), (-1, -1), MUTED),
    ]))

    company_info = [
        Paragraph(f"<b><font size='14' color='#0d47a1'>{_text(business.company_name)}</font></b>", styles["Normal"]),
        Paragraph(f"<font size='8' color='#666666'>{_text(business.address)}</font>", styles["Small"]),
        Paragraph(f"<font size='8' color='#666666'>Phone: {_text(business.phone)}</font>", styles["Small"]),
        Paragraph(f"<font size='8' color='#666666'>Email: {_text(business.email)}</font>", styles["Small"]),
        Paragraph(f"<font size='8' color='#666666'>GST: {_text(business.gst_number)}</font>", styles["Small"]),
    ]

    header_table = Table([[logo_placeholder, company_info]], colWidths=[35 * mm, 151 * mm])
    header_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ALIGN", (1, 0), (1, 0), "RIGHT"),
        ("BACKGROUND", (0, 0), (-1, 0), colors.white),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ("LEFTPADDING", (1, 0), (1, 0), 10),
    ]))

    story.extend([header_table, Spacer(1, 5)])

    # Separator line
    separator = Table([["" for _ in range(4)]], colWidths=[47 * mm, 47 * mm, 47 * mm, 47 * mm])
    separator.setStyle(TableStyle([("LINEBELOW", (0, 0), (-1, 0), 2, colors.HexColor("#0d47a1"))]))
    story.append(separator)
    story.append(Spacer(1, 5))

    # Title
    story.append(Paragraph("TAX INVOICE", styles["QuoteTitle"]))
    story.append(Spacer(1, 6))

    # Customer & Invoice Details
    cust_details = [
        Paragraph("BILL TO:", styles["InfoLabel"]),
        Paragraph(f"<b>{_text(invoice.customer.name)}</b>", styles["InfoValue"]),
        Paragraph(_text(invoice.customer.address or ""), styles["Small"]),
        Paragraph(_text(invoice.customer.phone or ""), styles["Small"]),
        Paragraph(f"GST: {_text(invoice.customer.gst_number or '-')}", styles["Small"]),
    ]

    invoice_details = [
        Paragraph("INVOICE DETAILS", styles["InfoLabel"]),
        Paragraph(f"<b>Ref No:</b> {_text(invoice.number)}", styles["InfoValue"]),
        Paragraph(f"<b>Date:</b> {invoice.invoice_date}", styles["InfoValue"]),
        Paragraph(f"<b>Due Date:</b> {invoice.due_date}", styles["InfoValue"]),
    ]

    info_table = Table([[cust_details, invoice_details]], colWidths=[93 * mm, 93 * mm])
    info_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), SOFT),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOX", (0, 0), (-1, -1), 0.5, BORDER),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.extend([info_table, Spacer(1, 8)])

    # Items Table Header
    header_row = [
        Paragraph("<b>S.No</b>", styles["BodySmall"]),
        Paragraph("<b>Description</b>", styles["BodySmall"]),
        Paragraph("<b>HSN</b>", styles["BodySmall"]),
        Paragraph("<b>Qty</b>", styles["BodySmall"]),
        Paragraph("<b>Unit</b>", styles["BodySmall"]),
        Paragraph("<b>Rate</b>", styles["BodySmall"]),
        Paragraph("<b>Amount</b>", styles["BodySmall"]),
    ]

    rows = [header_row]
    for i, item in enumerate(invoice.items, 1):
        rows.append([
            str(i),
            Paragraph(_text(item.description), styles["BodySmall"]),
            item.hsn_code or "-",
            f"{item.quantity}",
            item.unit or "-",
            _money(item.rate),
            _money(item.amount),
        ])

    items_table = Table(rows, colWidths=[8 * mm, 60 * mm, 18 * mm, 16 * mm, 18 * mm, 28 * mm, 38 * mm], repeatRows=1)
    items_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), HEADER_BG),
        ("TEXTCOLOR", (0, 0), (-1, 0), HEADER_TEXT),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.5, BORDER),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (0, -1), "CENTER"),
        ("ALIGN", (3, 1), (3, -1), "RIGHT"),
        ("ALIGN", (5, 1), (-1, -1), "RIGHT"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f9fafb")]),
    ]))
    story.append(items_table)
    story.append(Spacer(1, 6))

    # Summary Section
    summary_data = []
    summary_data.append([
        Paragraph("Subtotal:", styles["SummaryLabel"]),
        Paragraph(_money(invoice.subtotal), styles["SummaryValue"]),
    ])

    if Decimal(invoice.discount or 0) > 0:
        summary_data.append([
            Paragraph("Discount:", styles["SummaryLabel"]),
            Paragraph(_money(-invoice.discount), styles["DiscountValue"]),
        ])
        subtotal_after_discount = Decimal(invoice.subtotal or 0) - Decimal(invoice.discount or 0)
        summary_data.append([
            Paragraph("Subtotal after Discount:", styles["SummaryLabel"]),
            Paragraph(_money(subtotal_after_discount), styles["SummaryValue"]),
        ])

    if Decimal(invoice.igst or 0) > 0:
        summary_data.append([
            Paragraph("IGST (18%):", styles["SummaryLabel"]),
            Paragraph(_money(invoice.igst), styles["SummaryValue"]),
        ])
    else:
        summary_data.append([
            Paragraph("CGST (9%):", styles["SummaryLabel"]),
            Paragraph(_money(invoice.cgst or 0), styles["SummaryValue"]),
        ])
        summary_data.append([
            Paragraph("SGST (9%):", styles["SummaryLabel"]),
            Paragraph(_money(invoice.sgst or 0), styles["SummaryValue"]),
        ])

    summary_data.append([
        Paragraph("GRAND TOTAL:", styles["TotalLabel"]),
        Paragraph(_money(invoice.grand_total), styles["TotalValue"]),
    ])

    summary_table = Table(summary_data, colWidths=[120 * mm, 66 * mm])
    summary_table.setStyle(TableStyle([
        ("ALIGN", (0, 0), (0, -1), "RIGHT"),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, -1), (-1, -1), 10),
        ("LINEABOVE", (0, -1), (-1, -1), 1.5, colors.HexColor("#333333")),
        ("LINEBELOW", (0, -1), (-1, -1), 1.5, colors.HexColor("#333333")),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 10))

    # Footer: Terms & Conditions
    story.append(Paragraph("Terms & Conditions", styles["Section"]))
    terms_text = business.invoice_terms or ""
    story.append(Paragraph(_text(terms_text), styles["BodySmall"]))

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
    """Build A4 portrait quotation PDF matching the HTML template exactly"""
    """Build A4 portrait quotation PDF with professional layout"""
    buffer = BytesIO()
    styles = _styles()
    business = _business(settings)


    story = []

    # Header: Logo + Company Info
    logo_placeholder = Table(
        [["COMPANY LOGO"]],
        colWidths=[30 * mm],
        rowHeights=[22 * mm]
    )
    logo_placeholder.setStyle(TableStyle([
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BORDER", (0, 0), (-1, -1), 1.5, colors.HexColor("#0d47a1")),
        ("BORDERPADDING", (0, 0), (-1, -1), 2),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("TEXTCOLOR", (0, 0), (-1, -1), MUTED),
    ]))

    company_info = [
        Paragraph(f"<b><font size='14' color='#0d47a1'>{_text(business.company_name)}</font></b>", styles["Normal"]),
        Paragraph(f"<font size='8' color='#666666'>{_text(business.address)}</font>", styles["Small"]),
        Paragraph(f"<font size='8' color='#666666'>Phone: {_text(business.phone)}</font>", styles["Small"]),
        Paragraph(f"<font size='8' color='#666666'>Email: {_text(business.email)}</font>", styles["Small"]),
        Paragraph(f"<font size='8' color='#666666'>GST: {_text(business.gst_number)}</font>", styles["Small"]),
    ]

    header_table = Table([[logo_placeholder, company_info]], colWidths=[35 * mm, 151 * mm])
    header_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ALIGN", (1, 0), (1, 0), "RIGHT"),
        ("BACKGROUND", (0, 0), (-1, 0), colors.white),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ("LEFTPADDING", (1, 0), (1, 0), 10),
    ]))

    story.extend([header_table, Spacer(1, 5)])

    # Separator line
    separator = Table([["" for _ in range(4)]], colWidths=[47 * mm, 47 * mm, 47 * mm, 47 * mm])
    separator.setStyle(TableStyle([("LINEBELOW", (0, 0), (-1, 0), 2, colors.HexColor("#0d47a1"))]))
    story.append(separator)
    story.append(Spacer(1, 5))

    # Title
    story.append(Paragraph("QUOTATION", styles["QuoteTitle"]))
    story.append(Spacer(1, 6))

    # Customer & Quote Details - 2 column layout
    cust_details = [
        Paragraph("<b><font size='10' color='#333333'>BILL TO:</font></b>", styles["Normal"]),
        Paragraph(f"<b><font size='9' color='#333333'>{_text(quotation.customer.name)}</font></b>", styles["Normal"]),
        Paragraph(f"<font size='8' color='#666666'>{_text(quotation.address or quotation.customer.address or '')}</font>", styles["Small"]),
        Paragraph(f"<font size='8' color='#666666'>Phone: {_text(quotation.customer.phone or '')}</font>", styles["Small"]),
        Paragraph(f"<font size='8' color='#666666'>GST: {_text(quotation.customer.gst_number or '-')}</font>", styles["Small"]),
    ]

    quote_details = [
        Paragraph("<b><font size='10' color='#333333'>QUOTATION DETAILS</font></b>", styles["Normal"]),
        Paragraph(f"<font size='9'><b>Ref No:</b> <font color='#333333'>{_text(quotation.number)}</font></font>", styles["Normal"]),
        Paragraph(f"<font size='9'><b>Date:</b> <font color='#333333'>{quotation.quotation_date}</font></font>", styles["Normal"]),
        Paragraph(f"<font size='9'><b>Valid Till:</b> <font color='#333333'>{quotation.quotation_date + timedelta(days=quotation.validity_days)}</font></font>", styles["Normal"]),
    ]

    info_table = Table([[cust_details, quote_details]], colWidths=[90 * mm, 96 * mm])
    info_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f5f5f5")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cccccc")),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.extend([info_table, Spacer(1, 8)])

    # Items Table Header
    header_row = [
        Paragraph("<b>S.No</b>", styles["BodySmall"]),
        Paragraph("<b>Description</b>", styles["BodySmall"]),
        Paragraph("<b>HSN</b>", styles["BodySmall"]),
        Paragraph("<b>Qty</b>", styles["BodySmall"]),
        Paragraph("<b>Rate</b>", styles["BodySmall"]),
        Paragraph("<b>Amount</b>", styles["BodySmall"]),
    ]

    rows = [header_row]
    for i, item in enumerate(quotation.items, 1):
        desc = f"{item.category} {item.style}".strip() if hasattr(item, 'category') else "Item"
        rows.append([
            str(i),
            Paragraph(_text(desc), styles["BodySmall"]),
            item.hsn_code or "-",
            f"{item.quantity}",
            _money(item.rate_per_sft if hasattr(item, 'rate_per_sft') else item.rate if hasattr(item, 'rate') else 0),
            _money(item.amount if hasattr(item, 'amount') else 0),
        ])

    items_table = Table(rows, colWidths=[8 * mm, 70 * mm, 18 * mm, 16 * mm, 28 * mm, 46 * mm], repeatRows=1)
    items_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), HEADER_BG),
        ("TEXTCOLOR", (0, 0), (-1, 0), HEADER_TEXT),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.5, BORDER),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (0, -1), "CENTER"),
        ("ALIGN", (3, 1), (3, -1), "RIGHT"),
        ("ALIGN", (5, 1), (-1, -1), "RIGHT"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#fafafa")]),
    ]))
    story.append(items_table)
    story.append(Spacer(1, 6))

    # Summary Section
    summary_data = []
    summary_data.append([
        Paragraph("Subtotal:", styles["SummaryLabel"]),
        Paragraph(_money(quotation.subtotal), styles["SummaryValue"]),
    ])

    if Decimal(quotation.discount or 0) > 0:
        summary_data.append([
            Paragraph("Discount:", styles["SummaryLabel"]),
            Paragraph(_money(-quotation.discount), styles["DiscountValue"]),
        ])
        subtotal_after_discount = Decimal(quotation.subtotal or 0) - Decimal(quotation.discount or 0)
        summary_data.append([
            Paragraph("Subtotal after Discount:", styles["SummaryLabel"]),
            Paragraph(_money(subtotal_after_discount), styles["SummaryValue"]),
        ])

    summary_data.append([
        Paragraph("GST (18%):", styles["SummaryLabel"]),
        Paragraph(_money(quotation.gst or 0), styles["SummaryValue"]),
    ])

    summary_data.append([
        Paragraph("GRAND TOTAL:", styles["TotalLabel"]),
        Paragraph(_money(quotation.grand_total), styles["TotalValue"]),
    ])

    summary_table = Table(summary_data, colWidths=[120 * mm, 66 * mm])
    summary_table.setStyle(TableStyle([
        ("ALIGN", (0, 0), (0, -1), "RIGHT"),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, -1), (-1, -1), 10),
        ("LINEABOVE", (0, -1), (-1, -1), 1.5, colors.HexColor("#333333")),
        ("LINEBELOW", (0, -1), (-1, -1), 1.5, colors.HexColor("#333333")),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 10))

    # Footer: Terms & Conditions
    story.append(Paragraph("Terms & Conditions", styles["Section"]))
    terms_text = quotation.quotation_terms or business.quotation_terms or ""
    if quotation.notes:
        terms_text = f"{terms_text}\n\nNotes: {quotation.notes}"
    story.append(Paragraph(_text(terms_text), styles["BodySmall"]))

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
