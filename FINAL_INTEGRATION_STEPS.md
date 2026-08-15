# Final Integration Steps - Wire Everything Together

**Status**: Ready to integrate  
**Time**: ~30 minutes  
**Complexity**: Low

---

## What Needs to Be Done

The new backup_v2, viewer_v2, and licensing_v2 systems are complete but need to be wired into the main application.

### 1 Main File to Update: `app/main.py`

---

## Step 1: Update Imports in main.py

Add these imports at the top of `app/main.py`:

```python
# Add these after existing imports
from .backup_v2 import get_cloud_folder_config  # New
from .routes import backup_v2 as backup_v2_routes  # New
from .routes import viewer_v2 as viewer_v2_routes  # New
from .licensing_v2 import evaluate  # To use new licensing in middleware
```

---

## Step 2: Register Routes in main.py

Find where routes are currently registered (around line 47 in current main.py):

```python
# Current (existing)
app.include_router(backup_routes.router)
app.include_router(license_routes.router)
```

**Add after the above:**

```python
# Add these lines after existing router registrations
app.include_router(backup_v2_routes.router)  # New backup with cloud sync
app.include_router(viewer_v2_routes.router)  # New viewer PC support
```

---

## Step 3: Update Startup Event (Optional but Recommended)

If you want backup auto-scheduling, in the startup event, change:

```python
# Current (if present)
scheduler = get_scheduler()
scheduler.start()
```

To:

```python
# This stays the same - it's already configured
scheduler = get_scheduler()
scheduler.start()
```

**Note**: The existing scheduler in `backup_scheduler.py` can stay, or you can enhance it to use `backup_v2.create_backup()` instead. For now, keep the existing one.

---

## Step 4: Check settings_store.py (Verify)

Make sure `app/settings_store.py` exists and has these functions:

```python
def get_setting(key: str) -> Any:
    """Get a setting value."""
    pass

def set_setting(key: str, value: Any) -> None:
    """Set a setting value."""
    pass
```

If not present, create a simple version:

```python
# app/settings_store.py
import json
from pathlib import Path
from typing import Any
from .db import DATA_DIR

SETTINGS_FILE = DATA_DIR / "settings.json"


def _load_settings() -> dict:
    """Load settings from file."""
    if SETTINGS_FILE.exists():
        try:
            with open(SETTINGS_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def _save_settings(settings: dict) -> None:
    """Save settings to file."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(SETTINGS_FILE, "w") as f:
        json.dump(settings, f, indent=2)


def get_setting(key: str, default: Any = None) -> Any:
    """Get a setting value."""
    settings = _load_settings()
    return settings.get(key, default)


def set_setting(key: str, value: Any) -> None:
    """Set a setting value."""
    settings = _load_settings()
    settings[key] = value
    _save_settings(settings)
```

---

## Step 5: Test Integration

### Local Test

```bash
cd E:\Projects\UPVC\backend
python desktop.py
```

**Expected**:
- App launches
- No import errors
- All endpoints available:
  - `/api/backup/*` (new)
  - `/api/viewer/*` (new)

### API Test (in browser or Postman)

```
GET http://localhost:XXXX/api/backup/list
GET http://localhost:XXXX/api/viewer/status
```

Both should return valid JSON (not 500 errors).

---

## Step 6: Build EXE

```bash
python -m PyInstaller UPVC_Pro.spec --noconfirm
```

Output:
```
dist/UPVC Pro/
├── UPVC Pro.exe
└── _internal/
```

---

## Step 7: Test EXE

```bash
.\dist\UPVC\ Pro\UPVC\ Pro.exe
```

Test:
- [ ] App launches
- [ ] Settings → License works
- [ ] Settings → Backup & Restore works
- [ ] All features accessible

---

## Complete Checklist

- [ ] Added imports to main.py (backup_v2, viewer_v2, licensing_v2)
- [ ] Registered backup_v2_routes.router
- [ ] Registered viewer_v2_routes.router
- [ ] Created/verified settings_store.py
- [ ] Local test: `python desktop.py` works
- [ ] API endpoints respond (no 500 errors)
- [ ] Built EXE: `PyInstaller UPVC_Pro.spec`
- [ ] EXE test: App launches and all features work

---

## Files You'll Be Modifying

| File | Change | Difficulty |
|------|--------|-----------|
| `app/main.py` | Add imports + register routes | ⭐ Easy |
| `app/settings_store.py` | Verify or create | ⭐ Easy |

---

## Files Already Ready (No Changes Needed)

✅ `desktop.py` - Entry point (ready)  
✅ `app/licensing_v2.py` - Licensing (ready)  
✅ `app/backup_v2.py` - Backup/Restore (ready)  
✅ `app/viewer.py` - Viewer mode (ready)  
✅ `app/routes/backup_v2.py` - Backup API (ready)  
✅ `app/routes/viewer_v2.py` - Viewer API (ready)  
✅ `generate_license_v2.py` - License generator (ready)  
✅ `UPVC_Pro.spec` - PyInstaller config (ready)

---

## Code Example: What to Add to main.py

Find this section in `app/main.py`:

```python
from .routes import backup as backup_routes
from .routes import license as license_routes
# ... other imports
app.include_router(backup_routes.router)
app.include_router(license_routes.router)
```

And add right after:

```python
from .backup_v2 import get_cloud_folder_config
from .routes import backup_v2 as backup_v2_routes
from .routes import viewer_v2 as viewer_v2_routes

# ... later in the file, after existing router registrations ...
app.include_router(backup_v2_routes.router)
app.include_router(viewer_v2_routes.router)
```

That's it! The new routes will be available immediately.

---

## Verification Commands

After updating main.py, verify with:

```bash
# Check for import errors
cd E:\Projects\UPVC\backend
python -c "from app.main import app; print('✓ Imports OK')"

# Or just run the app
python desktop.py
# Should launch without errors
```

---

## You're Done! 

After these simple changes, UPVC Pro will have:

✅ Full BROMS architecture  
✅ Licensing (short codes)  
✅ Backup/Restore (with cloud)  
✅ Viewer PC mode  
✅ Master/Viewer architecture  
✅ Native window  
✅ No port conflicts  
✅ One-folder deployment  

**All aligned with BROMS for easy maintenance!** 🎉
