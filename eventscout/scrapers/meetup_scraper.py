"""
Meetup Scraper and Pipeline Coordinator for EventScout.
Combines browser automation, network interception, rule-based technical filtering,
and deduplication into a reliable data collection pipeline.
"""

import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# Ensure standard output can handle Unicode characters (arrows, emojis, dashes) on Windows
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from eventscout.database.mongodb import EventDatabase
from eventscout.filters.technical_filter import TechnicalEventFilter
from eventscout.models.event import Event
from eventscout.processors.deduplicator import EventDeduplicator
from eventscout.sources.meetup import MeetupSource, parse_meetup_node

# Configure standard logger
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("MeetupScraper")


def _safe_str(text: Any) -> str:
    """Safely sanitize text for terminal output without Unicode encoding errors."""
    if text is None:
        return ""
    s = str(text)
    try:
        # Test encoding to stdout encoding
        encoding = sys.stdout.encoding or "utf-8"
        return s.encode(encoding, errors="replace").decode(encoding)
    except Exception:
        return s.encode("ascii", errors="replace").decode("ascii")


def _parse_event_node(node: Dict[str, Any], index: int = 0) -> Optional[Event]:
    """
    Backward-compatible wrapper for parsing an individual Meetup event node.
    Used by existing test suites and external callers.
    """
    return parse_meetup_node(node, index)


def _print_pipeline_metrics(
    discovered: int,
    malformed: int,
    rejected_non_technical: int,
    duplicates: int,
    final_saved: int,
) -> None:
    """Displays a clean summary of data filtering metrics."""
    print("\n" + "=" * 60)
    print(" EVENTSCOUT PIPELINE METRICS")
    print("=" * 60)
    print(f"Discovered raw events:     {discovered}")
    print(f"Malformed / skipped:       {malformed}")
    print(f"Rejected as non-technical: {rejected_non_technical}")
    print(f"Duplicates removed:        {duplicates}")
    print(f"Finally saved:             {final_saved}")
    print("=" * 60 + "\n")


def _print_events_summary(events: List[Event]) -> None:
    """Prints a clean, human-readable summary of events to the terminal."""
    total = len(events)
    print("\n" + "=" * 80)
    print(f" TECHNICAL MEETUP EVENTS ({total} event{'s' if total != 1 else ''} retained)")
    print("=" * 80)

    for i, event in enumerate(events, start=1):
        dt = event.date_time
        date_display = dt.strftime("%A, %B %d, %Y at %I:%M %p") if isinstance(dt, datetime) else str(dt)

        if event.is_free:
            price_display = "Free"
        else:
            currency = event.price_currency or ""
            amount = event.price_amount
            price_display = f"{amount:.2f} {currency}".strip() if amount is not None else f"Paid ({currency})".strip()

        categories_str = ", ".join(event.categories) if event.categories else "General Tech"

        print(f"{i}. {_safe_str(event.title)}")
        print(f"   Date:       {_safe_str(date_display)}")
        print(f"   Organizer:  {_safe_str(event.organizer)}")
        print(f"   Categories: {_safe_str(categories_str)}")
        print(f"   Mode:       {_safe_str(event.mode_location)}")
        print(f"   Price:      {_safe_str(price_display)}")
        print(f"   URL:        {_safe_str(event.event_url)}")
        print("-" * 80)
    print()


def _save_events_json(events: List[Event], output_path: Path) -> None:
    """Saves cleaned events list to JSON with ISO-formatted datetimes."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    serialized = [event.to_dict() for event in events]

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(serialized, f, indent=2, ensure_ascii=False)


def scrape_meetup_events(output_file: Optional[str] = None, max_pages: int = 4) -> List[Dict[str, Any]]:
    """
    Main scraper and pipeline function for Meetup event listings.
    Collects multiple batches via Playwright, filters for technical events,
    deduplicates, and saves results to data/events.json.
    """
    print("\n[1/8] Starting Meetup scraper pipeline...")

    # Determine output path (default: data/events.json in package and workspace)
    if output_file:
        output_path = Path(output_file)
    else:
        base_dir = Path(__file__).resolve().parent.parent
        output_path = base_dir / "data" / "events.json"

    # Step 2-4: Collect raw events from Meetup source via browser automation
    print("[2/8] Launching headless browser via Playwright...")
    print("[3/8] Intercepting GraphQL responses from Meetup (gql2)...")
    print(f"[4/8] Collecting event batches via scroll pagination (max {max_pages} pages)...")

    source = MeetupSource()
    raw_events: List[Event] = source.collect_events(max_pages=max_pages)
    discovered_count = source.discovered_raw_count
    malformed_count = source.malformed_count

    print(f"[5/8] Raw events discovered: {discovered_count} (valid parsed: {len(raw_events)})")

    # Step 6: Technical event filtering
    print("[6/8] Filtering technical events...")
    tech_filter = TechnicalEventFilter()
    technical_events: List[Event] = []
    rejected_non_technical = 0

    for event in raw_events:
        # User request: Keep only Hyderabad and Online events
        if event.mode_location != "Online":
            city = (event.city or "").lower()
            if "hyderabad" not in city:
                continue

        is_tech, categories = tech_filter.classify(
            title=event.title,
            description=event.description,
            organizer=event.organizer,
        )
        if is_tech:
            event.is_technical = True
            event.categories = categories
            technical_events.append(event)
        else:
            rejected_non_technical += 1

    print(f"      Retained {len(technical_events)} technical events ({rejected_non_technical} non-technical rejected).")

    # Step 7: Deduplication & Validation
    print("[7/9] Deduplicating and validating events...")
    deduplicator = EventDeduplicator()
    unique_events, duplicate_count = deduplicator.deduplicate(technical_events)

    # Step 8: Filter Expired Events from Scrape Run
    print("[8/9] Filtering expired events from current batch...")
    active_events = []
    expired_in_batch = 0
    for ev in unique_events:
        if EventDatabase.is_expired(ev.date_time):
            expired_in_batch += 1
        else:
            active_events.append(ev)
    print(f"      Retained {len(active_events)} upcoming events ({expired_in_batch} expired excluded).")

    # Step 9: Save to JSON first, then Sync with MongoDB
    print("[9/9] Writing to events.json and synchronizing with MongoDB Atlas...")
    if active_events:
        _save_events_json(active_events, output_path)

        # Also write to workspace root data/events.json if different
        root_data_path = Path("data") / "events.json"
        if root_data_path.resolve() != output_path.resolve():
            _save_events_json(active_events, root_data_path)

        print(f"[SUCCESS] Saved {len(active_events)} technical events to {output_path}")
    else:
        print("[WARNING] Zero upcoming events were found to save.")

    # MongoDB Atlas Lifecycle: Remove Expired + Upsert
    mongo_metrics = {"new_inserted": 0, "existing_updated": 0, "already_current": 0, "total": 0}
    expired_removed_db = 0
    mongo_success = False

    try:
        db = EventDatabase()
        # 1. Clean up events in DB whose date_time has passed
        expired_removed_db = db.delete_expired_events()
        # 2. Upsert future events
        if active_events:
            mongo_metrics = db.upsert_events(active_events)
        mongo_success = True
    except Exception as e:
        logger.error("[ERROR] MongoDB sync failed: %s", e, exc_info=True)
        print(f"\n[WARNING] MongoDB sync failed: {e}")
        print("          Scraped events are safely preserved in data/events.json.")

    # Step 10: Display clear, useful logging summary
    print("\n" + "=" * 60)
    print("         EVENTSCOUT SCRAPER & MONGODB PIPELINE SUMMARY      ")
    print("=" * 60)
    print(f"Scraped raw events:         {discovered_count}")
    print(f"Valid parsed:               {len(raw_events)}")
    print(f"Technical retained:         {len(technical_events)} ({rejected_non_technical} non-technical rejected)")
    print(f"Batch duplicates removed:   {duplicate_count}")
    print(f"Valid future events:        {len(active_events)} ({expired_in_batch} expired excluded)")
    if mongo_success:
        print(f"Expired events removed (DB):{expired_removed_db}")
        print(f"New events inserted (DB):   {mongo_metrics['new_inserted']}")
        print(f"Existing events updated:    {mongo_metrics['existing_updated']}")
        print(f"Already current in DB:      {mongo_metrics['already_current']}")
        print("MongoDB sync status:        COMPLETE (Atlas up to date)")
    else:
        print("MongoDB sync status:        FAILED (Check connection / logs)")
    print(f"JSON backup saved to:       {output_path}")
    print("=" * 60 + "\n")

    if active_events:
        _print_events_summary(active_events)

    return [e.to_dict() for e in active_events]


if __name__ == "__main__":
    scrape_meetup_events()
