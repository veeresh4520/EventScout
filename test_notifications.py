"""
Unit and Integration tests for EventScout Automation and Notification Pipeline:
1. Scheduler execution and resilience on scraper failure.
2. New event detection vs existing event suppression.
3. Dashboard notification creation, read tracking, and idempotency.
4. Daily email digest generation and duplicate prevention on same calendar date.
5. Notification preference toggles (dashboard, browser, email).
6. User isolation (User A cannot access or mutate User B's notifications).
"""

import unittest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
from bson import ObjectId

from fastapi.testclient import TestClient
from api.main import app
from api.auth import create_access_token
from eventscout.database.notification_db import NotificationDatabase
from eventscout.services.notification_service import NotificationService, is_event_relevant
from eventscout.services.email_service import EmailService, build_daily_digest
from eventscout.services.scraper_service import ScraperService
from eventscout.scheduler import EventScoutScheduler


class TestAutomationAndNotifications(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.user_a_id = str(ObjectId())
        self.user_b_id = str(ObjectId())
        self.token_a = create_access_token({"sub": self.user_a_id, "email": "alice@example.com", "username": "alice"})
        self.token_b = create_access_token({"sub": self.user_b_id, "email": "bob@example.com", "username": "bob"})

        self.sample_event_id = str(ObjectId())
        self.sample_event = {
            "id": self.sample_event_id,
            "_id": self.sample_event_id,
            "title": "Autonomous AI Agents Workshop",
            "organizer": "AI Builders",
            "date_time": "2026-10-15T18:00:00+00:00",
            "mode_location": "Online",
            "event_url": "https://example.com/ai-agents",
            "categories": ["AI / ML", "Python"],
            "is_free": True,
        }

    # ------------------------------------------------------------------
    # 1. Relevance Determination
    # ------------------------------------------------------------------
    def test_relevance_matching(self):
        """User with matching interests matches relevant event; user with empty interests matches all."""
        user_ai = {"interests": ["AI / ML", "Data Science"]}
        user_web = {"interests": ["Web Development", "React"]}
        user_generic = {"interests": []}

        # Event is AI / ML
        self.assertTrue(is_event_relevant(user_ai, self.sample_event))
        self.assertFalse(is_event_relevant(user_web, self.sample_event))
        # Empty interests matches all technical events
        self.assertTrue(is_event_relevant(user_generic, self.sample_event))

    # ------------------------------------------------------------------
    # 2. Notification Dispatch & Idempotency
    # ------------------------------------------------------------------
    def test_notification_dispatch_and_duplicate_suppression(self):
        """NotificationService creates notifications and suppresses duplicates."""
        mock_user_db = MagicMock()
        mock_notif_db = MagicMock()

        mock_user_db.get_all_active_users.return_value = [
            {
                "id": self.user_a_id,
                "email": "alice@example.com",
                "interests": ["AI / ML"],
                "notification_preferences": {"dashboard_enabled": True},
            },
            {
                "id": self.user_b_id,
                "email": "bob@example.com",
                "interests": ["Cloud"],
                "notification_preferences": {"dashboard_enabled": False},  # Disabled
            },
        ]

        # First call succeeds
        mock_notif_db.create_notification.return_value = {"id": "notif123"}
        service = NotificationService(user_db=mock_user_db, notification_db=mock_notif_db)

        count = service.dispatch_new_event_notifications([self.sample_event])
        self.assertEqual(count, 1)  # Only User A receives it (User B has dashboard_enabled=False)

        # Second run: duplicate returns None from DB
        mock_notif_db.create_notification.return_value = None
        count_duplicate = service.dispatch_new_event_notifications([self.sample_event])
        self.assertEqual(count_duplicate, 0)

    # ------------------------------------------------------------------
    # 3. Notification API & User Isolation
    # ------------------------------------------------------------------
    @patch("api.routers.notifications.NotificationDatabase")
    def test_get_notifications_and_user_isolation(self, mock_db_cls):
        """User A receives only User A's notifications."""
        mock_db = MagicMock()
        mock_db_cls.return_value = mock_db

        mock_db.get_user_notifications.return_value = [
            {
                "id": "notif_1",
                "user_id": self.user_a_id,
                "event_id": self.sample_event_id,
                "type": "new_event",
                "title": "New Event: Autonomous AI Agents Workshop",
                "read": False,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
        ]
        mock_db.get_unread_count.return_value = 1

        res = self.client.get("/notifications", headers={"Authorization": f"Bearer {self.token_a}"})
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(len(data["notifications"]), 1)
        self.assertEqual(data["unread_count"], 1)
        mock_db.get_user_notifications.assert_called_with(user_id=self.user_a_id, limit=30)

    @patch("api.routers.notifications.NotificationDatabase")
    def test_mark_notification_read(self, mock_db_cls):
        """Marking a notification as read invokes mark_as_read with user_id."""
        mock_db = MagicMock()
        mock_db_cls.return_value = mock_db
        mock_db.mark_as_read.return_value = True

        res = self.client.post(
            "/notifications/notif_1/read",
            headers={"Authorization": f"Bearer {self.token_a}"},
        )
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.json()["read"])
        mock_db.mark_as_read.assert_called_with(user_id=self.user_a_id, notification_id="notif_1")

    @patch("api.routers.notifications.NotificationDatabase")
    def test_mark_all_read(self, mock_db_cls):
        """Mark all read marks all notifications as read for current user."""
        mock_db = MagicMock()
        mock_db_cls.return_value = mock_db
        mock_db.mark_all_read.return_value = 3

        res = self.client.post(
            "/notifications/read-all",
            headers={"Authorization": f"Bearer {self.token_a}"},
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["marked_read"], 3)
        mock_db.mark_all_read.assert_called_with(user_id=self.user_a_id)

    # ------------------------------------------------------------------
    # 4. Daily Email Digest & Idempotency
    # ------------------------------------------------------------------
    def test_build_daily_digest_content(self):
        """Daily digest builder includes event details, host, date, and link."""
        user = {"username": "sk", "email": "sk@example.com"}
        subject, text, html = build_daily_digest(user, [self.sample_event], "2026-10-15")

        self.assertIn("Daily Digest", subject)
        self.assertIn("Autonomous AI Agents Workshop", text)
        self.assertIn("AI Builders", text)
        self.assertIn("Autonomous AI Agents Workshop", html)
        self.assertIn("https://example.com/ai-agents", html)

    def test_email_digest_idempotency_and_preference_check(self):
        """Digest is sent only once per user per date, and disabled setting is respected."""
        mock_user_db = MagicMock()
        mock_event_db = MagicMock()
        mock_notif_db = MagicMock()

        mock_user_db.get_all_active_users.return_value = [
            {
                "id": self.user_a_id,
                "email": "alice@example.com",
                "notification_preferences": {"email_enabled": True},
            },
            {
                "id": self.user_b_id,
                "email": "bob@example.com",
                "notification_preferences": {"email_enabled": False},  # Disabled
            },
        ]
        mock_event_db.get_upcoming_events.return_value = [self.sample_event]

        # Alice has not received digest yet
        mock_notif_db.has_digest_been_sent.side_effect = lambda uid, d: False

        service = EmailService(
            user_db=mock_user_db,
            event_db=mock_event_db,
            notification_db=mock_notif_db,
        )

        with patch.object(service, "send_email", return_value=True) as mock_send:
            sent_count = service.send_daily_digests(target_date="2026-10-15")
            self.assertEqual(sent_count, 1)  # Only Alice
            mock_send.assert_called_once()
            mock_notif_db.record_digest_sent.assert_called_with(self.user_a_id, "2026-10-15", 1)

        # If digest has already been sent, it skips sending
        mock_notif_db.has_digest_been_sent.side_effect = lambda uid, d: True
        with patch.object(service, "send_email", return_value=True) as mock_send:
            sent_count_repeat = service.send_daily_digests(target_date="2026-10-15")
            self.assertEqual(sent_count_repeat, 0)
            mock_send.assert_not_called()

    # ------------------------------------------------------------------
    # 5. Scraper Service & Scheduler Resilience
    # ------------------------------------------------------------------
    @patch("eventscout.services.scraper_service.scrape_meetup_events")
    def test_scraper_service_identifies_new_events(self, mock_scrape):
        """ScraperService forwards only newly inserted events to NotificationService."""
        mock_notif_service = MagicMock()
        mock_notif_service.dispatch_new_event_notifications.return_value = 1

        mock_scrape.return_value = (
            [self.sample_event],
            {
                "new_inserted": 1,
                "existing_updated": 0,
                "already_current": 0,
                "new_events": [self.sample_event],
            },
        )

        service = ScraperService(notification_service=mock_notif_service)
        summary = service.run_pipeline()

        self.assertEqual(summary["new_inserted"], 1)
        self.assertEqual(summary["notifications_dispatched"], 1)
        mock_notif_service.dispatch_new_event_notifications.assert_called_once_with([self.sample_event])

    @patch("eventscout.services.scraper_service.scrape_meetup_events")
    def test_scheduler_handles_scraper_failure_cleanly(self, mock_scrape):
        """Scheduler handles scraping error without crashing the application."""
        mock_scrape.side_effect = RuntimeError("Playwright connection failed")

        scheduler = EventScoutScheduler()
        # Should not raise exception
        scheduler.run_scraper_job()

    # ------------------------------------------------------------------
    # 6. Preferences API Notification Toggles
    # ------------------------------------------------------------------
    @patch("api.routers.users.UserDatabase")
    def test_update_notification_preferences(self, mock_user_db_cls):
        """User can update notification preferences via PUT /me/preferences."""
        mock_db = MagicMock()
        mock_user_db_cls.return_value = mock_db

        mock_db.update_preferences.return_value = True
        mock_db.find_by_id.return_value = {
            "id": self.user_a_id,
            "interests": [],
            "skills": [],
            "preferred_event_types": [],
            "preferred_modes": [],
            "notification_preferences": {
                "dashboard_enabled": True,
                "browser_enabled": False,
                "email_enabled": True,
            },
        }

        res = self.client.put(
            "/me/preferences",
            json={
                "notification_preferences": {
                    "dashboard_enabled": True,
                    "browser_enabled": False,
                    "email_enabled": True,
                }
            },
            headers={"Authorization": f"Bearer {self.token_a}"},
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("notification_preferences", data)
        self.assertFalse(data["notification_preferences"]["browser_enabled"])


if __name__ == "__main__":
    unittest.main()
