export type Customer = {
  id: number;
  code: string;
  name: string;
  phone: string;
  email: string;
  address: string;
  gst_number: string;
  project_site: string;
  status: string;
  last_interaction?: string | null;
  next_followup?: string | null;
  quote_value: number | string;
  pending_payment: number | string;
  assigned_to: string;
  notes: string;
  created_at: string;
};

export type CatalogItem = {
  id: number;
  category: string;
  product_type: string;
  name: string;
  subtitle: string;
  profile_brand: string;
  profile_series: string;
  profile: string;
  track: string;
  glass_type: string;
  glass_thickness: string;
  glass_color: string;
  glass: string;
  hardware: string;
  reinforcement: string;
  mesh: string;
  color: string;
  hsn_code: string;
  min_billable_sft: number | string;
  rate_per_sft: number | string;
  gst_percent: number | string;
  installation_rate: number | string;
  rounding_rule: string;
  status: string;
  updated_at: string;
};

export type QuotationItem = {
  id?: number;
  catalog_item_id?: number | null;
  category: string;
  style: string;
  width_mm: number;
  height_mm: number;
  sft: number;
  quantity: number;
  total_sft: number;
  rate_per_sft: number;
  amount: number;
  hsn_code?: string;
  location: string;
  profile?: string;
  color?: string;
  track?: string;
  glass?: string;
  glass_color?: string;
  hardware?: string;
  reinforcement?: string;
  mesh?: string;
};

export type Quotation = {
  id: number;
  number: string;
  customer_id: number;
  quotation_date: string;
  validity_days: number;
  sales_person: string;
  site_location: string;
  address: string;
  status: string;
  subtotal: number | string;
  transport: number | string;
  discount: number | string;
  gst: number | string;
  grand_total: number | string;
  advance: number | string;
  balance: number | string;
  notes: string;
  created_at: string;
  items: QuotationItem[];
  customer: Customer;
};

export type InvoiceItem = {
  id: number;
  description: string;
  category: string;
  unit: string;
  quantity: number | string;
  rate: number | string;
  gst_percent: number | string;
  amount: number | string;
  hsn_code: string;
};

export type Payment = {
  id: number;
  invoice_id: number;
  payment_date: string;
  mode: string;
  reference_number: string;
  amount: number | string;
  received_by: string;
  notes: string;
  created_at: string;
};

export type Invoice = {
  id: number;
  number: string;
  quotation_id?: number | null;
  customer_id: number;
  invoice_date: string;
  due_date: string;
  status: string;
  subtotal: number | string;
  cgst: number | string;
  sgst: number | string;
  grand_total: number | string;
  paid_amount: number | string;
  pending_balance: number | string;
  created_at: string;
  items: InvoiceItem[];
  payments: Payment[];
  customer: Customer;
  quotation?: Quotation | null;
};

export type InvoiceSummary = {
  id: number;
  number: string;
  invoice_date: string;
  grand_total: number | string;
  pending_balance: number | string;
};

export type NoteItem = {
  id?: number;
  description: string;
  category: string;
  hsn_code: string;
  unit: string;
  quantity: number | string;
  rate: number | string;
  gst_percent: number | string;
  amount: number | string;
};

export type CreditNote = {
  id: number;
  number: string;
  invoice_id: number;
  customer_id: number;
  note_date: string;
  reason: string;
  status: string;
  subtotal: number | string;
  gst: number | string;
  grand_total: number | string;
  created_at: string;
  items: NoteItem[];
  invoice: InvoiceSummary;
  customer: Customer;
};

export type DebitNote = {
  id: number;
  number: string;
  invoice_id: number;
  customer_id: number;
  note_date: string;
  reason: string;
  status: string;
  subtotal: number | string;
  gst: number | string;
  grand_total: number | string;
  created_at: string;
  items: NoteItem[];
  invoice: InvoiceSummary;
  customer: Customer;
};

export type Vendor = {
  id: number;
  code: string;
  name: string;
  phone: string;
  email: string;
  address: string;
  gst_number: string;
  status: string;
  pending_payment: number | string;
  notes: string;
  created_at: string;
};

export type VendorSummary = {
  id: number;
  code: string;
  name: string;
  phone: string;
  gst_number: string;
};

export type PurchaseBillItem = {
  id?: number;
  description: string;
  category: string;
  hsn_code: string;
  unit: string;
  quantity: number | string;
  rate: number | string;
  gst_percent: number | string;
  amount: number | string;
};

export type VendorPayment = {
  id: number;
  purchase_bill_id: number;
  payment_date: string;
  mode: string;
  reference_number: string;
  amount: number | string;
  paid_by: string;
  notes: string;
  created_at: string;
};

export type PurchaseBill = {
  id: number;
  number: string;
  vendor_id: number;
  vendor_bill_number: string;
  bill_date: string;
  due_date: string;
  status: string;
  subtotal: number | string;
  cgst: number | string;
  sgst: number | string;
  grand_total: number | string;
  paid_amount: number | string;
  pending_balance: number | string;
  notes: string;
  created_at: string;
  items: PurchaseBillItem[];
  payments: VendorPayment[];
  vendor: VendorSummary;
};

export type Expense = {
  id: number;
  expense_date: string;
  category: string;
  description: string;
  amount: number | string;
  gst_percent: number | string;
  gst_amount: number | string;
  total: number | string;
  vendor_id?: number | null;
  mode: string;
  reference_number: string;
  notes: string;
  created_at: string;
  vendor?: VendorSummary | null;
};

export type ChartOfAccount = {
  id: number;
  code: string;
  name: string;
  account_type: string;
  account_group: string;
  status: string;
};

export type JournalLine = {
  id: number;
  account_id: number;
  debit: number | string;
  credit: number | string;
  account: ChartOfAccount;
};

export type JournalEntry = {
  id: number;
  number: string;
  entry_date: string;
  narration: string;
  source_type: string;
  source_id: number | null;
  created_at: string;
  lines: JournalLine[];
};

export type TrialBalanceRow = {
  account_id: number;
  code: string;
  name: string;
  account_type: string;
  debit: number | string;
  credit: number | string;
  balance: number | string;
};

export type LedgerLine = {
  id: number;
  debit: number | string;
  credit: number | string;
  entry: {
    id: number;
    number: string;
    entry_date: string;
    narration: string;
    source_type: string;
    source_id: number | null;
  };
};

export type Followup = {
  id: number;
  customer_id: number;
  scheduled_at: string;
  purpose: string;
  assigned_to: string;
  priority: string;
  channel: string;
  status: string;
  next_reminder?: string | null;
  notes: string;
  created_at: string;
  customer: Customer;
};

export type PricingRule = {
  id: number;
  within_city_transport: number | string;
  beyond_city_transport: number | string;
  minimum_billable_sft: number | string;
  rounding_rule: string;
  gst_rate: number | string;
  tax_type: string;
  installation_standard: number | string;
  installation_above_200: number | string;
  discount_upto_100: number | string;
  discount_100_300: number | string;
  discount_above_300: number | string;
};

export type BusinessSettings = {
  id: number;
  company_name: string;
  tagline: string;
  phone: string;
  email: string;
  address: string;
  gst_number: string;
  logo_text: string;
  logo_path: string;
  bank_name: string;
  account_name: string;
  account_number: string;
  ifsc: string;
  upi_id: string;
  quotation_terms: string;
  invoice_terms: string;
  payment_terms: string;
  updated_at: string;
};

export type CustomerTimelineItem = {
  type: string;
  title: string;
  detail: string;
  at: string;
};

export type CustomerProfile = {
  customer: Customer;
  metrics: {
    quotation_count: number;
    quotation_value: number;
    invoice_count: number;
    invoice_value: number;
    paid_amount: number;
    pending_amount: number;
    followup_count: number;
    open_followups: number;
  };
  quotations: Array<{
    id: number;
    number: string;
    quotation_date: string;
    status: string;
    grand_total: number | string;
    balance: number | string;
    created_at: string;
  }>;
  invoices: Array<{
    id: number;
    number: string;
    invoice_date: string;
    due_date: string;
    status: string;
    grand_total: number | string;
    paid_amount: number | string;
    pending_balance: number | string;
    created_at: string;
  }>;
  payments: Array<Payment & { invoice_number: string }>;
  followups: Followup[];
  timeline: CustomerTimelineItem[];
};
