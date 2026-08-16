from datetime import date, datetime
from decimal import Decimal
from app.database import SessionLocal
from app.models import Customer, Quotation, QuotationItem

session = SessionLocal()

try:
    # Create or get a customer
    customer = session.query(Customer).first()
    if not customer:
        customer = Customer(
            code="CUST-001",
            name="Test Customer",
            phone="+91 9876543210",
            email="test@example.com",
            address="Test Address, Vizianagaram",
            gst_number="27AABCT1234H1Z5",
            state="Telangana",
            project_site="Test Site",
            status="Active"
        )
        session.add(customer)
        session.flush()
    
    # Create quotation with new professional fields
    quotation = Quotation(
        number="QT-2026-001",
        customer_id=customer.id,
        quotation_date=date.today(),
        validity_days=30,
        sales_person="Arun Verma",
        site_location="Test Site",
        address="Test Address",
        status="Draft",
        subtotal=Decimal("22500"),
        transport=Decimal("1500"),
        discount=Decimal("0"),
        gst=Decimal("4320"),
        grand_total=Decimal("28320"),
        advance=Decimal("0"),
        balance=Decimal("28320"),
        notes="Test quotation for professional PDF",
        warranty_manufacturing_years=20,
        warranty_hardware_years=5,
        delivery_weeks=3,
        installation_notes="Standard installation with gap-filling upto 3mm. Gaps beyond 3mm require builder plastering.",
        quotation_terms="50% advance with order confirmation. 40% before delivery. 10% after installation."
    )
    session.add(quotation)
    session.flush()
    
    # Create a quotation item
    item = QuotationItem(
        quotation_id=quotation.id,
        category="Window",
        style="Casement",
        width_mm=Decimal("1000"),
        height_mm=Decimal("1500"),
        sft=Decimal("15"),
        quantity=1,
        total_sft=Decimal("15"),
        rate_per_sft=Decimal("1500"),
        amount=Decimal("22500"),
        hsn_code="7007",
        location="Living Room",
        profile="Enzo 90MM",
        color="White",
        track="2.5 Track",
        glass="5MM Float",
        glass_color="Clear",
        hardware="Fimet",
        reinforcement="1MM Steel",
        mesh="Stainless Steel"
    )
    session.add(item)
    session.commit()
    
    print(f"Created quotation QT-2026-001 with ID {quotation.id}")
    print(f"Professional fields:")
    print(f"  - Warranty Manufacturing: {quotation.warranty_manufacturing_years} years")
    print(f"  - Warranty Hardware: {quotation.warranty_hardware_years} years")
    print(f"  - Delivery Timeline: {quotation.delivery_weeks} weeks")
    print(f"  - Installation Notes: {quotation.installation_notes[:50]}...")
    print(f"  - Quotation Terms: {quotation.quotation_terms[:50]}...")
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
    session.rollback()
finally:
    session.close()
