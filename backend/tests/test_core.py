import os
from decimal import Decimal
from pathlib import Path

DB_FILE = Path(__file__).resolve().parents[1] / "test_upvc.db"
if DB_FILE.exists():
    DB_FILE.unlink()
os.environ["DATABASE_URL"] = f"sqlite:///{DB_FILE}"

from fastapi.testclient import TestClient
from app.main import app


def test_health():
    with TestClient(app) as client:
        assert client.get("/api/health").json() == {"status": "ok"}


def test_core_flow():
    with TestClient(app) as client:
        customers = client.get("/api/customers").json()
        assert customers
        payload = {
            "customer_id": customers[0]["id"],
            "quotation_date": "2026-07-14",
            "validity_days": 30,
            "sales_person": "Arun Verma",
            "site_location": "Test Site",
            "address": "Test Address",
            "status": "Draft",
            "transport": "1500",
            "discount": "0",
            "notes": "Test",
            "items": [{
                "category": "Sliding Window",
                "style": "2 Track",
                "width_mm": "1200",
                "height_mm": "1200",
                "sft": "11.56",
                "quantity": 1,
                "total_sft": "11.56",
                "rate_per_sft": "850",
                "amount": "9826",
                "location": "Hall"
            }]
        }
        quote = client.post("/api/quotations", json=payload)
        assert quote.status_code == 201, quote.text
        invoice = client.post(f"/api/quotations/{quote.json()['id']}/convert")
        assert invoice.status_code == 200, invoice.text
        invoice_json = invoice.json()
        amount = Decimal(invoice_json["pending_balance"]) / 2
        payment = client.post(f"/api/invoices/{invoice_json['id']}/payments", json={"payment_date": "2026-07-14", "mode": "UPI", "reference_number": "TEST123", "amount": str(amount), "received_by": "Admin", "notes": "Test payment"})
        assert payment.status_code == 201, payment.text
        assert payment.json()["status"] == "Partially Paid"


def test_prebuilt_frontend_is_served():
    with TestClient(app) as client:
        root = client.get("/")
        assert root.status_code == 200
        assert "<div id=\"root\"></div>" in root.text
        nested = client.get("/customers")
        assert nested.status_code == 200
        assert "<div id=\"root\"></div>" in nested.text
        assert client.get("/api/not-a-real-endpoint").status_code == 404
