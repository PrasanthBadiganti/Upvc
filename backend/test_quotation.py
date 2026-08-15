#!/usr/bin/env python3
"""Quick test to identify quotation API validation error"""
import requests
import json
from datetime import datetime

BASE_URL = "http://localhost:8000"

# Create one test customer
print("[*] Creating test customer...")
customer_payload = {
    "name": "Test Customer 1",
    "phone": "9876543210",
    "email": "test@company.com",
    "address": "123 Main Street",
    "gst_number": "36AABCT1234H1Z0",
    "state": "Telangana",
    "project_site": "Hyderabad",
    "status": "Active"
}
response = requests.post(f"{BASE_URL}/api/customers", json=customer_payload)
print(f"Customer creation: {response.status_code}")
if response.status_code != 201:
    print(f"Error: {response.text}")
    exit(1)
customer = response.json()
customer_id = customer["id"]
print(f"Customer ID: {customer_id}")

# Get catalog items
print("\n[*] Fetching catalog items...")
response = requests.get(f"{BASE_URL}/api/catalog?status=Active")
if response.status_code != 200:
    print(f"Error: {response.text}")
    exit(1)
catalog_items = response.json()
print(f"Found {len(catalog_items)} catalog items")

if not catalog_items:
    print("No catalog items found")
    exit(1)

# Create quotation with detailed debugging
print("\n[*] Creating quotation...")
catalog_item = catalog_items[0]
print(f"Using catalog item: {catalog_item['name']}")
print(f"Catalog item keys: {catalog_item.keys()}")

items = [{
    "catalog_item_id": catalog_item["id"],
    "category": catalog_item["category"],
    "style": catalog_item["product_type"],
    "width_mm": 1000,
    "height_mm": 1000,
    "sft": 11,
    "quantity": 1,
    "rate_per_sft": float(catalog_item["rate_per_sft"]),
    "location": "Main Location",
    "profile": catalog_item["profile"],
    "color": catalog_item["color"],
    "track": catalog_item.get("track", ""),
    "glass": catalog_item["glass"],
    "glass_color": catalog_item.get("glass_color", ""),
    "hardware": catalog_item["hardware"],
    "hsn_code": catalog_item.get("hsn_code", "")
}]

quotation_payload = {
    "customer_id": customer_id,
    "quotation_date": datetime.now().date().isoformat(),
    "validity_days": 30,
    "sales_person": "Arun Verma",
    "site_location": "On-site",
    "address": "Project Location",
    "items": items,
    "transport": 1000,
    "discount": 0,
    "notes": "Test quotation"
}

print(f"\nPayload JSON:\n{json.dumps(quotation_payload, indent=2)}")
print("\n[*] Sending quotation POST request...")
response = requests.post(f"{BASE_URL}/api/quotations", json=quotation_payload)
print(f"Status code: {response.status_code}")
print(f"Response:\n{response.text}")
