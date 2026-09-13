"""
Live integration test against FastAPI app using TestClient and MongoDB Atlas.
Validates:
1. Login with dev user 'sk' using username and password
2. Login with dev user using email and password
3. Calling GET /auth/me with Bearer token
4. Calling GET /events/saved with Bearer token
5. Calling GET /me/preferences with Bearer token
"""

import os
from dotenv import load_dotenv
from fastapi.testclient import TestClient
from api.main import app

load_dotenv()

client = TestClient(app)

username = os.getenv("DEV_USER_USERNAME", "sk")
email = os.getenv("DEV_USER_EMAIL", "saikeerthana.sathyavada@gmail.com")
password = os.getenv("DEV_USER_PASSWORD", "DevScout2026!")

print("=== 1. Testing Login with Username ===")
res_user = client.post("/auth/login", json={"username": username, "password": password})
assert res_user.status_code == 200, f"Login with username failed: {res_user.text}"
user_data = res_user.json()
print("SUCCESS: Logged in via username 'sk'. Token received.")
print("User profile in response:", user_data["user"])
assert "password_hash" not in user_data["user"]
assert user_data["user"]["username"] == "sk"
token = user_data["access_token"]

print("\n=== 2. Testing Login with Email ===")
res_email = client.post("/auth/login", json={"email": email, "password": password})
assert res_email.status_code == 200, f"Login with email failed: {res_email.text}"
print("SUCCESS: Logged in via email.")

print("\n=== 3. Testing GET /auth/me ===")
res_me = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
assert res_me.status_code == 200, f"GET /auth/me failed: {res_me.text}"
me_data = res_me.json()
print("SUCCESS: /auth/me returned profile:")
print(" ", me_data)
assert me_data["username"] == "sk"
assert "password_hash" not in me_data

print("\n=== 4. Testing Protected GET /events/saved ===")
res_saved = client.get("/events/saved", headers={"Authorization": f"Bearer {token}"})
assert res_saved.status_code == 200, f"GET /events/saved failed: {res_saved.text}"
print(f"SUCCESS: /events/saved returned {len(res_saved.json())} saved events for user.")

print("\n=== 5. Testing Protected GET /me/preferences ===")
res_prefs = client.get("/me/preferences", headers={"Authorization": f"Bearer {token}"})
assert res_prefs.status_code == 200, f"GET /me/preferences failed: {res_prefs.text}"
print("SUCCESS: /me/preferences returned:")
print(" ", res_prefs.json())

print("\n=== 6. Testing Unauthenticated Request Rejected (401) ===")
res_unauth = client.get("/events/saved")
assert res_unauth.status_code == 401 or res_unauth.status_code == 403
print("SUCCESS: Unauthenticated access to /events/saved correctly rejected!")

print("\nALL LIVE INTEGRATION CHECKS PASSED!")
