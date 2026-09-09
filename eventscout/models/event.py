"""
Event domain model for EventScout.
Provides a standardized representation of events collected across all platforms.
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class Event:
    """
    Standardized Event data model.
    Maintains 100% backward compatibility with existing data/events.json fields
    while providing enriched metadata for discovery, filtering, and notifications.
    """
    # Core identifying fields
    title: str
    event_url: str
    date_time: datetime
    organizer: str
    source: str = "meetup"

    # Location & Attendance
    mode_location: str = "Online"
    city: Optional[str] = None
    country: Optional[str] = None

    # Media & Display
    poster_image_url: Optional[str] = None
    description: Optional[str] = None

    # Pricing
    is_free: bool = True
    price_amount: Optional[float] = None
    price_currency: Optional[str] = None

    # Platform & Identification
    source_event_id: Optional[str] = None
    registration_url: Optional[str] = None

    # Technical Classification & Discovery
    is_technical: bool = True
    categories: List[str] = field(default_factory=list)

    # Metadata
    scraped_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")

    def __getitem__(self, key: str) -> Any:
        """Enables dictionary-style indexing e.g. event['title']."""
        try:
            return getattr(self, key)
        except AttributeError:
            raise KeyError(key)

    def get(self, key: str, default: Any = None) -> Any:
        """Enables dict-like get method e.g. event.get('price_amount')."""
        return getattr(self, key, default)

    def __contains__(self, key: str) -> bool:
        """Enables 'title' in event checks."""
        return hasattr(self, key)

    def to_dict(self) -> Dict[str, Any]:
        """Convert the Event instance into a JSON-serializable dictionary."""
        d = asdict(self)
        if isinstance(self.date_time, datetime):
            d["date_time"] = self.date_time.isoformat()
        return d
