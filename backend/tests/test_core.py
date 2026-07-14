import os
from decimal import Decimal
from pathlib import Path

DB_FILE = Path(__file__).resolve().parents[1] / "test_upvc.db"
if DB_FILE.exists():
    DB_FILE.unlink()
os.environ["DATABASE_URL"] = f"sqlite:///{DB_FILE}"

from fastapi.testclient import TestClient
from app import models
from app.database import SessionLocal
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


def test_customer_profile_and_extended_fields():
    with TestClient(app) as client:
        customers = client.get("/api/customers").json()
        assert customers
        customer = customers[0]
        payload = {
            **{key: customer[key] for key in [
                "name", "phone", "email", "address", "project_site", "status",
                "quote_value", "pending_payment", "assigned_to",
            ]},
            "gst_number": "27AAACG1234A1Z5",
            "notes": "Phase 2 profile test note",
            "last_interaction": customer["last_interaction"],
            "next_followup": customer["next_followup"],
        }
        updated = client.put(f"/api/customers/{customer['id']}", json=payload)
        assert updated.status_code == 200, updated.text
        assert updated.json()["gst_number"] == "27AAACG1234A1Z5"
        assert updated.json()["notes"] == "Phase 2 profile test note"

        profile = client.get(f"/api/customers/{customer['id']}/profile")
        assert profile.status_code == 200, profile.text
        data = profile.json()
        assert data["customer"]["id"] == customer["id"]
        assert "quotation_count" in data["metrics"]
        assert "pending_amount" in data["metrics"]
        assert isinstance(data["timeline"], list)
        assert data["timeline"]


def test_catalog_price_master_drives_quotation_item():
    with TestClient(app) as client:
        catalog_payload = {
            "category": "Windows",
            "product_type": "Sliding",
            "name": "Phase 3 Sliding Test",
            "subtitle": "2 Track",
            "profile_brand": "VEKA",
            "profile_series": "Euroline 60 mm",
            "profile": "VEKA 60 mm",
            "track": "2 Track",
            "glass_type": "Clear Toughened",
            "glass_thickness": "5 mm",
            "glass_color": "Clear",
            "glass": "5 MM Saint Gobain",
            "hardware": "McCoy",
            "reinforcement": "1.5 mm GI",
            "mesh": "SS Mesh",
            "color": "White",
            "min_billable_sft": "20",
            "rate_per_sft": "1000",
            "gst_percent": "18",
            "installation_rate": "120",
            "rounding_rule": "Round up",
            "status": "Active",
        }
        catalog = client.post("/api/catalog", json=catalog_payload)
        assert catalog.status_code == 201, catalog.text
        catalog_item = catalog.json()

        customers = client.get("/api/customers").json()
        payload = {
            "customer_id": customers[0]["id"],
            "quotation_date": "2026-07-14",
            "validity_days": 30,
            "sales_person": "Arun Verma",
            "site_location": "Phase 3 Site",
            "address": "Phase 3 Address",
            "status": "Draft",
            "transport": "0",
            "discount": "0",
            "notes": "Catalog linked item",
            "items": [{
                "catalog_item_id": catalog_item["id"],
                "category": catalog_item["name"],
                "style": catalog_item["product_type"],
                "width_mm": "600",
                "height_mm": "600",
                "sft": "3.88",
                "quantity": 1,
                "total_sft": "0",
                "rate_per_sft": "0",
                "amount": "0",
                "location": "Kitchen"
            }]
        }
        quote = client.post("/api/quotations", json=payload)
        assert quote.status_code == 201, quote.text
        item = quote.json()["items"][0]
        assert item["catalog_item_id"] == catalog_item["id"]
        assert Decimal(item["total_sft"]) == Decimal("20.00")
        assert Decimal(item["rate_per_sft"]) == Decimal("1000.00")
        assert Decimal(item["amount"]) == Decimal("20000.00")
        assert item["profile"] == "VEKA 60 mm"
        assert item["mesh"] == "SS Mesh"


def test_quotation_edit_duplicate_revise_and_lock():
    with TestClient(app) as client:
        customers = client.get("/api/customers").json()
        payload = {
            "customer_id": customers[0]["id"],
            "quotation_date": "2026-07-14",
            "validity_days": 30,
            "sales_person": "Arun Verma",
            "site_location": "Editable Site",
            "address": "Editable Address",
            "status": "Draft",
            "transport": "500",
            "discount": "0",
            "notes": "Editable quote",
            "items": [{
                "category": "Sliding Window",
                "style": "2 Track",
                "width_mm": "1000",
                "height_mm": "1000",
                "sft": "10.76",
                "quantity": 1,
                "total_sft": "10.76",
                "rate_per_sft": "800",
                "amount": "8608",
                "location": "Hall"
            }]
        }
        quote = client.post("/api/quotations", json=payload)
        assert quote.status_code == 201, quote.text
        quote_id = quote.json()["id"]

        edited_payload = {**payload, "site_location": "Edited Site", "transport": "1000"}
        edited = client.put(f"/api/quotations/{quote_id}", json=edited_payload)
        assert edited.status_code == 200, edited.text
        assert edited.json()["site_location"] == "Edited Site"
        assert edited.json()["transport"] == "1000.00"

        duplicate = client.post(f"/api/quotations/{quote_id}/duplicate")
        assert duplicate.status_code == 201, duplicate.text
        assert duplicate.json()["id"] != quote_id
        assert duplicate.json()["status"] == "Draft"
        assert duplicate.json()["number"] != edited.json()["number"]

        accepted = client.put(f"/api/quotations/{quote_id}/status", params={"status": "Accepted"})
        assert accepted.status_code == 200, accepted.text
        locked = client.put(f"/api/quotations/{quote_id}", json=edited_payload)
        assert locked.status_code == 409

        revision = client.post(f"/api/quotations/{quote_id}/revise")
        assert revision.status_code == 201, revision.text
        assert revision.json()["status"] == "Draft"
        assert "Revision of" in revision.json()["notes"]


def test_quotation_pdf_download():
    with TestClient(app) as client:
        customers = client.get("/api/customers").json()
        payload = {
            "customer_id": customers[0]["id"],
            "quotation_date": "2026-07-14",
            "validity_days": 30,
            "sales_person": "Arun Verma",
            "site_location": "PDF Site",
            "address": "PDF Address",
            "status": "Sent",
            "transport": "1000",
            "discount": "250",
            "notes": "PDF quotation test",
            "items": [{
                "category": "Casement Window",
                "style": "Openable",
                "width_mm": "900",
                "height_mm": "1200",
                "sft": "11.63",
                "quantity": 2,
                "total_sft": "23.26",
                "rate_per_sft": "950",
                "amount": "22097",
                "location": "Bedroom",
                "profile": "60 mm profile",
                "glass": "5 mm clear",
                "hardware": "Standard hardware"
            }]
        }
        quote = client.post("/api/quotations", json=payload)
        assert quote.status_code == 201, quote.text
        pdf = client.get(f"/api/quotations/{quote.json()['id']}/pdf")
        assert pdf.status_code == 200, pdf.text
        assert pdf.headers["content-type"] == "application/pdf"
        assert quote.json()["number"] in pdf.headers["content-disposition"]
        assert pdf.content.startswith(b"%PDF")


def test_payment_receipt_pdf_and_cancelled_invoice_guard():
    with TestClient(app) as client:
        customers = client.get("/api/customers").json()
        payload = {
            "customer_id": customers[0]["id"],
            "quotation_date": "2026-07-14",
            "validity_days": 30,
            "sales_person": "Arun Verma",
            "site_location": "Receipt Site",
            "address": "Receipt Address",
            "status": "Sent",
            "transport": "0",
            "discount": "0",
            "notes": "Receipt flow",
            "items": [{
                "category": "Sliding Door",
                "style": "2 Track",
                "width_mm": "1200",
                "height_mm": "2100",
                "sft": "27.13",
                "quantity": 1,
                "total_sft": "27.13",
                "rate_per_sft": "1100",
                "amount": "29843",
                "location": "Balcony"
            }]
        }
        quote = client.post("/api/quotations", json=payload)
        assert quote.status_code == 201, quote.text
        invoice = client.post(f"/api/quotations/{quote.json()['id']}/convert")
        assert invoice.status_code == 200, invoice.text
        invoice_json = invoice.json()

        payment = client.post(
            f"/api/invoices/{invoice_json['id']}/payments",
            json={
                "payment_date": "2026-07-14",
                "mode": "NEFT",
                "reference_number": "RCPT-001",
                "amount": "1000",
                "received_by": "Admin",
                "notes": "Receipt test payment",
            },
        )
        assert payment.status_code == 201, payment.text
        payment_id = payment.json()["payments"][0]["id"]
        detail = client.get(f"/api/payments/{payment_id}")
        assert detail.status_code == 200, detail.text
        assert detail.json()["reference_number"] == "RCPT-001"
        receipt = client.get(f"/api/payments/{payment_id}/receipt")
        assert receipt.status_code == 200, receipt.text
        assert receipt.headers["content-type"] == "application/pdf"
        assert "Receipt-" in receipt.headers["content-disposition"]
        assert receipt.content.startswith(b"%PDF")

        with SessionLocal() as db:
            cancelled_invoice = db.get(models.Invoice, invoice_json["id"])
            cancelled_invoice.status = "Cancelled"
            db.commit()

        cancelled_payment = client.post(
            f"/api/invoices/{invoice_json['id']}/payments",
            json={
                "payment_date": "2026-07-14",
                "mode": "Cash",
                "reference_number": "CANCELLED",
                "amount": "10",
                "received_by": "Admin",
                "notes": "Should fail",
            },
        )
        assert cancelled_payment.status_code == 400
        assert "cancelled invoice" in cancelled_payment.json()["detail"].lower()


def test_reports_include_collection_and_conversion_breakdowns():
    with TestClient(app) as client:
        report = client.get("/api/reports")
        assert report.status_code == 200, report.text
        data = report.json()
        assert "monthly" in data
        assert len(data["monthly"]) == 12
        assert {"month", "quotation_value", "invoice_value", "received", "pending"} <= set(data["monthly"][0])
        assert "aging" in data
        assert {row["bucket"] for row in data["aging"]} == {"Current", "1-30 Days", "31-60 Days", "60+ Days"}
        assert "top_pending" in data
        assert "salesperson_summary" in data
        assert data["salesperson_summary"]
        assert "conversion_summary" in data
        assert {"quotation_count", "converted_count", "open_count", "conversion_rate"} <= set(data["conversion_summary"])


def test_prebuilt_frontend_is_served():
    with TestClient(app) as client:
        root = client.get("/")
        assert root.status_code == 200
        assert "<div id=\"root\"></div>" in root.text
        nested = client.get("/customers")
        assert nested.status_code == 200
        assert "<div id=\"root\"></div>" in nested.text
        assert client.get("/api/not-a-real-endpoint").status_code == 404
