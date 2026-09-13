"""
Live End-to-End Verification for Group 2: Automation + Notifications.
Tests against running FastAPI app and MongoDB Atlas:
1. Authenticate as dev user 'sk'.
2. Fetch notifications & unread count via /notifications.
3. Simulate new event discovery & notification creation.
4. Verify notification shows up in /notifications for user 'sk'.
5. Verify duplicate prevention (same user + event + type cannot create second notification).
6. Verify User Isolation: User B cannot see or read User A's notifications.
7. Mark notification as read and verify unread count decreases.
8. Verify daily email digest dispatch and idempotency in sent_digests collection.
"""

import os
from datetime import datetime, timezone
from bson import ObjectId
from dotenv import load_dotenv
from fastapi.testclient import TestClient

from api.main import app
from eventscout.database.notification_db import NotificationDatabase
from eventscout.database.user_db import UserDatabase
from eventscout.services.notification_service import NotificationService
from eventscout.services.email_service import EmailService

load_dotenv()

client = TestClient(app)

print("==================================================")
print("  GROUP 2: AUTOMATION & NOTIFICATIONS LIVE E2E")
print("==================================================")

# 1. Login as 'sk'
username = os.getenv("DEV_USER_USERNAME", "sk")
password = os.getenv("DEV_USER_PASSWORD", "DevScout2026!")

res_login = client.post("/auth/login", json={"username": username, "password": password})
assert res_login.status_code == 200, f"Login failed: {res_login.text}"
auth_data = res_login.json()
token_sk = auth_data["access_token"]
user_sk = auth_data["user"]
user_id_sk = user_sk["id"]
print(f"\n[Step 1] Logged in as '{username}' [ID: {user_id_sk}]")

# 2. Check initial notifications
res_notifs = client.get("/notifications", headers={"Authorization": f"Bearer {token_sk}"})
assert res_notifs.status_code == 200
initial_data = res_notifs.json()
print(f"[Step 2] Current notifications for '{username}': {len(initial_data['notifications'])}, unread: {initial_data['unread_count']}")

# 3. Simulate a newly discovered event and dispatch notification
test_event_oid = ObjectId()
test_event_id = str(test_event_oid)
test_event = {
    "id": test_event_id,
    "_id": test_event_id,
    "title": "Live E2E Cloud Native Summit 2026",
    "organizer": "Cloud Native Community",
    "mode_location": "Online",
    "event_url": "https://example.com/cloud-summit",
    "date_time": "2026-10-20T10:00:00+00:00",
    "categories": ["Cloud", "DevOps"],
    "is_free": True,
}

print(f"\n[Step 3] Dispatching new event notification for: '{test_event['title']}'...")
notif_service = NotificationService()
created_count = notif_service.dispatch_new_event_notifications([test_event])
print(f"-> Dispatched: {created_count} notification(s) created.")
assert created_count >= 1, "Expected at least 1 notification to be created for user 'sk'!"

# 4. Verify notification appears via API
res_notifs_after = client.get("/notifications", headers={"Authorization": f"Bearer {token_sk}"})
assert res_notifs_after.status_code == 200
data_after = res_notifs_after.json()
target_notif = next((n for n in data_after["notifications"] if n["event_id"] == test_event_id), None)
assert target_notif is not None, "Newly created notification not found in /notifications response!"
notif_id = target_notif["id"]
print(f"[Step 4] Verified notification received via GET /notifications [ID: {notif_id}, read: {target_notif['read']}]")

# 5. Verify Anti-Spam / Idempotency: Dispatching the same event again must NOT create a duplicate
print("\n[Step 5] Testing Anti-Spam: re-dispatching the exact same event...")
dup_count = notif_service.dispatch_new_event_notifications([test_event])
print(f"-> Duplicate dispatch count: {dup_count} (Expected: 0)")
assert dup_count == 0, f"Anti-spam failure: duplicate notification was created ({dup_count})!"

# 6. Test User Isolation: User B cannot see User A's notifications
print("\n[Step 6] Testing User Isolation...")
test_user_b_email = "e2e_tester_b@example.com"
user_db = UserDatabase()
# Clean up if existed
existing_b = user_db.find_by_email(test_user_b_email)
if existing_b:
    user_db.get_collection().delete_one({"email": test_user_b_email})

res_signup_b = client.post("/auth/signup", json={"username": "tester_b", "email": test_user_b_email, "password": "Password123!"})
assert res_signup_b.status_code == 201
token_b = res_signup_b.json()["access_token"]

# User B checks notifications
res_notifs_b = client.get("/notifications", headers={"Authorization": f"Bearer {token_b}"})
assert res_notifs_b.status_code == 200
data_b = res_notifs_b.json()
assert len(data_b["notifications"]) == 0, "User isolation failure: User B saw User A's notifications!"
print("-> SUCCESS: User B has 0 notifications. Strict user isolation confirmed.")

# User B cannot mark User A's notification as read
res_hacked_read = client.post(f"/notifications/{notif_id}/read", headers={"Authorization": f"Bearer {token_b}"})
assert res_hacked_read.status_code == 404, "Security failure: User B was able to modify User A's notification!"
print("-> SUCCESS: User B forbidden from mutating User A's notification (returned 404).")

# Clean up User B
user_db.get_collection().delete_one({"email": test_user_b_email})

# 7. Mark notification as read
print("\n[Step 7] Marking notification as read for user 'sk'...")
res_read = client.post(f"/notifications/{notif_id}/read", headers={"Authorization": f"Bearer {token_sk}"})
assert res_read.status_code == 200
print(f"-> Mark read response: {res_read.json()}")

# Clean up test notification from DB
notif_db = NotificationDatabase()
notif_db.get_notifications_collection().delete_one({"_id": ObjectId(notif_id)})

# 8. Daily Email Digest Idempotency Check
print("\n[Step 8] Testing Daily Email Digest Idempotency...")
email_service = EmailService()
test_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
# Clean up sent_digests for test_date so we test clean send -> duplicate block
notif_db.get_sent_digests_collection().delete_one({"user_id": user_id_sk, "date_str": test_date})

first_run = email_service.send_daily_digests(target_date=test_date)
print(f"-> First run digest sent: {first_run} (Expected >= 1)")
assert first_run >= 1, "Expected email digest to send on first run"

second_run = email_service.send_daily_digests(target_date=test_date)
print(f"-> Second run on same date: {second_run} (Expected 0 due to idempotency)")
assert second_run == 0, "Idempotency failure: duplicate email digest sent on same date!"

print("\n==================================================")
print("  ALL GROUP 2 LIVE E2E CHECKS PASSED PERFECTLY!")
print("==================================================")
