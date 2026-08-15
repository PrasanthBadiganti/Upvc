"""Database backup and restore functionality"""

import shutil
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional

from .database import DEFAULT_DB_PATH


BACKUP_DIR = DEFAULT_DB_PATH.parent / "backups"
MAX_BACKUPS = 10  # Keep only 10 most recent backups


def _ensure_backup_dir() -> Path:
    """Ensure backup directory exists"""
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    return BACKUP_DIR


def _get_backup_filename(timestamp: Optional[datetime] = None) -> str:
    """Generate backup filename with timestamp"""
    if timestamp is None:
        timestamp = datetime.now()
    return f"upvc_backup_{timestamp.strftime('%Y%m%d_%H%M%S')}.db"


def _cleanup_old_backups() -> None:
    """Keep only MAX_BACKUPS most recent backups"""
    backups = sorted(
        BACKUP_DIR.glob("upvc_backup_*.db"),
        key=lambda p: p.stat().st_mtime,
        reverse=True
    )
    for old_backup in backups[MAX_BACKUPS:]:
        try:
            old_backup.unlink()
        except OSError:
            pass


def create_backup(backup_name: Optional[str] = None) -> dict:
    """
    Create a database backup

    Args:
        backup_name: Optional custom backup name (without .db extension)

    Returns:
        Dictionary with backup info: {'success': bool, 'path': str, 'size': int, 'timestamp': str}
    """
    try:
        _ensure_backup_dir()

        if backup_name:
            backup_path = BACKUP_DIR / f"{backup_name}.db"
        else:
            backup_path = BACKUP_DIR / _get_backup_filename()

        # Verify source database exists
        if not DEFAULT_DB_PATH.exists():
            return {
                "success": False,
                "error": "Database file not found",
                "path": str(backup_path)
            }

        # Use SQLite backup API for consistency (no corruption risk)
        source_conn = sqlite3.connect(str(DEFAULT_DB_PATH))
        dest_conn = sqlite3.connect(str(backup_path))

        with dest_conn:
            source_conn.backup(dest_conn)

        source_conn.close()
        dest_conn.close()

        backup_size = backup_path.stat().st_size
        _cleanup_old_backups()

        return {
            "success": True,
            "path": str(backup_path),
            "size": backup_size,
            "timestamp": datetime.now().isoformat(),
            "filename": backup_path.name
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "path": str(backup_path) if 'backup_path' in locals() else None
        }


def restore_backup(backup_file: str) -> dict:
    """
    Restore database from backup

    Args:
        backup_file: Backup filename or full path

    Returns:
        Dictionary with restore info: {'success': bool, 'message': str}
    """
    try:
        # Handle both filename and full path
        if backup_file.startswith("/") or backup_file.startswith("\\") or ":" in backup_file:
            backup_path = Path(backup_file)
        else:
            backup_path = BACKUP_DIR / backup_file

        if not backup_path.exists():
            return {
                "success": False,
                "error": f"Backup file not found: {backup_file}"
            }

        if not backup_path.suffix == ".db":
            return {
                "success": False,
                "error": "Invalid backup file (must be .db)"
            }

        # Create backup of current database before restoring
        current_backup = create_backup("pre_restore_backup")
        if not current_backup.get("success"):
            return {
                "success": False,
                "error": "Failed to create pre-restore backup"
            }

        # Restore from backup
        source_conn = sqlite3.connect(str(backup_path))
        dest_conn = sqlite3.connect(str(DEFAULT_DB_PATH))

        with dest_conn:
            source_conn.backup(dest_conn)

        source_conn.close()
        dest_conn.close()

        return {
            "success": True,
            "message": "Database restored successfully",
            "restored_from": backup_path.name,
            "pre_restore_backup": current_backup.get("filename")
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def list_backups() -> dict:
    """
    List all available backups

    Returns:
        Dictionary with list of backups and metadata
    """
    try:
        _ensure_backup_dir()

        backups = []
        for backup_file in sorted(BACKUP_DIR.glob("upvc_backup_*.db"), reverse=True):
            size = backup_file.stat().st_size
            mtime = datetime.fromtimestamp(backup_file.stat().st_mtime)
            backups.append({
                "filename": backup_file.name,
                "path": str(backup_file),
                "size": size,
                "size_mb": round(size / (1024 * 1024), 2),
                "created": mtime.isoformat(),
                "created_formatted": mtime.strftime("%Y-%m-%d %H:%M:%S")
            })

        return {
            "success": True,
            "backups": backups,
            "count": len(backups),
            "backup_dir": str(BACKUP_DIR)
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def delete_backup(backup_file: str) -> dict:
    """
    Delete a backup file

    Args:
        backup_file: Backup filename

    Returns:
        Dictionary with result: {'success': bool, 'message': str}
    """
    try:
        backup_path = BACKUP_DIR / backup_file

        if not backup_path.exists():
            return {
                "success": False,
                "error": f"Backup file not found: {backup_file}"
            }

        backup_path.unlink()

        return {
            "success": True,
            "message": f"Backup deleted: {backup_file}"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def export_backup(backup_file: str, export_path: str) -> dict:
    """
    Export/copy a backup to external location

    Args:
        backup_file: Backup filename in backup folder
        export_path: Destination path to copy to

    Returns:
        Dictionary with result: {'success': bool, 'message': str}
    """
    try:
        backup_path = BACKUP_DIR / backup_file

        if not backup_path.exists():
            return {
                "success": False,
                "error": f"Backup file not found: {backup_file}"
            }

        export_dest = Path(export_path)
        export_dest.parent.mkdir(parents=True, exist_ok=True)

        shutil.copy2(str(backup_path), str(export_dest))

        return {
            "success": True,
            "message": f"Backup exported to: {export_path}",
            "exported_path": str(export_dest)
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def get_database_info() -> dict:
    """Get current database information"""
    try:
        if not DEFAULT_DB_PATH.exists():
            return {
                "exists": False,
                "error": "Database not found"
            }

        size = DEFAULT_DB_PATH.stat().st_size
        mtime = datetime.fromtimestamp(DEFAULT_DB_PATH.stat().st_mtime)

        # Get table count
        conn = sqlite3.connect(str(DEFAULT_DB_PATH))
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
        table_count = cursor.fetchone()[0]
        conn.close()

        return {
            "exists": True,
            "path": str(DEFAULT_DB_PATH),
            "size": size,
            "size_mb": round(size / (1024 * 1024), 2),
            "modified": mtime.isoformat(),
            "modified_formatted": mtime.strftime("%Y-%m-%d %H:%M:%S"),
            "tables": table_count
        }
    except Exception as e:
        return {
            "exists": False,
            "error": str(e)
        }
