from functools import lru_cache

from django.conf import settings
from pymongo import MongoClient


@lru_cache(maxsize=1)
def get_mongo_database():
    uri = settings.MONGODB_URI
    if not uri:
        raise RuntimeError('MONGODB_URI is not configured.')

    client = MongoClient(uri, serverSelectionTimeoutMS=2000, connectTimeoutMS=2000)
    client.admin.command('ping')
    return client[settings.MONGODB_DATABASE]


def save_chat_log(document):
    return get_mongo_database()['chat_logs'].insert_one(document)


def save_feedback(document):
    return get_mongo_database()['feedback'].insert_one(document)
