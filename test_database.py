"""
Unit tests for EventScout MongoDB Database Layer.
Validates:
1. New event insertion
2. Idempotent deduplication (running same event twice)
3. Document updating on event detail changes
4. Expired event identification and removal
5. Future event retention
6. Stable identity (source + source_event_id)
"""

import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

from eventscout.database.mongodb import EventDatabase
from eventscout.models.event import Event


class TestEventDatabase(unittest.TestCase):
    """Test suite covering database behavior and requirements."""

    def setUp(self):
        self.now = datetime.now(timezone.utc)
        self.future_date = self.now + timedelta(days=7)
        self.past_date = self.now - timedelta(days=2)

        self.sample_event = Event(
            title="Kafka & Stream Processing Meetup",
            event_url="https://www.meetup.com/hyderabad-kafka/events/12345/",
            date_time=self.future_date,
            organizer="Hyderabad Kafka Group",
            source="meetup",
            source_event_id="12345",
            mode_location="Offline - Hyderabad",
            city="Hyderabad",
            is_free=True,
            categories=["Data & Databases"],
        )

    def test_6_stable_identity(self):
        """Test 6: Verify same Meetup event always resolves to the same identity key."""
        event1 = Event(
            title="Old Title",
            event_url="https://www.meetup.com/events/99999/",
            date_time=self.future_date,
            organizer="Group A",
            source="meetup",
            source_event_id="99999",
        )
        event2 = Event(
            title="Updated Title For Same Event",
            event_url="https://www.meetup.com/events/99999/",
            date_time=self.future_date,
            organizer="Group A",
            source="meetup",
            source_event_id="99999",
        )

        identity1 = f"{event1.source}:{event1.source_event_id}"
        identity2 = f"{event2.source}:{event2.source_event_id}"
        self.assertEqual(identity1, identity2)
        self.assertEqual(identity1, "meetup:99999")

    def test_4_expired_event_detection(self):
        """Test 4: An event whose date/time has passed is correctly identified as expired."""
        self.assertTrue(EventDatabase.is_expired(self.past_date, reference_time=self.now))
        # Also test ISO string format
        self.assertTrue(EventDatabase.is_expired(self.past_date.isoformat(), reference_time=self.now))

    def test_5_future_event_retention(self):
        """Test 5: A future event is NOT identified as expired and remains valid."""
        self.assertFalse(EventDatabase.is_expired(self.future_date, reference_time=self.now))
        self.assertFalse(EventDatabase.is_expired(self.future_date.isoformat(), reference_time=self.now))

    @patch("eventscout.database.mongodb.MongoClient")
    def test_1_new_event_inserted(self, mock_mongo_client):
        """Test 1: A new event is inserted using bulk upsert."""
        mock_col = MagicMock()
        mock_bulk_res = MagicMock()
        mock_bulk_res.upserted_count = 1
        mock_bulk_res.modified_count = 0
        mock_bulk_res.matched_count = 0
        mock_col.bulk_write.return_value = mock_bulk_res

        db = EventDatabase(uri="mongodb://localhost:27017")
        db._collection = mock_col

        metrics = db.upsert_events([self.sample_event])

        self.assertEqual(metrics["new_inserted"], 1)
        self.assertEqual(metrics["existing_updated"], 0)
        mock_col.bulk_write.assert_called_once()
        ops = mock_col.bulk_write.call_args[0][0]
        self.assertEqual(len(ops), 1)
        self.assertEqual(ops[0]._filter, {"source": "meetup", "source_event_id": "12345"})
        self.assertTrue(ops[0]._upsert)

    @patch("eventscout.database.mongodb.MongoClient")
    def test_2_existing_event_idempotency(self, mock_mongo_client):
        """Test 2: Running the same event twice matches without duplicating."""
        mock_col = MagicMock()
        mock_bulk_res = MagicMock()
        mock_bulk_res.upserted_count = 0
        mock_bulk_res.modified_count = 0
        mock_bulk_res.matched_count = 1
        mock_col.bulk_write.return_value = mock_bulk_res

        db = EventDatabase(uri="mongodb://localhost:27017")
        db._collection = mock_col

        metrics = db.upsert_events([self.sample_event])
        self.assertEqual(metrics["new_inserted"], 0)
        self.assertEqual(metrics["already_current"], 1)

    @patch("eventscout.database.mongodb.MongoClient")
    def test_3_existing_event_changed(self, mock_mongo_client):
        """Test 3: If an existing event's information changes, it is modified."""
        mock_col = MagicMock()
        mock_bulk_res = MagicMock()
        mock_bulk_res.upserted_count = 0
        mock_bulk_res.modified_count = 1
        mock_bulk_res.matched_count = 1
        mock_col.bulk_write.return_value = mock_bulk_res

        db = EventDatabase(uri="mongodb://localhost:27017")
        db._collection = mock_col

        self.sample_event.title = "Updated Kafka Conference 2026"
        metrics = db.upsert_events([self.sample_event])
        self.assertEqual(metrics["new_inserted"], 0)
        self.assertEqual(metrics["existing_updated"], 1)

    @patch("eventscout.database.mongodb.MongoClient")
    def test_4_delete_expired_events_query(self, mock_mongo_client):
        """Test 4: delete_expired_events deletes only expired documents."""
        mock_col = MagicMock()
        mock_col.find.return_value = [
            {"_id": "doc1", "date_time": self.past_date.isoformat()},
            {"_id": "doc2", "date_time": self.future_date.isoformat()},
        ]
        mock_delete_res = MagicMock()
        mock_delete_res.deleted_count = 1
        mock_col.delete_many.return_value = mock_delete_res

        db = EventDatabase(uri="mongodb://localhost:27017")
        db._collection = mock_col

        deleted = db.delete_expired_events(reference_time=self.now)
        self.assertEqual(deleted, 1)
        mock_col.delete_many.assert_called_once_with({"_id": {"$in": ["doc1"]}})


if __name__ == "__main__":
    unittest.main(verbosity=2)
