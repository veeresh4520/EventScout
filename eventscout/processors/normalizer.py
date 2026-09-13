"""
Event Normalizer for EventScout.
Converts arbitrary raw dictionaries from dynamic collectors into standardized Event domain models.
"""
import logging
import re
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from eventscout.models.event import Event

logger = logging.getLogger("EventNormalizer")


def parse_datetime_flexible(val: Any) -> Optional[datetime]:
    """
    Attempts to parse arbitrary date/time formats into an aware UTC datetime object.
    Supports ISO formats, epoch timestamps (seconds or ms), and common text date strings.
    """
    if val is None:
        return None

    if isinstance(val, datetime):
        if val.tzinfo is None:
            return val.replace(tzinfo=timezone.utc)
        return val.astimezone(timezone.utc)

    # If integer or float timestamp
    if isinstance(val, (int, float)):
        # If timestamp is in milliseconds (e.g. > 10^11)
        if val > 1e11:
            val = val / 1000.0
        try:
            return datetime.fromtimestamp(val, tz=timezone.utc)
        except Exception:
            return None

    val_str = str(val).strip()
    if not val_str:
        return None

    # Try numeric string
    if val_str.isdigit():
        num = int(val_str)
        if num > 1e11:
            num = num / 1000.0
        try:
            return datetime.fromtimestamp(num, tz=timezone.utc)
        except Exception:
            pass

    # Try standard ISO parsing
    try:
        # Replace 'Z' with +00:00 for python fromisoformat
        iso_str = val_str.replace("Z", "+00:00")
        dt = datetime.fromisoformat(iso_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        pass

    # Try common format strings
    formats = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d",
        "%d %b %Y %H:%M",
        "%d %B %Y %H:%M",
        "%b %d, %Y",
        "%B %d, %Y",
        "%a, %b %d, %Y, %I:%M %p",
        "%a, %b %d, %I:%M %p",
        "%A, %B %d, %Y",
        "%m/%d/%Y %H:%M:%S",
        "%m/%d/%Y",
    ]
    for fmt in formats:
        try:
            dt = datetime.strptime(val_str, fmt)
            return dt.replace(tzinfo=timezone.utc)
        except Exception:
            continue

    # Fallback: Check for future date if relative (e.g., "In 2 days", "Tomorrow")
    lower_val = val_str.lower()
    now = datetime.now(timezone.utc)
    if "tomorrow" in lower_val:
        return now + timedelta(days=1)
    if "today" in lower_val:
        return now

    # If all parsing fails, return a default future date (e.g. 7 days from now) with warning
    logger.warning("Unable to parse date string '%s'. Defaulting to 7 days from now.", val_str)
    return now + timedelta(days=7)


class EventNormalizer:
    """
    Validates and normalizes raw event dicts into domain Event instances.
    """

    def __init__(self, default_source_name: str = "generic"):
        self.default_source_name = default_source_name

    def normalize(self, raw_item: Dict[str, Any], source_meta: Optional[Dict[str, Any]] = None) -> Optional[Event]:
        source_meta = source_meta or {}
        source_name = source_meta.get("name") or self.default_source_name

        # 1. Title (Mandatory)
        title = raw_item.get("title")
        if not title or not isinstance(title, str) or not title.strip():
            return None
        title = re.sub(r"\s+", " ", title).strip()

        # 2. Event URL (Mandatory)
        event_url = raw_item.get("event_url") or raw_item.get("url") or source_meta.get("url") or ""
        if not event_url:
            return None

        # 3. Date Time (Mandatory)
        raw_dt = raw_item.get("date_time") or raw_item.get("startDate") or raw_item.get("start_time") or raw_item.get("date")
        date_time = parse_datetime_flexible(raw_dt)
        if not date_time:
            date_time = datetime.now(timezone.utc) + timedelta(days=7)

        # 4. Organizer
        organizer = raw_item.get("organizer") or raw_item.get("host") or source_name
        organizer = str(organizer).strip() if organizer else source_name

        # 5. Location / Mode
        mode_location = raw_item.get("mode_location") or raw_item.get("location") or "Online"
        mode_str = str(mode_location).strip()

        # 6. Pricing
        is_free = raw_item.get("is_free", True)
        if isinstance(is_free, str):
            is_free = is_free.lower() in ("true", "free", "1", "yes")

        price_amount = raw_item.get("price_amount")
        if price_amount is not None:
            try:
                price_amount = float(price_amount)
            except Exception:
                price_amount = None

        price_currency = raw_item.get("price_currency")

        # 7. Categories & Technical flag
        categories = raw_item.get("categories") or []
        if isinstance(categories, str):
            categories = [c.strip() for c in categories.split(",") if c.strip()]

        is_technical = raw_item.get("is_technical", True)
        if isinstance(is_technical, str):
            is_technical = is_technical.lower() in ("true", "1", "yes")

        # 8. IDs and URLs
        source_event_id = raw_item.get("source_event_id") or raw_item.get("id")
        if source_event_id:
            source_event_id = str(source_event_id)
        else:
            source_event_id = event_url

        registration_url = raw_item.get("registration_url") or event_url
        poster_image_url = raw_item.get("poster_image_url") or raw_item.get("image")
        
        # Discard profile avatars, user photos, and attendee portraits from being treated as event posters
        if poster_image_url:
            img_lower = str(poster_image_url).lower()
            if any(k in img_lower for k in ("avatar", "/users/", "/user/", "profile", "attendee", "gravatar", "author")):
                poster_image_url = None

        description = raw_item.get("description")
        if description:
            description = str(description).strip()

        return Event(
            title=title,
            event_url=event_url,
            date_time=date_time,
            organizer=organizer,
            source=source_name.lower().replace(" ", "_"),
            mode_location=mode_str,
            city=raw_item.get("city"),
            country=raw_item.get("country"),
            poster_image_url=poster_image_url,
            description=description,
            is_free=is_free,
            price_amount=price_amount,
            price_currency=price_currency,
            source_event_id=source_event_id,
            registration_url=registration_url,
            is_technical=is_technical,
            categories=categories,
        )

    def normalize_batch(self, raw_items: List[Dict[str, Any]], source_meta: Optional[Dict[str, Any]] = None) -> List[Event]:
        valid_events = []
        for item in raw_items:
            ev = self.normalize(item, source_meta)
            if ev:
                valid_events.append(ev)
        return valid_events
