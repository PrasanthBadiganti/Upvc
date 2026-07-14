from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(30), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(160), index=True)
    phone: Mapped[str] = mapped_column(String(30), default="")
    email: Mapped[str] = mapped_column(String(160), default="")
    address: Mapped[str] = mapped_column(Text, default="")
    project_site: Mapped[str] = mapped_column(String(200), default="")
    status: Mapped[str] = mapped_column(String(40), default="New", index=True)
    last_interaction: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    next_followup: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    quote_value: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    pending_payment: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    assigned_to: Mapped[str] = mapped_column(String(120), default="Arun Verma")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    quotations: Mapped[list["Quotation"]] = relationship(back_populates="customer", cascade="all, delete-orphan")
    invoices: Mapped[list["Invoice"]] = relationship(back_populates="customer", cascade="all, delete-orphan")
    followups: Mapped[list["Followup"]] = relationship(back_populates="customer", cascade="all, delete-orphan")


class CatalogItem(Base):
    __tablename__ = "catalog_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    category: Mapped[str] = mapped_column(String(100), index=True)
    product_type: Mapped[str] = mapped_column(String(100), default="")
    name: Mapped[str] = mapped_column(String(160), index=True)
    subtitle: Mapped[str] = mapped_column(String(200), default="")
    profile: Mapped[str] = mapped_column(String(120), default="")
    track: Mapped[str] = mapped_column(String(120), default="")
    glass: Mapped[str] = mapped_column(String(120), default="")
    hardware: Mapped[str] = mapped_column(String(120), default="")
    color: Mapped[str] = mapped_column(String(80), default="White")
    min_billable_sft: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=5)
    rate_per_sft: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    status: Mapped[str] = mapped_column(String(30), default="Active")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class PricingRule(Base):
    __tablename__ = "pricing_rules"

    id: Mapped[int] = mapped_column(primary_key=True, default=1)
    within_city_transport: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=1000)
    beyond_city_transport: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=2500)
    minimum_billable_sft: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=5)
    rounding_rule: Mapped[str] = mapped_column(String(50), default="Round up")
    gst_rate: Mapped[Decimal] = mapped_column(Numeric(6, 2), default=18)
    tax_type: Mapped[str] = mapped_column(String(30), default="Exclusive")
    installation_standard: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=120)
    installation_above_200: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=100)
    discount_upto_100: Mapped[Decimal] = mapped_column(Numeric(6, 2), default=2)
    discount_100_300: Mapped[Decimal] = mapped_column(Numeric(6, 2), default=4)
    discount_above_300: Mapped[Decimal] = mapped_column(Numeric(6, 2), default=6)


class Quotation(Base):
    __tablename__ = "quotations"

    id: Mapped[int] = mapped_column(primary_key=True)
    number: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), index=True)
    quotation_date: Mapped[date] = mapped_column(Date, default=date.today)
    validity_days: Mapped[int] = mapped_column(default=30)
    sales_person: Mapped[str] = mapped_column(String(120), default="Arun Verma")
    site_location: Mapped[str] = mapped_column(String(240), default="")
    address: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(40), default="Draft", index=True)
    subtotal: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    transport: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    discount: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    gst: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    grand_total: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    advance: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    balance: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    customer: Mapped[Customer] = relationship(back_populates="quotations")
    items: Mapped[list["QuotationItem"]] = relationship(back_populates="quotation", cascade="all, delete-orphan")
    invoice: Mapped["Invoice | None"] = relationship(back_populates="quotation", uselist=False)


class QuotationItem(Base):
    __tablename__ = "quotation_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    quotation_id: Mapped[int] = mapped_column(ForeignKey("quotations.id"), index=True)
    category: Mapped[str] = mapped_column(String(100))
    style: Mapped[str] = mapped_column(String(160), default="")
    width_mm: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0)
    height_mm: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0)
    sft: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0)
    quantity: Mapped[int] = mapped_column(default=1)
    total_sft: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0)
    rate_per_sft: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    location: Mapped[str] = mapped_column(String(120), default="")
    profile: Mapped[str] = mapped_column(String(120), default="")
    color: Mapped[str] = mapped_column(String(80), default="")
    track: Mapped[str] = mapped_column(String(120), default="")
    glass: Mapped[str] = mapped_column(String(120), default="")
    glass_color: Mapped[str] = mapped_column(String(80), default="")
    hardware: Mapped[str] = mapped_column(String(120), default="")
    reinforcement: Mapped[str] = mapped_column(String(120), default="")
    mesh: Mapped[str] = mapped_column(String(120), default="")

    quotation: Mapped[Quotation] = relationship(back_populates="items")


class Invoice(Base):
    __tablename__ = "invoices"

    id: Mapped[int] = mapped_column(primary_key=True)
    number: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    quotation_id: Mapped[int | None] = mapped_column(ForeignKey("quotations.id"), nullable=True, unique=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), index=True)
    invoice_date: Mapped[date] = mapped_column(Date, default=date.today)
    due_date: Mapped[date] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(40), default="Unpaid", index=True)
    subtotal: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    cgst: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    sgst: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    grand_total: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    paid_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    pending_balance: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    quotation: Mapped[Quotation | None] = relationship(back_populates="invoice")
    customer: Mapped[Customer] = relationship(back_populates="invoices")
    items: Mapped[list["InvoiceItem"]] = relationship(back_populates="invoice", cascade="all, delete-orphan")
    payments: Mapped[list["Payment"]] = relationship(back_populates="invoice", cascade="all, delete-orphan")


class InvoiceItem(Base):
    __tablename__ = "invoice_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    invoice_id: Mapped[int] = mapped_column(ForeignKey("invoices.id"), index=True)
    description: Mapped[str] = mapped_column(String(240))
    category: Mapped[str] = mapped_column(String(100), default="")
    unit: Mapped[str] = mapped_column(String(30), default="Sq. Ft.")
    quantity: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=1)
    rate: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    gst_percent: Mapped[Decimal] = mapped_column(Numeric(6, 2), default=18)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)

    invoice: Mapped[Invoice] = relationship(back_populates="items")


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(primary_key=True)
    invoice_id: Mapped[int] = mapped_column(ForeignKey("invoices.id"), index=True)
    payment_date: Mapped[date] = mapped_column(Date, default=date.today)
    mode: Mapped[str] = mapped_column(String(50), default="NEFT")
    reference_number: Mapped[str] = mapped_column(String(120), default="")
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    received_by: Mapped[str] = mapped_column(String(120), default="Arun Verma")
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    invoice: Mapped[Invoice] = relationship(back_populates="payments")


class Followup(Base):
    __tablename__ = "followups"

    id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), index=True)
    scheduled_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    purpose: Mapped[str] = mapped_column(String(200), default="Payment Reminder")
    assigned_to: Mapped[str] = mapped_column(String(120), default="Arun Verma")
    priority: Mapped[str] = mapped_column(String(30), default="Medium")
    channel: Mapped[str] = mapped_column(String(30), default="Call")
    status: Mapped[str] = mapped_column(String(30), default="Upcoming", index=True)
    next_reminder: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    customer: Mapped[Customer] = relationship(back_populates="followups")
