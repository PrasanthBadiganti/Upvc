# Architecture Comparison: UPVC Pro vs BROMS

## Executive Summary

**BROMS approach is SIGNIFICANTLY SIMPLER and more elegant.**

| Aspect | UPVC Pro (Current) | BROMS | Winner |
|--------|-------------------|-------|--------|
| Deployment | Single EXE | One-folder | ✅ BROMS (simpler) |
| UI Framework | Browser-based | Native pywebview | ✅ BROMS (no browser issues) |
| License Codes | Long base64 (128+ chars) | Short codes (16 chars) | ✅ BROMS (user-friendly) |
| Machine ID | MAC address | Windows Registry | ✅ BROMS (stable) |
| Port Handling | Fixed (8000, 3000) | Dynamic | ✅ BROMS (auto-solves conflicts) |
| License Type | 2 types (Master/Viewer) | 2 types (Master/Viewer) | 🤝 Equal |
| Backup/Restore | Basic | Advanced (cloud, verify) | ✅ BROMS (feature-rich) |
| Complexity | High | Medium | ✅ BROMS |
| Build Issues | Multiple (crypto, logging) | Clean | ✅ BROMS |

---

## Detailed Comparison

### 1. Deployment Model

#### UPVC Pro (Current)
```
Distribution: Single UPVC Pro.exe (30.8 MB)
Issues encountered:
  - PyInstaller single-file bundling complexities
  - Crypto dependencies missing initially
  - Logging framework conflicts in headless mode
  - All dependencies frozen into one file
  - Startup time: ~15-20 seconds (initial), ~5 seconds (subsequent)
```

#### BROMS
```
Distribution: One-folder (BROMS/BROMS.exe + dependencies)
Advantages:
  - Simpler PyInstaller configuration (COLLECT instead of EXE)
  - Cleaner dependency management
  - Easier to update individual components
  - Smaller main EXE (~20 MB vs 30.8 MB)
  - No bundling conflicts
  - Faster startup
```

**Advantage: BROMS** (One-folder is simpler for PyInstaller)

---

### 2. UI Framework

#### UPVC Pro (Current)
```python
# Starts FastAPI server, opens browser
Start-Process "UPVC Pro.exe"
# Browser opens to localhost:3000
# Full React app in browser window
```

Issues:
- Browser must be available
- Port conflicts can block startup
- Browser processes not tied to app lifecycle
- User might close browser accidentally, leaving server orphaned

#### BROMS
```python
# desktop.py entry point
import webview
import uvicorn

# Starts FastAPI in background thread
# Opens native Windows window with WebView2 embedded
port = _free_port()  # Auto-finds free port
threading.Thread(target=_run_server, args=(port,), daemon=True).start()
webview.start(...)  # Opens native window
```

Advantages:
- Single-file window (app looks like native app)
- Automatic port detection (no conflicts)
- Window lifecycle tied to app lifecycle
- No browser dependency
- Can use native Windows APIs (DPI awareness, downloads)
- Looks more professional

**Advantage: BROMS** (Native window is more polished)

---

### 3. License System

#### UPVC Pro (Current)
```json
{
  "license_key": "eyJsaWNlbnNlX2tleSI6ICJBQkMxMjM0...",  // Base64, 128+ chars
  "machine_id": "a1b2c3d4e5f6",
  "license_type": "master",
  "expiry_date": "2027-08-16",
  "activated_at": "2026-08-16"
}
```

Activation flow:
1. User gets Machine ID (Settings → License → Copy)
2. Admin generates license via `generate_license.py`
3. User pastes long base64 string
4. Application restarts

Issues:
- Long license keys hard to email/type
- Base64 encoding/decoding complexity
- Multiple format conversions

#### BROMS
```
Machine ID: XXXX-XXXX-XXXX-XXXX-XXXX  (20 hex chars, 5 groups)
License Code: ZGCQ-R2BA-LCWS-HSJ3     (16 chars, 4 groups, HMAC-SHA256)

License generation:
  python tools/make_license.py --machine XXXX-XXXX-XXXX-XXXX-XXXX --type MASTER
  Output: ZGCQ-R2BA-LCWS-HSJ3  (16-char code)
```

Activation flow:
1. User reads 20-char Machine ID
2. Admin runs: `python make_license.py --machine <ID> --type MASTER`
3. Admin gets 16-char code
4. User types 16-char code (copy-paste or manual)
5. App validates with HMAC verification

Advantages:
- Short, readable codes (16 chars vs 128+)
- Easier to email, call, or manually type
- User-friendly format (XXXX-XXXX-XXXX-XXXX)
- HMAC verification is simpler than base64 decoding
- No format conversions needed
- Code itself is the signature

**Advantage: BROMS** (Short, elegant codes)

---

### 4. Machine ID Generation

#### UPVC Pro (Current)
```python
def _get_machine_id():
    """UUID based on MAC address"""
    mac = uuid.getnode()
    return f"{mac:012x}".upper()[:12]  # First 12 hex chars
```

Issues:
- MAC address can change (network adapter replacement, virtual adapters)
- Not stable across Windows reinstalls
- Different if WiFi/Ethernet changes

#### BROMS
```python
def _raw_machine_guid() -> str:
    """HKLM\SOFTWARE\Microsoft\Cryptography\MachineGuid"""
    try:
        with winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            r"SOFTWARE\Microsoft\Cryptography",
            0,
            winreg.KEY_READ | winreg.KEY_WOW64_64KEY,
        ) as k:
            val, _ = winreg.QueryValueEx(k, "MachineGuid")
        return str(val).strip()
```

Then hashed:
```
SHA256("BROMS-LIC-v1|" + MachineGuid).hexdigest()[:20]
Result: XXXX-XXXX-XXXX-XXXX-XXXX
```

Advantages:
- Uses Windows MachineGuid (stable, created at Windows install)
- Survives network adapter changes
- Survives OS updates if on same hardware
- Hash provides abstraction (doesn't expose raw GUID)

**Advantage: BROMS** (Registry-based ID is more stable)

---

### 5. License Verification

#### UPVC Pro (Current)
```python
# Base64 decode → parse JSON → extract hash
license_json = base64.b64decode(license_key).decode()
license_data = json.loads(license_json)
stored_hash = license_data["license_key"]

# Recalculate hash
signature_data = f"{machine_id}:{license_type}:{expiry_date}"
expected_hash = hashlib.sha256(signature_data.encode()).hexdigest()[:32]

# Compare
if stored_hash == expected_hash:
    # Valid
```

Issues:
- Base64 encoding overhead
- JSON parsing overhead
- Multiple format conversions
- Longer verification logic

#### BROMS
```python
def identify(mid: str, code_text: str) -> tuple[str, int] | None:
    """Return (type, period_days) or None"""
    stored = normalize_code(code_text)  # Strip dashes, uppercase
    
    # Try perpetual codes first
    for ltype in VALID_TYPES:
        if hmac.compare_digest(stored, normalize_code(compute_code(mid, ltype, 0))):
            return (ltype, 0)
    
    # Try time-limited codes (brute-force search, fast)
    for days in range(1, MAX_PERIOD_DAYS + 1):
        for ltype in VALID_TYPES:
            if hmac.compare_digest(stored, normalize_code(compute_code(mid, ltype, days))):
                return (ltype, days)
    
    return None

def compute_code(mid: str, ltype: str, period_days: int = 0) -> str:
    """Compute HMAC for (machine, type, period)"""
    data = f"{mid}|{ltype}" if not period_days else f"{mid}|{ltype}|{period_days}"
    mac = hmac.new(_secret_bytes(), data.encode(), hashlib.sha256).digest()
    raw = base64.b32encode(mac[:10]).decode()  # 10 bytes → 16 chars
    return "-".join(raw[i : i + 4] for i in range(0, 16, 4))
```

Advantages:
- No JSON parsing or base64 decoding
- Direct HMAC comparison (cryptographically sound)
- Brute-force search is fast (few thousand HMACs, not slow)
- Can detect type and period from code alone
- No payload to decrypt (stateless verification)

**Advantage: BROMS** (Simpler, more elegant verification)

---

### 6. Port Management

#### UPVC Pro (Current)
```python
# Fixed ports
Backend: port 8000
Frontend: port 3000

# If either in use, startup fails
# User must restart computer or kill processes
# Port conflicts happen frequently
```

Issues:
- Fixed ports conflict with other apps
- Port 8000/3000 commonly used
- No automatic recovery
- User must manually troubleshoot

#### BROMS
```python
def _free_port() -> int:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port  # OS-assigned free port

# Then start server on that port
port = _free_port()
uvicorn.run(app, host="127.0.0.1", port=port, ...)
```

Advantages:
- Always finds free port automatically
- No conflicts, ever
- Multiple instances can run simultaneously
- Zero configuration
- No "port already in use" errors

**Advantage: BROMS** (Auto-port is elegant)

---

### 7. License Activation

#### UPVC Pro (Current)
Activation record stored:
```json
{
  "license_key": "...",
  "machine_id": "...",
  "license_type": "master",
  "expiry_date": "2027-08-16",
  "activated_at": "2026-08-16"
}
```

#### BROMS
Activation record stored (time-limited only):
```python
{
    "code": "ZGCQ-R2BA-LCWS-HSJ3",
    "ltype": "MASTER",
    "period_days": 365,
    "activated_on": "2026-08-16",
    "last_seen": "2026-08-16",
    "mac": "HMAC-SHA256(...)"  # Tamper seal
}
```

Perpetual licenses:
```
Just store the 16-char code, no activation record
Verification: recompute HMAC, compare codes
```

Advantages:
- Perpetual licenses: no activation record (just store code)
- Time-limited: minimal record (date + monotonic counter)
- MAC-protected record (tamper-evident)
- Clock-rollback protection built-in
- Simpler state management

**Advantage: BROMS** (Minimal activation state)

---

### 8. Backup & Restore

#### UPVC Pro (Current)
```
✓ Automatic hourly backups (configurable)
✓ Keep last 10 backups
✓ Manual backup/restore
✓ Export backup to file
✓ Pre-restore backup created
✗ No integrity verification
✗ No cloud backup support
✗ No multi-PC architecture
```

#### BROMS
```
✓ Automatic backups (hourly, 6-hourly, daily schedules)
✓ Keep last 30 backups (configurable)
✓ Manual backup/restore
✓ Verify backup:
    - WAL checkpoint
    - SQLite integrity check
    - Check core tables exist
✓ Cloud folder support (Google Drive, OneDrive, Dropbox)
✓ Pre-restore snapshot
✓ Master/Viewer PC architecture
  - Master writes to DB
  - Backups copied to synced folder
  - Viewers auto-load latest backup
  - Full data sync via cloud folder
✓ Scheduled backup only on data change (audit log aware)
✗ Viewer PCs can't modify data (read-only by design)
```

**Advantage: BROMS** (Advanced backup + cloud + multi-PC)

---

### 9. Build Complexity

#### UPVC Pro (Current)
Issues we hit:
1. ❌ bcrypt hidden imports missing
2. ❌ passlib.handlers.bcrypt not bundled
3. ❌ cryptography modules missing
4. ❌ Uvicorn logging requires TTY (failed in headless mode)
5. ❌ Custom logging setup needed
6. ❌ Relative imports in main.py caused module errors
7. ✅ Needed custom run_server.py entry point

Multiple rebuilds: 3+

#### BROMS
Build is clean:
- Single spec file
- No hidden import issues
- desktop.py works as-is
- Logging already configured

Single successful build (per their notes)

**Advantage: BROMS** (Clean build, no dependency issues)

---

### 10. Feature Comparison

| Feature | UPVC Pro | BROMS |
|---------|----------|-------|
| Sales Management | ✅ Yes | ✗ No (Real Estate focused) |
| GST Compliance | ✅ Yes | ✗ No |
| Accounting | ✅ Yes | ✗ No |
| Commission Tracking | ✗ No | ✅ Yes |
| Multi-PC Master/Viewer | ✗ No | ✅ Yes |
| Cloud Backup Sync | ✗ No | ✅ Yes |
| Native Window UI | ✗ No | ✅ Yes |
| Browser-based UI | ✅ Yes | ✗ No |
| Licensing System | ✅ Yes | ✅ Yes |
| Backup/Restore | ✅ Basic | ✅ Advanced |
| RBAC | ✅ Yes | ✅ Yes |

---

## Recommendation

### For UPVC Pro (going forward):

If you want to **simplify future EXE builds**, adopt BROMS approach:

1. **Switch to one-folder deployment** (not single EXE)
   ```spec
   COLLECT(exe, a.binaries, a.datas, ...)  # Instead of just exe
   ```

2. **Replace browser with pywebview**
   - `pip install pywebview`
   - Update `desktop.py` (launch webview instead of browser)
   - Auto-port detection
   - Native window

3. **Simplify licensing**
   - Switch to 16-char HMAC codes
   - Use Windows Registry for Machine ID
   - Remove base64 encoding complexity

4. **Improve backup system**
   - Add integrity checks (like BROMS)
   - Optional: add cloud folder support

### Implementation Priority:

| Change | Difficulty | Impact | Priority |
|--------|-----------|--------|----------|
| One-folder build | Easy | High (cleaner build) | 🔴 High |
| pywebview | Medium | High (professional UI) | 🔴 High |
| Short license codes | Medium | High (user-friendly) | 🟠 Medium |
| Registry Machine ID | Easy | Medium (stability) | 🟠 Medium |
| Backup verification | Easy | Low (nice-to-have) | 🟡 Low |
| Cloud sync | Hard | Low (not essential) | 🟡 Low |

---

## Quick Wins (Easiest to Implement)

1. ✅ **Switch to one-folder build** (5 minutes)
   - Change `.spec` file: use COLLECT instead of EXE
   
2. ✅ **Add pywebview** (1-2 hours)
   - Create `desktop.py` like BROMS
   - Auto-port detection
   - Keep all backend code unchanged

3. ✅ **Simplify license codes** (2-3 hours)
   - Copy BROMS' `compute_code()` and `identify()` functions
   - Adapt to UPVC Pro's needs
   - Reduce code length from 128+ to 16 chars

4. ✅ **Use Registry Machine ID** (1 hour)
   - Copy BROMS' `_raw_machine_guid()` function
   - Hash with namespace
   - More stable than MAC address

---

## Conclusion

**BROMS' approach is definitively simpler and more elegant.**

Key takeaway: The **one-folder + pywebview** combination is significantly better than the single-EXE browser approach. It avoids all the PyInstaller bundling complexity we hit and gives a more professional, native-looking application.

**Recommendation**: For your next EXE project (or UPVC Pro v1.1), adopt the BROMS architecture.
