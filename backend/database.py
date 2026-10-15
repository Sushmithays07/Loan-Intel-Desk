"""MongoDB access. One client is created per process and reused for every request."""
from __future__ import annotations

import logging
import os
import re
from datetime import datetime
from functools import wraps
from typing import Any

logger = logging.getLogger("loan_intel_desk.db")

try:
    from pymongo import ASCENDING, DESCENDING, MongoClient
    from pymongo.errors import DuplicateKeyError, PyMongoError
except ImportError:  # lets pure-logic tests run without pymongo installed
    MongoClient = None
    PyMongoError = Exception
    DuplicateKeyError = Exception
    ASCENDING, DESCENDING = 1, -1


class StorageUnavailable(Exception):
    """Database is not configured or not reachable. Message is safe to show to users."""


def _guard(fn):
    @wraps(fn)
    def wrapper(self, *args, **kwargs):
        try:
            return fn(self, *args, **kwargs)
        except StorageUnavailable:
            raise
        except PyMongoError as exc:
            # Log only the exception type: driver messages can contain host names / URIs.
            logger.error("MongoDB operation failed: %s", type(exc).__name__)
            raise StorageUnavailable("The database is currently unavailable.") from exc
    return wrapper


def to_json_safe(doc: dict[str, Any]) -> dict[str, Any]:
    """Drop ObjectId, turn datetimes into ISO-8601 strings."""
    out = {}
    for k, v in doc.items():
        if k == "_id":
            continue
        if isinstance(v, datetime):
            out[k] = v.isoformat()
        elif isinstance(v, dict):
            out[k] = to_json_safe(v)
        else:
            out[k] = v
    return out


class PredictionStore:
    def __init__(self, uri: str | None, db_name: str = "loan_intel_desk",
                 collection_name: str = "predictions", timeout_ms: int = 3000, client=None):
        self.uri = uri
        self.db_name = db_name
        self.collection_name = collection_name
        self.timeout_ms = timeout_ms
        self._client = client
        self._indexes_ready = False

    @classmethod
    def from_env(cls) -> "PredictionStore":
        return cls(
            uri=os.getenv("MONGODB_URI"),
            db_name=os.getenv("MONGODB_DB", "loan_intel_desk"),
            collection_name=os.getenv("MONGODB_COLLECTION", "predictions"),
        )

    # -- connection -------------------------------------------------------------
    def _collection(self):
        if self._client is None:
            if not self.uri:
                raise StorageUnavailable("MONGODB_URI is not configured.")
            if MongoClient is None:
                raise StorageUnavailable("pymongo is not installed.")
            # MongoClient is lazy: it does not connect until the first operation.
            self._client = MongoClient(self.uri, serverSelectionTimeoutMS=self.timeout_ms, tz_aware=True)
        return self._client[self.db_name][self.collection_name]

    def close(self):
        if self._client is not None:
            self._client.close()

    @_guard
    def ping(self) -> bool:
        self._collection()
        self._client.admin.command("ping")
        return True

    def is_available(self) -> bool:
        try:
            return self.ping()
        except StorageUnavailable:
            return False

    @_guard
    def ensure_indexes(self):
        col = self._collection()
        col.create_index([("application_id", ASCENDING)], unique=True, name="uniq_application_id")
        col.create_index([("created_at", DESCENDING)], name="created_at_desc")
        self._indexes_ready = True

    # -- writes -----------------------------------------------------------------
    @_guard
    def insert_prediction(self, doc: dict[str, Any]) -> None:
        if not self._indexes_ready:
            self.ensure_indexes()
        self._collection().insert_one(dict(doc))  # copy: insert_one adds _id to its argument

    @_guard
    def delete_seeded(self) -> int:
        return self._collection().delete_many({"source": "seed_demo"}).deleted_count

    # -- reads ------------------------------------------------------------------
    @_guard
    def list_predictions(self, page: int = 1, page_size: int = 10,
                         status: str | None = None, search: str | None = None):
        query: dict[str, Any] = {}
        if status == "approved":
            query["prediction"] = 1
        elif status == "rejected":
            query["prediction"] = 0
        if search:
            query["application_id"] = {"$regex": re.escape(search.strip()), "$options": "i"}
        col = self._collection()
        total = col.count_documents(query)
        cursor = (col.find(query).sort("created_at", DESCENDING)
                  .skip((page - 1) * page_size).limit(page_size))
        return [to_json_safe(d) for d in cursor], total

    @_guard
    def get_prediction(self, application_id: str):
        doc = self._collection().find_one({"application_id": application_id})
        return to_json_safe(doc) if doc else None

    @_guard
    def fetch_for_analytics(self, limit: int = 20000) -> list[dict[str, Any]]:
        projection = {"_id": 0, "created_at": 1, "prediction": 1, "source": 1,
                      "inputs.loan_amount": 1, "inputs.credit_score": 1, "inputs.loan_term": 1}
        return list(self._collection().find({}, projection).sort("created_at", DESCENDING).limit(limit))
