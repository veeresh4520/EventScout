"""
Main entry point for EventScout Meetup Scraper.
"""

import sys
from pathlib import Path

# Ensure parent directory is in sys.path when running eventscout/main.py directly
parent_dir = Path(__file__).resolve().parent.parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

from eventscout.scrapers.meetup_scraper import scrape_meetup_events


def main():
    scrape_meetup_events()


if __name__ == "__main__":
    main()
