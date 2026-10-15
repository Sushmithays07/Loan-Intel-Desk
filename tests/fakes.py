from datetime import datetime, timezone

from backend.database import StorageUnavailable, to_json_safe


class InMemoryStore:
    """Same interface as PredictionStore, no MongoDB needed."""
    def __init__(self):
        self.docs = []

    def ensure_indexes(self): pass
    def is_available(self): return True
    def close(self): pass

    def insert_prediction(self, doc):
        if any(d["application_id"] == doc["application_id"] for d in self.docs):
            raise ValueError("duplicate application_id")
        self.docs.append(dict(doc))

    def list_predictions(self, page=1, page_size=10, status=None, search=None):
        docs = sorted(self.docs, key=lambda d: d["created_at"], reverse=True)
        if status:
            docs = [d for d in docs if d["prediction"] == (1 if status == "approved" else 0)]
        if search:
            docs = [d for d in docs if search.lower() in d["application_id"].lower()]
        total = len(docs)
        return [to_json_safe(d) for d in docs[(page - 1) * page_size: page * page_size]], total

    def get_prediction(self, application_id):
        return next((to_json_safe(d) for d in self.docs if d["application_id"] == application_id), None)

    def fetch_for_analytics(self, limit=20000):
        return list(self.docs)


class DownStore(InMemoryStore):
    """Simulates MongoDB being unreachable."""
    def is_available(self): return False
    def ensure_indexes(self): raise StorageUnavailable("The database is currently unavailable.")
    def insert_prediction(self, doc): raise StorageUnavailable("The database is currently unavailable.")
    def list_predictions(self, *a, **k): raise StorageUnavailable("The database is currently unavailable.")
    def get_prediction(self, *a, **k): raise StorageUnavailable("The database is currently unavailable.")
    def fetch_for_analytics(self, *a, **k): raise StorageUnavailable("The database is currently unavailable.")
