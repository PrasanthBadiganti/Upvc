# UPVC Pro — Complete Knowledge Transfer & Reference Guide

This is the **goto file** for anyone onboarded to work with UPVC Pro — whether that means using it day-to-day to run the business, or supporting/maintaining it. It is exhaustive on purpose: every page, every field, every dropdown option, every button, every validation rule, every formula, and every status lifecycle in the application is documented below. Current as of 2026-07-24.

Two other docs exist alongside this one:
- **[README.md](README.md)** — installation/setup only.
- **[PROJECT_STATUS.md](PROJECT_STATUS.md)** — developer-facing technical reference (API routes, database schema, test coverage, phase changelog, the full correctness/performance audit).

This file is the **operational** reference — what the software does and how to drive every part of it.

---

## Table of Contents

1. [Orientation](#1-orientation)
2. [Glossary](#2-glossary)
3. [Business rules, formulas & numbering](#3-business-rules-formulas--numbering)
4. [Status lifecycles, at a glance](#4-status-lifecycles-at-a-glance)
5. [Icon legend](#5-icon-legend)
6. [Sales & CRM — full detail](#6-sales--crm--full-detail)
7. [Purchasing & Inventory — full detail](#7-purchasing--inventory--full-detail)
8. [Accounting — full detail](#8-accounting--full-detail)
9. [Reports & Filing — full detail](#9-reports--filing--full-detail)
10. [Data Tools — full detail](#10-data-tools--full-detail)
11. [Settings — full detail](#11-settings--full-detail)
12. [Dashboard — full detail](#12-dashboard--full-detail)
13. [Cross-cutting: what updates what](#13-cross-cutting-what-updates-what)
14. [Common tasks, step by step](#14-common-tasks-step-by-step)
15. [Known limitations](#15-known-limitations)

---

## 1. Orientation

### What this application is

UPVC Pro is a **local-first accounting/ERP system** for a UPVC windows, doors, and glass fabrication business. Everything — the app server and the database — runs on one machine. No cloud, no internet dependency, no subscription, no external service calls. All data lives in one SQLite file (`backend/upvc_pro.db`).

Primary business flow:

```text
Customer/Lead -> Follow-up -> Quotation -> Invoice -> Payments -> Ledger -> GST/Financial Reports
Vendor -> Purchase Bill -> Vendor Payment -> Ledger
```

Underneath the sales/purchase workflow is a **real double-entry accounting ledger**. Every transaction anywhere in the app — an invoice, a payment, a purchase bill, an expense, a depreciation run, a stock movement's cost — automatically posts a balanced journal entry behind the scenes. You never touch the ledger directly for normal work; it updates itself, and it is provably correct (see the audit summary in section 3).

### How to start it

- **Windows, normal use**: double-click `start-local.bat`. First time only, run `setup-local.bat` once first.
- **Mac/Linux**: `./setup-local.sh` once, then `./start-local.sh`.
- **Desktop app** (no browser tab, its own window): `start-desktop.bat`.
- Opens at `http://127.0.0.1:8000` (falls back to `8001` if that port is busy — the terminal window tells you which).
- Leave the terminal/command window open while using the app; closing it stops the server. `Ctrl+C` in that window stops it cleanly.

### There is no login

**Anyone who can reach that URL has full access to everything** — create, edit, cancel. There are no user accounts, no passwords, no permission levels, no audit trail of "who did what." If several staff use the same installation, the "Sales Person" / "Assigned To" / "Paid By" / "Received By" fields you see throughout the app are just free-text labels picked from a fixed 3-name list (**Arun Verma, Neha Kapoor, Rohit Singh**) — they identify who's associated with a record for reporting purposes only; they do **not** restrict what that person can see or do, and there's no way to add a fourth name to that list from the UI (it's hardcoded).

### The sidebar

Grouped by business domain. Click a group header (with the chevron) to expand/collapse it — your choice is remembered between visits (stored in the browser's local storage), and whichever group contains the page you're currently on auto-expands regardless of its saved state.

| Group | Default state | Pages |
|---|---|---|
| *(ungrouped, top)* | always visible | Dashboard |
| **Sales & CRM** | expanded | Customers, Quotations, Invoices, Credit Notes, Debit Notes, Payments, Follow-ups, Catalog |
| **Purchasing & Inventory** | expanded | Vendors, Purchase Bills, Expenses, Stock Items |
| **Accounting** | collapsed | Bank Accounts, Chart of Accounts, Journal, Trial Balance, Fixed Assets, Financial Years |
| **Reports & Filing** | collapsed | GST Reports, Profit & Loss, Balance Sheet, Cash Flow, AP Aging, Reports |
| **Data Tools** | collapsed | Tally Export, Opening Balances |
| *(ungrouped, bottom)* | always visible | Settings |

### Universal UI patterns (true on almost every page)

- **List pages**: a search box (filters client-side against whatever fields are named in that page's placeholder text, e.g. "Search invoice or customer..."), a data table, and small square icon buttons at the end of each row for actions (View/Edit/Cancel/Reopen/Duplicate/etc. — see the [Icon Legend](#5-icon-legend)). A "Refresh" button re-fetches from the server.
- **Detail pages** (reached via the eye/View icon): a row of summary metric cards at the top, then item/line tables, then an action bar (Record Payment, Download PDF, Cancel, etc.) toward the bottom.
- **Create/Edit**: either a **modal popup** for simple flat records (Customer, Vendor, Catalog Item, Expense, Stock Item, Fixed Asset, Financial Year, Bank Account), or a **dedicated full page** for anything with editable line items (Quotation, Purchase Bill, Manual Journal Entry).
- **Status badges**: colored pills (Draft, Sent, Unpaid, Partially Paid, Paid, Cancelled, Active, Issued, Open, Closed, Disposed, etc.) — see [section 4](#4-status-lifecycles-at-a-glance) for what triggers each transition.
- **PDF downloads**: generated fresh on every click, nothing is pre-stored. Every generated PDF pulls the business name/logo/GSTIN/bank details/terms live from **Settings** at the moment of download.
- **Currency formatting**: ₹ symbol, Indian digit grouping (₹1,23,456.00), almost always 2 decimal places on financial documents.
- **Required fields** are marked with a small red `*` next to the label. A form will not submit (button stays inert or the request is rejected with a red error banner) until every required field and every business-rule guard is satisfied — see each page's "Validation rules" list below.

---

## 2. Glossary

| Term | Meaning |
|---|---|
| **SFT** | Square Feet — the standard unit UPVC windows/doors are priced by. Calculated as `(width in mm ÷ 304.8) × (height in mm ÷ 304.8)`, since 304.8mm = 1 foot. |
| **HSN Code** | Harmonized System of Nomenclature — the tax-classification code every product/service needs for GST filing. |
| **GST** | Goods and Services Tax (India's VAT). Split into CGST + SGST (same state) or IGST (different states). |
| **CGST / SGST** | Central GST + State GST — each half the total GST rate, charged when buyer and seller are in the **same** state. |
| **IGST** | Integrated GST — the full GST rate charged as one line when buyer and seller are in **different** states ("interstate"). |
| **ITC** | Input Tax Credit — GST you paid on purchases, which offsets GST you owe on sales. |
| **GSTR-1** | Monthly/quarterly GST return listing all outward supplies (sales) — B2B, B2C, credit/debit notes, HSN summary. |
| **GSTR-3B** | Summary GST return — total tax liability minus ITC = net tax payable. |
| **COA** | Chart of Accounts — the fixed list of ledger accounts (Cash, Sales Revenue, Accounts Payable, etc.) everything posts to. |
| **Journal Entry** | A single balanced accounting posting (equal total debit and total credit) recording one business event. |
| **SLM** | Straight Line Method of depreciation — same amount depreciated every period. |
| **WDV** | Written Down Value method — a fixed % of the *remaining* book value is depreciated each period (declining amount over time). |
| **AP Aging** | Accounts Payable Aging — how overdue your unpaid vendor bills are, bucketed by days. |
| **Interstate** | Business's state (from Settings) differs from the customer's/vendor's state → triggers IGST instead of CGST+SGST. |
| **Opening Balance** | A starting balance migrated in from whatever system you used before UPVC Pro, entered once via the Opening Balances tool. |

---

## 3. Business rules, formulas & numbering

### SFT (Square Feet) calculation

```
raw_sft = (width_mm ÷ 304.8) × (height_mm ÷ 304.8)
sft = ROUND UP raw_sft to the next whole number   (never rounds to decimals)
billable_sft = MAX(sft, catalog item's "Min Billable SFT")
total_sft = billable_sft × quantity
amount = total_sft × rate_per_sft
```

Example: 12.1ft × 15.4ft = 186.34 sqft → bills as **187** sqft (rounds up, not to nearest). This matches how UPVC fabricators actually price jobs — you can't buy 0.34 of a square foot of material. This applies on Quotation item entry; the calculated `total_sft`/`amount` then carry forward unchanged onto the Invoice when converted.

### GST calculation

- Every invoice/purchase bill/quotation checks: is the customer's/vendor's **State** the same as the business's own **State** (set in Settings)?
  - **Same state** → split the GST rate in half: **CGST = rate÷2, SGST = rate÷2**.
  - **Different state** → charge the full rate as one line: **IGST = full rate**.
- If a customer/vendor has no State recorded at all, the system defaults to treating them as **intrastate** (CGST+SGST), not interstate.
- Default GST rate is 18% (editable per Catalog Item, or globally in Settings → Pricing & Tax Defaults).

### Depreciation formulas

- **Straight Line (SLM)**: `annual_depreciation = (purchase_cost − salvage_value) ÷ useful_life_years`, then prorated by the actual number of days since the asset's last depreciation run (or its purchase date, for the first run).
- **Written Down Value (WDV)**: `period_depreciation = current_book_value × depreciation_rate% `, prorated by days since the last run. **Requires you to enter a Depreciation Rate % when creating the asset** — the system rejects the save otherwise.
- Both methods are **capped so accumulated depreciation never exceeds `purchase_cost − salvage_value`** — an asset can never depreciate below its salvage value, and running depreciation again after that point returns an error ("No depreciation to record for this period").

### AP Aging buckets (days overdue, measured from each bill's Due Date to the report's "As Of" date)

| Bucket | Meaning |
|---|---|
| Current | Not yet due |
| 1-30 Days | 1 to 30 days overdue |
| 31-60 Days | 31 to 60 days overdue |
| 61-90 Days | 61 to 90 days overdue |
| 90+ Days | more than 90 days overdue |

### Document numbering (auto-generated, never typed by hand)

| Prefix | Document |
|---|---|
| `CUST-0001`, `CUST-0002`... | Customer code |
| `VEND-0001`... | Vendor code |
| `QT-YYYY-###` | Quotation number (year of creation + sequence) |
| `INV-YYYY-###` | Invoice number |
| `OB-YYYY-###` | Opening Balance invoice (a special Invoice representing migrated data) |
| `CN-YYYY-###` | Credit Note number |
| `DN-YYYY-###` | Debit Note number |
| `PB-YYYY-###` | Purchase Bill number (your internal number — separate from the vendor's own bill number, which you type in yourself) |
| *(fixed asset)* | Auto-generated `code` field, shown on the asset list/detail |
| *(stock item)* | Auto-generated `code` field |

### Chart of Accounts codes (seeded, fixed structure)

Accounts are numbered by type: **1000s = Assets** (Cash, Bank, Accounts Receivable, Input CGST/SGST/IGST ITC, Fixed Assets, Accumulated Depreciation), **2000s = Liabilities** (Accounts Payable, Output CGST/SGST/IGST Payable), **3000s = Equity** (Owner's Capital, Opening Balance Equity), **4000s = Income** (Sales Revenue, Sales Returns & Allowances), and further ranges for Expense accounts. You will see these codes throughout Journal, Trial Balance, and the Financial Statements.

### What the correctness audit proved (2026-07-24, full detail in PROJECT_STATUS.md)

16,440 automated checks against a database with 7,000+ real records, **zero failures**, confirming:
- `Customer.pending_payment` / `Vendor.pending_payment` always exactly match the true sum of that party's outstanding invoices/bills.
- Every journal entry balances; the global ledger balances to the paisa.
- Stock quantities, depreciation totals, and GST HSN reconciliation are all internally consistent at scale.
- The one confirmed **unfixed gap**: Invoices don't carry a Quotation's Transport/Discount forward as a visible line — see section 6.2.

---

## 4. Status lifecycles, at a glance

### Quotation
```
Draft ⇄ Sent ⇄ Accepted → Converted
```
- Draft/Sent/Accepted are manually selectable on the form.
- **Converted** is set automatically — only by clicking "Convert" (never manually selectable).
- Once **Accepted or Converted**, the quotation is **locked** — the Edit button is disabled. Use **Revise** to create a new editable copy linked to the original, or **Duplicate** to start a completely fresh independent copy.

### Invoice / Purchase Bill (identical lifecycle)
```
Unpaid → Partially Paid → Paid
  ↓ (Cancel, any state, force required if already Paid)
Cancelled → (Reopen) → back to Unpaid/Partially Paid/Paid based on actual balance
```
- Status is **never set manually** — it's always derived automatically from `paid_amount` vs `grand_total`.
- **Cancel** is blocked on an already-Paid invoice/bill unless you explicitly confirm ("force") — the confirmation dialog asks this for you.
- Cancelling reverses the revenue/GST journal entry and removes the balance from the customer's/vendor's running total, but does **not** delete the record — it stays visible with a "Cancelled" badge and a banner saying payments are blocked until reopened.

### Credit Note / Debit Note
```
Issued → (Cancel) → Cancelled
```
One-way in normal use; Cancel is the only transition, and it reverses the note's effect on the invoice balance.

### Fixed Asset
```
Active → (Dispose) → Disposed
```
One-way. Once Disposed, "Run Depreciation" and "Dispose Asset" buttons disappear from the detail page.

### Financial Year
```
Open ⇄ Closed
```
Two-way, but **strictly ordered**: you must close years oldest-first, and reopen years most-recently-closed-first. Closing locks every posting entry point for dates inside that year across the whole app.

### Journal Entry
Not a status field, but: **system-generated entries** (Source = Invoice/Payment/PurchaseBill/etc.) can only be undone by cancelling the *underlying transaction* they came from. **Manual entries** (Source = Manual) can be directly **Reversed**, which posts a new offsetting entry (the original is never edited or deleted).

### Customer / Vendor status (informational, doesn't lock anything)
Customer: `New → Quotation Sent → Negotiation → Live → Completed` (or `Lost` at any point). Automatically flips to **Live** the moment their first quotation converts to an invoice; otherwise it's a manual field you set yourself to track pipeline stage. Vendor: simply `Active` / `Inactive`.

### Catalog Item / Stock Item / Bank Account
Simple `Active` / `Inactive` toggle — inactive items are hidden from the "Active only" filters used when picking them elsewhere (e.g. inactive catalog items disappear from the Quotation's Price Master dropdown, inactive vendors disappear from the Purchase Bill vendor picker).

---

## 5. Icon legend

These icons repeat across almost every list/detail page with a consistent meaning:

| Icon | Meaning |
|---|---|
| 👁 Eye | View / open the detail page |
| ✏️ Edit3 (pencil) | Edit this record |
| 🚫 Ban | Cancel |
| ↩️ RotateCcw | Reopen (undo a cancellation) |
| 🗑 Trash2 | Delete (only where hard-delete is actually allowed: Expenses, Stock/Fixed Asset removal in-modal, journal line removal while composing) |
| 📋 Copy | Duplicate (Quotations) |
| 🌿 GitBranch | Revise (Quotations) — new editable version linked to the original |
| ⬇️ Download | Download the PDF (or CSV, or receipt) |
| 🔄 RefreshCw | Refresh the list from the server |
| ➕ Plus | Add a new row/item/record |
| 🔒 Lock / 🔓 Unlock | Close / Reopen a Financial Year |
| ⚠️ AlertTriangle | Low-stock warning marker next to a stock item's on-hand quantity |

---

## 6. Sales & CRM — full detail

### 6.1 Customers (`/customers`)

**List columns**: Customer (name + auto code), Contact (phone + email), Project/Site, Status, Last Interaction, Next Follow-up, Quote Value, Pending Payment, Assigned To, Actions (View, Edit via the "more" icon).

**Filters**: free-text search (name/phone/email), Status dropdown, Salesperson dropdown.

**Full field list (Add/Edit Customer modal)**:

| Field | Type | Default | Required |
|---|---|---|---|
| Customer Name | text | — | **Yes** |
| Phone | text | "" | No |
| Email | text | "" | No |
| GST Number | text | "" | No |
| State | dropdown, all 36 Indian states/UTs | "" | No (leaving blank defaults GST treatment to intrastate) |
| Status | dropdown: New, Quotation Sent, Negotiation, Live, Completed, Lost | New | No |
| Project / Site | text | "" | No |
| Assigned To | dropdown: Arun Verma, Neha Kapoor, Rohit Singh | Arun Verma | No |
| Next Follow-up | date+time picker | blank | No |
| Quote Value | number | 0 | No — **read-only in practice**, gets recalculated by the system |
| Pending Payment | number | 0 | No — **read-only in practice**, gets recalculated by the system |
| Address | textarea | "" | No |
| Notes | textarea | "" | No |

**Customer profile panel** (right side when a row is selected): Contact Information (phone/email/address/GST/state), Project/Site + Salesperson, four stat tiles (Total Quotations, Total Quote Value, Total Invoices, Pending Amount), Next Follow-up, Notes, Collections (Paid / Pending totals), Recent Timeline (last 6 events: customer created, quotations, invoices, payments, follow-ups — newest first).

**Import CSV button**: accepts a plain CSV (columns: name, phone, email, address, gst_number, project_site, assigned_to, notes, opening_balance) or a Tally ledger-masters XML export (auto-detected by file content). Shows a preview screen with a checkbox per row before you commit. Opening balance, if present, creates a real Opening Balance invoice for that customer as part of the import.

**⚠️ Important**: editing "Quote Value" or "Pending Payment" by hand in this form will appear to save, but gets silently overwritten the next time any quotation/invoice/payment/note touches that customer — the true values live in the actual transaction records, not in these fields.

### 6.2 Quotations

**List page** (`/quotations`) columns: Quotation No. + Site Location, Customer, Date, Validity, Item count, Subtotal, GST, Grand Total, Status, Actions (View, Edit — disabled if Accepted/Converted, Duplicate, Revise, and a "Convert" button — disabled if already Converted).

**Create/Edit Quotation** (`/quotations/new` or `/quotations/:id/edit`):

*Customer Details section — full field list:*

| Field | Type | Required |
|---|---|---|
| Customer Name | dropdown of all customers, plus a **"+" button to onboard a brand-new customer inline** without leaving the page | **Yes** — must explicitly pick one, no default pre-selected |
| Phone | read-only, auto-fills from the selected customer | — |
| Site Location | text | No |
| Sales Person | dropdown: Arun Verma, Neha Kapoor, Rohit Singh | **Yes** — must explicitly pick one |
| Address | text | No |
| Quotation Date | date | **Yes** — no default, must be picked |
| Validity | dropdown: 15 / 30 / 45 Days | **Yes** — no default, must be picked |
| Status | dropdown: Draft, Sent, Accepted | No (defaults to Draft) |

*Inline "Onboard New Customer" modal (via the "+" button)*: Customer Name (required), Phone, Email, GST Number, State, Project/Site, Address. On save, the new customer is created, auto-selected on the quotation, and its Assigned To is set to whichever Sales Person you'd already picked on the quotation (if any). If you left Site Location/Address blank on the quotation, they auto-fill from what you just typed for the new customer.

*Quotation Items table — one row per line item:*

| Column | Behavior |
|---|---|
| Price Master | dropdown of active Catalog items ("Manual" = type everything yourself). Picking one auto-fills Category, Style, HSN, Rate, and every spec field (Profile, Color, Track, Glass, Glass Color, Hardware, Reinforcement, Mesh). |
| Category / Style | text, editable regardless of Price Master selection |
| HSN | text |
| Width (mm) / Height (mm) | number — **SFT auto-calculates and rounds up** the moment either changes (see formula in section 3) |
| SFT | shows the calculated (or manually overridden) value — you *can* type directly into this box instead of Width/Height |
| Qty | number, defaults to 1 per new row |
| Total SFT | read-only, computed = max(SFT, catalog min billable SFT) × Qty |
| Rate / SFT | number — auto-filled if a Price Master item was picked, otherwise type it yourself |
| Amount | read-only, computed = Total SFT × Rate |
| Location | text, e.g. "Living Room" |
| Action | delete this row |

"Add Item" / "Add New Item" buttons both add a genuinely blank row (all numeric fields empty/zero, no placeholder data). "Import from Excel" button exists in the UI but has no wired functionality — it's a placeholder.

*Summary panel*: Subtotal (sum of item amounts), Transport (typed in, defaults blank/0), Discount (typed in, defaults blank/0), Taxable Amount, GST (18%), Grand Total, Advance (50%), Balance Due (50%) — the 50/40/10 split shown further down is a fixed display convention, not something the system enforces on actual payments.

**Validation rules**: Customer, Sales Person, Quotation Date, and Validity must all be explicitly set or the Save/Send buttons silently do nothing. The backend additionally rejects a quotation whose grand total is ≤ 0.

**Actions**: **Save Draft** (or "Save Changes" when editing) keeps whatever Status is selected. **Send Quotation** force-sets status to Sent regardless of the dropdown. **Preview PDF** opens the browser print dialog. **Convert to Invoice** (from the list or detail page) creates the Invoice — safe to click twice, the second click just returns the already-created invoice instead of duplicating it.

**Quotation Details page** (view-only, `/quotations/:id`): items table (Category, Style, HSN, Width, Height, SFT, Qty, Total SFT, Rate/SFT, Amount, Location), Customer & Site card, Commercial Summary (Subtotal, Transport, Discount, GST, Grand Total). Action bar: Print, Download PDF, Share (copies a link to clipboard), Edit (disabled if locked), Duplicate, Revise, Convert to Invoice. A banner appears if the quotation is locked (Accepted/Converted).

**⚠️ Transport/Discount visibility gap**: once converted, the Invoice has **no Transport or Discount field of its own** — the adjustment is folded silently into the invoice's Grand Total. Only the *Quotation* PDF shows Transport/Discount as separate line items; the Invoice PDF and Invoice Details page do not. The number is correct, just not itemized downstream. Confirmed by the audit; not yet fixed.

### 6.3 Invoices

**List page** (`/invoices`) columns: Invoice No., Customer + Project/Site, Invoice Date, Due Date, Grand Total, Paid, Pending, Status, source Quotation number, Actions (View, and Cancel/Reopen depending on current status).

**Invoice Details page** (`/invoices/:id`):
- Summary cards: Invoice Number, Invoice Date, Customer + GSTIN, Project Site, Due Date, Status.
- If converted from a quotation, a green badge links back to the source Quotation.
- **Invoice Items Summary** table: #, Item Description, HSN, Category, Unit, Qty, Rate, GST%, Amount — followed by Subtotal, then either IGST (if interstate) or CGST+SGST (if intrastate), then Grand Total.
- **Payment History** table: #, Payment Date, Mode of Payment, **Bank Account**, Reference No., Amount, Received By, Notes, Receipt (download button).
- **+ Record Payment** button opens a form:

| Field | Type | Required |
|---|---|---|
| Payment Date | date | **Yes** |
| Mode | dropdown: NEFT, UPI, Cash, Cheque, Card | No (defaults NEFT) |
| Bank Account | dropdown of your active Bank Accounts, or "-- None --" | No |
| Reference Number | text | No |
| Amount | number, capped at the current pending balance in the input's max | **Yes**, must be > 0 and ≤ pending balance |
| Received By | text | No (defaults Arun Verma) |
| Notes | text | No |

- **Create Credit Note** / **Create Debit Note** buttons (disabled if pending balance is 0 or the invoice is cancelled) — opens a modal pre-filled with the invoice's own line items so you can edit quantities/amounts down (credit) or add extra charges (debit); see section 6.4/6.5 for the full item field list.
- **Cancel Invoice** (confirms twice if already Paid) / **Reopen Invoice**, **Print Invoice**, **Download PDF**, **Share Invoice** (copies a link).
- Right side: Payment Summary (Grand Total, Paid, Pending, Next Due amount/date) and a visual 50%/40%/10% Payment Schedule (Advance on Confirmation / Before Delivery / After Installation) — purely illustrative, doesn't enforce anything.

**Validation rules**: a payment can't be zero/negative, can't exceed the pending balance, and can't be recorded against a Cancelled invoice.

### 6.4 Credit Notes

**List page** (`/credit-notes`, view-only — creation happens from the Invoice) columns: Credit Note No., Customer, Against Invoice, Note Date, Reason, Total, Status, Actions (View, Cancel).

**Creation form (from Invoice Details)**: Note Date (required), Reason (free text), and an items table copied from the invoice — each row: Description, HSN, Category, Unit, Qty, Rate, GST%, Amount, editable to reflect what's actually being credited.

**Validation rule**: the note's total **cannot exceed the invoice's current pending balance** — the system blocks this with a clear error.

**What it does**: reduces the invoice's `pending_balance` (never touches `grand_total`), reduces the customer's `pending_payment`, posts a reversing journal entry (Sales Returns account debited, Receivable credited, correct CGST/SGST or IGST reversal based on whether the original invoice was interstate).

**Credit Note Details page**: Number, Note Date, Customer, linked Invoice, Status; items table with Subtotal/GST/Grand Total; Reason card if provided; Print/Download PDF; Cancel button (reverses everything above).

### 6.5 Debit Notes

Same structure as Credit Notes, opposite direction: **increases** the invoice's pending balance and the customer's pending payment (Receivable debited, Sales credited). **No upper limit** on the amount — you can debit-note for any value.

### 6.6 Payments (`/payments`)

Read-only flat list across every invoice: #, Invoice ID, Payment Date, Mode, Reference No., Amount, Received By, Notes, and a receipt-download button per row. Payments themselves are only ever *created* from the Invoice Details page — this page is purely for browsing/finding one.

### 6.7 Follow-ups (`/followups`)

Create/complete follow-ups tied to a customer. Fields: Customer (required), Scheduled At (date+time, required), Purpose (Payment Reminder / Site Visit / Document Follow-up / etc.), Assigned To (Arun Verma/Neha Kapoor/Rohit Singh), Priority (Low/Medium/High), Channel (Call/WhatsApp/Visit), Notes. Grouped into Today / Upcoming / Overdue / Completed. Real `tel:` and `wa.me` links on each row call/WhatsApp the customer's actual phone number. Includes a Collections tracker with a stage filter (Overdue/Due Soon/Paid) and a genuinely-computed weekly-collected figure.

**No delete** — only create/update. Mark a follow-up Completed instead of trying to remove it.

### 6.8 Catalog & Price Master (`/catalog`)

Four tabs: **Products** (the main data table), **Materials**, **Rates**, **Rules** — the latter three are just alternate filtered views over the same underlying catalog data plus the Pricing Rules panel described below.

**Full field list (Add/Edit Catalog Item)**:

| Field | Type | Default |
|---|---|---|
| Category | dropdown: Windows, Doors, Glass, Mesh, Partitions, Custom | Windows |
| Product Type | dropdown: Sliding, Casement, Fixed, French, Openable, Partition, Custom | Sliding |
| Name | text, required | — |
| Subtitle | text | "" |
| Profile Brand / Profile Series / Profile Display | text | "" / "" / "" |
| Track | text | "" |
| Color | text | White |
| Glass Type / Thickness / Color / Display | text | all "" |
| Hardware | text | "" |
| Reinforcement | text | "" |
| Mesh | text | "" |
| HSN Code | text | "" |
| Min Billable SFT | number | 5 |
| Rate / SFT | number | 0 |
| GST % | number | 18 |
| Installation / SFT | number | 0 |
| Rounding Rule | dropdown: Round up, Nearest whole number, No rounding | Round up |
| Status | dropdown: Active, Inactive | Active |

**Pricing Rules & Defaults panel** (right side) — business-wide defaults, editable via "Edit Pricing Rules": Within-City Transport, Beyond-City Transport, Minimum Billable SFT, Rounding Rule, GST Rate, Tax Type (Exclusive/Inclusive), Standard Installation rate, Installation rate above 200 SFT, and three volume-based Discount tiers (up to 100 SFT / 100-300 SFT / above 300 SFT). These are the same values also editable from **Settings → Pricing & Tax Defaults**.

**What it does**: picking a catalog item on a Quotation line copies its Rate, HSN, and every spec field onto that line instantly. If a catalog item's HSN is left blank, every quotation/invoice line that uses it will also be blank on HSN — which then shows as a gap in the GST HSN Summary report.

---

## 7. Purchasing & Inventory — full detail

### 7.1 Vendors (`/vendors`)

Mirrors Customers exactly, minus the CRM-specific fields (no "Quote Value," "Next Follow-up," etc.). Fields: Name (required), Phone, Email, GST Number, State, Status (Active/Inactive), Address, Notes. Same CSV/Tally-XML import support, same "don't hand-edit pending_payment" caveat.

### 7.2 Purchase Bills

**List page** (`/purchase-bills`) columns: PB No. (internal), Vendor + GSTIN, Vendor's own Bill No., Bill Date, Due Date, Grand Total, Paid, Pending, Status, Actions.

**New Purchase Bill** (`/purchase-bills/new`):

| Field | Type | Required |
|---|---|---|
| Vendor | dropdown of active vendors | **Yes** |
| Vendor Bill No. | text — the *supplier's own* reference number, kept separate from your internal PB number | No |
| Bill Date | date | **Yes** |
| Due Date | date | **Yes** |
| Notes | text | No |

Items table, one row per line: Description, Category, HSN, Unit, Qty, Rate, GST%, **Amount (you type this yourself — it is not force-calculated from Qty × Rate on save, only shown as a live preview as you type)**, and an optional **Stock Item** link per row.

**⚠️ Validation caveat**: double-check the Amount column actually equals Qty × Rate before saving — unlike the Quotation form, nothing stops you from saving a mismatched amount here.

**What happens on save**: increases the vendor's `pending_payment`; posts a purchase/ITC journal entry (CGST+SGST or IGST depending on interstate detection); any line tagged to a Stock Item automatically posts a Stock-In movement for that quantity.

**Purchase Bill Details page**: identical shape to Invoice Details — item table, Payment History (with Bank Account tag), **+ Record Payment** (same field set as an invoice payment but "Paid By" instead of "Received By"), Cancel/Reopen, Print, Download PDF.

### 7.3 Expenses (`/expenses`)

Full CRUD (create/edit/**delete** — one of the few record types that can be hard-deleted).

| Field | Type | Default |
|---|---|---|
| Date | date, required | today |
| Category | dropdown: Rent, Salaries, Utilities, Transport, Office Supplies, Marketing, Professional Fees, Other | Other |
| Description | text | "" |
| Amount | number, required | — |
| GST % | number | 0 |
| Vendor (optional) | dropdown, reference-only, doesn't affect a vendor's pending payment | None |
| Paid Via | dropdown: Cash, NEFT, UPI, Cheque, Card | Cash |
| Reference Number | text | "" |
| Notes | text | "" |

**What it does**: posts a journal entry to the matching expense ledger account, flowing straight into the Profit & Loss report.

### 7.4 Stock Items

**List page** (`/stock-items`) — a "Low stock only" checkbox filters to items at or below their reorder level (flagged with a warning triangle).

**Add Stock Item** fields: Name (required), Category (dropdown: Profile, Glass, Hardware, Rubber Gasket, Fasteners, Other), Unit (free text, e.g. "Nos", "Mtr", "Sq.Ft", "Kg"), HSN Code, Reorder Level, Opening Quantity, Notes.

**Stock Item Details page**: shows On Hand quantity, Reorder Level, Status, then a full **Movement History** table (Date, Type, Reason, Reference, Quantity ± sign, Balance After). Two buttons:
- **Stock In**: Date, Quantity (required, > 0), Reason (dropdown: Manual, Opening Stock, Return), Reference, Notes.
- **Stock Out**: same fields, Reason dropdown becomes (Issued for Project, Wastage, Adjustment). **Blocked if it would take the balance negative** — the system returns a clear "Insufficient stock" error.

**What it does**: this module is **quantity-only** — no cost/valuation, no COGS journal entries, and deliberately **not wired into the ledger**. Every movement's `balance_after` is a permanent snapshot, and the item's live `quantity_on_hand` is kept in exact sync with the replay of every movement (audit-confirmed, zero drift across 60 movements).

---

## 8. Accounting — full detail

### 8.1 Bank Accounts (`/bank-accounts`)

Fields: Account Name (required, e.g. "HDFC Bank - Current A/c"), Bank Name, Account Number, IFSC, Account Type (dropdown: Current, Savings, OD/CC, Cash), Status (Active/Inactive), Notes.

**What it's for**: appears as an optional dropdown on the "Record Payment" form on both Invoice Details and Purchase Bill Details, so you can tag which physical account the money moved through.

**⚠️ Label only**: there is **no running balance** shown anywhere for a bank account — no "how much is currently in HDFC" report. Purely a tag for filtering/record-keeping on individual payments. Deliberate scope decision, not a bug.

### 8.2 Chart of Accounts (`/accounts`)

Read-only list of every ledger account, grouped by type (Asset, Liability, Equity, Income, Expense), each with a Code, Name, Group, and Status. Click the eye icon to open the **Account Ledger** for that account — every journal line ever posted to it, oldest first, with a running balance, and a click-through to the journal entry each line came from.

You never create/edit accounts directly through the UI — this list is seeded and extended internally as needed by new features.

### 8.3 Journal (`/journal`)

**List page**: every auto-generated and manually-created posting, ever. Columns: Journal No., Date, Narration, Source (Invoice/Payment/CreditNote/DebitNote/PurchaseBill/VendorPayment/Expense/Manual/FixedAsset events/OpeningBalance/etc.), Total, View link.

**New Manual Journal Entry** (`/journal/new`):

| Field | Type | Required |
|---|---|---|
| Entry Date | date | **Yes** |
| Narration | text — a description of *why* | **Yes** |
| Lines (2+ rows) | each: Account dropdown + Debit **or** Credit amount (typing in one clears the other on that row) | **Yes** — at least 2 rows with a nonzero amount, every nonzero row must have an account picked |

Live "Balanced" / "Not Balanced" indicator — **the Post button is disabled until total debits exactly equal total credits**. You can add/remove line rows freely (minimum 2 must remain).

**Journal Entry Details page**: Journal No., Date, Source, Narration, full line table with clickable account links. **Reverse Entry** button — **only appears when Source = "Manual."** System-generated entries can't be reversed here; you cancel the underlying transaction (invoice/bill/etc.) instead, which posts its own correct reversal.

### 8.4 Trial Balance (`/trial-balance`)

Pure report, no inputs — every account's total Debit and Credit, grouped by type, with a grand total row and a "Balanced" / "Out of balance" status line. Should always say Balanced. Loads fast regardless of transaction volume (scales with the fixed number of accounts, not transaction count).

### 8.5 Fixed Assets

**List page** (`/fixed-assets`): Asset + code, Category, Purchase Date, Cost, Accumulated Depreciation, Book Value (computed live as Cost − Accumulated Depreciation), Status.

**Add Asset fields**:

| Field | Type | Required |
|---|---|---|
| Asset Name | text | **Yes** |
| Category | dropdown: Machinery, Vehicle, Furniture, Computer & IT Equipment, Office Equipment, Building, Tools, Other | No (Other) |
| Purchase Date | date | **Yes** |
| Purchase Cost | number | **Yes**, must be > 0 |
| Salvage Value | number | No (0) |
| Useful Life (Years) | number | **Yes**, must be > 0 |
| Depreciation Method | dropdown: Straight Line, Written Down Value | Straight Line |
| Depreciation Rate (% p.a.) | number — **field only appears, and is required, when method = Written Down Value** | conditional |
| Vendor (optional) | dropdown — if set, the acquisition posts to Accounts Payable (you owe the vendor) instead of Cash/Bank | None |
| Payment Mode | dropdown: Bank, Cash | Bank |
| Location | text | No |
| Notes | textarea | No |

**Fixed Asset Details page**: summary cards (Purchase Cost, Accumulated Depreciation, Book Value, Status), Asset Details card (method + rate, useful life, salvage value, vendor, location, and disposal date/value once disposed), full Depreciation History table.
- **Run Depreciation**: pick an As Of Date, posts one prorated depreciation entry (capped at the depreciable base).
- **Dispose Asset**: pick a Disposal Date and Disposal Value — computes the real gain or loss versus book value and posts it to a dedicated Gain/Loss on Disposal account. Both action buttons disappear once an asset is Disposed.

### 8.6 Financial Years (`/financial-years`)

**Add Financial Year**: Start Date (required), End Date (required), Label (optional — auto-generates a `FY 2025-26`-style label if left blank).

**Close Year**: computes and permanently stores a P&L/Balance Sheet snapshot for the period. Blocked unless the year has actually ended, and must be closed in chronological order (oldest open year first).

**Reopen Year**: undoes a close. Must be undone in reverse-chronological order (the most recently closed year first).

**⚠️ Closing locks the ledger**: once closed, **every** posting entry point in the app (invoices, purchase bills, payments, credit/debit notes, expenses, manual journal entries, fixed asset acquisition/depreciation/disposal) rejects any new-or-edited transaction dated inside that year's range, with a clear error. Opening Balance imports are the one exception. **Don't close a year until you're genuinely finished with it** — if you need to fix something afterward, reopen first, fix, then re-close.

---

## 9. Reports & Filing — full detail

All of these follow the same shape: pick a date range (or a single "As Of" date for point-in-time reports), click **Run Report**. Pure read-only views — nothing here can be edited.

### 9.1 GST Reports (`/gst-reports`)

- **GSTR-1**: B2B invoice-wise table (GSTIN, customer, taxable value, rate, CGST/SGST/IGST, invoice value), B2C summary bucketed by rate, CDNR (credit/debit notes against invoices), HSN Summary (code, description, unit, quantity, taxable value, tax, total value).
- **GSTR-3B**: Outward Taxable Supplies (taxable value + CGST/SGST/IGST + total tax), Eligible ITC (input CGST/SGST/IGST + total), Net Tax Payable.
- **CSV downloads**: HSN Summary, Sales Register, Purchase Register.
- **Download GSTR-1 JSON**: a second export shaped for the actual GST-portal offline-tool upload format (`gstin`/`fp`/`b2b`/`b2cs`/`cdnr`/`hsn`) — structurally different from the on-screen GSTR-1 table above.

**⚠️ Validate before real filing**: the JSON export's schema and its state-code lookup table were built from general knowledge, not fetched live from the GST portal — check it against the actual GSTN offline tool before relying on it for a real return. Opening-balance invoices are automatically excluded from every GST report (they're migration artifacts, not real taxable supplies).

### 9.2 Profit & Loss (`/profit-and-loss`)

From/To date range. Income accounts and Expense accounts, each with a Code/Name/Amount table and a subtotal, then a Net Profit (green) or Net Loss (red) figure.

### 9.3 Balance Sheet (`/balance-sheet`)

Single "As Of" date. Assets table, Liabilities table, Equity table, each with totals, plus a Balanced/Out-of-balance status line (Assets should equal Liabilities + Equity).

### 9.4 Cash Flow (`/cash-flow`)

From/To date range. Three sections — Operating Activities, Investing Activities, Financing Activities — each listing the actual Cash/Bank ledger movements classified by source, with a Net Cash Flow subtotal per section, then Opening Cash & Bank Balance, Net Change in Cash, and Closing Cash & Bank Balance.

### 9.5 AP Aging (`/ap-aging`)

Single "As Of" date. Every vendor's outstanding bills bucketed into Current / 1-30 / 31-60 / 61-90 / 90+ days overdue (see formula in section 3), with a grand total row. Audit-confirmed to exactly match the independently-computed sum of every vendor's `pending_payment`.

### 9.6 Reports (`/reports`)

A broader sales/collections analytics dashboard, distinct from the Dashboard homepage: 4 metric cards (Total Quote Value, Total Invoice Value, Payments Received, Pending Collections), a Conversion Summary (quotation → invoice count and rate), Customer Mix breakdown, a Collection Aging snapshot, a Monthly Financial Trend bar chart (Quotes/Invoices/Received by month), a Collection Aging pie chart, a Top Pending Collections table, and a Salesperson Performance table (quotes/quote value/invoices/invoice value/received, per salesperson).

---

## 10. Data Tools — full detail

### 10.1 Tally Export (`/tally-export`)

Two exports, both as Tally-compatible XML for a chosen date range:
1. **Ledger Masters** — every Chart-of-Accounts ledger plus one ledger per customer (under Sundry Debtors) and one per vendor (under Sundry Creditors). Import this into Tally **first**, via *Gateway of Tally → Import Data → Masters*.
2. **Vouchers** — every journal entry in the period as a Tally voucher (Sales, Receipt, Purchase, Payment, Credit/Debit Note, or Journal). Import **second**, via *Gateway of Tally → Import Data → Day Book / Vouchers*.

**⚠️ Untested against a live Tally installation** — this follows Tally's documented XML format but hasn't been verified against a real import. Test with a small date range first. **⚠️ Performance**: at large data volumes (thousands of transactions) the Vouchers export took **over 10 seconds** in load testing.

### 10.2 Opening Balances (`/opening-balances`)

**Purpose**: the one-time tool for bringing your starting position over from whatever you used before UPVC Pro.

**How it works**: upload a CSV trial balance (columns: name, debit, credit) or a Tally XML export, plus an "As Of" date. Preview screen shows how each row auto-matched against your existing Customers/Vendors/Chart-of-Accounts by name, with checkboxes to include/exclude rows before committing. On commit: customer balances become a real Opening Balance invoice (`OB-YYYY-###`, so they show correctly everywhere downstream — dashboard, aging, customer profile); vendor and account balances post directly to the ledger.

**Run this once, early** — import Customers/Vendors first if a party isn't matching by name, and do this before ever closing a Financial Year (though it's technically exempt from the period-lock if you need to run it later).

---

## 11. Settings — full detail

Single page, three sections, each with its own Save button.

**Business Profile**: Logo (upload/remove — appears on every generated PDF and the sidebar), Business Name, Tagline, GST Number, State (**drives interstate/intrastate detection for every transaction in the app**), Logo Text (short fallback shown if no logo image is uploaded, max 4 characters), Phone, Email, Address.

**Bank Details** *(the business's own account shown on outgoing documents — not the same as the Bank Accounts module in section 8.1, which tags individual incoming/outgoing payments)*: Bank Name, Account Name, Account Number, IFSC, UPI ID.

**Document Terms**: the standard terms/conditions paragraphs printed on Quotation PDFs, Invoice PDFs, and Payment Receipt PDFs (three separate text boxes).

**Pricing & Tax Defaults**: GST Rate %, Tax Type (Exclusive/Inclusive), Minimum Billable SFT, Rounding Rule, Within-City Transport, Beyond-City Transport — identical to the panel on the Catalog page, editable from either place.

---

## 12. Dashboard — full detail (`/`)

Six metric cards, all computed live, none fabricated: **Total Leads** (+ "new this month"), **Live Customers** (+ "% of leads"), **Pending Customers** (+ "% of leads"), **Quotations This Month** (+ "% vs last month"), **Pending Payments** (+ "Across N invoices"), **Revenue Received** (+ "% collected").

Below that: a **Quotations vs Invoices (Monthly)** bar chart over the last 12 months, a **Customer Status Distribution** donut chart, a **Pending Payments** table (top overdue invoices with a "View All" link to Invoices), a **Today's Follow-ups** panel, and a **Recent Activity** feed (real recent payments/invoices/quotations, newest first).

Nothing here is editable — click through to the underlying record from any table row.

---

## 13. Cross-cutting: what updates what

| When you... | It also updates... |
|---|---|
| Create a Quotation | Nothing else — stays a draft until converted. |
| Convert a Quotation to Invoice | Creates the Invoice; sets Quotation status to **Converted**; flips Customer status to **Live**; posts a Sales journal entry; increases `Customer.pending_payment` by the invoice's full amount. |
| Record a Payment on an Invoice | Updates Invoice paid/pending + status; decreases `Customer.pending_payment`; posts a journal entry; can optionally tag a Bank Account. |
| Issue a Credit Note | Decreases the Invoice's *pending balance* (not grand total); decreases `Customer.pending_payment`; posts a reversing Sales Returns entry. |
| Issue a Debit Note | Increases the Invoice's pending balance; increases `Customer.pending_payment`; posts an additional Sales entry. |
| Cancel an Invoice | Removes its balance from `Customer.pending_payment`; reverses its revenue/GST journal entry; blocks new payments until reopened. |
| Save a Purchase Bill (with a Stock Item tagged on a line) | Increases `Vendor.pending_payment`; posts a Purchase/ITC entry; **and** posts a Stock-In movement raising that item's on-hand quantity. |
| Record a Vendor Payment | Updates Purchase Bill paid/pending; decreases `Vendor.pending_payment`; posts a journal entry. |
| Run Depreciation on a Fixed Asset | Increases `accumulated_depreciation`; posts Depreciation Expense / Accumulated Depreciation lines; updates book value everywhere it's shown. |
| Dispose a Fixed Asset | Computes real gain/loss vs. book value; posts to Gain/Loss on Disposal; asset becomes read-only. |
| Close a Financial Year | Snapshots P&L/Balance Sheet for the period; **locks every posting entry point** for dates inside that range, app-wide. |
| Change Business Settings (name/GSTIN/logo/state) | Immediately reflected in the sidebar, footer, every future PDF, and interstate GST detection — no restart needed. |
| Add a Bank Account | Becomes selectable on every future "Record Payment" form (invoice and purchase bill) — does **not** retroactively tag past payments. |

All of the "increases/decreases X" relationships are maintained by **incrementally adjusting the stored value at the moment of each transaction**, not recomputed from scratch on every page view. This is efficient but is exactly the kind of design where a bug could theoretically let a number drift over time. The 2026-07-24 audit verified zero drift across 7,000+ real transactions — if a number ever looks wrong in practice, trust the underlying invoices/payments over the summary field, and treat the summary field as the thing that's out of sync, never the other way around.

---

## 14. Common tasks, step by step

**Quote a new customer for a window job**
1. Quotations → Create Quotation.
2. Pick the customer, or click "+" to onboard them on the spot.
3. Pick a Sales Person, set the Quotation Date and Validity.
4. Add Item → pick the product from Price Master (or go Manual), type Width/Height in mm, set Quantity.
5. Repeat for each opening. Add Transport/Discount if applicable.
6. Save Draft (to keep editing later) or Send Quotation.

**Turn an accepted quotation into a bill**
1. Quotations list → find it → click **Convert** (or from Quotation Details → "Convert to Invoice").
2. You land on the new Invoice automatically.

**Record that a customer paid**
1. Open the Invoice (Invoices list → View, or click through from anywhere).
2. **+ Record Payment** → enter date, mode, amount, optionally a Bank Account → Record Payment.

**Handle a partial return / discount after the invoice was issued**
1. Open the Invoice → **Create Credit Note** → adjust the pre-filled items to reflect what's actually being credited → Save.

**Record a bill from a supplier**
1. Vendors → make sure the vendor exists (Add Vendor if not).
2. Purchase Bills → New Purchase Bill → pick the vendor, enter their bill number/dates, add line items.
3. If a line represents stock you're keeping (not immediately consumed), link it to a Stock Item so it auto-updates inventory.

**Pay a vendor**
1. Open the Purchase Bill → **+ Record Payment**.

**Check what you owe vs. what's owed to you**
1. Dashboard for the quick view, or Reports & Filing → AP Aging (what you owe vendors) and the Dashboard's "Pending Payments" table / Reports page (what customers owe you).

**Close the books for a finished year**
1. Accounting → Financial Years → Add Financial Year (or use one already created).
2. Confirm every transaction for that period is entered and correct — **you cannot easily undo this without reopening in strict order**.
3. Click the lock icon → Close Year.

**File GST for a period**
1. Reports & Filing → GST Reports → set the date range → Run Reports.
2. Review GSTR-1/GSTR-3B on screen, download CSVs or the GSTR-1 JSON as needed.
3. **Validate the JSON against the actual GST portal's offline tool before uploading it for a real filing.**

**Migrate historical data when first setting up**
1. Customers/Vendors → Import CSV (or Tally XML) for master data first.
2. Data Tools → Opening Balances → upload your trial balance CSV/XML, review the match preview, commit.
3. Do this before closing any Financial Year.

---

## 15. Known limitations

Scope decisions, not defects:

- **No login/authentication** — one shared workspace, no permissions, no audit trail of who did what.
- **No real Employee/Staff records** — salesperson names are a hardcoded 3-name list.
- **Inventory is quantity-only** — no cost valuation, no COGS in the P&L.
- **GST filing is compute-and-export only** — nothing files directly with the government; you still upload/file manually.
- **No Delivery Challan or TDS tracking.**
- **No Work Orders/installation tracking, no recurring transactions.**
- **Bank Accounts are label-only** — no per-account running balance.
- **Invoices don't show Transport/Discount as their own line** — folded silently into Grand Total.
- **List pages have no pagination** — confirmed in load testing to slow down noticeably (several pages hit 1-2+ seconds, Tally Voucher Export over 10 seconds) once the database holds several thousand records. Still fully correct at that scale, just slower to load.
- **Single SQLite file, no built-in backup/restore UI** — back up `backend/upvc_pro.db` manually and regularly.

---

*This guide draws on a full correctness audit and load test performed 2026-07-24 — see [PROJECT_STATUS.md](PROJECT_STATUS.md) for the technical detail behind every claim above (exact API endpoints, database schema, test coverage, and the raw audit numbers).*
