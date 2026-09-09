import os
from dotenv import load_dotenv
from pymongo import MongoClient

# Load variables from .env
load_dotenv()

mongo_uri = os.getenv("MONGODB_URI")
db_name = os.getenv("MONGODB_DATABASE", "eventscout")

print("--------------------------------------------------")
print(f"Connecting to MongoDB database: '{db_name}'...")
print("--------------------------------------------------")

try:
    # 5 second timeout so it fails quickly if IP address is not whitelisted
    client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
    
    # Send a ping command to confirm successful authentication and connection
    client.admin.command('ping')
    print("SUCCESS: Connected to MongoDB Atlas successfully!")
    print(f"Databases available on cluster: {client.list_database_names()}")

except Exception as e:
    print("\nERROR: Failed to connect to MongoDB Atlas.")
    print("Details:", e)
    print("\nCommon Troubleshooting Tips:")
    print("1. Did you whitelist your IP in Atlas under Network Access -> Add IP Address?")
    print("2. Is your username and password in .env correct?")
