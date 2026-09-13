"""
JWT Authentication utilities for EventScout API.

Provides:
- Password hashing/verification via bcrypt
- JWT token creation and decoding
- FastAPI dependency for extracting the current authenticated user
"""

import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import bcrypt
from dotenv import load_dotenv
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

load_dotenv()

logger = logging.getLogger("EventScoutAuth")

# ------------------------------------------------------------------
# Configuration
# ------------------------------------------------------------------

SECRET_KEY: str = os.getenv(
    "JWT_SECRET_KEY", "eventscout_dev_secret_key_change_in_production_32chars_minimum"
)
ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
EXPIRE_DAYS: int = int(os.getenv("JWT_EXPIRE_DAYS", "7"))

# HTTP Bearer token extractor (reads Authorization: Bearer <token>)
_bearer_scheme = HTTPBearer()


# ------------------------------------------------------------------
# Password utilities
# ------------------------------------------------------------------


def hash_password(plain_password: str) -> str:
    """Hash a plain-text password using bcrypt. Returns the hash string."""
    pwd_bytes = plain_password.encode("utf-8")[:72]
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pwd_bytes, salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Return True if plain_password matches the bcrypt hash."""
    try:
        pwd_bytes = plain_password.encode("utf-8")[:72]
        hashed_bytes = hashed_password.encode("utf-8")
        return bcrypt.checkpw(pwd_bytes, hashed_bytes)
    except Exception:
        return False


# ------------------------------------------------------------------
# JWT utilities
# ------------------------------------------------------------------


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a signed JWT containing the provided data payload.
    Adds an 'exp' (expiry) claim automatically.
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta if expires_delta else timedelta(days=EXPIRE_DAYS)
    )
    to_encode["exp"] = expire
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> Dict[str, Any]:
    """
    Decode and validate a JWT. Raises JWTError on invalid/expired tokens.
    """
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])


# ------------------------------------------------------------------
# FastAPI dependency
# ------------------------------------------------------------------


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
) -> Dict[str, Any]:
    """
    FastAPI dependency that extracts and validates the Bearer JWT.

    Usage in a route:
        @router.get("/protected")
        async def protected(current_user = Depends(get_current_user)):
            ...

    The returned dict contains at minimum:
        {"sub": "<user_id>", "email": "<user_email>"}

    Security note: The backend derives identity from the token.
    The frontend cannot supply or modify the user identity.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated. Please log in.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_token(credentials.credentials)
        user_id: str = payload.get("sub")
        email: str = payload.get("email")
        username: Optional[str] = payload.get("username")
        is_admin: bool = payload.get("is_admin", False)
        if user_id is None or email is None:
            raise credentials_exception
        user_dict = {"id": user_id, "email": email, "is_admin": is_admin}
        if username:
            user_dict["username"] = username
        return user_dict
    except JWTError:
        raise credentials_exception


def get_current_admin_user(
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    FastAPI dependency that ensures the authenticated user possesses admin privileges.
    Queries the database directly to ensure instant role synchronization.
    """
    from eventscout.database.user_db import UserDatabase

    db = UserDatabase()
    user_doc = db.find_by_id(current_user["id"])
    if not user_doc or not user_doc.get("is_admin", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Admin privileges required to perform this action.",
        )
    return user_doc


_optional_bearer_scheme = HTTPBearer(auto_error=False)


def get_optional_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_optional_bearer_scheme),
) -> Optional[Dict[str, Any]]:
    """
    FastAPI dependency that extracts and validates the Bearer JWT if present,
    returning None if no token or an invalid token is provided.
    Enables endpoints to serve personalized content to logged-in users while
    remaining open to anonymous users.
    """
    if not credentials:
        return None
    try:
        payload = decode_token(credentials.credentials)
        user_id: str = payload.get("sub")
        email: str = payload.get("email")
        if not user_id or not email:
            return None
        from eventscout.database.user_db import UserDatabase
        user_db = UserDatabase()
        user_doc = user_db.find_by_id(user_id)
        if user_doc:
            user_doc["id"] = str(user_doc.get("_id", user_id))
            return user_doc
        return {"id": user_id, "email": email, "is_admin": payload.get("is_admin", False)}
    except Exception:
        return None

