from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal
from io import BytesIO
import os
from pathlib import Path
import sys

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import func, or_, select
from sqlalchemy import text
from sqlalchemy.orm import Session, joinedload, selectinload

from . import models, schemas
from .database import Base, SessionLocal, engine, get_db
from .pdf import build_invoice_pdf, build_payment_receipt_pdf, build_quotation_pdf
from .seed import seed_database
from .services import convert_quotation_to_invoice, create_quotation, duplicate_quotation, get_invoice, get_payment, get_quotation, money, next_code, record_payment, update_quotation

app = FastAPI(title="UPVC Pro API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:4173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup() -> None:
    Base.metadata.create_all(bind=engine)
    ensure_schema()
    with SessionLocal() as db:
        seed_database(db)


def ensure_schema() -> None:
    if not engine.url.drivername.startswith("sqlite"):
        return
    migrations = {
        "customers": {
            "gst_number": "VARCHAR(40) DEFAULT ''",
            "notes": "TEXT DEFAULT ''",
        },
        "catalog_items": {
            "profile_brand": "VARCHAR(120) DEFAULT ''",
            "profile_series": "VARCHAR(120) DEFAULT ''",
            "glass_type": "VARCHAR(120) DEFAULT ''",
            "glass_thickness": "VARCHAR(60) DEFAULT ''",
            "glass_color": "VARCHAR(80) DEFAULT ''",
            "reinforcement": "VARCHAR(120) DEFAULT ''",
            "mesh": "VARCHAR(120) DEFAULT ''",
            "gst_percent": "NUMERIC(6, 2) DEFAULT 18",
            "installation_rate": "NUMERIC(12, 2) DEFAULT 0",
            "rounding_rule": "VARCHAR(50) DEFAULT 'Round up'",
        },
        "quotation_items": {
            "catalog_item_id": "INTEGER",
        },
    }
    with engine.begin() as connection:
        for table, columns in migrations.items():
            existing = {row[1] for row in connection.execute(text(f"PRAGMA table_info({table})"))}
            for column, definition in columns.items():
                if column not in existing:
                    connection.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {definition}"))


def get_or_create_business_settings(db: Session) -> models.BusinessSettings:
    settings = db.get(models.BusinessSettings, 1)
    if not settings:
        settings = models.BusinessSettings(id=1)
        db.add(settings)
        db.commit()
        db.refresh(settings)
    return settings


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


def sync_customer_financials(customer: models.Customer) -> None:
    customer.quote_value = money(sum((Decimal(q.grand_total or 0) for q in customer.quotations), Decimal("0")))
    invoice_total = sum((Decimal(i.grand_total or 0) for i in customer.invoices), Decimal("0"))
    paid_total = sum((Decimal(i.paid_amount or 0) for i in customer.invoices), Decimal("0"))
    pending_total = sum((Decimal(i.pending_balance or 0) for i in customer.invoices), Decimal("0"))
    customer.pending_payment = money(pending_total)
    customer._invoice_total = money(invoice_total)
    customer._paid_total = money(paid_total)


def build_customer_profile(customer: models.Customer) -> schemas.CustomerProfileResponse:
    sync_customer_financials(customer)
    quotations = sorted(customer.quotations, key=lambda q: q.created_at, reverse=True)
    invoices = sorted(customer.invoices, key=lambda i: i.created_at, reverse=True)
    followups = sorted(customer.followups, key=lambda f: f.scheduled_at, reverse=True)
    payments = sorted((payment for invoice in invoices for payment in invoice.payments), key=lambda p: p.created_at, reverse=True)

    timeline: list[schemas.CustomerTimelineItem] = [
        schemas.CustomerTimelineItem(type="customer", title="Customer Added", detail=f"{customer.name} created", at=customer.created_at)
    ]
    for quote in quotations:
        timeline.append(schemas.CustomerTimelineItem(type="quotation", title=f"Quotation {quote.status}", detail=f"{quote.number} - Rs. {Decimal(quote.grand_total or 0):,.0f}", at=quote.created_at))
    for invoice in invoices:
        timeline.append(schemas.CustomerTimelineItem(type="invoice", title=f"Invoice {invoice.status}", detail=f"{invoice.number} - Rs. {Decimal(invoice.grand_total or 0):,.0f}", at=invoice.created_at))
    for payment in payments:
        timeline.append(schemas.CustomerTimelineItem(type="payment", title="Payment Received", detail=f"Rs. {Decimal(payment.amount or 0):,.0f} via {payment.mode}", at=payment.created_at))
    for followup in followups:
        timeline.append(schemas.CustomerTimelineItem(type="followup", title=f"Follow-up {followup.status}", detail=f"{followup.purpose} via {followup.channel}", at=followup.created_at))
    timeline.sort(key=lambda row: row.at, reverse=True)

    metrics = {
        "quotation_count": len(quotations),
        "quotation_value": float(customer.quote_value),
        "invoice_count": len(invoices),
        "invoice_value": float(getattr(customer, "_invoice_total", Decimal("0"))),
        "paid_amount": float(getattr(customer, "_paid_total", Decimal("0"))),
        "pending_amount": float(customer.pending_payment),
        "followup_count": len(followups),
        "open_followups": sum(1 for f in followups if f.status != "Completed"),
    }
    return schemas.CustomerProfileResponse(
        customer=customer,
        metrics=metrics,
        quotations=quotations,
        invoices=invoices,
        payments=[
            schemas.CustomerPaymentSummary(
                id=payment.id,
                invoice_id=payment.invoice_id,
                payment_date=payment.payment_date,
                mode=payment.mode,
                reference_number=payment.reference_number,
                amount=payment.amount,
                received_by=payment.received_by,
                notes=payment.notes,
                created_at=payment.created_at,
                invoice_number=payment.invoice.number,
            )
            for payment in payments
        ],
        followups=followups,
        timeline=timeline[:20],
    )


@app.get("/api/dashboard", response_model=schemas.DashboardResponse)
def dashboard(db: Session = Depends(get_db)) -> schemas.DashboardResponse:
    customers = db.scalars(select(models.Customer)).all()
    invoices = db.scalars(select(models.Invoice)).all()
    quotations = db.scalars(select(models.Quotation).options(joinedload(models.Quotation.customer))).unique().all()
    followups = db.scalars(select(models.Followup).options(joinedload(models.Followup.customer))).unique().all()
    payments = db.scalars(select(models.Payment).options(joinedload(models.Payment.invoice).joinedload(models.Invoice.customer))).unique().all()

    pending = sum((Decimal(i.pending_balance or 0) for i in invoices), Decimal("0"))
    received = sum((Decimal(i.paid_amount or 0) for i in invoices), Decimal("0"))
    metrics = {
        "total_leads": len(customers),
        "live_customers": sum(1 for c in customers if c.status in {"Live", "Completed"}),
        "pending_customers": sum(1 for c in customers if c.status in {"New", "Negotiation", "Quotation Sent"}),
        "quotations_this_month": sum(1 for q in quotations if q.quotation_date.year == date.today().year and q.quotation_date.month == date.today().month),
        "pending_payments": float(pending),
        "revenue_received": float(received),
    }
    month_keys = []
    current = date.today().replace(day=1)
    for offset in range(11, -1, -1):
        year = current.year
        month = current.month - offset
        while month <= 0:
            month += 12
            year -= 1
        month_keys.append((year, month))
    monthly = [
        {
            "month": date(year, month, 1).strftime("%b '%y"),
            "quotations": sum(1 for q in quotations if q.quotation_date.year == year and q.quotation_date.month == month),
            "invoices": sum(1 for i in invoices if i.invoice_date.year == year and i.invoice_date.month == month),
        }
        for year, month in month_keys
    ]
    status_counts: dict[str, int] = {}
    for c in customers:
        group = "Active Customers" if c.status in {"Live", "Completed"} else "Pending Customers" if c.status in {"Negotiation", "Quotation Sent"} else "New Leads" if c.status == "New" else "Lost/Inactive"
        status_counts[group] = status_counts.get(group, 0) + 1
    customer_status = [{"name": name, "value": value} for name, value in status_counts.items()]

    pending_payments = []
    for inv in sorted((i for i in invoices if Decimal(i.pending_balance or 0) > 0), key=lambda x: x.due_date)[:5]:
        pending_payments.append({"customer": inv.customer.name, "invoice_no": inv.number, "due_date": inv.due_date.isoformat(), "balance": float(inv.pending_balance), "status": "Overdue" if inv.due_date < date.today() else "Due Soon"})
    today = date.today()
    today_followups = [
        {"time": f.scheduled_at.strftime("%I:%M %p"), "customer": f.customer.name, "purpose": f.purpose, "channel": f.channel}
        for f in followups if f.scheduled_at.date() == today
    ][:5]
    activity_rows: list[dict[str, object]] = []
    for quote in quotations:
        activity_rows.append({"type": "quotation", "title": "Quotation Created", "detail": f"{quote.number} for {quote.customer.name}", "at": quote.created_at})
    for invoice in invoices:
        activity_rows.append({"type": "invoice", "title": "Invoice Generated", "detail": f"{invoice.number} for {invoice.customer.name}", "at": invoice.created_at})
    for payment in payments:
        activity_rows.append({"type": "payment", "title": "Payment Received", "detail": f"Rs. {Decimal(payment.amount):,.0f} from {payment.invoice.customer.name}", "at": payment.created_at})
    for customer in customers:
        activity_rows.append({"type": "customer", "title": "Customer Added", "detail": customer.name, "at": customer.created_at})
    for followup in followups:
        if followup.status == "Completed":
            activity_rows.append({"type": "followup", "title": "Follow-up Completed", "detail": f"{followup.purpose} for {followup.customer.name}", "at": followup.created_at})
    activity_rows.sort(key=lambda row: row["at"], reverse=True)
    recent_activity = [
        {
            "type": str(row["type"]),
            "title": str(row["title"]),
            "detail": str(row["detail"]),
            "when": row["at"].strftime("%d %b, %I:%M %p") if isinstance(row["at"], datetime) else "",
        }
        for row in activity_rows[:5]
    ]
    return schemas.DashboardResponse(metrics=metrics, monthly=monthly, customer_status=customer_status, pending_payments=pending_payments, today_followups=today_followups, recent_activity=recent_activity)


@app.get("/api/customers", response_model=list[schemas.CustomerRead])
def list_customers(search: str = "", status: str = "", db: Session = Depends(get_db)):
    stmt = (
        select(models.Customer)
        .options(selectinload(models.Customer.quotations), selectinload(models.Customer.invoices).selectinload(models.Invoice.payments))
        .order_by(models.Customer.id)
    )
    if search:
        q = f"%{search}%"
        stmt = stmt.where(or_(models.Customer.name.ilike(q), models.Customer.phone.ilike(q), models.Customer.email.ilike(q)))
    if status:
        stmt = stmt.where(models.Customer.status == status)
    customers = db.scalars(stmt).unique().all()
    for customer in customers:
        sync_customer_financials(customer)
    db.commit()
    return customers


@app.get("/api/customers/{customer_id}/profile", response_model=schemas.CustomerProfileResponse)
def customer_profile(customer_id: int, db: Session = Depends(get_db)):
    stmt = (
        select(models.Customer)
        .where(models.Customer.id == customer_id)
        .options(
            selectinload(models.Customer.quotations),
            selectinload(models.Customer.invoices).selectinload(models.Invoice.payments),
            selectinload(models.Customer.followups),
        )
    )
    customer = db.scalars(stmt).unique().one_or_none()
    if not customer:
        raise HTTPException(404, "Customer not found")
    profile = build_customer_profile(customer)
    db.commit()
    return profile


@app.post("/api/customers", response_model=schemas.CustomerRead, status_code=201)
def add_customer(payload: schemas.CustomerCreate, db: Session = Depends(get_db)):
    customer = models.Customer(**payload.model_dump(exclude={"code"}), code=payload.code or next_code(db, models.Customer, "CUST"))
    db.add(customer)
    db.commit()
    db.refresh(customer)
    return customer


@app.put("/api/customers/{customer_id}", response_model=schemas.CustomerRead)
def update_customer(customer_id: int, payload: schemas.CustomerCreate, db: Session = Depends(get_db)):
    customer = db.get(models.Customer, customer_id)
    if not customer:
        raise HTTPException(404, "Customer not found")
    for key, value in payload.model_dump(exclude={"code"}).items():
        setattr(customer, key, value)
    if payload.code:
        customer.code = payload.code
    db.commit()
    db.refresh(customer)
    return customer


@app.delete("/api/customers/{customer_id}", status_code=204)
def delete_customer(customer_id: int, db: Session = Depends(get_db)):
    customer = db.get(models.Customer, customer_id)
    if not customer:
        raise HTTPException(404, "Customer not found")
    db.delete(customer)
    db.commit()


@app.get("/api/catalog", response_model=list[schemas.CatalogItemRead])
def list_catalog(search: str = "", category: str = "", product_type: str = "", status: str = "", db: Session = Depends(get_db)):
    stmt = select(models.CatalogItem).order_by(models.CatalogItem.id)
    if search:
        q = f"%{search}%"
        stmt = stmt.where(or_(
            models.CatalogItem.name.ilike(q),
            models.CatalogItem.product_type.ilike(q),
            models.CatalogItem.profile.ilike(q),
            models.CatalogItem.profile_brand.ilike(q),
            models.CatalogItem.profile_series.ilike(q),
            models.CatalogItem.glass.ilike(q),
            models.CatalogItem.glass_type.ilike(q),
            models.CatalogItem.hardware.ilike(q),
        ))
    if category:
        stmt = stmt.where(models.CatalogItem.category == category)
    if product_type:
        stmt = stmt.where(models.CatalogItem.product_type == product_type)
    if status:
        stmt = stmt.where(models.CatalogItem.status == status)
    return db.scalars(stmt).all()


@app.get("/api/catalog/summary")
def catalog_summary(db: Session = Depends(get_db)):
    items = db.scalars(select(models.CatalogItem)).all()
    return {
        "categories": sorted({item.category for item in items if item.category}),
        "product_types": sorted({item.product_type for item in items if item.product_type}),
        "profile_brands": sorted({item.profile_brand or item.profile for item in items if item.profile_brand or item.profile}),
        "glass_types": sorted({item.glass_type or item.glass for item in items if item.glass_type or item.glass}),
        "active_count": sum(1 for item in items if item.status == "Active"),
        "inactive_count": sum(1 for item in items if item.status != "Active"),
    }


@app.post("/api/catalog", response_model=schemas.CatalogItemRead, status_code=201)
def add_catalog_item(payload: schemas.CatalogItemBase, db: Session = Depends(get_db)):
    item = models.CatalogItem(**payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@app.put("/api/catalog/{item_id}", response_model=schemas.CatalogItemRead)
def update_catalog_item(item_id: int, payload: schemas.CatalogItemBase, db: Session = Depends(get_db)):
    item = db.get(models.CatalogItem, item_id)
    if not item:
        raise HTTPException(404, "Catalog item not found")
    for key, value in payload.model_dump().items():
        setattr(item, key, value)
    db.commit()
    db.refresh(item)
    return item


@app.delete("/api/catalog/{item_id}", status_code=204)
def delete_catalog_item(item_id: int, db: Session = Depends(get_db)):
    item = db.get(models.CatalogItem, item_id)
    if not item:
        raise HTTPException(404, "Catalog item not found")
    db.delete(item)
    db.commit()


@app.get("/api/pricing-rules", response_model=schemas.PricingRuleRead)
def get_pricing_rules(db: Session = Depends(get_db)):
    rule = db.get(models.PricingRule, 1)
    if not rule:
        rule = models.PricingRule(id=1)
        db.add(rule)
        db.commit()
        db.refresh(rule)
    return rule


@app.put("/api/pricing-rules", response_model=schemas.PricingRuleRead)
def update_pricing_rules(payload: schemas.PricingRulePayload, db: Session = Depends(get_db)):
    rule = db.get(models.PricingRule, 1) or models.PricingRule(id=1)
    for key, value in payload.model_dump().items():
        setattr(rule, key, value)
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule


@app.get("/api/business-settings", response_model=schemas.BusinessSettingsRead)
def get_business_settings(db: Session = Depends(get_db)):
    return get_or_create_business_settings(db)


@app.put("/api/business-settings", response_model=schemas.BusinessSettingsRead)
def update_business_settings(payload: schemas.BusinessSettingsPayload, db: Session = Depends(get_db)):
    settings = get_or_create_business_settings(db)
    for key, value in payload.model_dump().items():
        setattr(settings, key, value)
    db.commit()
    db.refresh(settings)
    return settings


@app.get("/api/quotations", response_model=list[schemas.QuotationRead])
def list_quotations(db: Session = Depends(get_db)):
    stmt = select(models.Quotation).options(selectinload(models.Quotation.items), joinedload(models.Quotation.customer)).order_by(models.Quotation.id.desc())
    return db.scalars(stmt).unique().all()


@app.get("/api/quotations/{quotation_id}", response_model=schemas.QuotationRead)
def read_quotation(quotation_id: int, db: Session = Depends(get_db)):
    try:
        return get_quotation(db, quotation_id)
    except Exception as exc:
        raise HTTPException(404, "Quotation not found") from exc


@app.post("/api/quotations", response_model=schemas.QuotationRead, status_code=201)
def add_quotation(payload: schemas.QuotationCreate, db: Session = Depends(get_db)):
    if not db.get(models.Customer, payload.customer_id):
        raise HTTPException(404, "Customer not found")
    return create_quotation(db, payload)


@app.put("/api/quotations/{quotation_id}", response_model=schemas.QuotationRead)
def edit_quotation(quotation_id: int, payload: schemas.QuotationUpdate, db: Session = Depends(get_db)):
    if not db.get(models.Customer, payload.customer_id):
        raise HTTPException(404, "Customer not found")
    try:
        return update_quotation(db, quotation_id, payload)
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc
    except Exception as exc:
        raise HTTPException(404, "Quotation not found") from exc


@app.put("/api/quotations/{quotation_id}/status", response_model=schemas.QuotationRead)
def update_quotation_status(quotation_id: int, status: str = Query(...), db: Session = Depends(get_db)):
    quote = db.get(models.Quotation, quotation_id)
    if not quote:
        raise HTTPException(404, "Quotation not found")
    quote.status = status
    db.commit()
    return get_quotation(db, quotation_id)


@app.post("/api/quotations/{quotation_id}/duplicate", response_model=schemas.QuotationRead, status_code=201)
def duplicate_quote(quotation_id: int, db: Session = Depends(get_db)):
    try:
        return duplicate_quotation(db, quotation_id, revision=False)
    except Exception as exc:
        raise HTTPException(404, "Quotation not found") from exc


@app.post("/api/quotations/{quotation_id}/revise", response_model=schemas.QuotationRead, status_code=201)
def revise_quote(quotation_id: int, db: Session = Depends(get_db)):
    try:
        return duplicate_quotation(db, quotation_id, revision=True)
    except Exception as exc:
        raise HTTPException(404, "Quotation not found") from exc


@app.post("/api/quotations/{quotation_id}/convert", response_model=schemas.InvoiceRead)
def convert_quotation(quotation_id: int, db: Session = Depends(get_db)):
    try:
        return convert_quotation_to_invoice(db, quotation_id)
    except Exception as exc:
        raise HTTPException(400, str(exc)) from exc


@app.get("/api/quotations/{quotation_id}/pdf")
def quotation_pdf(quotation_id: int, db: Session = Depends(get_db)):
    try:
        quotation = get_quotation(db, quotation_id)
    except Exception as exc:
        raise HTTPException(404, "Quotation not found") from exc
    data = build_quotation_pdf(quotation, get_or_create_business_settings(db))
    return StreamingResponse(BytesIO(data), media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="{quotation.number}.pdf"'})


@app.get("/api/invoices", response_model=list[schemas.InvoiceRead])
def list_invoices(db: Session = Depends(get_db)):
    stmt = select(models.Invoice).options(selectinload(models.Invoice.items), selectinload(models.Invoice.payments), joinedload(models.Invoice.customer), joinedload(models.Invoice.quotation).selectinload(models.Quotation.items), joinedload(models.Invoice.quotation).joinedload(models.Quotation.customer)).order_by(models.Invoice.id.desc())
    return db.scalars(stmt).unique().all()


@app.get("/api/invoices/{invoice_id}", response_model=schemas.InvoiceRead)
def read_invoice(invoice_id: int, db: Session = Depends(get_db)):
    try:
        return get_invoice(db, invoice_id)
    except Exception as exc:
        raise HTTPException(404, "Invoice not found") from exc


@app.post("/api/invoices/{invoice_id}/payments", response_model=schemas.InvoiceRead, status_code=201)
def add_payment(invoice_id: int, payload: schemas.PaymentCreate, db: Session = Depends(get_db)):
    try:
        return record_payment(db, invoice_id, payload.amount, **payload.model_dump(exclude={"amount"}))
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    except Exception as exc:
        raise HTTPException(404, "Invoice not found") from exc


@app.get("/api/payments", response_model=list[schemas.PaymentRead])
def list_payments(db: Session = Depends(get_db)):
    return db.scalars(select(models.Payment).order_by(models.Payment.id.desc())).all()


@app.get("/api/payments/{payment_id}", response_model=schemas.PaymentRead)
def read_payment(payment_id: int, db: Session = Depends(get_db)):
    try:
        return get_payment(db, payment_id)
    except Exception as exc:
        raise HTTPException(404, "Payment not found") from exc


@app.get("/api/payments/{payment_id}/receipt")
def payment_receipt(payment_id: int, db: Session = Depends(get_db)):
    try:
        payment = get_payment(db, payment_id)
    except Exception as exc:
        raise HTTPException(404, "Payment not found") from exc
    data = build_payment_receipt_pdf(payment, get_or_create_business_settings(db))
    filename = f"Receipt-{payment.invoice.number}-{payment.id}.pdf"
    return StreamingResponse(BytesIO(data), media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="{filename}"'})


@app.get("/api/invoices/{invoice_id}/pdf")
def invoice_pdf(invoice_id: int, db: Session = Depends(get_db)):
    try:
        invoice = get_invoice(db, invoice_id)
    except Exception as exc:
        raise HTTPException(404, "Invoice not found") from exc
    data = build_invoice_pdf(invoice, get_or_create_business_settings(db))
    return StreamingResponse(BytesIO(data), media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="{invoice.number}.pdf"'})


@app.get("/api/followups", response_model=list[schemas.FollowupRead])
def list_followups(status: str = "", db: Session = Depends(get_db)):
    stmt = select(models.Followup).options(joinedload(models.Followup.customer)).order_by(models.Followup.scheduled_at)
    if status:
        stmt = stmt.where(models.Followup.status == status)
    return db.scalars(stmt).unique().all()


@app.post("/api/followups", response_model=schemas.FollowupRead, status_code=201)
def add_followup(payload: schemas.FollowupCreate, db: Session = Depends(get_db)):
    if not db.get(models.Customer, payload.customer_id):
        raise HTTPException(404, "Customer not found")
    followup = models.Followup(**payload.model_dump())
    db.add(followup)
    db.commit()
    stmt = select(models.Followup).where(models.Followup.id == followup.id).options(joinedload(models.Followup.customer))
    return db.scalars(stmt).unique().one()


@app.put("/api/followups/{followup_id}", response_model=schemas.FollowupRead)
def update_followup(followup_id: int, payload: schemas.FollowupCreate, db: Session = Depends(get_db)):
    followup = db.get(models.Followup, followup_id)
    if not followup:
        raise HTTPException(404, "Follow-up not found")
    for key, value in payload.model_dump().items():
        setattr(followup, key, value)
    db.commit()
    stmt = select(models.Followup).where(models.Followup.id == followup.id).options(joinedload(models.Followup.customer))
    return db.scalars(stmt).unique().one()


@app.get("/api/reports")
def reports(db: Session = Depends(get_db)):
    today = date.today()
    customers = db.scalars(select(models.Customer)).all()
    quotations = db.scalars(select(models.Quotation).options(joinedload(models.Quotation.customer))).unique().all()
    invoices = db.scalars(select(models.Invoice).options(joinedload(models.Invoice.customer), joinedload(models.Invoice.quotation), selectinload(models.Invoice.payments))).unique().all()
    payments = db.scalars(select(models.Payment).options(joinedload(models.Payment.invoice).joinedload(models.Invoice.customer))).unique().all()

    active_invoices = [invoice for invoice in invoices if invoice.status != "Cancelled"]
    pending_invoices = [invoice for invoice in active_invoices if Decimal(invoice.pending_balance or 0) > 0]
    total_quotes = sum((Decimal(quote.grand_total or 0) for quote in quotations), Decimal("0"))
    total_invoices = sum((Decimal(invoice.grand_total or 0) for invoice in active_invoices), Decimal("0"))
    received = sum((Decimal(payment.amount or 0) for payment in payments if payment.invoice.status != "Cancelled"), Decimal("0"))
    pending = sum((Decimal(invoice.pending_balance or 0) for invoice in pending_invoices), Decimal("0"))

    by_status: dict[str, int] = {}
    for customer in customers:
        by_status[customer.status] = by_status.get(customer.status, 0) + 1

    month_keys = []
    current = today.replace(day=1)
    for offset in range(11, -1, -1):
        year = current.year
        month = current.month - offset
        while month <= 0:
            month += 12
            year -= 1
        month_keys.append((year, month))
    monthly = []
    for year, month in month_keys:
        monthly.append({
            "month": date(year, month, 1).strftime("%b '%y"),
            "quotation_value": float(sum((Decimal(q.grand_total or 0) for q in quotations if q.quotation_date.year == year and q.quotation_date.month == month), Decimal("0"))),
            "invoice_value": float(sum((Decimal(i.grand_total or 0) for i in active_invoices if i.invoice_date.year == year and i.invoice_date.month == month), Decimal("0"))),
            "received": float(sum((Decimal(p.amount or 0) for p in payments if p.payment_date.year == year and p.payment_date.month == month and p.invoice.status != "Cancelled"), Decimal("0"))),
            "pending": float(sum((Decimal(i.pending_balance or 0) for i in pending_invoices if i.due_date.year == year and i.due_date.month == month), Decimal("0"))),
        })

    aging_defs = [
        ("Current", None, 0),
        ("1-30 Days", 1, 30),
        ("31-60 Days", 31, 60),
        ("60+ Days", 61, None),
    ]
    aging = []
    for label, start, end in aging_defs:
        rows = []
        for invoice in pending_invoices:
            overdue_days = (today - invoice.due_date).days
            if start is None and overdue_days <= 0:
                rows.append(invoice)
            elif start is not None and end is not None and start <= overdue_days <= end:
                rows.append(invoice)
            elif start is not None and end is None and overdue_days >= start:
                rows.append(invoice)
        aging.append({"bucket": label, "count": len(rows), "amount": float(sum((Decimal(i.pending_balance or 0) for i in rows), Decimal("0")))})

    top_pending = [
        {
            "customer": invoice.customer.name,
            "invoice_no": invoice.number,
            "due_date": invoice.due_date.isoformat(),
            "days_overdue": max(0, (today - invoice.due_date).days),
            "pending": float(invoice.pending_balance),
            "status": "Overdue" if invoice.due_date < today else "Due Soon",
        }
        for invoice in sorted(pending_invoices, key=lambda row: Decimal(row.pending_balance or 0), reverse=True)[:10]
    ]

    salespeople = sorted({q.sales_person or "Unassigned" for q in quotations} | {c.assigned_to or "Unassigned" for c in customers})
    salesperson_summary = []
    for person in salespeople:
        person_quotes = [q for q in quotations if (q.sales_person or "Unassigned") == person]
        person_invoices = [i for i in active_invoices if (i.quotation.sales_person if i.quotation else i.customer.assigned_to) == person]
        person_payments = [p for p in payments if p.invoice.status != "Cancelled" and (p.invoice.quotation.sales_person if p.invoice.quotation else p.invoice.customer.assigned_to) == person]
        salesperson_summary.append({
            "sales_person": person,
            "quotation_count": len(person_quotes),
            "quotation_value": float(sum((Decimal(q.grand_total or 0) for q in person_quotes), Decimal("0"))),
            "invoice_count": len(person_invoices),
            "invoice_value": float(sum((Decimal(i.grand_total or 0) for i in person_invoices), Decimal("0"))),
            "received": float(sum((Decimal(p.amount or 0) for p in person_payments), Decimal("0"))),
        })

    converted_quotes = sum(1 for quote in quotations if quote.status == "Converted" or quote.invoice)
    conversion_summary = {
        "quotation_count": len(quotations),
        "converted_count": converted_quotes,
        "open_count": max(0, len(quotations) - converted_quotes),
        "conversion_rate": round((converted_quotes / len(quotations) * 100), 2) if quotations else 0,
    }

    return {
        "total_quote_value": float(total_quotes),
        "total_invoice_value": float(total_invoices),
        "received": float(received),
        "pending": float(pending),
        "customer_status": [{"name": status, "value": count} for status, count in sorted(by_status.items())],
        "monthly": monthly,
        "aging": aging,
        "top_pending": top_pending,
        "salesperson_summary": salesperson_summary,
        "conversion_summary": conversion_summary,
    }

def _frontend_dist() -> Path:
    configured = os.getenv("UPVC_FRONTEND_DIST")
    if configured:
        return Path(configured)
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS")) / "frontend" / "dist"
    return Path(__file__).resolve().parents[2] / "frontend" / "dist"


# Serve the prebuilt frontend from the same local FastAPI process.
# This removes Node/npm from the normal installation and startup path.
FRONTEND_DIST = _frontend_dist()
ASSETS_DIR = FRONTEND_DIST / "assets"

if ASSETS_DIR.exists():
    app.mount("/assets", StaticFiles(directory=str(ASSETS_DIR)), name="frontend-assets")


@app.get("/", include_in_schema=False)
def frontend_root():
    index_file = FRONTEND_DIST / "index.html"
    if not index_file.exists():
        raise HTTPException(503, "Prebuilt frontend files are missing")
    return FileResponse(index_file)


@app.get("/{full_path:path}", include_in_schema=False)
def frontend_spa(full_path: str):
    # API URLs should never silently fall back to the UI.
    if full_path.startswith("api/"):
        raise HTTPException(404, "API endpoint not found")

    index_file = FRONTEND_DIST / "index.html"
    if not index_file.exists():
        raise HTTPException(503, "Prebuilt frontend files are missing")
    return FileResponse(index_file)
