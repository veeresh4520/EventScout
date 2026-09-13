"""
tests/test_ranking_service.py
=============================
Unit tests for the EventScout Ranking Engine and Organization Registry.
"""

from datetime import datetime, timezone
import pytest

from eventscout.services.organization_registry import (
    HostType,
    organization_registry,
)
from eventscout.services.ranking_service import (
    RankingService,
    ranking_service,
)


def test_organization_classification_and_aliases():
    """Verify alias mapping and canonical resolution."""
    # Direct alias
    profile_ms = organization_registry.classify_organization("Microsoft Reactor")
    assert profile_ms.canonical_name == "Microsoft"
    assert profile_ms.organization_type == HostType.TIER_1_COMPANY
    assert profile_ms.verified is True

    # AWS alias
    profile_aws = organization_registry.classify_organization("AWS User Group Hyderabad")
    assert profile_aws.canonical_name == "Amazon Web Services"
    assert profile_aws.organization_type == HostType.TIER_1_COMPANY

    # University alias
    profile_iith = organization_registry.classify_organization("IIT Hyderabad")
    assert profile_iith.canonical_name == "IIT Hyderabad"
    assert profile_iith.organization_type == HostType.TOP_UNIVERSITY

    # Community detection
    profile_comm = organization_registry.classify_organization("Hyderabad Python Meetup Group")
    assert profile_comm.organization_type == HostType.COMMUNITY

    # Unknown fallback
    profile_unknown = organization_registry.classify_organization("")
    assert profile_unknown.organization_type == HostType.UNKNOWN


def test_event_ranking_scores(sample_events, sample_user_profile):
    """Verify that tier 1 tech events and premier university hackathons rank above casual meetups."""
    ranked = ranking_service.rank_events(sample_events, user=sample_user_profile)

    assert len(ranked) == 3
    # Top ranked event should have high score (> 0.70)
    top_event = ranked[0]
    assert top_event["ranking_score"] >= 0.70
    assert top_event["host_tier"] in [HostType.TIER_1_COMPANY.value, HostType.TOP_UNIVERSITY.value]

    # Casual coffee chat should rank lower
    bottom_event = ranked[-1]
    assert bottom_event["title"] == "Local Casual Coffee Chat"
    assert bottom_event["ranking_score"] < top_event["ranking_score"]


def test_ranking_explanations(sample_events, sample_user_profile):
    """Verify that human-readable explanations are generated without raw internal leak."""
    ranked = ranking_service.rank_events(sample_events, user=sample_user_profile)
    google_event = next(e for e in ranked if "Google" in e["title"])

    assert "why_recommended" in google_event
    reasons = google_event["why_recommended"]
    assert len(reasons) > 0
    # Should cite premier tech leader or matched interest
    assert any("premier tech leader" in r.lower() or "ai" in r.lower() or "free" in r.lower() for r in reasons)


def test_personalization_boost():
    """Verify that user interests directly boost the score for matching events."""
    event = {
        "title": "Rust and Golang Cloud Infrastructure",
        "organizer": "Cloud Devs",
        "date_time": datetime.now(timezone.utc).isoformat(),
        "mode_location": "Online",
        "is_free": True,
        "categories": ["Backend", "Cloud"],
        "description": "Building high-performance microservices with Rust.",
    }

    # User 1: Interested in Rust and Backend
    user_rust = {
        "interests": ["Rust", "Backend"],
        "skills": ["Rust"],
        "preferred_event_types": ["Workshop"],
        "preferred_modes": ["Online"],
    }

    # User 2: Interested in Frontend & Design
    user_ui = {
        "interests": ["Figma", "CSS"],
        "skills": ["React"],
        "preferred_event_types": ["Meetup"],
        "preferred_modes": ["In-Person"],
    }

    score_rust, _, breakdown_rust = ranking_service.calculate_event_score(event, user=user_rust)
    score_ui, _, breakdown_ui = ranking_service.calculate_event_score(event, user=user_ui)

    assert score_rust > score_ui
    assert breakdown_rust["personalization_score"] > breakdown_ui["personalization_score"]
