"""
tests/test_scraper_resilience.py
================================
Tests for scraper error resilience, failure isolation, and log sanitization.
"""

import pytest
from unittest.mock import MagicMock, patch

from eventscout.services.scraper_service import ScraperService
from eventscout.utils.logging_config import sanitize_dict, sanitize_value


def test_sensitive_data_sanitization():
    """Verify that passwords, tokens, and API keys are strictly redacted in logs."""
    raw_payload = {
        "email": "user@example.com",
        "password": "SuperSecretPassword123!",
        "jwt_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.dummy",
        "api_key": "AIzaSyDummyGeminiKey",
        "nested": {
            "bearer_token": "secret_bearer_token",
            "safe_field": "public_data",
        }
    }

    sanitized = sanitize_dict(raw_payload)

    assert sanitized["email"] == "user@example.com"
    assert sanitized["password"] == "***REDACTED***"
    assert sanitized["jwt_token"] == "***REDACTED***"
    assert sanitized["api_key"] == "***REDACTED***"
    assert sanitized["nested"]["bearer_token"] == "***REDACTED***"
    assert sanitized["nested"]["safe_field"] == "public_data"


def test_scraper_failure_isolation():
    """Verify that if one source raises an exception, the entire scraper does NOT crash."""
    mock_source_db = MagicMock()
    mock_source_db.get_enabled_sources.return_value = [
        {"id": "source_broken", "name": "Broken Site", "strategy": "REST_API"},
        {"id": "source_working", "name": "Working Site", "strategy": "REST_API"},
    ]

    mock_event_db = MagicMock()
    mock_notif_service = MagicMock()

    service = ScraperService(
        notification_service=mock_notif_service,
        source_db=mock_source_db,
        event_db=mock_event_db,
    )

    # Patch factory to simulate first source throwing an error and second succeeding
    with patch("eventscout.services.scraper_service.get_collector_for_source") as mock_factory:
        failing_collector = MagicMock()
        failing_collector.collect.side_effect = TimeoutError("Connection to source timed out")

        working_collector = MagicMock()
        working_collector.collect.return_value = [
            {"title": "Valid Event", "date_time": "2026-10-15T10:00:00Z", "url": "https://example.com/ev1"}
        ]

        mock_factory.side_effect = [failing_collector, working_collector]

        # Running pipeline should complete cleanly without unhandled exception
        summary = service.run_pipeline(max_pages=1)

        assert summary["dynamic_sources_executed"] == 2
        # Verify that source_db recorded failure for the broken source
        mock_source_db.update_source_health.assert_any_call(
            "source_broken", success=False, error_msg="Connection to source timed out"
        )
