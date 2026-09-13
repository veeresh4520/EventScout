"""
Source Registry and Dynamic Discovery API endpoints for EventScout.
Provides:
- User submission endpoint (accessible to all authenticated users)
- Admin verification, discovery, test scraping, approval, and management endpoints (Admin-only)
"""
import ipaddress
import logging
import socket
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse
from bson import ObjectId

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from pydantic import BaseModel, field_validator

from api.auth import get_current_user, get_current_admin_user
from eventscout.collectors.factory import get_collector_for_source
from eventscout.database.source_db import SourceDatabase, normalize_source_url
from eventscout.processors.normalizer import EventNormalizer
from eventscout.services.discovery_service import DiscoveryService

logger = logging.getLogger("SourcesRouter")
router = APIRouter(prefix="/api/sources", tags=["Sources"])


# ------------------------------------------------------------------
# Request & Response Schemas
# ------------------------------------------------------------------

class SubmitSourceRequest(BaseModel):
    url: str

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        url = v.strip()
        if not (url.startswith("http://") or url.startswith("https://")):
            raise ValueError("URL must begin with http:// or https://")

        parsed = urlparse(url)
        hostname = parsed.hostname
        if not hostname:
            raise ValueError("Invalid URL format.")

        # Prevent SSRF to local network or cloud metadata IP
        lowered = hostname.lower()
        if lowered in ("localhost", "127.0.0.1", "0.0.0.0"):
            raise ValueError("Submitting internal or local addresses is not permitted.")

        try:
            ip = ipaddress.ip_address(hostname)
            if ip.is_private or ip.is_loopback or ip.is_reserved or str(ip) == "169.254.169.254":
                raise ValueError("Submitting private or reserved network addresses is not permitted.")
        except ValueError:
            # It is a domain name, not a raw IP - safe to continue
            pass

        return url


class UpdateSourceRequest(BaseModel):
    name: Optional[str] = None
    source_type: Optional[str] = None
    collection_strategy: Optional[str] = None
    strategy: Optional[str] = None
    event_list_url: Optional[str] = None
    configuration: Optional[Dict[str, Any]] = None
    field_mapping: Optional[Dict[str, Any]] = None
    enabled: Optional[bool] = None
    status: Optional[str] = None


# ------------------------------------------------------------------
# Normal User Endpoints
# ------------------------------------------------------------------

def _run_background_discovery(source_id: str, url: str) -> None:
    """Background worker for automated discovery of submitted URLs."""
    try:
        service = DiscoveryService()
        service.discover_source(url=url, existing_source_id=source_id)
    except Exception as e:
        logger.error("Background discovery failed for source %s (%s): %s", source_id, url, e)


@router.post("/submit", status_code=status.HTTP_201_CREATED)
def submit_source(
    req: SubmitSourceRequest,
    background_tasks: BackgroundTasks,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Normal authenticated user submits a website URL for inclusion in EventScout.
    Enforces SSRF validation and duplicate detection.
    Stores source as PENDING and automatically dispatches the Gemini Discovery Agent.
    """
    db = SourceDatabase()
    url = req.url.strip()

    # Duplicate check
    existing = db.find_duplicate_source(url)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"This website is already registered in EventScout (Name: '{existing.get('name')}', Status: {existing.get('status')}).",
        )

    # Create in PENDING state
    parsed = urlparse(url)
    default_name = (parsed.netloc or url).replace("www.", "").split(".")[0].capitalize()

    new_source = db.create_source(
        url=url,
        name=default_name,
        status="PENDING",
        created_by=current_user.get("id", "user"),
    )
    source_id = new_source["id"]

    # Trigger Gemini Discovery in background
    background_tasks.add_task(_run_background_discovery, source_id, url)

    return {
        "message": "Source submitted successfully. Our system will analyze it and an administrator will review it.",
        "source_id": source_id,
        "name": default_name,
        "status": "PENDING",
    }


# ------------------------------------------------------------------
# Admin-Only Endpoints
# ------------------------------------------------------------------

@router.get("", response_model=List[Dict[str, Any]])
def list_sources(admin_user: Dict[str, Any] = Depends(get_current_admin_user)):
    """Admin: List all registered event sources."""
    db = SourceDatabase()
    return db.get_all_sources()


@router.get("/overview")
def get_sources_overview(admin_user: Dict[str, Any] = Depends(get_current_admin_user)):
    """Admin: Returns high-level metrics for the admin sources dashboard."""
    db = SourceDatabase()
    sources = db.get_all_sources()

    total = len(sources)
    enabled = sum(1 for s in sources if s.get("status") == "ENABLED")
    pending_review = sum(1 for s in sources if s.get("status") in ("READY_FOR_REVIEW", "PENDING"))
    discovering = sum(1 for s in sources if s.get("status") in ("DISCOVERING", "TESTING"))
    failed = sum(1 for s in sources if s.get("status") in ("FAILED", "NEEDS_REDISCOVERY"))
    disabled = sum(1 for s in sources if s.get("status") == "DISABLED")

    return {
        "total_sources": total,
        "enabled": enabled,
        "pending_review": pending_review,
        "discovering": discovering,
        "failed": failed,
        "disabled": disabled,
    }


@router.post("/discover")
def discover_source(
    req: SubmitSourceRequest,
    admin_user: Dict[str, Any] = Depends(get_current_admin_user),
):
    """
    Admin: Submits a URL and immediately executes inspection, Gemini analysis, and sample extraction.
    """
    url = req.url.strip()
    service = DiscoveryService()
    try:
        source_doc = service.discover_source(url)
        return source_doc
    except Exception as e:
        logger.error("Discovery error: %s", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Discovery failed: {str(e)}",
        )


@router.get("/{source_id}")
def get_source(
    source_id: str,
    admin_user: Dict[str, Any] = Depends(get_current_admin_user),
):
    """Admin: Fetch complete details of a single source including sample events and configuration."""
    db = SourceDatabase()
    source = db.get_source(source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found.")
    return source


@router.put("/{source_id}")
def update_source(
    source_id: str,
    req: UpdateSourceRequest,
    admin_user: Dict[str, Any] = Depends(get_current_admin_user),
):
    """Admin: Update configuration, selectors, strategy, or status for a source."""
    db = SourceDatabase()
    updates = req.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No fields provided to update.")

    # If enabled is explicitly passed, sync status
    if "enabled" in updates and "status" not in updates:
        updates["status"] = "ENABLED" if updates["enabled"] else "DISABLED"

    success = db.update_source(source_id, updates)
    if not success:
        raise HTTPException(status_code=404, detail="Source not found or update failed.")
    return db.get_source(source_id)


@router.post("/{source_id}/approve")
@router.post("/{source_id}/verify")
def approve_source(
    source_id: str,
    admin_user: Dict[str, Any] = Depends(get_current_admin_user),
):
    """Admin: Approve and enable a source for automatic scheduled scraping."""
    db = SourceDatabase()
    source = db.get_source(source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found.")

    db.update_source(source_id, {
        "status": "ENABLED",
        "enabled": True,
        "last_error": None,
        "consecutive_failures": 0,
    })
    from eventscout.utils.logging_config import structured_logger
    structured_logger.log_event(
        event_tag="ADMIN_SOURCE_APPROVED",
        message=f"Source '{source.get('name')}' approved and enabled",
        source=source.get("name"),
        extra={"source_id": source_id, "admin_email": admin_user.get("email")}
    )
    logger.info("[ADMIN] Source '%s' (%s) approved and ENABLED by %s.", source.get("name"), source_id, admin_user.get("email"))
    return db.get_source(source_id)


@router.post("/{source_id}/reject")
def reject_source(
    source_id: str,
    admin_user: Dict[str, Any] = Depends(get_current_admin_user),
):
    """Admin: Reject a source and mark it as DISABLED."""
    db = SourceDatabase()
    source = db.get_source(source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found.")

    db.update_source(source_id, {
        "status": "DISABLED",
        "enabled": False,
    })
    from eventscout.utils.logging_config import structured_logger
    structured_logger.log_event(
        event_tag="ADMIN_SOURCE_REJECTED",
        message=f"Source '{source.get('name')}' rejected and disabled",
        source=source.get("name"),
        extra={"source_id": source_id, "admin_email": admin_user.get("email")}
    )
    logger.info("[ADMIN] Source '%s' (%s) rejected by %s.", source.get("name"), source_id, admin_user.get("email"))
    return db.get_source(source_id)


@router.post("/{source_id}/retry-discovery")
def retry_discovery(
    source_id: str,
    admin_user: Dict[str, Any] = Depends(get_current_admin_user),
):
    """Admin: Re-runs discovery for a failed, pending, or degraded source."""
    db = SourceDatabase()
    source = db.get_source(source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found.")

    url = source.get("event_list_url") or source.get("base_url") or source.get("url")
    service = DiscoveryService()
    try:
        updated = service.discover_source(url=url, existing_source_id=source_id)
        return updated
    except Exception as e:
        logger.error("Retry discovery failed for %s: %s", source_id, e)
        raise HTTPException(status_code=500, detail=f"Retry discovery failed: {str(e)}")


@router.post("/{source_id}/toggle")
def toggle_source(
    source_id: str,
    admin_user: Dict[str, Any] = Depends(get_current_admin_user),
):
    """Admin: Toggle source between ENABLED and DISABLED."""
    db = SourceDatabase()
    source = db.get_source(source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found.")

    new_enabled = not source.get("enabled", False)
    new_status = "ENABLED" if new_enabled else "DISABLED"

    db.update_source(source_id, {"status": new_status, "enabled": new_enabled})
    return db.get_source(source_id)


@router.post("/{source_id}/test")
def test_scrape_source(
    source_id: str,
    admin_user: Dict[str, Any] = Depends(get_current_admin_user),
):
    """
    Admin: Executes a 1-page test scrape using the source configuration and returns
    extracted events without saving them to MongoDB.
    """
    db = SourceDatabase()
    source = db.get_source(source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found.")

    try:
        collector = get_collector_for_source(source)
        raw_events = collector.test()
        normalizer = EventNormalizer()
        valid_events = normalizer.normalize_batch(raw_events, source)

        return {
            "source_id": source_id,
            "source_name": source.get("name"),
            "strategy": source.get("collection_strategy") or source.get("strategy"),
            "raw_count": len(raw_events),
            "normalized_count": len(valid_events),
            "events": [e.to_dict() for e in valid_events[:10]],
        }
    except Exception as e:
        logger.error("Test scrape failed for source %s: %s", source_id, e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Test scrape failed: {str(e)}")


@router.delete("/{source_id}")
def delete_source(
    source_id: str,
    admin_user: Dict[str, Any] = Depends(get_current_admin_user),
):
    """Admin: Delete a source from the registry."""
    db = SourceDatabase()
    success = db.delete_source(source_id)
    if not success:
        raise HTTPException(status_code=404, detail="Source not found.")
    return {"deleted": True, "source_id": source_id}
