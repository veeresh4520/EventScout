"""
Sync events from events.json into MongoDB Atlas.
Executes the pipeline: Load -> Normalize -> Remove Expired -> Upsert.
"""

import json
from datetime import datetime
from pathlib import Path

from eventscout.models.event import Event
from eventscout.storage.mongo import MongoStorage


def sync_events_json_to_mongo():
    base_dir = Path(__file__).resolve().parent.parent.parent
    events_file = base_dir / "data" / "events.json"

    if not events_file.exists():
        # Fallback to eventscout/data/events.json
        events_file = base_dir / "eventscout" / "data" / "events.json"

    if not events_file.exists():
        print(f"Error: {events_file} not found. Run the scraper first.")
        return

    print("------------------------------------------------------------")
    print("EventScout: Syncing events.json to MongoDB Atlas")
    print("------------------------------------------------------------")
    print("1. [LOAD] Loading events from JSON file...")
    with open(events_file, "r", encoding="utf-8") as f:
        raw_list = json.load(f)

    print(f"   Loaded {len(raw_list)} raw events.")

    print("2. [NORMALIZE] Converting to standard Event models...")
    events = []
    for item in raw_list:
        try:
            # Parse ISO date string to datetime object
            dt_str = item.get("date_time")
            if dt_str:
                dt = datetime.fromisoformat(dt_str)
            else:
                continue

            event = Event(
                title=item.get("title", ""),
                event_url=item.get("event_url", ""),
                date_time=dt,
                organizer=item.get("organizer", ""),
                source=item.get("source", "meetup"),
                mode_location=item.get("mode_location", "Online"),
                city=item.get("city"),
                country=item.get("country"),
                poster_image_url=item.get("poster_image_url"),
                description=item.get("description"),
                is_free=item.get("is_free", True),
                price_amount=item.get("price_amount"),
                price_currency=item.get("price_currency"),
                source_event_id=item.get("source_event_id"),
                registration_url=item.get("registration_url"),
                is_technical=item.get("is_technical", True),
                categories=item.get("categories", []),
            )
            events.append(event)
        except Exception as e:
            continue

    print(f"   Normalized {len(events)} events.")

    print("3. [REMOVE EXPIRED] Filtering past events...")
    upcoming_events, expired_count = MongoStorage.filter_expired(events)
    print(f"   Removed {expired_count} expired events.")
    print(f"   Retained {len(upcoming_events)} upcoming events.")

    print("4. [UPSERT] Upserting to MongoDB Atlas (eventscout.events)...")
    storage = MongoStorage()
    metrics = storage.upsert_events(upcoming_events)

    print("------------------------------------------------------------")
    print("PIPELINE RESULT:")
    print(f"   Total processed: {metrics['total']}")
    print(f"   New inserted:    {metrics['upserted']}")
    print(f"   Updated:         {metrics['modified']}")
    print(f"   Already current: {metrics['matched']}")
    print("------------------------------------------------------------")
    print("SUCCESS: Events are now synchronized with MongoDB Atlas!")


if __name__ == "__main__":
    sync_events_json_to_mongo()
