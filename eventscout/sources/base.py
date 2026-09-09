"""
Base abstractions for EventScout sources.
Defines the standard EventSource interface that every platform collector must implement.
"""

from abc import ABC, abstractmethod
from typing import List
from eventscout.models.event import Event


class EventSource(ABC):
    """
    Abstract Base Class for an event source.
    Every platform scraper (Meetup, Devpost, GitHub, Eventbrite, etc.) implements this contract.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """The identifier name of the event source (e.g. 'meetup', 'devpost')."""
        pass

    @abstractmethod
    def collect_events(self, max_pages: int = 10) -> List[Event]:
        """
        Collects, parses, and returns normalized Event objects from this platform.

        Args:
            max_pages: Maximum number of pages/batches to scrape.

        Returns:
            List of normalized Event instances.
        """
        pass
