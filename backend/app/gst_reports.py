from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload, selectinload

from . import models
from .services import (
    ACCOUNT_BANK,
    ACCOUNT_CASH,
    ACCOUNT_INPUT_CGST,
    ACCOUNT_INPUT_IGST,
    ACCOUNT_INPUT_SGST,
    ACCOUNT_OUTPUT_CGST,
    ACCOUNT_OUTPUT_IGST,
    ACCOUNT_OUTPUT_SGST,
    ACCOUNT_OWNERS_CAPITAL,
    ACCOUNT_SALES,
    ACCOUNT_SALES_RETURNS,
    list_chart_of_accounts,
    money,
)

CASH_FLOW_SOURCE_LABELS = {
    "Payment": "Cash received from customers",
    "VendorPayment": "Cash paid to vendors",
    "Expense": "Cash paid for expenses",
    "Manual": "Manual adjustments",
    "ManualReversal": "Manual adjustment reversals",
    "OpeningBalance": "Opening balances",
    "FixedAsset": "Purchase of fixed assets",
    "FixedAssetDisposal": "Proceeds from sale of fixed assets",
}
INVESTING_SOURCE_TYPES = {"FixedAsset", "FixedAssetDisposal"}

# Standard CBIC/GST state codes (used as the "pos" / place-of-supply field in the GSTN
# return JSON). This table is entered from general knowledge, not fetched from an
# authoritative source at runtime - cross-check it against the current official list
# (gst.gov.in) before relying on it for a real filing.
GST_STATE_CODES = {
    "Jammu and Kashmir": "01",
    "Himachal Pradesh": "02",
    "Punjab": "03",
    "Chandigarh": "04",
    "Uttarakhand": "05",
    "Haryana": "06",
    "Delhi": "07",
    "Rajasthan": "08",
    "Uttar Pradesh": "09",
    "Bihar": "10",
    "Sikkim": "11",
    "Arunachal Pradesh": "12",
    "Nagaland": "13",
    "Manipur": "14",
    "Mizoram": "15",
    "Tripura": "16",
    "Meghalaya": "17",
    "Assam": "18",
    "West Bengal": "19",
    "Jharkhand": "20",
    "Odisha": "21",
    "Chhattisgarh": "22",
    "Madhya Pradesh": "23",
    "Gujarat": "24",
    "Dadra and Nagar Haveli and Daman and Diu": "26",
    "Maharashtra": "27",
    "Karnataka": "29",
    "Goa": "30",
    "Lakshadweep": "31",
    "Kerala": "32",
    "Tamil Nadu": "33",
    "Puducherry": "34",
    "Andaman and Nicobar Islands": "35",
    "Telangana": "36",
    "Andhra Pradesh": "37",
    "Ladakh": "38",
}


def _place_of_supply_code(customer_gstin: str, customer_state: str, business_state: str) -> str:
    gstin = (customer_gstin or "").strip()
    if len(gstin) >= 2 and gstin[:2].isdigit():
        return gstin[:2]
    if customer_state in GST_STATE_CODES:
        return GST_STATE_CODES[customer_state]
    if business_state in GST_STATE_CODES:
        return GST_STATE_CODES[business_state]
    return "00"


def _account_totals(db: Session, code: str, from_date: date | None, to_date: date | None) -> tuple[Decimal, Decimal]:
    account = db.scalar(select(models.ChartOfAccount).where(models.ChartOfAccount.code == code))
    if not account:
        return Decimal("0"), Decimal("0")
    stmt = select(models.JournalLine).join(models.JournalEntry).where(models.JournalLine.account_id == account.id)
    if from_date:
        stmt = stmt.where(models.JournalEntry.entry_date >= from_date)
    if to_date:
        stmt = stmt.where(models.JournalEntry.entry_date <= to_date)
    lines = db.scalars(stmt).all()
    debit = money(sum((Decimal(line.debit) for line in lines), Decimal("0")))
    credit = money(sum((Decimal(line.credit) for line in lines), Decimal("0")))
    return debit, credit


def gstr3b_report(db: Session, from_date: date, to_date: date) -> dict:
    sales_debit, sales_credit = _account_totals(db, ACCOUNT_SALES, from_date, to_date)
    returns_debit, returns_credit = _account_totals(db, ACCOUNT_SALES_RETURNS, from_date, to_date)
    out_cgst_debit, out_cgst_credit = _account_totals(db, ACCOUNT_OUTPUT_CGST, from_date, to_date)
    out_sgst_debit, out_sgst_credit = _account_totals(db, ACCOUNT_OUTPUT_SGST, from_date, to_date)
    out_igst_debit, out_igst_credit = _account_totals(db, ACCOUNT_OUTPUT_IGST, from_date, to_date)
    in_cgst_debit, in_cgst_credit = _account_totals(db, ACCOUNT_INPUT_CGST, from_date, to_date)
    in_sgst_debit, in_sgst_credit = _account_totals(db, ACCOUNT_INPUT_SGST, from_date, to_date)
    in_igst_debit, in_igst_credit = _account_totals(db, ACCOUNT_INPUT_IGST, from_date, to_date)

    taxable_outward = money((sales_credit - sales_debit) - (returns_debit - returns_credit))
    output_cgst = money(out_cgst_credit - out_cgst_debit)
    output_sgst = money(out_sgst_credit - out_sgst_debit)
    output_igst = money(out_igst_credit - out_igst_debit)
    input_cgst = money(in_cgst_debit - in_cgst_credit)
    input_sgst = money(in_sgst_debit - in_sgst_credit)
    input_igst = money(in_igst_debit - in_igst_credit)
    net_cgst_payable = money(max(Decimal("0"), output_cgst - input_cgst))
    net_sgst_payable = money(max(Decimal("0"), output_sgst - input_sgst))
    net_igst_payable = money(max(Decimal("0"), output_igst - input_igst))

    return {
        "period": {"from": from_date.isoformat(), "to": to_date.isoformat()},
        "outward_taxable_supplies": {
            "taxable_value": float(taxable_outward),
            "cgst": float(output_cgst),
            "sgst": float(output_sgst),
            "igst": float(output_igst),
            "total_tax": float(money(output_cgst + output_sgst + output_igst)),
        },
        "eligible_itc": {
            "cgst": float(input_cgst),
            "sgst": float(input_sgst),
            "igst": float(input_igst),
            "total_itc": float(money(input_cgst + input_sgst + input_igst)),
        },
        "net_tax_payable": {
            "cgst": float(net_cgst_payable),
            "sgst": float(net_sgst_payable),
            "igst": float(net_igst_payable),
            "total": float(money(net_cgst_payable + net_sgst_payable + net_igst_payable)),
        },
    }


def hsn_summary_report(db: Session, from_date: date, to_date: date) -> list[dict]:
    rows: dict[str, dict] = {}

    def add(hsn: str, category: str, unit: str, quantity, taxable, tax, sign: int) -> None:
        key = hsn or "(No HSN)"
        entry = rows.setdefault(key, {"hsn_code": key, "description": category or "", "unit": unit or "", "quantity": Decimal("0"), "taxable_value": Decimal("0"), "tax_amount": Decimal("0")})
        entry["quantity"] += sign * Decimal(quantity)
        entry["taxable_value"] += sign * Decimal(taxable)
        entry["tax_amount"] += sign * Decimal(tax)
        if not entry["description"] and category:
            entry["description"] = category

    invoice_items = db.scalars(
        select(models.InvoiceItem).join(models.Invoice).where(
            models.Invoice.status != "Cancelled",
            models.Invoice.quotation_id.is_not(None),  # excludes synthetic opening-balance invoices
            models.Invoice.invoice_date >= from_date,
            models.Invoice.invoice_date <= to_date,
        )
    ).all()
    for item in invoice_items:
        tax = money(Decimal(item.amount) * Decimal(item.gst_percent) / Decimal("100"))
        add(item.hsn_code, item.category, item.unit, item.quantity, item.amount, tax, 1)

    credit_items = db.scalars(
        select(models.CreditNoteItem).join(models.CreditNote).where(
            models.CreditNote.status != "Cancelled",
            models.CreditNote.note_date >= from_date,
            models.CreditNote.note_date <= to_date,
        )
    ).all()
    for item in credit_items:
        tax = money(Decimal(item.amount) * Decimal(item.gst_percent) / Decimal("100"))
        add(item.hsn_code, item.category, item.unit, item.quantity, item.amount, tax, -1)

    debit_items = db.scalars(
        select(models.DebitNoteItem).join(models.DebitNote).where(
            models.DebitNote.status != "Cancelled",
            models.DebitNote.note_date >= from_date,
            models.DebitNote.note_date <= to_date,
        )
    ).all()
    for item in debit_items:
        tax = money(Decimal(item.amount) * Decimal(item.gst_percent) / Decimal("100"))
        add(item.hsn_code, item.category, item.unit, item.quantity, item.amount, tax, 1)

    result = []
    for entry in rows.values():
        taxable_value = money(entry["taxable_value"])
        tax_amount = money(entry["tax_amount"])
        result.append({
            "hsn_code": entry["hsn_code"],
            "description": entry["description"],
            "unit": entry["unit"],
            "quantity": float(entry["quantity"]),
            "taxable_value": float(taxable_value),
            "tax_amount": float(tax_amount),
            "total_value": float(money(taxable_value + tax_amount)),
        })
    result.sort(key=lambda row: row["hsn_code"])
    return result


def gstr1_report(db: Session, from_date: date, to_date: date) -> dict:
    invoices = db.scalars(
        select(models.Invoice)
        .options(joinedload(models.Invoice.customer))
        .where(
            models.Invoice.status != "Cancelled",
            models.Invoice.quotation_id.is_not(None),  # excludes synthetic opening-balance invoices
            models.Invoice.invoice_date >= from_date,
            models.Invoice.invoice_date <= to_date,
        )
    ).unique().all()

    b2b = []
    b2c_buckets: dict[str, dict] = {}
    for invoice in invoices:
        total_tax = Decimal(invoice.cgst) + Decimal(invoice.sgst) + Decimal(invoice.igst)
        taxable = money(Decimal(invoice.grand_total) - total_tax)
        rate = money(total_tax / taxable * 100) if taxable > 0 else Decimal("0")
        if invoice.customer.gst_number:
            b2b.append({
                "gstin": invoice.customer.gst_number,
                "customer_name": invoice.customer.name,
                "invoice_number": invoice.number,
                "invoice_date": invoice.invoice_date.isoformat(),
                "invoice_value": float(invoice.grand_total),
                "taxable_value": float(taxable),
                "rate": float(rate),
                "cgst": float(invoice.cgst),
                "sgst": float(invoice.sgst),
                "igst": float(invoice.igst),
            })
        else:
            key = str(rate)
            bucket = b2c_buckets.setdefault(key, {"rate": float(rate), "taxable_value": Decimal("0"), "cgst": Decimal("0"), "sgst": Decimal("0"), "igst": Decimal("0")})
            bucket["taxable_value"] += taxable
            bucket["cgst"] += Decimal(invoice.cgst)
            bucket["sgst"] += Decimal(invoice.sgst)
            bucket["igst"] += Decimal(invoice.igst)

    b2c = [
        {"rate": b["rate"], "taxable_value": float(money(b["taxable_value"])), "cgst": float(money(b["cgst"])), "sgst": float(money(b["sgst"])), "igst": float(money(b["igst"]))}
        for b in b2c_buckets.values()
    ]

    credit_notes = db.scalars(
        select(models.CreditNote)
        .options(joinedload(models.CreditNote.customer), joinedload(models.CreditNote.invoice))
        .where(models.CreditNote.status != "Cancelled", models.CreditNote.note_date >= from_date, models.CreditNote.note_date <= to_date)
    ).unique().all()
    debit_notes = db.scalars(
        select(models.DebitNote)
        .options(joinedload(models.DebitNote.customer), joinedload(models.DebitNote.invoice))
        .where(models.DebitNote.status != "Cancelled", models.DebitNote.note_date >= from_date, models.DebitNote.note_date <= to_date)
    ).unique().all()

    cdnr = []
    for note in credit_notes:
        cdnr.append({"type": "Credit Note", "note_number": note.number, "note_date": note.note_date.isoformat(), "against_invoice": note.invoice.number, "gstin": note.customer.gst_number or "-", "customer_name": note.customer.name, "taxable_value": float(note.subtotal), "tax_amount": float(note.gst)})
    for note in debit_notes:
        cdnr.append({"type": "Debit Note", "note_number": note.number, "note_date": note.note_date.isoformat(), "against_invoice": note.invoice.number, "gstin": note.customer.gst_number or "-", "customer_name": note.customer.name, "taxable_value": float(note.subtotal), "tax_amount": float(note.gst)})

    return {
        "period": {"from": from_date.isoformat(), "to": to_date.isoformat()},
        "b2b": b2b,
        "b2c": b2c,
        "cdnr": cdnr,
        "hsn_summary": hsn_summary_report(db, from_date, to_date),
        "totals": {
            "b2b_taxable_value": float(money(sum((Decimal(str(r["taxable_value"])) for r in b2b), Decimal("0")))),
            "b2c_taxable_value": float(money(sum((Decimal(str(r["taxable_value"])) for r in b2c), Decimal("0")))),
        },
    }


def gstr1_offline_json(db: Session, from_date: date, to_date: date) -> dict:
    """GSTR-1 in the JSON shape the GST portal's offline return tool expects for
    upload (gstin/fp/b2b/b2cs/cdnr/hsn). Intended for a single return period - pass
    from_date/to_date spanning one calendar month; fp is derived from from_date."""
    settings = db.get(models.BusinessSettings, 1)
    business_gstin = (settings.gst_number if settings else "") or ""
    business_state = (settings.state if settings else "") or ""
    fp = from_date.strftime("%m%Y")

    invoices = db.scalars(
        select(models.Invoice)
        .options(joinedload(models.Invoice.customer))
        .where(
            models.Invoice.status != "Cancelled",
            models.Invoice.quotation_id.is_not(None),  # excludes synthetic opening-balance invoices
            models.Invoice.invoice_date >= from_date,
            models.Invoice.invoice_date <= to_date,
        )
    ).unique().all()

    b2b_by_gstin: dict[str, list[dict]] = {}
    b2cs_buckets: dict[tuple, dict] = {}

    for invoice in invoices:
        total_tax = Decimal(invoice.cgst) + Decimal(invoice.sgst) + Decimal(invoice.igst)
        taxable = money(Decimal(invoice.grand_total) - total_tax)
        rate = float(money(total_tax / taxable * 100)) if taxable > 0 else 0.0
        pos = _place_of_supply_code(invoice.customer.gst_number, invoice.customer.state, business_state)
        item = {"num": 1, "itm_det": {"rt": rate, "txval": float(taxable), "iamt": float(invoice.igst), "camt": float(invoice.cgst), "samt": float(invoice.sgst), "csamt": 0.0}}

        if invoice.customer.gst_number:
            inv = {
                "inum": invoice.number,
                "idt": invoice.invoice_date.strftime("%d-%m-%Y"),
                "val": float(invoice.grand_total),
                "pos": pos,
                "rchrg": "N",
                "inv_typ": "R",
                "itms": [item],
            }
            b2b_by_gstin.setdefault(invoice.customer.gst_number, []).append(inv)
        else:
            sply_ty = "INTER" if Decimal(invoice.igst) > 0 else "INTRA"
            key = (sply_ty, pos, rate)
            bucket = b2cs_buckets.setdefault(key, {"sply_ty": sply_ty, "pos": pos, "typ": "OE", "rt": rate, "txval": Decimal("0"), "iamt": Decimal("0"), "camt": Decimal("0"), "samt": Decimal("0")})
            bucket["txval"] += taxable
            bucket["iamt"] += Decimal(invoice.igst)
            bucket["camt"] += Decimal(invoice.cgst)
            bucket["samt"] += Decimal(invoice.sgst)

    b2b = [{"ctin": gstin, "inv": invs} for gstin, invs in b2b_by_gstin.items()]
    b2cs = [
        {"sply_ty": b["sply_ty"], "pos": b["pos"], "typ": b["typ"], "rt": b["rt"], "txval": float(money(b["txval"])), "iamt": float(money(b["iamt"])), "camt": float(money(b["camt"])), "samt": float(money(b["samt"]))}
        for b in b2cs_buckets.values()
    ]

    credit_notes = db.scalars(
        select(models.CreditNote)
        .options(joinedload(models.CreditNote.customer), joinedload(models.CreditNote.invoice))
        .where(models.CreditNote.status != "Cancelled", models.CreditNote.note_date >= from_date, models.CreditNote.note_date <= to_date)
    ).unique().all()
    debit_notes = db.scalars(
        select(models.DebitNote)
        .options(joinedload(models.DebitNote.customer), joinedload(models.DebitNote.invoice))
        .where(models.DebitNote.status != "Cancelled", models.DebitNote.note_date >= from_date, models.DebitNote.note_date <= to_date)
    ).unique().all()

    cdnr_by_gstin: dict[str, list[dict]] = {}
    for ntty, notes in (("C", credit_notes), ("D", debit_notes)):
        for note in notes:
            if not note.customer.gst_number:
                continue  # unregistered-recipient notes (CDNUR) are a separate section, not modeled here
            interstate = Decimal(note.invoice.igst or 0) > 0
            gst = money(note.gst)
            if interstate:
                iamt, camt, samt = float(gst), 0.0, 0.0
            else:
                half = money(gst / 2)
                iamt, camt, samt = 0.0, float(half), float(money(gst - half))
            rate = float(money(gst / note.subtotal * 100)) if Decimal(note.subtotal) > 0 else 0.0
            pos = _place_of_supply_code(note.customer.gst_number, note.customer.state, business_state)
            nt = {
                "ntty": ntty,
                "nt_num": note.number,
                "nt_dt": note.note_date.strftime("%d-%m-%Y"),
                "val": float(note.grand_total),
                "pos": pos,
                "rchrg": "N",
                "inv_typ": "R",
                "itms": [{"num": 1, "itm_det": {"rt": rate, "txval": float(note.subtotal), "iamt": iamt, "camt": camt, "samt": samt, "csamt": 0.0}}],
            }
            cdnr_by_gstin.setdefault(note.customer.gst_number, []).append(nt)
    cdnr = [{"ctin": gstin, "nt": notes} for gstin, notes in cdnr_by_gstin.items()]

    hsn_rows: dict[str, dict] = {}

    invoice_items = db.scalars(
        select(models.InvoiceItem)
        .join(models.Invoice)
        .options(joinedload(models.InvoiceItem.invoice))
        .where(
            models.Invoice.status != "Cancelled",
            models.Invoice.quotation_id.is_not(None),
            models.Invoice.invoice_date >= from_date,
            models.Invoice.invoice_date <= to_date,
        )
    ).all()

    def _apply(hsn_code: str, category: str, unit: str, quantity, amount, gst_percent, interstate: bool, sign: int) -> None:
        tax = money(Decimal(amount) * Decimal(gst_percent) / Decimal("100"))
        if interstate:
            iamt, camt, samt = tax, Decimal("0"), Decimal("0")
        else:
            camt = money(tax / 2)
            iamt, samt = Decimal("0"), money(tax - camt)
        key = hsn_code or "(No HSN)"
        row = hsn_rows.setdefault(key, {"hsn_sc": key, "desc": category or "", "uqc": (unit or "OTH").upper()[:3], "qty": Decimal("0"), "val": Decimal("0"), "txval": Decimal("0"), "iamt": Decimal("0"), "camt": Decimal("0"), "samt": Decimal("0")})
        row["qty"] += sign * Decimal(quantity)
        row["txval"] += sign * Decimal(amount)
        row["val"] += sign * (Decimal(amount) + tax)
        row["iamt"] += sign * iamt
        row["camt"] += sign * camt
        row["samt"] += sign * samt

    for item in invoice_items:
        interstate = Decimal(item.invoice.igst or 0) > 0
        _apply(item.hsn_code, item.category, item.unit, item.quantity, item.amount, item.gst_percent, interstate, 1)

    credit_note_items = db.scalars(
        select(models.CreditNoteItem).join(models.CreditNote).options(joinedload(models.CreditNoteItem.credit_note).joinedload(models.CreditNote.invoice))
        .where(models.CreditNote.status != "Cancelled", models.CreditNote.note_date >= from_date, models.CreditNote.note_date <= to_date)
    ).all()
    for item in credit_note_items:
        interstate = Decimal(item.credit_note.invoice.igst or 0) > 0
        _apply(item.hsn_code, item.category, item.unit, item.quantity, item.amount, item.gst_percent, interstate, -1)

    debit_note_items = db.scalars(
        select(models.DebitNoteItem).join(models.DebitNote).options(joinedload(models.DebitNoteItem.debit_note).joinedload(models.DebitNote.invoice))
        .where(models.DebitNote.status != "Cancelled", models.DebitNote.note_date >= from_date, models.DebitNote.note_date <= to_date)
    ).all()
    for item in debit_note_items:
        interstate = Decimal(item.debit_note.invoice.igst or 0) > 0
        _apply(item.hsn_code, item.category, item.unit, item.quantity, item.amount, item.gst_percent, interstate, 1)

    hsn_data = [
        {
            "num": i + 1, "hsn_sc": row["hsn_sc"], "desc": row["desc"], "uqc": row["uqc"],
            "qty": float(row["qty"]), "val": float(money(row["val"])), "txval": float(money(row["txval"])),
            "iamt": float(money(row["iamt"])), "camt": float(money(row["camt"])), "samt": float(money(row["samt"])), "csamt": 0.0,
        }
        for i, row in enumerate(sorted(hsn_rows.values(), key=lambda r: r["hsn_sc"]))
    ]

    return {
        "gstin": business_gstin,
        "fp": fp,
        "b2b": b2b,
        "b2cs": b2cs,
        "cdnr": cdnr,
        "hsn": {"data": hsn_data},
    }


def sales_register(db: Session, from_date: date, to_date: date) -> list[dict]:
    invoices = db.scalars(
        select(models.Invoice)
        .options(joinedload(models.Invoice.customer))
        .where(
            models.Invoice.quotation_id.is_not(None),  # excludes synthetic opening-balance invoices
            models.Invoice.invoice_date >= from_date,
            models.Invoice.invoice_date <= to_date,
        )
        .order_by(models.Invoice.invoice_date)
    ).unique().all()
    return [
        {
            "date": invoice.invoice_date.isoformat(),
            "number": invoice.number,
            "party": invoice.customer.name,
            "gstin": invoice.customer.gst_number or "-",
            "taxable_value": float(money(Decimal(invoice.grand_total) - Decimal(invoice.cgst) - Decimal(invoice.sgst) - Decimal(invoice.igst))),
            "cgst": float(invoice.cgst),
            "sgst": float(invoice.sgst),
            "igst": float(invoice.igst),
            "total": float(invoice.grand_total),
            "status": invoice.status,
        }
        for invoice in invoices
    ]


def purchase_register(db: Session, from_date: date, to_date: date) -> list[dict]:
    bills = db.scalars(
        select(models.PurchaseBill)
        .options(joinedload(models.PurchaseBill.vendor))
        .where(models.PurchaseBill.bill_date >= from_date, models.PurchaseBill.bill_date <= to_date)
        .order_by(models.PurchaseBill.bill_date)
    ).unique().all()
    return [
        {
            "date": bill.bill_date.isoformat(),
            "number": bill.number,
            "vendor_bill_number": bill.vendor_bill_number,
            "party": bill.vendor.name,
            "gstin": bill.vendor.gst_number or "-",
            "taxable_value": float(bill.subtotal),
            "cgst": float(bill.cgst),
            "sgst": float(bill.sgst),
            "igst": float(bill.igst),
            "total": float(bill.grand_total),
            "status": bill.status,
        }
        for bill in bills
    ]


def profit_and_loss_report(db: Session, from_date: date, to_date: date) -> dict:
    income_rows, expense_rows = [], []
    total_income = total_expense = Decimal("0")
    for account in list_chart_of_accounts(db):
        debit, credit = _account_totals(db, account.code, from_date, to_date)
        if account.account_type == "Income":
            net = money(credit - debit)
            if net != 0:
                income_rows.append({"code": account.code, "name": account.name, "amount": float(net)})
                total_income += net
        elif account.account_type == "Expense":
            net = money(debit - credit)
            if net != 0:
                expense_rows.append({"code": account.code, "name": account.name, "amount": float(net)})
                total_expense += net
    return {
        "period": {"from": from_date.isoformat(), "to": to_date.isoformat()},
        "income": income_rows,
        "expenses": expense_rows,
        "total_income": float(total_income),
        "total_expense": float(total_expense),
        "net_profit": float(money(total_income - total_expense)),
    }


def balance_sheet_report(db: Session, as_of_date: date) -> dict:
    assets, liabilities, equity = [], [], []
    total_assets = total_liabilities = total_equity = Decimal("0")
    income_total = expense_total = Decimal("0")
    for account in list_chart_of_accounts(db):
        debit, credit = _account_totals(db, account.code, None, as_of_date)
        if account.account_type == "Asset":
            net = money(debit - credit)
            if net != 0:
                assets.append({"code": account.code, "name": account.name, "amount": float(net)})
                total_assets += net
        elif account.account_type == "Liability":
            net = money(credit - debit)
            if net != 0:
                liabilities.append({"code": account.code, "name": account.name, "amount": float(net)})
                total_liabilities += net
        elif account.account_type == "Equity":
            net = money(credit - debit)
            if net != 0:
                equity.append({"code": account.code, "name": account.name, "amount": float(net)})
                total_equity += net
        elif account.account_type == "Income":
            income_total += money(credit - debit)
        elif account.account_type == "Expense":
            expense_total += money(debit - credit)

    retained_earnings = money(income_total - expense_total)
    if retained_earnings != 0:
        equity.append({"code": "3900", "name": "Retained Earnings (Current Period)", "amount": float(retained_earnings)})
        total_equity += retained_earnings

    total_liabilities_and_equity = money(total_liabilities + total_equity)
    return {
        "as_of": as_of_date.isoformat(),
        "assets": assets,
        "liabilities": liabilities,
        "equity": equity,
        "total_assets": float(total_assets),
        "total_liabilities": float(total_liabilities),
        "total_equity": float(total_equity),
        "balanced": abs(float(total_assets) - float(total_liabilities_and_equity)) < 0.01,
    }


def cash_flow_statement(db: Session, from_date: date, to_date: date) -> dict:
    cash_account_ids = {
        a.id for a in db.scalars(select(models.ChartOfAccount).where(models.ChartOfAccount.code.in_([ACCOUNT_CASH, ACCOUNT_BANK]))).all()
    }
    cash_lines = []
    if cash_account_ids:
        stmt = (
            select(models.JournalLine)
            .join(models.JournalEntry)
            .where(
                models.JournalLine.account_id.in_(cash_account_ids),
                models.JournalEntry.entry_date >= from_date,
                models.JournalEntry.entry_date <= to_date,
            )
            .options(joinedload(models.JournalLine.entry).selectinload(models.JournalEntry.lines).joinedload(models.JournalLine.account))
        )
        cash_lines = db.scalars(stmt).unique().all()

    operating: dict[str, Decimal] = {}
    investing: dict[str, Decimal] = {}
    financing: dict[str, Decimal] = {}

    for line in cash_lines:
        entry = line.entry
        net = money(Decimal(line.debit) - Decimal(line.credit))
        if net == 0:
            continue
        touches_capital = any(sibling.account.code == ACCOUNT_OWNERS_CAPITAL for sibling in entry.lines)
        label = CASH_FLOW_SOURCE_LABELS.get(entry.source_type, entry.source_type or "Other")
        if touches_capital:
            bucket = financing
        elif entry.source_type in INVESTING_SOURCE_TYPES:
            bucket = investing
        else:
            bucket = operating
        bucket[label] = bucket.get(label, Decimal("0")) + net

    def _rows(bucket: dict[str, Decimal]) -> list[dict]:
        return [{"label": label, "amount": float(money(amount))} for label, amount in sorted(bucket.items()) if amount != 0]

    operating_total = money(sum(operating.values(), Decimal("0")))
    investing_total = money(sum(investing.values(), Decimal("0")))
    financing_total = money(sum(financing.values(), Decimal("0")))
    net_change = money(operating_total + investing_total + financing_total)

    opening_debit = opening_credit = Decimal("0")
    for code in (ACCOUNT_CASH, ACCOUNT_BANK):
        d, c = _account_totals(db, code, None, from_date - timedelta(days=1))
        opening_debit += d
        opening_credit += c
    opening_balance = money(opening_debit - opening_credit)
    closing_balance = money(opening_balance + net_change)

    return {
        "period": {"from": from_date.isoformat(), "to": to_date.isoformat()},
        "operating_activities": {"rows": _rows(operating), "total": float(operating_total)},
        "investing_activities": {"rows": _rows(investing), "total": float(investing_total)},
        "financing_activities": {"rows": _rows(financing), "total": float(financing_total)},
        "net_change_in_cash": float(net_change),
        "opening_cash_balance": float(opening_balance),
        "closing_cash_balance": float(closing_balance),
    }


def ap_aging_report(db: Session, as_of_date: date) -> dict:
    stmt = (
        select(models.PurchaseBill)
        .where(models.PurchaseBill.status.in_(["Unpaid", "Partially Paid"]))
        .options(joinedload(models.PurchaseBill.vendor))
    )
    bills = db.scalars(stmt).unique().all()

    bucket_keys = ("current", "d1_30", "d31_60", "d61_90", "d90_plus")
    by_vendor: dict[int, dict] = {}
    totals = {key: Decimal("0") for key in bucket_keys}

    for bill in bills:
        pending = Decimal(bill.pending_balance or 0)
        if pending <= 0:
            continue
        days_overdue = (as_of_date - bill.due_date).days
        if days_overdue <= 0:
            key = "current"
        elif days_overdue <= 30:
            key = "d1_30"
        elif days_overdue <= 60:
            key = "d31_60"
        elif days_overdue <= 90:
            key = "d61_90"
        else:
            key = "d90_plus"
        row = by_vendor.setdefault(bill.vendor_id, {"vendor_id": bill.vendor_id, "vendor_name": bill.vendor.name, **{k: Decimal("0") for k in bucket_keys}})
        row[key] += pending
        totals[key] += pending

    rows = []
    for row in sorted(by_vendor.values(), key=lambda r: r["vendor_name"]):
        total = money(sum((row[k] for k in bucket_keys), Decimal("0")))
        rows.append({"vendor_id": row["vendor_id"], "vendor_name": row["vendor_name"], **{k: float(money(row[k])) for k in bucket_keys}, "total": float(total)})

    grand_total = money(sum(totals.values(), Decimal("0")))
    return {
        "as_of": as_of_date.isoformat(),
        "rows": rows,
        "totals": {**{k: float(money(v)) for k, v in totals.items()}, "total": float(grand_total)},
    }
