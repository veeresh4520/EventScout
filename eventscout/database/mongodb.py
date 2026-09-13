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

        new_event_ids = []
        new_events = []
        if hasattr(result, "upserted_ids") and result.upserted_ids:
            for op_idx, oid in result.upserted_ids.items():
                new_event_ids.append(str(oid))
                if op_idx < len(events):
                    ev_dict = events[op_idx].to_dict()
                    ev_dict["id"] = str(oid)
                    ev_dict["_id"] = str(oid)
                    new_events.append(ev_dict)

        metrics = {
            "total": len(events),
            "new_inserted": result.upserted_count,
            "existing_updated": result.modified_count,
            "already_current": result.matched_count - result.modified_count,
            "new_event_ids": new_event_ids,
            "new_events": new_events,
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

    def query_events(
        self,
        q: Optional[str] = None,
        category: Optional[str] = None,
        event_type: Optional[str] = None,
        mode: Optional[str] = None,
        city: Optional[str] = None,
        is_free: Optional[bool] = None,
        source: Optional[str] = None,
        skills: Optional[List[str]] = None,
        sort_by: str = "recommended",
        user: Optional[Dict[str, Any]] = None,
        limit: Optional[int] = None,
        skip: int = 0,
        reference_time: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        """
        Executes an efficient, multi-criteria query across events in MongoDB,
        ranks results intelligently with user personalization and explanations,
        and applies pagination.
        """
        import re
        from eventscout.services.ranking_service import ranking_service

        col = self.get_collection()
        conditions: List[Dict[str, Any]] = []

        # 1. Text Search across Title, Description, Organizer, Categories
        if q and q.strip():
            tokens = [t.strip() for t in q.strip().split() if t.strip()]
            for token in tokens:
                regex_pat = {"$regex": re.escape(token), "$options": "i"}
                token_or = [
                    {"title": regex_pat},
                    {"description": regex_pat},
                    {"organizer": regex_pat},
                    {"organization": regex_pat},
                    {"categories": regex_pat},
                    {"source": regex_pat},
                ]
                conditions.append({"$or": token_or})

        # 2. Event Type Filter (e.g. hackathon, workshop, conference)
        if event_type and event_type.strip() and event_type.lower() != "all":
            et_lower = event_type.strip().lower()
            regex_pat = {"$regex": re.escape(et_lower), "$options": "i"}
            conditions.append({
                "$or": [
                    {"title": regex_pat},
                    {"description": regex_pat},
                    {"categories": regex_pat},
                ]
            })

        # 3. Category Filter
        if category and category.strip() and category.lower() != "all":
            conditions.append({"categories": {"$regex": re.escape(category.strip()), "$options": "i"}})

        # 4. Mode / Location (Online vs In-Person vs Hybrid)
        if mode and mode.strip() and mode.lower() != "all":
            m_lower = mode.strip().lower()
            if m_lower == "online":
                conditions.append({"mode_location": {"$regex": "online", "$options": "i"}})
            elif m_lower in ["in-person", "offline"]:
                conditions.append({
                    "mode_location": {
                        "$nin": ["Online", "online", "Virtual", "virtual"]
                    }
                })

        # 5. City / Location Filter
        if city and city.strip() and city.lower() != "all":
            city_pat = {"$regex": re.escape(city.strip()), "$options": "i"}
            conditions.append({
                "$or": [
                    {"city": city_pat},
                    {"mode_location": city_pat},
                ]
            })

        # 6. Pricing (Free / Paid)
        if is_free is not None:
            conditions.append({"is_free": is_free})

        # 7. Source Platform
        if source and source.strip() and source.lower() != "all":
            conditions.append({"source": {"$regex": f"^{re.escape(source.strip())}$", "$options": "i"}})

        # 8. Skills
        if skills:
            skill_list = [s.strip() for s in skills if s.strip()]
            if skill_list:
                skill_ors = []
                for sk in skill_list:
                    sk_pat = {"$regex": re.escape(sk), "$options": "i"}
                    skill_ors.extend([
                        {"title": sk_pat},
                        {"description": sk_pat},
                        {"categories": sk_pat},
                    ])
                conditions.append({"$or": skill_ors})

        mongo_filter = {"$and": conditions} if conditions else {}

        raw_docs = list(col.find(mongo_filter))
        active_events = []

        for doc in raw_docs:
            dt_val = doc.get("date_time")
            if dt_val and self.is_expired(dt_val, reference_time=reference_time):
                continue

            if "_id" in doc:
                doc["id"] = str(doc["_id"])
                doc["_id"] = str(doc["_id"])

            if isinstance(doc.get("date_time"), datetime):
                doc["date_time"] = doc["date_time"].isoformat()

            if "organizer" in doc and "organization" not in doc:
                doc["organization"] = doc["organizer"]
            if "registration_url" in doc and "registrationUrl" not in doc:
                doc["registrationUrl"] = doc["registration_url"]
            if "mode_location" in doc and "location" not in doc:
                doc["location"] = doc["mode_location"]

            active_events.append(doc)

        # Apply multi-signal ranking and sorting
        ranked_events = ranking_service.rank_events(
            events=active_events,
            user=user,
            sort_by=sort_by,
        )

        # Pagination
        if skip > 0:
            ranked_events = ranked_events[skip:]
        if limit is not None and limit > 0:
            ranked_events = ranked_events[:limit]

        return ranked_events

    def find_all(self, filter_query: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Retrieves documents from the collection matching the filter."""
        col = self.get_collection()
        return list(col.find(filter_query or {}))

    def count_documents(self, filter_query: Optional[Dict[str, Any]] = None) -> int:
        """Returns the total number of documents in the collection."""
        col = self.get_collection()
        return col.count_documents(filter_query or {})


