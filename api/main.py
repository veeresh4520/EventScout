import logging
from typing import Any, Dict, List, Optional
from pydantic import BaseModel
from fastapi import FastAPI, HTTPException, Query, Depends, status
from fastapi.middleware.cors import CORSMiddleware

from eventscout.database.mongodb import EventDatabase
from eventscout.database.user_db import UserDatabase
from eventscout.models.event import Event
from api.auth import get_optional_current_user, get_current_user
from api.routers import auth as auth_router
from api.routers import users as users_router
from api.routers import saved_events as saved_events_router
from api.routers import notifications as notifications_router
from api.routers import sources as sources_router

logger = logging.getLogger("EventScoutAPI")

app = FastAPI(
    title="EventScout API",
    description="API to serve technical events from MongoDB for the EventScout platform.",
    version="2.0.0",
)

# Configure CORS for local development frontend and extension
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Mount routers
app.include_router(auth_router.router)
app.include_router(users_router.router)
app.include_router(saved_events_router.router)
app.include_router(notifications_router.router)
app.include_router(sources_router.router)


@app.get("/health", summary="Health Check")
async def health_check():
    """
    Returns a simple health check response to verify the API is running.
    """
    return {"status": "ok", "message": "EventScout API is running"}


class ExtensionSaveRequest(BaseModel):
    title: str
    event_url: str
    date_time: Optional[str] = None
    organizer: Optional[str] = "Web Discovery"
    description: Optional[str] = None
    mode_location: Optional[str] = "Online"
    is_free: Optional[bool] = True
    categories: Optional[List[str]] = None


@app.get("/events", response_model=List[Dict[str, Any]], summary="Get upcoming technical events with search, filtering, and intelligent ranking")
async def get_events(
    q: Optional[str] = Query(None, description="Search term matching title, description, organizer, or skills"),
    category: Optional[str] = Query(None, description="Category filter"),
    event_type: Optional[str] = Query(None, description="Event type filter (e.g. hackathon, workshop, conference)"),
    mode: Optional[str] = Query(None, description="Mode filter (online, in-person, hybrid)"),
    city: Optional[str] = Query(None, description="City location filter"),
    is_free: Optional[bool] = Query(None, description="Free events only (true/false)"),
    source: Optional[str] = Query(None, description="Source platform name"),
    skills: Optional[str] = Query(None, description="Comma-separated list of skills"),
    sort_by: str = Query("recommended", description="Sorting method: recommended, soonest, deadline, newest"),
    limit: Optional[int] = Query(None, ge=1, le=500, description="Max results to return"),
    skip: int = Query(0, ge=0, description="Number of results to skip"),
    current_user: Optional[Dict[str, Any]] = Depends(get_optional_current_user),
):
    """
    Retrieves active/future events from MongoDB Atlas with multi-criteria filtering,
    intelligent host & quality ranking, personalized recommendations for authenticated users,
    and sorting. Maintains 100% backward compatibility.
    """
    try:
        db = EventDatabase()
        skill_list = [s.strip() for s in skills.split(",")] if skills else None
        events = db.query_events(
            q=q,
            category=category,
            event_type=event_type,
            mode=mode,
            city=city,
            is_free=is_free,
            source=source,
            skills=skill_list,
            sort_by=sort_by,
            user=current_user,
            limit=limit,
            skip=skip,
        )
        return events
    except Exception as e:
        logger.error("Failed to retrieve events from MongoDB: %s", e, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Unable to load events from database: {str(e)}"
        )


@app.post("/events/extension-save", summary="Save an event detected by the browser extension")
async def save_event_from_extension(
    request: ExtensionSaveRequest,
    current_user: Optional[Dict[str, Any]] = Depends(get_optional_current_user),
):
    """
    Receives event metadata extracted by the EventScout Chrome extension,
    upserts it into MongoDB, and bookmarks it for the current user if logged in.
    """
    from datetime import datetime, timezone

    db = EventDatabase()
    now_iso = datetime.now(timezone.utc).isoformat()
    dt_val = None
    if request.date_time:
        try:
            s = request.date_time.strip()
            if s.endswith("Z"):
                s = s[:-1] + "+00:00"
            dt_val = datetime.fromisoformat(s)
        except Exception:
            pass
    if not dt_val:
        dt_val = datetime.now(timezone.utc)

    event_obj = Event(
        title=request.title,
        event_url=request.event_url,
        date_time=dt_val,
        organizer=request.organizer or "Web Discovery",
        source="extension",
        mode_location=request.mode_location or "Online",
        description=request.description,
        is_free=request.is_free if request.is_free is not None else True,
        categories=request.categories or ["General Tech"],
        scraped_at=now_iso,
    )

    metrics = db.upsert_events([event_obj])
    
    # If user is authenticated, also save it to their saved_event_ids
    saved_for_user = False
    if current_user and "id" in current_user:
        user_db = UserDatabase()
        # Find the event id
        ev_doc = db.get_collection().find_one({"source": "extension", "source_event_id": request.event_url})
        if ev_doc:
            user_db.save_event(current_user["id"], str(ev_doc["_id"]))
            saved_for_user = True

    return {
        "status": "success",
        "message": "Event successfully saved to EventScout",
        "saved_for_user": saved_for_user,
        "metrics": metrics,
    }

