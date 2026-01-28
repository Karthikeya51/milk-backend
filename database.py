from pymongo import MongoClient
import os
from dotenv import load_dotenv

load_dotenv()   # 👈 REQUIRED

MONGO_URL = os.getenv("MONGO_URL")

client = MongoClient(MONGO_URL)
db = client["milkdb"]
milk_collection = db["milk_entries"]

# ✅ NEW COLLECTION
cow_health_collection = db["cow_health"]