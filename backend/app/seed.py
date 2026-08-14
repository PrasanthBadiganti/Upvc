from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from . import models
from .schemas import QuotationCreate, QuotationItemPayload
from .services import convert_quotation_to_invoice, create_quotation, record_payment


# Representative HSN codes (3925.20.00 = plastic doors/windows/frames, 7007.19.00 = toughened
# safety glass, 3925.90.00 = other builders' ware of plastics) - not fetched from an authoritative
# source, confirm against the client's actual HSN master / CA before relying on them for filing.
CATALOG_HSN_CODES = {
    "Sliding Window": "3925.20.00",
    "Casement Window": "3925.20.00",
    "French Door": "3925.20.00",
    "Sliding Door": "3925.20.00",
    "Ventilator": "3925.20.00",
    "Fixed Glass": "7007.19.00",
    "Mosquito Mesh": "3925.90.00",
    "Toughened Glass Partition": "7007.19.00",
}


DEFAULT_CHART_OF_ACCOUNTS = [
    ("1000", "Cash", "Asset", "Current Assets"),
    ("1010", "Bank", "Asset", "Current Assets"),
    ("1100", "Accounts Receivable", "Asset", "Current Assets"),
    ("1200", "Input CGST (ITC)", "Asset", "Duties & Taxes"),
    ("1210", "Input SGST (ITC)", "Asset", "Duties & Taxes"),
    ("1220", "Input IGST (ITC)", "Asset", "Duties & Taxes"),
    ("1500", "Fixed Assets (Gross Block)", "Asset", "Fixed Assets"),
    ("1590", "Accumulated Depreciation", "Asset", "Fixed Assets"),
    ("2000", "Accounts Payable", "Liability", "Current Liabilities"),
    ("2100", "Output CGST Payable", "Liability", "Duties & Taxes"),
    ("2110", "Output SGST Payable", "Liability", "Duties & Taxes"),
    ("2120", "Output IGST Payable", "Liability", "Duties & Taxes"),
    ("3000", "Owner's Capital", "Equity", "Capital Account"),
    ("3800", "Opening Balance Equity", "Equity", "Capital Account"),
    ("4000", "Sales Revenue", "Income", "Direct Income"),
    ("4100", "Sales Returns & Allowances", "Income", "Direct Income"),
    ("4200", "Gain/Loss on Asset Disposal", "Income", "Indirect Income"),
    ("5000", "Purchases", "Expense", "Direct Expenses"),
    ("5100", "Rent", "Expense", "Indirect Expenses"),
    ("5110", "Salaries", "Expense", "Indirect Expenses"),
    ("5120", "Utilities", "Expense", "Indirect Expenses"),
    ("5130", "Transport", "Expense", "Indirect Expenses"),
    ("5140", "Office Supplies", "Expense", "Indirect Expenses"),
    ("5150", "Marketing", "Expense", "Indirect Expenses"),
    ("5160", "Professional Fees", "Expense", "Indirect Expenses"),
    ("5190", "Other Expenses", "Expense", "Indirect Expenses"),
    ("5200", "Depreciation Expense", "Expense", "Indirect Expenses"),
]


def ensure_chart_of_accounts(db: Session) -> None:
    existing = {row[0] for row in db.execute(select(models.ChartOfAccount.code))}
    changed = False
    for code, name, account_type, account_group in DEFAULT_CHART_OF_ACCOUNTS:
        if code not in existing:
            db.add(models.ChartOfAccount(code=code, name=name, account_type=account_type, account_group=account_group))
            changed = True
    if changed:
        db.commit()


def seed_database(db: Session) -> None:
    ensure_chart_of_accounts(db)
    if db.scalar(select(models.Customer.id).limit(1)) is not None:
        ensure_business_settings(db)
        backfill_customer_details(db)
        backfill_catalog_details(db)
        backfill_line_item_hsn(db)
        backfill_invoice_adjustments(db)
        return

    now = datetime.now().replace(second=0, microsecond=0)
    customers = [
        models.Customer(code="CUST-0001", name="Greenview Builders", phone="+91 98765 43210", email="info@greenview.in", address="Office No. 501, Galaxy Tower, Baner, Pune - 411045, Maharashtra", gst_number="27AAACG1234A1Z5", project_site="Greenview Residency, Pune", status="Quotation Sent", last_interaction=now - timedelta(days=1), next_followup=now + timedelta(days=1), quote_value=Decimal("1345600"), pending_payment=Decimal("215000"), assigned_to="Arun Verma", notes="Prefers premium profile and toughened glass options."),
        models.Customer(code="CUST-0002", name="Sharma Residency", phone="+91 98211 22334", email="sharma.r@residency.in", address="Lucknow, Uttar Pradesh", gst_number="09AAXCS5555L1Z2", project_site="Sharma Residency, Lucknow", status="Negotiation", last_interaction=now - timedelta(days=2), next_followup=now + timedelta(days=2), quote_value=Decimal("987500"), pending_payment=Decimal("120000"), assigned_to="Neha Kapoor", notes="Awaiting final approval from society committee."),
        models.Customer(code="CUST-0003", name="Sai Constructions", phone="+91 99887 66554", email="projects@saicon.in", address="Hyderabad, Telangana", gst_number="36AAECS7777F1Z8", project_site="Sai Heights, Hyderabad", status="Live", last_interaction=now - timedelta(days=3), next_followup=now + timedelta(days=4), quote_value=Decimal("1875300"), pending_payment=Decimal("0"), assigned_to="Rohit Singh", notes="Large ongoing project with phased delivery."),
        models.Customer(code="CUST-0004", name="Urban Spaces", phone="+91 98203 88477", email="info@urbanspaces.in", address="Bengaluru, Karnataka", gst_number="29AACCU2222P1Z7", project_site="Urbania, Bengaluru", status="New", last_interaction=now - timedelta(days=4), next_followup=now + timedelta(hours=5), quote_value=Decimal("456000"), pending_payment=Decimal("456000"), assigned_to="Arun Verma", notes="Needs site measurement before quote revision."),
        models.Customer(code="CUST-0005", name="Apex Developers", phone="+91 98111 22345", email="contact@apexdev.in", address="Noida, Uttar Pradesh", gst_number="09AACCA9876M1Z4", project_site="Apex Enclave, Noida", status="Completed", last_interaction=now - timedelta(days=7), quote_value=Decimal("1120800"), pending_payment=Decimal("0"), assigned_to="Neha Kapoor", notes="Completed customer. Useful reference project."),
        models.Customer(code="CUST-0006", name="Skyline Infra", phone="+91 98990 11223", email="purchase@skyline.in", address="Chennai, Tamil Nadu", gst_number="33AAACS6543D1Z1", project_site="Skyline Towers, Chennai", status="Live", last_interaction=now - timedelta(days=8), next_followup=now + timedelta(days=5), quote_value=Decimal("2235000"), pending_payment=Decimal("345000"), assigned_to="Rohit Singh", notes="Pending balance to be followed after delivery."),
        models.Customer(code="CUST-0007", name="Dream Homes", phone="+91 99555 66778", email="hello@dreamhomes.in", address="Jaipur, Rajasthan", gst_number="08AACCD4567K1Z9", project_site="Dream Villas, Jaipur", status="Negotiation", last_interaction=now - timedelta(days=9), next_followup=now + timedelta(days=3), quote_value=Decimal("678900"), pending_payment=Decimal("50000"), assigned_to="Arun Verma", notes="Interested in color laminate upgrade."),
        models.Customer(code="CUST-0008", name="Classic Associates", phone="+91 98100 88991", email="projects@classic.in", address="Kolkata, West Bengal", gst_number="19AACCC2222A1Z3", project_site="Classic Grande, Kolkata", status="Lost", last_interaction=now - timedelta(days=10), quote_value=Decimal("210000"), pending_payment=Decimal("0"), assigned_to="Neha Kapoor", notes="Lost due to budget constraints."),
    ]
    db.add_all(customers)

    catalog = [
        models.CatalogItem(category="Windows", product_type="Sliding", name="Sliding Window", subtitle="2 Track - 3 Panel", profile_brand="VEKA", profile_series="Euroline 60 mm", profile="VEKA 60 mm", track="2 Track", glass_type="Clear Toughened", glass_thickness="5 mm", glass_color="Clear", glass="5 MM Saint Gobain", hardware="McCoy Hardware", reinforcement="1.5 mm GI", mesh="SS Mesh", color="White", min_billable_sft=10, rate_per_sft=680, gst_percent=18, installation_rate=120, rounding_rule="Round up"),
        models.CatalogItem(category="Windows", product_type="Casement", name="Casement Window", subtitle="Side Hung - Outward", profile_brand="VEKA", profile_series="Euroline 60 mm", profile="VEKA 60 mm", track="--", glass_type="Clear Toughened", glass_thickness="5 mm", glass_color="Clear", glass="5 MM Saint Gobain", hardware="McCoy Hardware", reinforcement="1.5 mm GI", mesh="Optional", color="White", min_billable_sft=8, rate_per_sft=720, gst_percent=18, installation_rate=120, rounding_rule="Round up"),
        models.CatalogItem(category="Doors", product_type="French", name="French Door", subtitle="2 Panel - Outward", profile_brand="VEKA", profile_series="Euroline 70 mm", profile="VEKA 70 mm", track="--", glass_type="Clear Toughened", glass_thickness="6 mm", glass_color="Clear", glass="6 MM Saint Gobain", hardware="Dorma Handle Set", reinforcement="2 mm GI", mesh="Optional", color="White", min_billable_sft=15, rate_per_sft=1150, gst_percent=18, installation_rate=140, rounding_rule="Round up"),
        models.CatalogItem(category="Glass", product_type="Fixed", name="Fixed Glass", subtitle="Single Pane", profile_brand="VEKA", profile_series="Euroline 60 mm", profile="VEKA 60 mm", track="--", glass_type="Clear Toughened", glass_thickness="5 mm", glass_color="Clear", glass="5 MM Saint Gobain", hardware="Structural Silicone", reinforcement="1.5 mm GI", mesh="--", color="Clear", min_billable_sft=6, rate_per_sft=450, gst_percent=18, installation_rate=100, rounding_rule="Round up"),
        models.CatalogItem(category="Mesh", product_type="Openable", name="Mosquito Mesh", subtitle="Openable", profile_brand="Generic", profile_series="Mesh Frame", profile="--", track="1 MM Galvanized", glass_type="--", glass_thickness="", glass_color="", glass="--", hardware="S S Black Mesh", reinforcement="--", mesh="SS Black Mesh", color="Black", min_billable_sft=5, rate_per_sft=220, gst_percent=18, installation_rate=60, rounding_rule="Round up"),
        models.CatalogItem(category="Glass", product_type="Partition", name="Toughened Glass Partition", subtitle="Frameless / With Patch", profile_brand="Generic", profile_series="Frameless", profile="--", track="--", glass_type="Toughened", glass_thickness="10 mm", glass_color="Clear", glass="10 MM Toughened", hardware="SS Patch Fittings", reinforcement="--", mesh="--", color="Clear", min_billable_sft=20, rate_per_sft=1350, gst_percent=18, installation_rate=150, rounding_rule="Round up"),
    ]
    db.add_all(catalog)
    db.add(models.PricingRule(id=1))
    db.add(models.BusinessSettings(id=1))
    db.commit()

    quote = create_quotation(
        db,
        QuotationCreate(
            customer_id=customers[0].id,
            quotation_date=date.today() - timedelta(days=16),
            validity_days=30,
            sales_person="Arun Verma",
            site_location="Greenview Residency, Gandhinagar, Gujarat",
            address="Plot No. 45, Sector 9, Gandhinagar, Gujarat - 382009",
            status="Sent",
            transport=Decimal("2500"),
            discount=Decimal("5059.10"),
            notes="All dimensions are in mm. Delivery in 15-18 working days after confirmation.",
            items=[
                QuotationItemPayload(category="Sliding Window", style="2 Track 2 Shutter", width_mm=1200, height_mm=1200, sft=Decimal("11.56"), quantity=2, total_sft=Decimal("23.12"), rate_per_sft=950, amount=Decimal("21964"), location="Living Room", profile="VEKA Euroline 60 mm", color="White", track="Stainless Steel Track", glass="5mm Clear Toughened", glass_color="Clear", hardware="DORMA", reinforcement="1.5mm GI", mesh="SS Mesh"),
                QuotationItemPayload(category="Sliding Window", style="3 Track 3 Shutter", width_mm=1800, height_mm=1200, sft=Decimal("17.34"), quantity=2, total_sft=Decimal("34.68"), rate_per_sft=1050, amount=Decimal("36414"), location="Bed Room 1", profile="VEKA Euroline 60 mm", color="White", track="Stainless Steel Track", glass="5mm Clear Toughened", glass_color="Clear", hardware="DORMA", reinforcement="1.5mm GI", mesh="SS Mesh"),
                QuotationItemPayload(category="Fixed Glass", style="Fixed", width_mm=900, height_mm=1200, sft=Decimal("8.67"), quantity=1, total_sft=Decimal("8.67"), rate_per_sft=850, amount=Decimal("7369.50"), location="Staircase", profile="VEKA Euroline 60 mm", color="White", track="--", glass="5mm Clear Toughened", glass_color="Clear", hardware="Structural Silicone", reinforcement="1.5mm GI", mesh="--"),
                QuotationItemPayload(category="Sliding Door", style="2 Track 2 Shutter", width_mm=1800, height_mm=2100, sft=Decimal("26.25"), quantity=1, total_sft=Decimal("26.25"), rate_per_sft=1150, amount=Decimal("30187.50"), location="Balcony", profile="VEKA Euroline 60 mm", color="White", track="Stainless Steel Track", glass="5mm Clear Toughened", glass_color="Clear", hardware="DORMA", reinforcement="1.5mm GI", mesh="SS Mesh"),
                QuotationItemPayload(category="Ventilator", style="Top Hung", width_mm=600, height_mm=450, sft=Decimal("2.92"), quantity=2, total_sft=Decimal("5.83"), rate_per_sft=900, amount=Decimal("5247"), location="Toilet", profile="VEKA Euroline 60 mm", color="White", track="--", glass="5mm Clear Toughened", glass_color="Clear", hardware="DORMA", reinforcement="1.5mm GI", mesh="SS Mesh"),
            ],
        ),
    )
    invoice = convert_quotation_to_invoice(db, quote.id)
    invoice.number = "INV-2025-093"
    quote.number = "QT-2025-146"
    db.commit()
    record_payment(
        db,
        invoice.id,
        invoice.grand_total / 2,
        payment_date=date.today() - timedelta(days=12),
        mode="NEFT",
        reference_number="UTR1234567890",
        received_by="Arun Verma",
        notes="50% Advance received",
    )

    purposes = [
        (customers[0], "Payment Reminder", "High", "Call", now.replace(hour=10, minute=30), "Today, 04:00 PM"),
        (customers[1], "Payment Reminder", "Medium", "WhatsApp", now.replace(hour=12, minute=0), "Today, 05:00 PM"),
        (customers[2], "Document Follow-up", "High", "Visit", now.replace(hour=14, minute=30), "Today, 06:30 PM"),
        (customers[3], "Payment Reminder", "Medium", "WhatsApp", now.replace(hour=16, minute=0), "Tomorrow, 10:00 AM"),
        (customers[4], "Site Visit & Payment", "Low", "Visit", now.replace(hour=18, minute=0), "Tomorrow, 11:30 AM"),
    ]
    for customer, purpose, priority, channel, when, note in purposes:
        db.add(models.Followup(customer_id=customer.id, scheduled_at=when, purpose=purpose, assigned_to=customer.assigned_to, priority=priority, channel=channel, status="Today", next_reminder=when + timedelta(hours=4), notes=note))
    db.commit()
    backfill_customer_details(db)
    backfill_catalog_details(db)
    backfill_line_item_hsn(db)
    backfill_invoice_adjustments(db)
    ensure_business_settings(db)


def ensure_business_settings(db: Session) -> None:
    if not db.get(models.BusinessSettings, 1):
        db.add(models.BusinessSettings(id=1))
        db.commit()


def backfill_customer_details(db: Session) -> None:
    details = {
        "Greenview Builders": ("27AAACG1234A1Z5", "Prefers premium profile and toughened glass options."),
        "Sharma Residency": ("09AAXCS5555L1Z2", "Awaiting final approval from society committee."),
        "Sai Constructions": ("36AAECS7777F1Z8", "Large ongoing project with phased delivery."),
        "Urban Spaces": ("29AACCU2222P1Z7", "Needs site measurement before quote revision."),
        "Apex Developers": ("09AACCA9876M1Z4", "Completed customer. Useful reference project."),
        "Skyline Infra": ("33AAACS6543D1Z1", "Pending balance to be followed after delivery."),
        "Dream Homes": ("08AACCD4567K1Z9", "Interested in color laminate upgrade."),
        "Classic Associates": ("19AACCC2222A1Z3", "Lost due to budget constraints."),
    }
    changed = False
    for customer in db.scalars(select(models.Customer)).all():
        gst_number, notes = details.get(customer.name, ("", ""))
        if gst_number and not customer.gst_number:
            customer.gst_number = gst_number
            changed = True
        if notes and not customer.notes:
            customer.notes = notes
            changed = True
    if changed:
        db.commit()


def backfill_catalog_details(db: Session) -> None:
    defaults = {
        "Sliding Window": ("VEKA", "Euroline 60 mm", "Clear Toughened", "5 mm", "Clear", "1.5 mm GI", "SS Mesh", Decimal("18"), Decimal("120")),
        "Casement Window": ("VEKA", "Euroline 60 mm", "Clear Toughened", "5 mm", "Clear", "1.5 mm GI", "Optional", Decimal("18"), Decimal("120")),
        "French Door": ("VEKA", "Euroline 70 mm", "Clear Toughened", "6 mm", "Clear", "2 mm GI", "Optional", Decimal("18"), Decimal("140")),
        "Fixed Glass": ("VEKA", "Euroline 60 mm", "Clear Toughened", "5 mm", "Clear", "1.5 mm GI", "--", Decimal("18"), Decimal("100")),
        "Mosquito Mesh": ("Generic", "Mesh Frame", "--", "", "", "--", "SS Black Mesh", Decimal("18"), Decimal("60")),
        "Toughened Glass Partition": ("Generic", "Frameless", "Toughened", "10 mm", "Clear", "--", "--", Decimal("18"), Decimal("150")),
    }
    changed = False
    for item in db.scalars(select(models.CatalogItem)).all():
        values = defaults.get(item.name)
        if not values:
            continue
        profile_brand, profile_series, glass_type, glass_thickness, glass_color, reinforcement, mesh, gst_percent, installation_rate = values
        for field, value in {
            "profile_brand": profile_brand,
            "profile_series": profile_series,
            "glass_type": glass_type,
            "glass_thickness": glass_thickness,
            "glass_color": glass_color,
            "reinforcement": reinforcement,
            "mesh": mesh,
            "gst_percent": gst_percent,
            "installation_rate": installation_rate,
            "rounding_rule": "Round up",
            "hsn_code": CATALOG_HSN_CODES.get(item.name, ""),
        }.items():
            if not getattr(item, field):
                setattr(item, field, value)
                changed = True
    if changed:
        db.commit()


def backfill_line_item_hsn(db: Session) -> None:
    changed = False
    for item in db.scalars(select(models.QuotationItem)).all():
        code = CATALOG_HSN_CODES.get(item.category)
        if code and not item.hsn_code:
            item.hsn_code = code
            changed = True
    for item in db.scalars(select(models.InvoiceItem)).all():
        code = CATALOG_HSN_CODES.get(item.category)
        if code and not item.hsn_code:
            item.hsn_code = code
            changed = True
    if changed:
        db.commit()


def backfill_invoice_adjustments(db: Session) -> None:
    """Copy adjustment details to invoices created before those fields existed.

    Converted invoices have a one-to-one source quotation, so the original
    transport and discount values are the authoritative historical values.
    """
    changed = False
    invoices = db.scalars(
        select(models.Invoice).where(models.Invoice.quotation_id.is_not(None))
    ).all()
    for invoice in invoices:
        quotation = invoice.quotation
        if not quotation:
            continue
        if not invoice.transport and not invoice.discount and (quotation.transport or quotation.discount):
            invoice.transport = quotation.transport
            invoice.discount = quotation.discount
            changed = True
    if changed:
        db.commit()
