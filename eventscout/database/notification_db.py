"""
Notification Database Repository for EventScout.

Manages:
1. 'notifications' collection:
   - Stores in-app/dashboard notifications for authenticated users.
   - Compound unique index on (user_id, event_id, type) ensures NO DUPLICATE notifications.
   - Provides read/unread tracking and unread counts.
2. 'sent_digests' collection:
   - Tracks daily email digests sent per user per date.
   - Compound unique index on (user_id, date_str) prevents duplicate daily emails.
"""

import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from bson import ObjectId
from dotenv import load_dotenv
from pymongo import ASCENDING, DESCENDING, MongoClient
from pymongo.collection import Collection
from pymongo.errors import DuplicateKeyError

load_dotenv()

logger = logging.getLogger("EventScoutNotificationDB")


class NotificationDatabase:
    """
    Repository for managing notifications and email digest records in MongoDB.
    Enforces user-scoped access and idempotency at the database level.
    """

    NOTIFICATIONS_COLLECTION = "notifications"
    SENT_DIGESTS_COLLECTION = "sent_digests"

    def __init__(
        self,
        uri: Optional[str] = None,
        db_name: Optional[str] = None,
    ):
        self.uri = uri or os.getenv("MONGODB_URI")
        self.db_name = db_name or os.getenv("MONGODB_DATABASE", "eventscout")
        self._client: Optional[MongoClient] = None
        self._notifications_col: Optional[Collection] = None
        self._sent_digests_col: Optional[Collection] = None

    def get_client(self) -> MongoClient:
        if self._client is None:
            if not self.uri:
                raise ValueError("MONGODB_URI is not set.")
            self._client = MongoClient(self.uri, serverSelectionTimeoutMS=20000)
        return self._client

    def get_notifications_collection(self) -> Collection:
        """Lazily initializes connection and ensures indexes on 'notifications' collection."""
        if self._notifications_col is None:
            db = self.get_client()[self.db_name]
            self._notifications_col = db[self.NOTIFICATIONS_COLLECTION]

            # Compound unique index prevents notifying the same user about the same event twice
            self._notifications_col.create_index(
                [("user_id", ASCENDING), ("event_id", ASCENDING), ("type", ASCENDING)],
                unique=True,
                name="idx_notifications_user_event_type_unique",
                background=True,
            )

            # Query performance indexes
            self._notifications_col.create_index(
                [("user_id", ASCENDING), ("created_at", DESCENDING)],
                name="idx_notifications_user_created_desc",
                background=True,
            )
            self._notifications_col.create_index(
                [("user_id", ASCENDING), ("read", ASCENDING)],
                name="idx_notifications_user_read",
                background=True,
            )

        return self._notifications_col

    def get_sent_digests_collection(self) -> Collection:
        """Lazily initializes connection and ensures indexes on 'sent_digests' collection."""
        if self._sent_digests_col is None:
            db = self.get_client()[self.db_name]
            self._sent_digests_col = db[self.SENT_DIGESTS_COLLECTION]

            # Unique index on (user_id, date_str) prevents sending duplicate daily digests
            self._sent_digests_col.create_index(
                [("user_id", ASCENDING), ("date_str", ASCENDING)],
                unique=True,
                name="idx_sent_digests_user_date_unique",
                background=True,
            )

        return self._sent_digests_col

    # ------------------------------------------------------------------
    # Dashboard Notifications
    # ------------------------------------------------------------------

    def create_notification(
        self,
        user_id: str,
        event_id: str,
        title: str,
        message: str,
        notification_type: str = "new_event",
        event_url: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Creates a new dashboard notification for a user.
        If a notification for (user_id, event_id, notification_type) already exists,
        DuplicateKeyError is caught and None is returned (idempotent, no spam).
        """
        col = self.get_notifications_collection()
        doc = {
            "user_id": str(user_id),
            "event_id": str(event_id),
            "type": notification_type,
            "title": title.strip(),
            "message": message.strip(),
            "event_url": event_url or "",
            "read": False,
            "metadata": metadata or {},
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        try:
            result = col.insert_one(doc)
            doc["_id"] = str(result.inserted_id)
            doc["id"] = str(result.inserted_id)
            return doc
        except DuplicateKeyError:
            # Notification already exists for this event and user
            return None

    def get_user_notifications(self, user_id: str, limit: int = 30) -> List[Dict[str, Any]]:
        """
        Retrieves recent notifications for a user, newest first.
        Converts ObjectId to string.
        """
        col = self.get_notifications_collection()
        cursor = col.find({"user_id": str(user_id)}).sort("created_at", DESCENDING).limit(limit)

        notifications = []
        for doc in cursor:
            doc["id"] = str(doc["_id"])
            doc["_id"] = str(doc["_id"])
            notifications.append(doc)
        return notifications

    def get_unread_count(self, user_id: str) -> int:
        """Returns the number of unread notifications for a user."""
        col = self.get_notifications_collection()
        return col.count_documents({"user_id": str(user_id), "read": False})

    def mark_as_read(self, user_id: str, notification_id: str) -> bool:
        """
        Marks a specific notification as read.
        Ensures user_id matches so User A cannot modify User B's notifications.
        """
        col = self.get_notifications_collection()
        try:
            oid = ObjectId(notification_id)
        except Exception:
            return False

        result = col.update_one(
            {"_id": oid, "user_id": str(user_id)},
            {"$set": {"read": True}},
        )
        return result.modified_count > 0 or result.matched_count > 0

    def mark_all_read(self, user_id: str) -> int:
        """Marks all unread notifications for a user as read."""
        col = self.get_notifications_collection()
        result = col.update_many(
            {"user_id": str(user_id), "read": False},
            {"$set": {"read": True}},
        )
        return result.modified_count

    # ------------------------------------------------------------------
    # Daily Email Digest Idempotency
    # ------------------------------------------------------------------

    def has_digest_been_sent(self, user_id: str, date_str: str) -> bool:
        """
        Checks whether a daily digest was already sent to this user for date_str (YYYY-MM-DD).
        """
        col = self.get_sent_digests_collection()
        doc = col.find_one({"user_id": str(user_id), "date_str": date_str})
        return doc is not None

    def record_digest_sent(self, user_id: str, date_str: str, event_count: int) -> bool:
        """
        Records that a daily digest was sent to user_id on date_str.
        Returns True if recorded, False if already exists.
        """
        col = self.get_sent_digests_collection()
        try:
            col.insert_one({
                "user_id": str(user_id),
                "date_str": date_str,
                "event_count": event_count,
                "sent_at": datetime.now(timezone.utc).isoformat(),
            })
            return True
        except DuplicateKeyError:
            return False
