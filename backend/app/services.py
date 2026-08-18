from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal, ROUND_CEILING, ROUND_HALF_UP

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload, selectinload

from . import models
from .schemas import CreditNoteCreate, DebitNoteCreate, ExpenseCreate, FinancialYearCreate, FixedAssetCreate, PurchaseBillCreate, QuotationCreate, StockItemCreate, StockMovementCreate

TWOPLACES = Decimal("0.01")


def money(value: Decimal | int | float | str) -> Decimal:
    return Decimal(str(value)).quantize(TWOPLACES, rounding=ROUND_HALF_UP)


def next_code(db: Session, model: type, prefix: str) -> str:
    """Next sequential code for a model, e.g. CUST-0004.

    Derived from the highest existing suffix rather than a row count, so codes
    stay unique after rows are deleted. Imported codes that do not end in digits
    are skipped rather than breaking the sequence.
    """
    codes = db.scalars(select(model.code).where(model.code.like(f"{prefix}-%"))).all()
    highest = 0
    for code in codes:
        suffix = (code or "").rsplit("-", 1)[-1]
        if suffix.isdigit():
            highest = max(highest, int(suffix))
    return f"{prefix}-{highest + 1:04d}"


def next_sequence_number(db: Session, model: type) -> int:
    """Get the next auto-incrementing sequence number for a model (never resets)"""
    max_seq = db.scalar(select(func.max(model.sequence_number))) or 0
    return max_seq + 1

def format_document_number(prefix: str, sequence_number: int) -> str:
    """Format document number as PREFIX + YY + SEQUENCE (e.g. QT26-1)"""
    year = date.today().year % 100  # Last 2 digits of year
    return f"{prefix}{year}-{sequence_number}"


def calculate_sft(width_mm: Decimal, height_mm: Decimal, minimum: Decimal = Decimal("0")) -> Decimal:
    raw = (Decimal(width_mm) / Decimal("304.8")) * (Decimal(height_mm) / Decimal("304.8"))
    rounded = raw.quantize(Decimal("1"), rounding=ROUND_CEILING)
    return max(rounded, Decimal(minimum)).quantize(TWOPLACES)


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
    quote.charges.clear()
    for charge in payload.charges:
        label = (charge.label or "").strip()
        if not label or money(charge.amount) == 0:
            continue  # ignore blank rows left behind in the UI
        quote.charges.append(models.QuotationCharge(
            label=label, amount=money(charge.amount), taxable=charge.taxable,
        ))

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

    # Charges forming part of a composite supply are taxed with it; anything
    # flagged non-taxable (pure reimbursements) is added after GST instead.
    taxable_charges = sum((c.amount for c in quote.charges if c.taxable), Decimal("0"))
    exempt_charges = sum((c.amount for c in quote.charges if not c.taxable), Decimal("0"))
    taxable = subtotal + quote.transport + taxable_charges - quote.discount
    gst = money(taxable * gst_rate / Decimal("100"))
    grand = money(taxable + gst + exempt_charges)
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
    seq = next_sequence_number(db, models.Quotation)
    quote = models.Quotation(sequence_number=seq, number=format_document_number("QT", seq), customer_id=payload.customer_id)
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
        charges=[
            {"label": c.label, "amount": c.amount, "taxable": c.taxable}
            for c in quote.charges
        ],
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
        .options(
            selectinload(models.Quotation.items),
            selectinload(models.Quotation.charges),
            joinedload(models.Quotation.customer),
        )
    )
    return db.scalars(stmt).unique().one()


def get_invoice(db: Session, invoice_id: int) -> models.Invoice:
    stmt = (
        select(models.Invoice)
        .where(models.Invoice.id == invoice_id)
        .options(
            selectinload(models.Invoice.items),
            selectinload(models.Invoice.charges),
            selectinload(models.Invoice.payments).joinedload(models.Payment.bank_account),
            joinedload(models.Invoice.customer),
            joinedload(models.Invoice.quotation).selectinload(models.Quotation.items),
            joinedload(models.Invoice.quotation).selectinload(models.Quotation.charges),
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
    interstate = is_interstate(_business_state(db), quote.customer.state)
    seq = next_sequence_number(db, models.Invoice)
    invoice = models.Invoice(
        sequence_number=seq,
        number=format_document_number("IV", seq),
        quotation_id=quote.id,
        customer_id=quote.customer_id,
        invoice_date=date.today(),
        due_date=date.today() + timedelta(days=30),
        status="Unpaid",
        subtotal=subtotal,
        transport=money(quote.transport),
        discount=money(quote.discount),
        cgst=Decimal("0") if interstate else money(total_gst / 2),
        sgst=Decimal("0") if interstate else money(total_gst / 2),
        igst=total_gst if interstate else Decimal("0"),
        grand_total=money(quote.grand_total),
        paid_amount=Decimal("0"),
        pending_balance=money(quote.grand_total),
    )
    for charge in quote.charges:
        invoice.charges.append(models.InvoiceCharge(
            label=charge.label, amount=money(charge.amount), taxable=charge.taxable,
        ))
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
                style=item.style,
                width_mm=item.width_mm,
                height_mm=item.height_mm,
                sft=item.sft,
                piece_qty=item.quantity,
            )
        )
    quote.status = "Converted"
    customer = quote.customer
    customer.status = "Live"
    customer.pending_payment = money(Decimal(customer.pending_payment or 0) + invoice.pending_balance)
    db.add(invoice)
    db.flush()
    revenue_amount = money(Decimal(invoice.grand_total) - Decimal(invoice.cgst) - Decimal(invoice.sgst) - Decimal(invoice.igst))
    gst_lines = [(ACCOUNT_OUTPUT_IGST, Decimal("0"), invoice.igst)] if interstate else [
        (ACCOUNT_OUTPUT_CGST, Decimal("0"), invoice.cgst),
        (ACCOUNT_OUTPUT_SGST, Decimal("0"), invoice.sgst),
    ]
    post_journal_entry(db, invoice.invoice_date, f"Invoice {invoice.number} to {customer.name}", "Invoice", invoice.id, [
        (ACCOUNT_RECEIVABLE, invoice.grand_total, Decimal("0")),
        (ACCOUNT_SALES, Decimal("0"), revenue_amount),
        *gst_lines,
    ])
    db.commit()
    return get_invoice(db, invoice.id)


def create_opening_balance_invoice(db: Session, customer_id: int, amount: Decimal, as_of: date) -> models.Invoice:
    """Represents a migrated customer balance as a real Invoice so the existing
    invoice-derived Customer.pending_payment resync picks it up naturally."""
    customer = db.get(models.Customer, customer_id)
    if not customer:
        raise ValueError("Customer not found")
    amount = money(amount)
    seq = next_sequence_number(db, models.Invoice)
    invoice = models.Invoice(
        sequence_number=seq,
        number=format_document_number("OB", seq),
        quotation_id=None,
        customer_id=customer_id,
        invoice_date=as_of,
        due_date=as_of,
        status="Unpaid",
        subtotal=amount,
        cgst=Decimal("0"),
        sgst=Decimal("0"),
        grand_total=amount,
        paid_amount=Decimal("0"),
        pending_balance=amount,
    )
    invoice.items.append(models.InvoiceItem(
        description="Opening balance carried forward from migration",
        category="Opening Balance",
        unit="",
        quantity=1,
        rate=amount,
        gst_percent=Decimal("0"),
        amount=amount,
        hsn_code="",
    ))
    db.add(invoice)
    db.flush()
    post_journal_entry(db, as_of, f"Opening balance for {customer.name}", "OpeningBalance", invoice.id, [
        (ACCOUNT_RECEIVABLE, amount, Decimal("0")),
        (ACCOUNT_OPENING_BALANCE_EQUITY, Decimal("0"), amount),
    ])
    return invoice


def record_payment(db: Session, invoice_id: int, amount: Decimal, **kwargs) -> models.Invoice:
    if kwargs.get("payment_date"):
        _ensure_period_open(db, kwargs["payment_date"])
    invoice = get_invoice(db, invoice_id)
    if invoice.status == "Cancelled":
        raise ValueError("Cannot record payment against a cancelled invoice")
    amount = money(amount)
    if amount <= 0:
        raise ValueError("Payment amount must be greater than zero")
    if amount > Decimal(invoice.pending_balance):
        raise ValueError("Payment amount cannot exceed pending balance")
    seq = next_sequence_number(db, models.Payment)
    payment = models.Payment(sequence_number=seq, number=format_document_number("PAY", seq), invoice_id=invoice_id, amount=amount, **kwargs)
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
    revenue_amount = money(Decimal(invoice.grand_total) - Decimal(invoice.cgst) - Decimal(invoice.sgst) - Decimal(invoice.igst))
    gst_lines = [(ACCOUNT_OUTPUT_IGST, invoice.igst, Decimal("0"))] if Decimal(invoice.igst or 0) > 0 else [
        (ACCOUNT_OUTPUT_CGST, invoice.cgst, Decimal("0")),
        (ACCOUNT_OUTPUT_SGST, invoice.sgst, Decimal("0")),
    ]
    post_journal_entry(db, date.today(), f"Cancellation of invoice {invoice.number}", "InvoiceCancellation", invoice.id, [
        (ACCOUNT_SALES, revenue_amount, Decimal("0")),
        *gst_lines,
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
    revenue_amount = money(Decimal(invoice.grand_total) - Decimal(invoice.cgst) - Decimal(invoice.sgst) - Decimal(invoice.igst))
    gst_lines = [(ACCOUNT_OUTPUT_IGST, Decimal("0"), invoice.igst)] if Decimal(invoice.igst or 0) > 0 else [
        (ACCOUNT_OUTPUT_CGST, Decimal("0"), invoice.cgst),
        (ACCOUNT_OUTPUT_SGST, Decimal("0"), invoice.sgst),
    ]
    post_journal_entry(db, date.today(), f"Reopening of invoice {invoice.number}", "InvoiceReopen", invoice.id, [
        (ACCOUNT_RECEIVABLE, invoice.grand_total, Decimal("0")),
        (ACCOUNT_SALES, Decimal("0"), revenue_amount),
        *gst_lines,
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
ACCOUNT_OWNERS_CAPITAL = "3000"
ACCOUNT_RECEIVABLE = "1100"
ACCOUNT_INPUT_CGST = "1200"
ACCOUNT_INPUT_SGST = "1210"
ACCOUNT_INPUT_IGST = "1220"
ACCOUNT_PAYABLE = "2000"
ACCOUNT_OUTPUT_CGST = "2100"
ACCOUNT_OUTPUT_SGST = "2110"
ACCOUNT_OUTPUT_IGST = "2120"
ACCOUNT_SALES = "4000"
ACCOUNT_SALES_RETURNS = "4100"
ACCOUNT_OPENING_BALANCE_EQUITY = "3800"
ACCOUNT_PURCHASES = "5000"
ACCOUNT_FIXED_ASSETS = "1500"
ACCOUNT_ACCUMULATED_DEPRECIATION = "1590"
ACCOUNT_GAIN_LOSS_ON_DISPOSAL = "4200"
ACCOUNT_DEPRECIATION_EXPENSE = "5200"
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


def _ensure_period_open(db: Session, txn_date) -> None:
    closed = db.scalar(
        select(models.FinancialYear).where(
            models.FinancialYear.status == "Closed",
            models.FinancialYear.start_date <= txn_date,
            models.FinancialYear.end_date >= txn_date,
        )
    )
    if closed:
        raise ValueError(f"{txn_date} falls within {closed.label}, which is closed. Reopen the financial year to post here.")


def _cash_or_bank_code(mode: str) -> str:
    return ACCOUNT_CASH if mode == "Cash" else ACCOUNT_BANK


def _split_cgst_sgst(total: Decimal, cgst_code: str, sgst_code: str, debit: bool) -> list[tuple[str, Decimal, Decimal]]:
    total = Decimal(total)
    half = money(total / 2)
    remainder = money(total - half)
    if debit:
        return [(cgst_code, half, Decimal("0")), (sgst_code, remainder, Decimal("0"))]
    return [(cgst_code, Decimal("0"), half), (sgst_code, Decimal("0"), remainder)]


def _business_state(db: Session) -> str:
    settings = db.get(models.BusinessSettings, 1)
    return (settings.state if settings else "") or ""


def is_interstate(business_state: str, other_state: str) -> bool:
    business_state = (business_state or "").strip().lower()
    other_state = (other_state or "").strip().lower()
    if not business_state or not other_state:
        return False
    return business_state != other_state


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
    seq = next_sequence_number(db, models.JournalEntry)
    entry = models.JournalEntry(
        sequence_number=seq,
        number=format_document_number("JE", seq),
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


def create_manual_journal_entry(db: Session, entry_date, narration: str, lines: list[tuple[int, Decimal, Decimal]]) -> models.JournalEntry:
    _ensure_period_open(db, entry_date)
    if not narration or not narration.strip():
        raise ValueError("Narration is required")
    nonzero_lines = [(account_id, money(debit), money(credit)) for account_id, debit, credit in lines if money(debit) > 0 or money(credit) > 0]
    if len(nonzero_lines) < 2:
        raise ValueError("A journal entry needs at least two lines with an amount")
    resolved_lines = []
    for account_id, debit, credit in nonzero_lines:
        account = db.get(models.ChartOfAccount, account_id)
        if not account:
            raise ValueError(f"Account {account_id} not found")
        resolved_lines.append((account.code, debit, credit))
    entry = post_journal_entry(db, entry_date, narration.strip(), "Manual", None, resolved_lines)
    db.commit()
    return get_journal_entry(db, entry.id)


def reverse_manual_journal_entry(db: Session, entry_id: int) -> models.JournalEntry:
    entry = get_journal_entry(db, entry_id)
    if entry.source_type != "Manual":
        raise ValueError("Only manually created journal entries can be reversed")
    already_reversed = db.scalar(select(models.JournalEntry).where(models.JournalEntry.source_type == "ManualReversal", models.JournalEntry.source_id == entry.id))
    if already_reversed:
        raise ValueError("This journal entry has already been reversed")
    reversal_lines = [(line.account.code, line.credit, line.debit) for line in entry.lines]
    reversal = post_journal_entry(db, date.today(), f"Reversal of {entry.number}", "ManualReversal", entry.id, reversal_lines)
    db.commit()
    return get_journal_entry(db, reversal.id)


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


def credit_note_gst_deadline(supply_date: date) -> date:
    """Last date a credit note may still reduce output GST.

    Section 34(2) CGST Act: the adjustment must be declared by the 30th November
    following the end of the financial year of the original supply (September
    until the Finance Act 2022 moved it), or the date the annual return for that
    year is filed, whichever is earlier. Indian financial years run April-March.
    """
    fy_start_year = supply_date.year if supply_date.month >= 4 else supply_date.year - 1
    return date(fy_start_year + 1, 11, 30)


def issue_credit_note(db: Session, invoice_id: int, payload: CreditNoteCreate) -> models.CreditNote:
    _ensure_period_open(db, payload.note_date)
    invoice = get_invoice(db, invoice_id)
    if invoice.status == "Cancelled":
        raise ValueError("Cannot issue a credit note against a cancelled invoice")
    items, subtotal, gst_total = _build_note_items(models.CreditNoteItem, payload.items)
    grand_total = money(subtotal + gst_total)
    if grand_total <= 0:
        raise ValueError("Credit note total must be greater than zero")

    deadline = credit_note_gst_deadline(invoice.invoice_date)
    if payload.note_date > deadline:
        raise ValueError(
            f"The GST on a credit note against {invoice.number} (dated "
            f"{invoice.invoice_date:%d-%m-%Y}) can only be adjusted up to "
            f"{deadline:%d-%m-%Y} under section 34(2). After that date the tax "
            "stays paid - record a commercial credit through a manual journal entry instead."
        )

    # A credit note is capped by what was invoiced, not by what is still unpaid:
    # goods returned after the invoice was settled leave the customer in credit.
    already_credited = Decimal(
        db.scalar(
            select(func.coalesce(func.sum(models.CreditNote.grand_total), 0)).where(
                models.CreditNote.invoice_id == invoice.id,
                models.CreditNote.status != "Cancelled",
            )
        )
        or 0
    )
    if grand_total + already_credited > Decimal(invoice.grand_total):
        remaining = money(Decimal(invoice.grand_total) - already_credited)
        raise ValueError(
            f"Credit notes against {invoice.number} cannot exceed its value of "
            f"{invoice.grand_total}. Already credited: {already_credited}. Available: {remaining}."
        )

    seq = next_sequence_number(db, models.CreditNote)
    credit_note = models.CreditNote(
        sequence_number=seq,
        number=format_document_number("CN", seq),
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
    # Not floored at zero: crediting a settled invoice genuinely leaves the
    # business owing the customer, and that has to stay visible on the account.
    customer.pending_payment = money(Decimal(customer.pending_payment or 0) - grand_total)
    db.add(credit_note)
    db.flush()
    interstate = Decimal(invoice.igst or 0) > 0
    gst_lines = [(ACCOUNT_OUTPUT_IGST, credit_note.gst, Decimal("0"))] if interstate else _split_cgst_sgst(credit_note.gst, ACCOUNT_OUTPUT_CGST, ACCOUNT_OUTPUT_SGST, debit=True)
    post_journal_entry(db, credit_note.note_date, f"Credit note {credit_note.number} against {invoice.number}", "CreditNote", credit_note.id, [
        (ACCOUNT_SALES_RETURNS, credit_note.subtotal, Decimal("0")),
        *gst_lines,
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
    interstate = Decimal(invoice.igst or 0) > 0
    gst_lines = [(ACCOUNT_OUTPUT_IGST, Decimal("0"), credit_note.gst)] if interstate else _split_cgst_sgst(credit_note.gst, ACCOUNT_OUTPUT_CGST, ACCOUNT_OUTPUT_SGST, debit=False)
    post_journal_entry(db, date.today(), f"Cancellation of credit note {credit_note.number}", "CreditNoteCancellation", credit_note.id, [
        (ACCOUNT_RECEIVABLE, credit_note.grand_total, Decimal("0")),
        (ACCOUNT_SALES_RETURNS, Decimal("0"), credit_note.subtotal),
        *gst_lines,
    ])
    db.commit()
    db.expire_all()
    return get_credit_note(db, credit_note_id)


def issue_debit_note(db: Session, invoice_id: int, payload: DebitNoteCreate) -> models.DebitNote:
    _ensure_period_open(db, payload.note_date)
    invoice = get_invoice(db, invoice_id)
    if invoice.status == "Cancelled":
        raise ValueError("Cannot issue a debit note against a cancelled invoice")
    items, subtotal, gst_total = _build_note_items(models.DebitNoteItem, payload.items)
    grand_total = money(subtotal + gst_total)
    if grand_total <= 0:
        raise ValueError("Debit note total must be greater than zero")

    seq = next_sequence_number(db, models.DebitNote)
    debit_note = models.DebitNote(
        sequence_number=seq,
        number=format_document_number("DN", seq),
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
    interstate = Decimal(invoice.igst or 0) > 0
    gst_lines = [(ACCOUNT_OUTPUT_IGST, Decimal("0"), debit_note.gst)] if interstate else _split_cgst_sgst(debit_note.gst, ACCOUNT_OUTPUT_CGST, ACCOUNT_OUTPUT_SGST, debit=False)
    post_journal_entry(db, debit_note.note_date, f"Debit note {debit_note.number} against {invoice.number}", "DebitNote", debit_note.id, [
        (ACCOUNT_RECEIVABLE, debit_note.grand_total, Decimal("0")),
        (ACCOUNT_SALES, Decimal("0"), debit_note.subtotal),
        *gst_lines,
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
    interstate = Decimal(invoice.igst or 0) > 0
    gst_lines = [(ACCOUNT_OUTPUT_IGST, debit_note.gst, Decimal("0"))] if interstate else _split_cgst_sgst(debit_note.gst, ACCOUNT_OUTPUT_CGST, ACCOUNT_OUTPUT_SGST, debit=True)
    post_journal_entry(db, date.today(), f"Cancellation of debit note {debit_note.number}", "DebitNoteCancellation", debit_note.id, [
        (ACCOUNT_SALES, debit_note.subtotal, Decimal("0")),
        *gst_lines,
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
            selectinload(models.PurchaseBill.payments).joinedload(models.VendorPayment.bank_account),
            joinedload(models.PurchaseBill.vendor),
        )
    )
    return db.scalars(stmt).unique().one()


def create_purchase_bill(db: Session, vendor_id: int, payload: PurchaseBillCreate) -> models.PurchaseBill:
    _ensure_period_open(db, payload.bill_date)
    vendor = db.get(models.Vendor, vendor_id)
    if not vendor:
        raise ValueError("Vendor not found")
    items, subtotal, gst_total = _build_note_items(models.PurchaseBillItem, payload.items)
    grand_total = money(subtotal + gst_total)
    if grand_total <= 0:
        raise ValueError("Purchase bill total must be greater than zero")
    for item, payload_item in zip(items, payload.items):
        item.stock_item_id = payload_item.stock_item_id
        if payload_item.stock_item_id and not db.get(models.StockItem, payload_item.stock_item_id):
            raise ValueError(f"Stock item {payload_item.stock_item_id} not found")

    interstate = is_interstate(_business_state(db), vendor.state)
    seq = next_sequence_number(db, models.PurchaseBill)
    bill = models.PurchaseBill(
        sequence_number=seq,
        number=format_document_number("PB", seq),
        vendor_id=vendor.id,
        vendor_bill_number=payload.vendor_bill_number,
        bill_date=payload.bill_date,
        due_date=payload.due_date,
        status="Unpaid",
        subtotal=money(subtotal),
        cgst=Decimal("0") if interstate else money(gst_total / 2),
        sgst=Decimal("0") if interstate else money(gst_total / 2),
        igst=gst_total if interstate else Decimal("0"),
        grand_total=grand_total,
        paid_amount=Decimal("0"),
        pending_balance=grand_total,
        notes=payload.notes,
    )
    bill.items = items

    vendor.pending_payment = money(Decimal(vendor.pending_payment or 0) + grand_total)
    db.add(bill)
    db.flush()
    gst_lines = [(ACCOUNT_INPUT_IGST, bill.igst, Decimal("0"))] if interstate else [
        (ACCOUNT_INPUT_CGST, bill.cgst, Decimal("0")),
        (ACCOUNT_INPUT_SGST, bill.sgst, Decimal("0")),
    ]
    post_journal_entry(db, bill.bill_date, f"Purchase bill {bill.number} from {vendor.name}", "PurchaseBill", bill.id, [
        (ACCOUNT_PURCHASES, bill.subtotal, Decimal("0")),
        *gst_lines,
        (ACCOUNT_PAYABLE, Decimal("0"), bill.grand_total),
    ])
    for item in bill.items:
        if item.stock_item_id:
            stock_item = db.get(models.StockItem, item.stock_item_id)
            _post_stock_movement(db, stock_item, bill.bill_date, "In", Decimal(item.quantity), "Purchase", reference=bill.number, source_type="PurchaseBill", source_id=bill.id)
    db.commit()
    return get_purchase_bill(db, bill.id)


def record_vendor_payment(db: Session, purchase_bill_id: int, amount: Decimal, **kwargs) -> models.PurchaseBill:
    if kwargs.get("payment_date"):
        _ensure_period_open(db, kwargs["payment_date"])
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
    interstate = Decimal(bill.igst or 0) > 0
    gst_lines = [(ACCOUNT_INPUT_IGST, Decimal("0"), bill.igst)] if interstate else [
        (ACCOUNT_INPUT_CGST, Decimal("0"), bill.cgst),
        (ACCOUNT_INPUT_SGST, Decimal("0"), bill.sgst),
    ]
    post_journal_entry(db, date.today(), f"Cancellation of purchase bill {bill.number}", "PurchaseBillCancellation", bill.id, [
        (ACCOUNT_PAYABLE, bill.grand_total, Decimal("0")),
        (ACCOUNT_PURCHASES, Decimal("0"), bill.subtotal),
        *gst_lines,
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
    interstate = Decimal(bill.igst or 0) > 0
    gst_lines = [(ACCOUNT_INPUT_IGST, bill.igst, Decimal("0"))] if interstate else [
        (ACCOUNT_INPUT_CGST, bill.cgst, Decimal("0")),
        (ACCOUNT_INPUT_SGST, bill.sgst, Decimal("0")),
    ]
    post_journal_entry(db, date.today(), f"Reopening of purchase bill {bill.number}", "PurchaseBillReopen", bill.id, [
        (ACCOUNT_PURCHASES, bill.subtotal, Decimal("0")),
        *gst_lines,
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
    _ensure_period_open(db, payload.expense_date)
    seq = next_sequence_number(db, models.Expense)
    expense = models.Expense(sequence_number=seq, number=format_document_number("EX", seq))
    _apply_expense_payload(expense, payload)
    db.add(expense)
    db.flush()
    _post_expense_journal_entry(db, expense)
    db.commit()
    return get_expense(db, expense.id)


def update_expense(db: Session, expense_id: int, payload: ExpenseCreate) -> models.Expense:
    _ensure_period_open(db, payload.expense_date)
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


def get_fixed_asset(db: Session, fixed_asset_id: int) -> models.FixedAsset:
    stmt = (
        select(models.FixedAsset)
        .where(models.FixedAsset.id == fixed_asset_id)
        .options(selectinload(models.FixedAsset.depreciation_entries), joinedload(models.FixedAsset.vendor))
    )
    return db.scalars(stmt).unique().one()


def list_fixed_assets(db: Session) -> list[models.FixedAsset]:
    stmt = (
        select(models.FixedAsset)
        .options(selectinload(models.FixedAsset.depreciation_entries), joinedload(models.FixedAsset.vendor))
        .order_by(models.FixedAsset.id.desc())
    )
    return db.scalars(stmt).unique().all()


def create_fixed_asset(db: Session, payload: FixedAssetCreate) -> models.FixedAsset:
    _ensure_period_open(db, payload.purchase_date)
    if payload.purchase_cost <= 0:
        raise ValueError("Purchase cost must be greater than zero")
    if payload.salvage_value < 0 or payload.salvage_value >= payload.purchase_cost:
        raise ValueError("Salvage value must be zero or more, and less than the purchase cost")
    if payload.useful_life_years <= 0:
        raise ValueError("Useful life must be greater than zero years")
    if payload.depreciation_method == "Written Down Value" and (not payload.depreciation_rate or payload.depreciation_rate <= 0):
        raise ValueError("Written Down Value depreciation requires a depreciation rate")
    if payload.vendor_id and not db.get(models.Vendor, payload.vendor_id):
        raise ValueError("Vendor not found")

    asset = models.FixedAsset(
        code=next_code(db, models.FixedAsset, "FA"),
        name=payload.name,
        category=payload.category,
        purchase_date=payload.purchase_date,
        purchase_cost=money(payload.purchase_cost),
        salvage_value=money(payload.salvage_value),
        useful_life_years=payload.useful_life_years,
        depreciation_method=payload.depreciation_method,
        depreciation_rate=payload.depreciation_rate,
        vendor_id=payload.vendor_id,
        location=payload.location,
        notes=payload.notes,
        accumulated_depreciation=Decimal("0"),
        status="Active",
    )
    db.add(asset)
    db.flush()

    funding_code = _cash_or_bank_code(payload.payment_mode)
    payable_or_funding = ACCOUNT_PAYABLE if payload.vendor_id else funding_code
    post_journal_entry(db, asset.purchase_date, f"Acquisition of fixed asset {asset.name} ({asset.code})", "FixedAsset", asset.id, [
        (ACCOUNT_FIXED_ASSETS, asset.purchase_cost, Decimal("0")),
        (payable_or_funding, Decimal("0"), asset.purchase_cost),
    ])
    if payload.vendor_id:
        vendor = db.get(models.Vendor, payload.vendor_id)
        vendor.pending_payment = money(Decimal(vendor.pending_payment or 0) + asset.purchase_cost)
    db.commit()
    return get_fixed_asset(db, asset.id)


def record_depreciation(db: Session, fixed_asset_id: int, as_of_date) -> models.FixedAsset:
    _ensure_period_open(db, as_of_date)
    asset = get_fixed_asset(db, fixed_asset_id)
    if asset.status != "Active":
        raise ValueError("Depreciation can only be recorded for active assets")
    period_start = asset.last_depreciation_date or asset.purchase_date
    if as_of_date <= period_start:
        raise ValueError("The depreciation date must be after the last depreciation date")

    depreciable_base = money(Decimal(asset.purchase_cost) - Decimal(asset.salvage_value))
    book_value = money(Decimal(asset.purchase_cost) - Decimal(asset.accumulated_depreciation))
    remaining = money(book_value - Decimal(asset.salvage_value))
    if remaining <= 0:
        raise ValueError("This asset is already fully depreciated")

    days = (as_of_date - period_start).days
    if asset.depreciation_method == "Written Down Value":
        annual_amount = money(book_value * Decimal(asset.depreciation_rate) / Decimal("100"))
    else:
        annual_amount = money(depreciable_base / Decimal(asset.useful_life_years))
    period_amount = money(annual_amount * Decimal(days) / Decimal("365"))
    amount = min(period_amount, remaining)
    if amount <= 0:
        raise ValueError("No depreciation to record for this period")

    asset.accumulated_depreciation = money(Decimal(asset.accumulated_depreciation) + amount)
    asset.last_depreciation_date = as_of_date
    book_value_after = money(Decimal(asset.purchase_cost) - Decimal(asset.accumulated_depreciation))

    entry = models.DepreciationEntry(
        fixed_asset_id=asset.id,
        period_start=period_start,
        period_end=as_of_date,
        amount=amount,
        book_value_after=book_value_after,
    )
    db.add(entry)
    db.flush()

    post_journal_entry(db, as_of_date, f"Depreciation for {asset.name} ({asset.code})", "Depreciation", entry.id, [
        (ACCOUNT_DEPRECIATION_EXPENSE, amount, Decimal("0")),
        (ACCOUNT_ACCUMULATED_DEPRECIATION, Decimal("0"), amount),
    ])
    db.commit()
    db.expire_all()
    return get_fixed_asset(db, asset.id)


def dispose_fixed_asset(db: Session, fixed_asset_id: int, disposal_date, disposal_value: Decimal) -> models.FixedAsset:
    _ensure_period_open(db, disposal_date)
    asset = get_fixed_asset(db, fixed_asset_id)
    if asset.status != "Active":
        raise ValueError("This asset has already been disposed")
    disposal_value = money(disposal_value)
    if disposal_value < 0:
        raise ValueError("Disposal value cannot be negative")

    book_value = money(Decimal(asset.purchase_cost) - Decimal(asset.accumulated_depreciation))
    gain_loss = money(disposal_value - book_value)

    lines: list[tuple[str, Decimal, Decimal]] = [
        (ACCOUNT_BANK, disposal_value, Decimal("0")),
        (ACCOUNT_ACCUMULATED_DEPRECIATION, Decimal(asset.accumulated_depreciation), Decimal("0")),
        (ACCOUNT_FIXED_ASSETS, Decimal("0"), Decimal(asset.purchase_cost)),
    ]
    if gain_loss > 0:
        lines.append((ACCOUNT_GAIN_LOSS_ON_DISPOSAL, Decimal("0"), gain_loss))
    elif gain_loss < 0:
        lines.append((ACCOUNT_GAIN_LOSS_ON_DISPOSAL, -gain_loss, Decimal("0")))

    asset.status = "Disposed"
    asset.disposal_date = disposal_date
    asset.disposal_value = disposal_value
    db.flush()

    post_journal_entry(db, disposal_date, f"Disposal of fixed asset {asset.name} ({asset.code})", "FixedAssetDisposal", asset.id, lines)
    db.commit()
    db.expire_all()
    return get_fixed_asset(db, asset.id)


def list_financial_years(db: Session) -> list[models.FinancialYear]:
    return db.scalars(select(models.FinancialYear).order_by(models.FinancialYear.start_date)).all()


def get_financial_year(db: Session, financial_year_id: int) -> models.FinancialYear:
    fy = db.get(models.FinancialYear, financial_year_id)
    if not fy:
        raise ValueError("Financial year not found")
    return fy


def create_financial_year(db: Session, payload: FinancialYearCreate) -> models.FinancialYear:
    if payload.end_date <= payload.start_date:
        raise ValueError("End date must be after start date")
    overlap = db.scalar(
        select(models.FinancialYear).where(
            models.FinancialYear.start_date <= payload.end_date,
            models.FinancialYear.end_date >= payload.start_date,
        )
    )
    if overlap:
        raise ValueError(f"Overlaps with existing {overlap.label}")
    label = payload.label.strip() or f"FY {payload.start_date.year}-{str(payload.end_date.year)[-2:]}"
    if db.scalar(select(models.FinancialYear).where(models.FinancialYear.label == label)):
        raise ValueError(f"{label} already exists")
    fy = models.FinancialYear(label=label, start_date=payload.start_date, end_date=payload.end_date, status="Open")
    db.add(fy)
    db.commit()
    db.refresh(fy)
    return fy


def close_financial_year(
    db: Session,
    financial_year_id: int,
    total_income: Decimal,
    total_expense: Decimal,
    net_profit: Decimal,
    total_assets: Decimal,
    total_liabilities: Decimal,
    total_equity: Decimal,
) -> models.FinancialYear:
    fy = get_financial_year(db, financial_year_id)
    if fy.status == "Closed":
        raise ValueError(f"{fy.label} is already closed")
    if fy.end_date > date.today():
        raise ValueError("Cannot close a financial year that has not ended yet")
    earlier_open = db.scalar(
        select(models.FinancialYear).where(models.FinancialYear.status == "Open", models.FinancialYear.end_date < fy.end_date)
    )
    if earlier_open:
        raise ValueError(f"Close {earlier_open.label} first")

    fy.total_income = money(total_income)
    fy.total_expense = money(total_expense)
    fy.net_profit = money(net_profit)
    fy.total_assets = money(total_assets)
    fy.total_liabilities = money(total_liabilities)
    fy.total_equity = money(total_equity)
    fy.status = "Closed"
    fy.closed_at = datetime.utcnow()
    db.commit()
    db.refresh(fy)
    return fy


def reopen_financial_year(db: Session, financial_year_id: int) -> models.FinancialYear:
    fy = get_financial_year(db, financial_year_id)
    if fy.status != "Closed":
        raise ValueError(f"{fy.label} is not closed")
    later_closed = db.scalar(
        select(models.FinancialYear).where(models.FinancialYear.status == "Closed", models.FinancialYear.start_date > fy.start_date)
    )
    if later_closed:
        raise ValueError(f"Reopen {later_closed.label} first")
    fy.status = "Open"
    fy.closed_at = None
    db.commit()
    db.refresh(fy)
    return fy


def get_stock_item(db: Session, stock_item_id: int) -> models.StockItem:
    stmt = select(models.StockItem).where(models.StockItem.id == stock_item_id).options(selectinload(models.StockItem.movements))
    item = db.scalars(stmt).unique().one_or_none()
    if not item:
        raise ValueError("Stock item not found")
    return item


def list_stock_items(db: Session, low_stock: bool = False) -> list[models.StockItem]:
    stmt = select(models.StockItem).options(selectinload(models.StockItem.movements)).order_by(models.StockItem.name)
    items = db.scalars(stmt).unique().all()
    if low_stock:
        items = [i for i in items if Decimal(i.reorder_level) > 0 and Decimal(i.quantity_on_hand) <= Decimal(i.reorder_level)]
    return items


def _post_stock_movement(
    db: Session,
    stock_item: models.StockItem,
    movement_date,
    movement_type: str,
    quantity: Decimal,
    reason: str,
    reference: str = "",
    source_type: str = "Manual",
    source_id: int | None = None,
    notes: str = "",
) -> models.StockMovement:
    if movement_type not in ("In", "Out"):
        raise ValueError("Movement type must be 'In' or 'Out'")
    quantity = Decimal(quantity)
    if quantity <= 0:
        raise ValueError("Quantity must be greater than zero")
    current = Decimal(stock_item.quantity_on_hand)
    if movement_type == "In":
        new_balance = current + quantity
    else:
        if quantity > current:
            raise ValueError(f"Insufficient stock: {current} {stock_item.unit} on hand for {stock_item.name}")
        new_balance = current - quantity
    stock_item.quantity_on_hand = new_balance
    movement = models.StockMovement(
        stock_item_id=stock_item.id,
        movement_date=movement_date,
        movement_type=movement_type,
        reason=reason,
        quantity=quantity,
        balance_after=new_balance,
        reference=reference,
        source_type=source_type,
        source_id=source_id,
        notes=notes,
    )
    db.add(movement)
    db.flush()
    return movement


def create_stock_item(db: Session, payload: StockItemCreate) -> models.StockItem:
    item = models.StockItem(
        code=next_code(db, models.StockItem, "STK"),
        name=payload.name,
        category=payload.category,
        unit=payload.unit,
        hsn_code=payload.hsn_code,
        reorder_level=money(payload.reorder_level),
        quantity_on_hand=Decimal("0"),
        notes=payload.notes,
        status=payload.status,
    )
    db.add(item)
    db.flush()
    if Decimal(payload.opening_quantity) > 0:
        _post_stock_movement(db, item, date.today(), "In", Decimal(payload.opening_quantity), "Opening Stock")
    db.commit()
    return get_stock_item(db, item.id)


def update_stock_item(db: Session, stock_item_id: int, payload: StockItemCreate) -> models.StockItem:
    item = get_stock_item(db, stock_item_id)
    item.name = payload.name
    item.category = payload.category
    item.unit = payload.unit
    item.hsn_code = payload.hsn_code
    item.reorder_level = money(payload.reorder_level)
    item.notes = payload.notes
    item.status = payload.status
    db.commit()
    return get_stock_item(db, stock_item_id)


def record_stock_movement(db: Session, stock_item_id: int, payload: StockMovementCreate) -> models.StockItem:
    item = get_stock_item(db, stock_item_id)
    _post_stock_movement(db, item, payload.movement_date, payload.movement_type, payload.quantity, payload.reason, reference=payload.reference, notes=payload.notes)
    db.commit()
    db.expire_all()
    return get_stock_item(db, stock_item_id)
