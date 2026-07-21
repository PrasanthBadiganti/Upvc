# UPVC Pro Project Status

Last updated: 2026-07-22 (SFT round-off billing rule + HSN display fix and data backfill)

This is the go-to project reference for continuing development. Read this before changing code.

## Project Goal

UPVC Pro started as a local CRM/quotation/invoice workflow app for a UPVC windows, doors, and glass business. It has since grown into a fairly complete **local-first accounting/ERP system**: the original sales pipeline is now backed by a full double-entry ledger, GST filing reports, purchasing, inventory, fixed assets, financial-year close, and financial statements.

Primary business flow:

```text
Customer / Lead -> Follow-up -> Quotation -> Invoice -> Payments -> Ledger -> GST/Financial Reports
Vendor -> Purchase Bill -> Vendor Payment -> Ledger
```

The app must remain local-first, compact, easy to navigate, and deployable on a client Windows machine without Docker.

## Current Stack

Backend:

- Python 3.11+
- FastAPI
- Uvicorn
- SQLAlchemy 2.x
- Pydantic 2
- SQLite
- ReportLab (PDF generation)
- Pytest (81 backend tests, `backend/tests/test_core.py`)

Frontend:

- React 18
- TypeScript
- Vite
- React Router DOM
- Axios
- Recharts
- Lucide React
- Custom CSS

Desktop packaging:

- pywebview
- PyInstaller
- Optional Inno Setup installer

There is no separate migration tool (no Alembic). Schema changes to existing tables are applied additively at startup by `ensure_schema()` in `backend/app/main.py` (a hand-rolled `PRAGMA table_info` + `ALTER TABLE ADD COLUMN` dict). **Any time a column is added to an existing SQLAlchemy model, it must also be added to this dict**, or the change works against a fresh database (tests) but 500s against an existing one (the real dev/client database). This has bitten the project at least twice — see Known Gotchas below.

## Runtime Modes

### Local Python App

Normal no-Node runtime:

```bat
setup-local.bat
start-local.bat
```

FastAPI serves both:

- API routes under `/api`
- Prebuilt React frontend from `frontend/dist`

Default URL: `http://127.0.0.1:8000` (falls back to `8001` if busy)

### Separate Frontend Development

```bat
setup-frontend.bat
start-frontend-dev.bat
```

Frontend dev URL: `http://127.0.0.1:5173`, proxying `/api` to `http://127.0.0.1:8001`.

### Fresh Frontend Build

```bat
build-frontend.bat
```

Backs up the current `frontend/dist` into `frontend/dist-backups/` before generating a new production build. `frontend/dist` is intentionally tracked — it's required for the no-Node client runtime.

### Desktop App

```bat
start-desktop.bat      REM dev run
build-desktop.bat      REM build desktop-dist/UPVC Pro/UPVC Pro.exe
```

Desktop database: `%LOCALAPPDATA%\UPVC Pro\upvc_pro.db` (fallback `%USERPROFILE%\UPVC Pro\upvc_pro.db`).

## Supported Operations

### Sales & CRM

- Customer CRUD, search (name/phone/email), status filter, salesperson filter, CSV/Tally-XML import with opening-balance support.
- Quotation builder: multi-item, SFT calculation (width x height rounds **up** to the next whole square foot before pricing — not to 2 decimal places — matching how the business actually bills, e.g. 12.1ft x 15.4ft = 186.34 sqft bills as 187 sqft), catalog-linked items, draft/send/duplicate/revise, PDF, convert to invoice (idempotent — re-converting returns the existing invoice).
- Invoice lifecycle: Unpaid/Partially Paid/Paid/Cancelled, cancel with force-rule for paid invoices, reopen, PDF.
- Payments: multiple partial payments per invoice, guards against zero/negative/overpayment/payment-on-cancelled-invoice, receipt PDF.
- Credit Notes and Debit Notes against invoices, with their own cancel lifecycle and GST-correct reversing journal entries.
- Follow-ups & Collections: create/complete follow-ups, Today/Upcoming/Overdue/Completed grouping, collection tracker with a working stage filter (Overdue/Due Soon/Paid), real Call/WhatsApp (`tel:`/`wa.me`) actions, real weekly-collected figure, real recent-activity feed.

### Purchasing & Expenses

- Vendor CRUD, search, CSV/Tally-XML import with opening-balance support.
- Purchase Bills: multi-item, vendor bill number vs internal PB number, CGST/SGST or IGST (interstate-aware), vendor payments, cancel/reopen, PDF.
- Expenses: category-based CRUD, GST-aware, posts to the correct expense ledger account.
- Purchase bill line items can optionally link to a Stock Item, which auto-posts a stock-in movement.

### Inventory / Stock Tracking

- Stock Items (raw materials/hardware — separate from Catalog, which is sellable finished products) with category, unit, HSN code, reorder level.
- Manual Stock In/Out with a running balance, blocks going negative, reason/reference tracking.
- Automatic stock-in from tagged purchase bill lines.
- Low-stock filter/highlighting.
- Deliberately **not** wired into the ledger — quantity tracking only, no costing/valuation (would need a FIFO/weighted-average costing layer, which is out of scope for now).

### Fixed Assets & Depreciation

- Asset register: category, purchase cost, salvage value, useful life, Straight Line or Written Down Value depreciation, optional vendor funding (posts to Accounts Payable) or cash/bank funding.
- Depreciation run: prorated by days since last run, capped at salvage value, posts Depreciation Expense / Accumulated Depreciation.
- Disposal: computes real gain/loss vs. book value, posts to a dedicated Gain/Loss on Disposal account.

### General Ledger

- Chart of Accounts (seeded, extendable), account ledger drill-down, trial balance.
- Every transaction type in the app (invoices, payments, credit/debit notes, purchase bills, vendor payments, expenses, fixed asset acquisition/depreciation/disposal, opening balances) auto-posts a balanced double-entry journal entry.
- Manual Journal Entries: multi-line, balance-validated, with a reversal action (blocked for already-reversed entries and for system-generated entries — only entries with `source_type = "Manual"` can be reversed).

### Financial Year Management

- Define financial years (auto-labeled `FY 2025-26` style, or custom), close (computes and stores a P&L/Balance Sheet snapshot, requires the year to have actually ended, must be closed in chronological order), reopen (must be undone in reverse-chronological order).
- Closing a year **locks the ledger**: any new or edited transaction dated inside a closed year's range is rejected with a clear error, across every posting entry point (invoices, purchase bills, payments, credit/debit notes, expenses, manual journal entries, fixed asset acquisition/depreciation/disposal). Opening-balance imports are deliberately exempt (one-time migration tool, normally run before any year is ever closed).

### GST Filing Reports

Scoped to **filing support** (compute the numbers, export CSV/JSON) — not a live GSTN API integration.

- GSTR-1: B2B, B2C summary, CDNR (credit/debit notes), HSN summary.
- GSTR-3B: outward taxable supplies, eligible ITC, net tax payable — CGST/SGST/IGST all handled correctly for interstate vs intrastate.
- HSN Summary, Sales Register, Purchase Register — with CSV export.
- **GSTR-1 JSON export** (`GET /api/gst/gstr1/json`) — a second GSTR-1 representation shaped for the GST portal's offline-tool upload format (`gstin`/`fp`/`b2b`/`b2cs`/`cdnr`/`hsn`), not the same JSON as the `/api/gst/gstr1` UI endpoint. B2B is grouped by customer GSTIN, B2C is bucketed by place-of-supply + rate, CDNR nets credit/debit notes against their source invoice's GSTIN, and HSN is net of credit/debit note items (matches the on-screen HSN Summary exactly — this was a real bug caught during verification: the first version only counted invoice items and disagreed with the HSN Summary table). Place-of-supply state codes come from the customer's own GSTIN prefix when present, else a hardcoded state-name-to-code lookup table (`GST_STATE_CODES` in `gst_reports.py`) — **that table and the overall JSON schema are from general knowledge, not fetched from an authoritative source, and should be validated against the GST portal's current offline tool before relying on it for a real filing.**
- Interstate detection is automatic (business state vs. customer/vendor state); opening-balance invoices are excluded from GST reports (they're a migration artifact, not a real taxable supply).

### Financial Reports

- Profit & Loss and Balance Sheet — live aggregation over the ledger for any date range / as-of date.
- Cash Flow Statement (direct method) — classifies actual Cash/Bank journal lines by source into Operating / Investing / Financing, with opening/closing balance.
- AP Aging — vendor outstanding bills bucketed by days overdue (Current / 1-30 / 31-60 / 61-90 / 90+).

### Tally Integration

- Export ledger masters and vouchers as Tally-compatible XML for a given date range.
- Import customer/vendor masters from Tally ledger-master XML (auto-detected vs. plain CSV), including opening balances.

### Dashboard, Reports & Settings

- Dashboard: real metrics (leads, live/pending customers, quotations this month, pending payments, revenue received) with real computed captions (e.g. "50% of leads", "+400% vs last month", "Across 7 invoices") — no fabricated trend text.
- Global topbar search: live search across customers/invoices/quotations with a real results dropdown, `Ctrl/Cmd+K` to focus, deep-links into the matching record.
- Reports page: quotation/invoice trends, collection aging, salesperson performance, conversion summary — all DB-backed.
- Settings: business profile (name, tagline, GSTIN, logo), bank details, document terms, pricing/tax defaults — all persisted and actually used (the sidebar/footer/PDFs read the real business name, not a hardcoded one).

## API Endpoint Inventory

110 routes under `/api`, grouped by module (`backend/app/main.py`):

- **Core**: `/health`, `/dashboard`, `/reports`
- **Customers**: CRUD, `/profile`, `/import/preview`, `/import/commit`
- **Catalog & Pricing**: CRUD, `/summary`, `/pricing-rules`, `/business-settings` (+ `/logo`)
- **Quotations**: CRUD, `/status`, `/duplicate`, `/revise`, `/convert`, `/pdf`
- **Invoices & Payments**: CRUD, `/payments`, `/cancel`, `/reopen`, `/pdf`; `/payments/{id}/receipt`
- **Credit/Debit Notes**: create (under invoice), list, get, `/cancel`, `/pdf`
- **Vendors & Purchase Bills**: CRUD, `/import/preview`, `/import/commit`, `/purchase-bills` CRUD, `/payments`, `/cancel`, `/reopen`, `/pdf`
- **Opening Balances**: `/opening-balances/preview`, `/opening-balances/commit`
- **Expenses**: CRUD
- **Ledger**: `/accounts`, `/accounts/{id}/ledger`, `/journal`, `/journal/manual`, `/journal/{id}`, `/journal/{id}/reverse`, `/trial-balance`
- **Fixed Assets**: CRUD, `/depreciate`, `/dispose`
- **Financial Years**: CRUD, `/close`, `/reopen`
- **Stock Items**: CRUD, `/movements`
- **GST Reports**: `/gst/gstr1`, `/gst/gstr1/json` (GST-portal offline-tool format), `/gst/gstr3b`, `/gst/hsn-summary` (+ `/csv`), `/gst/sales-register` (+ `/csv`), `/gst/purchase-register` (+ `/csv`)
- **Financial Statements**: `/profit-and-loss`, `/balance-sheet`, `/cash-flow`, `/ap-aging`
- **Tally**: `/tally/export/masters`, `/tally/export/vouchers`
- **Follow-ups**: CRUD (no delete)
- **Frontend serving**: `/`, `/{full_path:path}` (SPA fallback)

Full request/response shapes: `http://127.0.0.1:8000/docs` (FastAPI auto-generated).

## Database Models

27 SQLAlchemy models (`backend/app/models.py`):

`Customer`, `CatalogItem`, `PricingRule`, `BusinessSettings`, `Quotation`, `QuotationItem`, `Invoice`, `InvoiceItem`, `CreditNote`, `CreditNoteItem`, `DebitNote`, `DebitNoteItem`, `Payment`, `Followup`, `Vendor`, `PurchaseBill`, `PurchaseBillItem`, `VendorPayment`, `Expense`, `ChartOfAccount`, `JournalEntry`, `JournalLine`, `FixedAsset`, `DepreciationEntry`, `FinancialYear`, `StockItem`, `StockMovement`.

Database path: `backend/upvc_pro.db` (local) / `%LOCALAPPDATA%\UPVC Pro\upvc_pro.db` (desktop package).

## Frontend Routes

`/`, `/customers`, `/quotations`, `/quotations/new`, `/quotations/:id`, `/quotations/:id/edit`, `/invoices`, `/invoices/:id`, `/credit-notes`, `/credit-notes/:id`, `/debit-notes`, `/debit-notes/:id`, `/vendors`, `/purchase-bills`, `/purchase-bills/new`, `/purchase-bills/:id`, `/expenses`, `/stock-items`, `/stock-items/:id`, `/fixed-assets`, `/fixed-assets/:id`, `/accounts`, `/accounts/:id`, `/journal`, `/journal/new`, `/journal/:id`, `/trial-balance`, `/financial-years`, `/gst-reports`, `/profit-and-loss`, `/balance-sheet`, `/cash-flow`, `/ap-aging`, `/tally-export`, `/opening-balances`, `/payments`, `/followups`, `/catalog`, `/reports`, `/settings`.

## Verification Status

Last verified: 2026-07-22.

- **81 backend tests passing** (`backend/tests/test_core.py`), covering every module below.
- Every phase in the list was verified live against the running dev database in a browser, not just against pytest's fresh test database — this caught real wiring bugs pytest alone missed: a missing `ensure_schema()` migration entry, a currency-symbol formatting bug on stock quantities, the GSTR-1 JSON export's HSN section disagreeing with the on-screen HSN Summary because it wasn't netting out credit/debit notes, and (this phase) the Quotation Details page having no HSN column at all.
- Phases completed, most recent first:
  1. **SFT round-off billing rule** — quotation item SFT auto-calculated from width x height now rounds **up** to the next whole square foot before pricing (`ROUND_CEILING` in the backend fallback calc, `Math.ceil` in the live frontend calc), not to 2 decimal places, matching real UPVC billing practice. Locked in with a regression test using the client's own example (12.1ft x 15.4ft = 186.34 sqft -> bills as 187).
  2. **HSN display fix + line-item data backfill** — `QuotationDetails.tsx` (the saved-quotation view page) was missing an HSN table column entirely; fixed. Separately, the original seed data never set `hsn_code` on Catalog items or the demo quotation/invoice, which is why HSN looked blank everywhere downstream even though the Create Quotation form, PDF generator, and Invoice Details page were all already correct. Added representative HSN codes (`CATALOG_HSN_CODES` in `seed.py`: 3925.20.00 for UPVC windows/doors, 7007.19.00 for toughened glass, 3925.90.00 for mesh — flagged in-code as needing confirmation against the client's actual HSN master) plus `backfill_line_item_hsn()`, a startup routine that patches existing Catalog/Quotation/Invoice rows in the live dev database without touching anything already set.
  3. **GSTR-1 offline JSON export** — GST-portal upload-format JSON (see GST Filing Reports above).
  4. **Punch-list cleanup** — removed all remaining hardcoded/fabricated UI (fake dashboard trend %, fake Followups metrics fallback numbers, fake "Recent Activity" feed, dead search/date-range/notification chrome, sidebar ignoring Business Settings) and replaced with real computed values or honest removal.
  5. **Cash Flow Statement + AP Aging.**
  6. **Inventory / Stock Tracking**, including auto-stock-in from purchase bills.
  7. **Financial Year Management** with ledger period-locking.
  8. **Fixed Assets & Depreciation** (SLM/WDV, disposal gain/loss).
  9. **Manual Journal Entries** with reversal.
  10. **IGST / interstate GST support** across invoices, purchase bills, credit/debit notes, GST reports, PDFs, Tally export.
  11. **Data migration**: Opening Balances import, Tally ledger-master XML import (customers + vendors).
  12. **CSV import** for customers and vendors.
  13. **GST filing reports** (GSTR-1, GSTR-3B, HSN summary, registers) + **Tally export** + **P&L/Balance Sheet**.
  14. **General Ledger**: Chart of Accounts, auto-posting journal engine, account ledger, trial balance.
  15. **Vendors / Purchase Bills / Expenses.**
  16. **HSN codes + Credit/Debit Notes.**
  17. Everything in the original README brief below "Completed modules" (Dashboard, Customers, Catalog, Quotations, Quotation→Invoice conversion, Invoices, Payments, Follow-ups, Reports, Settings, PDF generation) — all since fully DB-wired; see the punch-list cleanup phase above for what was still fake as of 2026-07-21 and has since been fixed.

## Known Limitations / Not Yet Implemented

These are scope decisions, not defects — each was either explicitly deferred or deliberately scoped down:

- **No multi-user authentication.** No login, no sessions, no roles. Anyone with the URL has full access. The topbar has no user profile for this reason (removed rather than left showing a fake logged-in user).
- **No Employee/Staff table.** `assigned_to` / `sales_person` / `paid_by` / `received_by` are free-text fields, pre-filled from a hardcoded 3-name list (Arun Verma, Neha Kapoor, Rohit Singh) copy-pasted across 6 files. Fixing this properly means building the auth/roles system above.
- **Inventory is quantity-only.** No FIFO/weighted-average costing, no COGS journal entries. Adding real costing is a meaningfully bigger feature than the current stock register.
- **GST filing is compute-and-export only.** No live GSTN API submission (deliberate "Option A" scope from the start of this project).
- **No Delivery Challan or TDS tracking.** Discussed and deliberately deprioritized — both are situational (only matter if the business does non-sale goods movement or has TDS deduction obligations).
- **No Work Orders / installation tracking, no recurring transactions.** Backlog items, not started.
- **Single SQLite file, no multi-tenant or cloud sync.**
- **Frontend ships as one ~850KB JS bundle** (no code-splitting) and list endpoints have no pagination — fine at current data volumes, worth revisiting if the customer/invoice count grows into the thousands.
- **No in-app backup/restore UI** — back up `backend/upvc_pro.db` manually.

## Known Gotchas

- **Adding a column to an existing model requires two edits**, not one: the SQLAlchemy model in `models.py`, *and* an entry in the `ensure_schema()` migrations dict in `main.py`. Skipping the second one works fine against pytest's fresh-created test database and then 500s against the real dev database the first time it's exercised. This has happened twice in this project (the Stock Items `purchase_bill_items.stock_item_id` column, and originally documented as a risk pattern from the IGST phase).
- **`expire_on_commit=False`** is set on the session factory. Any service function that re-loads an object it already touched earlier in the same call (e.g. `record_depreciation` loading the same `FixedAsset` twice) needs an explicit `db.expire_all()` before the second load, or SQLAlchemy will silently skip re-fetching relationships that were already loaded — this looks like a phantom empty list, not an error.
- **`Customer.pending_payment` (and similarly derived fields) are recomputed on every read**, not stored authoritatively — never write to them directly from a new feature; create a real `Invoice`/`Payment` row instead, or the value will silently reset on the next list/profile fetch.
- **Seed/demo data can silently lack fields added in a later phase** — e.g. `hsn_code` was never set on the original Catalog/Quotation/Invoice seed rows from early phases, so it looked "blank" everywhere downstream even though every display layer (form, PDF, details page) was already correctly wired. `seed.py` has a `backfill_*` function pattern (`backfill_catalog_details`, `backfill_line_item_hsn`, etc.) that runs on every startup and fills in blanks on already-existing rows without overwriting anything real — follow this pattern whenever a new required field needs to reach records created in an earlier phase, instead of hand-editing the live dev database.

## Development Rules

- Do not remove `frontend/dist`; it is required for no-Node client runtime.
- Make React changes in `frontend/src`, then run `build-frontend.bat`.
- Keep FastAPI serving the app and API from one local process.
- Keep Docker optional/not required.
- Preserve existing SQLite data; add `ensure_schema()` migration entries before/with any new column on an existing table.
- Add tests for major backend workflow changes, and verify live in the browser against the real dev database, not just pytest.
- Keep UI style compact and consistent with the current design.
