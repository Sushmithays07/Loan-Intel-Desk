"""Endpoint tests with an in-memory store (no MongoDB). Requires fastapi + httpx (see requirements.txt)."""
import importlib.util
import unittest
import warnings
from pathlib import Path

HAVE_DEPS = all(importlib.util.find_spec(m) for m in ("fastapi", "httpx", "pydantic"))
MODEL = Path(__file__).resolve().parent.parent / "model" / "loan_model.pkl"
VALID = dict(age=30, annual_income=600000, credit_score=700, loan_amount=300000, loan_term=60,
             existing_loans=0, existing_loan_amount=0, monthly_emi=0, dependents=0, savings=200000,
             employment_years=5, previous_defaults=0, assets=500000)


@unittest.skipUnless(HAVE_DEPS, "fastapi/httpx/pydantic not installed")
class ApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from fastapi.testclient import TestClient
        from backend.main import create_app
        from backend.prediction import ModelService
        from tests.fakes import DownStore, InMemoryStore
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            cls.svc = ModelService.load(MODEL)
        cls.create_app, cls.TestClient = create_app, TestClient
        cls.InMemoryStore, cls.DownStore = InMemoryStore, DownStore

    def client(self, store=None):
        return self.TestClient(self.create_app(model_service=self.svc, store=store or self.InMemoryStore()))

    def test_health(self):
        with self.client() as c:
            body = c.get("/health").json()
        self.assertEqual(body, {"status": "ok", "model_loaded": True, "database_connected": True})

    def test_valid_prediction_is_saved_and_in_history(self):
        with self.client() as c:
            r = c.post("/predict", json=VALID)
            self.assertEqual(r.status_code, 200)
            b = r.json()
            self.assertTrue(b["storage"]["saved"])
            self.assertTrue(b["application_id"].startswith("LID-"))
            self.assertAlmostEqual(b["approval_probability"] + b["rejection_probability"], 1.0)
            self.assertEqual(list(b["model_features"]), self.svc.feature_names)
            h = c.get("/history").json()
            self.assertEqual(h["total"], 1)
            self.assertEqual(h["items"][0]["application_id"], b["application_id"])
            self.assertEqual(c.get(f"/history/{b['application_id']}").status_code, 200)
            self.assertEqual(c.get("/history/NOPE").status_code, 404)
            self.assertEqual(c.get("/analytics").json()["total"], 1)

    def test_missing_fields(self):
        bad = {k: v for k, v in VALID.items() if k != "credit_score"}
        with self.client() as c:
            self.assertEqual(c.post("/predict", json=bad).status_code, 422)

    def test_invalid_values(self):
        with self.client() as c:
            for patch in ({"credit_score": 950}, {"credit_score": 100}, {"loan_amount": -1},
                          {"annual_income": 0}, {"annual_income": -10}, {"age": 12}, {"unknown": 1}):
                r = c.post("/predict", json={**VALID, **patch})
                self.assertEqual(r.status_code, 422, patch)

    def test_database_down_prediction_reports_not_saved(self):
        with self.client(self.DownStore()) as c:
            r = c.post("/predict", json=VALID)
            self.assertEqual(r.status_code, 200)
            self.assertFalse(r.json()["storage"]["saved"])
            self.assertEqual(c.get("/history").status_code, 503)
            self.assertEqual(c.get("/analytics").status_code, 503)
            self.assertFalse(c.get("/health").json()["database_connected"])

    def test_empty_database(self):
        with self.client() as c:
            h = c.get("/history").json()
            self.assertEqual((h["items"], h["total"], h["total_pages"]), ([], 0, 1))
            a = c.get("/analytics").json()
            self.assertEqual((a["total"], a["approval_rate"]), (0, None))

    def test_history_filters_and_pagination(self):
        with self.client() as c:
            for _ in range(3):
                c.post("/predict", json=VALID)
            self.assertEqual(len(c.get("/history", params={"page_size": 2}).json()["items"]), 2)
            self.assertEqual(c.get("/history", params={"page_size": 2}).json()["total_pages"], 2)
            self.assertEqual(c.get("/history", params={"status": "bogus"}).status_code, 422)

    def test_model_info(self):
        with self.client() as c:
            b = c.get("/model-info").json()
        self.assertEqual(b["feature_names"], self.svc.feature_names)
        self.assertEqual(b["model_type"], "DecisionTreeClassifier")

    def test_model_not_loaded_returns_503(self):
        with self.client() as c:
            c.app.state.model_service = None
            self.assertEqual(c.post("/predict", json=VALID).status_code, 503)
            self.assertFalse(c.get("/health").json()["model_loaded"])


if __name__ == "__main__":
    unittest.main()
