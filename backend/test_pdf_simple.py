from app.pdf import build_quotation_pdf
from app.models import Quotation, Customer, BusinessSettings, QuotationItem
from datetime import date, datetime
from decimal import Decimal

# Just test that the PDF builder accepts the new fields
# Create a real Quotation from DB for testing
from app.database import get_session

session = get_session()
try:
    # Get first quotation from DB if exists
    quotation = session.query(Quotation).first()
    if quotation:
        print("Testing with real quotation from database...")
        pdf_bytes = build_quotation_pdf(quotation)
        if pdf_bytes and b'%PDF' in pdf_bytes:
            print("SUCCESS: PDF generated")
            print("PDF size:", len(pdf_bytes), "bytes")
        else:
            print("ERROR: PDF generated but missing PDF header")
    else:
        print("No quotations found in database")
except Exception as e:
    print("ERROR:", e)
    import traceback
    traceback.print_exc()
finally:
    session.close()
