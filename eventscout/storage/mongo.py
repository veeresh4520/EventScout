"""
MongoDB Storage Layer for EventScout.
Handles connection, index management, time-based expiration filtering, and upsert operations.
"""

import os
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple, Any

from dotenv import load_dotenv
from pymongo import MongoClient, UpdateOne
from pymongo.collection import Collection
from pymongo.database import Database

from eventscout.models.event import Event

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)


class MongoStorage:
    """
    Manages persistence of EventScout events in MongoDB Atlas.
    Implements:
      - Expired event filtering
      - Idempotent upserts via source & source_event_id / event_url
    """

    def __init__(
        self,
        uri: Optional[str] = None,
        db_name: Optional[str] = None,
        collection_name: str = "events"
    ):
        self.uri = uri or os.getenv("MONGODB_URI")
        self.db_name = db_name or os.getenv("MONGODB_DATABASE", "eventscout")
        self.collection_name = collection_name
        self._client: Optional[MongoClient] = None
        self._db: Optional[Database] = None
        self._collection: Optional[Collection] = None

    def get_collection(self) -> Collection:
        """Lazily connects to MongoDB and returns the events collection."""
        if self._collection is None:
            if not self.uri:
                raise ValueError("MONGODB_URI is not set in environment or .env file.")

            self._client = MongoClient(self.uri, serverSelectionTimeoutMS=20000)
            self._db = self._client[self.db_name]
            self._collection = self._db[self.collection_name]

            # Ensure unique index on source + source_event_id for fast and safe upserts
            self._collection.create_index(
                [("source", 1), ("source_event_id", 1)],
                unique=True,
                name="idx_source_event_unique",
                background=True
            )
            # Index on date_time for chronological sorting and expired queries
            self._collection.create_index(
                [("date_time", 1)],
                name="idx_date_time_asc",
                background=True
            )

        return self._collection

    @staticmethod
    def filter_expired(events: List[Event]) -> Tuple[List[Event], int]:
        """
        Filters out events whose date_time is in the past.
        Returns: (active_upcoming_events, expired_count)
        """
        now = datetime.now(timezone.utc)
        active_events: List[Event] = []
        expired_count = 0

        for event in events:
            dt = event.date_time
            # Ensure timezone awareness for comparison
            if dt.tzinfo is None:
                # Assume UTC if naive
                dt_aware = dt.replace(tzinfo=timezone.utc)
            else:
                dt_aware = dt

            if dt_aware >= now:
                active_events.append(event)
            else:
                expired_count += 1

        return active_events, expired_count

    def upsert_events(self, events: List[Event]) -> Dict[str, Any]:
        """
        Performs bulk upsert operations into the MongoDB collection.
        If an event already exists (matched by source + source_event_id), it is updated.
        If it does not exist, it is inserted.
        """
        if not events:
            return {"total": 0, "upserted": 0, "modified": 0, "matched": 0}

        col = self.get_collection()
        operations = []

        for event in events:
            event_dict = event.to_dict()
            # Unique filter key for this event
            filter_query = {
                "source": event.source,
                "source_event_id": event.source_event_id or event.event_url,
            }

            operations.append(
                UpdateOne(
                    filter_query,
                    {
                        "$set": event_dict,
                        "$setOnInsert": {"first_discovered_at": datetime.now(timezone.utc).isoformat()}
                    },
                    upsert=True
                )
            )

        # Execute bulk write for maximum efficiency
        result = col.bulk_write(operations, ordered=False)

        metrics = {
            "total": len(events),
            "upserted": result.upserted_count,
            "modified": result.modified_count,
            "matched": result.matched_count,
        }
        return metrics
