#!/usr/bin/env python
"""
License Key Generator for UPVC Pro (BROMS-style short codes).

Generates short 16-character HMAC-based license codes bound to machine IDs.

Usage:
    python generate_license_v2.py

The script will prompt for:
    - License type (Master or Viewer)
    - Machine ID
    - Validity period (days, or perpetual)
    - Output file path (optional)

Example:
    License Type: Master
    Machine ID: XXXX-XXXX-XXXX-XXXX-XXXX
    Days valid: 365

    Generated Code: ZGCQ-R2BA-LCWS-HSJ3  (16 chars, easy to email/call)
"""

import base64
import hashlib
import hmac
import sys
from datetime import datetime, timedelta
from pathlib import Path


# IMPORTANT: This secret MUST match the one embedded in app/licensing_v2.py
# Generate once with: python tools/gen_secret.py
LICENSE_SECRET = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"


def compute_code(machine_id: str, license_type: str, period_days: int = 0) -> str:
    """Compute HMAC-based license code.

    Args:
        machine_id: Target machine ID (XXXX-XXXX-XXXX-XXXX-XXXX format)
        license_type: "MASTER" or "VIEWER"
        period_days: 0 for perpetual, or days for time-limited

    Returns:
        16-character code formatted as XXXX-XXXX-XXXX-XXXX
    """
    # Normalize machine ID (remove dashes)
    mid_clean = machine_id.replace("-", "").upper()

    # Create signature data
    if period_days == 0:
        data = f"{mid_clean}|{license_type}"  # Perpetual
    else:
        data = f"{mid_clean}|{license_type}|{period_days}"  # Time-limited

    # Compute HMAC-SHA256
    secret_bytes = bytes.fromhex(LICENSE_SECRET)
    mac = hmac.new(secret_bytes, data.encode("utf-8"), hashlib.sha256).digest()

    # Encode to base32 (10 bytes → 16 chars, no padding)
    raw = base64.b32encode(mac[:10]).decode("ascii")

    # Format as XXXX-XXXX-XXXX-XXXX
    return "-".join(raw[i : i + 4] for i in range(0, 16, 4))


def main():
    """Main generator."""
    print("=" * 70)
    print("UPVC Pro License Key Generator (BROMS-style)")
    print("=" * 70)
    print()

    try:
        # Get license type
        print("Select License Type:")
        print("  1. Master (Full features)")
        print("  2. Viewer (Read-only)")
        choice = input("\nEnter choice (1 or 2): ").strip()

        if choice == "1":
            license_type = "MASTER"
            mode_name = "Master"
        elif choice == "2":
            license_type = "VIEWER"
            mode_name = "Viewer"
        else:
            print("Invalid choice!")
            return

        # Get machine ID
        print("\nEnter Machine ID:")
        print("(Copy from target machine: Settings → License → Machine ID)")
        machine_id = input("Machine ID: ").strip()

        if not machine_id:
            print("Machine ID is required!")
            return

        # Get validity period
        print("\nValidity Period:")
        print("  (Leave blank for perpetual license that never expires)")
        days_input = input("Days valid (or press Enter for perpetual): ").strip()

        if days_input:
            try:
                period_days = int(days_input)
                if period_days < 1:
                    print("Days must be at least 1!")
                    return
            except ValueError:
                print("Invalid number!")
                return
        else:
            period_days = 0

        # Generate code
        print("\nGenerating license code...")
        code = compute_code(machine_id, license_type, period_days)

        # Display results
        print("\n" + "=" * 70)
        print("LICENSE GENERATED SUCCESSFULLY")
        print("=" * 70)
        print()
        print(f"License Type:   {mode_name}")
        print(f"Machine ID:     {machine_id}")

        if period_days == 0:
            print(f"Validity:       Perpetual (never expires)")
        else:
            expiry = datetime.now() + timedelta(days=period_days)
            print(f"Validity:       {period_days} days (expires ~{expiry.strftime('%Y-%m-%d')})")
            print("                (Actual expiry: {period_days} days after activation)")

        print()
        print("-" * 70)
        print("LICENSE CODE (Copy this 16-character code):")
        print("-" * 70)
        print(code)
        print("-" * 70)
        print()

        # Save to file option
        save_choice = input("Save to file? (y/n): ").strip().lower()
        if save_choice == "y":
            filename = f"license_{machine_id.replace('-', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            output_path = Path(filename)

            with open(output_path, "w") as f:
                f.write("UPVC Pro License Code\n")
                f.write("=" * 70 + "\n\n")
                f.write(f"License Type:   {mode_name}\n")
                f.write(f"Machine ID:     {machine_id}\n")

                if period_days == 0:
                    f.write(f"Validity:       Perpetual (never expires)\n")
                else:
                    expiry = datetime.now() + timedelta(days=period_days)
                    f.write(f"Validity:       {period_days} days (expires ~{expiry.strftime('%Y-%m-%d')})\n")
                    f.write(f"Note:           Actual expiry is {period_days} days after the user activates\n")

                f.write(f"\nGenerated:      {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                f.write("-" * 70 + "\n")
                f.write("LICENSE CODE (Give this to the user):\n")
                f.write("-" * 70 + "\n")
                f.write(code + "\n\n")
                f.write("INSTRUCTIONS FOR USER:\n")
                f.write("1. Open UPVC Pro\n")
                f.write("2. Go to Settings → License\n")
                f.write("3. Click 'Activate License'\n")
                f.write("4. Paste or type the code: " + code + "\n")
                f.write("5. Click 'Activate'\n\n")
                f.write("Note: Dashes, spaces, and case are ignored when entering the code.\n")

            print(f"License saved to: {output_path}")

        print("\nInstructions to send to user:")
        print("1. Open UPVC Pro application")
        print("2. Go to Settings → License")
        print("3. Click 'Activate License'")
        print(f"4. Enter this code: {code}")
        print("5. Click 'Activate'")
        print()
        print("Note: Dashes, spaces, and case don't matter when typing the code.")

    except KeyboardInterrupt:
        print("\n\nCancelled.")
        sys.exit(0)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
