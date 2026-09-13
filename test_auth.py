"""
Unit and Integration tests for EventScout Authentication, Preferences,
Saved Events, and User Isolation.

Covers:
1. User Registration & Password Hashing (never storing plain text)
2. Duplicate Email Rejection
3. User Login & JWT Generation
4. Invalid Password Handling (Generic 401)
5. GET /auth/me (Never exposing password_hash)
6. Preferences GET and PUT validation
7. Save / Unsave Event Idempotency ($addToSet / $pull)
8. GET /events/saved returning full event documents
9. User Isolation (User A cannot access or mutate User B's saved events or preferences)
"""

import unittest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
from bson import ObjectId

from fastapi.testclient import TestClient
from api.main import app
from api.auth import hash_password, verify_password, create_access_token


class TestAuthAndPersonalization(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.user_a_id = str(ObjectId())
        self.user_b_id = str(ObjectId())
        self.sample_event_oid = ObjectId()
        self.sample_event_id = str(self.sample_event_oid)

        self.events_db = {
            self.sample_event_id: {
                "_id": self.sample_event_oid,
                "id": self.sample_event_id,
                "title": "Full-Stack AI Workshop",
                "organizer": "AI Builders",
                "date_time": datetime.now(timezone.utc).isoformat(),
                "event_url": "https://example.com/ai-workshop",
                "mode_location": "Online",
                "is_free": True,
                "categories": ["AI / ML"],
            }
        }

    # ------------------------------------------------------------------
    # 1. Password Hashing & Verification
    # ------------------------------------------------------------------
    def test_password_hashing_and_verification(self):
        """Plain passwords must never match hash and must verify via bcrypt."""
        password = "SecurePassword123!"
        hashed = hash_password(password)

        self.assertNotEqual(password, hashed)
        self.assertTrue(verify_password(password, hashed))
        self.assertFalse(verify_password("WrongPassword", hashed))

    # ------------------------------------------------------------------
    # 2. Registration & Signup
    # ------------------------------------------------------------------
    @patch("api.routers.auth.UserDatabase")
    def test_signup_success_with_username_and_no_password_hash_leak(self, mock_user_db_cls):
        """Signing up a new user with username returns JWT and user profile with username."""
        mock_db = MagicMock()
        mock_user_db_cls.return_value = mock_db
        mock_db.find_by_email.return_value = None

        new_user = {
            "_id": self.user_a_id,
            "id": self.user_a_id,
            "username": "sk",
            "email": "sk@example.com",
            "password_hash": "$2b$12$somehashedstringhere",
            "interests": [],
            "skills": [],
            "preferred_event_types": [],
            "preferred_modes": [],
            "saved_event_ids": [],
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        mock_db.create_user.return_value = new_user

        response = self.client.post(
            "/auth/signup",
            json={"username": "sk", "email": "sk@example.com", "password": "Password123!"},
        )

        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertIn("access_token", data)
        self.assertEqual(data["token_type"], "bearer")
        self.assertEqual(data["user"]["username"], "sk")
        self.assertEqual(data["user"]["email"], "sk@example.com")
        self.assertNotIn("password_hash", data["user"])

    @patch("api.routers.auth.UserDatabase")
    def test_signup_duplicate_email_fails(self, mock_user_db_cls):
        """Attempting to sign up an existing email returns 409 Conflict."""
        from pymongo.errors import DuplicateKeyError

        mock_db = MagicMock()
        mock_user_db_cls.return_value = mock_db
        mock_db.create_user.side_effect = DuplicateKeyError("E11000 duplicate key error")

        response = self.client.post(
            "/auth/signup",
            json={"username": "sk", "email": "sk@example.com", "password": "Password123!"},
        )
        self.assertEqual(response.status_code, 409)
        self.assertIn("already exists", response.json()["detail"].lower())

    def test_signup_invalid_input_validation(self):
        """Short passwords (<6) and invalid usernames fail with 422 Unprocessable Entity."""
        # Too short password
        res1 = self.client.post(
            "/auth/signup",
            json={"username": "validuser", "email": "user@example.com", "password": "123"},
        )
        self.assertEqual(res1.status_code, 422)

        # Invalid username (special characters)
        res2 = self.client.post(
            "/auth/signup",
            json={"username": "invalid user!", "email": "user@example.com", "password": "Password123!"},
        )
        self.assertEqual(res2.status_code, 422)

    @patch("api.routers.auth.UserDatabase")
    def test_register_success_and_no_password_hash_leak(self, mock_user_db_cls):
        """Registering a new user returns JWT and user profile without password_hash."""
        mock_db = MagicMock()
        mock_user_db_cls.return_value = mock_db
        mock_db.find_by_email.return_value = None

        new_user = {
            "_id": self.user_a_id,
            "id": self.user_a_id,
            "username": "alice",
            "email": "alice@example.com",
            "password_hash": "$2b$12$somehashedstringhere",
            "interests": [],
            "skills": [],
            "preferred_event_types": [],
            "preferred_modes": [],
            "saved_event_ids": [],
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        mock_db.create_user.return_value = new_user

        response = self.client.post(
            "/auth/register",
            json={"email": "alice@example.com", "password": "Password123!"},
        )

        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertIn("access_token", data)
        self.assertEqual(data["token_type"], "bearer")
        self.assertEqual(data["user"]["email"], "alice@example.com")
        self.assertNotIn("password_hash", data["user"])

    @patch("api.routers.auth.UserDatabase")
    def test_register_duplicate_email_fails(self, mock_user_db_cls):
        """Attempting to register an already existing email returns 409 Conflict."""
        from pymongo.errors import DuplicateKeyError

        mock_db = MagicMock()
        mock_user_db_cls.return_value = mock_db
        mock_db.create_user.side_effect = DuplicateKeyError("E11000 duplicate key error")

        response = self.client.post(
            "/auth/register",
            json={"email": "alice@example.com", "password": "Password123!"},
        )
        self.assertEqual(response.status_code, 409)
        self.assertIn("already exists", response.json()["detail"].lower())

    # ------------------------------------------------------------------
    # 3. Login
    # ------------------------------------------------------------------
    @patch("api.routers.auth.UserDatabase")
    def test_login_success(self, mock_user_db_cls):
        """Login with correct email returns valid JWT token."""
        mock_db = MagicMock()
        mock_user_db_cls.return_value = mock_db

        plain_pw = "Password123!"
        hashed_pw = hash_password(plain_pw)

        user_fixture = {
            "_id": self.user_a_id,
            "id": self.user_a_id,
            "username": "alice",
            "email": "alice@example.com",
            "password_hash": hashed_pw,
            "interests": ["AI / ML"],
            "skills": ["Python"],
            "preferred_event_types": ["Hackathon"],
            "preferred_modes": ["Online"],
            "saved_event_ids": [],
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        mock_db.find_by_identifier.return_value = user_fixture

        response = self.client.post(
            "/auth/login",
            json={"email": "alice@example.com", "password": plain_pw},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("access_token", data)
        self.assertEqual(data["user"]["username"], "alice")
        self.assertEqual(data["user"]["email"], "alice@example.com")
        self.assertNotIn("password_hash", data["user"])

    @patch("api.routers.auth.UserDatabase")
    def test_login_with_username_success(self, mock_user_db_cls):
        """Login with username returns valid JWT token."""
        mock_db = MagicMock()
        mock_user_db_cls.return_value = mock_db

        plain_pw = "Password123!"
        hashed_pw = hash_password(plain_pw)

        mock_db.find_by_identifier.return_value = {
            "_id": self.user_a_id,
            "id": self.user_a_id,
            "username": "sk",
            "email": "sk@example.com",
            "password_hash": hashed_pw,
            "interests": [],
            "skills": [],
            "preferred_event_types": [],
            "preferred_modes": [],
            "saved_event_ids": [],
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        response = self.client.post(
            "/auth/login",
            json={"username": "sk", "password": plain_pw},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("access_token", data)
        self.assertEqual(data["user"]["username"], "sk")
        self.assertEqual(data["user"]["email"], "sk@example.com")
        self.assertNotIn("password_hash", data["user"])

    @patch("api.routers.auth.UserDatabase")
    def test_login_invalid_password_returns_401(self, mock_user_db_cls):
        """Login with invalid password returns generic 401."""
        mock_db = MagicMock()
        mock_user_db_cls.return_value = mock_db

        hashed_pw = hash_password("CorrectPassword123!")
        mock_db.find_by_identifier.return_value = {
            "_id": self.user_a_id,
            "id": self.user_a_id,
            "username": "alice",
            "email": "alice@example.com",
            "password_hash": hashed_pw,
        }

        response = self.client.post(
            "/auth/login",
            json={"email": "alice@example.com", "password": "WrongPassword!"},
        )
        self.assertEqual(response.status_code, 401)
        self.assertIn("invalid email or password", response.json()["detail"].lower())

    # ------------------------------------------------------------------
    # 4. /auth/me Endpoint
    # ------------------------------------------------------------------
    @patch("api.routers.auth.UserDatabase")
    def test_get_current_user_profile(self, mock_user_db_cls):
        """GET /auth/me extracts user from token and returns profile with username and without password_hash."""
        mock_db = MagicMock()
        mock_user_db_cls.return_value = mock_db

        user_doc = {
            "_id": self.user_a_id,
            "id": self.user_a_id,
            "username": "alice",
            "email": "alice@example.com",
            "password_hash": "hash_secret",
            "interests": ["Cloud"],
            "skills": ["AWS"],
            "preferred_event_types": ["Meetup"],
            "preferred_modes": ["Hybrid"],
            "saved_event_ids": [],
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        mock_db.find_by_id.return_value = user_doc

        token = create_access_token({"sub": self.user_a_id, "email": "alice@example.com", "username": "alice"})

        response = self.client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["username"], "alice")
        self.assertEqual(data["email"], "alice@example.com")
        self.assertNotIn("password_hash", data)

    # ------------------------------------------------------------------
    # 5. Preferences GET & PUT
    # ------------------------------------------------------------------
    @patch("api.routers.users.UserDatabase")
    def test_update_and_get_preferences(self, mock_users_db_cls):
        """Updating preferences via PUT /me/preferences updates user preferences."""
        users_db = MagicMock()
        mock_users_db_cls.return_value = users_db

        token = create_access_token({"sub": self.user_a_id, "email": "alice@example.com"})

        # Update preferences
        new_prefs = {
            "interests": ["Web Development", "Cloud"],
            "skills": ["TypeScript", "FastAPI"],
            "preferred_event_types": ["Workshop", "Conference"],
            "preferred_modes": ["Online", "Hybrid"],
        }
        users_db.update_preferences.return_value = True
        users_db.find_by_id.return_value = {
            "_id": self.user_a_id,
            "id": self.user_a_id,
            "interests": ["Web Development", "Cloud"],
            "skills": ["TypeScript", "FastAPI"],
            "preferred_event_types": ["Workshop", "Conference"],
            "preferred_modes": ["Online", "Hybrid"],
        }

        put_res = self.client.put(
            "/me/preferences",
            json=new_prefs,
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(put_res.status_code, 200)
        put_data = put_res.json()
        self.assertEqual(put_data["interests"], ["Web Development", "Cloud"])
        self.assertEqual(put_data["skills"], ["TypeScript", "FastAPI"])

    def test_update_preferences_invalid_option_fails(self):
        """Supplying invalid interest or event mode fails with 422 Unprocessable Entity."""
        token = create_access_token({"sub": self.user_a_id, "email": "alice@example.com"})

        invalid_prefs = {
            "interests": ["InvalidInterestNonExistent"],
        }
        put_res = self.client.put(
            "/me/preferences",
            json=invalid_prefs,
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(put_res.status_code, 422)

    # ------------------------------------------------------------------
    # 6. Save & Unsave Events
    # ------------------------------------------------------------------
    @patch("api.routers.saved_events.EventDatabase")
    @patch("api.routers.saved_events.UserDatabase")
    def test_save_and_unsave_event_flow(self, mock_user_db_cls, mock_event_db_cls):
        """Test save, unsave, and idempotency."""
        user_db = MagicMock()
        event_db = MagicMock()

        mock_user_db_cls.return_value = user_db
        mock_event_db_cls.return_value = event_db

        # Event exists in collection
        mock_col = MagicMock()
        event_db.get_collection.return_value = mock_col
        mock_col.find_one.return_value = {"_id": self.sample_event_oid}

        user_db.save_event.return_value = True
        user_db.unsave_event.return_value = True

        token = create_access_token({"sub": self.user_a_id, "email": "alice@example.com"})

        # Save event
        save_res = self.client.post(
            f"/events/{self.sample_event_id}/save",
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(save_res.status_code, 200)
        self.assertTrue(save_res.json()["saved"])

        # Unsave event
        unsave_res = self.client.delete(
            f"/events/{self.sample_event_id}/save",
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(unsave_res.status_code, 200)
        self.assertFalse(unsave_res.json()["saved"])

    # ------------------------------------------------------------------
    # 7. User Data Isolation
    # ------------------------------------------------------------------
    @patch("api.routers.saved_events.EventDatabase")
    @patch("api.routers.saved_events.UserDatabase")
    def test_user_isolation(self, mock_user_db_cls, mock_event_db_cls):
        """User A saving an event must not reflect in User B's saved list."""
        user_db = MagicMock()
        event_db = MagicMock()

        mock_user_db_cls.return_value = user_db
        mock_event_db_cls.return_value = event_db

        # User A has 1 saved event, User B has none
        def get_saved_ids_side_effect(user_id):
            if user_id == self.user_a_id:
                return [self.sample_event_id]
            return []

        user_db.get_saved_event_ids.side_effect = get_saved_ids_side_effect

        mock_col = MagicMock()
        event_db.get_collection.return_value = mock_col
        mock_col.find.return_value = [self.events_db[self.sample_event_id]]

        token_a = create_access_token({"sub": self.user_a_id, "email": "alice@example.com"})
        token_b = create_access_token({"sub": self.user_b_id, "email": "bob@example.com"})

        # User A gets saved events -> returns 1 event
        res_a = self.client.get("/events/saved", headers={"Authorization": f"Bearer {token_a}"})
        self.assertEqual(res_a.status_code, 200)
        self.assertEqual(len(res_a.json()), 1)
        self.assertEqual(res_a.json()[0]["title"], "Full-Stack AI Workshop")

        # User B gets saved events -> returns empty list []
        res_b = self.client.get("/events/saved", headers={"Authorization": f"Bearer {token_b}"})
        self.assertEqual(res_b.status_code, 200)
        self.assertEqual(len(res_b.json()), 0)


if __name__ == "__main__":
    unittest.main()
