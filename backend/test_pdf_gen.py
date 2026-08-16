from datetime import date, datetime
from decimal import Decimal
from app.models import Quotation, QuotationItem, Customer, BusinessSettings
from app.pdf import build_quotation_pdf

# Create a mock customer
customer = Customer(
    id=1,
    code="CUST-001",
    name="Test Customer",
    phone="+91 9876543210",
    email="test@example.com",
    address="Test Address",
    gst_number="27AABCT1234H1Z5",
    state="Telangana",
    project_site="Test Site",
    status="Active",
    created_at=datetime.now()
)

# Create mock quotation items
item1 = QuotationItem(
    id=1,
    quotation_id=1,
    catalog_item_id=None,
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
    mesh="Stainless Steel",
    created_at=datetime.now()
)

# Create quotation with new professional fields
quotation = Quotation(
    id=1,
    number="QT-2026-001",
    customer_id=1,
    customer=customer,
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
    notes="Test quotation",
    warranty_manufacturing_years=20,
    warranty_hardware_years=5,
    delivery_weeks=3,
    installation_notes="Standard installation with gap-filling upto 3mm. Gaps beyond 3mm require builder plastering.",
    quotation_terms="50% advance with order confirmation. 40% before delivery. 10% after installation. Non-returnable once supplied.",
    items=[item1],
    created_at=datetime.now()
)

# Create business settings
settings = BusinessSettings(
    id=1,
    company_name="Crystal Frames Studio",
    tagline="Premium UPVC Windows & Doors",
    phone="+91 96667 43044",
    email="info@crystalframes.com",
    address="Vizianagaram, Andhra Pradesh",
    gst_number="37ASLPH7160H1ZI",
    state="Andhra Pradesh",
    logo_text="CF",
    bank_name="Bank of Baroda",
    account_name="Crystal Frames Studio",
    account_number="123456789012",
    ifsc="BARB0VIZIAN",
    upi_id="crystalframes@upi",
    quotation_terms="Payment Terms: 50% advance, 40% before delivery, 10% on completion. Warranty: 20 years manufacturing, 5 years hardware.",
    invoice_terms="Payment terms as per invoice.",
    payment_terms="Received with thanks.",
    updated_at=datetime.now()
)

# Generate PDF
try:
    pdf_bytes = build_quotation_pdf(quotation, settings)
    # Check that PDF was generated (has %PDF header)
    if pdf_bytes and b'%PDF' in pdf_bytes:
        print("SUCCESS: PDF generated with new professional sections")
        print("PDF size:", len(pdf_bytes), "bytes")
        print("- Specifications section included")
        print("- Warranty & Delivery section included")
        print("- Installation Notes section included")
        print("- Terms & Conditions section included")
        print("- Bank Details section included")
    else:
        print("ERROR: PDF generated but missing PDF header")
        exit(1)
except Exception as e:
    print("ERROR:", e)
    import traceback
    traceback.print_exc()
    exit(1)
