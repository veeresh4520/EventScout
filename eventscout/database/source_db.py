"""
Database layer for managing the Source Registry.
Stores configurations for different event websites discovered by the AI Agent or pre-seeded.
"""
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse, urlunparse
from bson import ObjectId

from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.collection import Collection

load_dotenv()
logger = logging.getLogger("EventScoutSourceDB")


def normalize_source_url(url: str) -> str:
    """
    Normalizes a website URL for consistent matching and duplicate detection:
    - Strips whitespace
    - Lowercases protocol and domain
    - Strips 'www.' prefix
    - Strips trailing slash
    - Strips query params and fragments if general domain matching
    """
    if not url:
        return ""
    url = url.strip()
    if not (url.startswith("http://") or url.startswith("https://")):
        url = "https://" + url

    try:
        parsed = urlparse(url)
        netloc = parsed.netloc.lower()
        if netloc.startswith("www."):
            netloc = netloc[4:]
        
        path = parsed.path.rstrip("/")
        # Keep path if non-empty, otherwise empty
        normalized = urlunparse((parsed.scheme.lower(), netloc, path, "", parsed.query, ""))
        return normalized.rstrip("/")
    except Exception:
        return url.strip().rstrip("/").lower()


class SourceDatabase:
    """
    Repository for managing registered event sources in MongoDB.
    """
    COLLECTION_NAME = "sources"

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
        """Lazily initializes the MongoDB connection and ensures indexes."""
        if self._collection is None:
            if not self.uri:
                raise ValueError("MONGODB_URI is not set.")

            self._client = MongoClient(self.uri, serverSelectionTimeoutMS=20000)
            db = self._client[self.db_name]
            self._collection = db[self.COLLECTION_NAME]

            # Ensure indexes
            self._collection.create_index("normalized_url", unique=True, name="idx_sources_norm_url_unique", background=True)
            self._collection.create_index("url", background=True)
            self._collection.create_index("status", name="idx_sources_status", background=True)

        return self._collection

    def find_duplicate_source(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Checks if a source already exists with the given URL (matching raw or normalized URL).
        """
        col = self.get_collection()
        norm = normalize_source_url(url)
        doc = col.find_one({
            "$or": [
                {"normalized_url": norm},
                {"url": url.strip()},
                {"base_url": url.strip()},
                {"event_list_url": url.strip()},
            ]
        })
        if doc:
            doc["_id"] = str(doc["_id"])
            doc["id"] = str(doc["_id"])
        return doc

    def create_source(
        self,
        url: str,
        name: str = "Unknown",
        status: str = "PENDING",
        source_type: str = "event_platform",
        event_list_url: Optional[str] = None,
        collection_strategy: Optional[str] = None,
        configuration: Optional[Dict[str, Any]] = None,
        field_mapping: Optional[Dict[str, Any]] = None,
        created_by: str = "system",
    ) -> Dict[str, Any]:
        """Creates a new source in the registry."""
        col = self.get_collection()
        clean_url = url.strip()
        norm_url = normalize_source_url(clean_url)
        now = datetime.now(timezone.utc).isoformat()

        doc: Dict[str, Any] = {
            "name": name,
            "base_url": clean_url,
            "event_list_url": (event_list_url or clean_url).strip(),
            "url": clean_url,  # Backwards compatibility
            "normalized_url": norm_url,
            "source_type": source_type,
            "status": status,
            "discovery_status": "READY" if status == "ENABLED" else ("NOT_STARTED" if status == "PENDING" else "IN_PROGRESS"),
            "collection_strategy": collection_strategy or "PLAYWRIGHT",
            "strategy": collection_strategy or "playwright_html",  # Backwards compatibility
            "configuration": configuration or {},
            "field_mapping": field_mapping or {},
            "sample_events": [],
            "confidence_score": 1.0 if status == "ENABLED" else None,
            "notes": "",
            "enabled": (status == "ENABLED"),
            "last_scraped_at": None,
            "last_success_at": None,
            "last_error": None,
            "consecutive_failures": 0,
            "events_found_last_run": 0,
            "created_by": created_by,
            "created_at": now,
            "updated_at": now,
        }

        result = col.insert_one(doc)
        doc["_id"] = str(result.inserted_id)
        doc["id"] = str(result.inserted_id)
        return doc

    def get_source(self, source_id: str) -> Optional[Dict[str, Any]]:
        """Fetch a source by its ID."""
        col = self.get_collection()
        try:
            query = {"_id": ObjectId(source_id)} if ObjectId.is_valid(source_id) else {"_id": source_id}
            doc = col.find_one(query)
            if not doc:
                doc = col.find_one({"id": source_id})
        except Exception:
            return None

        if doc:
            doc["_id"] = str(doc["_id"])
            doc["id"] = str(doc["_id"])
        return doc

    def get_source_by_url(self, url: str) -> Optional[Dict[str, Any]]:
        """Fetch a source by its raw or normalized URL."""
        return self.find_duplicate_source(url)

    def get_all_sources(self) -> List[Dict[str, Any]]:
        """Fetch all sources for the admin panel, sorted by updated_at descending."""
        col = self.get_collection()
        docs = []
        for doc in col.find({}).sort("updated_at", -1):
            doc["_id"] = str(doc["_id"])
            doc["id"] = str(doc["_id"])
            docs.append(doc)
        return docs

    def get_enabled_sources(self) -> List[Dict[str, Any]]:
        """Fetch sources that are enabled and ready for scheduling."""
        col = self.get_collection()
        docs = []
        for doc in col.find({"status": "ENABLED"}):
            doc["_id"] = str(doc["_id"])
            doc["id"] = str(doc["_id"])
            docs.append(doc)
        return docs

    def update_source(self, source_id: str, updates: Dict[str, Any]) -> bool:
        """Update source properties."""
        col = self.get_collection()
        try:
            updates["updated_at"] = datetime.now(timezone.utc).isoformat()
            # If collection_strategy is updated, sync strategy
            if "collection_strategy" in updates and "strategy" not in updates:
                updates["strategy"] = updates["collection_strategy"]
            elif "strategy" in updates and "collection_strategy" not in updates:
                updates["collection_strategy"] = updates["strategy"]
            if "status" in updates:
                updates["enabled"] = (updates["status"] == "ENABLED")

            query = {"_id": ObjectId(source_id)} if ObjectId.is_valid(source_id) else {"_id": source_id}
            res = col.update_one(query, {"$set": updates})
            return res.modified_count > 0 or res.matched_count > 0
        except Exception as e:
            logger.error(f"Error updating source {source_id}: {e}")
            return False

    def update_source_health(
        self,
        source_id: str,
        success: bool,
        error_msg: Optional[str] = None,
        events_count: int = 0
    ) -> bool:
        """
        Updates scrape timestamp and health metrics:
        - If success: resets consecutive_failures to 0, sets last_success_at, updates events_found_last_run.
        - If failure: increments consecutive_failures, records last_error.
          If consecutive_failures reaches 3, automatically flags source as NEEDS_REDISCOVERY.
        """
        col = self.get_collection()
        now = datetime.now(timezone.utc).isoformat()
        query = {"_id": ObjectId(source_id)} if ObjectId.is_valid(source_id) else {"_id": source_id}

        try:
            if success:
                updates = {
                    "last_scraped_at": now,
                    "last_success_at": now,
                    "last_error": None,
                    "consecutive_failures": 0,
                    "events_found_last_run": events_count,
                    "updated_at": now,
                }
                res = col.update_one(query, {"$set": updates})
                return res.acknowledged
            else:
                current = self.get_source(source_id)
                fails = (current.get("consecutive_failures", 0) if current else 0) + 1
                updates = {
                    "last_scraped_at": now,
                    "last_error": error_msg,
                    "consecutive_failures": fails,
                    "updated_at": now,
                }
                if fails >= 3:
                    logger.warning(
                        "[HEALTH] Source %s reached %d consecutive failures. Flagging as NEEDS_REDISCOVERY.",
                        source_id, fails
                    )
                    updates["status"] = "NEEDS_REDISCOVERY"

                res = col.update_one(query, {"$set": updates})
                return res.acknowledged
        except Exception as e:
            logger.error(f"Error updating source health for {source_id}: {e}")
            return False

    def delete_source(self, source_id: str) -> bool:
        """Deletes a source document from the collection."""
        col = self.get_collection()
        try:
            query = {"_id": ObjectId(source_id)} if ObjectId.is_valid(source_id) else {"_id": source_id}
            res = col.delete_one(query)
            return res.deleted_count > 0
        except Exception as e:
            logger.error(f"Error deleting source {source_id}: {e}")
            return False
