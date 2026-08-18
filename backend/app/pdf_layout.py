"""Lightweight quotation and invoice PDFs.

Pure ReportLab - no browser, no native libraries. Generates in ~25 ms using a
few MB of memory, so it works on any machine and inside the packaged .exe.

The layout deliberately mirrors quotation_template_final_a4.html: navy rule
under the header, two grey party cards, a navy-headed items table, hairline
summary rows and a navy-bracketed grand total.
"""
from __future__ import annotations

from datetime import timedelta
from decimal import Decimal
from io import BytesIO
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    Image, KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
)

from .database import DEFAULT_DB_PATH
from .models import BusinessSettings, Invoice, Quotation

UPLOAD_DIR = DEFAULT_DB_PATH.parent / "uploads"

NAVY = colors.HexColor("#0d47a1")
CARD_BG = colors.HexColor("#f5f5f5")
LOGO_BG = colors.HexColor("#e8eef7")
INK = colors.HexColor("#333333")
MUTED = colors.HexColor("#666666")
TITLE_INK = colors.HexColor("#1a1a1a")
HAIRLINE = colors.HexColor("#eeeeee")
RED = colors.HexColor("#d32f2f")

PAGE_MARGIN = 13 * mm
CONTENT_W = A4[0] - 2 * PAGE_MARGIN

# ReportLab's built-in Helvetica has no rupee glyph and would print a black box.
# Segoe UI ships with Windows, carries the glyph, and is the face the reference
# template asks for - so use it when present and degrade to "Rs." if not.
FONT, FONT_BOLD, RUPEE = "Helvetica", "Helvetica-Bold", "Rs."


def _register_fonts() -> None:
    global FONT, FONT_BOLD, RUPEE
    for regular, bold, family in (("segoeui.ttf", "segoeuib.ttf", "SegoeUI"),
                                  ("arial.ttf", "arialbd.ttf", "ArialUI")):
        reg = Path(r"C:\Windows\Fonts") / regular
        bld = Path(r"C:\Windows\Fonts") / bold
        if not (reg.exists() and bld.exists()):
            continue
        try:
            pdfmetrics.registerFont(TTFont(family, str(reg)))
            pdfmetrics.registerFont(TTFont(f"{family}-Bold", str(bld)))
            pdfmetrics.registerFontFamily(family, normal=family, bold=f"{family}-Bold")
            FONT, FONT_BOLD, RUPEE = family, f"{family}-Bold", "\u20b9"
            return
        except Exception:
            continue


_register_fonts()

_S = {
    "company": ParagraphStyle("company", fontName=FONT_BOLD, fontSize=12.5,
                              textColor=NAVY, alignment=TA_RIGHT, leading=15),
    "company_detail": ParagraphStyle("cdetail", fontName=FONT, fontSize=7.6,
                                     textColor=MUTED, alignment=TA_RIGHT, leading=10.4),
    "logo_text": ParagraphStyle("logo", fontName=FONT, fontSize=7.6,
                                textColor=MUTED, alignment=TA_CENTER),
    "title": ParagraphStyle("title", fontName=FONT_BOLD, fontSize=15.5,
                            textColor=TITLE_INK, leading=18),
    "card_label": ParagraphStyle("clabel", fontName=FONT_BOLD, fontSize=7.6,
                                 textColor=INK, leading=11),
    "card_value": ParagraphStyle("cvalue", fontName=FONT, fontSize=8.4,
                                 textColor=MUTED, leading=12),
    "th": ParagraphStyle("th", fontName=FONT_BOLD, fontSize=7.8,
                         textColor=colors.white, leading=10),
    "td": ParagraphStyle("td", fontName=FONT, fontSize=7.8,
                         textColor=colors.HexColor("#233554"), leading=10.5),
    "td_sub": ParagraphStyle("tdsub", fontName=FONT, fontSize=6.8,
                             textColor=MUTED, leading=9),
    "sum_label": ParagraphStyle("slabel", fontName=FONT_BOLD, fontSize=8.4,
                                textColor=INK, leading=11),
    "sum_value": ParagraphStyle("svalue", fontName=FONT_BOLD, fontSize=8.4,
                                textColor=INK, alignment=TA_RIGHT, leading=11),
    "footer": ParagraphStyle("footer", fontName=FONT, fontSize=6.9,
                             textColor=MUTED, leading=9.6, alignment=TA_LEFT),
}


def _inr(value: object, decimals: int = 2) -> str:
    """Indian digit grouping, symbol set off from the number: 116375.02 -> Rs. 1,16,375.02"""
    amount = Decimal(str(value or 0))
    negative = amount < 0
    text = f"{abs(amount):.{decimals}f}"
    whole, _, frac = text.partition(".")
    if len(whole) > 3:
        head, tail = whole[:-3], whole[-3:]
        groups = []
        while len(head) > 2:
            groups.insert(0, head[-2:])
            head = head[:-2]
        if head:
            groups.insert(0, head)
        whole = ",".join(groups + [tail])
    out = f"{RUPEE} {whole}.{frac}" if frac else f"{RUPEE} {whole}"
    return f"-{out}" if negative else out


def _num(value: object, decimals: int = 2) -> str:
    return f"{Decimal(str(value or 0)):,.{decimals}f}"


def _esc(text: object) -> str:
    return (str(text or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def _logo_cell(settings: BusinessSettings):
    """Real logo when one is uploaded, otherwise the dashed placeholder box."""
    if settings.logo_path:
        path = UPLOAD_DIR / Path(settings.logo_path).name
        if path.exists():
            try:
                img = Image(str(path))
                ratio = img.imageHeight / float(img.imageWidth or 1)
                img.drawWidth = 32 * mm
                img.drawHeight = min(16 * mm, 32 * mm * ratio)
                return img, False
            except Exception:
                pass
    return Paragraph(_esc(settings.logo_text or "COMPANY LOGO"), _S["logo_text"]), True


def _header(settings: BusinessSettings) -> list:
    logo, dashed = _logo_cell(settings)
    lines = [ln.strip() for ln in (settings.address or "").splitlines() if ln.strip()]
    if settings.phone:
        lines.append(f"Phone: {settings.phone}")
    if settings.email:
        lines.append(f"Email: {settings.email}")
    if settings.gst_number:
        lines.append(f"GST: {settings.gst_number}")

    right = [Paragraph(_esc(settings.company_name), _S["company"])]
    right += [Paragraph(_esc(ln), _S["company_detail"]) for ln in lines]

    # No fixed row height: the company block grows with however many address
    # lines are configured, so nothing is ever clipped by the rule below.
    table = Table([[logo, right]], colWidths=[34 * mm, CONTENT_W - 34 * mm])
    style = [
        ("VALIGN", (0, 0), (0, 0), "MIDDLE"),
        ("VALIGN", (1, 0), (1, 0), "TOP"),
        ("ALIGN", (0, 0), (0, 0), "CENTER"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]
    if dashed:
        style += [("BACKGROUND", (0, 0), (0, 0), LOGO_BG),
                  ("BOX", (0, 0), (0, 0), 1.1, NAVY, None, (2.5, 2))]
    table.setStyle(TableStyle(style))
    return [table, Spacer(1, 5), _rule(1.6, NAVY), Spacer(1, 9)]


def _rule(thickness: float, color) -> Table:
    line = Table([[""]], colWidths=[CONTENT_W], rowHeights=[thickness])
    line.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), color),
        ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    return line


def _card(label: str, rows: list) -> Table:
    """Grey party card. rows is a list of strings, or (left, right) pairs."""
    body = [[Paragraph(label, _S["card_label"])]]
    for row in rows:
        if isinstance(row, tuple):
            inner = Table([[Paragraph(_esc(row[0]), _S["card_value"]),
                            Paragraph(f"<b>{_esc(row[1])}</b>", _S["card_value"])]],
                          colWidths=[(CONTENT_W / 2 - 14 * mm) * 0.45,
                                     (CONTENT_W / 2 - 14 * mm) * 0.55])
            inner.setStyle(TableStyle([
                ("ALIGN", (1, 0), (1, 0), "RIGHT"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 0.5),
            ]))
            body.append([inner])
        else:
            body.append([Paragraph(row, _S["card_value"])])

    card = Table(body, colWidths=[CONTENT_W / 2 - 4 * mm])
    card.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), CARD_BG),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 7), ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (0, 0), 7), ("BOTTOMPADDING", (0, 0), (0, 0), 3),
        ("TOPPADDING", (0, 1), (-1, -1), 1), ("BOTTOMPADDING", (0, -1), (-1, -1), 7),
    ]))
    return card


def _party_row(left: Table, right: Table) -> Table:
    row = Table([[left, right]], colWidths=[CONTENT_W / 2, CONTENT_W / 2])
    row.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (0, 0), 0), ("RIGHTPADDING", (0, 0), (0, 0), 4 * mm),
        ("LEFTPADDING", (1, 0), (1, 0), 4 * mm), ("RIGHTPADDING", (1, 0), (1, 0), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    return row


def _items_table(rows: list[list]) -> Table:
    head = [Paragraph(h, _S["th"]) for h in
            ("S.No", "Description", "HSN", "Qty", "Unit", "Rate", "Amount")]
    widths = [11 * mm, CONTENT_W - 108 * mm, 20 * mm, 16 * mm, 14 * mm, 22 * mm, 25 * mm]
    table = Table([head] + rows, colWidths=widths, repeatRows=1)
    style = [
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (0, -1), "CENTER"),
        ("ALIGN", (3, 0), (3, -1), "RIGHT"),
        ("ALIGN", (5, 0), (6, -1), "RIGHT"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5), ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 4.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 4.5),
        ("LINEBELOW", (0, 1), (-1, -2), 0.5, HAIRLINE),
        ("LINEBELOW", (0, -1), (-1, -1), 1.4, NAVY),
    ]
    table.setStyle(TableStyle(style))
    return table


def _summary(rows: list[tuple[str, str, str]]) -> Table:
    """rows: (label, value, kind) where kind is '', 'discount' or 'total'."""
    body, style = [], [
        ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]
    for i, (label, value, kind) in enumerate(rows):
        lab, val = _S["sum_label"], _S["sum_value"]
        if kind == "discount":
            lab = ParagraphStyle("d1", parent=lab, textColor=RED)
            val = ParagraphStyle("d2", parent=val, textColor=RED)
        elif kind == "total":
            lab = ParagraphStyle("t1", parent=lab, fontSize=9.6)
            val = ParagraphStyle("t2", parent=val, fontSize=9.6)
        body.append([Paragraph(label, lab), Paragraph(value, val)])
        if kind == "total":
            style += [("LINEABOVE", (0, i), (-1, i), 1.4, NAVY),
                      ("LINEBELOW", (0, i), (-1, i), 1.4, NAVY),
                      ("TOPPADDING", (0, i), (-1, i), 6), ("BOTTOMPADDING", (0, i), (-1, i), 6)]
        else:
            style += [("LINEBELOW", (0, i), (-1, i), 0.5, HAIRLINE),
                      ("TOPPADDING", (0, i), (-1, i), 3.6), ("BOTTOMPADDING", (0, i), (-1, i), 3.6)]
    table = Table(body, colWidths=[CONTENT_W * 0.62, CONTENT_W * 0.38])
    table.setStyle(TableStyle(style))
    return table


def _footer(terms: str) -> list:
    if not terms:
        return []
    return [Spacer(1, 9), _rule(0.5, colors.HexColor("#dddddd")), Spacer(1, 5),
            Paragraph(f"<b>Terms &amp; Conditions:</b> {_esc(terms)}", _S["footer"])]


def _document(title: str) -> tuple[BytesIO, SimpleDocTemplate]:
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4, title=title,
        leftMargin=PAGE_MARGIN, rightMargin=PAGE_MARGIN,
        topMargin=12 * mm, bottomMargin=12 * mm,
    )
    return buffer, doc


def _bill_to(customer, address_override: str = "") -> list:
    rows = [f"<b>{_esc(customer.name)}</b>"]
    for line in (address_override or customer.address or "").splitlines():
        if line.strip():
            rows.append(_esc(line.strip()))
    if customer.phone:
        rows.append(f"Phone: {_esc(customer.phone)}")
    if customer.gst_number:
        rows.append(f"GST: {_esc(customer.gst_number)}")
    return rows


def _tax_rows(cgst: Decimal, sgst: Decimal, igst: Decimal, taxable: Decimal) -> list:
    def pct(part):
        if taxable <= 0:
            return ""
        return f" ({(part / taxable * 100).quantize(Decimal('0.01')).normalize():f}%)"
    if igst > 0:
        return [(f"IGST{pct(igst)}:", _inr(igst), "")]
    return [(f"CGST{pct(cgst)}:", _inr(cgst), ""), (f"SGST{pct(sgst)}:", _inr(sgst), "")]


# --------------------------------------------------------------------------- #

def build_quotation_pdf(quotation: Quotation, settings: BusinessSettings | None = None) -> bytes:
    settings = settings or BusinessSettings(id=1)
    buffer, doc = _document(f"Quotation {quotation.number}")

    rows = []
    for i, item in enumerate(quotation.items, 1):
        title = " ".join(p for p in (item.category, item.style) if p)
        bits = []
        if item.width_mm and item.height_mm:
            bits.append(f"{_num(item.width_mm, 0)} x {_num(item.height_mm, 0)} mm")
        if item.quantity:
            bits.append(f"{item.quantity} nos")
        if item.location:
            bits.append(_esc(item.location))
        cell = [Paragraph(_esc(title), _S["td"])]
        if bits:
            cell.append(Paragraph(" &middot; ".join(bits), _S["td_sub"]))
        rows.append([Paragraph(str(i), _S["td"]), cell,
                     Paragraph(_esc(item.hsn_code or "-"), _S["td"]),
                     Paragraph(_num(item.total_sft), _S["td"]),
                     Paragraph("Sq. Ft.", _S["td"]),
                     Paragraph(_inr(item.rate_per_sft), _S["td"]),
                     Paragraph(_inr(item.amount), _S["td"])])

    subtotal = Decimal(quotation.subtotal or 0)
    transport = Decimal(quotation.transport or 0)
    discount = Decimal(quotation.discount or 0)
    gst = Decimal(quotation.gst or 0)
    charges = list(quotation.charges)
    taxable_charges = sum((Decimal(c.amount or 0) for c in charges if c.taxable), Decimal("0"))
    taxable = subtotal + transport + taxable_charges - discount

    summary = [("Subtotal:", _inr(subtotal), "")]
    if transport > 0:
        summary.append(("Transport:", _inr(transport), ""))
    for charge in charges:
        if charge.taxable:
            summary.append((f"{_esc(charge.label)}:", _inr(charge.amount), ""))
    if discount > 0:
        summary.append(("Discount:", f"-{_inr(discount)}", "discount"))
    if taxable != subtotal:
        summary.append(("Taxable Value:", _inr(taxable), ""))

    cs = (quotation.customer.state or "").strip().lower()
    bs = (settings.state or "").strip().lower()
    if cs and bs and cs != bs:
        summary += _tax_rows(Decimal(0), Decimal(0), gst, taxable)
    else:
        half = (gst / 2).quantize(Decimal("0.01"))
        summary += _tax_rows(half, gst - half, Decimal(0), taxable)
    for charge in charges:
        if not charge.taxable:
            summary.append((f"{_esc(charge.label)} (no GST):", _inr(charge.amount), ""))
    summary.append(("GRAND TOTAL:", _inr(quotation.grand_total), "total"))

    valid_till = quotation.quotation_date + timedelta(days=quotation.validity_days or 0)
    terms = (quotation.quotation_terms or "").strip() or (settings.quotation_terms or "").strip()

    story = _header(settings)
    story += [Paragraph("QUOTATION", _S["title"]), Spacer(1, 8)]
    story += [_party_row(
        _card("BILL TO:", _bill_to(quotation.customer, quotation.address)),
        _card("QUOTATION DETAILS", [
            ("Ref No:", quotation.number),
            ("Date:", quotation.quotation_date.strftime("%d-%b-%Y")),
            ("Valid Till:", valid_till.strftime("%d-%b-%Y")),
        ]),
    ), Spacer(1, 9)]
    story += [_items_table(rows), Spacer(1, 7), _summary(summary)]
    story += _footer(terms)

    doc.build(story)
    return buffer.getvalue()


def build_invoice_pdf(invoice: Invoice, settings: BusinessSettings | None = None) -> bytes:
    settings = settings or BusinessSettings(id=1)
    buffer, doc = _document(f"Invoice {invoice.number}")

    rows = []
    for i, item in enumerate(invoice.items, 1):
        rows.append([Paragraph(str(i), _S["td"]),
                     Paragraph(_esc(item.description), _S["td"]),
                     Paragraph(_esc(item.hsn_code or "-"), _S["td"]),
                     Paragraph(_num(item.quantity), _S["td"]),
                     Paragraph(_esc(item.unit or "Nos"), _S["td"]),
                     Paragraph(_inr(item.rate), _S["td"]),
                     Paragraph(_inr(item.amount), _S["td"])])

    subtotal = Decimal(invoice.subtotal or 0)
    transport = Decimal(invoice.transport or 0)
    discount = Decimal(invoice.discount or 0)
    charges = list(invoice.charges)
    taxable_charges = sum((Decimal(c.amount or 0) for c in charges if c.taxable), Decimal("0"))
    taxable = subtotal + transport + taxable_charges - discount

    summary = [("Subtotal:", _inr(subtotal), "")]
    if transport > 0:
        summary.append(("Transport:", _inr(transport), ""))
    for charge in charges:
        if charge.taxable:
            summary.append((f"{_esc(charge.label)}:", _inr(charge.amount), ""))
    if discount > 0:
        summary.append(("Discount:", f"-{_inr(discount)}", "discount"))
    if taxable != subtotal:
        summary.append(("Taxable Value:", _inr(taxable), ""))
    summary += _tax_rows(Decimal(invoice.cgst or 0), Decimal(invoice.sgst or 0),
                         Decimal(invoice.igst or 0), taxable)
    for charge in charges:
        if not charge.taxable:
            summary.append((f"{_esc(charge.label)} (no GST):", _inr(charge.amount), ""))
    summary.append(("GRAND TOTAL:", _inr(invoice.grand_total), "total"))
    if Decimal(invoice.paid_amount or 0) > 0:
        summary.append(("Amount Paid:", _inr(invoice.paid_amount), ""))
        summary.append(("Balance Due:", _inr(invoice.pending_balance), ""))

    story = _header(settings)
    story += [Paragraph("TAX INVOICE", _S["title"]), Spacer(1, 8)]
    story += [_party_row(
        _card("BILL TO:", _bill_to(invoice.customer)),
        _card("INVOICE DETAILS", [
            ("Invoice No:", invoice.number),
            ("Date:", invoice.invoice_date.strftime("%d-%b-%Y")),
            ("Due Date:", invoice.due_date.strftime("%d-%b-%Y")),
            ("Status:", invoice.status),
        ]),
    ), Spacer(1, 9)]
    story += [_items_table(rows), Spacer(1, 7), _summary(summary)]
    story += _footer((settings.invoice_terms or "").strip())

    bank_rows = [(lbl, val) for lbl, val in (
        ("Bank:", settings.bank_name), ("Account Name:", settings.account_name),
        ("Account No.:", settings.account_number), ("IFSC:", settings.ifsc),
        ("UPI:", settings.upi_id)) if val]
    if bank_rows:
        sign = Table([[Paragraph(f"For {_esc(settings.company_name)}", _S["card_value"])],
                      [Spacer(1, 16 * mm)],
                      [Paragraph("Authorised Signatory", _S["footer"])]],
                     colWidths=[CONTENT_W / 2 - 4 * mm])
        sign.setStyle(TableStyle([
            ("ALIGN", (0, 0), (-1, -1), "RIGHT"),
            ("LINEABOVE", (0, 2), (0, 2), 0.5, colors.HexColor("#999999")),
            ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ]))
        story += [Spacer(1, 9),
                  KeepTogether(_party_row(_card("BANK / PAYMENT DETAILS", bank_rows), sign))]

    doc.build(story)
    return buffer.getvalue()

