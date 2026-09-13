"""
Base Collector Interface.
All dynamic scraper implementations (Playwright HTML, API JSON, GraphQL, Static HTML) implement this class.
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List


class BaseCollector(ABC):
    """
    Abstract collector initialized with a source registry configuration.
    Produces raw extracted event dicts for subsequent normalization.
    """

    def __init__(self, source_config: Dict[str, Any]):
        self.source_config = source_config
        self.source_id = str(source_config.get("_id") or source_config.get("id") or "")
        self.source_name = source_config.get("name") or "unknown_source"
        self.source_url = (
            source_config.get("event_list_url")
            or source_config.get("url")
            or source_config.get("base_url")
            or ""
        )
        self.config = source_config.get("configuration", {})

    @property
    def target_url(self) -> str:
        """Resolves target URL from configuration or source level URLs."""
        return (
            self.config.get("target_url")
            or self.config.get("endpoint")
            or self.source_url
            or self.source_config.get("event_list_url")
            or self.source_config.get("base_url")
            or ""
        )

    @abstractmethod
    def collect(self, max_pages: int = 3) -> List[Dict[str, Any]]:
        """
        Executes extraction according to configuration.
        Returns a list of raw event dictionaries.
        """
        pass

    def test(self) -> List[Dict[str, Any]]:
        """
        Executes a 1-page sample extraction test.
        """
        return self.collect(max_pages=1)
