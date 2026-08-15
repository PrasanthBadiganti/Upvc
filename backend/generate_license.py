#!/usr/bin/env python
"""
License Key Generator for UPVC Pro

This script should only be run by authorized administrators.
It generates license keys that are tied to specific machine IDs.

Usage:
    python generate_license.py

The script will prompt for:
    - License type (master or viewer)
    - Machine ID
    - Validity period in days
    - Output file path
"""

import base64
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path


def generate_license_key(machine_id: str, license_type: str, days: int = 365) -> tuple:
    """
    Generate a license key

    Args:
        machine_id: The machine ID to generate license for
        license_type: 'master' or 'viewer'
        days: Validity period in days

    Returns:
        Tuple of (license_key, license_data)
    """
    import hashlib

    if license_type not in ["master", "viewer"]:
        raise ValueError("License type must be 'master' or 'viewer'")

    # Generate expiry date
    expiry_date = (datetime.now() + timedelta(days=days)).isoformat()

    # Create signature data
    signature_data = f"{machine_id}:{license_type}:{expiry_date}"

    # Generate license key hash
    license_hash = hashlib.sha256(signature_data.encode()).hexdigest().upper()[:32]

    # Create license data
    license_data = {
        "license_key": license_hash,
        "machine_id": machine_id,
        "license_type": license_type,
        "expiry_date": expiry_date,
        "days": days,
        "generated_at": datetime.now().isoformat()
    }

    # Encode to base64
    license_json = json.dumps(license_data)
    license_key = base64.b64encode(license_json.encode()).decode()

    return license_key, license_data


def main():
    """Main function"""
    print("=" * 60)
    print("UPVC Pro License Key Generator")
    print("=" * 60)
    print()

    try:
        # Get license type
        print("Select License Type:")
        print("  1. Master (Full features)")
        print("  2. Viewer (Read-only)")
        choice = input("\nEnter choice (1 or 2): ").strip()

        if choice == "1":
            license_type = "master"
        elif choice == "2":
            license_type = "viewer"
        else:
            print("Invalid choice!")
            return

        # Get machine ID
        print("\nEnter Machine ID:")
        print("(You can find this by running the app and checking Settings > License)")
        machine_id = input("Machine ID: ").strip()

        if not machine_id:
            print("Machine ID is required!")
            return

        # Get validity period
        print("\nValidity Period:")
        days_input = input("Days valid (default: 365): ").strip()
        days = int(days_input) if days_input else 365

        if days < 1:
            print("Days must be at least 1!")
            return

        # Generate license
        print("\nGenerating license key...")
        license_key, license_data = generate_license_key(machine_id, license_type, days)

        # Display results
        print("\n" + "=" * 60)
        print("LICENSE GENERATED SUCCESSFULLY")
        print("=" * 60)
        print()
        print(f"License Type:  {license_type.upper()}")
        print(f"Machine ID:    {machine_id}")
        print(f"Valid Days:    {days}")
        print(f"Expiry Date:   {license_data['expiry_date']}")
        print()
        print("-" * 60)
        print("LICENSE KEY (Copy this entire string):")
        print("-" * 60)
        print(license_key)
        print("-" * 60)
        print()

        # Save to file option
        save_choice = input("Save to file? (y/n): ").strip().lower()
        if save_choice == "y":
            filename = f"license_{machine_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            output_path = Path(filename)

            with open(output_path, "w") as f:
                f.write("UPVC Pro License Key\n")
                f.write("=" * 60 + "\n\n")
                f.write(f"License Type:  {license_type.upper()}\n")
                f.write(f"Machine ID:    {machine_id}\n")
                f.write(f"Valid Days:    {days}\n")
                f.write(f"Expiry Date:   {license_data['expiry_date']}\n")
                f.write(f"Generated At:  {license_data['generated_at']}\n\n")
                f.write("-" * 60 + "\n")
                f.write("LICENSE KEY (Paste this in UPVC Pro):\n")
                f.write("-" * 60 + "\n")
                f.write(license_key + "\n\n")
                f.write("Instructions:\n")
                f.write("1. Open UPVC Pro\n")
                f.write("2. Go to Settings > License\n")
                f.write("3. Paste the license key above\n")
                f.write("4. Click 'Activate License'\n")

            print(f"License saved to: {output_path}")

        print("\nInstructions to activate:")
        print("1. Open UPVC Pro application")
        print("2. Go to Settings > License")
        print("3. Paste the license key above")
        print("4. Click 'Activate License'")

    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n\nCancelled.")
        sys.exit(0)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
