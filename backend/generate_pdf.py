from app.database import SessionLocal
from app.models import Quotation, BusinessSettings
from app.pdf import build_quotation_pdf

session = SessionLocal()

try:
    # Get the test quotation
    quotation = session.query(Quotation).filter_by(number="QT-2026-001").first()
    settings = session.query(BusinessSettings).first()
    
    if quotation:
        print(f"Generating PDF for quotation {quotation.number}...")
        print(f"Quotation has professional fields:")
        print(f"  - Warranty Manufacturing: {quotation.warranty_manufacturing_years} years")
        print(f"  - Warranty Hardware: {quotation.warranty_hardware_years} years")
        print(f"  - Delivery Weeks: {quotation.delivery_weeks} weeks")
        print(f"  - Installation Notes: {len(quotation.installation_notes)} chars")
        print(f"  - Quotation Terms: {len(quotation.quotation_terms)} chars")
        
        # Generate PDF
        pdf_bytes = build_quotation_pdf(quotation, settings)
        
        # Save to file
        output_path = "test_quotation.pdf"
        with open(output_path, "wb") as f:
            f.write(pdf_bytes)
        
        print(f"\nPDF generated successfully!")
        print(f"PDF size: {len(pdf_bytes)} bytes")
        print(f"Saved to: {output_path}")
        print(f"\nPDF includes the following professional sections:")
        print(f"  1. Product Specifications (profile, color, glass, hardware, etc.)")
        print(f"  2. Warranty & Delivery (manufacturing years, hardware years, delivery timeline)")
        print(f"  3. Installation Notes ({len(quotation.installation_notes)} characters)")
        print(f"  4. Terms & Conditions (payment milestones, warranty details)")
        print(f"  5. Bank / Payment Details (account info)")
    else:
        print("Quotation not found")
        
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
finally:
    session.close()
