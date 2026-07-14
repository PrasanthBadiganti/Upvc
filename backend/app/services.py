from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload, selectinload

from . import models
from .schemas import QuotationCreate

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


def create_quotation(db: Session, payload: QuotationCreate) -> models.Quotation:
    rule = db.get(models.PricingRule, 1)
    gst_rate = Decimal(rule.gst_rate if rule else 18)

    quote = models.Quotation(
        number=next_document_number(db, models.Quotation, "QT"),
        customer_id=payload.customer_id,
        quotation_date=payload.quotation_date,
        validity_days=payload.validity_days,
        sales_person=payload.sales_person,
        site_location=payload.site_location,
        address=payload.address,
        status=payload.status,
        transport=money(payload.transport),
        discount=money(payload.discount),
        notes=payload.notes,
    )

    subtotal = Decimal("0")
    for item in payload.items:
        sft = money(item.sft)
        if sft <= 0 and item.width_mm > 0 and item.height_mm > 0:
            sft = calculate_sft(item.width_mm, item.height_mm)
        total_sft = money(item.total_sft if item.total_sft > 0 else sft * item.quantity)
        amount = money(item.amount if item.amount > 0 else total_sft * item.rate_per_sft)
        subtotal += amount
        quote.items.append(
            models.QuotationItem(
                category=item.category,
                style=item.style,
                width_mm=money(item.width_mm),
                height_mm=money(item.height_mm),
                sft=sft,
                quantity=item.quantity,
                total_sft=total_sft,
                rate_per_sft=money(item.rate_per_sft),
                amount=amount,
                location=item.location,
                profile=item.profile,
                color=item.color,
                track=item.track,
                glass=item.glass,
                glass_color=item.glass_color,
                hardware=item.hardware,
                reinforcement=item.reinforcement,
                mesh=item.mesh,
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

    customer = db.get(models.Customer, payload.customer_id)
    if customer:
        customer.quote_value = money(Decimal(customer.quote_value or 0) + grand)
        customer.last_interaction = __import__("datetime").datetime.utcnow()
        if quote.status.lower() in {"sent", "quotation sent"}:
            customer.status = "Quotation Sent"

    db.add(quote)
    db.commit()
    return get_quotation(db, quote.id)


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
            )
        )
    quote.status = "Converted"
    customer = quote.customer
    customer.status = "Live"
    customer.pending_payment = money(Decimal(customer.pending_payment or 0) + invoice.pending_balance)
    db.add(invoice)
    db.commit()
    return get_invoice(db, invoice.id)


def record_payment(db: Session, invoice_id: int, amount: Decimal, **kwargs) -> models.Invoice:
    invoice = get_invoice(db, invoice_id)
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
    db.commit()
    return get_invoice(db, invoice_id)
