from __future__ import annotations

from datetime import date
from decimal import Decimal
import xml.etree.ElementTree as ET

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload, selectinload

from . import models
from .services import ACCOUNT_PAYABLE, ACCOUNT_RECEIVABLE, list_chart_of_accounts

TALLY_PARENT_BY_CODE = {
    "1000": "Cash-in-Hand",
    "1010": "Bank Accounts",
    "1100": "Sundry Debtors",
    "1200": "Duties & Taxes",
    "1210": "Duties & Taxes",
    "2000": "Sundry Creditors",
    "2100": "Duties & Taxes",
    "2110": "Duties & Taxes",
    "3000": "Capital Account",
    "4000": "Sales Accounts",
    "4100": "Sales Accounts",
    "5000": "Purchase Accounts",
}

VOUCHER_TYPE_BY_SOURCE = {
    "Invoice": "Sales",
    "InvoiceReopen": "Sales",
    "InvoiceCancellation": "Journal",
    "Payment": "Receipt",
    "CreditNote": "Credit Note",
    "CreditNoteCancellation": "Journal",
    "DebitNote": "Debit Note",
    "DebitNoteCancellation": "Journal",
    "PurchaseBill": "Purchase",
    "PurchaseBillReopen": "Purchase",
    "PurchaseBillCancellation": "Journal",
    "VendorPayment": "Payment",
    "Expense": "Journal",
}


def _party_ledger_name(party) -> str:
    return f"{party.name} ({party.code})"


def _resolve_party(db: Session, source_type: str, source_id: int | None):
    if not source_id:
        return None
    if source_type in ("Invoice", "InvoiceCancellation", "InvoiceReopen"):
        invoice = db.get(models.Invoice, source_id)
        return invoice.customer if invoice else None
    if source_type == "Payment":
        payment = db.get(models.Payment, source_id)
        return payment.invoice.customer if payment else None
    if source_type in ("CreditNote", "CreditNoteCancellation"):
        note = db.get(models.CreditNote, source_id)
        return note.customer if note else None
    if source_type in ("DebitNote", "DebitNoteCancellation"):
        note = db.get(models.DebitNote, source_id)
        return note.customer if note else None
    if source_type in ("PurchaseBill", "PurchaseBillCancellation", "PurchaseBillReopen"):
        bill = db.get(models.PurchaseBill, source_id)
        return bill.vendor if bill else None
    if source_type == "VendorPayment":
        payment = db.get(models.VendorPayment, source_id)
        return payment.purchase_bill.vendor if payment else None
    return None


def _envelope_skeleton(report_name: str, company_name: str) -> tuple[ET.Element, ET.Element]:
    envelope = ET.Element("ENVELOPE")
    header = ET.SubElement(envelope, "HEADER")
    ET.SubElement(header, "TALLYREQUEST").text = "Import Data"
    body = ET.SubElement(envelope, "BODY")
    import_data = ET.SubElement(body, "IMPORTDATA")
    request_desc = ET.SubElement(import_data, "REQUESTDESC")
    ET.SubElement(request_desc, "REPORTNAME").text = report_name
    static_vars = ET.SubElement(request_desc, "STATICVARIABLES")
    ET.SubElement(static_vars, "SVCURRENTCOMPANY").text = company_name
    request_data = ET.SubElement(import_data, "REQUESTDATA")
    return envelope, request_data


def build_tally_masters_xml(db: Session) -> bytes:
    settings = db.get(models.BusinessSettings, 1)
    company_name = settings.company_name if settings else "UPVC Pro"
    envelope, request_data = _envelope_skeleton("All Masters", company_name)

    def add_ledger(name: str, parent: str) -> None:
        message = ET.SubElement(request_data, "TALLYMESSAGE", {"xmlns:UDF": "TallyUDF"})
        ledger = ET.SubElement(message, "LEDGER", {"NAME": name, "ACTION": "Create"})
        ET.SubElement(ledger, "PARENT").text = parent
        ET.SubElement(ledger, "ISBILLWISEON").text = "Yes" if parent in ("Sundry Debtors", "Sundry Creditors") else "No"
        ET.SubElement(ledger, "OPENINGBALANCE").text = "0.00"

    for account in list_chart_of_accounts(db):
        add_ledger(account.name, TALLY_PARENT_BY_CODE.get(account.code, "Indirect Expenses"))

    for customer in db.scalars(select(models.Customer)).all():
        add_ledger(_party_ledger_name(customer), "Sundry Debtors")

    for vendor in db.scalars(select(models.Vendor)).all():
        add_ledger(_party_ledger_name(vendor), "Sundry Creditors")

    return ET.tostring(envelope, encoding="utf-8", xml_declaration=True)


def build_tally_vouchers_xml(db: Session, from_date: date, to_date: date) -> bytes:
    settings = db.get(models.BusinessSettings, 1)
    company_name = settings.company_name if settings else "UPVC Pro"
    envelope, request_data = _envelope_skeleton("Vouchers", company_name)

    entries = db.scalars(
        select(models.JournalEntry)
        .options(selectinload(models.JournalEntry.lines).joinedload(models.JournalLine.account))
        .where(models.JournalEntry.entry_date >= from_date, models.JournalEntry.entry_date <= to_date)
        .order_by(models.JournalEntry.entry_date, models.JournalEntry.id)
    ).unique().all()

    for entry in entries:
        party = _resolve_party(db, entry.source_type, entry.source_id)
        party_name = _party_ledger_name(party) if party else None
        voucher_type = VOUCHER_TYPE_BY_SOURCE.get(entry.source_type, "Journal")

        message = ET.SubElement(request_data, "TALLYMESSAGE", {"xmlns:UDF": "TallyUDF"})
        voucher = ET.SubElement(message, "VOUCHER", {"VCHTYPE": voucher_type, "ACTION": "Create"})
        ET.SubElement(voucher, "DATE").text = entry.entry_date.strftime("%Y%m%d")
        ET.SubElement(voucher, "VOUCHERTYPENAME").text = voucher_type
        ET.SubElement(voucher, "VOUCHERNUMBER").text = entry.number
        if party_name:
            ET.SubElement(voucher, "PARTYLEDGERNAME").text = party_name
        ET.SubElement(voucher, "NARRATION").text = entry.narration

        for line in entry.lines:
            ledger_name = party_name if (party_name and line.account.code in (ACCOUNT_RECEIVABLE, ACCOUNT_PAYABLE)) else line.account.name
            list_entry = ET.SubElement(voucher, "ALLLEDGERENTRIES.LIST")
            ET.SubElement(list_entry, "LEDGERNAME").text = ledger_name
            debit = Decimal(line.debit)
            credit = Decimal(line.credit)
            if debit > 0:
                ET.SubElement(list_entry, "ISDEEMEDPOSITIVE").text = "Yes"
                ET.SubElement(list_entry, "AMOUNT").text = f"{-debit:.2f}"
            else:
                ET.SubElement(list_entry, "ISDEEMEDPOSITIVE").text = "No"
                ET.SubElement(list_entry, "AMOUNT").text = f"{credit:.2f}"

    return ET.tostring(envelope, encoding="utf-8", xml_declaration=True)
