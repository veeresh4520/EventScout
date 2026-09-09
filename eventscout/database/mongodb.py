"""
MongoDB Database & Repository Layer for EventScout.

Separates persistent storage concerns from scraping logic:
- Manages MongoDB Atlas connection & indexing
- Provides idempotent upsert capabilities based on (source + source_event_id)
- Handles timezone-aware deletion of expired events
- Maintains clean query interfaces for downstream consumers
"""

import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from dotenv import load_dotenv
from pymongo import MongoClient, UpdateOne
from pymongo.collection import Collection
from pymongo.database import Database

from eventscout.models.event import Event

load_dotenv()

logger = logging.getLogger("EventScoutDB")


class EventDatabase:
    """
    Repository for managing EventScout events in MongoDB.
    """

    def __init__(
        self,
        uri: Optional[str] = None,
        db_name: Optional[str] = None,
        collection_name: str = "events",
    ):
        self.uri = uri or os.getenv("MONGODB_URI")
        self.db_name = db_name or os.getenv("MONGODB_DATABASE", "eventscout")
        self.collection_name = collection_name
        self._client: Optional[MongoClient] = None
        self._db: Optional[Database] = None
        self._collection: Optional[Collection] = None

    def get_collection(self) -> Collection:
        """
        Lazily initializes the MongoDB connection and ensures indexes.
        """
        if self._collection is None:
            if not self.uri:
                raise ValueError(
                    "MONGODB_URI is not set. Please define it in your environment or .env file."
                )

            self._client = MongoClient(self.uri, serverSelectionTimeoutMS=20000)
            self._db = self._client[self.db_name]
            self._collection = self._db[self.collection_name]

            # Step 4: Compound unique index for stable event identity
            # Enforces uniqueness on (source, source_event_id)
            self._collection.create_index(
                [("source", 1), ("source_event_id", 1)],
                unique=True,
                name="idx_source_event_unique",
                background=True,
            )

            # Secondary index on date_time for fast sorting and expiration filtering
            self._collection.create_index(
                [("date_time", 1)],
                name="idx_date_time_asc",
                background=True,
            )

        return self._collection

    @staticmethod
    def is_expired(date_time_val: Any, reference_time: Optional[datetime] = None) -> bool:
        """
        Helper to check if a date_time (datetime or ISO string) is in the past.
        Correctly handles timezone-aware and naive datetimes.
        """
        if reference_time is None:
            reference_time = datetime.now(timezone.utc)
        elif reference_time.tzinfo is None:
            reference_time = reference_time.replace(tzinfo=timezone.utc)

        if isinstance(date_time_val, datetime):
            dt = date_time_val
        else:
            try:
                s = str(date_time_val).strip()
                if s.endswith("Z"):
                    s = s[:-1] + "+00:00"
                dt = datetime.fromisoformat(s)
            except Exception:
                return False

        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)

        return dt <= reference_time

    def delete_expired_events(self, reference_time: Optional[datetime] = None) -> int:
        """
        Removes events from the database whose event date_time has passed.
        Only removes events whose actual event date has elapsed.
        """
        col = self.get_collection()
        expired_ids = []

        for doc in col.find({}, {"_id": 1, "date_time": 1}):
            dt_val = doc.get("date_time")
            if dt_val and self.is_expired(dt_val, reference_time=reference_time):
                expired_ids.append(doc["_id"])

        if expired_ids:
            res = col.delete_many({"_id": {"$in": expired_ids}})
            logger.info("Cleaned up %d expired events from MongoDB.", res.deleted_count)
            return res.deleted_count

        return 0

    def upsert_events(self, events: List[Event]) -> Dict[str, int]:
        """
        Performs an idempotent bulk upsert into MongoDB.
        Uses (source, source_event_id) as the stable identity key.
        If the event exists, its fields are updated.
        If it does not exist, it is inserted as a new document.
        """
        if not events:
            return {
                "total": 0,
                "new_inserted": 0,
                "existing_updated": 0,
                "already_current": 0,
            }

        col = self.get_collection()
        operations = []

        for event in events:
            doc = event.to_dict()
            # Stable identity: source + source_event_id (fallback to event_url)
            event_id = event.source_event_id or event.event_url
            filter_query = {
                "source": event.source,
                "source_event_id": event_id,
            }

            operations.append(
                UpdateOne(
                    filter_query,
                    {
                        "$set": doc,
                        "$setOnInsert": {
                            "created_at": datetime.now(timezone.utc).isoformat()
                        },
                    },
                    upsert=True,
                )
            )

        result = col.bulk_write(operations, ordered=False)

        metrics = {
            "total": len(events),
            "new_inserted": result.upserted_count,
            "existing_updated": result.modified_count,
            "already_current": result.matched_count - result.modified_count,
        }
        return metrics

    def get_upcoming_events(self, reference_time: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """
        Retrieves all active/future events from MongoDB.
        Converts MongoDB-specific types (ObjectId, datetime) into frontend-safe JSON primitives.
        Excludes expired events and sorts chronologically by date_time.
        """
        col = self.get_collection()
        raw_docs = list(col.find().sort("date_time", 1))

        active_events = []
        for doc in raw_docs:
            dt_val = doc.get("date_time")
            # Exclude expired events
            if dt_val and self.is_expired(dt_val, reference_time=reference_time):
                continue

            # Convert ObjectId to string
            if "_id" in doc:
                doc["id"] = str(doc["_id"])
                doc["_id"] = str(doc["_id"])

            # Ensure date_time is an ISO string
            if isinstance(doc.get("date_time"), datetime):
                doc["date_time"] = doc["date_time"].isoformat()

            # Ensure UI convenience aliases if needed
            if "organizer" in doc and "organization" not in doc:
                doc["organization"] = doc["organizer"]
            if "registration_url" in doc and "registrationUrl" not in doc:
                doc["registrationUrl"] = doc["registration_url"]
            if "mode_location" in doc and "location" not in doc:
                doc["location"] = doc["mode_location"]

            active_events.append(doc)

        return active_events

    def find_all(self, filter_query: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Retrieves documents from the collection matching the filter."""
        col = self.get_collection()
        return list(col.find(filter_query or {}))

    def count_documents(self, filter_query: Optional[Dict[str, Any]] = None) -> int:
        """Returns the total number of documents in the collection."""
        col = self.get_collection()
        return col.count_documents(filter_query or {})

