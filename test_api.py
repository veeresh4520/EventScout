"""
Unit and Integration tests for EventScout FastAPI /events endpoint.
Tests:
1. GET /events returns events
2. Response is valid JSON
3. MongoDB documents are serialized correctly (ObjectId -> str, datetime -> str)
4. Expired events are not returned
5. Empty database returns an empty list
"""

import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, MagicMock
from bson import ObjectId

from fastapi.testclient import TestClient
from api.main import app


class TestEventsAPI(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.now = datetime.now(timezone.utc)
        self.future_date = self.now + timedelta(days=5)
        self.past_date = self.now - timedelta(days=2)

    def test_health_endpoint(self):
        """Verify /health returns 200 and status ok."""
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "ok")

    @patch("api.main.EventDatabase")
    def test_get_events_returns_events_and_valid_json(self, mock_db_class):
        """Test 1 & 2: GET /events returns valid JSON array of events."""
        mock_db = MagicMock()
        mock_db_class.return_value = mock_db

        mock_event = {
            "id": "66dae67890abcdef12345678",
            "_id": "66dae67890abcdef12345678",
            "title": "AWS Cloud Security Meetup",
            "organizer": "Cloud AWS Group",
            "organization": "Cloud AWS Group",
            "date_time": self.future_date.isoformat(),
            "event_url": "https://www.meetup.com/aws/events/101/",
            "registration_url": "https://www.meetup.com/aws/events/101/",
            "registrationUrl": "https://www.meetup.com/aws/events/101/",
            "mode_location": "Offline - Hyderabad",
            "location": "Offline - Hyderabad",
            "is_free": True,
            "categories": ["Cloud & DevOps", "Cybersecurity"],
            "source": "meetup",
            "source_event_id": "101",
        }
        mock_db.get_upcoming_events.return_value = [mock_event]

        response = self.client.get("/events")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIsInstance(data, list)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["title"], "AWS Cloud Security Meetup")
        self.assertEqual(data[0]["id"], "66dae67890abcdef12345678")

    @patch("eventscout.database.mongodb.MongoClient")
    def test_serialization_of_mongodb_types(self, mock_mongo):
        """Test 3: ObjectId and datetime objects are correctly serialized into JSON strings."""
        mock_col = MagicMock()
        raw_doc = {
            "_id": ObjectId("66dae67890abcdef12345678"),
            "title": "AI Builders",
            "organizer": "AI Community",
            "date_time": self.future_date,
            "source": "meetup",
            "source_event_id": "202",
            "mode_location": "Online",
        }
        mock_col.find.return_value.sort.return_value = [raw_doc]

        from eventscout.database.mongodb import EventDatabase
        db = EventDatabase(uri="mongodb://localhost:27017")
        db._collection = mock_col

        serialized_events = db.get_upcoming_events()
        self.assertEqual(len(serialized_events), 1)
        event = serialized_events[0]

        # Verify ObjectId converted to string
        self.assertEqual(event["_id"], "66dae67890abcdef12345678")
        self.assertEqual(event["id"], "66dae67890abcdef12345678")
        # Verify datetime converted to ISO format string
        self.assertIsInstance(event["date_time"], str)
        self.assertEqual(event["date_time"], self.future_date.isoformat())

    @patch("eventscout.database.mongodb.MongoClient")
    def test_expired_events_not_returned(self, mock_mongo):
        """Test 4: Expired events (in the past) are omitted from get_upcoming_events()."""
        mock_col = MagicMock()
        past_doc = {
            "_id": ObjectId("66dae67890abcdef12345671"),
            "title": "Old Event Yesterday",
            "date_time": self.past_date.isoformat(),
            "source": "meetup",
        }
        future_doc = {
            "_id": ObjectId("66dae67890abcdef12345672"),
            "title": "Upcoming Event Tomorrow",
            "date_time": self.future_date.isoformat(),
            "source": "meetup",
        }
        mock_col.find.return_value.sort.return_value = [past_doc, future_doc]

        from eventscout.database.mongodb import EventDatabase
        db = EventDatabase(uri="mongodb://localhost:27017")
        db._collection = mock_col

        upcoming = db.get_upcoming_events(reference_time=self.now)
        self.assertEqual(len(upcoming), 1)
        self.assertEqual(upcoming[0]["title"], "Upcoming Event Tomorrow")

    @patch("api.main.EventDatabase")
    def test_empty_database_returns_empty_list(self, mock_db_class):
        """Test 5: An empty database returns an empty list []."""
        mock_db = MagicMock()
        mock_db_class.return_value = mock_db
        mock_db.get_upcoming_events.return_value = []

        response = self.client.get("/events")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data, [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
