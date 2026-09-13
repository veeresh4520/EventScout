"""
Authentication router for EventScout API.

Endpoints:
    POST /auth/signup    — Create a new user account with username, email, password
    POST /auth/register  — Backward-compatible alias for user registration
    POST /auth/login     — Authenticate and receive a JWT
    GET  /auth/me        — Return the current user's public profile
"""

import logging
import re
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, field_validator, model_validator
from pymongo.errors import DuplicateKeyError

from api.auth import (
    create_access_token,
    get_current_user,
    hash_password,
    verify_password,
)
from eventscout.database.user_db import UserDatabase

logger = logging.getLogger("EventScoutAuthRouter")

router = APIRouter(prefix="/auth", tags=["Authentication"])


# ------------------------------------------------------------------
# Request / Response schemas
# ------------------------------------------------------------------


class SignupRequest(BaseModel):
    username: str
    email: EmailStr
    password: str

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        cleaned = v.strip()
        if len(cleaned) < 2:
            raise ValueError("Username must be at least 2 characters.")
        if len(cleaned) > 50:
            raise ValueError("Username cannot exceed 50 characters.")
        if not re.match(r"^[a-zA-Z0-9_\-]+$", cleaned):
            raise ValueError("Username can only contain alphanumeric characters, hyphens, and underscores.")
        return cleaned

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 6:
            raise ValueError("Password must be at least 6 characters.")
        return v


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    username: Optional[str] = None

    @field_validator("password")
    @classmethod
    def password_length(cls, v: str) -> str:
        if len(v) < 6:
            raise ValueError("Password must be at least 6 characters.")
        return v


class LoginRequest(BaseModel):
    email: Optional[str] = None
    username: Optional[str] = None
    password: str

    @model_validator(mode="after")
    def check_credentials(self) -> "LoginRequest":
        if not self.email and not self.username:
            raise ValueError("Email or username is required.")
        return self


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: Dict[str, Any]


def _build_public_user(user_doc: Dict[str, Any]) -> Dict[str, Any]:
    """Helper to construct safe user dictionary without password_hash."""
    return {
        "id": str(user_doc.get("id") or user_doc.get("_id")),
        "username": user_doc.get("username") or user_doc.get("email", "").split("@")[0],
        "email": user_doc.get("email"),
        "interests": user_doc.get("interests", []),
        "skills": user_doc.get("skills", []),
        "preferred_event_types": user_doc.get("preferred_event_types", []),
        "preferred_modes": user_doc.get("preferred_modes", []),
        "saved_event_ids": user_doc.get("saved_event_ids", []),
        "is_admin": bool(user_doc.get("is_admin", False)),
        "created_at": user_doc.get("created_at"),
    }


# ------------------------------------------------------------------
# Endpoints
# ------------------------------------------------------------------


@router.post(
    "/signup",
    status_code=status.HTTP_201_CREATED,
    summary="Sign up a new user account",
)
async def signup(body: SignupRequest) -> AuthResponse:
    """
    Creates a new user with username, email, and password.
    Passwords are safely hashed with bcrypt before MongoDB storage.
    Duplicate email addresses return 409 Conflict.
    Returns safe user object and JWT without exposing password_hash.
    """
    db = UserDatabase()
    password_hash = hash_password(body.password)

    try:
        user_doc = db.create_user(
            email=str(body.email),
            password_hash=password_hash,
            username=body.username,
        )
    except DuplicateKeyError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with that email address already exists.",
        )
    except Exception as exc:
        logger.error("Signup failed: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Signup failed. Please try again.",
        )

    token = create_access_token({
        "sub": user_doc["id"],
        "email": user_doc["email"],
        "username": user_doc.get("username"),
        "is_admin": bool(user_doc.get("is_admin", False)),
    })

    return AuthResponse(access_token=token, user=_build_public_user(user_doc))


@router.post(
    "/register",
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user account (alias)",
)
async def register(body: RegisterRequest) -> AuthResponse:
    """
    Backward-compatible registration endpoint.
    Passes through to user creation with bcrypt hashing.
    """
    db = UserDatabase()
    password_hash = hash_password(body.password)

    try:
        user_doc = db.create_user(
            email=str(body.email),
            password_hash=password_hash,
            username=body.username,
        )
    except DuplicateKeyError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with that email address already exists.",
        )
    except Exception as exc:
        logger.error("Registration failed: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed. Please try again.",
        )

    token = create_access_token({
        "sub": user_doc["id"],
        "email": user_doc["email"],
        "username": user_doc.get("username"),
        "is_admin": bool(user_doc.get("is_admin", False)),
    })

    return AuthResponse(access_token=token, user=_build_public_user(user_doc))


@router.post("/login", summary="Log in and receive a JWT token")
async def login(body: LoginRequest) -> AuthResponse:
    """
    Validates user credentials against stored bcrypt hash.
    Accepts either email or username in the request.
    Returns generic 401 on failure to prevent user enumeration.
    """
    from eventscout.utils.logging_config import structured_logger

    db = UserDatabase()
    identifier = body.email or body.username or ""
    user_doc = db.find_by_identifier(identifier)

    invalid_creds_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid email or password.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if not user_doc or not verify_password(body.password, user_doc.get("password_hash", "")):
        structured_logger.log_event(
            event_tag="AUTH_FAILURE",
            message="Failed login attempt for identifier",
            level=logging.WARNING,
            extra={"identifier": identifier}
        )
        raise invalid_creds_exc

    token = create_access_token({
        "sub": user_doc["id"],
        "email": user_doc["email"],
        "username": user_doc.get("username"),
        "is_admin": bool(user_doc.get("is_admin", False)),
    })

    structured_logger.log_event(
        event_tag="USER_LOGIN",
        message=f"User {user_doc['email']} logged in successfully",
        extra={"user_id": user_doc["id"], "is_admin": bool(user_doc.get("is_admin", False))}
    )

    return AuthResponse(access_token=token, user=_build_public_user(user_doc))


@router.get("/me", summary="Get current authenticated user's profile")
async def get_me(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    """
    Returns the full public profile of the currently authenticated user.
    Requires a valid Bearer token.
    Identity is derived securely by the backend from the token.
    Never returns password or password_hash.
    """
    db = UserDatabase()
    user_doc = db.find_by_id(current_user["id"])
    if not user_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    return _build_public_user(user_doc)
