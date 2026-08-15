"""
Enhanced backup and restore (BROMS-style).

Strategy: Backup & Restore + optional cloud-folder sync.

Each backup:
1. Checkpoints WAL where possible
2. Uses SQLite backup API to create consistent snapshot
3. Runs PRAGMA integrity_check
4. Confirms core UPVC tables exist
5. Optionally copies verified snapshot to configured cloud folder
6. Prunes old files according to retention settings

Schedules: OFF, HOURLY, SIX_HOURLY, DAILY
Cloud: Optional Google Drive / OneDrive / Dropbox synced folder
"""
import shutil
import sqlite3
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

from .database import DB_PATH, BACKEND_DIR, get_connection, db_cursor

# Backup configuration
BACKUP_DIR = BACKEND_DIR / "backups"
BACKUP_DIR.mkdir(exist_ok=True)

# Schedule options -> interval in seconds (0 = off)
SCHEDULES = {"OFF": 0, "HOURLY": 3600, "SIX_HOURLY": 6 * 3600, "DAILY": 24 * 3600}
KEEP_DEFAULT = 30  # regular backups retained (local + cloud)
PRERESTORE_KEEP = 10  # pre-restore safety copies retained

# Core tables that must exist for valid UPVC database
CORE_TABLES = {
    "users",
    "customers",
    "quotations",
    "invoices",
    "payments",
}


def _snapshot(dest: Path) -> None:
    """Write a consistent copy of live DB using SQLite backup API.

    Works correctly even with WAL active and concurrent writes.
    Checkpoints WAL first so snapshot is fully up to date.
    """
    src = sqlite3.connect(str(DB_PATH))
    try:
        # Checkpoint WAL if active
        try:
            src.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        except Exception:
            pass

        # Create backup
        dst = sqlite3.connect(str(dest))
        try:
            src.backup(dst)
        finally:
            dst.close()
    finally:
        src.close()


def _verify_db(path: Path) -> tuple[bool, str]:
    """Verify backup/restore source is valid.

    Must pass integrity_check AND contain core UPVC tables.
    Header magic alone is not enough.
    """
    try:
        c = sqlite3.connect(str(path))
        try:
            # Integrity check
            res = c.execute("PRAGMA integrity_check").fetchone()
            ok = (res[0] if res else "").lower()
            if ok != "ok":
                return False, f"integrity check failed: {res[0] if res else 'unknown'}"

            # Check core tables
            core = {
                r[0]
                for r in c.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' "
                    "AND name IN ('users','customers','quotations','invoices','payments')"
                ).fetchall()
            }

            if len(core) < len(CORE_TABLES):
                missing = CORE_TABLES - core
                return (
                    False,
                    f"missing core tables: {', '.join(sorted(missing))} — not a valid UPVC database",
                )

            return True, "ok"
        finally:
            c.close()
    except Exception as e:
        return False, str(e)


def _prune(folder: Path, pattern: str, keep: int) -> int:
    """Keep newest `keep` files matching pattern; delete the rest. keep<=0 disables."""
    if keep <= 0:
        return 0

    files = sorted(folder.glob(pattern), key=lambda f: f.stat().st_mtime, reverse=True)
    removed = 0
    for f in files[keep:]:
        try:
            f.unlink()
            removed += 1
        except Exception:
            pass

    return removed


def create_backup(cloud_folder: Optional[Path] = None) -> dict:
    """Create a backup snapshot.

    Args:
        cloud_folder: Optional path to synced cloud folder (Google Drive, OneDrive, etc.)

    Returns:
        Dict with backup info and status
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    local_file = BACKUP_DIR / f"upvc_backup_{timestamp}.db"

    try:
        # Create snapshot
        _snapshot(local_file)

        # Verify it
        ok, msg = _verify_db(local_file)
        if not ok:
            local_file.unlink(missing_ok=True)
            return {"success": False, "error": f"backup verification failed: {msg}"}

        # Optionally copy to cloud folder
        cloud_file = None
        if cloud_folder and cloud_folder.exists():
            try:
                cloud_file = cloud_folder / f"upvc_backup_{timestamp}.db"
                shutil.copy2(local_file, cloud_file)
            except Exception as e:
                # Cloud copy failed, but local backup succeeded
                pass

        # Prune old backups
        _prune(BACKUP_DIR, "upvc_backup_*.db", KEEP_DEFAULT)
        if cloud_folder and cloud_folder.exists():
            _prune(cloud_folder, "upvc_backup_*.db", KEEP_DEFAULT)

        return {
            "success": True,
            "filename": local_file.name,
            "timestamp": timestamp,
            "cloud_synced": cloud_file is not None,
            "size_mb": round(local_file.stat().st_size / (1024 * 1024), 2),
        }

    except Exception as e:
        local_file.unlink(missing_ok=True)
        return {"success": False, "error": str(e)}


def list_backups() -> list[dict]:
    """List available backups."""
    backups = []
    for f in sorted(BACKUP_DIR.glob("upvc_backup_*.db"), reverse=True):
        try:
            stat = f.stat()
            backups.append(
                {
                    "filename": f.name,
                    "timestamp": f.stem.replace("upvc_backup_", ""),
                    "size_mb": round(stat.st_size / (1024 * 1024), 2),
                    "created": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                }
            )
        except Exception:
            pass

    return backups


def restore_backup(filename: str, cloud_folder: Optional[Path] = None) -> dict:
    """Restore from a backup file.

    Before restore:
    - Creates pre-restore safety snapshot
    - Verifies source backup

    After restore:
    - Application must be restarted
    """
    backup_file = BACKUP_DIR / filename

    if not backup_file.exists():
        return {"success": False, "error": f"backup file not found: {filename}"}

    # Verify source
    ok, msg = _verify_db(backup_file)
    if not ok:
        return {"success": False, "error": f"backup verification failed: {msg}"}

    try:
        # Create pre-restore safety snapshot
        safety_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safety_file = BACKUP_DIR / f"upvc_backup_prerestore_{safety_timestamp}.db"
        _snapshot(safety_file)

        # Restore
        src = sqlite3.connect(str(backup_file))
        try:
            dst = sqlite3.connect(str(DB_PATH))
            try:
                src.backup(dst)
            finally:
                dst.close()
        finally:
            src.close()

        # Prune pre-restore backups (keep 10)
        _prune(BACKUP_DIR, "upvc_backup_prerestore_*.db", PRERESTORE_KEEP)

        return {
            "success": True,
            "message": "Backup restored successfully. Please restart the application.",
            "safety_backup": safety_file.name,
        }

    except Exception as e:
        return {"success": False, "error": f"restore failed: {str(e)}"}


def export_backup(filename: str, export_path: Path) -> dict:
    """Export a backup to external location."""
    backup_file = BACKUP_DIR / filename

    if not backup_file.exists():
        return {"success": False, "error": "backup file not found"}

    try:
        export_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(backup_file, export_path)
        return {
            "success": True,
            "exported_to": str(export_path),
            "size_mb": round(export_path.stat().st_size / (1024 * 1024), 2),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def delete_backup(filename: str) -> dict:
    """Delete a backup file (SuperAdmin only)."""
    backup_file = BACKUP_DIR / filename

    if not backup_file.exists():
        return {"success": False, "error": "backup file not found"}

    try:
        backup_file.unlink()
        return {"success": True, "message": f"backup deleted: {filename}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def get_database_info() -> dict:
    """Get current database info."""
    try:
        c = get_connection()
        try:
            # Database size
            size_bytes = Path(DB_PATH).stat().st_size
            size_mb = round(size_bytes / (1024 * 1024), 2)

            # Table counts
            tables = {
                r[0]: c.execute(f"SELECT COUNT(*) FROM {r[0]}").fetchone()[0]
                for r in c.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
                ).fetchall()
            }

            # Last modified
            last_modified = datetime.fromtimestamp(Path(DB_PATH).stat().st_mtime).isoformat()

            return {
                "success": True,
                "path": str(DB_PATH),
                "size_mb": size_mb,
                "last_modified": last_modified,
                "table_counts": tables,
                "total_rows": sum(tables.values()),
            }
        finally:
            c.close()
    except Exception as e:
        return {"success": False, "error": str(e)}


# Cloud folder configuration (stored in settings)
def save_cloud_folder_config(folder_path: Optional[str]) -> dict:
    """Save cloud folder configuration."""
    try:
        from .settings_store import set_setting

        if folder_path:
            path = Path(folder_path)
            if not path.exists():
                return {"success": False, "error": "folder does not exist"}
            set_setting("backup_cloud_folder", str(path))
        else:
            set_setting("backup_cloud_folder", None)

        return {"success": True, "message": "cloud folder configured"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def get_cloud_folder_config() -> Optional[Path]:
    """Get configured cloud folder."""
    try:
        from .settings_store import get_setting

        folder_str = get_setting("backup_cloud_folder")
        return Path(folder_str) if folder_str else None
    except Exception:
        return None
