"""
Tests for Meetup event parsing, technical event classification, deduplication,
and error resilience.
"""

from datetime import datetime
from eventscout.filters.technical_filter import TechnicalEventFilter
from eventscout.models.event import Event
from eventscout.processors.deduplicator import EventDeduplicator
from eventscout.scrapers.meetup_scraper import _parse_event_node


def test_valid_online_event():
    """Verify parsing of valid online event."""
    raw_node = {
        "title": " Test Event Online ",
        "eventUrl": "https://www.meetup.com/test-group/events/123/",
        "dateTime": "2026-08-30T10:00:00+00:00",
        "featuredEventPhoto": {"highResUrl": "https://img.meetup.com/photo.jpg"},
        "displayPhoto": {"highResUrl": "https://img.meetup.com/fallback.jpg"},
        "group": {"name": "Test Group"},
        "eventType": "ONLINE",
        "venue": {"name": "Online event", "city": ""},
        "feeSettings": None,
        "description": "Learn modern cloud architectures.",
        "id": "123",
    }
    result = _parse_event_node(raw_node, 0)
    assert result is not None
    assert result["title"] == "Test Event Online"
    assert result["event_url"] == "https://www.meetup.com/test-group/events/123/"
    assert isinstance(result["date_time"], datetime)
    assert result["poster_image_url"] == "https://img.meetup.com/photo.jpg"
    assert result["organizer"] == "Test Group"
    assert result["mode_location"] == "Online"
    assert result["is_free"] is True
    assert result["price_amount"] is None
    assert result["price_currency"] is None
    assert result["source"] == "meetup"
    assert result["description"] == "Learn modern cloud architectures."
    assert result["source_event_id"] == "123"


def test_valid_offline_event_with_paid_fee_and_city_fallback():
    """Verify fallback to venue name when city is blank, and paid fee parsing."""
    raw_node = {
        "title": "In-Person Workshop",
        "eventUrl": "https://www.meetup.com/test-group/events/456/",
        "dateTime": "2026-09-01T15:30:00Z",
        "featuredEventPhoto": None,
        "displayPhoto": {"highResUrl": "https://img.meetup.com/display.jpg"},
        "group": {"name": "Coding Club"},
        "eventType": "PHYSICAL",
        "venue": {"name": "Tech Hub Building 3", "city": "   ", "country": "India"},
        "feeSettings": {"amount": "25.50", "currency": "USD"},
    }
    result = _parse_event_node(raw_node, 1)
    assert result is not None
    assert result["poster_image_url"] == "https://img.meetup.com/display.jpg"
    assert result["mode_location"] == "Offline - Tech Hub Building 3"
    assert result["country"] == "India"
    assert result["is_free"] is False
    assert result["price_amount"] == 25.50
    assert result["price_currency"] == "USD"


def test_missing_optional_fields_resilience():
    """Ensure event parses cleanly when optional fields (description, photos, fee) are absent."""
    raw_node = {
        "title": "Minimal Event",
        "eventUrl": "https://www.meetup.com/minimal/events/789/",
        "dateTime": "2026-09-10T12:00:00Z",
        "group": {"name": "Minimalist Devs"},
        "eventType": "ONLINE",
    }
    result = _parse_event_node(raw_node, 2)
    assert result is not None
    assert result["title"] == "Minimal Event"
    assert result["poster_image_url"] is None
    assert result["description"] is None
    assert result["is_free"] is True


def test_malformed_events_skipped():
    """Verify malformed nodes are gracefully rejected."""
    # Missing title
    assert _parse_event_node({"eventUrl": "http://example.com", "dateTime": "2026-08-30T10:00:00Z"}, 0) is None

    # Missing eventUrl
    assert _parse_event_node({"title": "Valid", "dateTime": "2026-08-30T10:00:00Z"}, 1) is None

    # Invalid datetime
    assert _parse_event_node({"title": "Valid", "eventUrl": "http://example.com", "dateTime": "not-a-date"}, 2) is None

    # Missing group / organizer
    assert _parse_event_node({"title": "Valid", "eventUrl": "http://example.com", "dateTime": "2026-08-30T10:00:00Z"}, 3) is None

    # Completely not a dict
    assert _parse_event_node(None, 4) is None  # type: ignore


def test_technical_event_detection():
    """Verify technical topics are correctly classified."""
    classifier = TechnicalEventFilter()

    tech_samples = [
        ("Hands-on Docker and Kubernetes Bootcamp", "Learn container orchestration", "Cloud Native Meetup"),
        ("Deep Dive into Large Language Models & RAG", "Building GenAI pipelines with LangChain", "AI Guild"),
        ("HydPy Monthly Meetup", "Python packaging and FastAPI discussions", "Hyderabad Python User Group"),
        ("LeetCode DSA Problem Solving Session", "Graphs and dynamic programming", "Algo Coders"),
        ("Building Secure Cloud Services on AWS", "IAM policies and zero-trust", "AWS User Group"),
        ("Robotics Workshop with Arduino", "Sensors and embedded C", "Robotics Club"),
        ("Contributing to Open Source on GitHub", "Git workflows and pull requests", "FOSS Hyderabad"),
    ]

    for title, desc, org in tech_samples:
        is_tech, categories = classifier.classify(title, desc, org)
        assert is_tech is True, f"Failed to classify technical event: '{title}'"
        assert len(categories) > 0, f"Expected categories for '{title}', got none."


def test_non_technical_event_rejection():
    """Verify non-technical events are properly rejected."""
    classifier = TechnicalEventFilter()

    non_tech_samples = [
        ("Saturday Speed Dating for Singles", "Meet new people over coffee", "Singles Mixer"),
        ("Morning Yoga in the Park", "Vinyasa flow and relaxation", "Wellness Club"),
        ("Beginner Salsa Dancing Lessons", "Learn basic salsa steps", "Dance Academy"),
        ("Weekend Board Games & Pizza", "Casual Catan and chess night", "Board Gamers"),
        ("Real Estate Investing 101", "Property flipping strategies", "Wealth Creators"),
    ]

    for title, desc, org in non_tech_samples:
        is_tech, categories = classifier.classify(title, desc, org)
        assert is_tech is False, f"Erroneously classified non-tech event as technical: '{title}'"


def test_word_boundary_safety():
    """Verify substrings do not trigger false positive technical classifications."""
    classifier = TechnicalEventFilter()

    # "chair" contains "ai", "email" contains "ml", "training" contains "ai", "fountain" contains "ai"
    edge_cases = [
        ("Buying the Best Office Chair", "Ergonomics discussion", "Office Workers"),
        ("How to Clean Your Email Inbox", "Decluttering your mailbox", "Productivity Group"),
        ("Dog Training Fundamentals", "Puppy obedience tips", "Pet Lovers"),
    ]

    for title, desc, org in edge_cases:
        is_tech, categories = classifier.classify(title, desc, org)
        assert is_tech is False, f"False positive match on substring: '{title}' matched {categories}"


def test_deduplication_exact_and_composite():
    """Verify deduplication removes exact duplicates and cross-posted identical events."""
    dedup = EventDeduplicator()

    dt = datetime(2026, 9, 15, 10, 0, 0)

    event1 = Event(
        title="React Conf 2026",
        event_url="https://meetup.com/events/101",
        date_time=dt,
        organizer="React Community",
        source="meetup",
        source_event_id="101",
    )

    event1_exact_dup = Event(
        title="React Conf 2026",
        event_url="https://meetup.com/events/101",
        date_time=dt,
        organizer="React Community",
        source="meetup",
        source_event_id="101",
    )

    event1_crosspost = Event(
        title=" React Conf 2026! ",
        event_url="https://devpost.com/events/react-2026",
        date_time=dt,
        organizer="React Community",
        source="devpost",
        source_event_id="dp_999",
    )

    event2_distinct = Event(
        title="Vue Conf 2026",
        event_url="https://meetup.com/events/202",
        date_time=dt,
        organizer="Vue Community",
        source="meetup",
        source_event_id="202",
    )

    # First event should not be duplicate
    assert dedup.is_duplicate(event1) is False
    # Exact duplicate must be detected
    assert dedup.is_duplicate(event1_exact_dup) is True
    # Cross-source composite duplicate must be detected
    assert dedup.is_duplicate(event1_crosspost) is True
    # Distinct event must not be duplicate
    assert dedup.is_duplicate(event2_distinct) is False


def test_multi_batch_aggregation():
    """Verify collecting edges from multiple batches accumulates more than 12 events."""
    batch_1_nodes = [
        {
            "id": f"evt_{i}",
            "title": f"Tech Session #{i}",
            "eventUrl": f"https://meetup.com/events/{i}",
            "dateTime": "2026-09-20T10:00:00Z",
            "group": {"name": "Tech Hub"},
            "eventType": "ONLINE",
            "description": "Python and AI coding session.",
        }
        for i in range(1, 13)  # 12 events
    ]

    batch_2_nodes = [
        {
            "id": f"evt_{i}",
            "title": f"Tech Session #{i}",
            "eventUrl": f"https://meetup.com/events/{i}",
            "dateTime": "2026-09-21T10:00:00Z",
            "group": {"name": "Tech Hub"},
            "eventType": "ONLINE",
            "description": "Cloud and DevOps workshop.",
        }
        for i in range(13, 25)  # 12 more events
    ]

    all_raw_nodes = batch_1_nodes + batch_2_nodes
    assert len(all_raw_nodes) == 24

    parsed_events = [_parse_event_node(node, idx) for idx, node in enumerate(all_raw_nodes)]
    assert len(parsed_events) == 24
    assert all(e is not None for e in parsed_events)


if __name__ == "__main__":
    test_valid_online_event()
    test_valid_offline_event_with_paid_fee_and_city_fallback()
    test_missing_optional_fields_resilience()
    test_malformed_events_skipped()
    test_technical_event_detection()
    test_non_technical_event_rejection()
    test_word_boundary_safety()
    test_deduplication_exact_and_composite()
    test_multi_batch_aggregation()
    print("\nAll 9 comprehensive unit test suites passed successfully!")
