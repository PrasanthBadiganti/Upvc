# UPVC Pro - Licensing System

## Overview

Single EXE application with license-based feature differentiation:
- **Master License**: Full features (all CRUD operations)
- **Viewer License**: Read-only access to reports and data
- **No License**: Demo mode with limited functionality

## License Types

### Master License
- **Features**: Full CRUD operations on all resources
- **Viewer Access**: All pages and features available
- **Modifications**: Create, edit, delete allowed
- **Target**: Main users, managers, data entry staff
- **Use Case**: Full business operations

### Viewer License
- **Features**: Read-only access to reports and data
- **Viewer Access**: All report pages visible
- **Modifications**: No create, edit, or delete operations
- **Target**: Stakeholders, external viewers, audit
- **Use Case**: Report review, stakeholder access, offline viewing

### No License (Demo)
- **Features**: Limited demo functionality
- **Access**: Can view some pages
- **Modifications**: No modifications allowed
- **Time**: Limited to demo period
- **Target**: Trial/evaluation mode

---

## Machine ID System

### What is Machine ID?

A unique identifier for each installation, based on:
- MAC address of the primary network interface
- Generated on first run
- Consistent across application restarts
- Used to tie licenses to specific installations

### Getting Your Machine ID

**Method 1: Through UI**
1. Launch UPVC Pro EXE
2. Go to Settings → License
3. Machine ID displayed at top
4. Copy for license request

**Method 2: Through API**
```bash
curl http://localhost:8000/api/license/machine-id \
  -H "Authorization: Bearer <token>"
```

**Response**:
```json
{
  "machine_id": "a1b2c3d4e5f6",
  "message": "Copy this Machine ID when requesting a license key"
}
```

**Method 3: From License File**
- Windows: `%LOCALAPPDATA%\UPVC Pro\license.json`
- Contains machine_id field

---

## License Generation

### For Administrators Only

A script is provided to generate license keys for authorized machines.

### Using the License Generator

**Script Location**: `backend/generate_license.py`

**Usage**:
```bash
cd backend
python generate_license.py
```

**Interactive Menu**:
```
============================================================
UPVC Pro License Key Generator
============================================================

Select License Type:
  1. Master (Full features)
  2. Viewer (Read-only)

Enter choice (1 or 2): 1
```

**Enter Details**:
- Machine ID (get from target system)
- License type (Master or Viewer)
- Validity period in days (default: 365)

**Output**:
- Displays license key
- Option to save to file
- Full instructions for activation

### Example: Generate Master License

```
Machine ID: a1b2c3d4e5f6
License Type: Master
Days Valid: 365

Generated License Key:
eyJsaWNlbnNlX2tleSI6ICJBQkMxMjM0NRF...
```

---

## License Activation

### Through UI

**Steps**:
1. Launch UPVC Pro EXE
2. Navigate to Settings → License
3. Click "Enter License Key"
4. Paste entire license key
5. Click "Activate License"
6. Application restarts in licensed mode

### Through API

**Endpoint**:
```http
POST /api/license/activate
```

**Request**:
```bash
curl -X POST http://localhost:8000/api/license/activate \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"license_key": "eyJsaWNlbnNlX2tleSI6In..."}'
```

**Response**:
```json
{
  "success": true,
  "message": "License activated successfully",
  "license_type": "master",
  "expiry_date": "2027-08-16T12:34:56.789012",
  "days_valid": 365
}
```

---

## License Management

### Check Current License

**API Endpoint**:
```http
GET /api/license/info
```

**Response**:
```json
{
  "licensed": true,
  "license_type": "master",
  "expiry_date": "2027-08-16T12:34:56.789012",
  "expiry_formatted": "2027-08-16",
  "days_remaining": 365,
  "is_expired": false,
  "machine_id": "a1b2c3d4e5f6"
}
```

### Check License Type

**API Endpoint** (No authentication required):
```http
GET /api/license/check
```

**Response for Master**:
```json
{
  "licensed": true,
  "mode": "master",
  "features": "full"
}
```

**Response for Viewer**:
```json
{
  "licensed": true,
  "mode": "viewer",
  "features": "read-only",
  "message": "This is a viewer-only license. Read-only access only."
}
```

**Response for No License**:
```json
{
  "licensed": false,
  "mode": "demo",
  "message": "No valid license. Please activate a license."
}
```

### Deactivate License

**API Endpoint** (SuperAdmin only):
```http
POST /api/license/deactivate
```

**Response**:
```json
{
  "success": true,
  "message": "License deactivated"
}
```

---

## License Storage

### License File Location

**Windows**:
```
%LOCALAPPDATA%\UPVC Pro\license.json
```

**Example Path**:
```
C:\Users\YourName\AppData\Local\UPVC Pro\license.json
```

### License File Format

```json
{
  "license_key": "ABC123...",
  "machine_id": "a1b2c3d4e5f6",
  "license_type": "master",
  "expiry_date": "2027-08-16T12:34:56.789012",
  "activated_at": "2026-08-16T12:34:56.789012"
}
```

### Backup Your License

1. Locate license file (path above)
2. Copy to backup location (USB, cloud drive)
3. Keep safe for system restoration

---

## Feature Gating

### Master License Features
- ✅ Create customers
- ✅ Create quotations & invoices
- ✅ Record payments
- ✅ Manage vendors & purchase bills
- ✅ Create expenses
- ✅ View all reports
- ✅ Export reports
- ✅ Access all admin features

### Viewer License Features
- ❌ Create customers (no)
- ❌ Create quotations (no)
- ❌ Create invoices (no)
- ❌ Record payments (no)
- ✅ View all reports (yes)
- ✅ View customer/invoice data (yes)
- ✅ Export reports as PDF (yes)
- ✅ Search and filter (yes)
- ❌ Modify data (no)
- ❌ Admin features (no)

### Demo Mode Features
- Limited to sample data
- No persistent changes
- Time-limited
- Prompts to activate license

---

## License Expiry & Renewal

### Before Expiry

- Application shows expiry date
- Warning displayed: "X days remaining"
- 30 days before: More prominent warning
- 7 days before: Daily warning

### At Expiry

- License becomes invalid
- Application operates in demo mode
- All mutations blocked
- Prompt to renew license

### Renewing License

1. Contact administrator for new license key
2. Provide current machine ID
3. Receive new license key
4. Activate through Settings → License
5. Application resumes normal operation

---

## Migration & System Restore

### Moving to New Machine

**Step 1: Generate New License**
```bash
# On new machine, get machine ID
# Launch app → Settings → License → Copy Machine ID

# Send machine ID to administrator
# Administrator runs: python generate_license.py
# Administrator provides new license key
```

**Step 2: Activate on New Machine**
- Launch UPVC Pro on new machine
- Settings → License → Enter License Key
- Paste new license key
- Click Activate

### Migrating License (Same Hardware)

If upgrading/reinstalling same machine:
1. Original machine ID remains the same (based on MAC address)
2. Original license key can be reused
3. Simply activate same key on new installation

---

## Security Considerations

### License Key Format

- Base64 encoded JSON with embedded hash
- Hash prevents tampering/modification
- Machine ID prevents license sharing
- Expiry date embedded in hash

### Machine ID Binding

- Each license tied to specific machine
- Cannot use license on different machine
- Prevents unlimited license distribution
- Required for professional deployments

### License File Protection

- Stored in user AppData (Windows permission protected)
- Requires admin privileges to access/modify
- Single file (not distributed across system)
- Easy to backup and restore

---

## Troubleshooting

### "Invalid License Key" Error

**Causes**:
- Key corrupted or truncated
- Copy-paste error
- License for different machine

**Solution**:
1. Verify complete key copied (very long string)
2. Regenerate license key
3. Verify machine ID matches

### "License is for different machine"

**Cause**: License generated for different machine ID

**Solution**:
1. Get correct machine ID from current machine
2. Request new license for this machine ID
3. Activate new license

### "License has expired"

**Cause**: Expiry date has passed

**Solution**:
1. Contact administrator
2. Request license renewal
3. Provide machine ID and previous license type
4. Activate new license

### "No License Found"

**Cause**: Application running in demo mode

**Solution**:
1. Obtain license key from administrator
2. Settings → License → Enter License Key
3. Paste and activate

---

## License Key Format (Technical)

### Structure

```
Base64 Encoded:
{
  "license_key": "SHA256_HASH",
  "machine_id": "MAC_ADDRESS_HEX",
  "license_type": "master|viewer",
  "expiry_date": "ISO_DATETIME",
  "days": "INTEGER",
  "generated_at": "ISO_DATETIME"
}
```

### Hash Calculation

```
signature_data = f"{machine_id}:{license_type}:{expiry_date}"
license_key = SHA256(signature_data).hexdigest()[:32]
```

### Verification Process

1. Decode base64 to get JSON
2. Extract machine_id, license_type, expiry_date
3. Recalculate hash from these fields
4. Compare with provided license_key
5. Verify expiry_date is in future
6. Verify machine_id matches current system

---

## API Endpoints Summary

| Endpoint | Method | Auth | Purpose |
|----------|--------|------|---------|
| `/api/license/info` | GET | ✅ | Get license info (authenticated) |
| `/api/license/machine-id` | GET | ✅ | Get machine ID |
| `/api/license/check` | GET | ❌ | Check license type (no auth) |
| `/api/license/activate` | POST | ✅ | Activate license key |
| `/api/license/deactivate` | POST | ✅ SuperAdmin | Remove license |

---

## Files

**Implementation**:
- `backend/app/licensing.py` - License core logic
- `backend/app/routes/license.py` - License API endpoints
- `backend/generate_license.py` - License key generator

**Documentation**:
- `LICENSING.md` - This file

---

## Version

**v1.0.0** (2026-08-16)

Complete licensing system with machine ID binding, license key generation, and feature gating for Master/Viewer/Demo modes.
