"""
User Database & Repository Layer for EventScout.

Follows the same pattern as EventDatabase (eventscout/database/mongodb.py).
Manages the 'users' collection with:
- Unique email index
- Idempotent save/unsave operations using $addToSet / $pull
- Preference updates
- Password hash storage (never plain text)
"""

import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from bson import ObjectId
from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.collection import Collection

load_dotenv()

logger = logging.getLogger("EventScoutUserDB")


class UserDatabase:
    """
    Repository for managing EventScout users in MongoDB.
    All operations are user-scoped; no cross-user data access is possible
    through this interface.
    """

    COLLECTION_NAME = "users"

    def __init__(
        self,
        uri: Optional[str] = None,
        db_name: Optional[str] = None,
    ):
        self.uri = uri or os.getenv("MONGODB_URI")
        self.db_name = db_name or os.getenv("MONGODB_DATABASE", "eventscout")
        self._client: Optional[MongoClient] = None
        self._collection: Optional[Collection] = None

    def get_collection(self) -> Collection:
        """
        Lazily initializes the MongoDB connection and ensures indexes on
        the 'users' collection.
        """
        if self._collection is None:
            if not self.uri:
                raise ValueError(
                    "MONGODB_URI is not set. Please define it in your environment or .env file."
                )

            self._client = MongoClient(self.uri, serverSelectionTimeoutMS=20000)
            db = self._client[self.db_name]
            self._collection = db[self.COLLECTION_NAME]

            # Unique index on email — prevents duplicate accounts
            self._collection.create_index(
                "email",
                unique=True,
                name="idx_users_email_unique",
                background=True,
            )

            # Index on username for quick profile and login lookup
            self._collection.create_index(
                "username",
                name="idx_users_username",
                background=True,
            )

            # Index on saved_event_ids for efficient membership checks
            self._collection.create_index(
                "saved_event_ids",
                name="idx_users_saved_event_ids",
                background=True,
            )

        return self._collection

    # ------------------------------------------------------------------
    # User creation & lookup
    # ------------------------------------------------------------------

    def create_user(
        self,
        email: str,
        password_hash: str,
        username: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Inserts a new user document.
        Raises pymongo.errors.DuplicateKeyError if email already exists.
        Returns the inserted document with _id as string.
        """
        col = self.get_collection()
        cleaned_email = email.lower().strip()
        cleaned_username = (
            username.strip() if username else cleaned_email.split("@")[0]
        )

        doc = {
            "username": cleaned_username,
            "email": cleaned_email,
            "password_hash": password_hash,
            "interests": [],
            "skills": [],
            "preferred_event_types": [],
            "preferred_modes": [],
            "saved_event_ids": [],
            "is_admin": False,
            "notification_preferences": {
                "dashboard_enabled": True,
                "browser_enabled": True,
                "email_enabled": True,
            },
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        result = col.insert_one(doc)
        doc["_id"] = str(result.inserted_id)
        doc["id"] = str(result.inserted_id)
        return doc

    def find_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Find a user by email address (case-insensitive)."""
        col = self.get_collection()
        doc = col.find_one({"email": email.lower().strip()})
        if doc:
            doc["id"] = str(doc["_id"])
            doc["_id"] = str(doc["_id"])
        return doc

    def find_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """Find a user by username."""
        col = self.get_collection()
        doc = col.find_one({"username": username.strip()})
        if doc:
            doc["id"] = str(doc["_id"])
            doc["_id"] = str(doc["_id"])
        return doc

    def find_by_identifier(self, identifier: str) -> Optional[Dict[str, Any]]:
        """Find a user by either email or username."""
        cleaned = identifier.strip()
        if "@" in cleaned:
            return self.find_by_email(cleaned)
        user = self.find_by_username(cleaned)
        if not user:
            user = self.find_by_email(cleaned)
        return user

    def find_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Find a user by their MongoDB _id string."""
        col = self.get_collection()
        try:
            obj_id = ObjectId(user_id)
        except Exception:
            return None
        doc = col.find_one({"_id": obj_id})
        if doc:
            doc["id"] = str(doc["_id"])
            doc["_id"] = str(doc["_id"])
        return doc

    def get_all_active_users(self) -> List[Dict[str, Any]]:
        """Returns all users for notification processing and daily digests."""
        col = self.get_collection()
        users = []
        for doc in col.find({}):
            doc["id"] = str(doc["_id"])
            doc["_id"] = str(doc["_id"])
            if "notification_preferences" not in doc:
                doc["notification_preferences"] = {
                    "dashboard_enabled": True,
                    "browser_enabled": True,
                    "email_enabled": True,
                }
            users.append(doc)
        return users

    # ------------------------------------------------------------------
    # Preferences
    # ------------------------------------------------------------------

    def update_preferences(self, user_id: str, prefs: Dict[str, Any]) -> bool:
        """
        Updates the user's personalization preferences.
        Only updates allowed preference fields; ignores any other keys.
        Returns True if a document was modified.
        """
        allowed_fields = {
            "interests", "skills", "preferred_event_types", "preferred_modes", "notification_preferences"
        }
        update_doc = {
            k: v for k, v in prefs.items() if k in allowed_fields
        }
        if not update_doc:
            return False

        col = self.get_collection()
        try:
            obj_id = ObjectId(user_id)
        except Exception:
            return False

        result = col.update_one({"_id": obj_id}, {"$set": update_doc})
        return result.modified_count > 0 or result.matched_count > 0

    def update_profile(self, user_id: str, profile_data: Dict[str, Any]) -> bool:
        """
        Updates user profile attributes such as username.
        Prevents duplicate usernames across accounts.
        """
        col = self.get_collection()
        try:
            obj_id = ObjectId(user_id)
        except Exception:
            return False

        allowed_fields = {"username"}
        update_doc = {k: v for k, v in profile_data.items() if k in allowed_fields}
        if not update_doc:
            return False

        if "username" in update_doc:
            new_username = str(update_doc["username"]).strip()
            if not new_username:
                raise ValueError("Username cannot be empty.")
            existing = col.find_one({"username": new_username, "_id": {"$ne": obj_id}})
            if existing:
                raise ValueError(f"Username '{new_username}' is already taken.")
            update_doc["username"] = new_username

        result = col.update_one({"_id": obj_id}, {"$set": update_doc})
        return result.modified_count > 0 or result.matched_count > 0

    # ------------------------------------------------------------------
    # Save / Unsave events (user-specific relationship)
    # ------------------------------------------------------------------

    def save_event(self, user_id: str, event_id: str) -> bool:
        """
        Adds event_id to the user's saved_event_ids list.
        Uses $addToSet — idempotent, prevents duplicates at the DB level.
        Returns True if the document was found and operation succeeded.
        """
        col = self.get_collection()
        try:
            obj_id = ObjectId(user_id)
        except Exception:
            return False

        result = col.update_one(
            {"_id": obj_id},
            {"$addToSet": {"saved_event_ids": event_id}},
        )
        return result.matched_count > 0

    def unsave_event(self, user_id: str, event_id: str) -> bool:
        """
        Removes event_id from the user's saved_event_ids list.
        Uses $pull — idempotent, no error if event_id was not in the list.
        Returns True if the document was found.
        """
        col = self.get_collection()
        try:
            obj_id = ObjectId(user_id)
        except Exception:
            return False

        result = col.update_one(
            {"_id": obj_id},
            {"$pull": {"saved_event_ids": event_id}},
        )
        return result.matched_count > 0

    def get_saved_event_ids(self, user_id: str) -> List[str]:
        """
        Returns the list of saved event ID strings for a user.
        Returns an empty list if user not found.
        """
        col = self.get_collection()
        try:
            obj_id = ObjectId(user_id)
        except Exception:
            return []

        doc = col.find_one({"_id": obj_id}, {"saved_event_ids": 1})
        if not doc:
            return []
        return doc.get("saved_event_ids", [])
