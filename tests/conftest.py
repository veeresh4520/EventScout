"""
tests/conftest.py
=================
Pytest fixtures and test configuration for EventScout.
"""

import os
import pytest
from datetime import datetime, timezone

# Ensure test environment variables
os.environ["JWT_SECRET_KEY"] = "test_secret_key_for_eventscout_unit_tests_32_characters_minimum"
os.environ["JWT_ALGORITHM"] = "HS256"


@pytest.fixture
def sample_events():
    now_iso = datetime.now(timezone.utc).isoformat()
    return [
        {
            "title": "Google Cloud & AI DevFest 2026",
            "organizer": "Google Developer Groups",
            "source": "gdg",
            "date_time": now_iso,
            "mode_location": "Online",
            "is_free": True,
            "categories": ["AI", "Cloud", "Workshop"],
            "description": "Hands-on machine learning workshop using Gemini models.",
        },
        {
            "title": "IIT Hyderabad Hackathon for Healthcare",
            "organizer": "IIT Hyderabad",
            "source": "unstop",
            "date_time": now_iso,
            "mode_location": "Hyderabad",
            "is_free": True,
            "categories": ["Hackathon", "AI", "Healthcare"],
            "description": "48 hour national coding hackathon at IIT Hyderabad campus.",
        },
        {
            "title": "Local Casual Coffee Chat",
            "organizer": "Anonymous Hobbyist",
            "source": "meetup",
            "date_time": now_iso,
            "mode_location": "In-Person",
            "is_free": False,
            "price_amount": 200,
            "categories": ["Meetup"],
            "description": "Casual Sunday coffee chat for beginners.",
        },
    ]


@pytest.fixture
def sample_user_profile():
    return {
        "id": "usr_test_123",
        "email": "developer@eventscout.dev",
        "interests": ["AI", "Cloud", "Machine Learning"],
        "skills": ["Python", "TensorFlow"],
        "preferred_event_types": ["Hackathon", "Workshop"],
        "preferred_modes": ["Online"],
    }
