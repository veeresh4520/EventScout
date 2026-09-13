"""
Notifications router for EventScout API.

Endpoints:
    GET  /notifications               — Get user's notifications & unread count
    GET  /notifications/unread-count  — Get total unread count
    POST /notifications/{id}/read     — Mark a specific notification as read
    POST /notifications/read-all      — Mark all notifications as read
"""

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from api.auth import get_current_user
from eventscout.database.notification_db import NotificationDatabase

logger = logging.getLogger("EventScoutNotificationsRouter")

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("", summary="Get current user's notifications")
async def get_notifications(
    limit: int = Query(30, ge=1, le=100),
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Returns recent notifications for the authenticated user, sorted newest first.
    Includes the total unread count for UI badges.
    Enforces user isolation via Bearer JWT.
    """
    db = NotificationDatabase()
    user_id = current_user["id"]

    notifications = db.get_user_notifications(user_id=user_id, limit=limit)
    unread_count = db.get_unread_count(user_id=user_id)

    return {
        "notifications": notifications,
        "unread_count": unread_count,
    }


@router.get("/unread-count", summary="Get unread notification count")
async def get_unread_count(
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, int]:
    """
    Lightweight endpoint returning only the unread count for periodic UI polling.
    """
    db = NotificationDatabase()
    count = db.get_unread_count(current_user["id"])
    return {"unread_count": count}


@router.post("/{notification_id}/read", summary="Mark a notification as read")
async def mark_notification_read(
    notification_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Marks a single notification as read.
    Guarantees user isolation: User A cannot mark User B's notifications as read.
    """
    db = NotificationDatabase()
    success = db.mark_as_read(user_id=current_user["id"], notification_id=notification_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found.",
        )

    return {"id": notification_id, "read": True}


@router.post("/read-all", summary="Mark all notifications as read")
async def mark_all_notifications_read(
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Marks all notifications for the authenticated user as read.
    """
    db = NotificationDatabase()
    marked = db.mark_all_read(user_id=current_user["id"])
    return {"success": True, "marked_read": marked}
