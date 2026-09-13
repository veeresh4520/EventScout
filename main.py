"""
Main entry point for EventScout Multi-Source Scraper Pipeline.

Usage:
  python main.py                  # Scrapes all ENABLED sources in the registry (multi-source)
  python main.py --meetup-only    # Scrapes only Meetup events
  python main.py --enable-all     # Enables all seeded sources in MongoDB and scrapes them
  python main.py --enable-source <Name>  # Enables a specific source (e.g. Devpost, Devfolio)
  python main.py --pages 2        # Controls max pages to scrape per source
"""

import argparse
import logging
import sys
from pathlib import Path

# Ensure project root is in sys.path
root_dir = Path(__file__).resolve().parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("EventScoutMain")


def main():
    parser = argparse.ArgumentParser(
        description="EventScout Multi-Source Technical Event Scraper Pipeline"
    )
    parser.add_argument(
        "--meetup-only",
        action="store_true",
        help="Run only the legacy Meetup GraphQL scraper",
    )
    parser.add_argument(
        "--enable-all",
        action="store_true",
        help="Mark all registered sources in MongoDB as ENABLED before scraping",
    )
    parser.add_argument(
        "--enable-source",
        type=str,
        default=None,
        help="Mark a specific source (e.g. 'Devpost', 'Devfolio') as ENABLED",
    )
    parser.add_argument(
        "--pages",
        type=int,
        default=3,
        help="Max pages/scrolls per source (default: 3)",
    )
    args = parser.parse_args()

    if args.meetup_only:
        logger.info("=== Running Meetup-only scraper ===")
        from eventscout.scrapers.meetup_scraper import scrape_meetup_events
        scrape_meetup_events(max_pages=args.pages)
        return

    from eventscout.database.source_db import SourceDatabase
    sdb = SourceDatabase()
    scol = sdb.get_collection()

    if args.enable_all:
        logger.info("Enabling all registered sources in MongoDB...")
        res = scol.update_many({}, {"$set": {"status": "ENABLED", "enabled": True}})
        logger.info("Updated %d sources to ENABLED.", res.modified_count)

    if args.enable_source:
        logger.info("Enabling source: %s", args.enable_source)
        res = scol.update_one(
            {"name": {"$regex": f"^{args.enable_source}$", "$options": "i"}},
            {"$set": {"status": "ENABLED", "enabled": True}},
        )
        if res.matched_count > 0:
            logger.info("Source '%s' successfully ENABLED.", args.enable_source)
        else:
            logger.warning("Source '%s' not found in database.", args.enable_source)

    from eventscout.services.scraper_service import ScraperService
    service = ScraperService()
    summary = service.run_pipeline(max_pages=args.pages)

    print("\n" + "=" * 50)
    print("           SCRAPER PIPELINE SUMMARY")
    print("=" * 50)
    print(f"Sources processed:      {summary.get('dynamic_sources_executed', 0)}")
    print(f"New events discovered:  {summary.get('new_inserted', 0)}")
    print(f"Existing events updated:{summary.get('existing_updated', 0)}")
    print(f"Total active events:    {summary.get('total_active_events', 0)}")
    print(f"Notifications sent:     {summary.get('notifications_dispatched', 0)}")
    print("=" * 50 + "\n")


if __name__ == "__main__":
    main()
