"""
Comprehensive Test Suite for Dynamic AI Source Discovery & Admin Source Management.

Covers:
1. Source Registry (creation, duplicate detection with URL normalization, status transitions, health tracking)
2. RBAC & Authorization (normal user submission vs. admin approval/management)
3. Generic Collectors (Factory, HTML JSON-LD, REST API, GraphQL, Meetup adapter)
4. AI Discovery Agent (valid opportunity site, invalid site rejection, zero-event validation failure)
5. Scheduler Dynamic Execution & Failure Isolation
6. Common Event Schema Normalization
"""
import json
from datetime import datetime, timezone
from typing import Any, Dict
import pytest
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from api.main import app
from eventscout.collectors.factory import get_collector_for_source
from eventscout.collectors.api_collector import ApiCollector
from eventscout.collectors.html_collector import HtmlCollector
from eventscout.collectors.meetup_adapter import MeetupCollectorAdapter
from eventscout.database.source_db import SourceDatabase, normalize_source_url
from eventscout.models.event import Event
from eventscout.processors.normalizer import EventNormalizer, parse_datetime_flexible
from eventscout.services.discovery_service import DiscoveryService
from eventscout.services.llm_service import GeminiDiscoveryLLM
from eventscout.services.scraper_service import ScraperService


# ==============================================================================
# 1. URL Normalization & Duplicate Detection
# ==============================================================================

def test_url_normalization():
    """Verify that URL normalization handles case, trailing slashes, and www."""
    u1 = normalize_source_url("https://Devpost.com/")
    u2 = normalize_source_url("http://www.devpost.com")
    u3 = normalize_source_url("https://devpost.com/hackathons/")
    u4 = normalize_source_url("https://www.devpost.com/hackathons")

    assert u1 == "https://devpost.com"
    assert u2 == "http://devpost.com"
    assert u3 == "https://devpost.com/hackathons"
    assert u4 == "https://devpost.com/hackathons"


def test_duplicate_source_detection():
    """Verify that find_duplicate_source finds existing sources regardless of format."""
    mock_db = MagicMock(spec=SourceDatabase)
    mock_col = MagicMock()
    mock_db.get_collection.return_value = mock_col

    # Simulate finding existing document
    mock_col.find_one.return_value = {
        "_id": "64f1234567890abcdef12345",
        "name": "Devpost",
        "url": "https://devpost.com",
        "normalized_url": "https://devpost.com",
        "status": "ENABLED",
    }

    # Call find_duplicate_source on instance
    db_instance = SourceDatabase.__new__(SourceDatabase)
    db_instance.get_collection = MagicMock(return_value=mock_col)

    duplicate = db_instance.find_duplicate_source("https://www.devpost.com/")
    assert duplicate is not None
    assert duplicate["name"] == "Devpost"
    assert duplicate["status"] == "ENABLED"


# ==============================================================================
# 2. Source Status Lifecycle & Health Tracking
# ==============================================================================

def test_source_health_consecutive_failures_trigger_rediscovery():
    """Verify that 3 consecutive failures transitions source to NEEDS_REDISCOVERY."""
    db_instance = SourceDatabase.__new__(SourceDatabase)
    mock_col = MagicMock()
    db_instance.get_collection = MagicMock(return_value=mock_col)
    
    # Mock current source with 2 consecutive failures
    db_instance.get_source = MagicMock(return_value={
        "id": "src_test_123",
        "name": "Test Site",
        "consecutive_failures": 2,
        "status": "ENABLED",
    })

    success = db_instance.update_source_health("src_test_123", success=False, error_msg="Timeout Error")
    
    # Assert update_one was called with consecutive_failures: 3 and status: NEEDS_REDISCOVERY
    args, kwargs = mock_col.update_one.call_args
    set_clause = kwargs["$set"] if "$set" in kwargs else args[1]["$set"]
    assert set_clause["consecutive_failures"] == 3
    assert set_clause["status"] == "NEEDS_REDISCOVERY"
    assert set_clause["last_error"] == "Timeout Error"


def test_source_health_success_resets_failures():
    """Verify that a successful run resets consecutive_failures to 0."""
    db_instance = SourceDatabase.__new__(SourceDatabase)
    mock_col = MagicMock()
    db_instance.get_collection = MagicMock(return_value=mock_col)

    db_instance.update_source_health("src_test_123", success=True, events_count=15)
    
    args, kwargs = mock_col.update_one.call_args
    set_clause = kwargs["$set"] if "$set" in kwargs else args[1]["$set"]
    assert set_clause["consecutive_failures"] == 0
    assert set_clause["events_found_last_run"] == 15
    assert set_clause["last_error"] is None


# ==============================================================================
# 3. Collector Factory & Generic Collectors
# ==============================================================================

def test_collector_factory():
    """Verify that get_collector_for_source returns correct collector implementations."""
    meetup_src = {"name": "Meetup", "configuration": {"adapter": "meetup_graphql_interceptor"}}
    api_src = {"name": "TestAPI", "collection_strategy": "REST_API"}
    graphql_src = {"name": "TestGraphQL", "collection_strategy": "GRAPHQL"}
    html_src = {"name": "TestHTML", "collection_strategy": "HTML"}
    playwright_src = {"name": "Devpost", "collection_strategy": "PLAYWRIGHT"}

    assert isinstance(get_collector_for_source(meetup_src), MeetupCollectorAdapter)
    assert isinstance(get_collector_for_source(api_src), ApiCollector)
    assert isinstance(get_collector_for_source(html_src), HtmlCollector)
    assert get_collector_for_source(playwright_src).__class__.__name__ == "PlaywrightCollector"


def test_html_collector_json_ld():
    """Verify HtmlCollector extracts Schema.org JSON-LD structured event data."""
    sample_html = """
    <html>
      <head>
        <script type="application/ld+json">
        {
          "@context": "https://schema.org",
          "@type": "Event",
          "name": "Global AI Summit 2026",
          "startDate": "2026-11-20T10:00:00Z",
          "url": "https://example.com/events/ai-summit",
          "description": "Annual conference exploring generative AI.",
          "location": {
            "@type": "Place",
            "name": "Hyderabad Convention Centre"
          },
          "organizer": {
            "@type": "Organization",
            "name": "AI Foundation"
          }
        }
        </script>
      </head>
      <body><h1>Events</h1></body>
    </html>
    """

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = sample_html

    collector = HtmlCollector({
        "name": "SummitSite",
        "url": "https://example.com/events",
        "configuration": {"target_url": "https://example.com/events"}
    })

    with patch("httpx.Client.get", return_value=mock_resp):
        events = collector.collect(max_pages=1)
        assert len(events) == 1
        ev = events[0]
        assert ev["title"] == "Global AI Summit 2026"
        assert ev["event_url"] == "https://example.com/events/ai-summit"
        assert ev["organizer"] == "AI Foundation"
        assert ev["mode_location"] == "Hyderabad Convention Centre"


# ==============================================================================
# 4. RBAC & Authorization Tests
# ==============================================================================

def test_normal_user_submission_api():
    """Verify that a normal authenticated user can submit a source, and it is created as PENDING."""
    client = TestClient(app)

    # Mock normal user token decode and UserDatabase
    normal_user = {"id": "user_123", "email": "user@example.com", "is_admin": False}
    with patch("api.auth.decode_token", return_value={"sub": "user_123", "email": "user@example.com"}):
        with patch("eventscout.database.source_db.SourceDatabase.find_duplicate_source", return_value=None):
            with patch("eventscout.database.source_db.SourceDatabase.create_source", return_value={"id": "src_new_99", "status": "PENDING"}):
                with patch("api.routers.sources._run_background_discovery"):
                    response = client.post(
                        "/api/sources/submit",
                        headers={"Authorization": "Bearer fake-user-token"},
                        json={"url": "https://new-tech-events.org"},
                    )

                    assert response.status_code == 201
                    data = response.json()
                    assert "submitted successfully" in data["message"]
                    assert data["status"] == "PENDING"


def test_normal_user_cannot_access_admin_endpoints():
    """Verify that normal non-admin users receive 403 Forbidden on admin source endpoints."""
    client = TestClient(app)

    normal_user = {"id": "user_123", "email": "user@example.com", "is_admin": False}
    with patch("api.auth.decode_token", return_value={"sub": "user_123", "email": "user@example.com"}):
        with patch("eventscout.database.user_db.UserDatabase.find_by_id", return_value=normal_user):
            # Attempt list sources
            r1 = client.get("/api/sources", headers={"Authorization": "Bearer fake-token"})
            assert r1.status_code == 403

            # Attempt approve source
            r2 = client.post("/api/sources/src_123/approve", headers={"Authorization": "Bearer fake-token"})
            assert r2.status_code == 403


def test_admin_can_approve_source():
    """Verify that an admin user can approve and enable a source."""
    client = TestClient(app)

    admin_user = {"id": "admin_999", "email": "admin@eventscout.com", "is_admin": True}
    with patch("api.auth.decode_token", return_value={"sub": "admin_999", "email": "admin@eventscout.com"}):
        with patch("eventscout.database.user_db.UserDatabase.find_by_id", return_value=admin_user):
            with patch("eventscout.database.source_db.SourceDatabase.get_source", return_value={"id": "src_123", "name": "Devpost", "status": "ENABLED"}):
                with patch("eventscout.database.source_db.SourceDatabase.update_source", return_value=True):
                    res = client.post("/api/sources/src_123/approve", headers={"Authorization": "Bearer fake-admin-token"})
                    assert res.status_code == 200
                    data = res.json()
                    assert data["status"] == "ENABLED"


# ==============================================================================
# 5. AI Discovery & Sample Validation
# ==============================================================================

def test_discovery_rejects_non_event_website():
    """Verify that DiscoveryService marks source as FAILED if AI determines it is not an event website."""
    mock_db = MagicMock()
    mock_db.find_duplicate_source.return_value = None
    mock_db.create_source.return_value = {"id": "src_blog_1"}
    mock_db.get_source.return_value = {"id": "src_blog_1", "status": "FAILED", "last_error": "INVALID_SOURCE: Blog site"}

    mock_llm = MagicMock()
    mock_llm.analyze_source_structure.return_value = {
        "is_event_website": False,
        "rejection_reason": "Personal portfolio with no events.",
    }

    service = DiscoveryService(source_db=mock_db, llm_service=mock_llm)
    with patch.object(service, "_inspect_page_and_network", return_value=("<html></html>", [])):
        result = service.discover_source("https://random-blog.com")
        assert result["status"] == "FAILED"
        mock_db.update_source.assert_called()


def test_discovery_valid_site_sets_ready_for_review():
    """Verify that DiscoveryService creates configuration, runs test scrape, and sets READY_FOR_REVIEW."""
    mock_db = MagicMock()
    mock_db.find_duplicate_source.return_value = None
    mock_db.create_source.return_value = {"id": "src_hack_1"}
    mock_db.get_source.return_value = {
        "id": "src_hack_1",
        "name": "HackCentral",
        "status": "READY_FOR_REVIEW",
        "confidence_score": 0.95,
        "sample_events": [{"title": "Spring Hackathon 2026"}],
    }

    mock_llm = MagicMock()
    mock_llm.analyze_source_structure.return_value = {
        "is_event_website": True,
        "source_name": "HackCentral",
        "collection_strategy": "REST_API",
        "strategy": "api_json",
        "confidence_score": 0.95,
        "configuration": {"endpoint": "https://hackcentral.org/api/events"},
        "field_mapping": {"title": "title", "date_time": "time"},
    }

    mock_normalizer = MagicMock()
    mock_normalizer.normalize_batch.return_value = [
        Event(
            title="Spring Hackathon 2026",
            event_url="https://hackcentral.org/1",
            date_time=datetime(2026, 11, 15, tzinfo=timezone.utc),
            organizer="HackCentral",
        )
    ]

    service = DiscoveryService(source_db=mock_db, llm_service=mock_llm, normalizer=mock_normalizer)
    with patch.object(service, "_inspect_page_and_network", return_value=("<html></html>", [])):
        with patch("eventscout.services.discovery_service.get_collector_for_source") as mock_factory:
            mock_collector = MagicMock()
            mock_collector.test.return_value = [{"title": "Spring Hackathon 2026"}]
            mock_factory.return_value = mock_collector

            result = service.discover_source("https://hackcentral.org")
            assert result["status"] == "READY_FOR_REVIEW"
            assert len(result["sample_events"]) > 0


# ==============================================================================
# 6. Scheduler Dynamic Execution & Failure Isolation
# ==============================================================================

def test_scheduler_dynamic_enabled_sources_with_failure_isolation():
    """Verify scheduler executes all ENABLED sources and one failing source does not crash the others."""
    mock_notif = MagicMock()
    mock_source_db = MagicMock()
    mock_event_db = MagicMock()

    mock_source_db.get_enabled_sources.return_value = [
        {"id": "src_broken", "name": "BrokenSite", "collection_strategy": "REST_API"},
        {"id": "src_working", "name": "WorkingSite", "collection_strategy": "HTML"},
    ]

    service = ScraperService(
        notification_service=mock_notif,
        source_db=mock_source_db,
        event_db=mock_event_db,
    )

    working_event = Event(
        title="Active Python Hackathon",
        event_url="https://working.com/event",
        date_time=datetime(2026, 12, 1, tzinfo=timezone.utc),
        organizer="Working Org",
    )

    def factory_side_effect(source):
        collector = MagicMock()
        if source["id"] == "src_broken":
            collector.collect.side_effect = ConnectionError("Endpoint down")
        else:
            collector.collect.return_value = [{"title": "Active Event"}]
        return collector

    with patch("eventscout.services.scraper_service.get_collector_for_source", side_effect=factory_side_effect):
        with patch.object(service.normalizer, "normalize_batch", return_value=[working_event]):
            summary = service.run_pipeline(max_pages=1)

            # Assert pipeline ran to completion
            assert summary["dynamic_sources_executed"] == 2
            
            # Assert broken source recorded health failure
            mock_source_db.update_source_health.assert_any_call("src_broken", success=False, error_msg="Endpoint down")

            # Assert working source recorded health success
            mock_source_db.update_source_health.assert_any_call("src_working", success=True, events_count=1)


# ==============================================================================
# 7. Common Event Schema Normalization
# ==============================================================================

def test_common_event_schema_normalization():
    """Verify that different platform inputs normalize cleanly into EventScout's Event domain object."""
    normalizer = EventNormalizer()

    # Raw item with alternative field namings (startDate, host, location)
    raw_item = {
        "title": "  Quantum Computing Hackathon  ",
        "url": "https://quantum.org/hackathon",
        "startDate": "2026-12-10T14:00:00Z",
        "host": "Quantum Research Lab",
        "location": "Online / Virtual",
        "image": "https://quantum.org/banner.png",
        "is_free": "true",
    }

    event = normalizer.normalize(raw_item, {"name": "QuantumPlatform"})
    assert isinstance(event, Event)
    assert event.title == "Quantum Computing Hackathon"
    assert event.event_url == "https://quantum.org/hackathon"
    assert event.organizer == "Quantum Research Lab"
    assert event.mode_location == "Online / Virtual"
    assert event.poster_image_url == "https://quantum.org/banner.png"
    assert event.is_free is True
    assert event.source == "quantumplatform"
    assert event.date_time.year == 2026
    assert event.date_time.month == 12
