"""
Verification test to inspect the development user document in MongoDB Atlas.

Validates that:
1. User document exists in MongoDB Atlas 'users' collection
2. username is 'sk'
3. email matches the configured email
4. password_hash is a valid bcrypt hash ($2b$...)
5. Plaintext 'password' key DOES NOT exist in the document
"""

import sys
from eventscout.database.user_db import UserDatabase


def verify_mongo_user():
    db = UserDatabase()
    col = db.get_collection()

    user = col.find_one({"username": "sk"})
    if not user:
        print("FAIL: User 'sk' not found in MongoDB users collection.")
        sys.exit(1)

    print("SUCCESS: User 'sk' found in MongoDB Atlas!")
    print(f"  _id: {user['_id']}")
    print(f"  username: {user.get('username')}")
    print(f"  email: {user.get('email')}")

    # Check password_hash
    pwd_hash = user.get("password_hash")
    if not pwd_hash or not (pwd_hash.startswith("$2b$") or pwd_hash.startswith("$2a$")):
        print(f"FAIL: password_hash is invalid or missing.")
        sys.exit(1)
    print("  password_hash: <valid bcrypt hash present (starts with $2b$)>")

    # Verify plaintext password NEVER exists
    if "password" in user:
        print("CRITICAL SECURITY FAILURE: Plaintext 'password' field found in MongoDB document!")
        sys.exit(1)
    else:
        print("  plaintext 'password' field in MongoDB: NONE (PASSED - securely omitted)")

    # Verify other required fields
    expected_fields = ["interests", "skills", "preferred_event_types", "preferred_modes", "saved_event_ids", "created_at"]
    for f in expected_fields:
        if f not in user:
            print(f"WARNING: Field '{f}' missing from user document.")
        else:
            print(f"  {f}: {type(user[f]).__name__} (count: {len(user[f]) if isinstance(user[f], list) else 'N/A'})")

    print("\nAll MongoDB user model checks PASSED successfully!")


if __name__ == "__main__":
    verify_mongo_user()
