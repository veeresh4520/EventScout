"""
tests/test_event_filters.py
===========================
Tests for event querying, multi-criteria filtering, and sorting combinations.
"""

import pytest
from eventscout.database.mongodb import EventDatabase


def test_event_database_query_filtering(sample_events):
    """Test memory or live DB multi-criteria query logic."""
    db = EventDatabase()

    # Query with combined filters
    hackathons = db.query_events(
        q="AI",
        event_type="hackathon",
        is_free=True,
        sort_by="recommended"
    )

    # Should return only hackathons matching AI and Free
    assert isinstance(hackathons, list)
    for ev in hackathons:
        assert ev.get("is_free") is True
        title = ev.get("title") or ""
        desc = ev.get("description") or ""
        cats = ev.get("categories") or []
        text = f"{title} {desc} {' '.join(cats)}".lower()
        assert "hackathon" in text or "hack" in text or "code" in text or "build" in text


def test_sorting_strategies():
    """Verify different sorting algorithms work as expected."""
    db = EventDatabase()

    soonest = db.query_events(sort_by="soonest", limit=5)
    assert isinstance(soonest, list)
    if len(soonest) > 1:
        # Check ascending date order
        for i in range(len(soonest) - 1):
            d1 = soonest[i].get("date_time", "")
            d2 = soonest[i+1].get("date_time", "")
            assert d1 <= d2

    recommended = db.query_events(sort_by="recommended", limit=5)
    assert isinstance(recommended, list)
    if len(recommended) > 1:
        # Check descending ranking_score order
        for i in range(len(recommended) - 1):
            s1 = recommended[i].get("ranking_score", 0.0)
            s2 = recommended[i+1].get("ranking_score", 0.0)
            assert s1 >= s2
