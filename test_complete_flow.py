"""
Comprehensive End-to-End Verification of EventScout Auth & Personalization:
1. Login as dev user 'sk'
2. Fetch events from /events
3. Save an event for 'sk'
4. Verify /events/saved returns the saved event for 'sk'
5. Update preferences for 'sk' via PUT /me/preferences
6. Verify /me/preferences returns updated preferences for 'sk'
7. Sign up a second user 'bob_tester'
8. Verify user isolation: 'bob_tester' sees 0 saved events and empty preferences
9. Unsave event for 'sk' and verify clean state
"""

import os
from dotenv import load_dotenv
from fastapi.testclient import TestClient
from api.main import app
from eventscout.database.user_db import UserDatabase

load_dotenv()

client = TestClient(app)

username = os.getenv("DEV_USER_USERNAME", "sk")
password = os.getenv("DEV_USER_PASSWORD", "DevScout2026!")

print("==================================================")
print("  EVENTSCOUT COMPLETE AUTH & PERSONALIZATION FLOW")
print("==================================================")

# 1. Login as 'sk'
print("\n[Step 1] Logging in as seeded user 'sk'...")
res_login = client.post("/auth/login", json={"username": username, "password": password})
assert res_login.status_code == 200, f"Login failed: {res_login.text}"
auth_sk = res_login.json()
token_sk = auth_sk["access_token"]
user_sk = auth_sk["user"]
print(f"-> Authenticated as '{user_sk['username']}' ({user_sk['email']}) [ID: {user_sk['id']}]")

# 2. Fetch events from database
print("\n[Step 2] Fetching upcoming events from /events...")
res_events = client.get("/events")
assert res_events.status_code == 200, f"Get events failed: {res_events.text}"
events = res_events.json()
print(f"-> Retrieved {len(events)} upcoming events from MongoDB.")

if events:
    target_event = events[0]
    target_event_id = target_event["id"]
    target_event_title = target_event["title"]
    print(f"-> Target event for save test: '{target_event_title}' (ID: {target_event_id})")

    # 3. Save event for 'sk'
    print("\n[Step 3] Saving event for user 'sk'...")
    res_save = client.post(
        f"/events/{target_event_id}/save",
        headers={"Authorization": f"Bearer {token_sk}"},
    )
    assert res_save.status_code == 200, f"Save failed: {res_save.text}"
    print(f"-> Save response: {res_save.json()}")

    # 4. Verify saved events list
    print("\n[Step 4] Checking GET /events/saved for user 'sk'...")
    res_saved = client.get(
        "/events/saved",
        headers={"Authorization": f"Bearer {token_sk}"},
    )
    assert res_saved.status_code == 200, f"GET saved failed: {res_saved.text}"
    saved_list = res_saved.json()
    assert any(e["id"] == target_event_id for e in saved_list), "Target event not found in saved list!"
    print(f"-> User 'sk' currently has {len(saved_list)} saved event(s): '{saved_list[0]['title']}'")

# 5. Update preferences for 'sk'
print("\n[Step 5] Updating preferences for user 'sk'...")
new_prefs = {
    "interests": ["AI / ML", "Web Development", "Cloud"],
    "skills": ["Python", "FastAPI", "React"],
    "preferred_event_types": ["Hackathon", "Workshop"],
    "preferred_modes": ["Online", "Hybrid"],
}
res_prefs_put = client.put(
    "/me/preferences",
    json=new_prefs,
    headers={"Authorization": f"Bearer {token_sk}"},
)
assert res_prefs_put.status_code == 200, f"Preferences update failed: {res_prefs_put.text}"
print(f"-> PUT /me/preferences succeeded: {res_prefs_put.json()}")

# 6. Verify preferences persistence
print("\n[Step 6] Verifying GET /me/preferences for user 'sk'...")
res_prefs_get = client.get(
    "/me/preferences",
    headers={"Authorization": f"Bearer {token_sk}"},
)
assert res_prefs_get.status_code == 200
prefs_data = res_prefs_get.json()
assert "AI / ML" in prefs_data["interests"]
assert "FastAPI" in prefs_data["skills"]
print(f"-> Verified stored preferences: {prefs_data}")

# 7. Create a second user via /auth/signup to test isolation
print("\n[Step 7] Testing User Isolation: signing up 'bob_tester'...")
test_email = "bob_tester@example.com"
# Clean up if existed from previous run
db = UserDatabase()
existing_bob = db.find_by_email(test_email)
if existing_bob:
    db.get_collection().delete_one({"email": test_email})

res_signup_bob = client.post(
    "/auth/signup",
    json={"username": "bob_tester", "email": test_email, "password": "Password123!"},
)
assert res_signup_bob.status_code == 201, f"Signup bob failed: {res_signup_bob.text}"
token_bob = res_signup_bob.json()["access_token"]
print("-> Signed up 'bob_tester' successfully.")

# 8. Verify bob has 0 saved events and empty preferences
print("\n[Step 8] Verifying 'bob_tester' cannot see 'sk's saved events or preferences...")
res_bob_saved = client.get(
    "/events/saved",
    headers={"Authorization": f"Bearer {token_bob}"},
)
assert res_bob_saved.status_code == 200
assert len(res_bob_saved.json()) == 0, "Isolation failure: bob sees saved events!"
print("-> SUCCESS: Bob has 0 saved events (User isolation confirmed).")

res_bob_prefs = client.get(
    "/me/preferences",
    headers={"Authorization": f"Bearer {token_bob}"},
)
assert res_bob_prefs.status_code == 200
assert len(res_bob_prefs.json()["interests"]) == 0, "Isolation failure: bob sees sk's preferences!"
print("-> SUCCESS: Bob has empty default preferences (User isolation confirmed).")

# Cleanup bob
db.get_collection().delete_one({"email": test_email})

# 9. Unsave event for 'sk'
if events:
    print("\n[Step 9] Testing unsave event for user 'sk'...")
    res_unsave = client.delete(
        f"/events/{target_event_id}/save",
        headers={"Authorization": f"Bearer {token_sk}"},
    )
    assert res_unsave.status_code == 200
    print(f"-> Unsave response: {res_unsave.json()}")

    res_saved_after = client.get(
        "/events/saved",
        headers={"Authorization": f"Bearer {token_sk}"},
    )
    assert res_saved_after.status_code == 200
    assert not any(e["id"] == target_event_id for e in res_saved_after.json())
    print("-> Verified event was removed from user 'sk's saved list.")

print("\n==================================================")
print("  ALL COMPLETE FLOW CHECKS PASSED PERFECTLY!")
print("==================================================")
