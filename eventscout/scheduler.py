"""
EventScout Background Scheduler.

Runs periodic automated jobs:
1. Scraper Job: Periodically runs Meetup scraper -> MongoDB upsert -> notification dispatch.
2. Daily Digest Job: Runs once a day at configured hour/minute -> sends daily email digests.

Configuration (via .env):
- SCRAPE_INTERVAL_HOURS (default: 6)
- SCRAPE_INTERVAL_MINUTES (optional override for development)
- DAILY_DIGEST_HOUR (default: 8)
- DAILY_DIGEST_MINUTE (default: 0)

CLI options:
- python -m eventscout.scheduler --run-now       # Trigger immediate scrape & notification run
- python -m eventscout.scheduler --digest-now    # Trigger immediate daily email digest run
- python -m eventscout.scheduler                 # Run background scheduler daemon
"""

import argparse
import logging
import os
import sys
import time
from datetime import datetime, timezone
from typing import Optional
from dotenv import load_dotenv

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from eventscout.services.email_service import EmailService
from eventscout.services.scraper_service import ScraperService

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("EventScoutScheduler")


class EventScoutScheduler:
    """
    Background scheduler orchestrating periodic scraping and daily digest jobs.
    """

    def __init__(
        self,
        scraper_service: Optional = None,
        email_service: Optional = None,
    ):
        self.scraper_service = scraper_service or ScraperService()
        self.email_service = email_service or EmailService()
        self.scheduler = BackgroundScheduler()

        # Configurable intervals
        self.scrape_hours = int(os.getenv("SCRAPE_INTERVAL_HOURS", "6"))
        self.scrape_minutes = int(os.getenv("SCRAPE_INTERVAL_MINUTES", "0"))

        self.digest_hour = int(os.getenv("DAILY_DIGEST_HOUR", "8"))
        self.digest_minute = int(os.getenv("DAILY_DIGEST_MINUTE", "0"))

    def run_scraper_job(self) -> None:
        """Scheduled task: executes dynamic multi-source scraper pipeline with error resilience."""
        logger.info("=== [SCHEDULER] Triggering scheduled multi-source scraper job ===")
        try:
            summary = self.scraper_service.run_pipeline()
            logger.info("=== [SCHEDULER] Multi-source scraper job completed: %s ===", summary)
        except Exception as exc:
            # Scheduler must not crash on scraper failure
            logger.error("[SCHEDULER ERROR] Scraper job encountered an error: %s", exc, exc_info=True)

    def run_daily_digest_job(self) -> None:
        """Scheduled task: executes daily email digest dispatch."""
        logger.info("=== [SCHEDULER] Triggering scheduled daily email digest job ===")
        try:
            sent_count = self.email_service.send_daily_digests()
            logger.info("=== [SCHEDULER] Daily digest job completed. Sent %d digest(s). ===", sent_count)
        except Exception as exc:
            logger.error("[SCHEDULER ERROR] Daily digest job encountered an error: %s", exc, exc_info=True)

    def start(self, blocking: bool = True) -> None:
        """Configures schedules and starts the background scheduler."""
        logger.info("Starting EventScout Automation Scheduler...")

        # 1. Scraper Interval
        if self.scrape_minutes > 0:
            trigger = IntervalTrigger(minutes=self.scrape_minutes)
            logger.info("Configured Scraper job: every %d minute(s).", self.scrape_minutes)
        else:
            trigger = IntervalTrigger(hours=self.scrape_hours)
            logger.info("Configured Scraper job: every %d hour(s).", self.scrape_hours)

        self.scheduler.add_job(
            self.run_scraper_job,
            trigger=trigger,
            id="multi_source_scraper_job",
            name="Dynamic Multi-Source Scraper Job",
            replace_existing=True,
        )

        # 2. Daily Digest Cron
        digest_trigger = CronTrigger(
            hour=self.digest_hour,
            minute=self.digest_minute,
            timezone="UTC",
        )
        logger.info(
            "Configured Daily Email Digest job: daily at %02d:%02d UTC.",
            self.digest_hour,
            self.digest_minute,
        )

        self.scheduler.add_job(
            self.run_daily_digest_job,
            trigger=digest_trigger,
            id="daily_email_digest_job",
            name="Daily Email Digest Job",
            replace_existing=True,
        )

        self.scheduler.start()
        logger.info("Scheduler successfully started. All background jobs active.")

        if blocking:
            try:
                while True:
                    time.sleep(1)
            except (KeyboardInterrupt, SystemExit):
                logger.info("Stopping EventScout Scheduler...")
                self.scheduler.shutdown(wait=False)
                logger.info("Scheduler stopped cleanly.")

    def stop(self) -> None:
        """Stops the scheduler."""
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)


def main():
    parser = argparse.ArgumentParser(description="EventScout Background Automation Scheduler")
    parser.add_argument("--run-now", action="store_true", help="Execute scraper pipeline immediately and exit")
    parser.add_argument("--digest-now", action="store_true", help="Execute daily email digest dispatch immediately and exit")
    parser.add_argument("--interval-minutes", type=int, default=None, help="Override scraper interval in minutes")
    args = parser.parse_args()

    scheduler = EventScoutScheduler()

    if args.interval_minutes:
        scheduler.scrape_minutes = args.interval_minutes

    if args.run_now:
        logger.info("Manual execution requested: running scraper pipeline now...")
        scheduler.run_scraper_job()
        sys.exit(0)

    if args.digest_now:
        logger.info("Manual execution requested: sending daily email digests now...")
        scheduler.run_daily_digest_job()
        sys.exit(0)

    # Otherwise run continuous scheduler daemon
    scheduler.start(blocking=True)


if __name__ == "__main__":
    main()
