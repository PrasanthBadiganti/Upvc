#!/usr/bin/env python3
"""Comprehensive test data loader for UPVC Pro"""
import requests
import json
from datetime import datetime, timedelta
import random
import sys

BASE_URL = "http://localhost:8000"

CITIES_BY_STATE = {
    "Telangana": ["Hyderabad", "Secunderabad", "Warangal", "Karimnagar"],
    "Karnataka": ["Bangalore", "Pune", "Mysore", "Hubli"],
    "Tamil Nadu": ["Chennai", "Coimbatore", "Madurai", "Salem"],
    "Maharashtra": ["Mumbai", "Pune", "Nagpur", "Aurangabad"],
    "Uttar Pradesh": ["Delhi", "Noida", "Lucknow", "Kanpur"],
    "Gujarat": ["Ahmedabad", "Surat", "Rajkot", "Vadodara"],
}

CUSTOMER_NAMES = [
    "Apex Construction", "BuildRight Enterprises", "Modern Homes Ltd",
    "Urban Development Corp", "Premier Interiors", "Global Glass Works",
    "Structural Solutions", "Design Innovations", "Elite Builders",
    "Future Constructions", "Standard Projects", "Classic Structures",
]

def create_customer(name, state, city):
    """Create a customer via API"""
    payload = {
        "name": name,
        "phone": f"9{random.randint(100000000, 999999999)}",
        "email": f"{name.lower().replace(' ', '')}@company.com",
        "address": f"{random.randint(1, 999)} {city} Road",
        "gst_number": f"36{random.randint(100000000000, 999999999999)}",
        "state": state,
        "project_site": city,
        "status": "Active"
    }
    try:
        response = requests.post(f"{BASE_URL}/api/customers", json=payload)
        if response.status_code == 201:
            return response.json()
    except Exception as e:
        print(f"Error creating customer: {e}")
    return None

def create_quotation(customer_id, items):
    """Create a quotation via API"""
    payload = {
        "customer_id": customer_id,
        "quotation_date": datetime.now().date().isoformat(),
        "validity_days": 30,
        "sales_person": random.choice(["Arun Verma", "Neha Kapoor", "Rohit Singh"]),
        "site_location": "On-site",
        "address": "Project Location",
        "items": items,
        "transport": random.randint(500, 2000),
        "discount": random.randint(0, 5000),
        "notes": "Standard quotation"
    }
    try:
        response = requests.post(f"{BASE_URL}/api/quotations", json=payload)
        if response.status_code == 201:
            return response.json()
        else:
            print(f"[ERR] Quotation POST returned {response.status_code}: {response.text[:200]}")
    except Exception as e:
        print(f"[ERR] Exception in quotation creation: {e}")
    return None

def create_invoice_from_quotation(quotation_id):
    """Convert quotation to invoice via API"""
    payload = {
        "quotation_id": quotation_id,
        "invoice_date": datetime.now().date().isoformat(),
        "due_date": (datetime.now() + timedelta(days=30)).date().isoformat()
    }
    try:
        response = requests.post(f"{BASE_URL}/api/quotations/{quotation_id}/convert", json=payload)
        if response.status_code == 201:
            return response.json()
        else:
            print(f"[ERR] Invoice POST returned {response.status_code}: {response.text[:200]}")
    except Exception as e:
        print(f"[ERR] Exception in invoice creation: {e}")
    return None

def create_payment(invoice_id, amount):
    """Record payment for invoice via API"""
    payload = {
        "payment_date": datetime.now().date().isoformat(),
        "mode": random.choice(["NEFT", "RTGS", "Cheque", "UPI"]),
        "reference_number": f"REF{random.randint(100000, 999999)}",
        "amount": amount,
        "received_by": "Arun Verma",
        "notes": "Payment received"
    }
    try:
        response = requests.post(f"{BASE_URL}/api/invoices/{invoice_id}/payments", json=payload)
        if response.status_code == 201:
            return response.json()
        else:
            print(f"[ERR] Payment POST returned {response.status_code}: {response.text[:200]}")
    except Exception as e:
        print(f"[ERR] Exception in payment creation: {e}")
    return None

def main():
    print("[*] Starting comprehensive test data load...\n")

    # Get catalog items
    print("[*] Fetching catalog items...")
    try:
        catalog_response = requests.get(f"{BASE_URL}/api/catalog?status=Active")
        if catalog_response.status_code != 200:
            print("Error fetching catalog items")
            return
    except Exception as e:
        print(f"Cannot connect to backend: {e}")
        return

    catalog_items = catalog_response.json()
    if not catalog_items:
        print("No catalog items found. Catalog items exist: OK")
        return

    print(f"Found {len(catalog_items)} catalog items\n")

    customer_count = 0
    quotation_count = 0
    invoice_count = 0
    payment_count = 0

    # Create customers
    print("[*] Creating customers...")
    customers = []
    for state, cities in CITIES_BY_STATE.items():
        for i in range(15):  # 15 customers per state
            city = random.choice(cities)
            customer_name = f"{random.choice(CUSTOMER_NAMES)} {i+1}"
            customer = create_customer(customer_name, state, city)
            if customer:
                customers.append(customer)
                customer_count += 1
                sys.stdout.write(f"\r[*] Created {customer_count} customers...")
                sys.stdout.flush()

    print(f"\n[OK] Created {customer_count} customers\n")

    # Create quotations and invoices
    print("[*] Creating quotations and invoices...")
    for idx, customer in enumerate(customers):
        # 1-2 quotations per customer
        for _ in range(random.randint(1, 2)):
            # 2-5 line items per quotation
            items = []
            for _ in range(random.randint(2, 5)):
                if not catalog_items:
                    break
                catalog_item = random.choice(catalog_items)
                width = random.choice([1000, 1200, 1500, 2000])
                height = random.choice([1000, 1200, 1500, 2000])
                sft = (width/304.8) * (height/304.8)

                items.append({
                    "catalog_item_id": catalog_item["id"],
                    "category": catalog_item["category"],
                    "style": catalog_item["product_type"],
                    "width_mm": width,
                    "height_mm": height,
                    "sft": round(sft),
                    "quantity": random.randint(1, 3),
                    "rate_per_sft": float(catalog_item["rate_per_sft"]),
                    "location": "Main Location",
                    "profile": catalog_item["profile"],
                    "color": catalog_item["color"],
                    "track": catalog_item.get("track", ""),
                    "glass": catalog_item["glass"],
                    "glass_color": catalog_item.get("glass_color", ""),
                    "hardware": catalog_item["hardware"],
                    "hsn_code": catalog_item.get("hsn_code", "")
                })

            # Create quotation
            quotation = create_quotation(customer["id"], items)
            if quotation:
                quotation_count += 1

                # Convert to invoice
                invoice = create_invoice_from_quotation(quotation["id"])
                if invoice:
                    invoice_count += 1

                    # Create payments
                    payment_percentage = random.choice([30, 50, 75, 100])
                    payment_amount = (invoice["grand_total"] * payment_percentage) / 100

                    payment = create_payment(invoice["id"], payment_amount)
                    if payment:
                        payment_count += 1

        sys.stdout.write(f"\r[*] Created {quotation_count} quotations, {invoice_count} invoices, {payment_count} payments...")
        sys.stdout.flush()

    print(f"\n\n[SUMMARY]")
    print(f"Customers:    {customer_count}")
    print(f"Quotations:   {quotation_count}")
    print(f"Invoices:     {invoice_count}")
    print(f"Payments:     {payment_count}")
    print(f"Catalog:      {len(catalog_items)}")
    print(f"\n[OK] Test data load complete!")

if __name__ == "__main__":
    main()
