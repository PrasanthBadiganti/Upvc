from __future__ import annotations

import csv
from datetime import date
from decimal import Decimal
from io import StringIO

from sqlalchemy import select
from sqlalchemy.orm import Session

from . import models
from .services import ACCOUNT_OPENING_BALANCE_EQUITY, ACCOUNT_PAYABLE, create_opening_balance_invoice, money, post_journal_entry


def _parse_rows(content: bytes) -> list[dict]:
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError("CSV file must be UTF-8 encoded") from exc
    reader = csv.DictReader(StringIO(text))
    if not reader.fieldnames:
        raise ValueError("CSV file has no header row")
    normalized = {name: name.strip().lower().replace(" ", "_") for name in reader.fieldnames}
    if "name" not in normalized.values():
        raise ValueError("CSV must include a 'name' column (ledger or party name)")

    rows = []
    for raw in reader:
        row = {normalized[key]: (value or "").strip() for key, value in raw.items() if key in normalized}
        name = row.get("name", "")
        if not name:
            continue
        try:
            debit = Decimal(row.get("debit") or "0")
            credit = Decimal(row.get("credit") or "0")
        except Exception as exc:
            raise ValueError(f"Row for '{name}' has a non-numeric debit or credit value") from exc
        rows.append({"name": name, "debit": debit, "credit": credit})
    return rows


def _resolve(db: Session, name: str) -> tuple[str, int | str | None, str | None]:
    customer = db.scalar(select(models.Customer).where(models.Customer.name.ilike(name)))
    if customer:
        return "customer", customer.id, customer.name
    vendor = db.scalar(select(models.Vendor).where(models.Vendor.name.ilike(name)))
    if vendor:
        return "vendor", vendor.id, vendor.name
    account = db.scalar(select(models.ChartOfAccount).where(models.ChartOfAccount.name.ilike(name)))
    if not account:
        account = db.scalar(select(models.ChartOfAccount).where(models.ChartOfAccount.code == name))
    if account:
        return "account", account.code, f"{account.code} - {account.name}"
    return "unmatched", None, None


def preview_opening_balances(db: Session, content: bytes) -> list[dict]:
    results = []
    for row in _parse_rows(content):
        match_type, match_id, match_name = _resolve(db, row["name"])
        results.append({
            "name": row["name"],
            "debit": float(row["debit"]),
            "credit": float(row["credit"]),
            "match_type": match_type,
            "match_id": match_id,
            "match_name": match_name,
        })
    return results


def commit_opening_balances(db: Session, rows: list[dict], as_of: date) -> dict:
    ap_debit = ap_credit = Decimal("0")
    lines: list[tuple[str, Decimal, Decimal]] = []
    applied = 0
    skipped = 0

    for row in rows:
        debit = money(Decimal(str(row.get("debit") or 0)))
        credit = money(Decimal(str(row.get("credit") or 0)))
        if debit == 0 and credit == 0:
            continue
        match_type = row.get("match_type")

        if match_type == "customer":
            # Customer.pending_payment is re-derived from real Invoice records on every
            # read, so the balance must be represented as an invoice, not a raw field
            # write. Only a net receivable (debit > credit) fits the Invoice model;
            # a net credit/advance balance isn't representable yet and is skipped.
            net = debit - credit
            if net <= 0:
                skipped += 1
                continue
            customer = db.get(models.Customer, row.get("match_id"))
            if not customer:
                skipped += 1
                continue
            create_opening_balance_invoice(db, customer.id, net, as_of)
            applied += 1
        elif match_type == "vendor":
            vendor = db.get(models.Vendor, row.get("match_id"))
            if not vendor:
                skipped += 1
                continue
            vendor.pending_payment = money(Decimal(vendor.pending_payment or 0) + credit - debit)
            ap_debit += debit
            ap_credit += credit
            applied += 1
        elif match_type == "account":
            lines.append((str(row.get("match_id")), debit, credit))
            applied += 1
        else:
            skipped += 1

    if ap_debit or ap_credit:
        lines.append((ACCOUNT_PAYABLE, ap_debit, ap_credit))

    if lines:
        total_debit = money(sum((debit for _, debit, _ in lines), Decimal("0")))
        total_credit = money(sum((credit for _, _, credit in lines), Decimal("0")))
        plug = money(total_debit - total_credit)
        if plug > 0:
            lines.append((ACCOUNT_OPENING_BALANCE_EQUITY, Decimal("0"), plug))
        elif plug < 0:
            lines.append((ACCOUNT_OPENING_BALANCE_EQUITY, -plug, Decimal("0")))
        post_journal_entry(db, as_of, f"Opening balances as of {as_of.isoformat()}", "OpeningBalance", None, lines)

    db.commit()
    return {"applied": applied, "skipped": skipped}
