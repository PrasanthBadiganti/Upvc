#!/usr/bin/env python
"""Test PDF generation"""

from app.models import Quotation
from app.database import SessionLocal
from app.pdf import build_quotation_pdf
from pathlib import Path

db = SessionLocal()
quote = db.query(Quotation).first()

if quote:
    pdf_bytes = build_quotation_pdf(quote)
    output_path = Path("test_quotation.pdf")
    output_path.write_bytes(pdf_bytes)
    print(f"✅ PDF generated: {output_path}")
    print(f"📄 File size: {len(pdf_bytes)} bytes")
    print(f"✅ Quotation: {quote.number}")
    print(f"✅ Items: {len(quote.items)}")
else:
    print("❌ No quotation found")
