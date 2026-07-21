from __future__ import annotations

import csv
from datetime import date
from decimal import Decimal
from io import StringIO
import xml.etree.ElementTree as ET

from sqlalchemy import select
from sqlalchemy.orm import Session

from . import models
from .services import ACCOUNT_OPENING_BALANCE_EQUITY, ACCOUNT_PAYABLE, create_opening_balance_invoice, money, next_code, post_journal_entry

CUSTOMER_FIELDS = ["name", "phone", "email", "address", "gst_number", "project_site", "assigned_to", "notes", "opening_balance"]
VENDOR_FIELDS = ["name", "phone", "email", "address", "gst_number", "notes", "opening_balance"]


def _looks_like_xml(content: bytes) -> bool:
    stripped = content.lstrip()
    return stripped.startswith(b"<?xml") or stripped.startswith(b"<ENVELOPE")


def _parse_csv_rows(content: bytes, fields: list[str]) -> list[dict]:
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError("CSV file must be UTF-8 encoded") from exc
    reader = csv.DictReader(StringIO(text))
    if not reader.fieldnames:
        raise ValueError("CSV file has no header row")
    normalized = {name: name.strip().lower().replace(" ", "_") for name in reader.fieldnames}
    if "name" not in normalized.values():
        raise ValueError("CSV must include a 'name' column")

    rows = []
    for raw_row in reader:
        row = {normalized[key]: (value or "").strip() for key, value in raw_row.items() if key in normalized}
        if not row.get("name"):
            continue
        rows.append({field: row.get(field, "") for field in fields})
    return rows


def _parse_tally_ledger_rows(content: bytes, parent_groups: set[str], fields: list[str]) -> list[dict]:
    try:
        root = ET.fromstring(content)
    except ET.ParseError as exc:
        raise ValueError("Could not parse this file as Tally XML (expected a LEDGER masters export)") from exc

    rows = []
    for ledger in root.iter("LEDGER"):
        parent = (ledger.findtext("PARENT") or "").strip()
        if parent not in parent_groups:
            continue
        name = (ledger.get("NAME") or ledger.findtext("NAME") or "").strip()
        if not name:
            continue
        row = {field: "" for field in fields}
        row["name"] = name
        if "gst_number" in row:
            row["gst_number"] = (ledger.findtext("PARTYGSTIN") or ledger.findtext("GSTREGISTRATIONNUMBER") or "").strip()
        if "phone" in row:
            row["phone"] = (ledger.findtext("LEDGERPHONE") or ledger.findtext("LEDGERMOBILE") or "").strip()
        if "address" in row:
            parts = [el.text.strip() for el in ledger.findall("ADDRESS.LIST/ADDRESS") if el.text and el.text.strip()]
            row["address"] = ", ".join(parts)
        if "opening_balance" in row:
            try:
                row["opening_balance"] = str(abs(Decimal(ledger.findtext("OPENINGBALANCE") or "0")))
            except Exception:
                row["opening_balance"] = "0"
        rows.append(row)
    return rows


def _parse_rows(content: bytes, fields: list[str], tally_parent_groups: set[str]) -> list[dict]:
    if _looks_like_xml(content):
        return _parse_tally_ledger_rows(content, tally_parent_groups, fields)
    return _parse_csv_rows(content, fields)


def _find_match(db: Session, model: type, row: dict):
    if row.get("gst_number"):
        match = db.scalar(select(model).where(model.gst_number == row["gst_number"]))
        if match:
            return match
    if row.get("phone"):
        match = db.scalar(select(model).where(model.phone == row["phone"]))
        if match:
            return match
    if row.get("email"):
        match = db.scalar(select(model).where(model.email == row["email"]))
        if match:
            return match
    return None


def preview_customer_import(db: Session, content: bytes) -> list[dict]:
    results = []
    for row in _parse_rows(content, CUSTOMER_FIELDS, {"Sundry Debtors"}):
        match = _find_match(db, models.Customer, row)
        results.append({
            "row": row,
            "status": "duplicate" if match else "new",
            "matched_id": match.id if match else None,
            "matched_name": match.name if match else None,
        })
    return results


def commit_customer_import(db: Session, rows: list[dict], as_of: date | None = None) -> int:
    created = 0
    pending_opening_balances: list[tuple[int, Decimal]] = []
    for row in rows:
        if not row.get("name"):
            continue
        customer = models.Customer(
            code=next_code(db, models.Customer, "CUST"),
            name=row.get("name", ""),
            phone=row.get("phone", ""),
            email=row.get("email", ""),
            address=row.get("address", ""),
            gst_number=row.get("gst_number", ""),
            project_site=row.get("project_site", ""),
            assigned_to=row.get("assigned_to") or "Arun Verma",
            notes=row.get("notes", ""),
        )
        db.add(customer)
        db.flush()
        opening_balance = money(Decimal(str(row.get("opening_balance") or 0)))
        if opening_balance > 0:
            pending_opening_balances.append((customer.id, opening_balance))
        created += 1
    for customer_id, amount in pending_opening_balances:
        create_opening_balance_invoice(db, customer_id, amount, as_of or date.today())
    db.commit()
    return created


def preview_vendor_import(db: Session, content: bytes) -> list[dict]:
    results = []
    for row in _parse_rows(content, VENDOR_FIELDS, {"Sundry Creditors"}):
        match = _find_match(db, models.Vendor, row)
        results.append({
            "row": row,
            "status": "duplicate" if match else "new",
            "matched_id": match.id if match else None,
            "matched_name": match.name if match else None,
        })
    return results


def commit_vendor_import(db: Session, rows: list[dict], as_of: date | None = None) -> int:
    created = 0
    ap_credit = Decimal("0")
    for row in rows:
        if not row.get("name"):
            continue
        vendor = models.Vendor(
            code=next_code(db, models.Vendor, "VEND"),
            name=row.get("name", ""),
            phone=row.get("phone", ""),
            email=row.get("email", ""),
            address=row.get("address", ""),
            gst_number=row.get("gst_number", ""),
            notes=row.get("notes", ""),
        )
        opening_balance = money(Decimal(str(row.get("opening_balance") or 0)))
        if opening_balance > 0:
            vendor.pending_payment = opening_balance
            ap_credit += opening_balance
        db.add(vendor)
        created += 1
    if ap_credit > 0:
        post_journal_entry(db, as_of or date.today(), "Opening balances from vendor import", "OpeningBalance", None, [
            (ACCOUNT_OPENING_BALANCE_EQUITY, ap_credit, Decimal("0")),
            (ACCOUNT_PAYABLE, Decimal("0"), ap_credit),
        ])
    db.commit()
    return created
