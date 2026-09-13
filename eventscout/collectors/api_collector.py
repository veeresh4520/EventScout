"""
API/JSON Collector for EventScout.
Extracts event data directly from public JSON REST or GraphQL endpoints.
"""
import logging
from typing import Any, Dict, List, Optional
import httpx

from eventscout.collectors.base_collector import BaseCollector

logger = logging.getLogger("ApiCollector")


def _get_nested_val(data: Any, path: str) -> Any:
    """Retrieve nested value using dot notation, e.g. 'data.events'."""
    if not path:
        return data
    parts = path.split(".")
    curr = data
    for part in parts:
        if isinstance(curr, dict):
            curr = curr.get(part)
        elif isinstance(curr, list) and part.isdigit():
            idx = int(part)
            if 0 <= idx < len(curr):
                curr = curr[idx]
            else:
                return None
        else:
            return None
    return curr


class ApiCollector(BaseCollector):
    """
    HTTP API collector that queries REST or GraphQL endpoints directly.
    """

    def collect(self, max_pages: int = 3) -> List[Dict[str, Any]]:
        endpoint = self.config.get("endpoint") or self.source_url
        method = self.config.get("method", "GET").upper()
        headers = self.config.get("headers", {})
        params = self.config.get("params", {})
        payload = self.config.get("payload")
        items_path = self.config.get("items_path", "")
        field_mapping = self.config.get("fields", {})
        pagination = self.config.get("pagination", {})

        raw_events: List[Dict[str, Any]] = []

        page_param = pagination.get("page_param")
        page_start = pagination.get("start_page", 1)
        page_size_param = pagination.get("size_param")
        page_size = pagination.get("page_size", 20)

        curr_page = page_start
        pages_fetched = 0

        with httpx.Client(timeout=30.0, follow_redirects=True) as client:
            while pages_fetched < max_pages:
                pages_fetched += 1
                curr_params = dict(params)
                curr_payload = dict(payload) if isinstance(payload, dict) else payload

                if page_param:
                    if method == "GET":
                        curr_params[page_param] = curr_page
                        if page_size_param:
                            curr_params[page_size_param] = page_size
                    elif isinstance(curr_payload, dict):
                        curr_payload[page_param] = curr_page
                        if page_size_param:
                            curr_payload[page_size_param] = page_size

                try:
                    logger.info("[%s] Fetching API endpoint %s (page=%s)", self.source_name, endpoint, curr_page)
                    if method == "POST":
                        res = client.post(endpoint, headers=headers, params=curr_params, json=curr_payload)
                    else:
                        res = client.get(endpoint, headers=headers, params=curr_params)

                    res.raise_for_status()
                    data = res.json()
                except Exception as e:
                    logger.error("[%s] Error fetching API endpoint: %s", self.source_name, e)
                    break

                # Extract items
                items = _get_nested_val(data, items_path) if items_path else data
                if not isinstance(items, list):
                    logger.warning("[%s] Extracted items at path '%s' is not a list. Type: %s", 
                                   self.source_name, items_path, type(items))
                    break

                if not items:
                    logger.info("[%s] No items returned on page %d, ending fetch.", self.source_name, curr_page)
                    break

                for idx, item in enumerate(items):
                    if not isinstance(item, dict):
                        continue

                    event_data: Dict[str, Any] = {"_raw_index": idx}
                    for target_field, src_path in field_mapping.items():
                        if isinstance(src_path, str):
                            val = _get_nested_val(item, src_path)
                        elif isinstance(src_path, dict):
                            key_path = src_path.get("path")
                            default_val = src_path.get("default")
                            val = _get_nested_val(item, key_path) if key_path else default_val
                        else:
                            val = None

                        if val is not None:
                            event_data[target_field] = val

                    if event_data.get("title"):
                        raw_events.append(event_data)

                curr_page += 1

        logger.info("[%s] Successfully extracted %d raw events via API.", self.source_name, len(raw_events))
        return raw_events
