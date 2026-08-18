"""Quotation and invoice PDFs built from the reference HTML template.

The CSS is copied verbatim from quotation_template_final_a4.html; only the
print-specific rules from that file's @media print block are applied inline
(white background, no shadow, auto height) plus an @page rule so Chromium emits
a true A4 page. Both documents share the same shell, so a change to the
template's look applies to quotations and invoices alike.
"""
from __future__ import annotations

import base64
from datetime import timedelta
from decimal import Decimal
from html import escape
from pathlib import Path

from .database import DEFAULT_DB_PATH
from .html_pdf import render_pdf
from .models import BusinessSettings, Invoice, Quotation

UPLOAD_DIR = DEFAULT_DB_PATH.parent / "uploads"

_LOGO_MIME = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp"}

# Verbatim from quotation_template_final_a4.html, with its @media print rules
# folded in and an @page rule added so Chromium emits a real A4 page.
_BASE_CSS = """
        @page { size: A4; margin: 0; }
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: white;
            padding: 0;
            -webkit-print-color-adjust: exact;
            print-color-adjust: exact;
        }
        .a4-container {
            max-width: 210mm;
            min-height: 297mm;
            background: white;
            margin: 0 auto;
            padding: 20px;
            overflow: visible;
        }

        /* Header Section */
        .header {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            border-bottom: 2px solid #0d47a1;
            padding-bottom: 15px;
            margin-bottom: 15px;
        }
        .logo-section {
            width: 120px;
            height: 60px;
            background: #e8eef7;
            border: 2px dashed #0d47a1;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 10px;
            color: #666;
            border-radius: 4px;
            flex-shrink: 0;
        }
        .logo-section.has-logo { background: none; border: none; }
        .logo-section img { max-width: 100%; max-height: 100%; object-fit: contain; }
        .company-info {
            text-align: right;
            font-size: 12px;
        }
        .company-name {
            font-size: 16px;
            font-weight: 700;
            color: #0d47a1;
            margin-bottom: 3px;
        }
        .company-details {
            font-size: 10px;
            color: #666;
            line-height: 1.4;
        }

        /* Title */
        .quote-title {
            font-size: 20px;
            font-weight: 700;
            margin-bottom: 12px;
            color: #1a1a1a;
        }

        /* Two Column Section */
        .info-section {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
            margin-bottom: 12px;
            font-size: 11px;
        }
        .info-block {
            background: #f5f5f5;
            padding: 10px;
            border-radius: 4px;
        }
        .info-label {
            font-weight: 600;
            color: #333;
            margin-bottom: 4px;
            font-size: 10px;
        }
        .info-value {
            color: #666;
            line-height: 1.5;
        }
        .detail-row {
            display: flex;
            justify-content: space-between;
            margin-bottom: 4px;
        }
        .detail-row:last-child { margin-bottom: 0; }
        .detail-row span:last-child { font-weight: 600; }

        /* Items Table */
        .items-section { margin-bottom: 12px; }
        table {
            width: 100%;
            border-collapse: collapse;
            font-size: 10px;
            margin-bottom: 8px;
        }
        th {
            background: #0d47a1;
            color: white;
            padding: 6px;
            text-align: left;
            font-weight: 600;
            border: none;
        }
        td {
            padding: 6px;
            border-bottom: 1px solid #eee;
        }
        tr:last-child td { border-bottom: 2px solid #0d47a1; }
        .item-detail {
            color: #666;
            font-size: 9px;
            margin-top: 2px;
        }
        .num-col { width: 30px; text-align: center; }
        .qty-col { width: 45px; text-align: right; }
        .rate-col { width: 55px; text-align: right; }
        .amount-col { width: 55px; text-align: right; }

        /* Summary Section */
        .summary-section { margin-top: 10px; }
        .summary-row {
            display: flex;
            justify-content: space-between;
            padding: 4px 0;
            font-size: 11px;
            border-bottom: 1px solid #eee;
        }
        .summary-label { font-weight: 500; color: #333; }
        .summary-value { text-align: right; color: #333; font-weight: 500; }
        .total-row {
            border-top: 2px solid #0d47a1;
            border-bottom: 2px solid #0d47a1;
            padding: 6px 0 !important;
            font-size: 12px !important;
            font-weight: 700 !important;
        }
        .discount-row { color: #d32f2f; }
        .balance-row { color: #0d47a1; }
        /* The template sets colour on the row, but .summary-label/.summary-value
           set #333 on the child spans and win. Restate it on the children so the
           discount actually reads red, as the template intends. */
        .discount-row .summary-label,
        .discount-row .summary-value { color: #d32f2f; }
        .balance-row .summary-label,
        .balance-row .summary-value { color: #0d47a1; font-weight: 700; }

        /* Terms/Notes */
        .footer {
            margin-top: 10px;
            font-size: 9px;
            color: #666;
            border-top: 1px solid #ddd;
            padding-top: 8px;
        }
        .footer-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
            margin-top: 12px;
            font-size: 10px;
        }
        .signature {
            margin-top: 16px;
            text-align: right;
            font-size: 10px;
            color: #333;
        }
        .signature-line {
            display: inline-block;
            min-width: 55mm;
            margin-top: 30px;
            padding-top: 4px;
            border-top: 1px solid #999;
            text-align: center;
            font-size: 9px;
            color: #666;
        }
"""


def _inr(value: object, decimals: int = 2) -> str:
    """Format a number with Indian digit grouping, e.g. 116375.02 -> 1,16,375.02."""
    amount = Decimal(str(value or 0))
    negative = amount < 0
    text = f"{abs(amount):.{decimals}f}"
    whole, _, fraction = text.partition(".")
    if len(whole) > 3:
        head, tail = whole[:-3], whole[-3:]
        groups = []
        while len(head) > 2:
            groups.insert(0, head[-2:])
            head = head[:-2]
        if head:
            groups.insert(0, head)
        whole = ",".join(groups + [tail])
    formatted = f"&#8377;{whole}.{fraction}" if fraction else f"&#8377;{whole}"
    return f"-{formatted}" if negative else formatted


def _num(value: object, decimals: int = 2) -> str:
    return f"{Decimal(str(value or 0)):,.{decimals}f}"


def _pct(part: Decimal, taxable: Decimal) -> str:
    """Derive the effective tax rate from the amounts, so mixed GST slabs stay honest."""
    if taxable <= 0:
        return ""
    rate = (part / taxable * 100).quantize(Decimal("0.01"))
    return f" ({rate.normalize():f}%)"


def _logo_markup(settings: BusinessSettings) -> str:
    """Embed the uploaded logo as a data URI, or fall back to the template placeholder."""
    if settings.logo_path:
        logo_file = UPLOAD_DIR / Path(settings.logo_path).name
        mime = _LOGO_MIME.get(logo_file.suffix.lower())
        if logo_file.exists() and mime:
            encoded = base64.b64encode(logo_file.read_bytes()).decode("ascii")
            return (
                f'<div class="logo-section has-logo">'
                f'<img src="data:{mime};base64,{encoded}" alt="{escape(settings.company_name)}"/>'
                f"</div>"
            )
    return f'<div class="logo-section">{escape(settings.logo_text or "COMPANY LOGO")}</div>'


def _header(settings: BusinessSettings) -> str:
    lines = [escape(line.strip()) for line in (settings.address or "").splitlines() if line.strip()]
    if settings.phone:
        lines.append(f"Phone: {escape(settings.phone)}")
    if settings.email:
        lines.append(f"Email: {escape(settings.email)}")
    if settings.gst_number:
        lines.append(f"GST: {escape(settings.gst_number)}")
    return f"""        <div class="header">
            {_logo_markup(settings)}
            <div class="company-info">
                <div class="company-name">{escape(settings.company_name)}</div>
                <div class="company-details">
                    {"<br/>".join(lines)}
                </div>
            </div>
        </div>"""


def _bill_to_lines(customer, address_override: str = "") -> list[str]:
    lines = [f"<strong>{escape(customer.name)}</strong>"]
    for line in (address_override or customer.address or "").splitlines():
        if line.strip():
            lines.append(escape(line.strip()))
    if customer.phone:
        lines.append(f"Phone: {escape(customer.phone)}")
    if customer.gst_number:
        lines.append(f"GST: {escape(customer.gst_number)}")
    return lines


def _info_section(bill_to: list[str], details_label: str, details: list[tuple[str, str]]) -> str:
    detail_rows = "\n".join(
        f'                    <div class="detail-row"><span>{label}</span> <span>{value}</span></div>'
        for label, value in details
    )
    return f"""        <div class="info-section">
            <div class="info-block">
                <div class="info-label">BILL TO:</div>
                <div class="info-value">
                    {"<br/>".join(bill_to)}
                </div>
            </div>
            <div class="info-block">
                <div class="info-label">{details_label}</div>
                <div class="info-value">
{detail_rows}
                </div>
            </div>
        </div>"""


def _items_table(rows: list[str]) -> str:
    return f"""        <div class="items-section">
            <table>
                <tr>
                    <th class="num-col">S.No</th>
                    <th>Description</th>
                    <th style="width: 40px;">HSN</th>
                    <th class="qty-col">Qty</th>
                    <th style="width: 40px;">Unit</th>
                    <th class="rate-col">Rate</th>
                    <th class="amount-col">Amount</th>
                </tr>
{chr(10).join(rows)}
            </table>
        </div>"""


def _item_row(index: int, description: str, detail: str, hsn: str, qty: str, unit: str, rate: str, amount: str) -> str:
    body = escape(description)
    if detail:
        body += f'<div class="item-detail">{detail}</div>'
    return f"""                <tr>
                    <td class="num-col">{index}</td>
                    <td>{body}</td>
                    <td>{escape(hsn or "-")}</td>
                    <td class="qty-col">{qty}</td>
                    <td>{escape(unit)}</td>
                    <td class="rate-col">{rate}</td>
                    <td class="amount-col">{amount}</td>
                </tr>"""


def _summary(rows: list[tuple[str, str, str]]) -> str:
    body = "\n".join(
        f"""            <div class="summary-row{extra}">
                <span class="summary-label">{label}</span>
                <span class="summary-value">{value}</span>
            </div>"""
        for label, value, extra in rows
    )
    return f"""        <div class="summary-section">
{body}
        </div>"""


def _tax_rows(cgst: Decimal, sgst: Decimal, igst: Decimal, taxable: Decimal) -> list[tuple[str, str, str]]:
    if igst > 0:
        return [(f"IGST{_pct(igst, taxable)}:", _inr(igst), "")]
    return [
        (f"CGST{_pct(cgst, taxable)}:", _inr(cgst), ""),
        (f"SGST{_pct(sgst, taxable)}:", _inr(sgst), ""),
    ]


def _document(title: str, heading: str, sections: list[str]) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>{escape(title)}</title>
    <style>{_BASE_CSS}    </style>
</head>
<body>
    <div class="a4-container">
{chr(10).join(sections[:1])}

        <div class="quote-title">{heading}</div>

{chr(10).join(sections[1:])}
    </div>
</body>
</html>
"""


# --------------------------------------------------------------------------- #
# Quotation
# --------------------------------------------------------------------------- #

def build_quotation_html(quotation: Quotation, settings: BusinessSettings) -> str:
    rows = []
    for index, item in enumerate(quotation.items, 1):
        size = ""
        if item.width_mm and item.height_mm:
            size = f"{_num(item.width_mm, 0)} x {_num(item.height_mm, 0)} mm"
        detail = " &middot; ".join(
            part
            for part in (size, f"{item.quantity} nos" if item.quantity else "", escape(item.location or ""))
            if part
        )
        rows.append(_item_row(
            index,
            " ".join(part for part in (item.category, item.style) if part),
            detail,
            item.hsn_code,
            _num(item.total_sft),
            "Sq. Ft.",
            _inr(item.rate_per_sft),
            _inr(item.amount),
        ))

    subtotal = Decimal(quotation.subtotal or 0)
    transport = Decimal(quotation.transport or 0)
    discount = Decimal(quotation.discount or 0)
    gst = Decimal(quotation.gst or 0)
    taxable_charges = sum((Decimal(c.amount or 0) for c in quotation.charges if c.taxable), Decimal("0"))
    taxable = subtotal + transport + taxable_charges - discount

    summary: list[tuple[str, str, str]] = [("Subtotal:", _inr(subtotal), "")]
    if transport > 0:
        summary.append(("Transport:", _inr(transport), ""))
    for charge in quotation.charges:
        if charge.taxable:
            summary.append((f"{escape(charge.label)}:", _inr(charge.amount), ""))
    if discount > 0:
        summary.append(("Discount:", f"-{_inr(discount)}", " discount-row"))
    if discount > 0 or quotation.charges or transport > 0:
        summary.append(("Taxable Value:", _inr(taxable), ""))

    # Quotations store one GST figure; split it the way the invoice does -
    # IGST when the customer is in another state, else CGST + SGST.
    customer_state = (quotation.customer.state or "").strip().lower()
    business_state = (settings.state or "").strip().lower()
    if customer_state and business_state and customer_state != business_state:
        summary.extend(_tax_rows(Decimal(0), Decimal(0), gst, taxable))
    else:
        half = (gst / 2).quantize(Decimal("0.01"))
        summary.extend(_tax_rows(half, gst - half, Decimal(0), taxable))
    # Non-taxable charges sit after the tax lines so the column adds up in reading order.
    for charge in quotation.charges:
        if not charge.taxable:
            summary.append((f"{escape(charge.label)} (no GST):", _inr(charge.amount), ""))
    summary.append(("GRAND TOTAL:", _inr(quotation.grand_total), " total-row"))

    valid_till = quotation.quotation_date + timedelta(days=quotation.validity_days or 0)
    terms = (quotation.quotation_terms or "").strip() or (settings.quotation_terms or "").strip()

    return _document(
        f"Quotation - {quotation.number}",
        "QUOTATION",
        [
            _header(settings),
            _info_section(
                _bill_to_lines(quotation.customer, quotation.address),
                "QUOTATION DETAILS",
                [
                    ("Ref No:", escape(quotation.number)),
                    ("Date:", quotation.quotation_date.strftime("%d-%b-%Y")),
                    ("Valid Till:", valid_till.strftime("%d-%b-%Y")),
                ],
            ),
            _items_table(rows),
            _summary(summary),
            f"""        <div class="footer">
            <strong>Terms &amp; Conditions:</strong> {escape(terms)}
        </div>""",
        ],
    )


def build_quotation_pdf_html(quotation: Quotation, settings: BusinessSettings) -> bytes:
    return render_pdf(build_quotation_html(quotation, settings))


# --------------------------------------------------------------------------- #
# Invoice
# --------------------------------------------------------------------------- #

def build_invoice_html(invoice: Invoice, settings: BusinessSettings) -> str:
    rows = []
    for index, item in enumerate(invoice.items, 1):
        # description already carries category, style and size - no sub-line needed.
        rows.append(_item_row(
            index,
            item.description,
            "",
            item.hsn_code,
            _num(item.quantity),
            item.unit or "Nos",
            _inr(item.rate),
            _inr(item.amount),
        ))

    subtotal = Decimal(invoice.subtotal or 0)
    transport = Decimal(invoice.transport or 0)
    discount = Decimal(invoice.discount or 0)
    taxable_charges = sum((Decimal(c.amount or 0) for c in invoice.charges if c.taxable), Decimal("0"))
    taxable = subtotal + transport + taxable_charges - discount

    summary: list[tuple[str, str, str]] = [("Subtotal:", _inr(subtotal), "")]
    if transport > 0:
        summary.append(("Transport:", _inr(transport), ""))
    for charge in invoice.charges:
        if charge.taxable:
            summary.append((f"{escape(charge.label)}:", _inr(charge.amount), ""))
    if discount > 0:
        summary.append(("Discount:", f"-{_inr(discount)}", " discount-row"))
    if discount > 0 or invoice.charges or transport > 0:
        summary.append(("Taxable Value:", _inr(taxable), ""))
    summary.extend(_tax_rows(
        Decimal(invoice.cgst or 0), Decimal(invoice.sgst or 0), Decimal(invoice.igst or 0), taxable
    ))
    # Non-taxable charges sit after the tax lines so the column adds up in reading order.
    for charge in invoice.charges:
        if not charge.taxable:
            summary.append((f"{escape(charge.label)} (no GST):", _inr(charge.amount), ""))
    summary.append(("GRAND TOTAL:", _inr(invoice.grand_total), " total-row"))
    if Decimal(invoice.paid_amount or 0) > 0:
        summary.append(("Amount Paid:", _inr(invoice.paid_amount), ""))
        summary.append(("Balance Due:", _inr(invoice.pending_balance), " balance-row"))

    terms = (settings.invoice_terms or "").strip()
    bank_rows = [
        ("Bank:", escape(settings.bank_name or "")),
        ("Account Name:", escape(settings.account_name or "")),
        ("Account No.:", escape(settings.account_number or "")),
        ("IFSC:", escape(settings.ifsc or "")),
        ("UPI:", escape(settings.upi_id or "")),
    ]
    bank_html = "\n".join(
        f'                    <div class="detail-row"><span>{label}</span> <span>{value}</span></div>'
        for label, value in bank_rows if value
    )

    footer = f"""        <div class="footer">
            <strong>Terms &amp; Conditions:</strong> {escape(terms)}
        </div>

        <div class="footer-grid">
            <div class="info-block">
                <div class="info-label">BANK / PAYMENT DETAILS</div>
                <div class="info-value">
{bank_html}
                </div>
            </div>
            <div class="signature">
                For {escape(settings.company_name)}
                <div class="signature-line">Authorised Signatory</div>
            </div>
        </div>"""

    return _document(
        f"Invoice - {invoice.number}",
        "TAX INVOICE",
        [
            _header(settings),
            _info_section(
                _bill_to_lines(invoice.customer),
                "INVOICE DETAILS",
                [
                    ("Invoice No:", escape(invoice.number)),
                    ("Date:", invoice.invoice_date.strftime("%d-%b-%Y")),
                    ("Due Date:", invoice.due_date.strftime("%d-%b-%Y")),
                    ("Status:", escape(invoice.status)),
                ],
            ),
            _items_table(rows),
            _summary(summary),
            footer,
        ],
    )


def build_invoice_pdf_html(invoice: Invoice, settings: BusinessSettings) -> bytes:
    return render_pdf(build_invoice_html(invoice, settings))
