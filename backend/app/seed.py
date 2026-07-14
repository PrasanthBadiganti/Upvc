from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from . import models
from .schemas import QuotationCreate, QuotationItemPayload
from .services import convert_quotation_to_invoice, create_quotation, record_payment


def seed_database(db: Session) -> None:
    if db.scalar(select(models.Customer.id).limit(1)) is not None:
        return

    now = datetime.now().replace(second=0, microsecond=0)
    customers = [
        models.Customer(code="CUST-0001", name="Greenview Builders", phone="+91 98765 43210", email="info@greenview.in", address="Office No. 501, Galaxy Tower, Baner, Pune - 411045, Maharashtra", project_site="Greenview Residency, Pune", status="Quotation Sent", last_interaction=now - timedelta(days=1), next_followup=now + timedelta(days=1), quote_value=Decimal("1345600"), pending_payment=Decimal("215000"), assigned_to="Arun Verma"),
        models.Customer(code="CUST-0002", name="Sharma Residency", phone="+91 98211 22334", email="sharma.r@residency.in", address="Lucknow, Uttar Pradesh", project_site="Sharma Residency, Lucknow", status="Negotiation", last_interaction=now - timedelta(days=2), next_followup=now + timedelta(days=2), quote_value=Decimal("987500"), pending_payment=Decimal("120000"), assigned_to="Neha Kapoor"),
        models.Customer(code="CUST-0003", name="Sai Constructions", phone="+91 99887 66554", email="projects@saicon.in", address="Hyderabad, Telangana", project_site="Sai Heights, Hyderabad", status="Live", last_interaction=now - timedelta(days=3), next_followup=now + timedelta(days=4), quote_value=Decimal("1875300"), pending_payment=Decimal("0"), assigned_to="Rohit Singh"),
        models.Customer(code="CUST-0004", name="Urban Spaces", phone="+91 98203 88477", email="info@urbanspaces.in", address="Bengaluru, Karnataka", project_site="Urbania, Bengaluru", status="New", last_interaction=now - timedelta(days=4), next_followup=now + timedelta(hours=5), quote_value=Decimal("456000"), pending_payment=Decimal("456000"), assigned_to="Arun Verma"),
        models.Customer(code="CUST-0005", name="Apex Developers", phone="+91 98111 22345", email="contact@apexdev.in", address="Noida, Uttar Pradesh", project_site="Apex Enclave, Noida", status="Completed", last_interaction=now - timedelta(days=7), quote_value=Decimal("1120800"), pending_payment=Decimal("0"), assigned_to="Neha Kapoor"),
        models.Customer(code="CUST-0006", name="Skyline Infra", phone="+91 98990 11223", email="purchase@skyline.in", address="Chennai, Tamil Nadu", project_site="Skyline Towers, Chennai", status="Live", last_interaction=now - timedelta(days=8), next_followup=now + timedelta(days=5), quote_value=Decimal("2235000"), pending_payment=Decimal("345000"), assigned_to="Rohit Singh"),
        models.Customer(code="CUST-0007", name="Dream Homes", phone="+91 99555 66778", email="hello@dreamhomes.in", address="Jaipur, Rajasthan", project_site="Dream Villas, Jaipur", status="Negotiation", last_interaction=now - timedelta(days=9), next_followup=now + timedelta(days=3), quote_value=Decimal("678900"), pending_payment=Decimal("50000"), assigned_to="Arun Verma"),
        models.Customer(code="CUST-0008", name="Classic Associates", phone="+91 98100 88991", email="projects@classic.in", address="Kolkata, West Bengal", project_site="Classic Grande, Kolkata", status="Lost", last_interaction=now - timedelta(days=10), quote_value=Decimal("210000"), pending_payment=Decimal("0"), assigned_to="Neha Kapoor"),
    ]
    db.add_all(customers)

    catalog = [
        models.CatalogItem(category="Windows", product_type="Sliding", name="Sliding Window", subtitle="2 Track  -  3 Panel", profile="VEKA 60 mm", track="2 Track", glass="5 MM Saint Gobain", hardware="McCoy Hardware", color="White", min_billable_sft=10, rate_per_sft=680),
        models.CatalogItem(category="Windows", product_type="Casement", name="Casement Window", subtitle="Side Hung  -  Outward", profile="VEKA 60 mm", track="--", glass="5 MM Saint Gobain", hardware="McCoy Hardware", color="White", min_billable_sft=8, rate_per_sft=720),
        models.CatalogItem(category="Doors", product_type="French", name="French Door", subtitle="2 Panel  -  Outward", profile="VEKA 70 mm", track="--", glass="6 MM Saint Gobain", hardware="Dorma Handle Set", color="White", min_billable_sft=15, rate_per_sft=1150),
        models.CatalogItem(category="Glass", product_type="Fixed", name="Fixed Glass", subtitle="Single Pane", profile="VEKA 60 mm", track="--", glass="5 MM Saint Gobain", hardware="Structural Silicone", color="Clear", min_billable_sft=6, rate_per_sft=450),
        models.CatalogItem(category="Mesh", product_type="Openable", name="Mosquito Mesh", subtitle="Openable", profile="--", track="1 MM Galvanized", glass="--", hardware="S S Black Mesh", color="Black", min_billable_sft=5, rate_per_sft=220),
        models.CatalogItem(category="Glass", product_type="Partition", name="Toughened Glass Partition", subtitle="Frameless / With Patch", profile="--", track="--", glass="10 MM Toughened", hardware="SS Patch Fittings", color="Clear", min_billable_sft=20, rate_per_sft=1350),
    ]
    db.add_all(catalog)
    db.add(models.PricingRule(id=1))
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
