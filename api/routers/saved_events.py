"""
Saved Events router for EventScout API.

Endpoints:
    POST   /events/{event_id}/save  — Save an event for the current user
    DELETE /events/{event_id}/save  — Unsave an event for the current user
    GET    /events/saved            — Get full event documents saved by the current user
"""

import logging
from typing import Any, Dict, List

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, Depends, HTTPException, status

from api.auth import get_current_user
from eventscout.database.mongodb import EventDatabase
from eventscout.database.user_db import UserDatabase

logger = logging.getLogger("EventScoutSavedEventsRouter")

router = APIRouter(tags=["Saved Events"])


def _validate_event_id(event_id: str) -> ObjectId:
    """
    Validates that event_id is a valid MongoDB ObjectId string.
    Raises 422 if invalid.
    """
    try:
        return ObjectId(event_id)
    except (InvalidId, Exception):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid event ID format: '{event_id}'. Expected a 24-character hex string.",
        )


@router.get("/events/saved", summary="Get all events saved by the current user")
async def get_saved_events(
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> List[Dict[str, Any]]:
    """
    Returns the full event documents for all events saved by the authenticated user.
    The user's saved_event_ids are fetched from the users collection,
    then the matching event documents are fetched from the events collection.

    This endpoint returns [] if the user has no saved events.
    Does NOT return IDs only — returns complete event documents.
    """
    user_db = UserDatabase()
    event_db = EventDatabase()

    saved_ids = user_db.get_saved_event_ids(current_user["id"])
    if not saved_ids:
        return []

    # Convert string IDs back to ObjectId for MongoDB lookup
    valid_obj_ids = []
    for eid in saved_ids:
        try:
            valid_obj_ids.append(ObjectId(eid))
        except Exception:
            # Skip any malformed IDs silently
            continue

    if not valid_obj_ids:
        return []

    # Fetch all matching events in a single query
    col = event_db.get_collection()
    raw_docs = list(col.find({"_id": {"$in": valid_obj_ids}}))

    # Serialize MongoDB-specific types to JSON-safe primitives
    result = []
    for doc in raw_docs:
        if "_id" in doc:
            doc["id"] = str(doc["_id"])
            doc["_id"] = str(doc["_id"])

        from datetime import datetime
        if isinstance(doc.get("date_time"), datetime):
            doc["date_time"] = doc["date_time"].isoformat()

        # Ensure UI convenience aliases (same as EventDatabase.get_upcoming_events)
        if "organizer" in doc and "organization" not in doc:
            doc["organization"] = doc["organizer"]
        if "registration_url" in doc and "registrationUrl" not in doc:
            doc["registrationUrl"] = doc["registration_url"]
        if "mode_location" in doc and "location" not in doc:
            doc["location"] = doc["mode_location"]

        result.append(doc)

    return result


@router.post(
    "/events/{event_id}/save",
    status_code=status.HTTP_200_OK,
    summary="Save an event for the current user",
)
async def save_event(
    event_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Saves the specified event for the authenticated user.

    - If already saved: returns success without creating a duplicate
      ($addToSet in MongoDB ensures idempotency at the DB level).
    - If the event does not exist in the events collection: returns 404.
    - The save relationship is user-specific: User A's saves do NOT affect User B.

    The event_id is the MongoDB _id of the event document (string form).
    """
    obj_id = _validate_event_id(event_id)

    # Verify the event actually exists before saving
    event_db = EventDatabase()
    col = event_db.get_collection()
    event_doc = col.find_one({"_id": obj_id}, {"_id": 1})
    if not event_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Event '{event_id}' not found.",
        )

    user_db = UserDatabase()
    success = user_db.save_event(current_user["id"], event_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    return {"saved": True, "event_id": event_id}


@router.delete(
    "/events/{event_id}/save",
    status_code=status.HTTP_200_OK,
    summary="Remove a saved event for the current user",
)
async def unsave_event(
    event_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Removes the specified event from the authenticated user's saved list.

    - If the event was not saved: handled gracefully, returns success
      ($pull in MongoDB is idempotent — removes the element if present).
    - The unsave is user-specific: only affects the current user's saved list.
    """
    _validate_event_id(event_id)  # Validate format even if we don't need the ObjectId here

    user_db = UserDatabase()
    success = user_db.unsave_event(current_user["id"], event_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    return {"saved": False, "event_id": event_id}
