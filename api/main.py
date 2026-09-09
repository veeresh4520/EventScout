import logging
from typing import Any, Dict, List

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from eventscout.database.mongodb import EventDatabase

logger = logging.getLogger("EventScoutAPI")

app = FastAPI(
    title="EventScout API",
    description="API to serve technical events from MongoDB for the EventScout platform.",
    version="1.0.0",
)

# Configure CORS specifically for local development frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["GET", "OPTIONS"],
    allow_headers=["*"],
)


@app.get("/health", summary="Health Check")
async def health_check():
    """
    Returns a simple health check response to verify the API is running.
    """
    return {"status": "ok", "message": "EventScout API is running"}


@app.get("/events", response_model=List[Dict[str, Any]], summary="Get all upcoming technical events from MongoDB")
async def get_events():
    """
    Retrieves active/future events from MongoDB Atlas using the data layer.
    MongoDB documents are normalized into JSON-serializable primitives.
    Expired events are automatically filtered out.
    """
    try:
        db = EventDatabase()
        events = db.get_upcoming_events()
        return events
    except Exception as e:
        logger.error("Failed to retrieve events from MongoDB: %s", e, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Unable to load events from database: {str(e)}"
        )
