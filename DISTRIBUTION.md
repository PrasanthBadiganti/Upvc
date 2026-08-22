# UPVC Pro - Distribution Guide

## Quick Start (Development Mode)

### Windows
Simply run the provided batch file:
```bash
start-app.bat
```

This will:
1. Start the FastAPI backend on http://127.0.0.1:8000
2. Start the React frontend dev server on http://localhost:5173
3. Open the app in your default browser

### Manual Start
**Terminal 1 - Backend:**
```bash
cd backend
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

**Terminal 2 - Frontend:**
```bash
cd frontend
npm run dev
```

Then open: http://localhost:5173

---

## Production Build (Executable)

### Prerequisites
- Python 3.10+ 
- Node.js 16+ with npm
- PyInstaller: `pip install pyinstaller`

### Build Standalone EXE

Run the build script:
```bash
build-desktop.bat
```

This will create: `backend\dist\UPVC Pro\UPVC Pro.exe`

The script builds the frontend, closes any running copy, clears the previous
build, bundles with `backend\UPVC_Pro.spec`, then runs the packaged exe's
`--self-test` and fails the build if it does not pass.

Ship the whole `backend\dist\UPVC Pro` folder, not just the .exe - the exe
needs the `_internal` folder beside it. Business data lives separately in
`%LOCALAPPDATA%\UPVC Pro`, so it survives a rebuild.

**What happens during build:**
1. Builds React frontend to static files
2. Copies static files to backend folder
3. Bundles Python backend with PyInstaller
4. Creates standalone executable

### Running the EXE

Simply double-click: `UPVC Pro.exe`

- Runs in its own desktop window (no browser needed)
- API binds to 127.0.0.1 on a random free port
- Database (SQLite) lives in `%LOCALAPPDATA%\UPVC Pro`

---

## Database Management

### Fresh Database (Empty)
The application includes an empty database by default. To start fresh:

```bash
cd backend
del upvc_pro.db
python -c "from app.database import engine, Base; Base.metadata.create_all(bind=engine)"
```

### Database Location
- Development: `backend/upvc_pro.db`
- Distribution: `%LOCALAPPDATA%\UPVC Pro\upvc_pro.db` (survives rebuilds)

---

## API Documentation

After starting the app, visit:
- **API Docs (Swagger):** http://127.0.0.1:8000/docs
- **ReDoc:** http://127.0.0.1:8000/redoc

---

## Project Structure

```
UPVC/
├── backend/              # FastAPI Python backend
│   ├── app/
│   │   ├── models.py     # Database models
│   │   ├── schemas.py    # API schemas
│   │   ├── services.py   # Business logic
│   │   ├── main.py       # FastAPI app
│   │   └── pdf.py        # PDF generation
│   ├── upvc_pro.db       # SQLite database (empty on fresh install)
│   └── requirements.txt
│
├── frontend/             # React + TypeScript frontend
│   ├── src/
│   │   ├── pages/        # App pages
│   │   ├── components/   # Reusable components
│   │   └── types/        # TypeScript types
│   ├── dist/             # Built frontend (for EXE)
│   └── package.json
│
├── start-app.bat         # Quick start script (Dev)
├── build-desktop.bat     # Build the desktop executable
├── launcher.py           # Python launcher
└── DISTRIBUTION.md       # This file
```

---

## Features

### Sales & CRM
- Quotations (QT26-1 format)
- Invoices (IV26-1 format)
- Credit Notes (CN26-1 format)
- Debit Notes (DN26-1 format)
- Payments (PAY26-1 format)
- Customer management
- Follow-ups & pipeline tracking

### Purchasing & Inventory
- Vendors
- Purchase Bills (PB26-1 format)
- Expenses (EX26-1 format)
- Stock tracking

### Accounting
- Chart of Accounts
- Journal Entries (JE26-1 format)
- Trial Balance
- Ledger reports

### Reports & Filing
- GST reports (GSTR-1, GSTR-3B, HSN summary)
- P&L Statement
- Balance Sheet
- Cash Flow
- AP Aging
- Tally XML export
- CSV import

### Data Tools
- Customer/Vendor bulk import
- Opening balances import
- Fixed assets management
- Financial year management

---

## Compact Document ID Format

All document IDs use a compact format: `PREFIX + YY + SEQUENCE`

| Document | Format | Example |
|----------|--------|---------|
| Quotation | QT | QT26-1, QT26-2 |
| Invoice | IV | IV26-1, IV26-2 |
| Credit Note | CN | CN26-1, CN26-2 |
| Debit Note | DN | DN26-1, DN26-2 |
| Purchase Bill | PB | PB26-1, PB26-2 |
| Expense | EX | EX26-1, EX26-2 |
| Payment | PAY | PAY26-1, PAY26-2 |
| Journal Entry | JE | JE26-1, JE26-2 |

**Key features:**
- Sequence never resets (continuous across years)
- 2026: QT26-1 to QT26-999+
- 2027: QT27-1000, QT27-1001 (continues from last year)
- Very compact and readable

---

## Testing with Empty Database

When you start with a fresh/empty database:

1. **Create a customer** - Start at Customers page
2. **Create a quotation** - Go to Quotations, create one with items
3. **See the ID format** - Notice QT26-1 (not QT-2026-001)
4. **Create an invoice** - Convert quotation to invoice
5. **See more IDs** - IV26-1, CN26-1 for credit notes, etc.

---

## Troubleshooting

### Port 8000 already in use
Change the port in start-app.bat:
```bash
python -m uvicorn app.main:app --port 8001
```

### Frontend not loading
Ensure npm is installed and run:
```bash
cd frontend
npm install
npm run dev
```

### Database errors
Delete the database and recreate:
```bash
cd backend
del upvc_pro.db
python -c "from app.database import engine, Base; Base.metadata.create_all(bind=engine)"
```

### EXE won't start
Ensure Python path includes required packages. Try running from command line to see errors:
```bash
cd "backend/dist/UPVC Pro"
"UPVC Pro.exe" --self-test
```

---

## Support

For issues or feature requests, check the application's built-in API documentation at `/docs`

---

**UPVC Pro v1.0** - Professional UPVC Business Management System
