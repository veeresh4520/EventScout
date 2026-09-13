"""
Collector Factory for EventScout.
Selects and instantiates the appropriate generic collector based on source configuration.
"""
import logging
from typing import Any, Dict

from eventscout.collectors.base_collector import BaseCollector
from eventscout.collectors.api_collector import ApiCollector
from eventscout.collectors.graphql_collector import GraphQLCollector
from eventscout.collectors.html_collector import HtmlCollector
from eventscout.collectors.playwright_collector import PlaywrightCollector
from eventscout.collectors.meetup_adapter import MeetupCollectorAdapter

logger = logging.getLogger("CollectorFactory")


def get_collector_for_source(source: Dict[str, Any]) -> BaseCollector:
    """
    Instantiates the appropriate collector for the given source document.
    """
    name = (source.get("name") or "").strip().lower()
    strategy = (source.get("collection_strategy") or source.get("strategy") or "").strip().lower()
    config = source.get("configuration", {})

    # Check for Meetup adapter
    if name == "meetup" or config.get("adapter") == "meetup_graphql_interceptor":
        return MeetupCollectorAdapter(source)

    # REST API
    if strategy in ("api_json", "api", "rest_api"):
        return ApiCollector(source)

    # GraphQL
    if strategy in ("graphql", "graphql_api"):
        return GraphQLCollector(source)

    # Static HTML / JSON-LD
    if strategy in ("html", "static_html", "json_ld"):
        return HtmlCollector(source)

    # Default to Playwright browser scraper
    return PlaywrightCollector(source)
