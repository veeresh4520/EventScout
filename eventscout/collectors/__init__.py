"""
EventScout Generic Collectors Package.
"""
from eventscout.collectors.base_collector import BaseCollector
from eventscout.collectors.api_collector import ApiCollector
from eventscout.collectors.html_collector import HtmlCollector
from eventscout.collectors.graphql_collector import GraphQLCollector
from eventscout.collectors.playwright_collector import PlaywrightCollector
from eventscout.collectors.meetup_adapter import MeetupCollectorAdapter
from eventscout.collectors.factory import get_collector_for_source

__all__ = [
    "BaseCollector",
    "ApiCollector",
    "HtmlCollector",
    "GraphQLCollector",
    "PlaywrightCollector",
    "MeetupCollectorAdapter",
    "get_collector_for_source",
]
