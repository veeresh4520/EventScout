"""
Meetup Event Source for EventScout.
Automates headless browser session, intercepts live GraphQL event responses,
and performs dynamic pagination via infinite-scroll emulation.
"""

import json
import logging
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from playwright.sync_api import sync_playwright, Response, Error as PlaywrightError

from eventscout.models.event import Event
from eventscout.sources.base import EventSource

logger = logging.getLogger("MeetupSource")

TARGET_URL = "https://www.meetup.com/find/?categoryId=546&source=EVENTS"
PAGE_TIMEOUT_SECONDS = 20.0


def _clean_str(value: Optional[Any]) -> Optional[str]:
    """Helper to trim whitespace and return clean string or None if empty."""
    if value is None:
        return None
    s = str(value).strip()
    return s if s else None


def parse_meetup_node(node: Dict[str, Any], index: int = 0) -> Optional[Event]:
    """
    Safely extract and normalize a single Meetup GraphQL event node into an Event instance.
    Returns None if required fields are missing or invalid.
    """
    if not isinstance(node, dict):
        logger.warning("[WARNING] Skipping invalid event at index %d: node is not a dictionary.", index)
        return None

    # 1. Title (Mandatory)
    title = _clean_str(node.get("title"))
    if not title:
        logger.warning("[WARNING] Skipping event at index %d: missing or empty 'title' field.", index)
        return None

    # 2. Event URL (Mandatory)
    event_url = _clean_str(node.get("eventUrl"))
    if not event_url:
        logger.warning("[WARNING] Skipping event at index %d ('%s'): missing or empty 'eventUrl' field.", index, title)
        return None

    # 3. Date Time (Mandatory, parsed to Python datetime)
    raw_date_time = node.get("dateTime")
    if not raw_date_time:
        logger.warning("[WARNING] Skipping event at index %d ('%s'): missing 'dateTime' field.", index, title)
        return None

    try:
        dt_str = str(raw_date_time).strip()
        if dt_str.endswith("Z"):
            dt_str = dt_str[:-1] + "+00:00"
        date_time_obj = datetime.fromisoformat(dt_str)
    except Exception as e:
        logger.warning(
            "[WARNING] Skipping event at index %d ('%s'): invalid 'dateTime' format '%s' (Error: %s).",
            index,
            title,
            raw_date_time,
            e,
        )
        return None

    # 4. Organizer / Group Name (Mandatory)
    group = node.get("group")
    organizer = None
    if isinstance(group, dict):
        organizer = _clean_str(group.get("name"))
    if not organizer:
        logger.warning("[WARNING] Skipping event at index %d ('%s'): missing organizer/group name.", index, title)
        return None

    # 5. Poster Image URL (featuredEventPhoto -> displayPhoto -> None)
    poster_image_url = None
    featured_photo = node.get("featuredEventPhoto")
    if isinstance(featured_photo, dict):
        poster_image_url = _clean_str(featured_photo.get("highResUrl"))

    if not poster_image_url:
        display_photo = node.get("displayPhoto")
        if isinstance(display_photo, dict):
            poster_image_url = _clean_str(display_photo.get("highResUrl"))

    # 6. Location & Attendance Mode
    event_type = _clean_str(node.get("eventType"))
    venue = node.get("venue") if isinstance(node.get("venue"), dict) else {}
    venue_city = _clean_str(venue.get("city"))
    venue_name = _clean_str(venue.get("name"))
    venue_country = _clean_str(venue.get("country"))

    if event_type == "ONLINE":
        mode_location = "Online"
    else:
        location_detail = venue_city or venue_name or "Location not specified"
        mode_location = f"Offline - {location_detail}"

    # 7. Price Settings
    fee_settings = node.get("feeSettings")
    if fee_settings is None:
        is_free = True
        price_amount: Optional[float] = None
        price_currency: Optional[str] = None
    else:
        is_free = False
        raw_amount = fee_settings.get("amount") if isinstance(fee_settings, dict) else None
        raw_currency = fee_settings.get("currency") if isinstance(fee_settings, dict) else None

        try:
            price_amount = float(raw_amount) if raw_amount is not None else None
        except (ValueError, TypeError):
            price_amount = None

        price_currency = _clean_str(raw_currency)

    # 8. Description & Source Event ID (Enriched fields)
    description = _clean_str(node.get("description"))
    source_event_id = _clean_str(node.get("id"))

    return Event(
        title=title,
        event_url=event_url,
        date_time=date_time_obj,
        organizer=organizer,
        source="meetup",
        mode_location=mode_location,
        city=venue_city,
        country=venue_country,
        poster_image_url=poster_image_url,
        description=description,
        is_free=is_free,
        price_amount=price_amount,
        price_currency=price_currency,
        source_event_id=source_event_id,
        registration_url=event_url,
        is_technical=True,
    )


class MeetupSource(EventSource):
    """
    Scrapes events from Meetup using Playwright network interception and dynamic scroll pagination.
    """

    def __init__(self, target_url: str = TARGET_URL):
        self.target_url = target_url
        self.discovered_raw_count = 0
        self.malformed_count = 0

    @property
    def name(self) -> str:
        return "meetup"

    def collect_events(self, max_pages: int = 5) -> List[Event]:
        """
        Launches Playwright, intercepts multiple GraphQL batches via scrolling,
        and parses nodes into Event objects.
        """
        raw_nodes: List[Dict[str, Any]] = []
        seen_node_ids = set()
        has_next_page = True

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(
                    headless=True,
                    args=["--no-sandbox", "--disable-dev-shm-usage"],
                )
                context = browser.new_context(
                    user_agent=(
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/124.0.0.0 Safari/537.36"
                    ),
                    viewport={"width": 1280, "height": 800},
                )
                page = context.new_page()

                def handle_response(response: Response) -> None:
                    nonlocal has_next_page
                    if "gql2" in response.url and response.status == 200:
                        try:
                            body_text = response.text()
                            if "edges" in body_text and "totalCount" in body_text:
                                payload = json.loads(body_text)
                                result = payload.get("data", {}).get("result", {})
                                page_info = result.get("pageInfo", {})
                                has_next_page = page_info.get("hasNextPage", False)

                                edges = result.get("edges", [])
                                for edge in edges:
                                    node = edge.get("node") if isinstance(edge, dict) else None
                                    if node and isinstance(node, dict):
                                        node_id = node.get("id") or node.get("eventUrl") or len(raw_nodes)
                                        if node_id not in seen_node_ids:
                                            seen_node_ids.add(node_id)
                                            raw_nodes.append(node)
                        except Exception:
                            pass

                page.on("response", handle_response)

                # 1. Initial navigation
                try:
                    page.goto(self.target_url, wait_until="domcontentloaded", timeout=PAGE_TIMEOUT_SECONDS * 1000)
                except PlaywrightError as e:
                    logger.warning("Navigation notice: %s", e)

                # Wait for initial GraphQL response
                start_wait = time.time()
                while time.time() - start_wait < 6.0 and len(raw_nodes) == 0:
                    page.wait_for_timeout(300)

                # 2. Dynamic Pagination: Scroll down to trigger subsequent GraphQL requests
                scroll_count = 0
                while scroll_count < max_pages and has_next_page:
                    prev_count = len(raw_nodes)
                    # Scroll to bottom of window
                    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    scroll_count += 1

                    # Wait for network response to register
                    wait_for_new_nodes_start = time.time()
                    while time.time() - wait_for_new_nodes_start < 3.0:
                        page.wait_for_timeout(250)
                        if len(raw_nodes) > prev_count:
                            break

                    # If no new nodes arrived after scrolling and waiting, exit loop
                    if len(raw_nodes) == prev_count:
                        break

                browser.close()

        except Exception as e:
            logger.error("[ERROR] Failed during Playwright browser automation: %s", e)
            return []

        self.discovered_raw_count = len(raw_nodes)

        # 3. Parse and validate nodes
        parsed_events: List[Event] = []
        for idx, node in enumerate(raw_nodes):
            event = parse_meetup_node(node, idx)
            if event is not None:
                parsed_events.append(event)
            else:
                self.malformed_count += 1

        return parsed_events
