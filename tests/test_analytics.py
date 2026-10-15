import unittest
from datetime import datetime, timedelta, timezone

from backend.analytics import compute_analytics
from backend.database import PredictionStore, StorageUnavailable, to_json_safe

NOW = datetime(2026, 10, 9, 12, 0, tzinfo=timezone.utc)


def rec(days_ago, pred, **inputs):
    return {"created_at": NOW - timedelta(days=days_ago), "prediction": pred,
            "inputs": {"loan_amount": 1e5, "credit_score": 700, "loan_term": 60, **inputs}}


class AnalyticsTests(unittest.TestCase):
    def test_empty_database(self):
        s = compute_analytics([], days=7, now=NOW)
        self.assertEqual((s["total"], s["approved"], s["rejected"]), (0, 0, 0))
        self.assertIsNone(s["approval_rate"])
        self.assertEqual(len(s["trend"]), 7)
        self.assertTrue(all(d["applications"] == 0 for d in s["trend"]))
        self.assertEqual(s["distributions"]["loan_term"], {})

    def test_counts_rate_and_trend(self):
        s = compute_analytics([rec(0, 1), rec(0, 0), rec(1, 1), rec(30, 1)], days=7, now=NOW)
        self.assertEqual((s["total"], s["approved"], s["rejected"]), (4, 3, 1))
        self.assertEqual(s["approval_rate"], 75.0)
        self.assertEqual(s["trend"][-1], {"date": "2026-10-09", "applications": 2, "approved": 1, "rejected": 1})
        self.assertEqual(sum(d["applications"] for d in s["trend"]), 3)  # 30-day-old record is outside 7 days

    def test_term_distribution_sorted(self):
        s = compute_analytics([rec(0, 1, loan_term=120), rec(0, 1, loan_term=12), rec(0, 0, loan_term=12)], now=NOW)
        self.assertEqual(s["distributions"]["loan_term"], {"12": 2, "120": 1})

    def test_to_json_safe_removes_objectid_and_formats_datetime(self):
        out = to_json_safe({"_id": object(), "created_at": NOW, "inputs": {"x": 1}})
        self.assertNotIn("_id", out)
        self.assertIsInstance(out["created_at"], str)

    def test_store_without_uri_reports_unavailable(self):
        store = PredictionStore(uri=None)
        self.assertFalse(store.is_available())
        with self.assertRaises(StorageUnavailable):
            store.insert_prediction({"application_id": "x"})


if __name__ == "__main__":
    unittest.main()
