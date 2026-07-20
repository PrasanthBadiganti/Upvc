from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class CustomerBase(BaseModel):
    name: str
    phone: str = ""
    email: str = ""
    address: str = ""
    gst_number: str = ""
    project_site: str = ""
    status: str = "New"
    last_interaction: datetime | None = None
    next_followup: datetime | None = None
    quote_value: Decimal = Decimal("0")
    pending_payment: Decimal = Decimal("0")
    assigned_to: str = "Arun Verma"
    notes: str = ""


class CustomerCreate(CustomerBase):
    code: str | None = None


class CustomerRead(CustomerBase, ORMModel):
    id: int
    code: str
    created_at: datetime


class CatalogItemBase(BaseModel):
    category: str
    product_type: str = ""
    name: str
    subtitle: str = ""
    profile_brand: str = ""
    profile_series: str = ""
    profile: str = ""
    track: str = ""
    glass_type: str = ""
    glass_thickness: str = ""
    glass_color: str = ""
    glass: str = ""
    hardware: str = ""
    reinforcement: str = ""
    mesh: str = ""
    color: str = "White"
    hsn_code: str = ""
    min_billable_sft: Decimal = Decimal("5")
    rate_per_sft: Decimal = Decimal("0")
    gst_percent: Decimal = Decimal("18")
    installation_rate: Decimal = Decimal("0")
    rounding_rule: str = "Round up"
    status: str = "Active"


class CatalogItemRead(CatalogItemBase, ORMModel):
    id: int
    updated_at: datetime


class PricingRulePayload(BaseModel):
    within_city_transport: Decimal
    beyond_city_transport: Decimal
    minimum_billable_sft: Decimal
    rounding_rule: str
    gst_rate: Decimal
    tax_type: str
    installation_standard: Decimal
    installation_above_200: Decimal
    discount_upto_100: Decimal
    discount_100_300: Decimal
    discount_above_300: Decimal


class PricingRuleRead(PricingRulePayload, ORMModel):
    id: int


class BusinessSettingsPayload(BaseModel):
    company_name: str = "Crystal Frames Studio"
    tagline: str = "Premium UPVC Windows, Doors and Glass Solutions"
    phone: str = "+91 96667 43044"
    email: str = "hello@crystalframes.example"
    address: str = "Vizianagaram, Andhra Pradesh"
    gst_number: str = "37ASLPH7160H1ZI"
    logo_text: str = "CF"
    logo_path: str = ""
    bank_name: str = "Bank of Baroda"
    account_name: str = "Crystal Frames Studio"
    account_number: str = "000000000000"
    ifsc: str = "BARB0VIZIAN"
    upi_id: str = "crystalframes@upi"
    quotation_terms: str = "50% advance with order confirmation. Balance as per approved payment schedule. Final billing is subject to site measurement and approved specifications."
    invoice_terms: str = "Payment due as per agreed schedule. Goods once supplied against approved specifications are not returnable."
    payment_terms: str = "Payment received with thanks. This receipt is valid subject to bank realization."


class BusinessSettingsRead(BusinessSettingsPayload, ORMModel):
    id: int
    updated_at: datetime


class QuotationItemPayload(BaseModel):
    catalog_item_id: int | None = None
    category: str
    style: str = ""
    width_mm: Decimal = Decimal("0")
    height_mm: Decimal = Decimal("0")
    sft: Decimal = Decimal("0")
    quantity: int = 1
    total_sft: Decimal = Decimal("0")
    rate_per_sft: Decimal = Decimal("0")
    amount: Decimal = Decimal("0")
    hsn_code: str = ""
    location: str = ""
    profile: str = ""
    color: str = ""
    track: str = ""
    glass: str = ""
    glass_color: str = ""
    hardware: str = ""
    reinforcement: str = ""
    mesh: str = ""


class QuotationItemRead(QuotationItemPayload, ORMModel):
    id: int


class QuotationCreate(BaseModel):
    customer_id: int
    quotation_date: date = Field(default_factory=date.today)
    validity_days: int = 30
    sales_person: str = "Arun Verma"
    site_location: str = ""
    address: str = ""
    status: str = "Draft"
    transport: Decimal = Decimal("0")
    discount: Decimal = Decimal("0")
    notes: str = ""
    items: list[QuotationItemPayload]


class QuotationUpdate(QuotationCreate):
    pass


class QuotationRead(ORMModel):
    id: int
    number: str
    customer_id: int
    quotation_date: date
    validity_days: int
    sales_person: str
    site_location: str
    address: str
    status: str
    subtotal: Decimal
    transport: Decimal
    discount: Decimal
    gst: Decimal
    grand_total: Decimal
    advance: Decimal
    balance: Decimal
    notes: str
    created_at: datetime
    items: list[QuotationItemRead]
    customer: CustomerRead


class InvoiceItemRead(ORMModel):
    id: int
    description: str
    category: str
    unit: str
    quantity: Decimal
    rate: Decimal
    gst_percent: Decimal
    amount: Decimal
    hsn_code: str


class PaymentCreate(BaseModel):
    payment_date: date = Field(default_factory=date.today)
    mode: str = "NEFT"
    reference_number: str = ""
    amount: Decimal
    received_by: str = "Arun Verma"
    notes: str = ""


class PaymentRead(PaymentCreate, ORMModel):
    id: int
    invoice_id: int
    created_at: datetime


class InvoiceRead(ORMModel):
    id: int
    number: str
    quotation_id: int | None
    customer_id: int
    invoice_date: date
    due_date: date
    status: str
    subtotal: Decimal
    cgst: Decimal
    sgst: Decimal
    grand_total: Decimal
    paid_amount: Decimal
    pending_balance: Decimal
    created_at: datetime
    items: list[InvoiceItemRead]
    payments: list[PaymentRead]
    customer: CustomerRead
    quotation: QuotationRead | None = None


class InvoiceSummaryRead(ORMModel):
    id: int
    number: str
    invoice_date: date
    grand_total: Decimal
    pending_balance: Decimal


class CreditNoteItemPayload(BaseModel):
    description: str
    category: str = ""
    hsn_code: str = ""
    unit: str = "Sq. Ft."
    quantity: Decimal = Decimal("1")
    rate: Decimal = Decimal("0")
    gst_percent: Decimal = Decimal("18")
    amount: Decimal = Decimal("0")


class CreditNoteItemRead(CreditNoteItemPayload, ORMModel):
    id: int


class CreditNoteCreate(BaseModel):
    note_date: date = Field(default_factory=date.today)
    reason: str = ""
    items: list[CreditNoteItemPayload]


class CreditNoteRead(ORMModel):
    id: int
    number: str
    invoice_id: int
    customer_id: int
    note_date: date
    reason: str
    status: str
    subtotal: Decimal
    gst: Decimal
    grand_total: Decimal
    created_at: datetime
    items: list[CreditNoteItemRead]
    invoice: InvoiceSummaryRead
    customer: CustomerRead


class DebitNoteItemPayload(BaseModel):
    description: str
    category: str = ""
    hsn_code: str = ""
    unit: str = "Sq. Ft."
    quantity: Decimal = Decimal("1")
    rate: Decimal = Decimal("0")
    gst_percent: Decimal = Decimal("18")
    amount: Decimal = Decimal("0")


class DebitNoteItemRead(DebitNoteItemPayload, ORMModel):
    id: int


class DebitNoteCreate(BaseModel):
    note_date: date = Field(default_factory=date.today)
    reason: str = ""
    items: list[DebitNoteItemPayload]


class DebitNoteRead(ORMModel):
    id: int
    number: str
    invoice_id: int
    customer_id: int
    note_date: date
    reason: str
    status: str
    subtotal: Decimal
    gst: Decimal
    grand_total: Decimal
    created_at: datetime
    items: list[DebitNoteItemRead]
    invoice: InvoiceSummaryRead
    customer: CustomerRead


class VendorBase(BaseModel):
    name: str
    phone: str = ""
    email: str = ""
    address: str = ""
    gst_number: str = ""
    status: str = "Active"
    pending_payment: Decimal = Decimal("0")
    notes: str = ""


class VendorCreate(VendorBase):
    code: str | None = None


class VendorRead(VendorBase, ORMModel):
    id: int
    code: str
    created_at: datetime


class VendorSummaryRead(ORMModel):
    id: int
    code: str
    name: str
    phone: str
    gst_number: str


class PurchaseBillItemPayload(BaseModel):
    description: str
    category: str = ""
    hsn_code: str = ""
    unit: str = "Nos"
    quantity: Decimal = Decimal("1")
    rate: Decimal = Decimal("0")
    gst_percent: Decimal = Decimal("18")
    amount: Decimal = Decimal("0")


class PurchaseBillItemRead(PurchaseBillItemPayload, ORMModel):
    id: int


class PurchaseBillCreate(BaseModel):
    vendor_bill_number: str = ""
    bill_date: date = Field(default_factory=date.today)
    due_date: date
    notes: str = ""
    items: list[PurchaseBillItemPayload]


class VendorPaymentCreate(BaseModel):
    payment_date: date = Field(default_factory=date.today)
    mode: str = "NEFT"
    reference_number: str = ""
    amount: Decimal
    paid_by: str = "Arun Verma"
    notes: str = ""


class VendorPaymentRead(VendorPaymentCreate, ORMModel):
    id: int
    purchase_bill_id: int
    created_at: datetime


class PurchaseBillRead(ORMModel):
    id: int
    number: str
    vendor_id: int
    vendor_bill_number: str
    bill_date: date
    due_date: date
    status: str
    subtotal: Decimal
    cgst: Decimal
    sgst: Decimal
    grand_total: Decimal
    paid_amount: Decimal
    pending_balance: Decimal
    notes: str
    created_at: datetime
    items: list[PurchaseBillItemRead]
    payments: list[VendorPaymentRead]
    vendor: VendorSummaryRead


class ExpenseCreate(BaseModel):
    expense_date: date = Field(default_factory=date.today)
    category: str = "Other"
    description: str = ""
    amount: Decimal
    gst_percent: Decimal = Decimal("0")
    vendor_id: int | None = None
    mode: str = "Cash"
    reference_number: str = ""
    notes: str = ""


class ExpenseRead(ExpenseCreate, ORMModel):
    id: int
    gst_amount: Decimal
    total: Decimal
    created_at: datetime
    vendor: VendorSummaryRead | None = None


class ChartOfAccountRead(ORMModel):
    id: int
    code: str
    name: str
    account_type: str
    account_group: str
    status: str


class JournalLineRead(ORMModel):
    id: int
    account_id: int
    debit: Decimal
    credit: Decimal
    account: ChartOfAccountRead


class JournalEntryRead(ORMModel):
    id: int
    number: str
    entry_date: date
    narration: str
    source_type: str
    source_id: int | None
    created_at: datetime
    lines: list[JournalLineRead]


class TrialBalanceRow(BaseModel):
    account_id: int
    code: str
    name: str
    account_type: str
    debit: Decimal
    credit: Decimal
    balance: Decimal


class JournalEntrySummaryRead(ORMModel):
    id: int
    number: str
    entry_date: date
    narration: str
    source_type: str
    source_id: int | None


class LedgerLineRead(ORMModel):
    id: int
    debit: Decimal
    credit: Decimal
    entry: JournalEntrySummaryRead


class FollowupCreate(BaseModel):
    customer_id: int
    scheduled_at: datetime
    purpose: str = "Payment Reminder"
    assigned_to: str = "Arun Verma"
    priority: str = "Medium"
    channel: str = "Call"
    status: str = "Upcoming"
    next_reminder: datetime | None = None
    notes: str = ""


class FollowupRead(FollowupCreate, ORMModel):
    id: int
    created_at: datetime
    customer: CustomerRead


class CustomerQuotationSummary(ORMModel):
    id: int
    number: str
    quotation_date: date
    status: str
    grand_total: Decimal
    balance: Decimal
    created_at: datetime


class CustomerInvoiceSummary(ORMModel):
    id: int
    number: str
    invoice_date: date
    due_date: date
    status: str
    grand_total: Decimal
    paid_amount: Decimal
    pending_balance: Decimal
    created_at: datetime


class CustomerPaymentSummary(ORMModel):
    id: int
    invoice_id: int
    payment_date: date
    mode: str
    reference_number: str
    amount: Decimal
    received_by: str
    notes: str
    created_at: datetime
    invoice_number: str


class CustomerTimelineItem(BaseModel):
    type: str
    title: str
    detail: str
    at: datetime


class CustomerProfileResponse(BaseModel):
    customer: CustomerRead
    metrics: dict[str, Any]
    quotations: list[CustomerQuotationSummary]
    invoices: list[CustomerInvoiceSummary]
    payments: list[CustomerPaymentSummary]
    followups: list[FollowupRead]
    timeline: list[CustomerTimelineItem]


class DashboardResponse(BaseModel):
    metrics: dict[str, Any]
    monthly: list[dict[str, Any]]
    customer_status: list[dict[str, Any]]
    pending_payments: list[dict[str, Any]]
    today_followups: list[dict[str, Any]]
    recent_activity: list[dict[str, Any]]
