"""
Utility script to grant a user administrative privileges.
Usage: python -m eventscout.database.make_admin <email>
"""
import sys
import logging
from eventscout.database.user_db import UserDatabase

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("make_admin")

def main():
    if len(sys.argv) < 2:
        print("Usage: python -m eventscout.database.make_admin <user_email>")
        sys.exit(1)
        
    email = sys.argv[1].strip()
    db = UserDatabase()
    
    user = db.find_by_email(email)
    if not user:
        logger.error(f"User with email {email} not found.")
        sys.exit(1)
        
    col = db.get_collection()
    res = col.update_one({"email": email.lower()}, {"$set": {"is_admin": True}})
    
    if res.modified_count > 0 or res.matched_count > 0:
        logger.info(f"Successfully granted admin privileges to {email}.")
    else:
        logger.error("Failed to update user.")

if __name__ == "__main__":
    main()
