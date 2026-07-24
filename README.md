# UPVC Pro -- Local Version Without Node or Docker

This package contains the FastAPI backend, SQLite database, React source code, and a prebuilt frontend. Normal installation and startup require only Python. Node.js, npm, Docker, PostgreSQL, and any cloud service are not required.

## What this is

UPVC Pro is a local-first accounting/ERP system for a UPVC windows, doors, and glass business, built around this workflow:

```text
Customer/Lead -> Follow-up -> Quotation -> Invoice -> Payments -> Ledger -> GST/Financial Reports
Vendor -> Purchase Bill -> Vendor Payment -> Ledger
```

Beyond the original CRM/quotation/invoice pipeline, it now includes a full double-entry general ledger with auto-posting from every transaction, GST filing reports (GSTR-1/3B, HSN summary, registers), purchasing and vendor management, inventory/stock tracking, fixed assets and depreciation, financial-year close with ledger locking, Tally import/export, and financial statements (P&L, Balance Sheet, Cash Flow, AP Aging).

For the full module-by-module breakdown, the complete API/model/route inventory, verification status, and known limitations, see **[PROJECT_STATUS.md](PROJECT_STATUS.md)** — that is the living reference for continuing development; read it before changing code.

New to the application itself (not the code)? **[KT_GUIDE.md](KT_GUIDE.md)** is a page-by-page knowledge transfer guide — what every screen is for, how to use it, what it updates elsewhere, and what to double-check. Start there if you're learning to *use* UPVC Pro rather than *develop* it.

## Windows -- recommended

1. Extract the ZIP fully to a normal folder such as `D:\Projects\upvc-pro-local-no-node`.
2. Double-click `setup-local.bat` once.
3. Double-click `start-local.bat` whenever you want to use the application.
4. The browser opens at `http://127.0.0.1:8000`.
5. Keep the command window open. Press `Ctrl+C` to stop the application.

Requirements: Python 3.11 or newer. While installing Python, select **Add Python to PATH**.

If port `8000` is already in use, `start-local.bat` automatically falls back to `http://127.0.0.1:8001` and prints the exact URL.

## Windows desktop app

For client machines, the application can also run as a desktop app using pywebview. The desktop app starts the same FastAPI backend internally and opens the existing React UI in an application window.

Development run:

```bat
start-desktop.bat
```

Build an installable desktop package:

```bat
build-desktop.bat
```

Build output:

- Desktop app folder: `desktop-dist\UPVC Pro\`
- Main executable: `desktop-dist\UPVC Pro\UPVC Pro.exe`
- Installer output, when Inno Setup is installed: `installer\Output\UPVC-Pro-Setup.exe`

The desktop build stores the live SQLite database under the logged-in Windows user's local app data folder:

```text
%LOCALAPPDATA%\UPVC Pro\upvc_pro.db
```

Back up this file before reinstalling Windows or moving the client to another machine.

## WSL, Linux, or macOS

```bash
chmod +x setup-local.sh start-local.sh
./setup-local.sh
./start-local.sh
```

Open `http://127.0.0.1:8000`.

## URLs

- Application: `http://127.0.0.1:8000`
- API documentation: `http://127.0.0.1:8000/docs`
- Health check: `http://127.0.0.1:8000/api/health`

## Database

The browser/local version creates SQLite automatically as `backend/upvc_pro.db`. The desktop EXE version stores it under `%LOCALAPPDATA%\UPVC Pro\upvc_pro.db`. Back up the active database file to preserve client data. Delete it only when intentionally resetting all data to the included sample dataset.

## Frontend source

Editable React/TypeScript source is under `frontend/src`. The already compiled browser files used during normal startup are under `frontend/dist`; therefore no frontend dependency installation is needed.

For active frontend development, install Node.js 22 LTS or newer and run:

```bat
setup-frontend.bat
start-frontend-dev.bat
```

This starts a separate Vite development server at `http://127.0.0.1:5173`. It proxies API calls to the FastAPI backend, so keep the backend running at `http://127.0.0.1:8001` while developing, or update `VITE_API_PROXY` if your backend is on a different port.

To create a fresh production frontend build:

```bat
build-frontend.bat
```

The build command backs up the existing `frontend/dist` into `frontend/dist-backups` before generating a new `frontend/dist`. The application will automatically serve the updated `frontend/dist` on its next FastAPI restart.

## Correctness & performance (audited 2026-07-24)

The system was put through a data-driven correctness audit and load test — 7,224 API requests created 3,000 quotations, 1,954 invoices, payments, credit/debit notes, purchase bills, stock movements, fixed-asset depreciation, and more, entirely against an isolated throwaway database (the real dev DB was untouched).

- **Correctness: 16,440 automated checks, 0 failures.** Every derived value that's supposed to track another (customer/vendor outstanding balances, stock quantities, depreciation totals, ledger balance, GST report reconciliation) matched its independently-computed ground truth across the full dataset.
- **One real finding, not yet fixed**: invoices don't carry a quotation's Transport/Discount forward as visible fields — the amount is correct but isn't itemized anywhere on the Invoice PDF or details page.
- **Performance**: several list/report pages (Invoices, Quotations, Journal, Dashboard, Reports, Tally Voucher Export) slow down substantially once data volume passes a few thousand records — Tally Voucher Export in particular went from 51ms empty to 10+ seconds at full load. This is a known scaling limitation (no pagination yet), not a correctness issue.

Full detail, exact numbers, and the reasoning behind each finding: see **[PROJECT_STATUS.md](PROJECT_STATUS.md)** — "Data Integrity & Correctness Audit" and "Load & Performance Testing" sections.

## Automated checks

```bash
cd backend
.venv/Scripts/python.exe -m pytest -q   # Windows
# or
.venv/bin/python -m pytest -q           # Linux/macOS
```
