from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from . import models
from .services import (
    ACCOUNT_INPUT_CGST,
    ACCOUNT_INPUT_SGST,
    ACCOUNT_OUTPUT_CGST,
    ACCOUNT_OUTPUT_SGST,
    ACCOUNT_SALES,
    ACCOUNT_SALES_RETURNS,
    list_chart_of_accounts,
    money,
)


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
    in_cgst_debit, in_cgst_credit = _account_totals(db, ACCOUNT_INPUT_CGST, from_date, to_date)
    in_sgst_debit, in_sgst_credit = _account_totals(db, ACCOUNT_INPUT_SGST, from_date, to_date)

    taxable_outward = money((sales_credit - sales_debit) - (returns_debit - returns_credit))
    output_cgst = money(out_cgst_credit - out_cgst_debit)
    output_sgst = money(out_sgst_credit - out_sgst_debit)
    input_cgst = money(in_cgst_debit - in_cgst_credit)
    input_sgst = money(in_sgst_debit - in_sgst_credit)
    net_cgst_payable = money(max(Decimal("0"), output_cgst - input_cgst))
    net_sgst_payable = money(max(Decimal("0"), output_sgst - input_sgst))

    return {
        "period": {"from": from_date.isoformat(), "to": to_date.isoformat()},
        "outward_taxable_supplies": {
            "taxable_value": float(taxable_outward),
            "cgst": float(output_cgst),
            "sgst": float(output_sgst),
            "total_tax": float(money(output_cgst + output_sgst)),
        },
        "eligible_itc": {
            "cgst": float(input_cgst),
            "sgst": float(input_sgst),
            "total_itc": float(money(input_cgst + input_sgst)),
        },
        "net_tax_payable": {
            "cgst": float(net_cgst_payable),
            "sgst": float(net_sgst_payable),
            "total": float(money(net_cgst_payable + net_sgst_payable)),
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
        .where(models.Invoice.status != "Cancelled", models.Invoice.invoice_date >= from_date, models.Invoice.invoice_date <= to_date)
    ).unique().all()

    b2b = []
    b2c_buckets: dict[str, dict] = {}
    for invoice in invoices:
        taxable = money(Decimal(invoice.grand_total) - Decimal(invoice.cgst) - Decimal(invoice.sgst))
        rate = money((Decimal(invoice.cgst) + Decimal(invoice.sgst)) / taxable * 100) if taxable > 0 else Decimal("0")
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
            })
        else:
            key = str(rate)
            bucket = b2c_buckets.setdefault(key, {"rate": float(rate), "taxable_value": Decimal("0"), "cgst": Decimal("0"), "sgst": Decimal("0")})
            bucket["taxable_value"] += taxable
            bucket["cgst"] += Decimal(invoice.cgst)
            bucket["sgst"] += Decimal(invoice.sgst)

    b2c = [
        {"rate": b["rate"], "taxable_value": float(money(b["taxable_value"])), "cgst": float(money(b["cgst"])), "sgst": float(money(b["sgst"]))}
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


def sales_register(db: Session, from_date: date, to_date: date) -> list[dict]:
    invoices = db.scalars(
        select(models.Invoice)
        .options(joinedload(models.Invoice.customer))
        .where(models.Invoice.invoice_date >= from_date, models.Invoice.invoice_date <= to_date)
        .order_by(models.Invoice.invoice_date)
    ).unique().all()
    return [
        {
            "date": invoice.invoice_date.isoformat(),
            "number": invoice.number,
            "party": invoice.customer.name,
            "gstin": invoice.customer.gst_number or "-",
            "taxable_value": float(money(Decimal(invoice.grand_total) - Decimal(invoice.cgst) - Decimal(invoice.sgst))),
            "cgst": float(invoice.cgst),
            "sgst": float(invoice.sgst),
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
