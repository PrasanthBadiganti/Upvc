# UPVC Pro -- Local Version Without Node or Docker

This package contains the FastAPI backend, SQLite database, React source code, and a prebuilt frontend. Normal installation and startup require only Python. Node.js, npm, Docker, PostgreSQL, and any cloud service are not required.

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

## Automated checks

```bash
cd backend
.venv/Scripts/python.exe -m pytest -q   # Windows
# or
.venv/bin/python -m pytest -q           # Linux/macOS
```
-----------



I am developing a local desktop-style web application for a client who runs a UPVC windows, doors, and glass business.

Please inspect the complete source code I attach before making changes. Continue from the existing implementation rather than rebuilding the project from scratch.

Project goal

The application manages the complete UPVC business workflow:

Customer/Lead
→ Follow-up
→ Measurement
→ Quotation
→ Customer Confirmation
→ Invoice
→ Partial Payments
→ Pending Collections
→ Completion

The software must remain compact, attractive, easy to navigate, and closely aligned with the existing UI design.

Current technology stack
Backend
Python 3.11+
FastAPI
Uvicorn
SQLAlchemy 2.x
Pydantic 2
Pydantic Settings
SQLite
ReportLab for PDF generation
Pytest
FastAPI TestClient / HTTPX
Frontend
React
TypeScript
Vite
React Router DOM
Axios
Recharts
Lucide React
Custom CSS
Local architecture
React frontend
      ↓ REST API
FastAPI backend
      ↓ SQLAlchemy
SQLite database

FastAPI serves both:

The REST API
The compiled React frontend

The entire application runs from:

http://127.0.0.1:8000

API documentation:

http://127.0.0.1:8000/docs

The normal user does not need Docker, Node.js, or npm. The compiled frontend is already included. Node.js is only required when changing and rebuilding the React source.

Local setup requirements

The application must continue to work without Docker.

Windows flow:

1. Run setup-local.bat once
2. Run start-local.bat
3. Open http://127.0.0.1:8000

Relevant directories:

backend/
frontend/src/
frontend/dist/

SQLite database:

backend/upvc_pro.db

Do not change the project into a Docker-only or Node-runtime-dependent solution.

Completed modules
1. Dashboard

The dashboard currently shows:

Total leads
Live customers
Pending customers
Quotations count
Pending payments
Revenue received
Quotations versus invoices chart
Customer-status distribution chart
Pending-payment table
Today’s follow-ups
Recent activity

Some totals come from SQLite. Some chart/activity information may still use sample data and should eventually become fully database-driven.

2. Customer and lead management

Implemented:

Add customer
Edit customer
Search by name, phone, or email
Filter by customer status
Customer code generation such as CUST-0001
Contact details
Customer address
Project/site information
Assigned salesperson
Last interaction
Next follow-up
Quotation value
Pending-payment value
Customer details side panel

Statuses include:

New
Quotation Sent
Negotiation
Live
Completed
Lost

A backend delete endpoint may exist, but delete functionality is not fully exposed in the frontend.

3. Catalog and price master

Implemented catalog fields:

Category
Product type
Product name
Style
Profile
Track
Glass
Hardware
Colour
Minimum billable square feet
Rate per square foot
Active/inactive status

Typical products include:

Sliding window
Casement window
French door
Fixed glass
Mosquito mesh
Toughened glass partition

Pricing-rule settings include:

Within-city transport charge
Outside-city transport charge
Minimum billable SFT
Rounding rule
GST percentage
Inclusive/exclusive tax type
Installation charges
Discount percentage ranges

Catalog add and edit are implemented. Backend delete may exist, but frontend deletion is not complete.

4. Quotation management

Implemented:

Automatic quotation number generation, such as QT-2026-001
Customer selection
Customer phone and address
Site location
Quotation date
Validity period
Salesperson
Draft, sent, accepted, and converted statuses
Multiple quotation line items
Add and remove line items
Product category
Product style
Width in millimetres
Height in millimetres
Quantity
Square-foot calculation
Total square feet
Rate per square foot
Item amount
Room/site location
Profile and material specifications
Transport charge
Discount
GST
Grand total
Advance
Balance
Save draft
Send/save quotation
Quotation list
Quotation details
Browser print preview
Convert quotation into invoice

Current approximate SFT calculation:

SFT = width in feet × height in feet

The client’s exact calculation still needs confirmation because the original sample invoice appears to use minimum-area and/or special rounding rules.

5. Quotation-to-invoice conversion

Implemented end-to-end:

Convert quotation into invoice
Copy customer details
Copy project/site details
Copy line items
Copy dimensions
Copy rates and amounts
Copy taxes and totals
Link invoice to original quotation
Generate invoice number such as INV-2026-001
Set invoice due date
Change quotation status to Converted
Change customer status to Live
Update customer pending-payment amount
Prevent duplicate invoices from being generated from the same quotation

If conversion is called again, the existing invoice should be returned instead of creating another one.

6. Invoice management

Implemented:

Invoice listing
Invoice details
Link to originating quotation
Customer details
Project/site information
Invoice item table
Subtotal
CGST
SGST
Grand total
Paid amount
Pending balance
Due date
Browser printing
Invoice PDF download
Copy/share page link

Invoice statuses:

Unpaid
Partially Paid
Paid

Payment schedule displayed:

50% advance
40% before delivery
10% after installation
7. Payment management

Implemented:

Multiple partial payments against one invoice
Payment date
Payment method
Reference/transaction number
Received-by field
Notes
Payment history
All-payments page
Automatic paid-amount update
Automatic pending-balance update
Automatic customer pending-payment update
Automatic invoice status update
Prevent zero or negative payments
Prevent payment greater than pending balance

Payment modes include:

NEFT
UPI
Cash
Cheque
Card
8. Follow-ups and collections

Implemented:

Create follow-up
Select customer
Date and time
Purpose
Assigned employee
Priority
Contact channel
Next reminder
Mark follow-up completed
Group by status
Pending-payment tracker
Invoice due date
Pending amount
Reminder status

Priorities:

Low
Medium
High

Channels:

Call
WhatsApp
Visit
Email

Follow-up groups:

Today
Upcoming
Overdue
Completed

Call and WhatsApp buttons are currently UI actions only. They are not connected to a real telephone or WhatsApp Business API.

9. Reports

Implemented summary reporting for:

Total quotation value
Total invoice value
Total payments received
Pending collections
Financial bar chart
Customer-status chart

Reports should eventually become completely dynamic and support filters and exports.

10. Settings

Persisted settings include:

GST percentage
Tax type
Minimum billable SFT
Rounding rule
Transport charges

The business-profile screen may currently contain sample values, but full persistence is still needed for:

Business name
GST number
Phone
Email
Address
Bank name
Account number
IFSC
Logo
Quotation terms
Invoice terms
11. PDF generation

Invoice PDF generation is implemented using ReportLab.

The PDF includes:

Invoice number
Customer
Project
Invoice date
Due date
Item details
Quantity
Rate
GST
Subtotal
CGST
SGST
Grand total
Paid amount
Pending amount
Payment terms

A dedicated backend-generated quotation PDF still needs to be implemented. Current quotation preview mainly uses browser printing.

UI pages already designed and implemented

The product uses a compact SaaS-style interface with:

Light theme
White cards
Subtle shadows
Blue and teal accents
Compact typography
Left navigation sidebar
Header search
Date selector
Notification area
User profile
Responsive tables
Status pills
Charts and summary cards

Main pages:

Dashboard
Customers
Quotations
Create Quotation
Quotation Details
Invoices
Invoice Details
Payments
Follow-ups & Collections
Catalog & Price Master
Reports
Settings

Please preserve the existing design language and avoid unnecessary changes to spacing, typography, colours, navigation, and page structure.

Important business rules

The original client quotation/invoice uses:

Width and height
SFT
Number of windows
Total SFT
Rate per SFT
Total amount
Installation location
Transport
Discount
Profile
Track
Glass type
Glass colour
Hardware
Reinforcement
Mesh
Payment schedule

Payment terms:

50% advance with work order
40% before material delivery
10% after installation

The exact UPVC square-foot formula must remain configurable because the client may use:

Actual calculated square feet
Minimum billable square feet
Rounding up
Frame/profile allowance
Product-specific minimum values
Different rates for styles and materials

Do not hard-code one calculation rule everywhere.

Main remaining work

Please review the code and create a prioritized implementation plan for these items:

Authentication and login
User roles and permissions
Admin, salesperson, accountant, and staff roles
Audit trail and history
Quotation revision history
Dedicated quotation PDF generation
Persist business-profile and bank details
Company logo upload
Terms-and-conditions templates
Backup and restore
Database export/import
Excel import for catalog and quotation measurements
WhatsApp integration
Email integration
Proper reminder notifications
Dynamic recent activity
Fully dynamic dashboard charts
Better reports and CSV/PDF export
Product-specific SFT rules
Discount approval rules
GST-compliant numbering and financial validation
Customer statement/ledger
Payment receipt PDF
Work-order generation
Delivery tracking
Installation tracking
File and document attachments
Stronger frontend/backend validation
Error handling and logging
Security hardening
Production deployment preparation
Instructions for continuing development

Before modifying anything:

Inspect the entire project structure.
Run the existing backend tests.
Run the application locally.
Identify broken or incomplete functions.
Confirm the database schema and relationships.
Do not remove working functionality.
Do not redesign the UI without approval.
Maintain backward compatibility with existing SQLite data.
Add database migrations when changing tables.
Add tests for every major feature.
Keep the application runnable without Docker.
Preserve the single local URL served by FastAPI.
Keep the React source editable and the compiled frontend deployable.
Update the README after every setup-related change.

Start by reporting:

Existing folder structure
Existing API endpoints
Existing database models
Existing frontend routes
Current test results
Bugs or technical debt discovered
Recommended next development phase

Do not claim a feature is complete until it has been run and tested.
