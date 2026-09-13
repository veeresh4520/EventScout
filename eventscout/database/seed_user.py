"""
Safe, idempotent seed script for the EventScout development user.

Features:
- Configurable via environment variables (DEV_USER_USERNAME, DEV_USER_EMAIL, DEV_USER_PASSWORD)
- Uses secure bcrypt password hashing
- Idempotent: skips or updates without creating duplicates if the user already exists
- NEVER prints or logs plaintext passwords
- Can be executed directly: python -m eventscout.database.seed_user
"""

import logging
import os
import sys
from dotenv import load_dotenv

from api.auth import hash_password
from eventscout.database.user_db import UserDatabase

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("EventScoutUserSeed")


def seed_development_user() -> dict:
    """
    Seeds an initial development user into the MongoDB users collection.
    Returns the public user information dictionary.
    """
    username = os.getenv("DEV_USER_USERNAME", "sk").strip()
    email = os.getenv("DEV_USER_EMAIL", "saikeerthana.sathyavada@gmail.com").lower().strip()
    plaintext_password = os.getenv("DEV_USER_PASSWORD", "DevScout2026!")

    if not username:
        raise ValueError("DEV_USER_USERNAME cannot be empty.")
    if not email:
        raise ValueError("DEV_USER_EMAIL cannot be empty.")
    if len(plaintext_password) < 6:
        raise ValueError("DEV_USER_PASSWORD must be at least 6 characters.")

    db = UserDatabase()
    col = db.get_collection()

    # Check if user already exists by email or username
    existing_user = db.find_by_email(email) or db.find_by_username(username)

    if existing_user:
        logger.info(
            "Development user '%s' (%s) already exists with ID: %s. Ensuring password hash and username are up to date.",
            username,
            email,
            existing_user["id"],
        )
        new_hash = hash_password(plaintext_password)
        col.update_one(
            {"_id": col.find_one({"email": email})["_id"]},
            {"$set": {"username": username, "password_hash": new_hash}},
        )
        updated = db.find_by_email(email)
        return {
            "id": updated["id"],
            "username": updated.get("username", username),
            "email": updated["email"],
            "status": "updated",
        }

    # User does not exist, create safely
    logger.info("Creating initial development user '%s' (%s)...", username, email)
    password_hash = hash_password(plaintext_password)
    user_doc = db.create_user(
        email=email,
        password_hash=password_hash,
        username=username,
    )
    logger.info("Successfully seeded development user with ID: %s", user_doc["id"])

    return {
        "id": user_doc["id"],
        "username": user_doc.get("username", username),
        "email": user_doc["email"],
        "status": "created",
    }


if __name__ == "__main__":
    try:
        result = seed_development_user()
        print(f"Seed complete: User '{result['username']}' ({result['email']}) -> {result['status']}")
    except Exception as e:
        logger.error("Seeding failed: %s", e, exc_info=True)
        sys.exit(1)
