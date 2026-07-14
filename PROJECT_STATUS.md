# UPVC Pro Project Status

Last updated: 2026-07-14

This is the go-to project reference for continuing development. Read this before changing code.

## Project Goal

UPVC Pro is a local business workflow app for a UPVC windows, doors, glass, quotation, invoice, payment, and collection process.

Primary business flow:

```text
Customer / Lead -> Follow-up -> Quotation -> Invoice -> Payments -> Dashboard / Reports
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
- ReportLab
- Pytest

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

Default URL:

```text
http://127.0.0.1:8000
```

Current active dev backend may run on:

```text
http://127.0.0.1:8001
```

### Separate Frontend Development

Use this when changing React/TypeScript source:

```bat
setup-frontend.bat
start-frontend-dev.bat
```

Frontend dev URL:

```text
http://127.0.0.1:5173
```

Vite proxies `/api` to:

```text
http://127.0.0.1:8001
```

### Fresh Frontend Build

```bat
build-frontend.bat
```

This backs up the current `frontend/dist` into `frontend/dist-backups/` before generating a new production build.

Important: `frontend/dist` is intentionally tracked/kept because it is required for the no-Node client runtime.

### Desktop App

Development desktop run:

```bat
start-desktop.bat
```

Build desktop app folder:

```bat
build-desktop.bat
```

Output:

```text
desktop-dist/UPVC Pro/UPVC Pro.exe
```

If Inno Setup `iscc` is installed, installer output goes to:

```text
installer/Output/UPVC-Pro-Setup.exe
```

Desktop database location:

```text
%LOCALAPPDATA%\UPVC Pro\upvc_pro.db
```

Fallback on locked-down PCs:

```text
%USERPROFILE%\UPVC Pro\upvc_pro.db
```

## Supported Operations

### Customers

Supported:

- List customers
- Search by name, phone, email
- Filter by status
- Add customer
- Edit customer
- Delete customer via API
- Store contact details, address, project/site, status, assigned salesperson
- Track quote value and pending payment
- Show customer detail side panel

Statuses:

- New
- Quotation Sent
- Negotiation
- Live
- Completed
- Lost

Frontend delete is not fully exposed yet.

### Catalog and Price Master

Supported:

- List catalog items
- Search catalog
- Filter by category/status
- Add catalog item
- Edit catalog item
- Delete catalog item via API
- Maintain profile, track, glass, hardware, color, min billable SFT, rate/SFT
- Maintain pricing rules

Pricing rules currently include:

- Within-city transport
- Beyond-city transport
- Minimum billable SFT
- Rounding rule
- GST rate
- Tax type
- Installation rates
- Discount ranges

### Quotations

Supported:

- List quotations
- View quotation detail
- Create quotation
- Add multiple quotation items
- Calculate SFT, total SFT, amount, subtotal, GST, grand total, advance, balance
- Save draft
- Send quotation
- Update quotation status
- Convert quotation to invoice
- Browser print preview

Statuses:

- Draft
- Sent
- Accepted
- Converted
- Rejected is planned but not fully enforced

Dedicated backend quotation PDF is not implemented yet.

### Invoices

Supported:

- List invoices
- View invoice detail
- Convert from quotation
- Link invoice to source quotation
- Prevent duplicate invoice generation from same quotation
- Track subtotal, CGST, SGST, grand total, paid amount, pending balance
- Download backend-generated invoice PDF

Statuses:

- Unpaid
- Partially Paid
- Paid
- Cancelled is planned but not fully exposed

### Payments

Supported:

- Record payment against invoice
- Multiple partial payments
- Payment date
- Payment mode
- Transaction/reference number
- Received by
- Notes
- Payment history
- Auto-update invoice paid/pending amount
- Auto-update invoice status
- Auto-update customer pending payment
- Reject zero/negative payment
- Reject overpayment

Payment modes:

- NEFT
- UPI
- Cash
- Cheque
- Card

Payment receipt PDF is not implemented yet.

### Follow-ups and Collections

Supported:

- List follow-ups
- Filter follow-ups by status
- Create follow-up
- Update follow-up
- Store schedule, purpose, assigned user, priority, channel, reminder, notes
- Dashboard shows today's follow-ups

Groups/statuses:

- Today
- Upcoming
- Overdue
- Completed

Call/WhatsApp buttons are UI-only if present.

### Dashboard and Reports

Supported:

- Total leads
- Live customers
- Pending customers
- Quotations this month
- Pending payments
- Revenue received
- Customer status chart
- Pending payment table
- Today's follow-ups
- Reports summary endpoint

Recently improved:

- Monthly quotation/invoice chart now comes from database counts instead of fixed sample chart data.

Still partly static:

- Recent activity still needs to become fully database-driven.
- Some dashboard comparison text in frontend is still fixed copy.

### Settings

Supported:

- Persist pricing/tax defaults through pricing rules API

Not fully supported:

- Business profile persistence
- Bank details persistence
- Logo upload
- Terms template persistence

## API Endpoint Inventory

Health:

- `GET /api/health`

Dashboard and reports:

- `GET /api/dashboard`
- `GET /api/reports`

Customers:

- `GET /api/customers`
- `POST /api/customers`
- `PUT /api/customers/{customer_id}`
- `DELETE /api/customers/{customer_id}`

Catalog and pricing:

- `GET /api/catalog`
- `POST /api/catalog`
- `PUT /api/catalog/{item_id}`
- `DELETE /api/catalog/{item_id}`
- `GET /api/pricing-rules`
- `PUT /api/pricing-rules`

Quotations:

- `GET /api/quotations`
- `GET /api/quotations/{quotation_id}`
- `POST /api/quotations`
- `PUT /api/quotations/{quotation_id}/status`
- `POST /api/quotations/{quotation_id}/convert`

Invoices and payments:

- `GET /api/invoices`
- `GET /api/invoices/{invoice_id}`
- `GET /api/invoices/{invoice_id}/pdf`
- `POST /api/invoices/{invoice_id}/payments`
- `GET /api/payments`

Follow-ups:

- `GET /api/followups`
- `POST /api/followups`
- `PUT /api/followups/{followup_id}`

Frontend serving:

- `GET /`
- `GET /{full_path:path}`

## Database Models

Current SQLAlchemy models:

- `Customer`
- `CatalogItem`
- `PricingRule`
- `Quotation`
- `QuotationItem`
- `Invoice`
- `InvoiceItem`
- `Payment`
- `Followup`

Current source database path:

```text
backend/upvc_pro.db
```

Desktop packaged database path:

```text
%LOCALAPPDATA%\UPVC Pro\upvc_pro.db
```

## Frontend Routes

- `/`
- `/customers`
- `/quotations`
- `/quotations/new`
- `/quotations/:id`
- `/invoices`
- `/invoices/:id`
- `/payments`
- `/followups`
- `/catalog`
- `/reports`
- `/settings`

## Verification Status

Last verified on 2026-07-14:

- Backend tests passed: `3 passed`
- FastAPI served app shell successfully
- Frontend dependencies installed
- Fresh frontend build passed
- Vite dev server started at `http://127.0.0.1:5173`
- Vite `/api/health` proxy returned `{"status":"ok"}`
- Desktop PyInstaller app folder built at `desktop-dist/UPVC Pro`
- Source desktop launcher self-test passed with workspace data dir

Known environment notes:

- Running Vite/esbuild inside the sandbox can fail with `spawn EPERM`; use the provided batch scripts normally on Windows.
- Inno Setup compiler `iscc` was not installed, so installer EXE was not generated in this environment.
- `backend/.pytest_cache` has local permission issues but tests still run.

## Immediate Priorities

Phase 1 remaining cleanup:

- Make recent activity fully database-driven.
- Clean visible mojibake/encoding damage in README, seed data, PDFs, and UI strings.
- Add a lightweight migration strategy before changing existing SQLite schema.
- Add better startup diagnostics for port conflicts.

Next business phases:

- Phase 2: customer history/timeline, follow-up notes, reliable customer aggregates.
- Phase 3: richer inventory/material/price-master fields and product-specific SFT rules.
- Phase 4: stronger quotation builder with catalog item picking, duplication, revisions, accepted quote locking.
- Phase 5: backend quotation PDF.
- Phase 6+: invoice/payment/report polishing.

## Development Rules

- Do not remove `frontend/dist`; it is required for no-Node client runtime.
- Make React changes in `frontend/src`, then run `build-frontend.bat`.
- Keep FastAPI serving the app and API from one local process.
- Keep Docker optional/not required.
- Preserve existing SQLite data; add migrations before schema changes.
- Add tests for major backend workflow changes.
- Keep UI style compact and consistent with the current design.
