"""Authentication and authorization utilities"""

from datetime import datetime, timedelta
from typing import Optional
from passlib.context import CryptContext
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer
from sqlalchemy.orm import Session

from . import models, schemas
from .database import get_db

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT configuration
SECRET_KEY = "your-secret-key-change-this-in-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 480  # 8 hours

security = HTTPBearer()


def hash_password(password: str) -> str:
    """Hash password"""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password"""
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(user_id: int, username: str, role: str, expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT token"""
    if expires_delta is None:
        expires_delta = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    expire = datetime.utcnow() + expires_delta
    to_encode = {"sub": username, "user_id": user_id, "role": role, "exp": expire}

    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_token(token: str) -> dict:
    """Verify JWT token and return payload"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")


async def get_current_user(credentials = Depends(security), db: Session = Depends(get_db)) -> models.User:
    """Get current authenticated user"""
    token = credentials.credentials
    payload = verify_token(token)
    user_id = payload.get("user_id")

    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="User is inactive")

    return user


def require_permission(resource: str, action: str):
    """Decorator to check permission"""
    async def permission_checker(current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
        from .rbac import check_permission

        if not check_permission(db, current_user.id, resource, action):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: {action} on {resource}"
            )
        return current_user

    return permission_checker
