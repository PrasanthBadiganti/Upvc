from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload, selectinload

from . import models
from .schemas import CreditNoteCreate, DebitNoteCreate, ExpenseCreate, PurchaseBillCreate, QuotationCreate

TWOPLACES = Decimal("0.01")


def money(value: Decimal | int | float | str) -> Decimal:
    return Decimal(str(value)).quantize(TWOPLACES, rounding=ROUND_HALF_UP)


def next_code(db: Session, model: type, prefix: str) -> str:
    count = db.scalar(select(func.count()).select_from(model)) or 0
    return f"{prefix}-{count + 1:04d}"


def next_document_number(db: Session, model: type, prefix: str) -> str:
    year = date.today().year
    count = db.scalar(select(func.count()).select_from(model)) or 0
    return f"{prefix}-{year}-{count + 1:03d}"


def calculate_sft(width_mm: Decimal, height_mm: Decimal, minimum: Decimal = Decimal("0")) -> Decimal:
    raw = (Decimal(width_mm) / Decimal("304.8")) * (Decimal(height_mm) / Decimal("304.8"))
    raw = raw.quantize(TWOPLACES, rounding=ROUND_HALF_UP)
    return max(raw, Decimal(minimum)).quantize(TWOPLACES)


def apply_quotation_payload(db: Session, quote: models.Quotation, payload: QuotationCreate) -> None:
    rule = db.get(models.PricingRule, 1)
    gst_rate = Decimal(rule.gst_rate if rule else 18)

    quote.customer_id = payload.customer_id
    quote.quotation_date = payload.quotation_date
    quote.validity_days = payload.validity_days
    quote.sales_person = payload.sales_person
    quote.site_location = payload.site_location
    quote.address = payload.address
    quote.status = payload.status
    quote.transport = money(payload.transport)
    quote.discount = money(payload.discount)
    quote.notes = payload.notes
    quote.items.clear()

    subtotal = Decimal("0")
    for item in payload.items:
        catalog_item = db.get(models.CatalogItem, item.catalog_item_id) if item.catalog_item_id else None
        rate_per_sft = money(item.rate_per_sft if item.rate_per_sft > 0 else (catalog_item.rate_per_sft if catalog_item else 0))
        min_billable_sft = Decimal(catalog_item.min_billable_sft) if catalog_item else Decimal("0")
        sft = money(item.sft)
        if sft <= 0 and item.width_mm > 0 and item.height_mm > 0:
            sft = calculate_sft(item.width_mm, item.height_mm)
        billable_sft = max(sft, min_billable_sft)
        total_sft = money(item.total_sft if item.total_sft > 0 else billable_sft * item.quantity)
        amount = money(item.amount if item.amount > 0 else total_sft * rate_per_sft)
        subtotal += amount
        quote.items.append(
            models.QuotationItem(
                catalog_item_id=item.catalog_item_id,
                category=item.category,
                style=item.style,
                width_mm=money(item.width_mm),
                height_mm=money(item.height_mm),
                sft=sft,
                quantity=item.quantity,
                total_sft=total_sft,
                rate_per_sft=rate_per_sft,
                amount=amount,
                hsn_code=item.hsn_code or (catalog_item.hsn_code if catalog_item else ""),
                location=item.location,
                profile=item.profile or (catalog_item.profile if catalog_item else ""),
                color=item.color or (catalog_item.color if catalog_item else ""),
                track=item.track or (catalog_item.track if catalog_item else ""),
                glass=item.glass or (catalog_item.glass if catalog_item else ""),
                glass_color=item.glass_color or (catalog_item.glass_color if catalog_item else ""),
                hardware=item.hardware or (catalog_item.hardware if catalog_item else ""),
                reinforcement=item.reinforcement or (catalog_item.reinforcement if catalog_item else ""),
                mesh=item.mesh or (catalog_item.mesh if catalog_item else ""),
            )
        )

    taxable = subtotal + quote.transport - quote.discount
    gst = money(taxable * gst_rate / Decimal("100"))
    grand = money(taxable + gst)
    advance = money(grand * Decimal("0.50"))
    quote.subtotal = money(subtotal)
    quote.gst = gst
    quote.grand_total = grand
    quote.advance = advance
    quote.balance = money(grand - advance)


def refresh_customer_quote_value(db: Session, customer_id: int) -> None:
    customer = db.get(models.Customer, customer_id)
    if not customer:
        return
    total = db.scalar(select(func.sum(models.Quotation.grand_total)).where(models.Quotation.customer_id == customer_id)) or Decimal("0")
    customer.quote_value = money(total)


def create_quotation(db: Session, payload: QuotationCreate) -> models.Quotation:
    quote = models.Quotation(number=next_document_number(db, models.Quotation, "QT"), customer_id=payload.customer_id)
    apply_quotation_payload(db, quote, payload)

    customer = db.get(models.Customer, payload.customer_id)
    if customer:
        customer.last_interaction = __import__("datetime").datetime.utcnow()
        if quote.status.lower() in {"sent", "quotation sent"}:
            customer.status = "Quotation Sent"

    db.add(quote)
    db.commit()
    refresh_customer_quote_value(db, payload.customer_id)
    db.commit()
    return get_quotation(db, quote.id)


def update_quotation(db: Session, quotation_id: int, payload: QuotationCreate) -> models.Quotation:
    quote = get_quotation(db, quotation_id)
    if quote.status in {"Accepted", "Converted"}:
        raise ValueError("Accepted or converted quotations are locked. Create a revision instead.")
    old_customer_id = quote.customer_id
    apply_quotation_payload(db, quote, payload)
    customer = db.get(models.Customer, payload.customer_id)
    if customer:
        customer.last_interaction = __import__("datetime").datetime.utcnow()
        if quote.status.lower() in {"sent", "quotation sent"}:
            customer.status = "Quotation Sent"
    db.commit()
    refresh_customer_quote_value(db, old_customer_id)
    if old_customer_id != payload.customer_id:
        refresh_customer_quote_value(db, payload.customer_id)
    db.commit()
    return get_quotation(db, quotation_id)


def duplicate_quotation(db: Session, quotation_id: int, revision: bool = False) -> models.Quotation:
    quote = get_quotation(db, quotation_id)
    payload = QuotationCreate(
        customer_id=quote.customer_id,
        quotation_date=date.today(),
        validity_days=quote.validity_days,
        sales_person=quote.sales_person,
        site_location=quote.site_location,
        address=quote.address,
        status="Draft",
        transport=quote.transport,
        discount=quote.discount,
        notes=(f"Revision of {quote.number}. {quote.notes}".strip() if revision else f"Duplicated from {quote.number}. {quote.notes}".strip()),
        items=[
            {
                "catalog_item_id": item.catalog_item_id,
                "category": item.category,
                "style": item.style,
                "width_mm": item.width_mm,
                "height_mm": item.height_mm,
                "sft": item.sft,
                "quantity": item.quantity,
                "total_sft": item.total_sft,
                "rate_per_sft": item.rate_per_sft,
                "amount": item.amount,
                "hsn_code": item.hsn_code,
                "location": item.location,
                "profile": item.profile,
                "color": item.color,
                "track": item.track,
                "glass": item.glass,
                "glass_color": item.glass_color,
                "hardware": item.hardware,
                "reinforcement": item.reinforcement,
                "mesh": item.mesh,
            }
            for item in quote.items
        ],
    )
    return create_quotation(db, payload)


def get_quotation(db: Session, quotation_id: int) -> models.Quotation:
    stmt = (
        select(models.Quotation)
        .where(models.Quotation.id == quotation_id)
        .options(selectinload(models.Quotation.items), joinedload(models.Quotation.customer))
    )
    return db.scalars(stmt).unique().one()


def get_invoice(db: Session, invoice_id: int) -> models.Invoice:
    stmt = (
        select(models.Invoice)
        .where(models.Invoice.id == invoice_id)
        .options(
            selectinload(models.Invoice.items),
            selectinload(models.Invoice.payments),
            joinedload(models.Invoice.customer),
            joinedload(models.Invoice.quotation).selectinload(models.Quotation.items),
            joinedload(models.Invoice.quotation).joinedload(models.Quotation.customer),
        )
    )
    return db.scalars(stmt).unique().one()


def get_payment(db: Session, payment_id: int) -> models.Payment:
    stmt = (
        select(models.Payment)
        .where(models.Payment.id == payment_id)
        .options(
            joinedload(models.Payment.invoice).joinedload(models.Invoice.customer),
            joinedload(models.Payment.invoice).selectinload(models.Invoice.payments),
        )
    )
    return db.scalars(stmt).unique().one()


def convert_quotation_to_invoice(db: Session, quotation_id: int) -> models.Invoice:
    quote = get_quotation(db, quotation_id)
    if quote.invoice:
        return get_invoice(db, quote.invoice.id)

    subtotal = money(quote.subtotal)
    total_gst = money(quote.gst)
    invoice = models.Invoice(
        number=next_document_number(db, models.Invoice, "INV"),
        quotation_id=quote.id,
        customer_id=quote.customer_id,
        invoice_date=date.today(),
        due_date=date.today() + timedelta(days=30),
        status="Unpaid",
        subtotal=subtotal,
        cgst=money(total_gst / 2),
        sgst=money(total_gst / 2),
        grand_total=money(quote.grand_total),
        paid_amount=Decimal("0"),
        pending_balance=money(quote.grand_total),
    )
    for item in quote.items:
        description = f"{item.category} {item.style} {int(item.width_mm)}x{int(item.height_mm)}mm".strip()
        invoice.items.append(
            models.InvoiceItem(
                description=description,
                category=item.category,
                unit="Sq. Ft.",
                quantity=money(item.total_sft),
                rate=money(item.rate_per_sft),
                gst_percent=18,
                amount=money(item.amount),
                hsn_code=item.hsn_code,
            )
        )
    quote.status = "Converted"
    customer = quote.customer
    customer.status = "Live"
    customer.pending_payment = money(Decimal(customer.pending_payment or 0) + invoice.pending_balance)
    db.add(invoice)
    db.flush()
    revenue_amount = money(Decimal(invoice.grand_total) - Decimal(invoice.cgst) - Decimal(invoice.sgst))
    post_journal_entry(db, invoice.invoice_date, f"Invoice {invoice.number} to {customer.name}", "Invoice", invoice.id, [
        (ACCOUNT_RECEIVABLE, invoice.grand_total, Decimal("0")),
        (ACCOUNT_SALES, Decimal("0"), revenue_amount),
        (ACCOUNT_OUTPUT_CGST, Decimal("0"), invoice.cgst),
        (ACCOUNT_OUTPUT_SGST, Decimal("0"), invoice.sgst),
    ])
    db.commit()
    return get_invoice(db, invoice.id)


def record_payment(db: Session, invoice_id: int, amount: Decimal, **kwargs) -> models.Invoice:
    invoice = get_invoice(db, invoice_id)
    if invoice.status == "Cancelled":
        raise ValueError("Cannot record payment against a cancelled invoice")
    amount = money(amount)
    if amount <= 0:
        raise ValueError("Payment amount must be greater than zero")
    if amount > Decimal(invoice.pending_balance):
        raise ValueError("Payment amount cannot exceed pending balance")
    payment = models.Payment(invoice_id=invoice_id, amount=amount, **kwargs)
    invoice.paid_amount = money(Decimal(invoice.paid_amount) + amount)
    invoice.pending_balance = money(Decimal(invoice.grand_total) - Decimal(invoice.paid_amount))
    invoice.status = "Paid" if invoice.pending_balance <= 0 else "Partially Paid"
    customer = invoice.customer
    customer.pending_payment = money(max(Decimal("0"), Decimal(customer.pending_payment or 0) - amount))
    db.add(payment)
    db.flush()
    post_journal_entry(db, payment.payment_date, f"Payment received for {invoice.number}", "Payment", payment.id, [
        (_cash_or_bank_code(payment.mode), amount, Decimal("0")),
        (ACCOUNT_RECEIVABLE, Decimal("0"), amount),
    ])
    db.commit()
    db.expire_all()
    return get_invoice(db, invoice_id)


def cancel_invoice(db: Session, invoice_id: int, force: bool = False) -> models.Invoice:
    invoice = get_invoice(db, invoice_id)
    if invoice.status == "Cancelled":
        return invoice
    if invoice.status == "Paid" and not force:
        raise ValueError("Fully paid invoices require force=true to cancel")
    customer = invoice.customer
    customer.pending_payment = money(max(Decimal("0"), Decimal(customer.pending_payment or 0) - Decimal(invoice.pending_balance or 0)))
    invoice.status = "Cancelled"
    revenue_amount = money(Decimal(invoice.grand_total) - Decimal(invoice.cgst) - Decimal(invoice.sgst))
    post_journal_entry(db, date.today(), f"Cancellation of invoice {invoice.number}", "InvoiceCancellation", invoice.id, [
        (ACCOUNT_SALES, revenue_amount, Decimal("0")),
        (ACCOUNT_OUTPUT_CGST, invoice.cgst, Decimal("0")),
        (ACCOUNT_OUTPUT_SGST, invoice.sgst, Decimal("0")),
        (ACCOUNT_RECEIVABLE, Decimal("0"), invoice.grand_total),
    ])
    db.commit()
    db.expire_all()
    return get_invoice(db, invoice_id)


def reopen_invoice(db: Session, invoice_id: int) -> models.Invoice:
    invoice = get_invoice(db, invoice_id)
    if invoice.status != "Cancelled":
        return invoice
    pending = Decimal(invoice.pending_balance or 0)
    paid = Decimal(invoice.paid_amount or 0)
    invoice.status = "Paid" if pending <= 0 else "Partially Paid" if paid > 0 else "Unpaid"
    invoice.customer.pending_payment = money(Decimal(invoice.customer.pending_payment or 0) + pending)
    revenue_amount = money(Decimal(invoice.grand_total) - Decimal(invoice.cgst) - Decimal(invoice.sgst))
    post_journal_entry(db, date.today(), f"Reopening of invoice {invoice.number}", "InvoiceReopen", invoice.id, [
        (ACCOUNT_RECEIVABLE, invoice.grand_total, Decimal("0")),
        (ACCOUNT_SALES, Decimal("0"), revenue_amount),
        (ACCOUNT_OUTPUT_CGST, Decimal("0"), invoice.cgst),
        (ACCOUNT_OUTPUT_SGST, Decimal("0"), invoice.sgst),
    ])
    db.commit()
    db.expire_all()
    return get_invoice(db, invoice_id)


def _derive_balance_status(invoice: models.Invoice) -> str:
    pending = Decimal(invoice.pending_balance or 0)
    paid = Decimal(invoice.paid_amount or 0)
    return "Paid" if pending <= 0 else "Partially Paid" if paid > 0 else "Unpaid"


ACCOUNT_CASH = "1000"
ACCOUNT_BANK = "1010"
ACCOUNT_RECEIVABLE = "1100"
ACCOUNT_INPUT_CGST = "1200"
ACCOUNT_INPUT_SGST = "1210"
ACCOUNT_PAYABLE = "2000"
ACCOUNT_OUTPUT_CGST = "2100"
ACCOUNT_OUTPUT_SGST = "2110"
ACCOUNT_SALES = "4000"
ACCOUNT_SALES_RETURNS = "4100"
ACCOUNT_PURCHASES = "5000"
EXPENSE_ACCOUNT_CODES = {
    "Rent": "5100",
    "Salaries": "5110",
    "Utilities": "5120",
    "Transport": "5130",
    "Office Supplies": "5140",
    "Marketing": "5150",
    "Professional Fees": "5160",
    "Other": "5190",
}


def _cash_or_bank_code(mode: str) -> str:
    return ACCOUNT_CASH if mode == "Cash" else ACCOUNT_BANK


def _expense_account_code(category: str) -> str:
    return EXPENSE_ACCOUNT_CODES.get(category, "5190")


def _account(db: Session, code: str) -> models.ChartOfAccount:
    account = db.scalar(select(models.ChartOfAccount).where(models.ChartOfAccount.code == code))
    if not account:
        raise ValueError(f"Chart of accounts entry {code} is missing")
    return account


def post_journal_entry(db: Session, entry_date, narration: str, source_type: str, source_id: int, lines: list[tuple[str, Decimal, Decimal]]) -> models.JournalEntry:
    total_debit = money(sum((money(debit) for _, debit, _ in lines), Decimal("0")))
    total_credit = money(sum((money(credit) for _, _, credit in lines), Decimal("0")))
    if total_debit != total_credit:
        raise ValueError(f"Journal entry for {source_type} #{source_id} is not balanced ({total_debit} debit vs {total_credit} credit)")
    entry = models.JournalEntry(
        number=next_document_number(db, models.JournalEntry, "JE"),
        entry_date=entry_date,
        narration=narration[:240],
        source_type=source_type,
        source_id=source_id,
    )
    for code, debit, credit in lines:
        if money(debit) <= 0 and money(credit) <= 0:
            continue
        account = _account(db, code)
        entry.lines.append(models.JournalLine(account_id=account.id, debit=money(debit), credit=money(credit)))
    db.add(entry)
    db.flush()
    return entry


def _delete_source_journal_entries(db: Session, source_type: str, source_id: int) -> None:
    entries = db.scalars(select(models.JournalEntry).where(models.JournalEntry.source_type == source_type, models.JournalEntry.source_id == source_id)).all()
    for entry in entries:
        db.delete(entry)


def _build_note_items(item_model: type, payload_items) -> tuple[list, Decimal, Decimal]:
    items = []
    subtotal = Decimal("0")
    gst_total = Decimal("0")
    for item in payload_items:
        amount = money(item.amount if item.amount > 0 else Decimal(item.quantity) * Decimal(item.rate))
        item_gst = money(amount * Decimal(item.gst_percent) / Decimal("100"))
        subtotal += amount
        gst_total += item_gst
        items.append(
            item_model(
                description=item.description,
                category=item.category,
                hsn_code=item.hsn_code,
                unit=item.unit,
                quantity=item.quantity,
                rate=item.rate,
                gst_percent=item.gst_percent,
                amount=amount,
            )
        )
    return items, subtotal, gst_total


def get_credit_note(db: Session, credit_note_id: int) -> models.CreditNote:
    stmt = (
        select(models.CreditNote)
        .where(models.CreditNote.id == credit_note_id)
        .options(selectinload(models.CreditNote.items), joinedload(models.CreditNote.customer), joinedload(models.CreditNote.invoice))
    )
    return db.scalars(stmt).unique().one()


def get_debit_note(db: Session, debit_note_id: int) -> models.DebitNote:
    stmt = (
        select(models.DebitNote)
        .where(models.DebitNote.id == debit_note_id)
        .options(selectinload(models.DebitNote.items), joinedload(models.DebitNote.customer), joinedload(models.DebitNote.invoice))
    )
    return db.scalars(stmt).unique().one()


def issue_credit_note(db: Session, invoice_id: int, payload: CreditNoteCreate) -> models.CreditNote:
    invoice = get_invoice(db, invoice_id)
    if invoice.status == "Cancelled":
        raise ValueError("Cannot issue a credit note against a cancelled invoice")
    items, subtotal, gst_total = _build_note_items(models.CreditNoteItem, payload.items)
    grand_total = money(subtotal + gst_total)
    if grand_total <= 0:
        raise ValueError("Credit note total must be greater than zero")
    if grand_total > Decimal(invoice.pending_balance or 0):
        raise ValueError("Credit note total cannot exceed the invoice's pending balance")

    credit_note = models.CreditNote(
        number=next_document_number(db, models.CreditNote, "CN"),
        invoice_id=invoice.id,
        customer_id=invoice.customer_id,
        note_date=payload.note_date,
        reason=payload.reason,
        status="Issued",
        subtotal=money(subtotal),
        gst=money(gst_total),
        grand_total=grand_total,
    )
    credit_note.items = items

    invoice.pending_balance = money(Decimal(invoice.pending_balance or 0) - grand_total)
    invoice.status = _derive_balance_status(invoice)
    customer = invoice.customer
    customer.pending_payment = money(max(Decimal("0"), Decimal(customer.pending_payment or 0) - grand_total))
    db.add(credit_note)
    db.flush()
    gst_half = money(Decimal(credit_note.gst) / 2)
    post_journal_entry(db, credit_note.note_date, f"Credit note {credit_note.number} against {invoice.number}", "CreditNote", credit_note.id, [
        (ACCOUNT_SALES_RETURNS, credit_note.subtotal, Decimal("0")),
        (ACCOUNT_OUTPUT_CGST, gst_half, Decimal("0")),
        (ACCOUNT_OUTPUT_SGST, Decimal(credit_note.gst) - gst_half, Decimal("0")),
        (ACCOUNT_RECEIVABLE, Decimal("0"), credit_note.grand_total),
    ])
    db.commit()
    return get_credit_note(db, credit_note.id)


def cancel_credit_note(db: Session, credit_note_id: int) -> models.CreditNote:
    credit_note = get_credit_note(db, credit_note_id)
    if credit_note.status == "Cancelled":
        return credit_note
    invoice = credit_note.invoice
    invoice.pending_balance = money(Decimal(invoice.pending_balance or 0) + Decimal(credit_note.grand_total))
    invoice.status = _derive_balance_status(invoice)
    invoice.customer.pending_payment = money(Decimal(invoice.customer.pending_payment or 0) + Decimal(credit_note.grand_total))
    credit_note.status = "Cancelled"
    gst_half = money(Decimal(credit_note.gst) / 2)
    post_journal_entry(db, date.today(), f"Cancellation of credit note {credit_note.number}", "CreditNoteCancellation", credit_note.id, [
        (ACCOUNT_RECEIVABLE, credit_note.grand_total, Decimal("0")),
        (ACCOUNT_SALES_RETURNS, Decimal("0"), credit_note.subtotal),
        (ACCOUNT_OUTPUT_CGST, Decimal("0"), gst_half),
        (ACCOUNT_OUTPUT_SGST, Decimal("0"), Decimal(credit_note.gst) - gst_half),
    ])
    db.commit()
    db.expire_all()
    return get_credit_note(db, credit_note_id)


def issue_debit_note(db: Session, invoice_id: int, payload: DebitNoteCreate) -> models.DebitNote:
    invoice = get_invoice(db, invoice_id)
    if invoice.status == "Cancelled":
        raise ValueError("Cannot issue a debit note against a cancelled invoice")
    items, subtotal, gst_total = _build_note_items(models.DebitNoteItem, payload.items)
    grand_total = money(subtotal + gst_total)
    if grand_total <= 0:
        raise ValueError("Debit note total must be greater than zero")

    debit_note = models.DebitNote(
        number=next_document_number(db, models.DebitNote, "DN"),
        invoice_id=invoice.id,
        customer_id=invoice.customer_id,
        note_date=payload.note_date,
        reason=payload.reason,
        status="Issued",
        subtotal=money(subtotal),
        gst=money(gst_total),
        grand_total=grand_total,
    )
    debit_note.items = items

    invoice.pending_balance = money(Decimal(invoice.pending_balance or 0) + grand_total)
    invoice.status = _derive_balance_status(invoice)
    customer = invoice.customer
    customer.pending_payment = money(Decimal(customer.pending_payment or 0) + grand_total)
    db.add(debit_note)
    db.flush()
    gst_half = money(Decimal(debit_note.gst) / 2)
    post_journal_entry(db, debit_note.note_date, f"Debit note {debit_note.number} against {invoice.number}", "DebitNote", debit_note.id, [
        (ACCOUNT_RECEIVABLE, debit_note.grand_total, Decimal("0")),
        (ACCOUNT_SALES, Decimal("0"), debit_note.subtotal),
        (ACCOUNT_OUTPUT_CGST, Decimal("0"), gst_half),
        (ACCOUNT_OUTPUT_SGST, Decimal("0"), Decimal(debit_note.gst) - gst_half),
    ])
    db.commit()
    return get_debit_note(db, debit_note.id)


def cancel_debit_note(db: Session, debit_note_id: int) -> models.DebitNote:
    debit_note = get_debit_note(db, debit_note_id)
    if debit_note.status == "Cancelled":
        return debit_note
    invoice = debit_note.invoice
    invoice.pending_balance = money(max(Decimal("0"), Decimal(invoice.pending_balance or 0) - Decimal(debit_note.grand_total)))
    invoice.status = _derive_balance_status(invoice)
    invoice.customer.pending_payment = money(max(Decimal("0"), Decimal(invoice.customer.pending_payment or 0) - Decimal(debit_note.grand_total)))
    debit_note.status = "Cancelled"
    gst_half = money(Decimal(debit_note.gst) / 2)
    post_journal_entry(db, date.today(), f"Cancellation of debit note {debit_note.number}", "DebitNoteCancellation", debit_note.id, [
        (ACCOUNT_SALES, debit_note.subtotal, Decimal("0")),
        (ACCOUNT_OUTPUT_CGST, gst_half, Decimal("0")),
        (ACCOUNT_OUTPUT_SGST, Decimal(debit_note.gst) - gst_half, Decimal("0")),
        (ACCOUNT_RECEIVABLE, Decimal("0"), debit_note.grand_total),
    ])
    db.commit()
    db.expire_all()
    return get_debit_note(db, debit_note_id)


def get_purchase_bill(db: Session, purchase_bill_id: int) -> models.PurchaseBill:
    stmt = (
        select(models.PurchaseBill)
        .where(models.PurchaseBill.id == purchase_bill_id)
        .options(
            selectinload(models.PurchaseBill.items),
            selectinload(models.PurchaseBill.payments),
            joinedload(models.PurchaseBill.vendor),
        )
    )
    return db.scalars(stmt).unique().one()


def create_purchase_bill(db: Session, vendor_id: int, payload: PurchaseBillCreate) -> models.PurchaseBill:
    vendor = db.get(models.Vendor, vendor_id)
    if not vendor:
        raise ValueError("Vendor not found")
    items, subtotal, gst_total = _build_note_items(models.PurchaseBillItem, payload.items)
    grand_total = money(subtotal + gst_total)
    if grand_total <= 0:
        raise ValueError("Purchase bill total must be greater than zero")

    bill = models.PurchaseBill(
        number=next_document_number(db, models.PurchaseBill, "PB"),
        vendor_id=vendor.id,
        vendor_bill_number=payload.vendor_bill_number,
        bill_date=payload.bill_date,
        due_date=payload.due_date,
        status="Unpaid",
        subtotal=money(subtotal),
        cgst=money(gst_total / 2),
        sgst=money(gst_total / 2),
        grand_total=grand_total,
        paid_amount=Decimal("0"),
        pending_balance=grand_total,
        notes=payload.notes,
    )
    bill.items = items

    vendor.pending_payment = money(Decimal(vendor.pending_payment or 0) + grand_total)
    db.add(bill)
    db.flush()
    post_journal_entry(db, bill.bill_date, f"Purchase bill {bill.number} from {vendor.name}", "PurchaseBill", bill.id, [
        (ACCOUNT_PURCHASES, bill.subtotal, Decimal("0")),
        (ACCOUNT_INPUT_CGST, bill.cgst, Decimal("0")),
        (ACCOUNT_INPUT_SGST, bill.sgst, Decimal("0")),
        (ACCOUNT_PAYABLE, Decimal("0"), bill.grand_total),
    ])
    db.commit()
    return get_purchase_bill(db, bill.id)


def record_vendor_payment(db: Session, purchase_bill_id: int, amount: Decimal, **kwargs) -> models.PurchaseBill:
    bill = get_purchase_bill(db, purchase_bill_id)
    if bill.status == "Cancelled":
        raise ValueError("Cannot record payment against a cancelled purchase bill")
    amount = money(amount)
    if amount <= 0:
        raise ValueError("Payment amount must be greater than zero")
    if amount > Decimal(bill.pending_balance):
        raise ValueError("Payment amount cannot exceed pending balance")
    payment = models.VendorPayment(purchase_bill_id=purchase_bill_id, amount=amount, **kwargs)
    bill.paid_amount = money(Decimal(bill.paid_amount) + amount)
    bill.pending_balance = money(Decimal(bill.grand_total) - Decimal(bill.paid_amount))
    bill.status = "Paid" if bill.pending_balance <= 0 else "Partially Paid"
    vendor = bill.vendor
    vendor.pending_payment = money(max(Decimal("0"), Decimal(vendor.pending_payment or 0) - amount))
    db.add(payment)
    db.flush()
    post_journal_entry(db, payment.payment_date, f"Payment made for {bill.number}", "VendorPayment", payment.id, [
        (ACCOUNT_PAYABLE, amount, Decimal("0")),
        (_cash_or_bank_code(payment.mode), Decimal("0"), amount),
    ])
    db.commit()
    db.expire_all()
    return get_purchase_bill(db, purchase_bill_id)


def cancel_purchase_bill(db: Session, purchase_bill_id: int, force: bool = False) -> models.PurchaseBill:
    bill = get_purchase_bill(db, purchase_bill_id)
    if bill.status == "Cancelled":
        return bill
    if bill.status == "Paid" and not force:
        raise ValueError("Fully paid purchase bills require force=true to cancel")
    vendor = bill.vendor
    vendor.pending_payment = money(max(Decimal("0"), Decimal(vendor.pending_payment or 0) - Decimal(bill.pending_balance or 0)))
    bill.status = "Cancelled"
    post_journal_entry(db, date.today(), f"Cancellation of purchase bill {bill.number}", "PurchaseBillCancellation", bill.id, [
        (ACCOUNT_PAYABLE, bill.grand_total, Decimal("0")),
        (ACCOUNT_PURCHASES, Decimal("0"), bill.subtotal),
        (ACCOUNT_INPUT_CGST, Decimal("0"), bill.cgst),
        (ACCOUNT_INPUT_SGST, Decimal("0"), bill.sgst),
    ])
    db.commit()
    db.expire_all()
    return get_purchase_bill(db, purchase_bill_id)


def reopen_purchase_bill(db: Session, purchase_bill_id: int) -> models.PurchaseBill:
    bill = get_purchase_bill(db, purchase_bill_id)
    if bill.status != "Cancelled":
        return bill
    pending = Decimal(bill.pending_balance or 0)
    paid = Decimal(bill.paid_amount or 0)
    bill.status = "Paid" if pending <= 0 else "Partially Paid" if paid > 0 else "Unpaid"
    bill.vendor.pending_payment = money(Decimal(bill.vendor.pending_payment or 0) + pending)
    post_journal_entry(db, date.today(), f"Reopening of purchase bill {bill.number}", "PurchaseBillReopen", bill.id, [
        (ACCOUNT_PURCHASES, bill.subtotal, Decimal("0")),
        (ACCOUNT_INPUT_CGST, bill.cgst, Decimal("0")),
        (ACCOUNT_INPUT_SGST, bill.sgst, Decimal("0")),
        (ACCOUNT_PAYABLE, Decimal("0"), bill.grand_total),
    ])
    db.commit()
    db.expire_all()
    return get_purchase_bill(db, purchase_bill_id)


def get_expense(db: Session, expense_id: int) -> models.Expense:
    stmt = select(models.Expense).where(models.Expense.id == expense_id).options(joinedload(models.Expense.vendor))
    return db.scalars(stmt).unique().one()


def _apply_expense_payload(expense: models.Expense, payload: ExpenseCreate) -> None:
    expense.expense_date = payload.expense_date
    expense.category = payload.category
    expense.description = payload.description
    expense.amount = money(payload.amount)
    expense.gst_percent = payload.gst_percent
    expense.gst_amount = money(expense.amount * Decimal(payload.gst_percent) / Decimal("100"))
    expense.total = money(expense.amount + expense.gst_amount)
    expense.vendor_id = payload.vendor_id
    expense.mode = payload.mode
    expense.reference_number = payload.reference_number
    expense.notes = payload.notes


def _post_expense_journal_entry(db: Session, expense: models.Expense) -> None:
    lines: list[tuple[str, Decimal, Decimal]] = [(_expense_account_code(expense.category), Decimal(expense.amount), Decimal("0"))]
    if Decimal(expense.gst_amount) > 0:
        gst_half = money(Decimal(expense.gst_amount) / 2)
        lines.append((ACCOUNT_INPUT_CGST, gst_half, Decimal("0")))
        lines.append((ACCOUNT_INPUT_SGST, Decimal(expense.gst_amount) - gst_half, Decimal("0")))
    lines.append((_cash_or_bank_code(expense.mode), Decimal("0"), Decimal(expense.total)))
    narration = f"Expense: {expense.category}" + (f" - {expense.description}" if expense.description else "")
    post_journal_entry(db, expense.expense_date, narration, "Expense", expense.id, lines)


def create_expense(db: Session, payload: ExpenseCreate) -> models.Expense:
    expense = models.Expense()
    _apply_expense_payload(expense, payload)
    db.add(expense)
    db.flush()
    _post_expense_journal_entry(db, expense)
    db.commit()
    return get_expense(db, expense.id)


def update_expense(db: Session, expense_id: int, payload: ExpenseCreate) -> models.Expense:
    expense = get_expense(db, expense_id)
    _apply_expense_payload(expense, payload)
    db.flush()
    _delete_source_journal_entries(db, "Expense", expense.id)
    _post_expense_journal_entry(db, expense)
    db.commit()
    return get_expense(db, expense_id)


def delete_expense(db: Session, expense_id: int) -> None:
    expense = get_expense(db, expense_id)
    _delete_source_journal_entries(db, "Expense", expense_id)
    db.delete(expense)
    db.commit()


def list_chart_of_accounts(db: Session) -> list[models.ChartOfAccount]:
    return db.scalars(select(models.ChartOfAccount).order_by(models.ChartOfAccount.code)).all()


def get_journal_entry(db: Session, journal_entry_id: int) -> models.JournalEntry:
    stmt = (
        select(models.JournalEntry)
        .where(models.JournalEntry.id == journal_entry_id)
        .options(selectinload(models.JournalEntry.lines).joinedload(models.JournalLine.account))
    )
    return db.scalars(stmt).unique().one()


def list_journal_entries(db: Session) -> list[models.JournalEntry]:
    stmt = (
        select(models.JournalEntry)
        .options(selectinload(models.JournalEntry.lines).joinedload(models.JournalLine.account))
        .order_by(models.JournalEntry.id.desc())
    )
    return db.scalars(stmt).unique().all()


def get_account_ledger(db: Session, account_id: int) -> list[models.JournalLine]:
    stmt = (
        select(models.JournalLine)
        .join(models.JournalEntry)
        .where(models.JournalLine.account_id == account_id)
        .options(joinedload(models.JournalLine.entry))
        .order_by(models.JournalEntry.entry_date, models.JournalEntry.id)
    )
    return db.scalars(stmt).unique().all()


def get_trial_balance(db: Session) -> list[dict]:
    rows = []
    for account in list_chart_of_accounts(db):
        debit_total = money(db.scalar(select(func.coalesce(func.sum(models.JournalLine.debit), 0)).where(models.JournalLine.account_id == account.id)) or 0)
        credit_total = money(db.scalar(select(func.coalesce(func.sum(models.JournalLine.credit), 0)).where(models.JournalLine.account_id == account.id)) or 0)
        if debit_total == 0 and credit_total == 0:
            continue
        rows.append({
            "account_id": account.id,
            "code": account.code,
            "name": account.name,
            "account_type": account.account_type,
            "debit": debit_total,
            "credit": credit_total,
            "balance": money(debit_total - credit_total),
        })
    return rows
