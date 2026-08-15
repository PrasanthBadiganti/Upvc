# UPVC Pro - Enterprise ERP System

A comprehensive Enterprise Resource Planning (ERP) system built for UPVC (Unplasticized Polyvinyl Chloride) profile manufacturing and trading businesses.

## Quick Start

### Default Users & Credentials

```
SuperAdmin
  Username: superadmin
  Password: SuperAdmin@123
  Email: superadmin@upvc.com

Admin
  Username: admin
  Password: Admin@123
  Email: admin@upvc.com

Manager
  Username: manager
  Password: Manager@123
  Email: manager@upvc.com

DataEntry
  Username: dataentry
  Password: DataEntry@123
  Email: dataentry@upvc.com
```

### Running the Application

**Backend** (Terminal 1):
```bash
cd backend
.\.venv\Scripts\python -m uvicorn app.main:app --reload
```

**Frontend** (Terminal 2):
```bash
cd frontend
npm run dev
```

Access: http://localhost:5173

---

## Application Overview

**UPVC Pro** is a full-stack ERP system for UPVC businesses with:

- **Sales Management**: Customers, Quotations, Invoices, Payments
- **Purchase Management**: Vendors, Purchase Bills, Vendor Payments
- **Inventory**: Catalog management, Stock tracking
- **Financial**: Chart of Accounts, Journal entries, Ledgers
- **GST Compliance**: GSTR-1, GSTR-3B, HSN summaries
- **Reporting**: P&L, Balance Sheet, Cash Flow, AP Aging
- **Role-Based Access**: Four roles with granular permissions

---

## Roles & Permissions

### Permission Matrix

| Resource | SuperAdmin | Admin | Manager | DataEntry |
|----------|:----------:|:-----:|:-------:|:---------:|
| Customer | CRUD | CRUD | CRU | CR |
| Quotation | CRUD | CRUD | CRU | CR |
| Invoice | CRUD | CRUD | R | R |
| Payment | CRUD | CRUD | CR | R |
| Credit Note | CRUD | CRUD | R | R |
| Debit Note | CRUD | CRUD | R | R |
| Vendor | CRUD | CRUD | R | R |
| Purchase Bill | CRUD | CRUD | R | R |
| Expense | CRUD | CRUD | CRU | CR |
| Catalog | CRUD | CRUD | R | R |
| User | CRUD | R | R | - |
| Role | CRUD | R | R | - |

**Legend**: C=Create, R=Read, U=Update, D=Delete, "-"=No Access

### Role Descriptions

**SuperAdmin**: System administrator with complete access to all features and user management

**Admin**: Business administrator with full operational access except user/role management

**Manager**: Team lead with create/update permissions on customers, quotations, and expenses

**DataEntry**: Data entry operator with create/read access on customers, quotations, and expenses only

---

## Core Business Workflows

### 1. Sales Workflow
```
Customer → Quotation → Invoice → Payment → Closed
```

### 2. Purchase Workflow
```
Vendor → Purchase Bill → Payment → Closed
```

### 3. Adjustments
```
Invoice → Credit Note (refund) / Debit Note (charges)
```

### 4. GST Reporting
```
Monthly Transactions → GSTR-1 & GSTR-3B → GSTN Filing
```

### 5. Financial Close
```
Transactions → P&L & Balance Sheet → Financial Year Close
```

---

## Technology Stack

- **Backend**: FastAPI (Python 3.12)
- **Frontend**: React 18 + Vite
- **Database**: SQLite with SQLAlchemy ORM
- **Authentication**: JWT + bcrypt password hashing
- **PDF Generation**: ReportLab
- **Testing**: pytest

---

## API Endpoints

### Authentication
- `POST /api/login` - Login user
- `GET /api/me` - Current user profile
- `GET /api/permissions` - User permissions

### Users & Roles
- `POST /api/users` - Create user
- `GET /api/users` - List users
- `GET /api/roles` - List roles

### Sales
- `POST /api/quotations` - Create quotation
- `POST /api/quotations/{id}/convert` - Convert to invoice
- `POST /api/invoices/{id}/payments` - Record payment
- `POST /api/invoices/{id}/credit-notes` - Issue credit note

### Purchase
- `POST /api/vendors` - Create vendor
- `POST /api/vendors/{id}/purchase-bills` - Create purchase bill
- `POST /api/purchase-bills/{id}/payments` - Record payment

### Reports
- `GET /api/dashboard` - Dashboard metrics
- `GET /api/gstr1` - GSTR-1 report
- `GET /api/gstr3b` - GSTR-3B report
- `GET /api/balance-sheet` - Balance sheet
- `GET /api/profit-and-loss` - P&L statement

---

## Key Features

### Sales Operations
- ✅ Quotation to Invoice conversion
- ✅ Multi-line item management
- ✅ HSN code mapping for GST
- ✅ Credit/Debit note issuance
- ✅ Payment tracking with status
- ✅ PDF generation (quotation, invoice, receipt)

### Purchase Operations
- ✅ Vendor management
- ✅ Purchase bill creation with HSN codes
- ✅ Vendor payment tracking
- ✅ Purchase bill PDF generation
- ✅ Purchase order history

### Inventory
- ✅ Product catalog with specifications
- ✅ Stock level tracking
- ✅ Stock movement recording
- ✅ Opening balance import

### Financial Management
- ✅ Chart of Accounts (50+ default accounts)
- ✅ Journal entry creation
- ✅ Ledger reports by account
- ✅ Trial balance
- ✅ Fixed asset depreciation
- ✅ Financial year management

### GST Compliance
- ✅ Automatic SGST/CGST/IGST calculation
- ✅ GSTR-1 report generation
- ✅ GSTR-3B summary
- ✅ HSN-wise supply summary
- ✅ JSON export for GSTN offline tool
- ✅ Interstate/Intrastate detection

### Reporting
- ✅ Dashboard with metrics
- ✅ Profit & Loss statement
- ✅ Balance Sheet
- ✅ Cash Flow statement
- ✅ AP Aging analysis
- ✅ Sales & Purchase registers
- ✅ CSV export for all reports

### Data Import
- ✅ CSV import for customers
- ✅ CSV import for vendors
- ✅ Tally ledger masters XML import
- ✅ Opening balances import

### Role-Based Access Control
- ✅ Four-tier role hierarchy
- ✅ Granular permission matrix (12 resources)
- ✅ JWT-based authentication
- ✅ Bcrypt password hashing
- ✅ Permission enforcement on all endpoints

---

## Installation

### Prerequisites
- Python 3.12+
- Node.js 16+
- Git

### Backend Setup
```bash
cd backend
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

### Frontend Setup
```bash
cd frontend
npm install
```

---

## Testing

```bash
cd backend
.\.venv\Scripts\pytest tests/test_core.py -v
```

---

## Security Notes

⚠️ **Important for Production**:
1. Change all default credentials immediately
2. Set a strong SECRET_KEY for JWT
3. Enable HTTPS/TLS
4. Implement database encryption
5. Enable rate limiting
6. Add audit logging
7. Regular backups with encryption

---

## Database

- **Location**: `backend/upvc_pro.db` (SQLite)
- **Reset**: Delete the .db file and restart server
- **Schema**: 18 core models with relationships

---

## Support

- **API Docs**: http://localhost:8000/docs (Swagger)
- **ReDoc**: http://localhost:8000/redoc
- **Database**: SQLite in backend/upvc_pro.db

---

## Version

**v1.0.0** (2026-08-16)

Complete RBAC implementation with four roles, 11 resources, permission matrix, JWT authentication, and all business workflows enabled.

