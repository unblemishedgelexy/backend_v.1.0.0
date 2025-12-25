import os
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

_MONGO_CLIENT = None

def get_mongo_client():
    global _MONGO_CLIENT
    if _MONGO_CLIENT is None:
        _MONGO_CLIENT = MongoClient(
            os.getenv("MONGO_URI"),
            maxPoolSize=50,
            serverSelectionTimeoutMS=5000
        )
    return _MONGO_CLIENT


def get_db():
    client = get_mongo_client()
    return client[os.getenv("MONGO_DB_NAME")]