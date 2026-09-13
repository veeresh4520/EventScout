"""
Meetup Collector Adapter for EventScout.
Bridges the existing Playwright GraphQL-intercepting Meetup implementation
into the unified BaseCollector interface without altering its behavior.
"""
import logging
from typing import Any, Dict, List

from eventscout.collectors.base_collector import BaseCollector
from eventscout.scrapers.meetup_scraper import scrape_meetup_events

logger = logging.getLogger("MeetupCollectorAdapter")


class MeetupCollectorAdapter(BaseCollector):
    """
    Adapter preserving the working Playwright + GraphQL interception implementation for Meetup.
    """

    def collect(self, max_pages: int = 3) -> List[Dict[str, Any]]:
        logger.info("[Meetup] Executing specialized GraphQL interceptor adapter (max_pages=%d)...", max_pages)
        try:
            active_events, metrics = scrape_meetup_events(
                max_pages=max_pages,
                return_metrics=True,
            )
            # Convert Event objects to dicts for standard pipeline processing
            raw_dicts = []
            for ev in active_events:
                if hasattr(ev, "to_dict"):
                    raw_dicts.append(ev.to_dict())
                elif isinstance(ev, dict):
                    raw_dicts.append(ev)
            logger.info("[Meetup] Adapter collected %d events.", len(raw_dicts))
            return raw_dicts
        except Exception as e:
            logger.error("[Meetup] Error in Meetup adapter: %s", e, exc_info=True)
            raise e
