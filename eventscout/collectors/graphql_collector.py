"""
GraphQL Collector for EventScout.
Extracts event data by querying GraphQL HTTP endpoints directly.
"""
import logging
from typing import Any, Dict, List, Optional
import httpx

from eventscout.collectors.base_collector import BaseCollector
from eventscout.collectors.api_collector import _get_nested_val

logger = logging.getLogger("GraphQLCollector")


class GraphQLCollector(BaseCollector):
    """
    Direct GraphQL collector that queries endpoints via POST requests with GraphQL payloads.
    """

    def collect(self, max_pages: int = 3) -> List[Dict[str, Any]]:
        endpoint = self.config.get("endpoint") or self.target_url
        query = self.config.get("query", "")
        variables = self.config.get("variables", {})
        headers = self.config.get("headers", {
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        })
        items_path = self.config.get("items_path", "data")
        field_mapping = self.config.get("fields", {})

        if not endpoint or not query:
            logger.error("Missing GraphQL endpoint or query for source %s", self.source_name)
            return []

        raw_events: List[Dict[str, Any]] = []

        try:
            with httpx.Client(timeout=30.0, follow_redirects=True) as client:
                res = client.post(
                    endpoint,
                    headers=headers,
                    json={"query": query, "variables": variables},
                )
                res.raise_for_status()
                data = res.json()

            items = _get_nested_val(data, items_path) if items_path else data
            if not isinstance(items, list):
                logger.warning("[%s] Extracted items at path '%s' is not a list.", self.source_name, items_path)
                return []

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

            logger.info("[%s] Extracted %d raw events via GraphQL.", self.source_name, len(raw_events))
            return raw_events

        except Exception as e:
            logger.error("[%s] Error during GraphQL collection: %s", self.source_name, e)
            raise e
