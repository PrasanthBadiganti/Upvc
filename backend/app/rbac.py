"""Role-Based Access Control (RBAC) utilities"""

from sqlalchemy.orm import Session
from . import models, schemas
from typing import Optional


# Role definitions with default permissions
ROLE_PERMISSIONS = {
    "SuperAdmin": {
        "customer": {"create": True, "read": True, "update": True, "delete": True},
        "quotation": {"create": True, "read": True, "update": True, "delete": True},
        "invoice": {"create": True, "read": True, "update": True, "delete": True},
        "payment": {"create": True, "read": True, "update": True, "delete": True},
        "credit_note": {"create": True, "read": True, "update": True, "delete": True},
        "debit_note": {"create": True, "read": True, "update": True, "delete": True},
        "vendor": {"create": True, "read": True, "update": True, "delete": True},
        "purchase_bill": {"create": True, "read": True, "update": True, "delete": True},
        "expense": {"create": True, "read": True, "update": True, "delete": True},
        "catalog": {"create": True, "read": True, "update": True, "delete": True},
        "user": {"create": True, "read": True, "update": True, "delete": True},
        "role": {"create": True, "read": True, "update": True, "delete": True},
    },
    "Admin": {
        "customer": {"create": True, "read": True, "update": True, "delete": True},
        "quotation": {"create": True, "read": True, "update": True, "delete": True},
        "invoice": {"create": True, "read": True, "update": True, "delete": True},
        "payment": {"create": True, "read": True, "update": True, "delete": True},
        "credit_note": {"create": True, "read": True, "update": True, "delete": True},
        "debit_note": {"create": True, "read": True, "update": True, "delete": True},
        "vendor": {"create": True, "read": True, "update": True, "delete": True},
        "purchase_bill": {"create": True, "read": True, "update": True, "delete": True},
        "expense": {"create": True, "read": True, "update": True, "delete": True},
        "catalog": {"create": True, "read": True, "update": True, "delete": True},
        "user": {"create": True, "read": True, "update": False, "delete": False},  # Can read users but not modify
        "role": {"create": False, "read": True, "update": False, "delete": False},  # Can view roles only
    },
    "Manager": {
        "customer": {"create": True, "read": True, "update": True, "delete": False},
        "quotation": {"create": True, "read": True, "update": True, "delete": False},
        "invoice": {"create": False, "read": True, "update": False, "delete": False},
        "payment": {"create": True, "read": True, "update": False, "delete": False},
        "credit_note": {"create": False, "read": True, "update": False, "delete": False},
        "debit_note": {"create": False, "read": True, "update": False, "delete": False},
        "vendor": {"create": False, "read": True, "update": False, "delete": False},
        "purchase_bill": {"create": False, "read": True, "update": False, "delete": False},
        "expense": {"create": True, "read": True, "update": True, "delete": False},
        "catalog": {"create": False, "read": True, "update": False, "delete": False},
        "user": {"create": False, "read": True, "update": False, "delete": False},
        "role": {"create": False, "read": True, "update": False, "delete": False},
    },
    "DataEntry": {
        "customer": {"create": True, "read": True, "update": False, "delete": False},
        "quotation": {"create": True, "read": True, "update": False, "delete": False},
        "invoice": {"create": False, "read": True, "update": False, "delete": False},
        "payment": {"create": False, "read": True, "update": False, "delete": False},
        "credit_note": {"create": False, "read": True, "update": False, "delete": False},
        "debit_note": {"create": False, "read": True, "update": False, "delete": False},
        "vendor": {"create": False, "read": True, "update": False, "delete": False},
        "purchase_bill": {"create": False, "read": True, "update": False, "delete": False},
        "expense": {"create": True, "read": True, "update": False, "delete": False},
        "catalog": {"create": False, "read": True, "update": False, "delete": False},
        "user": {"create": False, "read": False, "update": False, "delete": False},
        "role": {"create": False, "read": False, "update": False, "delete": False},
    },
}


def initialize_roles_and_permissions(db: Session):
    """Initialize default roles and permissions in database"""

    for role_name, permissions in ROLE_PERMISSIONS.items():
        # Check if role exists
        existing_role = db.query(models.Role).filter(models.Role.name == role_name).first()

        if existing_role:
            # Delete existing permissions and recreate them
            db.query(models.Permission).filter(models.Permission.role_id == existing_role.id).delete()
            db.commit()
        else:
            # Create new role
            existing_role = models.Role(name=role_name, description=f"{role_name} role")
            db.add(existing_role)
            db.commit()
            db.refresh(existing_role)

        # Add permissions for this role
        for resource, perms in permissions.items():
            permission = models.Permission(
                role_id=existing_role.id,
                resource=resource,
                create=perms.get("create", False),
                read=perms.get("read", False),
                update=perms.get("update", False),
                delete=perms.get("delete", False),
            )
            db.add(permission)

        db.commit()


def get_user_permissions(db: Session, user_id: int) -> dict:
    """Get all permissions for a user"""
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        return {}

    permissions = db.query(models.Permission).filter(
        models.Permission.role_id == user.role_id
    ).all()

    perms_dict = {}
    for perm in permissions:
        perms_dict[perm.resource] = {
            "create": perm.create,
            "read": perm.read,
            "update": perm.update,
            "delete": perm.delete,
        }

    return perms_dict


def check_permission(db: Session, user_id: int, resource: str, action: str) -> bool:
    """Check if user has permission for a specific resource and action"""
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        return False

    if action not in ["create", "read", "update", "delete"]:
        return False

    permission = db.query(models.Permission).filter(
        models.Permission.role_id == user.role_id,
        models.Permission.resource == resource
    ).first()

    if not permission:
        return False

    return getattr(permission, action, False)


def get_user_role(db: Session, user_id: int) -> Optional[str]:
    """Get user's role name"""
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        return None

    role = db.query(models.Role).filter(models.Role.id == user.role_id).first()
    return role.name if role else None


def is_superadmin(db: Session, user_id: int) -> bool:
    """Check if user is SuperAdmin"""
    return get_user_role(db, user_id) == "SuperAdmin"


def is_admin_or_above(db: Session, user_id: int) -> bool:
    """Check if user is Admin or SuperAdmin"""
    role = get_user_role(db, user_id)
    return role in ["Admin", "SuperAdmin"]
