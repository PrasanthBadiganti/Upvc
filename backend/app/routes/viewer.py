"""Viewer PC API endpoints (BROMS-style read-only viewers)."""
from fastapi import APIRouter, HTTPException, Depends
from pathlib import Path
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..viewer import (
    get_viewer_status,
    get_viewer_source_path,
    save_viewer_source_path,
    refresh_viewer_database,
)
from ..auth import get_current_user
from ..database import get_db
from ..models import User
from ..rbac import require_permission
from ..licensing import is_viewer_license

router = APIRouter(prefix="/api/viewer", tags=["viewer"])


class ViewerSourceConfig(BaseModel):
    """Viewer cloud folder configuration."""

    folder_path: str | None = None


@router.get("/status")
def viewer_status():
    """Get viewer PC status (no auth required).

    Checks if cloud folder is available and latest backup info.
    Called on first launch to auto-load latest backup.
    """
    return get_viewer_status()


@router.get("/source")
def get_viewer_source(current_user: User = Depends(get_current_user)):
    """Get configured viewer source folder (all authenticated users).

    Returns the cloud folder path that viewer is syncing from.
    """
    folder = get_viewer_source_path()
    return {
        "configured": folder is not None,
        "folder": str(folder) if folder else None,
    }


@router.put("/source")
def set_viewer_source(
    config: ViewerSourceConfig,
    current_user: User = Depends(require_permission("user", "update")),
):
    """Set viewer cloud folder (Admin+ with user:update permission).

    Example: /api/viewer/source
    Body: {"folder_path": "G:/My Drive/UPVCBackups"}
    """
    result = save_viewer_source_path(config.folder_path)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    return result


@router.post("/refresh")
def refresh_viewer(
    current_user: User = Depends(require_permission("user", "update")),
):
    """Refresh viewer database from latest cloud backup.

    Only on Viewer PCs. Loads latest backup from configured cloud folder.
    Application must be restarted after refresh.

    Admin+ with user:update permission (typically only on viewer PCs).
    """
    result = refresh_viewer_database()
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    return result


@router.get("/is-viewer")
def check_if_viewer_license(current_user: User = Depends(get_current_user)):
    """Check if this installation has Viewer license."""
    is_viewer = is_viewer_license()
    return {
        "is_viewer_license": is_viewer,
        "mode": "viewer" if is_viewer else "master",
    }
