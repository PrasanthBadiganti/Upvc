"""License management API endpoints."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import auth, licensing, models
from ..database import get_db

router = APIRouter(prefix="/api", tags=["license"])


@router.get("/license/info")
def get_license_info(current_user: models.User = Depends(auth.get_current_user)):
    """Get current license information (all authenticated users)"""
    return licensing.get_license_info()


@router.get("/license/machine-id")
def get_machine_id(current_user: models.User = Depends(auth.get_current_user)):
    """Get machine ID for this installation (all authenticated users)"""
    return {
        "machine_id": licensing.get_machine_id(),
        "message": "Copy this Machine ID when requesting a license key"
    }


@router.post("/license/activate")
def activate_license_endpoint(
    license_code: str,
    current_user: models.User = Depends(auth.get_current_user)
):
    """Activate a license code (requires authentication)"""
    result = licensing.activate_license(license_code)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    return result


@router.post("/license/deactivate")
def deactivate_license_endpoint(
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """Deactivate current license (SuperAdmin only)"""
    result = licensing.deactivate_license()
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    return result
