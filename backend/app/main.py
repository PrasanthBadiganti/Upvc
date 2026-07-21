from __future__ import annotations

import csv
import json
from datetime import date, datetime, timedelta
from decimal import Decimal
from io import BytesIO, StringIO
import os
from pathlib import Path
import sys

from fastapi import Depends, FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import func, or_, select
from sqlalchemy import text
from sqlalchemy.orm import Session, joinedload, selectinload

from . import models, schemas
from .database import Base, DEFAULT_DB_PATH, SessionLocal, engine, get_db
from .gst_reports import ap_aging_report, balance_sheet_report, cash_flow_statement, gstr1_offline_json, gstr1_report, gstr3b_report, hsn_summary_report, profit_and_loss_report, purchase_register, sales_register
from .opening_balances import commit_opening_balances, preview_opening_balances
from .party_import import commit_customer_import, commit_vendor_import, preview_customer_import, preview_vendor_import
from .pdf import build_credit_note_pdf, build_debit_note_pdf, build_invoice_pdf, build_payment_receipt_pdf, build_purchase_bill_pdf, build_quotation_pdf
from .seed import seed_database
from .services import cancel_credit_note, cancel_debit_note, cancel_invoice, cancel_purchase_bill, close_financial_year, convert_quotation_to_invoice, create_expense, create_financial_year, create_fixed_asset, create_manual_journal_entry, create_purchase_bill, create_quotation, create_stock_item, delete_expense, dispose_fixed_asset, duplicate_quotation, get_account_ledger, get_credit_note, get_debit_note, get_expense, get_financial_year, get_fixed_asset, get_invoice, get_journal_entry, get_payment, get_purchase_bill, get_quotation, get_stock_item, get_trial_balance, issue_credit_note, issue_debit_note, list_chart_of_accounts, list_financial_years, list_fixed_assets, list_journal_entries, list_stock_items, money, next_code, record_depreciation, record_payment, record_stock_movement, record_vendor_payment, reopen_financial_year, reopen_invoice, reopen_purchase_bill, reverse_manual_journal_entry, update_expense, update_quotation, update_stock_item
from .tally_export import build_tally_masters_xml, build_tally_vouchers_xml

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
            "state": "VARCHAR(60) DEFAULT ''",
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
            "hsn_code": "VARCHAR(20) DEFAULT ''",
        },
        "quotation_items": {
            "catalog_item_id": "INTEGER",
            "hsn_code": "VARCHAR(20) DEFAULT ''",
        },
        "invoice_items": {
            "hsn_code": "VARCHAR(20) DEFAULT ''",
        },
        "invoices": {
            "igst": "NUMERIC(14, 2) DEFAULT 0",
        },
        "vendors": {
            "state": "VARCHAR(60) DEFAULT ''",
        },
        "purchase_bills": {
            "igst": "NUMERIC(14, 2) DEFAULT 0",
        },
        "purchase_bill_items": {
            "stock_item_id": "INTEGER",
        },
        "business_settings": {
            "logo_path": "VARCHAR(260) DEFAULT ''",
            "state": "VARCHAR(60) DEFAULT 'Andhra Pradesh'",
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


UPLOAD_DIR = DEFAULT_DB_PATH.parent / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def _logo_public_path(filename: str) -> str:
    return f"/uploads/{filename}"


def _logo_file_path(public_path: str) -> Path:
    return UPLOAD_DIR / Path(public_path).name


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
    today_date = date.today()
    prev_month_end = today_date.replace(day=1) - timedelta(days=1)
    metrics = {
        "total_leads": len(customers),
        "live_customers": sum(1 for c in customers if c.status in {"Live", "Completed"}),
        "pending_customers": sum(1 for c in customers if c.status in {"New", "Negotiation", "Quotation Sent"}),
        "quotations_this_month": sum(1 for q in quotations if q.quotation_date.year == today_date.year and q.quotation_date.month == today_date.month),
        "pending_payments": float(pending),
        "revenue_received": float(received),
        "new_leads_this_month": sum(1 for c in customers if c.created_at.year == today_date.year and c.created_at.month == today_date.month),
        "quotations_last_month": sum(1 for q in quotations if q.quotation_date.year == prev_month_end.year and q.quotation_date.month == prev_month_end.month),
        "pending_invoice_count": sum(1 for i in invoices if Decimal(i.pending_balance or 0) > 0),
        "overdue_invoice_count": sum(1 for i in invoices if Decimal(i.pending_balance or 0) > 0 and i.due_date < today_date),
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


@app.post("/api/customers/import/preview")
async def customers_import_preview(file: UploadFile = File(...), db: Session = Depends(get_db)):
    content = await file.read()
    try:
        return preview_customer_import(db, content)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@app.post("/api/customers/import/commit")
def customers_import_commit(payload: schemas.CustomerImportCommit, db: Session = Depends(get_db)):
    created = commit_customer_import(db, [row.model_dump() for row in payload.rows], payload.as_of)
    return {"created": created}


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


@app.post("/api/business-settings/logo", response_model=schemas.BusinessSettingsRead)
async def upload_business_logo(file: UploadFile = File(...), db: Session = Depends(get_db)):
    allowed = {
        "image/png": ".png",
        "image/jpeg": ".jpg",
        "image/webp": ".webp",
    }
    extension = allowed.get(file.content_type or "")
    if not extension:
        raise HTTPException(400, "Logo must be a PNG, JPG, or WEBP image")
    data = await file.read()
    if not data:
        raise HTTPException(400, "Logo file is empty")
    if len(data) > 2 * 1024 * 1024:
        raise HTTPException(400, "Logo file must be 2 MB or smaller")

    settings = get_or_create_business_settings(db)
    if settings.logo_path:
        old_path = _logo_file_path(settings.logo_path)
        if old_path.exists():
            old_path.unlink()
    filename = f"business-logo{extension}"
    target = UPLOAD_DIR / filename
    target.write_bytes(data)
    settings.logo_path = _logo_public_path(filename)
    db.commit()
    db.refresh(settings)
    return settings


@app.delete("/api/business-settings/logo", response_model=schemas.BusinessSettingsRead)
def remove_business_logo(db: Session = Depends(get_db)):
    settings = get_or_create_business_settings(db)
    if settings.logo_path:
        logo_file = _logo_file_path(settings.logo_path)
        if logo_file.exists():
            logo_file.unlink()
    settings.logo_path = ""
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


@app.post("/api/invoices/{invoice_id}/cancel", response_model=schemas.InvoiceRead)
def cancel_invoice_endpoint(invoice_id: int, force: bool = Query(False), db: Session = Depends(get_db)):
    try:
        return cancel_invoice(db, invoice_id, force=force)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    except Exception as exc:
        raise HTTPException(404, "Invoice not found") from exc


@app.post("/api/invoices/{invoice_id}/reopen", response_model=schemas.InvoiceRead)
def reopen_invoice_endpoint(invoice_id: int, db: Session = Depends(get_db)):
    try:
        return reopen_invoice(db, invoice_id)
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


@app.post("/api/invoices/{invoice_id}/credit-notes", response_model=schemas.CreditNoteRead, status_code=201)
def create_credit_note(invoice_id: int, payload: schemas.CreditNoteCreate, db: Session = Depends(get_db)):
    try:
        return issue_credit_note(db, invoice_id, payload)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    except Exception as exc:
        raise HTTPException(404, "Invoice not found") from exc


@app.get("/api/credit-notes", response_model=list[schemas.CreditNoteRead])
def list_credit_notes(db: Session = Depends(get_db)):
    stmt = select(models.CreditNote).options(selectinload(models.CreditNote.items), joinedload(models.CreditNote.customer), joinedload(models.CreditNote.invoice)).order_by(models.CreditNote.id.desc())
    return db.scalars(stmt).unique().all()


@app.get("/api/credit-notes/{credit_note_id}", response_model=schemas.CreditNoteRead)
def read_credit_note(credit_note_id: int, db: Session = Depends(get_db)):
    try:
        return get_credit_note(db, credit_note_id)
    except Exception as exc:
        raise HTTPException(404, "Credit note not found") from exc


@app.post("/api/credit-notes/{credit_note_id}/cancel", response_model=schemas.CreditNoteRead)
def cancel_credit_note_endpoint(credit_note_id: int, db: Session = Depends(get_db)):
    try:
        return cancel_credit_note(db, credit_note_id)
    except Exception as exc:
        raise HTTPException(404, "Credit note not found") from exc


@app.get("/api/credit-notes/{credit_note_id}/pdf")
def credit_note_pdf(credit_note_id: int, db: Session = Depends(get_db)):
    try:
        credit_note = get_credit_note(db, credit_note_id)
    except Exception as exc:
        raise HTTPException(404, "Credit note not found") from exc
    data = build_credit_note_pdf(credit_note, get_or_create_business_settings(db))
    return StreamingResponse(BytesIO(data), media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="{credit_note.number}.pdf"'})


@app.post("/api/invoices/{invoice_id}/debit-notes", response_model=schemas.DebitNoteRead, status_code=201)
def create_debit_note(invoice_id: int, payload: schemas.DebitNoteCreate, db: Session = Depends(get_db)):
    try:
        return issue_debit_note(db, invoice_id, payload)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    except Exception as exc:
        raise HTTPException(404, "Invoice not found") from exc


@app.get("/api/debit-notes", response_model=list[schemas.DebitNoteRead])
def list_debit_notes(db: Session = Depends(get_db)):
    stmt = select(models.DebitNote).options(selectinload(models.DebitNote.items), joinedload(models.DebitNote.customer), joinedload(models.DebitNote.invoice)).order_by(models.DebitNote.id.desc())
    return db.scalars(stmt).unique().all()


@app.get("/api/debit-notes/{debit_note_id}", response_model=schemas.DebitNoteRead)
def read_debit_note(debit_note_id: int, db: Session = Depends(get_db)):
    try:
        return get_debit_note(db, debit_note_id)
    except Exception as exc:
        raise HTTPException(404, "Debit note not found") from exc


@app.post("/api/debit-notes/{debit_note_id}/cancel", response_model=schemas.DebitNoteRead)
def cancel_debit_note_endpoint(debit_note_id: int, db: Session = Depends(get_db)):
    try:
        return cancel_debit_note(db, debit_note_id)
    except Exception as exc:
        raise HTTPException(404, "Debit note not found") from exc


@app.get("/api/debit-notes/{debit_note_id}/pdf")
def debit_note_pdf(debit_note_id: int, db: Session = Depends(get_db)):
    try:
        debit_note = get_debit_note(db, debit_note_id)
    except Exception as exc:
        raise HTTPException(404, "Debit note not found") from exc
    data = build_debit_note_pdf(debit_note, get_or_create_business_settings(db))
    return StreamingResponse(BytesIO(data), media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="{debit_note.number}.pdf"'})


@app.get("/api/vendors", response_model=list[schemas.VendorRead])
def list_vendors(search: str = "", status: str = "", db: Session = Depends(get_db)):
    stmt = select(models.Vendor).order_by(models.Vendor.id)
    if search:
        q = f"%{search}%"
        stmt = stmt.where(or_(models.Vendor.name.ilike(q), models.Vendor.phone.ilike(q), models.Vendor.email.ilike(q)))
    if status:
        stmt = stmt.where(models.Vendor.status == status)
    return db.scalars(stmt).all()


@app.get("/api/vendors/{vendor_id}", response_model=schemas.VendorRead)
def read_vendor(vendor_id: int, db: Session = Depends(get_db)):
    vendor = db.get(models.Vendor, vendor_id)
    if not vendor:
        raise HTTPException(404, "Vendor not found")
    return vendor


@app.post("/api/vendors", response_model=schemas.VendorRead, status_code=201)
def add_vendor(payload: schemas.VendorCreate, db: Session = Depends(get_db)):
    vendor = models.Vendor(**payload.model_dump(exclude={"code"}), code=payload.code or next_code(db, models.Vendor, "VEND"))
    db.add(vendor)
    db.commit()
    db.refresh(vendor)
    return vendor


@app.put("/api/vendors/{vendor_id}", response_model=schemas.VendorRead)
def update_vendor(vendor_id: int, payload: schemas.VendorCreate, db: Session = Depends(get_db)):
    vendor = db.get(models.Vendor, vendor_id)
    if not vendor:
        raise HTTPException(404, "Vendor not found")
    for key, value in payload.model_dump(exclude={"code"}).items():
        setattr(vendor, key, value)
    if payload.code:
        vendor.code = payload.code
    db.commit()
    db.refresh(vendor)
    return vendor


@app.post("/api/vendors/import/preview")
async def vendors_import_preview(file: UploadFile = File(...), db: Session = Depends(get_db)):
    content = await file.read()
    try:
        return preview_vendor_import(db, content)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@app.post("/api/vendors/import/commit")
def vendors_import_commit(payload: schemas.VendorImportCommit, db: Session = Depends(get_db)):
    created = commit_vendor_import(db, [row.model_dump() for row in payload.rows], payload.as_of)
    return {"created": created}


@app.post("/api/opening-balances/preview")
async def opening_balances_preview(file: UploadFile = File(...), db: Session = Depends(get_db)):
    content = await file.read()
    try:
        return preview_opening_balances(db, content)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@app.post("/api/opening-balances/commit")
def opening_balances_commit(payload: schemas.OpeningBalanceCommit, db: Session = Depends(get_db)):
    try:
        return commit_opening_balances(db, [row.model_dump() for row in payload.rows], payload.as_of)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@app.post("/api/vendors/{vendor_id}/purchase-bills", response_model=schemas.PurchaseBillRead, status_code=201)
def create_purchase_bill_endpoint(vendor_id: int, payload: schemas.PurchaseBillCreate, db: Session = Depends(get_db)):
    try:
        return create_purchase_bill(db, vendor_id, payload)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@app.get("/api/purchase-bills", response_model=list[schemas.PurchaseBillRead])
def list_purchase_bills(db: Session = Depends(get_db)):
    stmt = select(models.PurchaseBill).options(selectinload(models.PurchaseBill.items), selectinload(models.PurchaseBill.payments), joinedload(models.PurchaseBill.vendor)).order_by(models.PurchaseBill.id.desc())
    return db.scalars(stmt).unique().all()


@app.get("/api/purchase-bills/{purchase_bill_id}", response_model=schemas.PurchaseBillRead)
def read_purchase_bill(purchase_bill_id: int, db: Session = Depends(get_db)):
    try:
        return get_purchase_bill(db, purchase_bill_id)
    except Exception as exc:
        raise HTTPException(404, "Purchase bill not found") from exc


@app.post("/api/purchase-bills/{purchase_bill_id}/payments", response_model=schemas.PurchaseBillRead, status_code=201)
def add_vendor_payment(purchase_bill_id: int, payload: schemas.VendorPaymentCreate, db: Session = Depends(get_db)):
    try:
        return record_vendor_payment(db, purchase_bill_id, payload.amount, **payload.model_dump(exclude={"amount"}))
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    except Exception as exc:
        raise HTTPException(404, "Purchase bill not found") from exc


@app.post("/api/purchase-bills/{purchase_bill_id}/cancel", response_model=schemas.PurchaseBillRead)
def cancel_purchase_bill_endpoint(purchase_bill_id: int, force: bool = Query(False), db: Session = Depends(get_db)):
    try:
        return cancel_purchase_bill(db, purchase_bill_id, force=force)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    except Exception as exc:
        raise HTTPException(404, "Purchase bill not found") from exc


@app.post("/api/purchase-bills/{purchase_bill_id}/reopen", response_model=schemas.PurchaseBillRead)
def reopen_purchase_bill_endpoint(purchase_bill_id: int, db: Session = Depends(get_db)):
    try:
        return reopen_purchase_bill(db, purchase_bill_id)
    except Exception as exc:
        raise HTTPException(404, "Purchase bill not found") from exc


@app.get("/api/purchase-bills/{purchase_bill_id}/pdf")
def purchase_bill_pdf(purchase_bill_id: int, db: Session = Depends(get_db)):
    try:
        bill = get_purchase_bill(db, purchase_bill_id)
    except Exception as exc:
        raise HTTPException(404, "Purchase bill not found") from exc
    data = build_purchase_bill_pdf(bill, get_or_create_business_settings(db))
    return StreamingResponse(BytesIO(data), media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="{bill.number}.pdf"'})


@app.get("/api/expenses", response_model=list[schemas.ExpenseRead])
def list_expenses(db: Session = Depends(get_db)):
    stmt = select(models.Expense).options(joinedload(models.Expense.vendor)).order_by(models.Expense.id.desc())
    return db.scalars(stmt).unique().all()


@app.post("/api/expenses", response_model=schemas.ExpenseRead, status_code=201)
def add_expense(payload: schemas.ExpenseCreate, db: Session = Depends(get_db)):
    try:
        return create_expense(db, payload)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@app.put("/api/expenses/{expense_id}", response_model=schemas.ExpenseRead)
def edit_expense(expense_id: int, payload: schemas.ExpenseCreate, db: Session = Depends(get_db)):
    try:
        return update_expense(db, expense_id, payload)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    except Exception as exc:
        raise HTTPException(404, "Expense not found") from exc


@app.delete("/api/expenses/{expense_id}", status_code=204)
def remove_expense(expense_id: int, db: Session = Depends(get_db)):
    try:
        delete_expense(db, expense_id)
    except Exception as exc:
        raise HTTPException(404, "Expense not found") from exc


@app.get("/api/accounts", response_model=list[schemas.ChartOfAccountRead])
def list_accounts(db: Session = Depends(get_db)):
    return list_chart_of_accounts(db)


@app.get("/api/accounts/{account_id}/ledger", response_model=list[schemas.LedgerLineRead])
def account_ledger(account_id: int, db: Session = Depends(get_db)):
    if not db.get(models.ChartOfAccount, account_id):
        raise HTTPException(404, "Account not found")
    return get_account_ledger(db, account_id)


@app.get("/api/journal", response_model=list[schemas.JournalEntryRead])
def list_journal(db: Session = Depends(get_db)):
    return list_journal_entries(db)


@app.post("/api/journal/manual", response_model=schemas.JournalEntryRead, status_code=201)
def create_manual_journal_entry_endpoint(payload: schemas.ManualJournalEntryCreate, db: Session = Depends(get_db)):
    try:
        return create_manual_journal_entry(db, payload.entry_date, payload.narration, [(line.account_id, line.debit, line.credit) for line in payload.lines])
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@app.get("/api/journal/{journal_entry_id}", response_model=schemas.JournalEntryRead)
def read_journal_entry(journal_entry_id: int, db: Session = Depends(get_db)):
    try:
        return get_journal_entry(db, journal_entry_id)
    except Exception as exc:
        raise HTTPException(404, "Journal entry not found") from exc


@app.post("/api/journal/{journal_entry_id}/reverse", response_model=schemas.JournalEntryRead)
def reverse_manual_journal_entry_endpoint(journal_entry_id: int, db: Session = Depends(get_db)):
    try:
        entry = get_journal_entry(db, journal_entry_id)
    except Exception as exc:
        raise HTTPException(404, "Journal entry not found") from exc
    try:
        return reverse_manual_journal_entry(db, entry.id)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@app.get("/api/trial-balance", response_model=list[schemas.TrialBalanceRow])
def trial_balance(db: Session = Depends(get_db)):
    return get_trial_balance(db)


@app.get("/api/fixed-assets", response_model=list[schemas.FixedAssetRead])
def list_fixed_assets_endpoint(db: Session = Depends(get_db)):
    return list_fixed_assets(db)


@app.post("/api/fixed-assets", response_model=schemas.FixedAssetRead, status_code=201)
def create_fixed_asset_endpoint(payload: schemas.FixedAssetCreate, db: Session = Depends(get_db)):
    try:
        return create_fixed_asset(db, payload)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@app.get("/api/fixed-assets/{fixed_asset_id}", response_model=schemas.FixedAssetRead)
def read_fixed_asset(fixed_asset_id: int, db: Session = Depends(get_db)):
    try:
        return get_fixed_asset(db, fixed_asset_id)
    except Exception as exc:
        raise HTTPException(404, "Fixed asset not found") from exc


@app.post("/api/fixed-assets/{fixed_asset_id}/depreciate", response_model=schemas.FixedAssetRead)
def depreciate_fixed_asset_endpoint(fixed_asset_id: int, payload: schemas.DepreciationRunRequest, db: Session = Depends(get_db)):
    try:
        return record_depreciation(db, fixed_asset_id, payload.as_of_date)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@app.post("/api/fixed-assets/{fixed_asset_id}/dispose", response_model=schemas.FixedAssetRead)
def dispose_fixed_asset_endpoint(fixed_asset_id: int, payload: schemas.FixedAssetDisposeRequest, db: Session = Depends(get_db)):
    try:
        return dispose_fixed_asset(db, fixed_asset_id, payload.disposal_date, payload.disposal_value)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


def _csv_response(rows: list[dict], filename: str) -> StreamingResponse:
    buffer = StringIO()
    fieldnames = list(rows[0].keys()) if rows else []
    writer = csv.DictWriter(buffer, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)
    return StreamingResponse(iter([buffer.getvalue()]), media_type="text/csv", headers={"Content-Disposition": f'attachment; filename="{filename}"'})


@app.get("/api/gst/gstr1")
def gstr1(from_date: date = Query(...), to_date: date = Query(...), db: Session = Depends(get_db)):
    return gstr1_report(db, from_date, to_date)


@app.get("/api/gst/gstr1/json")
def gstr1_json(from_date: date = Query(...), to_date: date = Query(...), db: Session = Depends(get_db)):
    payload = gstr1_offline_json(db, from_date, to_date)
    body = json.dumps(payload, indent=2)
    return StreamingResponse(iter([body]), media_type="application/json", headers={"Content-Disposition": f'attachment; filename="gstr1-{from_date}-to-{to_date}.json"'})


@app.get("/api/gst/gstr3b")
def gstr3b(from_date: date = Query(...), to_date: date = Query(...), db: Session = Depends(get_db)):
    return gstr3b_report(db, from_date, to_date)


@app.get("/api/gst/hsn-summary")
def hsn_summary(from_date: date = Query(...), to_date: date = Query(...), db: Session = Depends(get_db)):
    return hsn_summary_report(db, from_date, to_date)


@app.get("/api/gst/hsn-summary/csv")
def hsn_summary_csv(from_date: date = Query(...), to_date: date = Query(...), db: Session = Depends(get_db)):
    return _csv_response(hsn_summary_report(db, from_date, to_date), f"hsn-summary-{from_date}-to-{to_date}.csv")


@app.get("/api/gst/sales-register")
def sales_register_endpoint(from_date: date = Query(...), to_date: date = Query(...), db: Session = Depends(get_db)):
    return sales_register(db, from_date, to_date)


@app.get("/api/gst/sales-register/csv")
def sales_register_csv(from_date: date = Query(...), to_date: date = Query(...), db: Session = Depends(get_db)):
    return _csv_response(sales_register(db, from_date, to_date), f"sales-register-{from_date}-to-{to_date}.csv")


@app.get("/api/gst/purchase-register")
def purchase_register_endpoint(from_date: date = Query(...), to_date: date = Query(...), db: Session = Depends(get_db)):
    return purchase_register(db, from_date, to_date)


@app.get("/api/gst/purchase-register/csv")
def purchase_register_csv(from_date: date = Query(...), to_date: date = Query(...), db: Session = Depends(get_db)):
    return _csv_response(purchase_register(db, from_date, to_date), f"purchase-register-{from_date}-to-{to_date}.csv")


@app.get("/api/profit-and-loss")
def profit_and_loss(from_date: date = Query(...), to_date: date = Query(...), db: Session = Depends(get_db)):
    return profit_and_loss_report(db, from_date, to_date)


@app.get("/api/balance-sheet")
def balance_sheet(as_of: date = Query(...), db: Session = Depends(get_db)):
    return balance_sheet_report(db, as_of)


@app.get("/api/cash-flow")
def cash_flow(from_date: date = Query(...), to_date: date = Query(...), db: Session = Depends(get_db)):
    return cash_flow_statement(db, from_date, to_date)


@app.get("/api/ap-aging")
def ap_aging(as_of: date = Query(...), db: Session = Depends(get_db)):
    return ap_aging_report(db, as_of)


@app.get("/api/financial-years", response_model=list[schemas.FinancialYearRead])
def list_financial_years_endpoint(db: Session = Depends(get_db)):
    return list_financial_years(db)


@app.post("/api/financial-years", response_model=schemas.FinancialYearRead, status_code=201)
def create_financial_year_endpoint(payload: schemas.FinancialYearCreate, db: Session = Depends(get_db)):
    try:
        return create_financial_year(db, payload)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@app.get("/api/financial-years/{financial_year_id}", response_model=schemas.FinancialYearRead)
def read_financial_year(financial_year_id: int, db: Session = Depends(get_db)):
    try:
        return get_financial_year(db, financial_year_id)
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc


@app.post("/api/financial-years/{financial_year_id}/close", response_model=schemas.FinancialYearRead)
def close_financial_year_endpoint(financial_year_id: int, db: Session = Depends(get_db)):
    try:
        fy = get_financial_year(db, financial_year_id)
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc
    pl = profit_and_loss_report(db, fy.start_date, fy.end_date)
    bs = balance_sheet_report(db, fy.end_date)
    try:
        return close_financial_year(
            db, financial_year_id,
            Decimal(str(pl["total_income"])), Decimal(str(pl["total_expense"])), Decimal(str(pl["net_profit"])),
            Decimal(str(bs["total_assets"])), Decimal(str(bs["total_liabilities"])), Decimal(str(bs["total_equity"])),
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@app.post("/api/financial-years/{financial_year_id}/reopen", response_model=schemas.FinancialYearRead)
def reopen_financial_year_endpoint(financial_year_id: int, db: Session = Depends(get_db)):
    try:
        return reopen_financial_year(db, financial_year_id)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@app.get("/api/stock-items", response_model=list[schemas.StockItemRead])
def list_stock_items_endpoint(low_stock: bool = Query(False), db: Session = Depends(get_db)):
    return list_stock_items(db, low_stock)


@app.post("/api/stock-items", response_model=schemas.StockItemRead, status_code=201)
def create_stock_item_endpoint(payload: schemas.StockItemCreate, db: Session = Depends(get_db)):
    try:
        return create_stock_item(db, payload)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@app.get("/api/stock-items/{stock_item_id}", response_model=schemas.StockItemRead)
def read_stock_item(stock_item_id: int, db: Session = Depends(get_db)):
    try:
        return get_stock_item(db, stock_item_id)
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc


@app.put("/api/stock-items/{stock_item_id}", response_model=schemas.StockItemRead)
def update_stock_item_endpoint(stock_item_id: int, payload: schemas.StockItemCreate, db: Session = Depends(get_db)):
    try:
        return update_stock_item(db, stock_item_id, payload)
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc


@app.post("/api/stock-items/{stock_item_id}/movements", response_model=schemas.StockItemRead, status_code=201)
def record_stock_movement_endpoint(stock_item_id: int, payload: schemas.StockMovementCreate, db: Session = Depends(get_db)):
    try:
        return record_stock_movement(db, stock_item_id, payload)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@app.get("/api/tally/export/masters")
def tally_export_masters(db: Session = Depends(get_db)):
    data = build_tally_masters_xml(db)
    return StreamingResponse(BytesIO(data), media_type="application/xml", headers={"Content-Disposition": 'attachment; filename="tally-masters.xml"'})


@app.get("/api/tally/export/vouchers")
def tally_export_vouchers(from_date: date = Query(...), to_date: date = Query(...), db: Session = Depends(get_db)):
    data = build_tally_vouchers_xml(db, from_date, to_date)
    return StreamingResponse(BytesIO(data), media_type="application/xml", headers={"Content-Disposition": f'attachment; filename="tally-vouchers-{from_date}-to-{to_date}.xml"'})


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

if UPLOAD_DIR.exists():
    app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")


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
