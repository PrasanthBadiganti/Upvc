from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String, Text, Table, Column, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


# RBAC Models
class Role(Base):
    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, index=True)  # SuperAdmin, Admin, Manager, DataEntry
    description: Mapped[str] = mapped_column(String(200), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    users: Mapped[list["User"]] = relationship(back_populates="role")
    permissions: Mapped[list["Permission"]] = relationship(back_populates="role", cascade="all, delete-orphan")


class Permission(Base):
    __tablename__ = "permissions"

    id: Mapped[int] = mapped_column(primary_key=True)
    role_id: Mapped[int] = mapped_column(ForeignKey("roles.id"), index=True)
    resource: Mapped[str] = mapped_column(String(50))  # customer, quotation, invoice, etc
    create: Mapped[bool] = mapped_column(Boolean, default=False)
    read: Mapped[bool] = mapped_column(Boolean, default=False)
    update: Mapped[bool] = mapped_column(Boolean, default=False)
    delete: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    role: Mapped["Role"] = relationship(back_populates="permissions")


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str] = mapped_column(String(100), default="")
    role_id: Mapped[int] = mapped_column(ForeignKey("roles.id"), index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    role: Mapped["Role"] = relationship(back_populates="users")


class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(30), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(160), index=True)
    phone: Mapped[str] = mapped_column(String(30), default="")
    email: Mapped[str] = mapped_column(String(160), default="")
    address: Mapped[str] = mapped_column(Text, default="")
    gst_number: Mapped[str] = mapped_column(String(40), default="")
    state: Mapped[str] = mapped_column(String(60), default="")
    project_site: Mapped[str] = mapped_column(String(200), default="")
    status: Mapped[str] = mapped_column(String(40), default="New", index=True)
    last_interaction: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    next_followup: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    quote_value: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    pending_payment: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    assigned_to: Mapped[str] = mapped_column(String(120), default="Arun Verma")
    notes: Mapped[str] = mapped_column(Text, default="")
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
    profile_brand: Mapped[str] = mapped_column(String(120), default="")
    profile_series: Mapped[str] = mapped_column(String(120), default="")
    profile: Mapped[str] = mapped_column(String(120), default="")
    track: Mapped[str] = mapped_column(String(120), default="")
    glass_type: Mapped[str] = mapped_column(String(120), default="")
    glass_thickness: Mapped[str] = mapped_column(String(60), default="")
    glass_color: Mapped[str] = mapped_column(String(80), default="")
    glass: Mapped[str] = mapped_column(String(120), default="")
    hardware: Mapped[str] = mapped_column(String(120), default="")
    reinforcement: Mapped[str] = mapped_column(String(120), default="")
    mesh: Mapped[str] = mapped_column(String(120), default="")
    color: Mapped[str] = mapped_column(String(80), default="White")
    hsn_code: Mapped[str] = mapped_column(String(20), default="")
    min_billable_sft: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=5)
    rate_per_sft: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    gst_percent: Mapped[Decimal] = mapped_column(Numeric(6, 2), default=18)
    installation_rate: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    rounding_rule: Mapped[str] = mapped_column(String(50), default="Round up")
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


class RateCard(Base):
    __tablename__ = "rate_cards"

    id: Mapped[int] = mapped_column(primary_key=True)
    catalog_item_id: Mapped[int] = mapped_column(ForeignKey("catalog_items.id"), index=True)
    min_sft: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0)
    max_sft: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=100)
    rate_per_sft: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    discount_percent: Mapped[Decimal] = mapped_column(Numeric(6, 2), default=0)
    status: Mapped[str] = mapped_column(String(30), default="Active")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class BankAccount(Base):
    __tablename__ = "bank_accounts"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(160), index=True)
    bank_name: Mapped[str] = mapped_column(String(160), default="")
    account_number: Mapped[str] = mapped_column(String(80), default="")
    ifsc: Mapped[str] = mapped_column(String(40), default="")
    account_type: Mapped[str] = mapped_column(String(40), default="Current")
    status: Mapped[str] = mapped_column(String(30), default="Active", index=True)
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class BusinessSettings(Base):
    __tablename__ = "business_settings"

    id: Mapped[int] = mapped_column(primary_key=True, default=1)
    company_name: Mapped[str] = mapped_column(String(180), default="Crystal Frames Studio")
    tagline: Mapped[str] = mapped_column(String(220), default="Premium UPVC Windows, Doors and Glass Solutions")
    phone: Mapped[str] = mapped_column(String(60), default="+91 96667 43044")
    email: Mapped[str] = mapped_column(String(160), default="hello@crystalframes.example")
    address: Mapped[str] = mapped_column(Text, default="Vizianagaram, Andhra Pradesh")
    gst_number: Mapped[str] = mapped_column(String(40), default="37ASLPH7160H1ZI")
    state: Mapped[str] = mapped_column(String(60), default="Andhra Pradesh")
    logo_text: Mapped[str] = mapped_column(String(12), default="CF")
    logo_path: Mapped[str] = mapped_column(String(260), default="")
    bank_name: Mapped[str] = mapped_column(String(160), default="Bank of Baroda")
    account_name: Mapped[str] = mapped_column(String(180), default="Crystal Frames Studio")
    account_number: Mapped[str] = mapped_column(String(80), default="000000000000")
    ifsc: Mapped[str] = mapped_column(String(40), default="BARB0VIZIAN")
    upi_id: Mapped[str] = mapped_column(String(120), default="crystalframes@upi")
    quotation_terms: Mapped[str] = mapped_column(Text, default="50% advance with order confirmation. Balance as per approved payment schedule. Final billing is subject to site measurement and approved specifications.")
    invoice_terms: Mapped[str] = mapped_column(Text, default="Payment due as per agreed schedule. Goods once supplied against approved specifications are not returnable.")
    payment_terms: Mapped[str] = mapped_column(Text, default="Payment received with thanks. This receipt is valid subject to bank realization.")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


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
    catalog_item_id: Mapped[int | None] = mapped_column(ForeignKey("catalog_items.id"), nullable=True, index=True)
    category: Mapped[str] = mapped_column(String(100))
    style: Mapped[str] = mapped_column(String(160), default="")
    width_mm: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0)
    height_mm: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0)
    sft: Mapped[Decimal] = mapped_column(Numeric(10, 0), default=0)
    quantity: Mapped[int] = mapped_column(default=1)
    total_sft: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0)
    rate_per_sft: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    hsn_code: Mapped[str] = mapped_column(String(20), default="")
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
    transport: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    discount: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    cgst: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    sgst: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    igst: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
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
    hsn_code: Mapped[str] = mapped_column(String(20), default="")

    invoice: Mapped[Invoice] = relationship(back_populates="items")


class CreditNote(Base):
    __tablename__ = "credit_notes"

    id: Mapped[int] = mapped_column(primary_key=True)
    number: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    invoice_id: Mapped[int] = mapped_column(ForeignKey("invoices.id"), index=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), index=True)
    note_date: Mapped[date] = mapped_column(Date, default=date.today)
    reason: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(30), default="Issued", index=True)
    subtotal: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    gst: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    grand_total: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    invoice: Mapped[Invoice] = relationship()
    customer: Mapped[Customer] = relationship()
    items: Mapped[list["CreditNoteItem"]] = relationship(back_populates="credit_note", cascade="all, delete-orphan")


class CreditNoteItem(Base):
    __tablename__ = "credit_note_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    credit_note_id: Mapped[int] = mapped_column(ForeignKey("credit_notes.id"), index=True)
    description: Mapped[str] = mapped_column(String(240))
    category: Mapped[str] = mapped_column(String(100), default="")
    hsn_code: Mapped[str] = mapped_column(String(20), default="")
    unit: Mapped[str] = mapped_column(String(30), default="Sq. Ft.")
    quantity: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=1)
    rate: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    gst_percent: Mapped[Decimal] = mapped_column(Numeric(6, 2), default=18)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)

    credit_note: Mapped[CreditNote] = relationship(back_populates="items")


class DebitNote(Base):
    __tablename__ = "debit_notes"

    id: Mapped[int] = mapped_column(primary_key=True)
    number: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    invoice_id: Mapped[int] = mapped_column(ForeignKey("invoices.id"), index=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), index=True)
    note_date: Mapped[date] = mapped_column(Date, default=date.today)
    reason: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(30), default="Issued", index=True)
    subtotal: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    gst: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    grand_total: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    invoice: Mapped[Invoice] = relationship()
    customer: Mapped[Customer] = relationship()
    items: Mapped[list["DebitNoteItem"]] = relationship(back_populates="debit_note", cascade="all, delete-orphan")


class DebitNoteItem(Base):
    __tablename__ = "debit_note_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    debit_note_id: Mapped[int] = mapped_column(ForeignKey("debit_notes.id"), index=True)
    description: Mapped[str] = mapped_column(String(240))
    category: Mapped[str] = mapped_column(String(100), default="")
    hsn_code: Mapped[str] = mapped_column(String(20), default="")
    unit: Mapped[str] = mapped_column(String(30), default="Sq. Ft.")
    quantity: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=1)
    rate: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    gst_percent: Mapped[Decimal] = mapped_column(Numeric(6, 2), default=18)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)

    debit_note: Mapped[DebitNote] = relationship(back_populates="items")


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
    bank_account_id: Mapped[int | None] = mapped_column(ForeignKey("bank_accounts.id"), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    invoice: Mapped[Invoice] = relationship(back_populates="payments")
    bank_account: Mapped["BankAccount | None"] = relationship()


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


class Vendor(Base):
    __tablename__ = "vendors"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(30), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(160), index=True)
    phone: Mapped[str] = mapped_column(String(30), default="")
    email: Mapped[str] = mapped_column(String(160), default="")
    address: Mapped[str] = mapped_column(Text, default="")
    gst_number: Mapped[str] = mapped_column(String(40), default="")
    state: Mapped[str] = mapped_column(String(60), default="")
    status: Mapped[str] = mapped_column(String(40), default="Active", index=True)
    pending_payment: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    purchase_bills: Mapped[list["PurchaseBill"]] = relationship(back_populates="vendor", cascade="all, delete-orphan")
    expenses: Mapped[list["Expense"]] = relationship(back_populates="vendor")


class PurchaseBill(Base):
    __tablename__ = "purchase_bills"

    id: Mapped[int] = mapped_column(primary_key=True)
    number: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    vendor_id: Mapped[int] = mapped_column(ForeignKey("vendors.id"), index=True)
    vendor_bill_number: Mapped[str] = mapped_column(String(60), default="")
    bill_date: Mapped[date] = mapped_column(Date, default=date.today)
    due_date: Mapped[date] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(40), default="Unpaid", index=True)
    subtotal: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    cgst: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    sgst: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    igst: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    grand_total: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    paid_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    pending_balance: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    vendor: Mapped[Vendor] = relationship(back_populates="purchase_bills")
    items: Mapped[list["PurchaseBillItem"]] = relationship(back_populates="purchase_bill", cascade="all, delete-orphan")
    payments: Mapped[list["VendorPayment"]] = relationship(back_populates="purchase_bill", cascade="all, delete-orphan")


class PurchaseBillItem(Base):
    __tablename__ = "purchase_bill_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    purchase_bill_id: Mapped[int] = mapped_column(ForeignKey("purchase_bills.id"), index=True)
    description: Mapped[str] = mapped_column(String(240))
    category: Mapped[str] = mapped_column(String(100), default="")
    hsn_code: Mapped[str] = mapped_column(String(20), default="")
    unit: Mapped[str] = mapped_column(String(30), default="Nos")
    quantity: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=1)
    rate: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    gst_percent: Mapped[Decimal] = mapped_column(Numeric(6, 2), default=18)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    stock_item_id: Mapped[int | None] = mapped_column(ForeignKey("stock_items.id"), nullable=True, index=True)

    purchase_bill: Mapped[PurchaseBill] = relationship(back_populates="items")


class VendorPayment(Base):
    __tablename__ = "vendor_payments"

    id: Mapped[int] = mapped_column(primary_key=True)
    purchase_bill_id: Mapped[int] = mapped_column(ForeignKey("purchase_bills.id"), index=True)
    payment_date: Mapped[date] = mapped_column(Date, default=date.today)
    mode: Mapped[str] = mapped_column(String(50), default="NEFT")
    reference_number: Mapped[str] = mapped_column(String(120), default="")
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    paid_by: Mapped[str] = mapped_column(String(120), default="Arun Verma")
    notes: Mapped[str] = mapped_column(Text, default="")
    bank_account_id: Mapped[int | None] = mapped_column(ForeignKey("bank_accounts.id"), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    purchase_bill: Mapped[PurchaseBill] = relationship(back_populates="payments")
    bank_account: Mapped["BankAccount | None"] = relationship()


class Expense(Base):
    __tablename__ = "expenses"

    id: Mapped[int] = mapped_column(primary_key=True)
    expense_date: Mapped[date] = mapped_column(Date, default=date.today)
    category: Mapped[str] = mapped_column(String(60), default="Other")
    description: Mapped[str] = mapped_column(String(240), default="")
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    gst_percent: Mapped[Decimal] = mapped_column(Numeric(6, 2), default=0)
    gst_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    total: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    vendor_id: Mapped[int | None] = mapped_column(ForeignKey("vendors.id"), nullable=True, index=True)
    mode: Mapped[str] = mapped_column(String(50), default="Cash")
    reference_number: Mapped[str] = mapped_column(String(120), default="")
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    vendor: Mapped[Vendor | None] = relationship(back_populates="expenses")


class ChartOfAccount(Base):
    __tablename__ = "chart_of_accounts"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(160))
    account_type: Mapped[str] = mapped_column(String(30), index=True)
    account_group: Mapped[str] = mapped_column(String(80), default="")
    status: Mapped[str] = mapped_column(String(30), default="Active")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class JournalEntry(Base):
    __tablename__ = "journal_entries"

    id: Mapped[int] = mapped_column(primary_key=True)
    number: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    entry_date: Mapped[date] = mapped_column(Date, default=date.today, index=True)
    narration: Mapped[str] = mapped_column(String(240), default="")
    source_type: Mapped[str] = mapped_column(String(40), index=True)
    source_id: Mapped[int | None] = mapped_column(nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    lines: Mapped[list["JournalLine"]] = relationship(back_populates="entry", cascade="all, delete-orphan")


class JournalLine(Base):
    __tablename__ = "journal_lines"

    id: Mapped[int] = mapped_column(primary_key=True)
    journal_entry_id: Mapped[int] = mapped_column(ForeignKey("journal_entries.id"), index=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("chart_of_accounts.id"), index=True)
    debit: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    credit: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)

    entry: Mapped[JournalEntry] = relationship(back_populates="lines")
    account: Mapped[ChartOfAccount] = relationship()


class FixedAsset(Base):
    __tablename__ = "fixed_assets"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(30), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(160))
    category: Mapped[str] = mapped_column(String(60), default="Other")
    purchase_date: Mapped[date] = mapped_column(Date, default=date.today)
    purchase_cost: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    salvage_value: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    useful_life_years: Mapped[Decimal] = mapped_column(Numeric(6, 2), default=1)
    depreciation_method: Mapped[str] = mapped_column(String(30), default="Straight Line")
    depreciation_rate: Mapped[Decimal | None] = mapped_column(Numeric(6, 2), nullable=True)
    vendor_id: Mapped[int | None] = mapped_column(ForeignKey("vendors.id"), nullable=True, index=True)
    location: Mapped[str] = mapped_column(String(160), default="")
    notes: Mapped[str] = mapped_column(Text, default="")
    accumulated_depreciation: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    last_depreciation_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="Active", index=True)
    disposal_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    disposal_value: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    vendor: Mapped[Vendor | None] = relationship()
    depreciation_entries: Mapped[list["DepreciationEntry"]] = relationship(back_populates="fixed_asset", cascade="all, delete-orphan", order_by="DepreciationEntry.period_end")


class DepreciationEntry(Base):
    __tablename__ = "depreciation_entries"

    id: Mapped[int] = mapped_column(primary_key=True)
    fixed_asset_id: Mapped[int] = mapped_column(ForeignKey("fixed_assets.id"), index=True)
    period_start: Mapped[date] = mapped_column(Date)
    period_end: Mapped[date] = mapped_column(Date)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    book_value_after: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    fixed_asset: Mapped[FixedAsset] = relationship(back_populates="depreciation_entries")


class FinancialYear(Base):
    __tablename__ = "financial_years"

    id: Mapped[int] = mapped_column(primary_key=True)
    label: Mapped[str] = mapped_column(String(30), unique=True, index=True)
    start_date: Mapped[date] = mapped_column(Date, index=True)
    end_date: Mapped[date] = mapped_column(Date, index=True)
    status: Mapped[str] = mapped_column(String(20), default="Open", index=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    total_income: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    total_expense: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    net_profit: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    total_assets: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    total_liabilities: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    total_equity: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class StockItem(Base):
    __tablename__ = "stock_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(30), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(160), index=True)
    category: Mapped[str] = mapped_column(String(60), default="Other")
    unit: Mapped[str] = mapped_column(String(20), default="Nos")
    hsn_code: Mapped[str] = mapped_column(String(20), default="")
    reorder_level: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    quantity_on_hand: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    notes: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(30), default="Active", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    movements: Mapped[list["StockMovement"]] = relationship(back_populates="stock_item", cascade="all, delete-orphan", order_by="StockMovement.id")


class StockMovement(Base):
    __tablename__ = "stock_movements"

    id: Mapped[int] = mapped_column(primary_key=True)
    stock_item_id: Mapped[int] = mapped_column(ForeignKey("stock_items.id"), index=True)
    movement_date: Mapped[date] = mapped_column(Date, default=date.today, index=True)
    movement_type: Mapped[str] = mapped_column(String(20), index=True)
    reason: Mapped[str] = mapped_column(String(60), default="Manual")
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    balance_after: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    reference: Mapped[str] = mapped_column(String(160), default="")
    source_type: Mapped[str] = mapped_column(String(40), default="Manual")
    source_id: Mapped[int | None] = mapped_column(nullable=True, index=True)
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    stock_item: Mapped[StockItem] = relationship(back_populates="movements")
