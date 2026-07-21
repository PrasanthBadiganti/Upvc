import csv
import io
import os
import xml.etree.ElementTree as ET
from decimal import Decimal
from pathlib import Path
from io import BytesIO

DB_FILE = Path(__file__).resolve().parents[1] / "test_upvc.db"
if DB_FILE.exists():
    DB_FILE.unlink()
os.environ["DATABASE_URL"] = f"sqlite:///{DB_FILE}"

from fastapi.testclient import TestClient
from PIL import Image
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


def test_invoice_cancel_reopen_and_force_rules():
    with TestClient(app) as client:
        customers = client.get("/api/customers").json()
        payload = {
            "customer_id": customers[0]["id"],
            "quotation_date": "2026-07-14",
            "validity_days": 30,
            "sales_person": "Arun Verma",
            "site_location": "Lifecycle Site",
            "address": "Lifecycle Address",
            "status": "Sent",
            "transport": "0",
            "discount": "0",
            "notes": "Lifecycle flow",
            "items": [{
                "category": "Fixed Glass",
                "style": "Fixed",
                "width_mm": "1000",
                "height_mm": "1000",
                "sft": "10.76",
                "quantity": 1,
                "total_sft": "10.76",
                "rate_per_sft": "700",
                "amount": "7532",
                "location": "Study"
            }]
        }
        quote = client.post("/api/quotations", json=payload)
        assert quote.status_code == 201, quote.text
        invoice = client.post(f"/api/quotations/{quote.json()['id']}/convert")
        assert invoice.status_code == 200, invoice.text
        invoice_id = invoice.json()["id"]

        cancelled = client.post(f"/api/invoices/{invoice_id}/cancel")
        assert cancelled.status_code == 200, cancelled.text
        assert cancelled.json()["status"] == "Cancelled"
        blocked = client.post(f"/api/invoices/{invoice_id}/payments", json={"payment_date": "2026-07-14", "mode": "Cash", "reference_number": "BLOCKED", "amount": "10", "received_by": "Admin", "notes": ""})
        assert blocked.status_code == 400
        assert "cancelled invoice" in blocked.json()["detail"].lower()

        reopened = client.post(f"/api/invoices/{invoice_id}/reopen")
        assert reopened.status_code == 200, reopened.text
        assert reopened.json()["status"] == "Unpaid"

        paid = client.post(f"/api/invoices/{invoice_id}/payments", json={"payment_date": "2026-07-14", "mode": "UPI", "reference_number": "FULL", "amount": reopened.json()["pending_balance"], "received_by": "Admin", "notes": ""})
        assert paid.status_code == 201, paid.text
        assert paid.json()["status"] == "Paid"
        no_force = client.post(f"/api/invoices/{invoice_id}/cancel")
        assert no_force.status_code == 400
        forced = client.post(f"/api/invoices/{invoice_id}/cancel", params={"force": "true"})
        assert forced.status_code == 200, forced.text
        assert forced.json()["status"] == "Cancelled"


def test_business_settings_drive_document_generation():
    with TestClient(app) as client:
        settings = client.get("/api/business-settings")
        assert settings.status_code == 200, settings.text
        payload = {**settings.json(), "company_name": "Astra Glaze Systems", "logo_text": "AG", "upi_id": "astra@upi"}
        payload.pop("id", None)
        payload.pop("updated_at", None)
        saved = client.put("/api/business-settings", json=payload)
        assert saved.status_code == 200, saved.text
        assert saved.json()["company_name"] == "Astra Glaze Systems"

        customers = client.get("/api/customers").json()
        quote_payload = {
            "customer_id": customers[0]["id"],
            "quotation_date": "2026-07-14",
            "validity_days": 30,
            "sales_person": "Arun Verma",
            "site_location": "Settings PDF Site",
            "address": "Settings PDF Address",
            "status": "Sent",
            "transport": "0",
            "discount": "0",
            "notes": "Settings PDF test",
            "items": [{
                "category": "Sliding Window",
                "style": "2 Track",
                "width_mm": "1000",
                "height_mm": "1000",
                "sft": "10.76",
                "quantity": 1,
                "total_sft": "10.76",
                "rate_per_sft": "900",
                "amount": "9684",
                "location": "Hall"
            }]
        }
        quote = client.post("/api/quotations", json=quote_payload)
        assert quote.status_code == 201, quote.text
        quote_pdf = client.get(f"/api/quotations/{quote.json()['id']}/pdf")
        assert quote_pdf.status_code == 200, quote_pdf.text
        assert quote_pdf.content.startswith(b"%PDF")

        invoice = client.post(f"/api/quotations/{quote.json()['id']}/convert")
        assert invoice.status_code == 200, invoice.text
        invoice_pdf = client.get(f"/api/invoices/{invoice.json()['id']}/pdf")
        assert invoice_pdf.status_code == 200, invoice_pdf.text
        assert invoice_pdf.content.startswith(b"%PDF")

        payment = client.post(
            f"/api/invoices/{invoice.json()['id']}/payments",
            json={"payment_date": "2026-07-14", "mode": "UPI", "reference_number": "SETTINGS-PDF", "amount": "500", "received_by": "Admin", "notes": "Receipt"},
        )
        assert payment.status_code == 201, payment.text
        receipt = client.get(f"/api/payments/{payment.json()['payments'][0]['id']}/receipt")
        assert receipt.status_code == 200, receipt.text
        assert receipt.content.startswith(b"%PDF")


def test_business_logo_upload_preview_pdf_and_remove():
    with TestClient(app) as client:
        image_bytes = BytesIO()
        Image.new("RGB", (80, 40), color=(37, 99, 235)).save(image_bytes, format="PNG")
        upload = client.post(
            "/api/business-settings/logo",
            files={"file": ("logo.png", image_bytes.getvalue(), "image/png")},
        )
        assert upload.status_code == 200, upload.text
        logo_path = upload.json()["logo_path"]
        assert logo_path.startswith("/uploads/")
        preview = client.get(logo_path)
        assert preview.status_code == 200
        assert preview.headers["content-type"] == "image/png"

        quotes = client.get("/api/quotations").json()
        assert quotes
        pdf = client.get(f"/api/quotations/{quotes[0]['id']}/pdf")
        assert pdf.status_code == 200, pdf.text
        assert pdf.content.startswith(b"%PDF")

        removed = client.delete("/api/business-settings/logo")
        assert removed.status_code == 200, removed.text
        assert removed.json()["logo_path"] == ""
        assert client.get(logo_path).status_code == 404


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


def _create_paid_invoice(client, hsn_code="3925.20.00"):
    customers = client.get("/api/customers").json()
    payload = {
        "customer_id": customers[0]["id"],
        "quotation_date": "2026-07-14",
        "validity_days": 30,
        "sales_person": "Arun Verma",
        "site_location": "CN/DN Site",
        "address": "CN/DN Address",
        "status": "Sent",
        "transport": "0",
        "discount": "0",
        "notes": "Credit/Debit note test",
        "items": [{
            "category": "Sliding Window",
            "style": "2 Track",
            "width_mm": "1200",
            "height_mm": "1200",
            "sft": "11.56",
            "quantity": 1,
            "total_sft": "11.56",
            "rate_per_sft": "1000",
            "amount": "11560",
            "hsn_code": hsn_code,
            "location": "Hall",
        }],
    }
    quote = client.post("/api/quotations", json=payload)
    assert quote.status_code == 201, quote.text
    invoice = client.post(f"/api/quotations/{quote.json()['id']}/convert")
    assert invoice.status_code == 200, invoice.text
    return invoice.json()


def test_hsn_code_flows_from_catalog_through_invoice_pdf():
    with TestClient(app) as client:
        invoice = _create_paid_invoice(client, hsn_code="3925.20.00")
        assert invoice["items"][0]["hsn_code"] == "3925.20.00"
        pdf = client.get(f"/api/invoices/{invoice['id']}/pdf")
        assert pdf.status_code == 200, pdf.text
        assert pdf.content.startswith(b"%PDF")


def test_credit_note_reduces_balance_and_can_be_cancelled():
    with TestClient(app) as client:
        invoice = _create_paid_invoice(client)
        pending_before = Decimal(invoice["pending_balance"])
        customer_before = Decimal(client.get(f"/api/customers/{invoice['customer_id']}/profile").json()["customer"]["pending_payment"])

        cn_payload = {
            "note_date": "2026-07-15",
            "reason": "Damaged panel returned",
            "items": [{
                "description": "Sliding Window return",
                "category": "Sliding Window",
                "hsn_code": "3925.20.00",
                "unit": "Sq. Ft.",
                "quantity": "1",
                "rate": "1000",
                "gst_percent": "18",
                "amount": "1000",
            }],
        }
        cn = client.post(f"/api/invoices/{invoice['id']}/credit-notes", json=cn_payload)
        assert cn.status_code == 201, cn.text
        cn_json = cn.json()
        assert cn_json["number"].startswith("CN-")
        assert cn_json["status"] == "Issued"
        expected_total = Decimal("1000") * Decimal("1.18")
        assert Decimal(cn_json["grand_total"]) == expected_total.quantize(Decimal("0.01"))

        updated_invoice = client.get(f"/api/invoices/{invoice['id']}").json()
        assert Decimal(updated_invoice["pending_balance"]) == pending_before - Decimal(cn_json["grand_total"])

        customer_after = Decimal(client.get(f"/api/customers/{invoice['customer_id']}/profile").json()["customer"]["pending_payment"])
        assert customer_after == customer_before - Decimal(cn_json["grand_total"])

        pdf = client.get(f"/api/credit-notes/{cn_json['id']}/pdf")
        assert pdf.status_code == 200, pdf.text
        assert pdf.content.startswith(b"%PDF")

        cancelled = client.post(f"/api/credit-notes/{cn_json['id']}/cancel")
        assert cancelled.status_code == 200, cancelled.text
        assert cancelled.json()["status"] == "Cancelled"
        restored_invoice = client.get(f"/api/invoices/{invoice['id']}").json()
        assert Decimal(restored_invoice["pending_balance"]) == pending_before

        # Cancelling twice is a no-op, not an error.
        again = client.post(f"/api/credit-notes/{cn_json['id']}/cancel")
        assert again.status_code == 200, again.text
        assert again.json()["status"] == "Cancelled"


def test_credit_note_cannot_exceed_pending_balance():
    with TestClient(app) as client:
        invoice = _create_paid_invoice(client)
        over_amount = Decimal(invoice["pending_balance"]) + Decimal("1000")
        oversized = client.post(f"/api/invoices/{invoice['id']}/credit-notes", json={
            "note_date": "2026-07-15",
            "reason": "Too much",
            "items": [{"description": "Oversized credit", "quantity": "1", "rate": str(over_amount), "gst_percent": "0"}],
        })
        assert oversized.status_code == 400
        assert "pending balance" in oversized.json()["detail"].lower()


def test_debit_note_increases_balance_and_can_be_cancelled():
    with TestClient(app) as client:
        invoice = _create_paid_invoice(client)
        pending_before = Decimal(invoice["pending_balance"])

        dn = client.post(f"/api/invoices/{invoice['id']}/debit-notes", json={
            "note_date": "2026-07-15",
            "reason": "Undercharged installation",
            "items": [{
                "description": "Installation surcharge",
                "category": "Service",
                "hsn_code": "9954",
                "quantity": "1",
                "rate": "500",
                "gst_percent": "18",
                "amount": "500",
            }],
        })
        assert dn.status_code == 201, dn.text
        dn_json = dn.json()
        assert dn_json["number"].startswith("DN-")

        updated_invoice = client.get(f"/api/invoices/{invoice['id']}").json()
        assert Decimal(updated_invoice["pending_balance"]) == pending_before + Decimal(dn_json["grand_total"])

        pdf = client.get(f"/api/debit-notes/{dn_json['id']}/pdf")
        assert pdf.status_code == 200, pdf.text
        assert pdf.content.startswith(b"%PDF")

        cancelled = client.post(f"/api/debit-notes/{dn_json['id']}/cancel")
        assert cancelled.status_code == 200, cancelled.text
        restored_invoice = client.get(f"/api/invoices/{invoice['id']}").json()
        assert Decimal(restored_invoice["pending_balance"]) == pending_before


def test_credit_and_debit_notes_blocked_on_cancelled_invoice():
    with TestClient(app) as client:
        invoice = _create_paid_invoice(client)
        cancelled = client.post(f"/api/invoices/{invoice['id']}/cancel")
        assert cancelled.status_code == 200, cancelled.text

        cn = client.post(f"/api/invoices/{invoice['id']}/credit-notes", json={
            "note_date": "2026-07-15",
            "reason": "Blocked",
            "items": [{"description": "x", "quantity": "1", "rate": "10", "gst_percent": "0"}],
        })
        assert cn.status_code == 400
        assert "cancelled invoice" in cn.json()["detail"].lower()

        dn = client.post(f"/api/invoices/{invoice['id']}/debit-notes", json={
            "note_date": "2026-07-15",
            "reason": "Blocked",
            "items": [{"description": "x", "quantity": "1", "rate": "10", "gst_percent": "0"}],
        })
        assert dn.status_code == 400
        assert "cancelled invoice" in dn.json()["detail"].lower()


def _create_vendor(client, name="Steelframe Supplies"):
    resp = client.post("/api/vendors", json={
        "name": name,
        "phone": "+91 90000 11111",
        "email": "info@steelframe.example",
        "address": "Industrial Area, Vizianagaram",
        "gst_number": "37AAACS1234A1Z5",
        "status": "Active",
        "notes": "",
    })
    assert resp.status_code == 201, resp.text
    return resp.json()


def _create_purchase_bill(client, vendor_id, hsn_code="3925.20.00"):
    resp = client.post(f"/api/vendors/{vendor_id}/purchase-bills", json={
        "vendor_bill_number": "SF-INV-9001",
        "bill_date": "2026-07-15",
        "due_date": "2026-08-14",
        "notes": "Raw profile stock",
        "items": [{
            "description": "VEKA 60mm profile bundle",
            "category": "Raw Material",
            "hsn_code": hsn_code,
            "unit": "Nos",
            "quantity": "10",
            "rate": "1200",
            "gst_percent": "18",
            "amount": "12000",
        }],
    })
    assert resp.status_code == 201, resp.text
    return resp.json()


def test_vendor_crud():
    with TestClient(app) as client:
        vendor = _create_vendor(client)
        assert vendor["code"].startswith("VEND-")
        assert vendor["status"] == "Active"

        listed = client.get("/api/vendors").json()
        assert any(v["id"] == vendor["id"] for v in listed)

        fetched = client.get(f"/api/vendors/{vendor['id']}")
        assert fetched.status_code == 200, fetched.text

        updated = client.put(f"/api/vendors/{vendor['id']}", json={**vendor, "status": "Inactive"})
        assert updated.status_code == 200, updated.text
        assert updated.json()["status"] == "Inactive"


def test_purchase_bill_create_and_record_payment():
    with TestClient(app) as client:
        vendor = _create_vendor(client, name="Glass Traders Co")
        bill = _create_purchase_bill(client, vendor["id"])
        assert bill["number"].startswith("PB-")
        assert bill["status"] == "Unpaid"
        assert bill["items"][0]["hsn_code"] == "3925.20.00"
        expected_total = Decimal("12000") * Decimal("1.18")
        assert Decimal(bill["grand_total"]) == expected_total.quantize(Decimal("0.01"))

        vendor_after_bill = client.get(f"/api/vendors/{vendor['id']}").json()
        assert Decimal(vendor_after_bill["pending_payment"]) == Decimal(bill["grand_total"])

        partial = Decimal(bill["pending_balance"]) / 2
        payment = client.post(f"/api/purchase-bills/{bill['id']}/payments", json={
            "payment_date": "2026-07-16", "mode": "NEFT", "reference_number": "TXN1", "amount": str(partial), "paid_by": "Admin", "notes": "",
        })
        assert payment.status_code == 201, payment.text
        assert payment.json()["status"] == "Partially Paid"

        pdf = client.get(f"/api/purchase-bills/{bill['id']}/pdf")
        assert pdf.status_code == 200, pdf.text
        assert pdf.content.startswith(b"%PDF")

        overpay = client.post(f"/api/purchase-bills/{bill['id']}/payments", json={
            "payment_date": "2026-07-16", "mode": "NEFT", "reference_number": "TXN2", "amount": str(bill["grand_total"]), "paid_by": "Admin", "notes": "",
        })
        assert overpay.status_code == 400
        assert "pending balance" in overpay.json()["detail"].lower()


def test_purchase_bill_cancel_reopen_and_force_rules():
    with TestClient(app) as client:
        vendor = _create_vendor(client, name="Hardware House")
        bill = _create_purchase_bill(client, vendor["id"])

        cancelled = client.post(f"/api/purchase-bills/{bill['id']}/cancel")
        assert cancelled.status_code == 200, cancelled.text
        assert cancelled.json()["status"] == "Cancelled"

        blocked = client.post(f"/api/purchase-bills/{bill['id']}/payments", json={
            "payment_date": "2026-07-16", "mode": "Cash", "reference_number": "X", "amount": "10", "paid_by": "Admin", "notes": "",
        })
        assert blocked.status_code == 400
        assert "cancelled purchase bill" in blocked.json()["detail"].lower()

        reopened = client.post(f"/api/purchase-bills/{bill['id']}/reopen")
        assert reopened.status_code == 200, reopened.text
        assert reopened.json()["status"] == "Unpaid"

        paid = client.post(f"/api/purchase-bills/{bill['id']}/payments", json={
            "payment_date": "2026-07-16", "mode": "NEFT", "reference_number": "FULL", "amount": reopened.json()["pending_balance"], "paid_by": "Admin", "notes": "",
        })
        assert paid.status_code == 201, paid.text
        assert paid.json()["status"] == "Paid"

        no_force = client.post(f"/api/purchase-bills/{bill['id']}/cancel")
        assert no_force.status_code == 400
        forced = client.post(f"/api/purchase-bills/{bill['id']}/cancel", params={"force": "true"})
        assert forced.status_code == 200, forced.text
        assert forced.json()["status"] == "Cancelled"


def test_expense_crud():
    with TestClient(app) as client:
        vendor = _create_vendor(client, name="City Fuel Station")
        created = client.post("/api/expenses", json={
            "expense_date": "2026-07-16",
            "category": "Transport",
            "description": "Diesel for delivery van",
            "amount": "2000",
            "gst_percent": "18",
            "vendor_id": vendor["id"],
            "mode": "Cash",
            "reference_number": "",
            "notes": "",
        })
        assert created.status_code == 201, created.text
        expense = created.json()
        assert Decimal(expense["gst_amount"]) == Decimal("360.00")
        assert Decimal(expense["total"]) == Decimal("2360.00")

        listed = client.get("/api/expenses").json()
        assert any(e["id"] == expense["id"] for e in listed)

        updated = client.put(f"/api/expenses/{expense['id']}", json={**{k: expense[k] for k in ("expense_date", "category", "description", "amount", "gst_percent", "vendor_id", "mode", "reference_number", "notes")}, "amount": "2500"})
        assert updated.status_code == 200, updated.text
        assert Decimal(updated.json()["total"]) == Decimal("2950.00")

        deleted = client.delete(f"/api/expenses/{expense['id']}")
        assert deleted.status_code == 204, deleted.text
        assert not any(e["id"] == expense["id"] for e in client.get("/api/expenses").json())


def _journal_entries_for(client, source_type, source_id):
    entries = client.get("/api/journal").json()
    return [e for e in entries if e["source_type"] == source_type and e["source_id"] == source_id]


def _assert_balanced(entry):
    total_debit = sum(Decimal(line["debit"]) for line in entry["lines"])
    total_credit = sum(Decimal(line["credit"]) for line in entry["lines"])
    assert total_debit == total_credit, entry


def test_chart_of_accounts_seeded():
    with TestClient(app) as client:
        accounts = client.get("/api/accounts").json()
        codes = {a["code"] for a in accounts}
        assert {"1000", "1010", "1100", "1200", "1210", "2000", "2100", "2110", "4000", "4100", "5000"} <= codes


def test_invoice_and_payment_post_balanced_journal_entries():
    with TestClient(app) as client:
        invoice = _create_paid_invoice(client)
        invoice_entries = _journal_entries_for(client, "Invoice", invoice["id"])
        assert len(invoice_entries) == 1
        _assert_balanced(invoice_entries[0])
        ar_line = next(l for l in invoice_entries[0]["lines"] if l["account"]["code"] == "1100")
        assert Decimal(ar_line["debit"]) == Decimal(invoice["grand_total"])

        payment = client.post(f"/api/invoices/{invoice['id']}/payments", json={
            "payment_date": "2026-07-16", "mode": "UPI", "reference_number": "PAYTEST", "amount": "1000", "received_by": "Admin", "notes": "",
        })
        assert payment.status_code == 201, payment.text
        payment_id = payment.json()["payments"][-1]["id"]
        payment_entries = _journal_entries_for(client, "Payment", payment_id)
        assert len(payment_entries) == 1
        _assert_balanced(payment_entries[0])


def test_invoice_cancel_reverses_journal_entry():
    with TestClient(app) as client:
        invoice = _create_paid_invoice(client)
        cancelled = client.post(f"/api/invoices/{invoice['id']}/cancel")
        assert cancelled.status_code == 200, cancelled.text
        reversal_entries = _journal_entries_for(client, "InvoiceCancellation", invoice["id"])
        assert len(reversal_entries) == 1
        _assert_balanced(reversal_entries[0])

        ar_account_id = next(a["id"] for a in client.get("/api/accounts").json() if a["code"] == "1100")
        ar_ledger = client.get(f"/api/accounts/{ar_account_id}/ledger").json()
        net = sum(Decimal(l["debit"]) - Decimal(l["credit"]) for l in ar_ledger if l["entry"]["source_id"] == invoice["id"] and l["entry"]["source_type"] in ("Invoice", "InvoiceCancellation"))
        assert net == Decimal("0.00")


def test_credit_and_debit_note_post_balanced_journal_entries():
    with TestClient(app) as client:
        invoice = _create_paid_invoice(client)
        cn = client.post(f"/api/invoices/{invoice['id']}/credit-notes", json={
            "note_date": "2026-07-15", "reason": "Return",
            "items": [{"description": "x", "quantity": "1", "rate": "1000", "gst_percent": "18"}],
        })
        assert cn.status_code == 201, cn.text
        cn_entries = _journal_entries_for(client, "CreditNote", cn.json()["id"])
        assert len(cn_entries) == 1
        _assert_balanced(cn_entries[0])

        dn = client.post(f"/api/invoices/{invoice['id']}/debit-notes", json={
            "note_date": "2026-07-15", "reason": "Undercharge",
            "items": [{"description": "x", "quantity": "1", "rate": "500", "gst_percent": "18"}],
        })
        assert dn.status_code == 201, dn.text
        dn_entries = _journal_entries_for(client, "DebitNote", dn.json()["id"])
        assert len(dn_entries) == 1
        _assert_balanced(dn_entries[0])


def test_purchase_bill_and_vendor_payment_post_balanced_journal_entries():
    with TestClient(app) as client:
        vendor = _create_vendor(client, name="Ledger Test Vendor")
        bill = _create_purchase_bill(client, vendor["id"])
        bill_entries = _journal_entries_for(client, "PurchaseBill", bill["id"])
        assert len(bill_entries) == 1
        _assert_balanced(bill_entries[0])

        payment = client.post(f"/api/purchase-bills/{bill['id']}/payments", json={
            "payment_date": "2026-07-16", "mode": "Cash", "reference_number": "", "amount": "1000", "paid_by": "Admin", "notes": "",
        })
        assert payment.status_code == 201, payment.text
        payment_id = payment.json()["payments"][-1]["id"]
        payment_entries = _journal_entries_for(client, "VendorPayment", payment_id)
        assert len(payment_entries) == 1
        _assert_balanced(payment_entries[0])

        cancelled = client.post(f"/api/purchase-bills/{bill['id']}/cancel", params={"force": "true"})
        assert cancelled.status_code == 200, cancelled.text
        cancel_entries = _journal_entries_for(client, "PurchaseBillCancellation", bill["id"])
        assert len(cancel_entries) == 1
        _assert_balanced(cancel_entries[0])


def test_expense_journal_entry_follows_edits():
    with TestClient(app) as client:
        created = client.post("/api/expenses", json={
            "expense_date": "2026-07-16", "category": "Marketing", "description": "Banner printing",
            "amount": "1000", "gst_percent": "18", "vendor_id": None, "mode": "Cash", "reference_number": "", "notes": "",
        })
        assert created.status_code == 201, created.text
        expense = created.json()
        entries = _journal_entries_for(client, "Expense", expense["id"])
        assert len(entries) == 1
        _assert_balanced(entries[0])
        assert any(l["account"]["code"] == "5150" for l in entries[0]["lines"])

        updated = client.put(f"/api/expenses/{expense['id']}", json={
            "expense_date": "2026-07-16", "category": "Rent", "description": "Corrected to rent",
            "amount": "1000", "gst_percent": "18", "vendor_id": None, "mode": "Cash", "reference_number": "", "notes": "",
        })
        assert updated.status_code == 200, updated.text
        entries_after_update = _journal_entries_for(client, "Expense", expense["id"])
        assert len(entries_after_update) == 1
        _assert_balanced(entries_after_update[0])
        assert any(l["account"]["code"] == "5100" for l in entries_after_update[0]["lines"])

        deleted = client.delete(f"/api/expenses/{expense['id']}")
        assert deleted.status_code == 204, deleted.text
        assert not _journal_entries_for(client, "Expense", expense["id"])


def test_trial_balance_is_balanced():
    with TestClient(app) as client:
        invoice = _create_paid_invoice(client)
        client.post(f"/api/invoices/{invoice['id']}/payments", json={
            "payment_date": "2026-07-16", "mode": "UPI", "reference_number": "TB1", "amount": "2000", "received_by": "Admin", "notes": "",
        })
        vendor = _create_vendor(client, name="Trial Balance Vendor")
        _create_purchase_bill(client, vendor["id"])
        client.post("/api/expenses", json={
            "expense_date": "2026-07-16", "category": "Utilities", "description": "Power bill",
            "amount": "500", "gst_percent": "0", "vendor_id": None, "mode": "Cash", "reference_number": "", "notes": "",
        })

        rows = client.get("/api/trial-balance").json()
        assert rows
        total_debit = sum(Decimal(r["debit"]) for r in rows)
        total_credit = sum(Decimal(r["credit"]) for r in rows)
        assert total_debit == total_credit


PERIOD = {"from_date": "2026-01-01", "to_date": "2026-12-31"}


def test_gstr1_report_b2b_and_hsn():
    with TestClient(app) as client:
        invoice = _create_paid_invoice(client, hsn_code="3925.20.00")
        gstr1 = client.get("/api/gst/gstr1", params=PERIOD)
        assert gstr1.status_code == 200, gstr1.text
        data = gstr1.json()
        b2b_row = next((r for r in data["b2b"] if r["invoice_number"] == invoice["number"]), None)
        assert b2b_row is not None, data["b2b"]
        assert Decimal(str(b2b_row["cgst"])) == Decimal(invoice["cgst"])
        assert Decimal(str(b2b_row["sgst"])) == Decimal(invoice["sgst"])
        hsn_row = next((r for r in data["hsn_summary"] if r["hsn_code"] == "3925.20.00"), None)
        assert hsn_row is not None, data["hsn_summary"]
        assert hsn_row["taxable_value"] > 0


def test_gstr3b_report_reflects_ledger():
    with TestClient(app) as client:
        invoice = _create_paid_invoice(client)
        vendor = _create_vendor(client, name="GSTR3B Vendor")
        _create_purchase_bill(client, vendor["id"])

        gstr3b = client.get("/api/gst/gstr3b", params=PERIOD)
        assert gstr3b.status_code == 200, gstr3b.text
        data = gstr3b.json()
        assert data["outward_taxable_supplies"]["cgst"] >= float(invoice["cgst"])
        assert data["eligible_itc"]["total_itc"] > 0
        expected_net_cgst = max(0.0, data["outward_taxable_supplies"]["cgst"] - data["eligible_itc"]["cgst"])
        assert abs(data["net_tax_payable"]["cgst"] - expected_net_cgst) < 0.01


def test_hsn_summary_nets_credit_note():
    with TestClient(app) as client:
        invoice = _create_paid_invoice(client, hsn_code="7005.29.00")
        before = client.get("/api/gst/hsn-summary", params=PERIOD).json()
        before_row = next(r for r in before if r["hsn_code"] == "7005.29.00")

        client.post(f"/api/invoices/{invoice['id']}/credit-notes", json={
            "note_date": "2026-07-15", "reason": "Return",
            "items": [{"description": "x", "hsn_code": "7005.29.00", "quantity": "1", "rate": "1000", "gst_percent": "18"}],
        })
        after = client.get("/api/gst/hsn-summary", params=PERIOD).json()
        after_row = next(r for r in after if r["hsn_code"] == "7005.29.00")
        assert after_row["taxable_value"] == before_row["taxable_value"] - 1000


def test_sales_and_purchase_register_csv():
    with TestClient(app) as client:
        _create_paid_invoice(client)
        vendor = _create_vendor(client, name="Register CSV Vendor")
        _create_purchase_bill(client, vendor["id"])

        sales_csv = client.get("/api/gst/sales-register/csv", params=PERIOD)
        assert sales_csv.status_code == 200, sales_csv.text
        assert sales_csv.headers["content-type"].startswith("text/csv")
        sales_rows = list(csv.DictReader(io.StringIO(sales_csv.text)))
        assert sales_rows

        purchase_csv = client.get("/api/gst/purchase-register/csv", params=PERIOD)
        assert purchase_csv.status_code == 200, purchase_csv.text
        purchase_rows = list(csv.DictReader(io.StringIO(purchase_csv.text)))
        assert purchase_rows


def test_profit_and_loss_and_balance_sheet():
    with TestClient(app) as client:
        invoice = _create_paid_invoice(client)
        client.post(f"/api/invoices/{invoice['id']}/payments", json={
            "payment_date": "2026-07-16", "mode": "UPI", "reference_number": "PNL1", "amount": "3000", "received_by": "Admin", "notes": "",
        })
        client.post("/api/expenses", json={
            "expense_date": "2026-07-16", "category": "Rent", "description": "Office rent",
            "amount": "1000", "gst_percent": "0", "vendor_id": None, "mode": "Cash", "reference_number": "", "notes": "",
        })

        pnl = client.get("/api/profit-and-loss", params=PERIOD)
        assert pnl.status_code == 200, pnl.text
        pnl_data = pnl.json()
        assert pnl_data["total_income"] > 0
        assert pnl_data["total_expense"] > 0
        assert abs(pnl_data["net_profit"] - (pnl_data["total_income"] - pnl_data["total_expense"])) < 0.01

        bs = client.get("/api/balance-sheet", params={"as_of": "2026-12-31"})
        assert bs.status_code == 200, bs.text
        bs_data = bs.json()
        assert bs_data["balanced"] is True
        assert abs(bs_data["total_assets"] - (bs_data["total_liabilities"] + bs_data["total_equity"])) < 0.01


def test_tally_export_masters_and_vouchers_are_well_formed():
    with TestClient(app) as client:
        _create_paid_invoice(client)
        vendor = _create_vendor(client, name="Tally Vendor")
        _create_purchase_bill(client, vendor["id"])

        masters = client.get("/api/tally/export/masters")
        assert masters.status_code == 200, masters.text
        assert masters.headers["content-type"].startswith("application/xml")
        masters_root = ET.fromstring(masters.content)
        ledger_names = {ledger.get("NAME") for ledger in masters_root.iter("LEDGER")}
        assert "Cash" in ledger_names
        assert "Sales Revenue" in ledger_names
        assert any("Tally Vendor" in name for name in ledger_names)

        vouchers = client.get("/api/tally/export/vouchers", params=PERIOD)
        assert vouchers.status_code == 200, vouchers.text
        vouchers_root = ET.fromstring(vouchers.content)
        voucher_elements = list(vouchers_root.iter("VOUCHER"))
        assert voucher_elements
        for voucher in voucher_elements:
            total = Decimal("0")
            for entry in voucher.findall("ALLLEDGERENTRIES.LIST"):
                total += Decimal(entry.findtext("AMOUNT"))
            assert total == Decimal("0.00"), ET.tostring(voucher, encoding="unicode")


def test_customer_csv_import_preview_and_commit():
    with TestClient(app) as client:
        existing = client.get("/api/customers").json()[0]
        csv_bytes = (
            "name,phone,email,gst_number\n"
            f"{existing['name']} Duplicate,{existing['phone']},,\n"
            "Brand New Customer,+91 90000 55555,newcustomer@example.com,\n"
        ).encode("utf-8")

        preview = client.post("/api/customers/import/preview", files={"file": ("customers.csv", csv_bytes, "text/csv")})
        assert preview.status_code == 200, preview.text
        rows = preview.json()
        assert len(rows) == 2
        dup_row = next(r for r in rows if r["row"]["name"].endswith("Duplicate"))
        new_row = next(r for r in rows if r["row"]["name"] == "Brand New Customer")
        assert dup_row["status"] == "duplicate"
        assert dup_row["matched_id"] == existing["id"]
        assert new_row["status"] == "new"

        before_count = len(client.get("/api/customers").json())
        commit = client.post("/api/customers/import/commit", json={"rows": [new_row["row"]]})
        assert commit.status_code == 200, commit.text
        assert commit.json()["created"] == 1
        after = client.get("/api/customers").json()
        assert len(after) == before_count + 1
        assert any(c["name"] == "Brand New Customer" and c["email"] == "newcustomer@example.com" for c in after)


def test_vendor_csv_import_preview_and_commit():
    with TestClient(app) as client:
        created = client.post("/api/vendors", json={
            "name": "Import Match Vendor", "phone": "+91 90000 77777", "email": "", "address": "",
            "gst_number": "27UNIQUEIMPORTV1Z1", "status": "Active", "pending_payment": 0, "notes": "",
        })
        assert created.status_code == 201, created.text
        existing = created.json()
        csv_bytes = (
            "name,phone,email,gst_number,address,notes\n"
            f"Some Other Name,,,{existing['gst_number']},,\n"
            "Brand New Vendor,+91 90000 66666,newvendor@example.com,,Vendor Street,Imported\n"
        ).encode("utf-8")

        preview = client.post("/api/vendors/import/preview", files={"file": ("vendors.csv", csv_bytes, "text/csv")})
        assert preview.status_code == 200, preview.text
        rows = preview.json()
        dup_row = next(r for r in rows if r["row"]["name"] == "Some Other Name")
        new_row = next(r for r in rows if r["row"]["name"] == "Brand New Vendor")
        assert dup_row["status"] == "duplicate"
        assert dup_row["matched_id"] == existing["id"]
        assert new_row["status"] == "new"

        commit = client.post("/api/vendors/import/commit", json={"rows": [new_row["row"]]})
        assert commit.status_code == 200, commit.text
        assert commit.json()["created"] == 1
        vendors = client.get("/api/vendors").json()
        assert any(v["name"] == "Brand New Vendor" and v["email"] == "newvendor@example.com" for v in vendors)


def test_customer_import_rejects_csv_without_name_column():
    with TestClient(app) as client:
        csv_bytes = "phone,email\n+911234,x@example.com\n".encode("utf-8")
        preview = client.post("/api/customers/import/preview", files={"file": ("bad.csv", csv_bytes, "text/csv")})
        assert preview.status_code == 400
        assert "name" in preview.json()["detail"].lower()


def _trial_balance_totals(client):
    rows = client.get("/api/trial-balance").json()
    total_debit = sum(Decimal(str(r["debit"])) for r in rows)
    total_credit = sum(Decimal(str(r["credit"])) for r in rows)
    return total_debit, total_credit


def test_customer_import_with_opening_balance_posts_journal_and_balances():
    with TestClient(app) as client:
        before_debit, before_credit = _trial_balance_totals(client)
        csv_bytes = "name,phone,opening_balance\nMigrated Customer,+91 90000 12121,25000\n".encode("utf-8")
        preview = client.post("/api/customers/import/preview", files={"file": ("customers.csv", csv_bytes, "text/csv")})
        assert preview.status_code == 200, preview.text
        row = preview.json()[0]
        assert row["status"] == "new"

        commit = client.post("/api/customers/import/commit", json={"rows": [row["row"]], "as_of": "2026-04-01"})
        assert commit.status_code == 200, commit.text
        assert commit.json()["created"] == 1

        customers = client.get("/api/customers").json()
        migrated = next(c for c in customers if c["name"] == "Migrated Customer")
        assert Decimal(migrated["pending_payment"]) == Decimal("25000.00")

        all_entries = client.get("/api/journal").json()
        matching = [e for e in all_entries if e["source_type"] == "OpeningBalance" and e["narration"] == "Opening balance for Migrated Customer"]
        assert len(matching) == 1
        _assert_balanced(matching[0])

        after_debit, after_credit = _trial_balance_totals(client)
        assert after_debit == after_credit
        assert after_debit - before_debit == Decimal("25000.00")


def test_opening_balance_csv_resolves_customer_vendor_account_and_unmatched():
    with TestClient(app) as client:
        customers = client.get("/api/customers").json()
        target_customer = customers[0]
        vendor = _create_vendor(client, name="Opening Balance Vendor")

        csv_bytes = (
            "name,debit,credit\n"
            f"{target_customer['name']},18000,0\n"
            f"{vendor['name']},0,9000\n"
            "1010,60000,0\n"
            "Totally Unknown Ledger,500,0\n"
        ).encode("utf-8")
        preview = client.post("/api/opening-balances/preview", files={"file": ("tb.csv", csv_bytes, "text/csv")})
        assert preview.status_code == 200, preview.text
        rows = preview.json()
        by_name = {r["name"]: r for r in rows}
        assert by_name[target_customer["name"]]["match_type"] == "customer"
        assert by_name[target_customer["name"]]["match_id"] == target_customer["id"]
        assert by_name[vendor["name"]]["match_type"] == "vendor"
        assert by_name["1010"]["match_type"] == "account"
        assert by_name["Totally Unknown Ledger"]["match_type"] == "unmatched"

        before_debit, before_credit = _trial_balance_totals(client)
        matched_rows = [r for r in rows if r["match_type"] != "unmatched"]
        commit = client.post("/api/opening-balances/commit", json={"rows": matched_rows, "as_of": "2026-04-01"})
        assert commit.status_code == 200, commit.text
        assert commit.json()["applied"] == 3

        customer_after = client.get(f"/api/customers/{target_customer['id']}/profile").json()["customer"]
        assert Decimal(customer_after["pending_payment"]) == Decimal(target_customer["pending_payment"]) + Decimal("18000.00")
        vendor_after = client.get(f"/api/vendors/{vendor['id']}").json()
        assert Decimal(vendor_after["pending_payment"]) == Decimal(vendor["pending_payment"]) + Decimal("9000.00")

        after_debit, after_credit = _trial_balance_totals(client)
        assert after_debit == after_credit


def test_opening_balance_import_rejects_csv_without_name_column():
    with TestClient(app) as client:
        csv_bytes = "debit,credit\n1000,0\n".encode("utf-8")
        preview = client.post("/api/opening-balances/preview", files={"file": ("bad.csv", csv_bytes, "text/csv")})
        assert preview.status_code == 400


TALLY_LEDGER_MASTERS_XML = """<ENVELOPE>
<BODY>
<IMPORTDATA>
<REQUESTDATA>
<TALLYMESSAGE>
<LEDGER NAME="Tally Test Customer">
<PARENT>Sundry Debtors</PARENT>
<PARTYGSTIN>29ABCDE1234F1Z5</PARTYGSTIN>
<LEDGERPHONE>9998887777</LEDGERPHONE>
<ADDRESS.LIST>
<ADDRESS>123 Test Street</ADDRESS>
<ADDRESS>Bangalore</ADDRESS>
</ADDRESS.LIST>
<OPENINGBALANCE>-15000</OPENINGBALANCE>
</LEDGER>
<LEDGER NAME="Tally Test Vendor">
<PARENT>Sundry Creditors</PARENT>
<OPENINGBALANCE>8000</OPENINGBALANCE>
</LEDGER>
</TALLYMESSAGE>
</REQUESTDATA>
</IMPORTDATA>
</BODY>
</ENVELOPE>"""


def test_tally_ledger_masters_xml_import_customers_and_vendors():
    with TestClient(app) as client:
        xml_bytes = TALLY_LEDGER_MASTERS_XML.encode("utf-8")

        cust_preview = client.post("/api/customers/import/preview", files={"file": ("masters.xml", xml_bytes, "application/xml")})
        assert cust_preview.status_code == 200, cust_preview.text
        cust_rows = cust_preview.json()
        assert len(cust_rows) == 1
        cust_row = cust_rows[0]["row"]
        assert cust_row["name"] == "Tally Test Customer"
        assert cust_row["gst_number"] == "29ABCDE1234F1Z5"
        assert cust_row["phone"] == "9998887777"
        assert cust_row["address"] == "123 Test Street, Bangalore"
        assert cust_row["opening_balance"] == "15000"

        vendor_preview = client.post("/api/vendors/import/preview", files={"file": ("masters.xml", xml_bytes, "application/xml")})
        assert vendor_preview.status_code == 200, vendor_preview.text
        vendor_rows = vendor_preview.json()
        assert len(vendor_rows) == 1
        assert vendor_rows[0]["row"]["name"] == "Tally Test Vendor"
        assert vendor_rows[0]["row"]["opening_balance"] == "8000"

        commit = client.post("/api/customers/import/commit", json={"rows": [cust_row], "as_of": "2026-04-01"})
        assert commit.status_code == 200, commit.text
        created = client.get("/api/customers").json()
        imported = next(c for c in created if c["name"] == "Tally Test Customer")
        assert imported["gst_number"] == "29ABCDE1234F1Z5"
        assert Decimal(imported["pending_payment"]) == Decimal("15000.00")


def _create_customer(client, name, state=""):
    resp = client.post("/api/customers", json={
        "name": name, "phone": "", "email": "", "address": "", "gst_number": "",
        "state": state, "project_site": "", "status": "New", "quote_value": 0,
        "pending_payment": 0, "assigned_to": "Arun Verma", "notes": "",
    })
    assert resp.status_code == 201, resp.text
    return resp.json()


def _create_invoice_for_customer(client, customer_id, hsn_code="3925.20.00"):
    payload = {
        "customer_id": customer_id,
        "quotation_date": "2026-07-14",
        "validity_days": 30,
        "sales_person": "Arun Verma",
        "site_location": "IGST Test Site",
        "address": "IGST Test Address",
        "status": "Sent",
        "transport": "0",
        "discount": "0",
        "notes": "IGST test",
        "items": [{
            "category": "Sliding Window",
            "style": "2 Track",
            "width_mm": "1200",
            "height_mm": "1200",
            "sft": "11.56",
            "quantity": 1,
            "total_sft": "11.56",
            "rate_per_sft": "1000",
            "amount": "11560",
            "hsn_code": hsn_code,
            "location": "Hall",
        }],
    }
    quote = client.post("/api/quotations", json=payload)
    assert quote.status_code == 201, quote.text
    invoice = client.post(f"/api/quotations/{quote.json()['id']}/convert")
    assert invoice.status_code == 200, invoice.text
    return invoice.json()


def test_interstate_invoice_posts_igst_not_cgst_sgst():
    with TestClient(app) as client:
        customer = _create_customer(client, "Karnataka Buyer", state="Karnataka")
        invoice = _create_invoice_for_customer(client, customer["id"])
        assert Decimal(invoice["igst"]) > 0
        assert Decimal(invoice["cgst"]) == 0
        assert Decimal(invoice["sgst"]) == 0

        entries = _journal_entries_for(client, "Invoice", invoice["id"])
        assert len(entries) == 1
        _assert_balanced(entries[0])
        codes = {line["account"]["code"] for line in entries[0]["lines"]}
        assert "2120" in codes
        assert "2100" not in codes and "2110" not in codes


def test_intrastate_invoice_still_posts_cgst_sgst():
    with TestClient(app) as client:
        customer = _create_customer(client, "AP Buyer", state="Andhra Pradesh")
        invoice = _create_invoice_for_customer(client, customer["id"])
        assert Decimal(invoice["cgst"]) > 0
        assert Decimal(invoice["sgst"]) > 0
        assert Decimal(invoice["igst"]) == 0


def test_invoice_with_blank_state_defaults_to_intrastate():
    with TestClient(app) as client:
        customer = _create_customer(client, "No State Buyer", state="")
        invoice = _create_invoice_for_customer(client, customer["id"])
        assert Decimal(invoice["cgst"]) > 0
        assert Decimal(invoice["igst"]) == 0


def test_interstate_purchase_bill_posts_input_igst():
    with TestClient(app) as client:
        vendor_resp = client.post("/api/vendors", json={
            "name": "Maharashtra Vendor", "phone": "", "email": "", "address": "", "gst_number": "",
            "state": "Maharashtra", "status": "Active", "pending_payment": 0, "notes": "",
        })
        assert vendor_resp.status_code == 201, vendor_resp.text
        vendor = vendor_resp.json()
        bill = _create_purchase_bill(client, vendor["id"])
        assert Decimal(bill["igst"]) > 0
        assert Decimal(bill["cgst"]) == 0
        assert Decimal(bill["sgst"]) == 0

        entries = _journal_entries_for(client, "PurchaseBill", bill["id"])
        assert len(entries) == 1
        _assert_balanced(entries[0])
        codes = {line["account"]["code"] for line in entries[0]["lines"]}
        assert "1220" in codes


def test_interstate_credit_note_uses_igst():
    with TestClient(app) as client:
        customer = _create_customer(client, "Telangana Buyer", state="Telangana")
        invoice = _create_invoice_for_customer(client, customer["id"])
        cn = client.post(f"/api/invoices/{invoice['id']}/credit-notes", json={
            "note_date": "2026-07-15", "reason": "Return",
            "items": [{"description": "x", "quantity": "1", "rate": "1000", "gst_percent": "18"}],
        })
        assert cn.status_code == 201, cn.text
        entries = _journal_entries_for(client, "CreditNote", cn.json()["id"])
        assert len(entries) == 1
        _assert_balanced(entries[0])
        codes = {line["account"]["code"] for line in entries[0]["lines"]}
        assert "2120" in codes
        assert "2100" not in codes and "2110" not in codes


def test_gstr3b_includes_igst():
    with TestClient(app) as client:
        customer = _create_customer(client, "Gujarat Buyer", state="Gujarat")
        _create_invoice_for_customer(client, customer["id"])
        gstr3b = client.get("/api/gst/gstr3b", params=PERIOD).json()
        assert gstr3b["outward_taxable_supplies"]["igst"] > 0


def test_gstr1_b2b_reports_igst_for_interstate_invoice():
    with TestClient(app) as client:
        customer = _create_customer(client, "Punjab GST Buyer", state="Punjab")
        client.put(f"/api/customers/{customer['id']}", json={**customer, "gst_number": "03PUNJABGST1Z5"})
        invoice = _create_invoice_for_customer(client, customer["id"])
        gstr1 = client.get("/api/gst/gstr1", params=PERIOD).json()
        row = next(r for r in gstr1["b2b"] if r["invoice_number"] == invoice["number"])
        assert row["igst"] > 0
        assert row["cgst"] == 0
        assert row["sgst"] == 0


def test_trial_balance_balances_with_mixed_igst_and_intrastate():
    with TestClient(app) as client:
        interstate_customer = _create_customer(client, "Rajasthan Buyer", state="Rajasthan")
        intrastate_customer = _create_customer(client, "AP Buyer 2", state="Andhra Pradesh")
        _create_invoice_for_customer(client, interstate_customer["id"])
        _create_invoice_for_customer(client, intrastate_customer["id"])
        total_debit, total_credit = _trial_balance_totals(client)
        assert total_debit == total_credit


def _account_id(client, code):
    accounts = client.get("/api/accounts").json()
    return next(a["id"] for a in accounts if a["code"] == code)


def test_manual_journal_entry_create_and_balance():
    with TestClient(app) as client:
        cash_id = _account_id(client, "1000")
        rent_id = _account_id(client, "5100")
        before_debit, before_credit = _trial_balance_totals(client)

        resp = client.post("/api/journal/manual", json={
            "entry_date": "2026-07-20",
            "narration": "Office rent paid in cash",
            "lines": [
                {"account_id": rent_id, "debit": "5000", "credit": "0"},
                {"account_id": cash_id, "debit": "0", "credit": "5000"},
            ],
        })
        assert resp.status_code == 201, resp.text
        entry = resp.json()
        assert entry["source_type"] == "Manual"
        assert entry["source_id"] is None
        assert entry["narration"] == "Office rent paid in cash"
        _assert_balanced(entry)

        after_debit, after_credit = _trial_balance_totals(client)
        assert after_debit - before_debit == Decimal("5000")
        assert after_credit - before_credit == Decimal("5000")


def test_manual_journal_entry_rejects_unbalanced_lines():
    with TestClient(app) as client:
        cash_id = _account_id(client, "1000")
        rent_id = _account_id(client, "5100")
        resp = client.post("/api/journal/manual", json={
            "entry_date": "2026-07-20",
            "narration": "Unbalanced entry",
            "lines": [
                {"account_id": rent_id, "debit": "5000", "credit": "0"},
                {"account_id": cash_id, "debit": "0", "credit": "4000"},
            ],
        })
        assert resp.status_code == 400
        assert "not balanced" in resp.json()["detail"].lower()


def test_manual_journal_entry_requires_narration():
    with TestClient(app) as client:
        cash_id = _account_id(client, "1000")
        rent_id = _account_id(client, "5100")
        resp = client.post("/api/journal/manual", json={
            "entry_date": "2026-07-20",
            "narration": "   ",
            "lines": [
                {"account_id": rent_id, "debit": "1000", "credit": "0"},
                {"account_id": cash_id, "debit": "0", "credit": "1000"},
            ],
        })
        assert resp.status_code == 400
        assert "narration" in resp.json()["detail"].lower()


def test_manual_journal_entry_requires_two_nonzero_lines():
    with TestClient(app) as client:
        cash_id = _account_id(client, "1000")
        resp = client.post("/api/journal/manual", json={
            "entry_date": "2026-07-20",
            "narration": "Only one line",
            "lines": [
                {"account_id": cash_id, "debit": "1000", "credit": "0"},
            ],
        })
        assert resp.status_code == 400
        assert "two lines" in resp.json()["detail"].lower()


def test_manual_journal_entry_reversal():
    with TestClient(app) as client:
        cash_id = _account_id(client, "1000")
        rent_id = _account_id(client, "5100")
        created = client.post("/api/journal/manual", json={
            "entry_date": "2026-07-20",
            "narration": "Reverse me",
            "lines": [
                {"account_id": rent_id, "debit": "2000", "credit": "0"},
                {"account_id": cash_id, "debit": "0", "credit": "2000"},
            ],
        }).json()

        before_debit, before_credit = _trial_balance_totals(client)
        reversal = client.post(f"/api/journal/{created['id']}/reverse")
        assert reversal.status_code == 200, reversal.text
        reversal_entry = reversal.json()
        assert reversal_entry["source_type"] == "ManualReversal"
        assert reversal_entry["source_id"] == created["id"]
        _assert_balanced(reversal_entry)
        rent_line = next(l for l in reversal_entry["lines"] if l["account"]["code"] == "5100")
        assert Decimal(rent_line["credit"]) == Decimal("2000")

        after_debit, after_credit = _trial_balance_totals(client)
        assert after_debit - before_debit == Decimal("2000")
        assert after_credit - before_credit == Decimal("2000")

        again = client.post(f"/api/journal/{created['id']}/reverse")
        assert again.status_code == 400
        assert "already been reversed" in again.json()["detail"].lower()


def test_manual_journal_entry_reversal_blocked_for_system_entries():
    with TestClient(app) as client:
        invoice = _create_paid_invoice(client)
        invoice_entries = _journal_entries_for(client, "Invoice", invoice["id"])
        resp = client.post(f"/api/journal/{invoice_entries[0]['id']}/reverse")
        assert resp.status_code == 400
        assert "manually created" in resp.json()["detail"].lower()


def _create_fixed_asset(client, **overrides):
    payload = {
        "name": "Edge Banding Machine",
        "category": "Machinery",
        "purchase_date": "2025-01-01",
        "purchase_cost": "120000",
        "salvage_value": "12000",
        "useful_life_years": "6",
        "depreciation_method": "Straight Line",
        "payment_mode": "Bank",
        "location": "Factory Floor 1",
        "notes": "",
    }
    payload.update(overrides)
    resp = client.post("/api/fixed-assets", json=payload)
    assert resp.status_code == 201, resp.text
    return resp.json()


def test_fixed_asset_creation_posts_balanced_acquisition_journal():
    with TestClient(app) as client:
        asset = _create_fixed_asset(client)
        assert asset["code"]
        assert asset["status"] == "Active"
        assert Decimal(asset["accumulated_depreciation"]) == Decimal("0")

        entries = _journal_entries_for(client, "FixedAsset", asset["id"])
        assert len(entries) == 1
        _assert_balanced(entries[0])
        fa_line = next(l for l in entries[0]["lines"] if l["account"]["code"] == "1500")
        bank_line = next(l for l in entries[0]["lines"] if l["account"]["code"] == "1010")
        assert Decimal(fa_line["debit"]) == Decimal("120000.00")
        assert Decimal(bank_line["credit"]) == Decimal("120000.00")


def test_fixed_asset_rejects_salvage_value_greater_than_cost():
    with TestClient(app) as client:
        resp = client.post("/api/fixed-assets", json={
            "name": "Bad Asset", "category": "Other", "purchase_date": "2025-01-01",
            "purchase_cost": "10000", "salvage_value": "15000", "useful_life_years": "5",
            "depreciation_method": "Straight Line", "payment_mode": "Cash",
        })
        assert resp.status_code == 400
        assert "salvage" in resp.json()["detail"].lower()


def test_fixed_asset_purchase_via_vendor_credits_payable():
    with TestClient(app) as client:
        vendor = _create_vendor(client, "Machine Traders")
        asset = _create_fixed_asset(client, vendor_id=vendor["id"])
        entries = _journal_entries_for(client, "FixedAsset", asset["id"])
        payable_line = next(l for l in entries[0]["lines"] if l["account"]["code"] == "2000")
        assert Decimal(payable_line["credit"]) == Decimal("120000.00")

        updated_vendor = client.get(f"/api/vendors/{vendor['id']}").json()
        assert Decimal(updated_vendor["pending_payment"]) == Decimal("120000.00")


def test_straight_line_depreciation_posts_balanced_journal():
    with TestClient(app) as client:
        asset = _create_fixed_asset(client, purchase_cost="120000", salvage_value="12000", useful_life_years="6", depreciation_method="Straight Line")
        resp = client.post(f"/api/fixed-assets/{asset['id']}/depreciate", json={"as_of_date": "2026-01-01"})
        assert resp.status_code == 200, resp.text
        updated = resp.json()
        assert Decimal(updated["accumulated_depreciation"]) == Decimal("18000.00")

        entries = _journal_entries_for(client, "Depreciation", updated["depreciation_entries"][0]["id"])
        assert len(entries) == 1
        _assert_balanced(entries[0])
        expense_line = next(l for l in entries[0]["lines"] if l["account"]["code"] == "5200")
        accum_line = next(l for l in entries[0]["lines"] if l["account"]["code"] == "1590")
        assert Decimal(expense_line["debit"]) == Decimal("18000.00")
        assert Decimal(accum_line["credit"]) == Decimal("18000.00")


def test_written_down_value_depreciation_uses_book_value():
    with TestClient(app) as client:
        asset = _create_fixed_asset(
            client, name="Delivery Van", category="Vehicle", purchase_cost="100000", salvage_value="1000",
            useful_life_years="5", depreciation_method="Written Down Value", depreciation_rate="20",
        )
        resp = client.post(f"/api/fixed-assets/{asset['id']}/depreciate", json={"as_of_date": "2026-01-01"})
        assert resp.status_code == 200, resp.text
        first = resp.json()
        assert Decimal(first["accumulated_depreciation"]) == Decimal("20000.00")

        resp2 = client.post(f"/api/fixed-assets/{asset['id']}/depreciate", json={"as_of_date": "2027-01-01"})
        assert resp2.status_code == 200, resp2.text
        second = resp2.json()
        assert Decimal(second["accumulated_depreciation"]) == Decimal("36000.00")


def test_depreciation_capped_at_salvage_value_and_blocks_when_fully_depreciated():
    with TestClient(app) as client:
        asset = _create_fixed_asset(client, name="Cheap Drill", category="Tools", purchase_cost="10000", salvage_value="9500", useful_life_years="1", depreciation_method="Straight Line")
        resp = client.post(f"/api/fixed-assets/{asset['id']}/depreciate", json={"as_of_date": "2026-01-01"})
        assert resp.status_code == 200, resp.text
        updated = resp.json()
        assert Decimal(updated["accumulated_depreciation"]) == Decimal("500.00")

        again = client.post(f"/api/fixed-assets/{asset['id']}/depreciate", json={"as_of_date": "2026-06-01"})
        assert again.status_code == 400
        assert "fully depreciated" in again.json()["detail"].lower()


def test_dispose_fixed_asset_with_gain_and_loss():
    with TestClient(app) as client:
        gain_asset = _create_fixed_asset(client, name="Asset For Gain")
        client.post(f"/api/fixed-assets/{gain_asset['id']}/depreciate", json={"as_of_date": "2026-01-01"})
        disposed = client.post(f"/api/fixed-assets/{gain_asset['id']}/dispose", json={"disposal_date": "2026-02-01", "disposal_value": "110000"})
        assert disposed.status_code == 200, disposed.text
        body = disposed.json()
        assert body["status"] == "Disposed"
        entries = _journal_entries_for(client, "FixedAssetDisposal", gain_asset["id"])
        _assert_balanced(entries[0])
        gain_line = next(l for l in entries[0]["lines"] if l["account"]["code"] == "4200")
        assert Decimal(gain_line["credit"]) > 0

        loss_asset = _create_fixed_asset(client, name="Asset For Loss")
        client.post(f"/api/fixed-assets/{loss_asset['id']}/depreciate", json={"as_of_date": "2026-01-01"})
        disposed2 = client.post(f"/api/fixed-assets/{loss_asset['id']}/dispose", json={"disposal_date": "2026-02-01", "disposal_value": "50000"})
        assert disposed2.status_code == 200, disposed2.text
        entries2 = _journal_entries_for(client, "FixedAssetDisposal", loss_asset["id"])
        _assert_balanced(entries2[0])
        loss_line = next(l for l in entries2[0]["lines"] if l["account"]["code"] == "4200")
        assert Decimal(loss_line["debit"]) > 0

        already = client.post(f"/api/fixed-assets/{gain_asset['id']}/dispose", json={"disposal_date": "2026-03-01", "disposal_value": "0"})
        assert already.status_code == 400


def test_trial_balance_stays_balanced_with_fixed_assets_activity():
    with TestClient(app) as client:
        asset = _create_fixed_asset(client, name="Balance Check Asset")
        client.post(f"/api/fixed-assets/{asset['id']}/depreciate", json={"as_of_date": "2026-01-01"})
        client.post(f"/api/fixed-assets/{asset['id']}/dispose", json={"disposal_date": "2026-02-01", "disposal_value": "115000"})
        total_debit, total_credit = _trial_balance_totals(client)
        assert total_debit == total_credit


def _create_financial_year(client, start_date, end_date, label=""):
    resp = client.post("/api/financial-years", json={"start_date": start_date, "end_date": end_date, "label": label})
    assert resp.status_code == 201, resp.text
    return resp.json()


def _create_expense_dated(client, expense_date, amount="1000"):
    return client.post("/api/expenses", json={
        "expense_date": expense_date, "category": "Rent", "description": "FY lock test", "amount": amount,
        "gst_percent": "0", "vendor_id": None, "mode": "Cash", "reference_number": "", "notes": "",
    })


def test_create_financial_year_generates_label_and_rejects_overlap():
    with TestClient(app) as client:
        fy = _create_financial_year(client, "2000-04-01", "2001-03-31")
        assert fy["label"] == "FY 2000-01"
        assert fy["status"] == "Open"

        overlap = client.post("/api/financial-years", json={"start_date": "2000-06-01", "end_date": "2000-12-31", "label": ""})
        assert overlap.status_code == 400
        assert "overlaps" in overlap.json()["detail"].lower()

        bad_range = client.post("/api/financial-years", json={"start_date": "2010-04-01", "end_date": "2009-03-31", "label": ""})
        assert bad_range.status_code == 400

        closed = client.post(f"/api/financial-years/{fy['id']}/close")
        assert closed.status_code == 200, closed.text


def test_close_financial_year_computes_snapshot_and_locks_period():
    with TestClient(app) as client:
        expense = _create_expense_dated(client, "2001-06-15", "1000")
        assert expense.status_code == 201, expense.text

        fy = _create_financial_year(client, "2001-04-01", "2002-03-31")
        resp = client.post(f"/api/financial-years/{fy['id']}/close")
        assert resp.status_code == 200, resp.text
        closed = resp.json()
        assert closed["status"] == "Closed"
        assert closed["closed_at"]
        assert Decimal(closed["total_expense"]) == Decimal("1000.00")
        assert Decimal(closed["net_profit"]) == Decimal("-1000.00")

        blocked = _create_expense_dated(client, "2001-09-01", "500")
        assert blocked.status_code == 400
        assert "closed" in blocked.json()["detail"].lower()

        blocked_manual = client.post("/api/journal/manual", json={
            "entry_date": "2001-12-31", "narration": "backdated into closed year",
            "lines": [{"account_id": 1, "debit": "100", "credit": "0"}, {"account_id": 2, "debit": "0", "credit": "100"}],
        })
        assert blocked_manual.status_code == 400
        assert "closed" in blocked_manual.json()["detail"].lower()

        blocked_asset = client.post("/api/fixed-assets", json={
            "name": "Backdated Asset", "category": "Other", "purchase_date": "2001-08-01",
            "purchase_cost": "5000", "salvage_value": "0", "useful_life_years": "5",
            "depreciation_method": "Straight Line", "payment_mode": "Cash",
        })
        assert blocked_asset.status_code == 400
        assert "closed" in blocked_asset.json()["detail"].lower()

        allowed = _create_expense_dated(client, "2002-06-01", "500")
        assert allowed.status_code == 201, allowed.text


def test_close_financial_year_rejects_out_of_order_and_before_end_date():
    with TestClient(app) as client:
        fy_c = _create_financial_year(client, "2002-04-01", "2003-03-31")
        fy_d = _create_financial_year(client, "2003-04-01", "2004-03-31")

        out_of_order = client.post(f"/api/financial-years/{fy_d['id']}/close")
        assert out_of_order.status_code == 400
        assert fy_c["label"].lower() in out_of_order.json()["detail"].lower()

        close_c = client.post(f"/api/financial-years/{fy_c['id']}/close")
        assert close_c.status_code == 200, close_c.text
        close_d = client.post(f"/api/financial-years/{fy_d['id']}/close")
        assert close_d.status_code == 200, close_d.text

        future_fy = _create_financial_year(client, "2030-04-01", "2031-03-31")
        too_early = client.post(f"/api/financial-years/{future_fy['id']}/close")
        assert too_early.status_code == 400
        assert "has not ended" in too_early.json()["detail"].lower()


def test_reopen_financial_year_rejects_out_of_order_and_restores_posting():
    with TestClient(app) as client:
        fy_f = _create_financial_year(client, "2004-04-01", "2005-03-31")
        fy_g = _create_financial_year(client, "2005-04-01", "2006-03-31")
        assert client.post(f"/api/financial-years/{fy_f['id']}/close").status_code == 200
        assert client.post(f"/api/financial-years/{fy_g['id']}/close").status_code == 200

        blocked = _create_expense_dated(client, "2004-07-01", "200")
        assert blocked.status_code == 400

        out_of_order = client.post(f"/api/financial-years/{fy_f['id']}/reopen")
        assert out_of_order.status_code == 400
        assert fy_g["label"].lower() in out_of_order.json()["detail"].lower()

        reopened_g = client.post(f"/api/financial-years/{fy_g['id']}/reopen")
        assert reopened_g.status_code == 200, reopened_g.text
        assert reopened_g.json()["status"] == "Open"

        allowed = _create_expense_dated(client, "2005-07-01", "200")
        assert allowed.status_code == 201, allowed.text

        still_blocked = _create_expense_dated(client, "2004-07-01", "200")
        assert still_blocked.status_code == 400


def _create_stock_item(client, name="VEKA 60mm Profile - White", opening_quantity="0", reorder_level="0"):
    resp = client.post("/api/stock-items", json={
        "name": name, "category": "Profile", "unit": "Mtr", "hsn_code": "3925.20.00",
        "reorder_level": reorder_level, "opening_quantity": opening_quantity, "notes": "", "status": "Active",
    })
    assert resp.status_code == 201, resp.text
    return resp.json()


def test_create_stock_item_with_opening_quantity_records_movement():
    with TestClient(app) as client:
        item = _create_stock_item(client, "Opening Stock Profile", opening_quantity="100")
        assert item["code"].startswith("STK-")
        assert Decimal(item["quantity_on_hand"]) == Decimal("100.00")
        assert len(item["movements"]) == 1
        assert item["movements"][0]["movement_type"] == "In"
        assert item["movements"][0]["reason"] == "Opening Stock"
        assert Decimal(item["movements"][0]["balance_after"]) == Decimal("100.00")


def test_stock_in_and_out_movements_update_balance():
    with TestClient(app) as client:
        item = _create_stock_item(client, "Multipoint Lock Set")
        stock_in = client.post(f"/api/stock-items/{item['id']}/movements", json={
            "movement_date": "2026-07-01", "movement_type": "In", "quantity": "50", "reason": "Manual", "reference": "", "notes": "",
        })
        assert stock_in.status_code == 201, stock_in.text
        assert Decimal(stock_in.json()["quantity_on_hand"]) == Decimal("50.00")

        stock_out = client.post(f"/api/stock-items/{item['id']}/movements", json={
            "movement_date": "2026-07-05", "movement_type": "Out", "quantity": "20", "reason": "Issued for Project", "reference": "Sharma Residency", "notes": "",
        })
        assert stock_out.status_code == 201, stock_out.text
        updated = stock_out.json()
        assert Decimal(updated["quantity_on_hand"]) == Decimal("30.00")
        assert len(updated["movements"]) == 2
        assert Decimal(updated["movements"][1]["balance_after"]) == Decimal("30.00")


def test_stock_out_rejects_when_insufficient_balance():
    with TestClient(app) as client:
        item = _create_stock_item(client, "5mm Toughened Glass", opening_quantity="10")
        over = client.post(f"/api/stock-items/{item['id']}/movements", json={
            "movement_date": "2026-07-01", "movement_type": "Out", "quantity": "15", "reason": "Manual", "reference": "", "notes": "",
        })
        assert over.status_code == 400
        assert "insufficient" in over.json()["detail"].lower()


def test_purchase_bill_with_stock_item_posts_automatic_stock_in():
    with TestClient(app) as client:
        vendor = _create_vendor(client, "Stock Linked Vendor")
        item = _create_stock_item(client, "SS Roller Set")

        bill_resp = client.post(f"/api/vendors/{vendor['id']}/purchase-bills", json={
            "vendor_bill_number": "SF-STK-1", "bill_date": "2026-07-10", "due_date": "2026-08-09", "notes": "",
            "items": [{
                "description": "SS Roller Set", "category": "Hardware", "hsn_code": "8302.42",
                "unit": "Nos", "quantity": "25", "rate": "80", "gst_percent": "18", "amount": "2000",
                "stock_item_id": item["id"],
            }],
        })
        assert bill_resp.status_code == 201, bill_resp.text
        bill = bill_resp.json()

        updated_item = client.get(f"/api/stock-items/{item['id']}").json()
        assert Decimal(updated_item["quantity_on_hand"]) == Decimal("25.00")
        movement = updated_item["movements"][-1]
        assert movement["source_type"] == "PurchaseBill"
        assert movement["source_id"] == bill["id"]
        assert movement["reference"] == bill["number"]


def test_low_stock_filter_returns_only_items_at_or_below_reorder_level():
    with TestClient(app) as client:
        low = _create_stock_item(client, "Low Stock Hinges", opening_quantity="5", reorder_level="10")
        healthy = _create_stock_item(client, "Healthy Stock Hinges", opening_quantity="50", reorder_level="10")
        untracked = _create_stock_item(client, "Untracked Item", opening_quantity="0", reorder_level="0")

        low_stock = client.get("/api/stock-items", params={"low_stock": "true"}).json()
        low_stock_ids = {i["id"] for i in low_stock}
        assert low["id"] in low_stock_ids
        assert healthy["id"] not in low_stock_ids
        assert untracked["id"] not in low_stock_ids


def test_cash_flow_statement_classifies_operating_and_investing_activities():
    with TestClient(app) as client:
        customer_id = client.get("/api/customers").json()[0]["id"]
        invoice = _create_invoice_for_customer(client, customer_id)
        payment = client.post(f"/api/invoices/{invoice['id']}/payments", json={
            "payment_date": "2010-03-10", "mode": "UPI", "reference_number": "CF1", "amount": "5000", "received_by": "Admin", "notes": "",
        })
        assert payment.status_code == 201, payment.text

        expense = client.post("/api/expenses", json={
            "expense_date": "2010-04-01", "category": "Rent", "description": "", "amount": "2000", "gst_percent": "0",
            "vendor_id": None, "mode": "Bank", "reference_number": "", "notes": "",
        })
        assert expense.status_code == 201, expense.text

        asset = client.post("/api/fixed-assets", json={
            "name": "CF Test Asset", "category": "Other", "purchase_date": "2010-05-01",
            "purchase_cost": "3000", "salvage_value": "0", "useful_life_years": "3",
            "depreciation_method": "Straight Line", "payment_mode": "Bank",
        })
        assert asset.status_code == 201, asset.text

        report = client.get("/api/cash-flow", params={"from_date": "2010-01-01", "to_date": "2010-12-31"}).json()
        assert report["operating_activities"]["total"] == 3000.0
        assert report["investing_activities"]["total"] == -3000.0
        assert report["financing_activities"]["total"] == 0.0
        assert report["net_change_in_cash"] == 0.0
        assert report["closing_cash_balance"] == report["opening_cash_balance"]

        operating_labels = {row["label"] for row in report["operating_activities"]["rows"]}
        assert "Cash received from customers" in operating_labels
        assert "Cash paid for expenses" in operating_labels
        investing_labels = {row["label"] for row in report["investing_activities"]["rows"]}
        assert "Purchase of fixed assets" in investing_labels


def test_ap_aging_buckets_vendor_bill_by_days_overdue():
    with TestClient(app) as client:
        vendor = _create_vendor(client, "Aging Test Vendor")
        bill_resp = client.post(f"/api/vendors/{vendor['id']}/purchase-bills", json={
            "vendor_bill_number": "AGE-1", "bill_date": "2025-12-01", "due_date": "2026-01-01", "notes": "",
            "items": [{
                "description": "Hardware batch", "category": "Hardware", "hsn_code": "", "unit": "Nos",
                "quantity": "1", "rate": "10000", "gst_percent": "18", "amount": "10000",
            }],
        })
        assert bill_resp.status_code == 201, bill_resp.text

        overdue = client.get("/api/ap-aging", params={"as_of": "2026-02-15"}).json()
        row = next(r for r in overdue["rows"] if r["vendor_id"] == vendor["id"])
        assert row["d31_60"] > 0
        assert row["current"] == 0
        assert row["d1_30"] == 0
        assert row["d61_90"] == 0
        assert row["d90_plus"] == 0
        assert row["total"] == row["d31_60"]

        not_yet_due = client.get("/api/ap-aging", params={"as_of": "2025-12-15"}).json()
        row2 = next(r for r in not_yet_due["rows"] if r["vendor_id"] == vendor["id"])
        assert row2["current"] > 0
        assert row2["d1_30"] == 0


def test_ap_aging_excludes_paid_bills():
    with TestClient(app) as client:
        vendor = _create_vendor(client, "Paid Off Vendor")
        bill = _create_purchase_bill(client, vendor["id"])
        pay = client.post(f"/api/purchase-bills/{bill['id']}/payments", json={
            "payment_date": "2026-07-20", "mode": "NEFT", "reference_number": "", "amount": bill["grand_total"], "paid_by": "Admin", "notes": "",
        })
        assert pay.status_code == 201, pay.text

        aging = client.get("/api/ap-aging", params={"as_of": "2026-09-01"}).json()
        assert not any(r["vendor_id"] == vendor["id"] for r in aging["rows"])
