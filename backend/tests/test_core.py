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
