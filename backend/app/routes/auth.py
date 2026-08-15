"""Authentication and User Management endpoints"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import models, schemas, auth, rbac
from ..database import get_db

router = APIRouter(prefix="/api", tags=["auth"])


@router.post("/login", response_model=schemas.Token)
def login(login_data: schemas.UserLogin, db: Session = Depends(get_db)):
    """Login endpoint"""
    user = db.query(models.User).filter(models.User.username == login_data.username).first()

    if not user or not auth.verify_password(login_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="User is inactive")

    role = db.query(models.Role).filter(models.Role.id == user.role_id).first()
    role_name = role.name if role else "Unknown"

    token = auth.create_access_token(user.id, user.username, role_name)

    return {
        "access_token": token,
        "token_type": "bearer",
        "user_id": user.id,
        "username": user.username,
        "role": role_name,
    }


@router.post("/users", response_model=schemas.UserRead)
def create_user(user_data: schemas.UserCreate, current_user: models.User = Depends(auth.require_permission("user", "create")), db: Session = Depends(get_db)):
    """Create new user (Admin/SuperAdmin only)"""

    # Check if username already exists
    existing_user = db.query(models.User).filter(models.User.username == user_data.username).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already exists")

    # Check if email already exists
    existing_email = db.query(models.User).filter(models.User.email == user_data.email).first()
    if existing_email:
        raise HTTPException(status_code=400, detail="Email already exists")

    # Create new user
    new_user = models.User(
        username=user_data.username,
        email=user_data.email,
        full_name=user_data.full_name,
        role_id=user_data.role_id,
        hashed_password=auth.hash_password(user_data.password),
        is_active=user_data.is_active,
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return new_user


@router.get("/users", response_model=list[schemas.UserRead])
def list_users(current_user: models.User = Depends(auth.require_permission("user", "read")), db: Session = Depends(get_db)):
    """List all users"""
    users = db.query(models.User).all()
    return users


@router.get("/users/{user_id}", response_model=schemas.UserRead)
def get_user(user_id: int, current_user: models.User = Depends(auth.require_permission("user", "read")), db: Session = Depends(get_db)):
    """Get user by ID"""
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.put("/users/{user_id}", response_model=schemas.UserRead)
def update_user(user_id: int, user_data: schemas.UserUpdate, current_user: models.User = Depends(auth.require_permission("user", "update")), db: Session = Depends(get_db)):
    """Update user (SuperAdmin can manage all, Admin can manage except admins)"""

    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Check authorization
    current_role = db.query(models.Role).filter(models.Role.id == current_user.role_id).first()
    target_role = db.query(models.Role).filter(models.Role.id == user.role_id).first()

    if current_role.name == "Admin" and target_role.name in ["SuperAdmin", "Admin"]:
        raise HTTPException(status_code=403, detail="Cannot modify SuperAdmin or Admin users")

    if user_data.full_name:
        user.full_name = user_data.full_name
    if user_data.email:
        user.email = user_data.email
    if user_data.role_id:
        user.role_id = user_data.role_id
    if user_data.is_active is not None:
        user.is_active = user_data.is_active

    db.commit()
    db.refresh(user)

    return user


@router.delete("/users/{user_id}", status_code=204)
def delete_user(user_id: int, current_user: models.User = Depends(auth.require_permission("user", "delete")), db: Session = Depends(get_db)):
    """Delete user (SuperAdmin only)"""

    current_role = db.query(models.Role).filter(models.Role.id == current_user.role_id).first()
    if current_role.name != "SuperAdmin":
        raise HTTPException(status_code=403, detail="Only SuperAdmin can delete users")

    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    db.delete(user)
    db.commit()

    return None


@router.get("/roles", response_model=list[schemas.RoleRead])
def list_roles(current_user: models.User = Depends(auth.require_permission("role", "read")), db: Session = Depends(get_db)):
    """List all roles"""
    roles = db.query(models.Role).all()
    return roles


@router.get("/roles/{role_id}", response_model=schemas.RoleRead)
def get_role(role_id: int, current_user: models.User = Depends(auth.require_permission("role", "read")), db: Session = Depends(get_db)):
    """Get role by ID"""
    role = db.query(models.Role).filter(models.Role.id == role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    return role


@router.get("/me", response_model=schemas.UserRead)
def get_current_user_info(current_user: models.User = Depends(auth.get_current_user)):
    """Get current user info"""
    return current_user


@router.get("/permissions")
def get_my_permissions(current_user: models.User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    """Get current user's permissions"""
    permissions = rbac.get_user_permissions(db, current_user.id)
    return permissions
