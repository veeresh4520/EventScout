"""
Event Deduplicator for EventScout.
Prevents duplicate events across multiple batches, repeated scraper runs,
and multi-platform cross-posting.
"""

import re
from typing import Dict, List, Optional, Set, Tuple
from eventscout.models.event import Event


def _normalize_string(s: Optional[str]) -> str:
    """Lowercase, strip, and remove excessive punctuation/whitespace."""
    if not s:
        return ""
    # Keep alphanumeric characters and single spaces
    cleaned = re.sub(r"[^\w\s]", "", s.lower())
    return re.sub(r"\s+", " ", cleaned).strip()


class EventDeduplicator:
    """
    In-memory deduplicator utilizing composite exact and fuzzy key fingerprints.
    """

    def __init__(self):
        # Set of seen exact URLs and source-specific IDs
        self._seen_exact_keys: Set[str] = set()
        # Set of composite semantic keys: (normalized_title, date_str, normalized_organizer)
        self._seen_composite_keys: Set[str] = set()

    def is_duplicate(self, event: Event) -> bool:
        """
        Determines whether the given event has already been seen.
        If it's new, registers its signatures and returns False.
        If it's a duplicate, returns True.
        """
        # 1. Exact ID match (e.g. "meetup:316348822")
        exact_id_key = f"{event.source}:{event.source_event_id}" if event.source_event_id else None
        if exact_id_key and exact_id_key in self._seen_exact_keys:
            return True

        # 2. Exact URL match
        if event.event_url and event.event_url in self._seen_exact_keys:
            return True

        # 3. Normalized cross-source composite key:
        # Matches events that have the same title, date, and organizer even if posted on different platforms
        norm_title = _normalize_string(event.title)
        # Group by YYYY-MM-DD
        date_key = event.date_time.strftime("%Y-%m-%d") if hasattr(event.date_time, "strftime") else str(event.date_time)[:10]
        norm_org = _normalize_string(event.organizer)

        composite_key = f"{norm_title}::{date_key}::{norm_org}"
        if composite_key in self._seen_composite_keys:
            return True

        # Register event signatures
        if exact_id_key:
            self._seen_exact_keys.add(exact_id_key)
        if event.event_url:
            self._seen_exact_keys.add(event.event_url)
        if composite_key:
            self._seen_composite_keys.add(composite_key)

        return False

    def deduplicate(self, events: List[Event]) -> Tuple[List[Event], int]:
        """
        Deduplicates a list of events.
        
        Returns:
            Tuple of (unique_events: List[Event], duplicates_removed: int)
        """
        unique_events: List[Event] = []
        duplicate_count = 0

        for event in events:
            if self.is_duplicate(event):
                duplicate_count += 1
            else:
                unique_events.append(event)

        return unique_events, duplicate_count
