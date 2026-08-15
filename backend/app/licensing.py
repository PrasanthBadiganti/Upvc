"""Licensing system for UPVC Pro"""

import hashlib
import json
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from .database import DEFAULT_DB_PATH


LICENSE_DIR = DEFAULT_DB_PATH.parent
LICENSE_FILE = LICENSE_DIR / "license.json"

# License types
LICENSE_TYPE_MASTER = "master"
LICENSE_TYPE_VIEWER = "viewer"

VALID_LICENSE_TYPES = [LICENSE_TYPE_MASTER, LICENSE_TYPE_VIEWER]


def _get_machine_id() -> str:
    """Generate machine ID based on system hardware"""
    try:
        # Use UUID based on MAC address
        mac = uuid.getnode()
        return str(mac)
    except Exception:
        # Fallback to a static ID if unable to get MAC
        return "000000000000"


def _generate_license_key(machine_id: str, license_type: str, days: int = 365) -> dict:
    """
    Generate a license key for given machine ID

    This function should only be called by authorized administrators

    Args:
        machine_id: The machine ID to generate license for
        license_type: 'master' or 'viewer'
        days: Validity period in days

    Returns:
        Dictionary with license key and metadata
    """
    if license_type not in VALID_LICENSE_TYPES:
        raise ValueError(f"Invalid license type: {license_type}")

    # Generate expiry date
    expiry_date = (datetime.now() + timedelta(days=days)).isoformat()

    # Create signature data
    signature_data = f"{machine_id}:{license_type}:{expiry_date}"

    # Generate license key hash
    license_key = hashlib.sha256(signature_data.encode()).hexdigest().upper()[:32]

    return {
        "license_key": license_key,
        "machine_id": machine_id,
        "license_type": license_type,
        "expiry_date": expiry_date,
        "days": days,
        "generated_at": datetime.now().isoformat()
    }


def _verify_license_key(license_key: str, machine_id: str, license_type: str, expiry_date: str) -> bool:
    """Verify license key matches the provided details"""
    signature_data = f"{machine_id}:{license_type}:{expiry_date}"
    expected_key = hashlib.sha256(signature_data.encode()).hexdigest().upper()[:32]
    return license_key.upper() == expected_key


def get_machine_id() -> str:
    """Get the machine ID for this installation"""
    return _get_machine_id()


def get_license_info() -> dict:
    """Get current license information"""
    try:
        if LICENSE_FILE.exists():
            with open(LICENSE_FILE, "r") as f:
                license_data = json.load(f)

            # Check if license is expired
            expiry = datetime.fromisoformat(license_data.get("expiry_date"))
            is_expired = datetime.now() > expiry

            return {
                "licensed": True,
                "license_type": license_data.get("license_type"),
                "expiry_date": license_data.get("expiry_date"),
                "expiry_formatted": expiry.strftime("%Y-%m-%d"),
                "days_remaining": (expiry - datetime.now()).days,
                "is_expired": is_expired,
                "machine_id": license_data.get("machine_id")
            }
        else:
            return {
                "licensed": False,
                "message": "No license found",
                "machine_id": get_machine_id()
            }
    except Exception as e:
        return {
            "licensed": False,
            "error": str(e),
            "machine_id": get_machine_id()
        }


def activate_license(license_key: str) -> dict:
    """
    Activate a license key

    Args:
        license_key: License key provided by user

    Returns:
        Dictionary with activation result
    """
    try:
        # License key should be in format: base64 encoded JSON
        import base64

        try:
            # Try to decode the license key
            decoded = base64.b64decode(license_key.encode())
            license_data = json.loads(decoded)
        except Exception:
            return {
                "success": False,
                "error": "Invalid license key format"
            }

        machine_id = get_machine_id()
        provided_machine_id = license_data.get("machine_id")
        license_type = license_data.get("license_type")
        license_hash = license_data.get("license_key")
        expiry_date = license_data.get("expiry_date")

        # Validate license
        if not all([provided_machine_id, license_type, license_hash, expiry_date]):
            return {
                "success": False,
                "error": "License key is incomplete or corrupted"
            }

        # Check machine ID matches
        if provided_machine_id != machine_id:
            return {
                "success": False,
                "error": f"License is for different machine (Expected: {machine_id}, Got: {provided_machine_id})"
            }

        # Verify license signature
        if not _verify_license_key(license_hash, machine_id, license_type, expiry_date):
            return {
                "success": False,
                "error": "License key is invalid or tampered"
            }

        # Check expiry
        expiry = datetime.fromisoformat(expiry_date)
        if datetime.now() > expiry:
            return {
                "success": False,
                "error": f"License has expired ({expiry.strftime('%Y-%m-%d')})"
            }

        # Save license
        license_to_save = {
            "license_key": license_hash,
            "machine_id": machine_id,
            "license_type": license_type,
            "expiry_date": expiry_date,
            "activated_at": datetime.now().isoformat()
        }

        LICENSE_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(LICENSE_FILE, "w") as f:
            json.dump(license_to_save, f, indent=2)

        return {
            "success": True,
            "message": f"License activated successfully",
            "license_type": license_type,
            "expiry_date": expiry_date,
            "days_valid": (expiry - datetime.now()).days
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def is_master_license() -> bool:
    """Check if current license is master (full features)"""
    info = get_license_info()
    if info.get("licensed") and not info.get("is_expired"):
        return info.get("license_type") == LICENSE_TYPE_MASTER
    return False


def is_viewer_license() -> bool:
    """Check if current license is viewer (read-only)"""
    info = get_license_info()
    if info.get("licensed") and not info.get("is_expired"):
        return info.get("license_type") == LICENSE_TYPE_VIEWER
    return False


def is_licensed() -> bool:
    """Check if system has valid license"""
    info = get_license_info()
    return info.get("licensed", False) and not info.get("is_expired", True)


def deactivate_license() -> dict:
    """Remove the current license"""
    try:
        if LICENSE_FILE.exists():
            LICENSE_FILE.unlink()
            return {
                "success": True,
                "message": "License deactivated"
            }
        return {
            "success": False,
            "error": "No license to deactivate"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }
