"""
Viewer PC mode (BROMS-style read-only viewer architecture).

On a Viewer PC (VIEWER license):
- No business data of its own — local DB is a disposable mirror
- Auto-detects cloud folder (Google Drive default)
- Auto-loads latest backup on startup
- Can refresh from cloud folder on demand
- All business endpoints return read-only or are blocked
- Only Viewer-licensed users can log in

Master PC (MASTER license):
- Normal operation with all features
- Backups auto-synced to cloud folder
- Viewers pull from cloud folder

This enables a Master PC + many Viewer PCs architecture:
  MASTER PC                    CLOUD FOLDER              VIEWER PC(s)
  data/upvc.db ──backup───→    upvc_backup_*.db  ──sync──→ mirror in viewer's local DB
  (all writes)                  (auto/manual)              (read-only access)
"""
from pathlib import Path
from typing import Optional

from .database import DATA_DIR, DB_PATH

DEFAULT_VIEWER_FOLDER = Path("G:/My Drive/UPVCBackups")


def _detect_cloud_folder() -> Optional[Path]:
    r"""Auto-detect cloud folder (Google Drive default).

    Checks for common cloud sync folders in order:
    1. G:\My Drive\UPVCBackups (Google Drive common)
    2. C:\Users\...\OneDrive\UPVCBackups (OneDrive)
    3. C:\Users\...\Dropbox\UPVCBackups (Dropbox)
    """
    # Google Drive (varies per system: G:, H:, etc.)
    for drive_letter in ["G", "H", "I", "D", "E", "F"]:
        google_path = Path(f"{drive_letter}:/My Drive/UPVCBackups")
        if google_path.exists():
            return google_path

    # OneDrive
    onedrive_base = Path.home() / "OneDrive"
    if onedrive_base.exists():
        onedrive_path = onedrive_base / "UPVCBackups"
        if onedrive_path.exists():
            return onedrive_path

    # Dropbox
    dropbox_base = Path.home() / "Dropbox"
    if dropbox_base.exists():
        dropbox_path = dropbox_base / "UPVCBackups"
        if dropbox_path.exists():
            return dropbox_path

    return None


def get_viewer_source_path() -> Optional[Path]:
    """Get configured viewer source folder path.

    Checks in order:
    1. data/viewer_source.json (custom configuration)
    2. Auto-detected cloud folder (default)
    """
    import json

    viewer_config_file = DATA_DIR / "viewer_source.json"

    # Check for custom configuration
    if viewer_config_file.exists():
        try:
            with open(viewer_config_file, "r") as f:
                config = json.load(f)
            folder_str = config.get("folder")
            if folder_str:
                path = Path(folder_str)
                if path.exists():
                    return path
        except Exception:
            pass

    # Fall back to auto-detection
    detected = _detect_cloud_folder()
    if detected:
        return detected

    return None


def save_viewer_source_path(folder_path: Optional[str]) -> dict:
    """Save viewer cloud folder configuration."""
    import json

    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        viewer_config_file = DATA_DIR / "viewer_source.json"

        if folder_path:
            path = Path(folder_path)
            if not path.exists():
                return {"success": False, "error": "folder does not exist"}

            config = {"folder": str(path)}
            with open(viewer_config_file, "w") as f:
                json.dump(config, f)
        else:
            viewer_config_file.unlink(missing_ok=True)

        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}


def get_latest_backup(folder: Path) -> Optional[Path]:
    """Get the most recent backup file in folder."""
    try:
        backups = sorted(
            folder.glob("upvc_backup_*.db"),
            key=lambda f: f.stat().st_mtime,
            reverse=True,
        )
        return backups[0] if backups else None
    except Exception:
        return None


def refresh_viewer_database(source_folder: Optional[Path] = None) -> dict:
    """Refresh viewer's local database from latest backup in cloud folder.

    This is safe to call on a Viewer PC:
    - Loads latest backup from cloud folder
    - Replaces viewer's local DB
    - User must re-login after refresh
    """
    import shutil
    import sqlite3

    try:
        # Get source folder
        if not source_folder:
            source_folder = get_viewer_source_path()

        if not source_folder or not source_folder.exists():
            return {
                "success": False,
                "error": "cloud folder not configured or not accessible",
            }

        # Find latest backup
        latest = get_latest_backup(source_folder)
        if not latest:
            return {"success": False, "error": "no backups found in cloud folder"}

        # Verify backup is valid
        try:
            c = sqlite3.connect(str(latest))
            try:
                res = c.execute("PRAGMA integrity_check").fetchone()
                if (res[0] if res else "").lower() != "ok":
                    return {"success": False, "error": "backup integrity check failed"}
            finally:
                c.close()
        except Exception as e:
            return {"success": False, "error": f"backup verification failed: {str(e)}"}

        # Restore to viewer's local DB
        try:
            # Backup current viewer DB first (safety)
            if DB_PATH.exists():
                backup_path = DB_PATH.with_suffix(".db.bak")
                shutil.copy2(DB_PATH, backup_path)

            # Copy latest backup to viewer's DB
            shutil.copy2(latest, DB_PATH)

            from datetime import datetime

            timestamp = latest.stat().st_mtime
            data_timestamp = datetime.fromtimestamp(timestamp).isoformat()

            return {
                "success": True,
                "message": "viewer database refreshed",
                "data_timestamp": data_timestamp,
                "backup_file": latest.name,
                "safety_backup": backup_path.name if DB_PATH.exists() else None,
            }

        except Exception as e:
            return {"success": False, "error": f"database refresh failed: {str(e)}"}

    except Exception as e:
        return {"success": False, "error": str(e)}


def get_viewer_status() -> dict:
    """Get viewer PC status.

    Called on first launch to check if cloud folder is available
    and optionally auto-load latest backup.
    """
    source_folder = get_viewer_source_path()

    if not source_folder:
        return {
            "configured": False,
            "folder": None,
            "latest_backup": None,
            "data_timestamp": None,
        }

    latest = get_latest_backup(source_folder)
    if not latest:
        return {
            "configured": True,
            "folder": str(source_folder),
            "latest_backup": None,
            "data_timestamp": None,
            "message": "no backups found",
        }

    try:
        from datetime import datetime

        timestamp = latest.stat().st_mtime
        data_timestamp = datetime.fromtimestamp(timestamp).isoformat()

        return {
            "configured": True,
            "folder": str(source_folder),
            "latest_backup": latest.name,
            "data_timestamp": data_timestamp,
            "size_mb": round(latest.stat().st_size / (1024 * 1024), 2),
        }
    except Exception as e:
        return {
            "configured": True,
            "folder": str(source_folder),
            "error": str(e),
        }
