"""
Static HTML and JSON-LD Collector for EventScout.
Extracts event data from static web pages without headless browser overhead,
including support for Schema.org Event JSON-LD structured data.
"""
import json
import logging
import re
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin
import httpx
from bs4 import BeautifulSoup

from eventscout.collectors.base_collector import BaseCollector

logger = logging.getLogger("HtmlCollector")


class HtmlCollector(BaseCollector):
    """
    Lightweight HTTP collector using httpx and BeautifulSoup.
    Ideal for static websites or pages featuring Schema.org Event JSON-LD metadata.
    """

    def collect(self, max_pages: int = 3) -> List[Dict[str, Any]]:
        target_url = self.target_url
        if not target_url:
            logger.error("No target URL specified for source %s", self.source_name)
            return []

        container_selector = self.config.get("container_selector")
        field_selectors = self.config.get("fields", {})
        headers = self.config.get("headers", {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        })

        raw_events: List[Dict[str, Any]] = []

        try:
            with httpx.Client(timeout=30.0, follow_redirects=True, headers=headers) as client:
                res = client.get(target_url)
                res.raise_for_status()
                html_text = res.text

            soup = BeautifulSoup(html_text, "html.parser")

            # 1. Check for JSON-LD structured data
            json_ld_scripts = soup.find_all("script", type="application/ld+json")
            for script in json_ld_scripts:
                try:
                    if not script.string:
                        continue
                    data = json.loads(script.string)
                    items = data if isinstance(data, list) else [data]
                    for item in items:
                        if isinstance(item, dict):
                            # Check @graph or direct @type Event
                            graph = item.get("@graph")
                            candidates = graph if isinstance(graph, list) else [item]
                            for cand in candidates:
                                type_val = cand.get("@type", "")
                                if isinstance(type_val, list):
                                    is_event = any("Event" in str(t) for t in type_val)
                                else:
                                    is_event = "Event" in str(type_val)

                                if is_event and cand.get("name"):
                                    organizer_val = cand.get("organizer", {})
                                    org_name = organizer_val.get("name") if isinstance(organizer_val, dict) else str(organizer_val)
                                    location_val = cand.get("location", {})
                                    loc_str = location_val.get("name") or location_val.get("address") if isinstance(location_val, dict) else str(location_val)

                                    raw_events.append({
                                        "title": cand.get("name"),
                                        "event_url": cand.get("url") or target_url,
                                        "date_time": cand.get("startDate"),
                                        "description": cand.get("description"),
                                        "organizer": org_name or self.source_name,
                                        "mode_location": loc_str or "Online",
                                        "poster_image_url": cand.get("image"),
                                        "_source_strategy": "JSON-LD",
                                    })
                except Exception as e:
                    logger.debug("Failed parsing JSON-LD script tag: %s", e)

            if raw_events:
                logger.info("[%s] Extracted %d events from JSON-LD metadata.", self.source_name, len(raw_events))
                return raw_events

            # 2. CSS Selector parsing if container_selector is configured
            if container_selector:
                containers = soup.select(container_selector)
                logger.info("[%s] Found %d matching containers with selector '%s'", self.source_name, len(containers), container_selector)

                for idx, container in enumerate(containers):
                    event_data: Dict[str, Any] = {"_raw_index": idx}

                    for field_name, rule in field_selectors.items():
                        if isinstance(rule, str):
                            rule = {"selector": rule, "type": "text"}

                        selector = rule.get("selector")
                        extract_type = rule.get("type", "text")
                        attr_name = rule.get("attribute", "href")
                        default_val = rule.get("default")

                        val = default_val
                        if selector:
                            el = container.select_one(selector)
                            if el:
                                if extract_type == "text":
                                    val = el.get_text(strip=True)
                                elif extract_type == "attribute":
                                    val = el.get(attr_name)
                                    if val and attr_name in ("href", "src"):
                                        val = urljoin(target_url, val)
                                elif extract_type == "html":
                                    val = str(el)

                        if val is not None:
                            event_data[field_name] = val

                    if event_data.get("title"):
                        if not event_data.get("event_url"):
                            event_data["event_url"] = target_url
                        raw_events.append(event_data)

            logger.info("[%s] Extracted %d events via HTML parsing.", self.source_name, len(raw_events))
            return raw_events

        except Exception as e:
            logger.error("[%s] Error during HTML collection: %s", self.source_name, e)
            raise e
