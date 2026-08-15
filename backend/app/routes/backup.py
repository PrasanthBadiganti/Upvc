"""Backup & Restore API endpoints (BROMS-style)."""
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
from ..auth import get_current_user
from ..database import get_db
from ..models import User
from ..rbac import require_permission

router = APIRouter(prefix="/api/backup", tags=["backup"])


class CloudFolderConfig(BaseModel):
    """Cloud folder configuration."""

    folder_path: str | None = None


@router.get("/database-info")
def get_db_info(current_user: User = Depends(get_current_user)):
    """Get current database info (all authenticated users)."""
    return get_database_info()


@router.post("/create")
def create_backup_endpoint(
    current_user: User = Depends(require_permission("user", "read")),
):
    """Create manual backup (Admin+ with user:read permission)."""
    cloud_folder = get_cloud_folder_config()
    return create_backup(cloud_folder=cloud_folder)


@router.get("/list")
def list_backups_endpoint(
    current_user: User = Depends(require_permission("user", "read")),
):
    """List available backups (Admin+ with user:read permission)."""
    return {"backups": list_backups()}


@router.delete("/delete/{filename}")
def delete_backup_endpoint(
    filename: str,
    current_user: User = Depends(require_permission("user", "delete")),
):
    """Delete a backup (SuperAdmin only with user:delete permission)."""
    result = delete_backup(filename)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    return result


@router.post("/restore/{filename}")
def restore_backup_endpoint(
    filename: str,
    current_user: User = Depends(require_permission("user", "delete")),
):
    """Restore from backup (SuperAdmin only with user:delete permission).

    Important: Application must be restarted after restore.
    """
    result = restore_backup(filename)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    return result


@router.post("/export/{filename}")
def export_backup_endpoint(
    filename: str,
    export_path: str,
    current_user: User = Depends(require_permission("user", "read")),
):
    """Export backup to external location (Admin+ with user:read permission)."""
    result = export_backup(filename, Path(export_path))
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    return result


@router.get("/cloud/config")
def get_cloud_config(
    current_user: User = Depends(require_permission("user", "read")),
):
    """Get cloud folder configuration (Admin+ with user:read permission)."""
    folder = get_cloud_folder_config()
    return {
        "configured": folder is not None,
        "folder": str(folder) if folder else None,
    }


@router.put("/cloud/config")
def set_cloud_config(
    config: CloudFolderConfig,
    current_user: User = Depends(require_permission("user", "update")),
):
    """Set cloud folder configuration (Admin+ with user:update permission).

    Example: /api/backup/cloud/config
    Body: {"folder_path": "G:/My Drive/UPVCBackups"}
    """
    result = save_cloud_folder_config(config.folder_path)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    return result
