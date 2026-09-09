import os
from datetime import datetime, timezone
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv()

mongo_uri = os.getenv("MONGODB_URI")
db_name = os.getenv("MONGODB_DATABASE", "eventscout")

client = MongoClient(mongo_uri)
db = client[db_name]
collection = db["events"]

# Sample single event document
test_event = {
    "title": "Hyderabad MongoDB User Group Test Event",
    "organizer": "Hyderabad MongoDB User Group",
    "date_time": "2026-09-26T10:00:00+05:30",
    "mode_location": "Offline - Hyderabad",
    "city": "Hyderabad",
    "is_free": True,
    "is_technical": True,
    "categories": ["Data & Databases"],
    "source": "manual_test",
    "created_at": datetime.now(timezone.utc).isoformat()
}

print(f"Inserting test document into {db_name}.events...")
result = collection.insert_one(test_event)

print("----------------------------------------------------------------")
print(f"SUCCESS: Document inserted into collection 'events'!")
print(f"Generated Document _id: {result.inserted_id}")
print("----------------------------------------------------------------")
print("You can now go to Atlas -> Clusters -> Browse Collections to view it!")
