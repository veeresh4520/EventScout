"""
Users / Preferences router for EventScout API.

Endpoints:
    GET /me/preferences  — Retrieve current user's preferences
    PUT /me/preferences  — Update current user's preferences
"""

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from api.auth import get_current_user
from eventscout.database.user_db import UserDatabase

logger = logging.getLogger("EventScoutUsersRouter")

router = APIRouter(prefix="/me", tags=["User Preferences"])

# ------------------------------------------------------------------
# Valid preference values (used for input validation)
# ------------------------------------------------------------------

VALID_INTERESTS = {
    "AI / ML",
    "Web Development",
    "Cloud",
    "Cybersecurity",
    "Data Science",
    "DevOps",
    "Open Source",
    "Mobile Development",
    "Blockchain",
    "IoT",
    "Robotics",
    "Game Development",
}

VALID_EVENT_TYPES = {"Hackathon", "Workshop", "Meetup", "Conference", "Webinar", "Talk"}

VALID_MODES = {"Online", "Offline", "Hybrid"}


# ------------------------------------------------------------------
# Request / Response schemas
# ------------------------------------------------------------------


class NotificationPreferencesModel(BaseModel):
    dashboard_enabled: Optional[bool] = None
    browser_enabled: Optional[bool] = None
    email_enabled: Optional[bool] = None


class PreferencesUpdate(BaseModel):
    interests: Optional[List[str]] = None
    skills: Optional[List[str]] = None
    preferred_event_types: Optional[List[str]] = None
    preferred_modes: Optional[List[str]] = None
    notification_preferences: Optional[NotificationPreferencesModel] = None


# ------------------------------------------------------------------
# Endpoints
# ------------------------------------------------------------------


@router.get("/preferences", summary="Get current user's preferences")
async def get_preferences(
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Returns the preferences for the authenticated user.
    User identity is derived from the Bearer token — never from request body.
    """
    db = UserDatabase()
    user_doc = db.find_by_id(current_user["id"])
    if not user_doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    return {
        "interests": user_doc.get("interests", []),
        "skills": user_doc.get("skills", []),
        "preferred_event_types": user_doc.get("preferred_event_types", []),
        "preferred_modes": user_doc.get("preferred_modes", []),
        "notification_preferences": user_doc.get("notification_preferences", {
            "dashboard_enabled": True,
            "browser_enabled": True,
            "email_enabled": True,
        }),
    }


@router.put("/preferences", summary="Update current user's preferences")
async def update_preferences(
    body: PreferencesUpdate,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Updates preferences for the authenticated user.
    Only fields present in the request body are updated.
    Validates interest, event type, and mode values against known valid options.
    A user cannot modify another user's preferences — identity comes from the token.
    """
    # Validate interests
    if body.interests is not None:
        invalid = [i for i in body.interests if i not in VALID_INTERESTS]
        if invalid:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid interests: {invalid}. Valid options: {sorted(VALID_INTERESTS)}",
            )

    # Validate event types
    if body.preferred_event_types is not None:
        invalid = [t for t in body.preferred_event_types if t not in VALID_EVENT_TYPES]
        if invalid:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid event types: {invalid}. Valid options: {sorted(VALID_EVENT_TYPES)}",
            )

    # Validate modes
    if body.preferred_modes is not None:
        invalid = [m for m in body.preferred_modes if m not in VALID_MODES]
        if invalid:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid modes: {invalid}. Valid options: {sorted(VALID_MODES)}",
            )

    # Build update dict from non-None fields
    prefs = body.model_dump(exclude_none=True)

    db = UserDatabase()
    success = db.update_preferences(current_user["id"], prefs)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    # Return the updated preferences
    user_doc = db.find_by_id(current_user["id"])
    return {
        "interests": user_doc.get("interests", []),
        "skills": user_doc.get("skills", []),
        "preferred_event_types": user_doc.get("preferred_event_types", []),
        "preferred_modes": user_doc.get("preferred_modes", []),
        "notification_preferences": user_doc.get("notification_preferences", {
            "dashboard_enabled": True,
            "browser_enabled": True,
            "email_enabled": True,
        }),
    }
