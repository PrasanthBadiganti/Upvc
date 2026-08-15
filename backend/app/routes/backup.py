"""Backup and restore API endpoints"""

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, Query
from sqlalchemy.orm import Session

from .. import auth, backup, models
from ..backup_scheduler import get_scheduler
from ..database import get_db

router = APIRouter(prefix="/api", tags=["backup"])


@router.get("/backup/database-info")
def get_database_info(current_user: models.User = Depends(auth.get_current_user)):
    """Get current database information (all users)"""
    return backup.get_database_info()


@router.post("/backup/create")
def create_backup_manual(
    backup_name: str = Query(None),
    current_user: models.User = Depends(auth.require_permission("user", "read")),
    db: Session = Depends(get_db)
):
    """Create manual backup (Admin+ only)"""
    result = backup.create_backup(backup_name)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    return result


@router.get("/backup/list")
def list_backups(current_user: models.User = Depends(auth.require_permission("user", "read"))):
    """List all available backups (Admin+ only)"""
    result = backup.list_backups()
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    return result


@router.delete("/backup/delete/{backup_file}")
def delete_backup_file(
    backup_file: str,
    current_user: models.User = Depends(auth.require_permission("user", "delete")),
    db: Session = Depends(get_db)
):
    """Delete a backup file (SuperAdmin only)"""
    result = backup.delete_backup(backup_file)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    return result


@router.post("/backup/restore/{backup_file}")
def restore_backup_file(
    backup_file: str,
    current_user: models.User = Depends(auth.require_permission("user", "delete")),
    db: Session = Depends(get_db)
):
    """Restore database from backup (SuperAdmin only)"""
    result = backup.restore_backup(backup_file)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    return result


@router.get("/backup/scheduler/config")
def get_scheduler_config(current_user: models.User = Depends(auth.require_permission("user", "read"))):
    """Get backup scheduler configuration (Admin+ only)"""
    scheduler = get_scheduler()
    return scheduler.get_config()


@router.put("/backup/scheduler/config")
def update_scheduler_config(
    enabled: bool = Query(None),
    interval_hours: int = Query(None),
    current_user: models.User = Depends(auth.require_permission("user", "update")),
    db: Session = Depends(get_db)
):
    """Update backup scheduler configuration (Admin+ only)"""
    scheduler = get_scheduler()
    result = scheduler.update_config(enabled=enabled, interval_hours=interval_hours)
    return result


@router.post("/backup/scheduler/force")
def force_backup_now(
    current_user: models.User = Depends(auth.require_permission("user", "create")),
    db: Session = Depends(get_db)
):
    """Force an immediate backup (Admin+ only)"""
    scheduler = get_scheduler()
    result = scheduler.force_backup()
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    return result


@router.post("/backup/export/{backup_file}")
def export_backup_file(
    backup_file: str,
    export_path: str = Query(...),
    current_user: models.User = Depends(auth.require_permission("user", "read")),
    db: Session = Depends(get_db)
):
    """Export backup to external location (Admin+ only)"""
    result = backup.export_backup(backup_file, export_path)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    return result
