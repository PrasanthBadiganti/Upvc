"""
UPVC Pro hardware-locked licensing (BROMS-style short HMAC codes).

A license is a short 16-character code: ZGCQ-R2BA-LCWS-HSJ3

The code is an HMAC-SHA256 of machine_id|type (or with period for time-limited).
It carries no payload — the app knows its own Machine ID, so on activation it
recomputes the expected code for MASTER and VIEWER and sees which one matches.

Machine binding is automatic: the Machine ID is inside the HMAC.
80 bits of entropy makes a code unguessable.

Two license types:
  MASTER -> full application (all features)
  VIEWER -> read-only (no create/edit/delete)
"""
from __future__ import annotations

import base64
import datetime as dt
import hashlib
import hmac
import json
import sys
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from .database import DATA_DIR, IS_FROZEN

LICENSE_FILENAME = "license.key"
_NAMESPACE = "UPVC-LIC-v1|"
VALID_TYPES = ("MASTER", "VIEWER")
CODE_LEN = 16  # base32 chars (80 bits) before grouping
MAX_PERIOD_DAYS = 3660  # ~10 years


def _today() -> dt.date:
    """Current date (indirection for testing)."""
    return dt.date.today()


# ─────────────────────────────────────────────────────────────────────────── #
# Machine fingerprint (Windows Registry)                                      #
# ─────────────────────────────────────────────────────────────────────────── #
def _raw_machine_guid() -> str:
    """Stable Windows install identifier: HKLM\\...\\Cryptography\\MachineGuid."""
    try:
        import winreg

        with winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            r"SOFTWARE\Microsoft\Cryptography",
            0,
            winreg.KEY_READ | winreg.KEY_WOW64_64KEY,
        ) as k:
            val, _ = winreg.QueryValueEx(k, "MachineGuid")
        return str(val).strip()
    except Exception:
        # Non-Windows / dev fallback
        import uuid

        return f"fallback-{uuid.getnode():x}"


@lru_cache(maxsize=1)
def get_machine_id() -> str:
    """Friendly, stable machine ID: XXXX-XXXX-XXXX-XXXX-XXXX (20 hex chars)."""
    digest = hashlib.sha256((_NAMESPACE + _raw_machine_guid()).encode("utf-8")).hexdigest()
    chunk = digest[:20].upper()
    return "-".join(chunk[i : i + 4] for i in range(0, 20, 4))


# ─────────────────────────────────────────────────────────────────────────── #
# License code (short, paste-able key)                                        #
# ─────────────────────────────────────────────────────────────────────────── #
# Embedded secret (vendor fills this in; see generate_license_v2.py)
LICENSE_SECRET = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"


def _secret_bytes() -> bytes:
    """The embedded shared secret as raw bytes."""
    return bytes.fromhex(LICENSE_SECRET)


def compute_code(mid: str, ltype: str, period_days: int = 0) -> str:
    """Canonical license code for (machine, type, period): XXXX-XXXX-XXXX-XXXX

    period_days == 0 means perpetual (backward compatible).
    """
    data = f"{mid}|{ltype}" if not period_days else f"{mid}|{ltype}|{period_days}"
    mac = hmac.new(_secret_bytes(), data.encode("utf-8"), hashlib.sha256).digest()
    raw = base64.b32encode(mac[:10]).decode("ascii")  # 10 bytes → 16 chars, no padding
    return "-".join(raw[i : i + 4] for i in range(0, CODE_LEN, 4))


def normalize_code(text: str | None) -> str:
    """Strip grouping/spacing/case: 'k7q2-9fma' and 'K7Q29FMA' compare equal."""
    return "".join(ch for ch in (text or "").upper() if ch.isalnum())


def identify(mid: str, code_text: str | None) -> tuple[str, int] | None:
    """Return (type, period_days) a code grants on this machine, or None.

    Searches perpetual first, then every day-length up to MAX_PERIOD_DAYS.
    """
    stored = normalize_code(code_text)
    if len(stored) != CODE_LEN:
        return None

    # Try perpetual codes
    for ltype in VALID_TYPES:
        if hmac.compare_digest(stored, normalize_code(compute_code(mid, ltype, 0))):
            return (ltype, 0)

    # Try time-limited codes
    for days in range(1, MAX_PERIOD_DAYS + 1):
        for ltype in VALID_TYPES:
            if hmac.compare_digest(stored, normalize_code(compute_code(mid, ltype, days))):
                return (ltype, days)

    return None


# ─────────────────────────────────────────────────────────────────────────── #
# Activation record (time-limited licenses)                                   #
# ─────────────────────────────────────────────────────────────────────────── #
def _record_mac(
    code: str, ltype: str, period_days: int, activated_on: str, last_seen: str
) -> str:
    """Tamper seal over activation record fields."""
    base = f"REC|{code}|{ltype}|{period_days}|{activated_on}|{last_seen}"
    return hmac.new(_secret_bytes(), base.encode("utf-8"), hashlib.sha256).hexdigest()


def _build_record(
    mid: str, ltype: str, period_days: int, activated_on: str, last_seen: str
) -> dict:
    """Build activation record for time-limited license."""
    code = compute_code(mid, ltype, period_days)
    return {
        "code": code,
        "type": ltype,
        "period_days": period_days,
        "activated_on": activated_on,
        "last_seen": last_seen,
        "mac": _record_mac(code, ltype, period_days, activated_on, last_seen),
    }


def _verify_record(rec: dict) -> bool:
    """Verify record MAC is intact (not tampered)."""
    try:
        expected = _record_mac(
            rec["code"],
            rec["type"],
            rec["period_days"],
            rec["activated_on"],
            rec["last_seen"],
        )
        return hmac.compare_digest(rec.get("mac", ""), expected)
    except Exception:
        return False


# ─────────────────────────────────────────────────────────────────────────── #
# License file (stored in data folder)                                        #
# ─────────────────────────────────────────────────────────────────────────── #
def _license_path() -> Path:
    """License file location."""
    return DATA_DIR / LICENSE_FILENAME


def load_license_record() -> dict | None:
    """Load stored license record, or None if not activated."""
    path = _license_path()
    if not path.exists():
        return None
    try:
        with open(path, "r") as f:
            return json.load(f)
    except Exception:
        return None


def save_license_record(rec: dict) -> None:
    """Save license activation record."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(_license_path(), "w") as f:
        json.dump(rec, f, indent=2)


def delete_license_record() -> None:
    """Delete saved license (deactivate)."""
    _license_path().unlink(missing_ok=True)


# ─────────────────────────────────────────────────────────────────────────── #
# Validation                                                                   #
# ─────────────────────────────────────────────────────────────────────────── #
@dataclass
class LicenseStatus:
    """License evaluation result."""

    licensed: bool  # Is app licensed?
    mode: str  # "master", "viewer", or "demo"
    license_type: str | None  # "MASTER" or "VIEWER" if licensed
    is_expired: bool  # Is time-limited license expired?
    days_remaining: int | None  # Days left (if time-limited)
    error: str | None = None  # Human-readable error if any


def evaluate() -> LicenseStatus:
    """Check if app is licensed (called on every protected API)."""
    mid = get_machine_id()
    rec = load_license_record()

    # No license file → demo mode
    if not rec:
        return LicenseStatus(
            licensed=False,
            mode="demo",
            license_type=None,
            is_expired=False,
            days_remaining=None,
        )

    # Verify saved code matches this machine
    result = identify(mid, rec.get("code"))
    if not result:
        return LicenseStatus(
            licensed=False,
            mode="demo",
            license_type=None,
            is_expired=False,
            days_remaining=None,
            error="License is for a different machine",
        )

    ltype, period_days = result

    # Perpetual license: always valid
    if period_days == 0:
        return LicenseStatus(
            licensed=True,
            mode=("master" if ltype == "MASTER" else "viewer"),
            license_type=ltype,
            is_expired=False,
            days_remaining=None,
        )

    # Time-limited: check expiry
    if not _verify_record(rec):
        return LicenseStatus(
            licensed=False,
            mode="demo",
            license_type=None,
            is_expired=False,
            days_remaining=None,
            error="License record is corrupted",
        )

    # Update last_seen (clock-rollback detection)
    try:
        activated = dt.datetime.fromisoformat(rec["activated_on"]).date()
        today = _today()
        elapsed = (today - activated).days

        # Update last_seen if moving forward in time
        last_seen = dt.datetime.fromisoformat(rec.get("last_seen", rec["activated_on"])).date()
        if today > last_seen:
            rec["last_seen"] = today.isoformat()
            save_license_record(rec)

        # Check expiry
        if elapsed >= period_days:
            return LicenseStatus(
                licensed=False,
                mode="demo",
                license_type=ltype,
                is_expired=True,
                days_remaining=0,
                error="License has expired",
            )

        remaining = period_days - elapsed
        return LicenseStatus(
            licensed=True,
            mode=("master" if ltype == "MASTER" else "viewer"),
            license_type=ltype,
            is_expired=False,
            days_remaining=remaining,
        )
    except Exception as e:
        return LicenseStatus(
            licensed=False,
            mode="demo",
            license_type=None,
            is_expired=False,
            days_remaining=None,
            error=str(e),
        )


def activate_license(code_text: str) -> dict:
    """Activate a license code."""
    mid = get_machine_id()
    result = identify(mid, code_text)

    if not result:
        return {"success": False, "error": "Invalid license code for this machine"}

    ltype, period_days = result

    if period_days == 0:
        # Perpetual: just store code
        save_license_record(
            {
                "code": normalize_code(code_text),
                "type": ltype,
                "period_days": 0,
            }
        )
    else:
        # Time-limited: store with activation record
        today = _today().isoformat()
        rec = _build_record(mid, ltype, period_days, today, today)
        save_license_record(rec)

    status = evaluate()
    return {
        "success": True,
        "license_type": ltype.lower(),
        "mode": status.mode,
        "days_remaining": status.days_remaining,
    }


def deactivate_license() -> dict:
    """Remove license (SuperAdmin only)."""
    delete_license_record()
    return {"success": True, "message": "License deactivated"}


def get_license_info() -> dict:
    """Get current license status."""
    status = evaluate()
    if not status.licensed:
        return {
            "licensed": False,
            "mode": status.mode,
            "machine_id": get_machine_id(),
        }

    return {
        "licensed": True,
        "mode": status.mode,
        "license_type": status.license_type.lower(),
        "is_expired": status.is_expired,
        "days_remaining": status.days_remaining,
        "machine_id": get_machine_id(),
    }


def is_master_license() -> bool:
    """Check if licensed as MASTER."""
    status = evaluate()
    return status.licensed and status.license_type == "MASTER"


def is_viewer_license() -> bool:
    """Check if licensed as VIEWER."""
    status = evaluate()
    return status.licensed and status.license_type == "VIEWER"


def is_licensed() -> bool:
    """Check if any valid license exists."""
    status = evaluate()
    return status.licensed
