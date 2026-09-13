"""
Scraper Service for EventScout.

Coordinates:
1. Dynamically querying the Source Registry for enabled sources.
2. Selecting and running generic collectors (HTML, REST API, GraphQL, Playwright, Meetup Adapter).
3. Isolating collector failures so broken sources do not crash the scheduler or other scrapers.
4. Normalizing, deduplicating, and technical-filtering events.
5. Synchronizing events with MongoDB and extracting newly discovered events.
6. Passing newly discovered events to NotificationService for user alerts and digests.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from eventscout.collectors.factory import get_collector_for_source
from eventscout.database.mongodb import EventDatabase
from eventscout.database.source_db import SourceDatabase
from eventscout.filters.technical_filter import TechnicalEventFilter
from eventscout.models.event import Event
from eventscout.processors.deduplicator import EventDeduplicator
from eventscout.processors.normalizer import EventNormalizer
from eventscout.scrapers.meetup_scraper import scrape_meetup_events
from eventscout.services.notification_service import NotificationService
from eventscout.utils.logging_config import structured_logger

logger = logging.getLogger("EventScoutScraperService")


class ScraperService:
    """
    Coordinates dynamic scraper runs and handoff to the notification pipeline.
    """

    def __init__(
        self,
        notification_service: Optional[NotificationService] = None,
        source_db: Optional[SourceDatabase] = None,
        event_db: Optional[EventDatabase] = None,
    ):
        self.notification_service = notification_service or NotificationService()
        self.source_db = source_db or SourceDatabase()
        self.event_db = event_db or EventDatabase()
        self.normalizer = EventNormalizer()
        self.tech_filter = TechnicalEventFilter()
        self.deduplicator = EventDeduplicator()

    def run_pipeline(self, max_pages: int = 4) -> Dict[str, Any]:
        """
        Executes the dynamic scraping pipeline:
        1. Find all sources where status = ENABLED
        2. For each source, instantiate generic collector & extract with Failure Isolation
        3. Normalize, filter, deduplicate, and upsert to MongoDB
        4. Update source health metrics
        5. Dispatch notifications for newly discovered events
        """
        logger.info("Starting automated dynamic scraper pipeline run (max_pages=%d)...", max_pages)

        all_new_events: List[Dict[str, Any]] = []
        total_active_events_count = 0
        total_new_count = 0
        total_updated_count = 0
        total_current_count = 0

        # Query enabled sources from Source Registry
        enabled_sources: List[Dict[str, Any]] = []
        try:
            enabled_sources = self.source_db.get_enabled_sources()
            if not enabled_sources:
                logger.info("No enabled sources found in registry. Checking seeder...")
                from eventscout.database.seed_sources import seed_predefined_sources
                seed_predefined_sources(self.source_db)
                enabled_sources = self.source_db.get_enabled_sources()

            logger.info("[SCHEDULER] Found %d enabled sources", len(enabled_sources))
        except Exception as e:
            logger.error("[SCHEDULER ERROR] Error retrieving enabled sources: %s", e)

        import time

        # Scrape each enabled source with strict failure isolation
        for source in enabled_sources:
            source_id = source.get("id") or source.get("_id")
            source_name = source.get("name", "Unknown Source")
            strategy = source.get("collection_strategy") or source.get("strategy", "PLAYWRIGHT")

            start_t = time.time()
            structured_logger.log_event(
                event_tag="SCRAPE_STARTED",
                message=f"Starting collection for source {source_name}",
                source=source_name,
                extra={"strategy": strategy}
            )

            try:
                # 1. Instantiate collector via Factory
                collector = get_collector_for_source(source)

                # 2. Extract raw events
                raw_items = collector.collect(max_pages=max_pages)
                logger.info("[SOURCE] %s → %d raw items extracted", source_name, len(raw_items))

                # 3. Normalize into Event domain models
                normalized = self.normalizer.normalize_batch(raw_items, source)

                # 4. Filter expired, duplicates, and non-technical
                tech_events = []
                for ev in normalized:
                    if EventDatabase.is_expired(ev.date_time):
                        continue
                    if self.deduplicator.is_duplicate(ev):
                        continue
                    if self.tech_filter.is_technical_event(ev.title, ev.description or ""):
                        tech_events.append(ev)

                # 5. Upsert to MongoDB
                inserted = 0
                updated = 0
                if tech_events:
                    metrics = self.event_db.upsert_events(tech_events)
                    inserted = metrics.get("new_inserted", 0)
                    updated = metrics.get("existing_updated", 0)
                    total_active_events_count += len(tech_events)
                    total_new_count += inserted
                    total_updated_count += updated
                    total_current_count += metrics.get("already_current", 0)
                    all_new_events.extend(metrics.get("new_events", []))

                    if inserted > 0:
                        structured_logger.log_event(
                            event_tag="EVENT_INSERTED",
                            message=f"Inserted {inserted} new events for {source_name}",
                            source=source_name,
                            events_inserted=inserted,
                        )

                # 6. Record source health on success
                duration = time.time() - start_t
                self.source_db.update_source_health(
                    source_id,
                    success=True,
                    events_count=len(tech_events)
                )
                structured_logger.log_event(
                    event_tag="SCRAPE_COMPLETED",
                    message=f"Successfully scraped {len(tech_events)} events from {source_name}",
                    source=source_name,
                    duration=duration,
                    events_found=len(tech_events),
                    events_inserted=inserted,
                    events_updated=updated,
                )
                logger.info("[SOURCE] %s → %d events → success (%.2fs)", source_name, len(tech_events), duration)

            except Exception as source_err:
                # Failure Isolation: Log error and update health, DO NOT break scheduler loop
                duration = time.time() - start_t
                logger.error("[SOURCE] %s ❌ error: %s", source_name, source_err, exc_info=True)
                self.source_db.update_source_health(
                    source_id,
                    success=False,
                    error_msg=str(source_err)
                )
                structured_logger.log_event(
                    event_tag="SCRAPE_FAILED",
                    message=f"Failed to scrape {source_name}: {str(source_err)}",
                    level=logging.ERROR,
                    source=source_name,
                    duration=duration,
                    errors=str(source_err)
                )

        # Dispatch notifications for newly discovered events
        notifs_dispatched = 0
        if all_new_events:
            logger.info("Found %d newly discovered events across all sources. Dispatching notifications...", len(all_new_events))
            try:
                notifs_dispatched = self.notification_service.dispatch_new_event_notifications(all_new_events)
            except Exception as notif_err:
                logger.error("Error dispatching notifications: %s", notif_err)
        else:
            logger.info("No newly discovered events in this cycle. Skipping notification dispatch.")

        summary = {
            "total_active_events": total_active_events_count,
            "new_inserted": total_new_count,
            "existing_updated": total_updated_count,
            "already_current": total_current_count,
            "notifications_dispatched": notifs_dispatched,
            "dynamic_sources_executed": len(enabled_sources),
        }
        return summary
