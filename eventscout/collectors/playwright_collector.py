"""
Playwright Generic Collector for EventScout.
Extracts event data from rendered DOM using dynamic CSS/XPath selectors and pagination,
with resilient fallbacks for single-page applications and varying website structures.
"""
import logging
import time
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

from eventscout.collectors.base_collector import BaseCollector

logger = logging.getLogger("PlaywrightCollector")

FALLBACK_CONTAINER_SELECTORS = [
    "a[itemtype*='Event']",
    "[itemtype*='Event']",
    "a.item[href*='/hackathons/']",
    "a[href*='/hackathons/']",
    "a[href*='/competitions/']",
    "a[href*='/events/details/']",
    "a[href*='devpost.com']",
    "div[class*='HackathonCard']",
    "div[class*='hackathon-card']",
    "div[class*='hackathon_card']",
    "div[class*='opportunity-card']",
    "div[class*='event-card']",
    "div[class*='eventCard']",
    "section.event-card-details",
    "div[class*='challenge-card']",
    "div.hackathon-tile",
    "article",
]


class PlaywrightCollector(BaseCollector):
    """
    DOM-based collector that runs headless Playwright and executes selectors
    defined in the source registry configuration.
    """

    def collect(self, max_pages: int = 3) -> List[Dict[str, Any]]:
        target_url = self.target_url
        if not target_url:
            logger.error("No target_url specified for source %s", self.source_name)
            return []

        container_selector = self.config.get("container_selector")
        field_selectors = self.config.get("fields", {})
        pagination_config = self.config.get("pagination", {})
        wait_selector = self.config.get("wait_selector", container_selector)

        raw_events: List[Dict[str, Any]] = []

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                    viewport={"width": 1280, "height": 800},
                )
                page = context.new_page()

                logger.info("[%s] Navigating to %s", self.source_name, target_url)
                page.goto(target_url, wait_until="domcontentloaded", timeout=45000)

                # Wait for main elements with reasonable timeout
                if wait_selector:
                    try:
                        page.wait_for_selector(wait_selector, timeout=6000)
                    except PlaywrightTimeoutError:
                        logger.debug("[%s] Settle wait on '%s' ended without match.", self.source_name, wait_selector)

                # Settle time for dynamic JavaScript hydration
                time.sleep(2.5)

                pag_type = pagination_config.get("type", "scroll")
                pages_scraped = 0

                while pages_scraped < max_pages:
                    pages_scraped += 1

                    # Extract currently visible cards
                    cards = []
                    if container_selector:
                        cards = page.query_selector_all(container_selector)

                    # Fallback container matching if primary selector returned 0 cards
                    if not cards:
                        for fb_sel in FALLBACK_CONTAINER_SELECTORS:
                            candidate_cards = page.query_selector_all(fb_sel)
                            if candidate_cards and len(candidate_cards) >= 2:
                                logger.info("[%s] Primary selector returned 0; fallback selector '%s' found %d cards.",
                                            self.source_name, fb_sel, len(candidate_cards))
                                cards = candidate_cards
                                break

                    logger.info("[%s] Page %d: Found %d item containers", self.source_name, pages_scraped, len(cards))

                    for idx, card in enumerate(cards):
                        event_data: Dict[str, Any] = {"_raw_index": idx}

                        for field_name, rule in field_selectors.items():
                            if isinstance(rule, str):
                                rule = {"selector": rule, "type": "text"}

                            selector = rule.get("selector")
                            extract_type = rule.get("type", "text")
                            attr_name = rule.get("attribute", "href")
                            default_val = rule.get("default")

                            val = None
                            el = None

                            if selector in ("self", ".", "", "root"):
                                el = card
                            elif selector:
                                try:
                                    el = card.query_selector(selector)
                                except Exception:
                                    el = None

                            if el:
                                try:
                                    if extract_type == "text":
                                        val = el.inner_text()
                                    elif extract_type == "attribute":
                                        val = el.get_attribute(attr_name)
                                        if val and attr_name in ("href", "src"):
                                            val = urljoin(page.url, val)
                                    elif extract_type == "html":
                                        val = el.inner_html()
                                except Exception as ex:
                                    logger.debug("[%s] Error extracting field %s: %s", self.source_name, field_name, ex)

                            # Fallbacks for missing required fields
                            if not val:
                                if field_name in ("event_url", "registration_url") or attr_name == "href":
                                    card_href = card.get_attribute("href")
                                    if card_href:
                                        val = urljoin(page.url, card_href)
                                    else:
                                        a_el = card.query_selector("a[href]")
                                        if a_el and a_el.get_attribute("href"):
                                            val = urljoin(page.url, a_el.get_attribute("href"))

                                elif field_name == "title":
                                    # Try heading or bold element inside card
                                    h_candidates = card.query_selector_all("h1, h2, h3, h4, h5, [class*='title'], [class*='event-name'], [class*='name'], [class*='heading'], strong")
                                    for h_el in h_candidates:
                                        t_text = (h_el.inner_text() or "").strip()
                                        if t_text and not t_text.lower().startswith("http"):
                                            val = t_text
                                            break
                                    if not val:
                                        img_el = card.query_selector("img[alt]")
                                        if img_el and img_el.get_attribute("alt") and not img_el.get_attribute("alt").lower().startswith("http"):
                                            val = img_el.get_attribute("alt").strip()
                                    if not val:
                                        # Fallback to lines of card text
                                        text_lines = [l.strip() for l in (card.inner_text() or "").split("\n") if l.strip()]
                                        for line in text_lines:
                                            if len(line) > 2 and not line.lower().startswith("http") and line.lower() not in ("in-person", "online", "hybrid", "free", "view", "register"):
                                                val = line
                                                break

                                elif field_name in ("poster_image_url", "image"):
                                    all_imgs = card.query_selector_all("img[src]")
                                    for img_el in all_imgs:
                                        src = img_el.get_attribute("src") or ""
                                        src_lower = src.lower()
                                        # Skip avatars, profile photos, attendee icons
                                        if any(k in src_lower for k in ("avatar", "/users/", "/user/", "profile", "attendee", "gravatar", "author", "icon")):
                                            continue
                                        val = urljoin(page.url, src)
                                        break

                                elif field_name in ("date_time", "date"):
                                    d_candidates = card.query_selector_all("time, [class*='date'], [class*='deadline'], [class*='time'], p, span")
                                    for d_el in d_candidates:
                                        d_text = (d_el.inner_text() or "").strip()
                                        if d_text and not d_text.lower().startswith("http") and len(d_text) < 100:
                                            # Check if text contains typical date indicators (months, numbers, 'left')
                                            val = d_text
                                            break

                            if val is None:
                                val = default_val

                            if isinstance(val, str):
                                val = val.strip()

                            event_data[field_name] = val

                        # If title still accidentally looks like a URL, recover from card text
                        if event_data.get("title") and str(event_data.get("title")).lower().startswith("http"):
                            text_lines = [l.strip() for l in (card.inner_text() or "").split("\n") if l.strip()]
                            for line in text_lines:
                                if len(line) > 2 and not line.lower().startswith("http") and line.lower() not in ("in-person", "online", "hybrid", "free", "view", "register"):
                                    event_data["title"] = line
                                    break

                        # If date_time looks like a URL, clear it so normalizer can assign default
                        if event_data.get("date_time") and str(event_data.get("date_time")).lower().startswith("http"):
                            event_data["date_time"] = None

                        # Ensure valid event_url exists
                        if not event_data.get("event_url"):
                            card_href = card.get_attribute("href")
                            if card_href:
                                event_data["event_url"] = urljoin(page.url, card_href)
                            else:
                                a_el = card.query_selector("a[href]")
                                if a_el and a_el.get_attribute("href"):
                                    event_data["event_url"] = urljoin(page.url, a_el.get_attribute("href"))

                        # Retain if title exists
                        if event_data.get("title") and len(str(event_data.get("title"))) > 1:
                            raw_events.append(event_data)

                    # Check pagination
                    if pages_scraped >= max_pages:
                        break

                    if pag_type == "scroll":
                        prev_height = page.evaluate("document.body.scrollHeight")
                        page.evaluate("window.scrollTo(0, document.body.scrollHeight);")
                        time.sleep(2.5)
                        new_height = page.evaluate("document.body.scrollHeight")
                        if new_height == prev_height:
                            break
                    elif pag_type == "next_button":
                        next_btn_selector = pagination_config.get("selector")
                        if not next_btn_selector:
                            break
                        next_btn = page.query_selector(next_btn_selector)
                        if next_btn and next_btn.is_visible() and next_btn.is_enabled():
                            next_btn.click()
                            time.sleep(3)
                        else:
                            break
                    else:
                        break

                browser.close()

        except Exception as e:
            logger.error("[%s] Error running PlaywrightCollector: %s", self.source_name, e, exc_info=True)
            raise e

        logger.info("[%s] Successfully extracted %d raw events.", self.source_name, len(raw_events))
        return raw_events
