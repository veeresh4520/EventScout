"""
Notification Service for EventScout.

Coordinates:
1. Relevance determination between user preferences and events.
2. In-app dashboard notification creation for newly discovered events.
3. Anti-spam / duplicate prevention using database unique constraints.
"""

import logging
from typing import Any, Dict, List, Optional

from eventscout.database.notification_db import NotificationDatabase
from eventscout.database.user_db import UserDatabase

logger = logging.getLogger("EventScoutNotificationService")


def is_event_relevant(user: Dict[str, Any], event: Dict[str, Any]) -> bool:
    """
    Determines if an event is relevant to a user based on their preferences.
    Rule-based deterministic matching:
    - If the user has configured interests, matches if event categories overlap with interests.
    - If the user has no interests configured, all technical events are considered relevant.
    """
    user_interests = [i.lower().strip() for i in user.get("interests", []) if i]
    if not user_interests:
        return True

    event_categories = [c.lower().strip() for c in event.get("categories", []) if c]
    event_title = event.get("title", "").lower()

    # Check category intersection
    for interest in user_interests:
        if any(interest in cat or cat in interest for cat in event_categories):
            return True
        if interest in event_title:
            return True

    return False


class NotificationService:
    """
    Service responsible for dispatching dashboard notifications to eligible users.
    """

    def __init__(
        self,
        user_db: Optional[UserDatabase] = None,
        notification_db: Optional[NotificationDatabase] = None,
    ):
        self.user_db = user_db or UserDatabase()
        self.notification_db = notification_db or NotificationDatabase()

    def dispatch_new_event_notifications(
        self,
        new_events: List[Dict[str, Any]],
    ) -> int:
        """
        Dispatches dashboard notifications for newly discovered events.
        Only notifies users who have dashboard notifications enabled.
        Evaluates relevance per user and inserts notifications idempotently.
        Returns the total number of notifications created.
        """
        if not new_events:
            return 0

        users = self.user_db.get_all_active_users()
        total_created = 0

        for user in users:
            user_id = str(user.get("id") or user.get("_id"))
            notif_prefs = user.get("notification_preferences", {})
            if not notif_prefs.get("dashboard_enabled", True):
                continue

            for event in new_events:
                if not is_event_relevant(user, event):
                    continue

                event_id = str(event.get("id") or event.get("_id"))
                event_title = event.get("title", "Technical Event")
                organizer = event.get("organizer", "Organizer")
                location = event.get("mode_location", "Online")
                event_url = event.get("event_url") or event.get("registration_url") or ""

                title = f"New Event: {event_title}"
                message = f"{organizer} announced '{event_title}' ({location})."

                created = self.notification_db.create_notification(
                    user_id=user_id,
                    event_id=event_id,
                    title=title,
                    message=message,
                    notification_type="new_event",
                    event_url=event_url,
                    metadata={
                        "organizer": organizer,
                        "location": location,
                        "date_time": str(event.get("date_time", "")),
                        "categories": event.get("categories", []),
                    },
                )
                if created:
                    total_created += 1

        logger.info(
            "Notification dispatch completed: %d new notifications created for %d newly discovered events across %d users.",
            total_created,
            len(new_events),
            len(users),
        )
        return total_created
