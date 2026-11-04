"""MongoDB storage for assistant conversations, messages and feedback.

MongoDB is optional at runtime: every function degrades gracefully (logging
the failure and returning None/False) so chat keeps working when MongoDB is
down. Credentials only ever live in the MONGODB_URI environment variable.
"""
import logging
import time
import uuid

from bson import ObjectId
from bson.errors import InvalidId
from django.conf import settings
from django.utils import timezone
from pymongo import ASCENDING, MongoClient
from pymongo.errors import PyMongoError

logger = logging.getLogger("inventory.app")

_client = None
_client_uri = None
_indexes_ready = False


def _get_db():
    global _client, _client_uri, _indexes_ready
    uri = settings.MONGODB_URI
    if not uri:
        return None
    if _client is None or _client_uri != uri:
        _client = MongoClient(uri, serverSelectionTimeoutMS=settings.MONGODB_TIMEOUT_MS,
                              connectTimeoutMS=settings.MONGODB_TIMEOUT_MS, appname="inventory-assistant")
        _client_uri = uri
        _indexes_ready = False
    db = _client[settings.MONGODB_DB_NAME]
    if not _indexes_ready:
        db.conversations.create_index([("conversation_id", ASCENDING)], unique=True)
        db.messages.create_index([("conversation_id", ASCENDING), ("timestamp", ASCENDING)])
        db.feedback.create_index([("message_id", ASCENDING)])
        _indexes_ready = True
    return db


def reset_client():
    global _client, _client_uri, _indexes_ready
    if _client is not None:
        _client.close()
    _client = _client_uri = None
    _indexes_ready = False


def ping():
    if not settings.MONGODB_URI:
        return {"status": "not_configured"}
    started = time.perf_counter()
    try:
        db = _get_db()
        db.command("ping")
        return {"status": "connected", "latency_ms": round((time.perf_counter() - started) * 1000, 2)}
    except PyMongoError as exc:
        logger.warning("MongoDB ping failed: %s", exc.__class__.__name__)
        return {"status": "unavailable", "error": exc.__class__.__name__}


def new_conversation_id():
    return uuid.uuid4().hex


def ensure_conversation(conversation_id, user_id=None, session_id=None):
    try:
        db = _get_db()
        if db is None:
            return False
        now = timezone.now()
        db.conversations.update_one(
            {"conversation_id": conversation_id},
            {"$setOnInsert": {"conversation_id": conversation_id, "created_at": now,
                              "user_id": user_id, "session_id": None if user_id else session_id},
             "$set": {"updated_at": now}},
            upsert=True,
        )
        return True
    except PyMongoError as exc:
        logger.error("MongoDB conversation upsert failed: %s", exc.__class__.__name__)
        return False


def save_message(conversation_id, user_message, assistant_response, source, user_id=None, session_id=None,
                 ticket_id=None, matched=None):
    """Persist one exchange. Returns the message id string, or None if MongoDB is unavailable."""
    try:
        db = _get_db()
        if db is None:
            return None
        ensure_conversation(conversation_id, user_id, session_id)
        doc = {
            "conversation_id": conversation_id,
            "user_message": user_message,
            "assistant_response": assistant_response,
            "source": source,
            "matched": matched,
            "ticket_id": ticket_id,
            "timestamp": timezone.now(),
        }
        return str(db.messages.insert_one(doc).inserted_id)
    except PyMongoError as exc:
        logger.error("MongoDB message insert failed: %s", exc.__class__.__name__)
        return None


def get_history(conversation_id, limit=50):
    try:
        db = _get_db()
        if db is None:
            return []
        cursor = db.messages.find({"conversation_id": conversation_id}).sort("timestamp", ASCENDING).limit(limit)
        return [{"id": str(m["_id"]), "user_message": m["user_message"], "assistant_response": m["assistant_response"],
                 "source": m.get("source"), "ticket_id": m.get("ticket_id"),
                 "timestamp": m["timestamp"].isoformat()} for m in cursor]
    except PyMongoError as exc:
        logger.error("MongoDB history read failed: %s", exc.__class__.__name__)
        return []


def message_belongs_to(conversation_id, message_id):
    try:
        db = _get_db()
        if db is None:
            return False
        return db.messages.count_documents({"_id": ObjectId(message_id), "conversation_id": conversation_id}) == 1
    except (PyMongoError, InvalidId, TypeError):
        return False


def save_feedback(conversation_id, message_id, rating, feedback_text=""):
    try:
        db = _get_db()
        if db is None:
            return None
        doc = {"conversation_id": conversation_id, "message_id": message_id, "rating": rating,
               "feedback_text": feedback_text, "timestamp": timezone.now()}
        return str(db.feedback.insert_one(doc).inserted_id)
    except PyMongoError as exc:
        logger.error("MongoDB feedback insert failed: %s", exc.__class__.__name__)
        return None


def collection_counts():
    try:
        db = _get_db()
        if db is None:
            return None
        return {name: db[name].count_documents({}) for name in ("conversations", "messages", "feedback")}
    except PyMongoError:
        return None
