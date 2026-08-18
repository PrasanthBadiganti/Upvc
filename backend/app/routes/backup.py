"""Backup & Restore API endpoints.

No auth dependencies: UPVC Pro ships as a single-user desktop app with no
login, and the API binds to 127.0.0.1 on a random port. Guarding these routes
behind get_current_user made them permanently unreachable (403).
"""
from fastapi import APIRouter, HTTPException, Depends
from pathlib import Path
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..backup import (
    create_backup,
    list_backups,
    restore_backup,
    export_backup,
    delete_backup,
    get_database_info,
    get_cloud_folder_config,
    save_cloud_folder_config,
)
from ..database import get_db

router = APIRouter(prefix="/api/backup", tags=["backup"])


class CloudFolderConfig(BaseModel):
    """Cloud folder configuration."""

    folder_path: str | None = None


@router.get("/database-info")
def get_db_info():
    """Get current database info."""
    return get_database_info()


@router.post("/create")
def create_backup_endpoint():
    """Create manual backup."""
    cloud_folder = get_cloud_folder_config()
    return create_backup(cloud_folder=cloud_folder)


@router.get("/list")
def list_backups_endpoint():
    """List available backups."""
    return {"backups": list_backups()}


@router.delete("/delete/{filename}")
def delete_backup_endpoint(filename: str):
    """Delete a backup."""
    result = delete_backup(filename)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    return result


@router.post("/restore/{filename}")
def restore_backup_endpoint(filename: str):
    """Restore from backup.

    Important: Application must be restarted after restore.
    """
    result = restore_backup(filename)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    return result


@router.post("/export/{filename}")
def export_backup_endpoint(
    filename: str,
    export_path: str
):
    """Export backup to external location."""
    result = export_backup(filename, Path(export_path))
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    return result


@router.get("/cloud/config")
def get_cloud_config():
    """Get cloud folder configuration."""
    folder = get_cloud_folder_config()
    return {
        "configured": folder is not None,
        "folder": str(folder) if folder else None,
    }


@router.put("/cloud/config")
def set_cloud_config(config: CloudFolderConfig):
    """Set cloud folder configuration.

    Example: /api/backup/cloud/config
    Body: {"folder_path": "G:/My Drive/UPVCBackups"}
    """
    result = save_cloud_folder_config(config.folder_path)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    return result
