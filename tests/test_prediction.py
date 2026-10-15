import unittest
import warnings
from pathlib import Path

import pandas as pd

from backend.prediction import (EXPECTED_FEATURES, ModelService, ModelUnavailable,
                                compute_engineered_features)

MODEL = Path(__file__).resolve().parent.parent / "model" / "loan_model.pkl"
VALID = dict(age=30, annual_income=600000.0, credit_score=700, loan_amount=300000.0, loan_term=60,
             existing_loans=0, existing_loan_amount=0.0, monthly_emi=0.0, dependents=0, savings=200000.0,
             employment_years=5, previous_defaults=0, assets=500000.0)


class PredictionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            cls.svc = ModelService.load(MODEL)

    def test_model_schema_matches_expected_16_features(self):
        self.assertEqual(self.svc.feature_names, EXPECTED_FEATURES)
        self.assertEqual(len(EXPECTED_FEATURES), 16)

    def test_engineered_features(self):
        f = compute_engineered_features({**VALID, "existing_loan_amount": 120000.0})
        self.assertAlmostEqual(f["dti"], 0.2)
        self.assertAlmostEqual(f["loan_income_ratio"], 0.5)
        self.assertAlmostEqual(f["savings_loan_ratio"], 200000 / 300000)

    def test_zero_or_negative_divisors_rejected(self):
        for field in ("annual_income", "loan_amount"):
            for bad in (0, -5):
                with self.assertRaises(ValueError):
                    compute_engineered_features({**VALID, field: bad})

    def test_feature_order_sent_to_model(self):
        r = self.svc.predict(VALID)
        self.assertEqual(list(r["model_features"].keys()), EXPECTED_FEATURES)

    def test_probabilities_valid_and_consistent_with_label(self):
        r = self.svc.predict(VALID)
        for p in (r["approval_probability"], r["rejection_probability"]):
            self.assertGreaterEqual(p, 0.0)
            self.assertLessEqual(p, 1.0)
        self.assertAlmostEqual(r["approval_probability"] + r["rejection_probability"], 1.0)
        self.assertEqual(r["prediction"], 1 if r["approval_probability"] > 0.5 else 0)

    def test_matches_direct_model_call_like_original_app(self):
        """Reproduces the original app.py logic and compares."""
        r = self.svc.predict(VALID)
        row = {**VALID, **compute_engineered_features(VALID)}
        X = pd.DataFrame([row])[list(self.svc.model.feature_names_in_)]
        self.assertEqual(r["prediction"], int(self.svc.model.predict(X)[0]))
        self.assertAlmostEqual(r["approval_probability"], float(self.svc.model.predict_proba(X)[0][1]))

    def test_strong_and_weak_applicants_differ(self):
        strong = self.svc.predict({**VALID, "credit_score": 850, "loan_amount": 100000.0})
        weak = self.svc.predict({**VALID, "credit_score": 350, "loan_amount": 2500000.0,
                                 "previous_defaults": 2, "savings": 1000.0})
        self.assertGreater(strong["approval_probability"], weak["approval_probability"])

    def test_missing_model_file(self):
        with self.assertRaises(ModelUnavailable):
            ModelService.load(MODEL.with_name("does_not_exist.pkl"))

    def test_wrong_schema_rejected(self):
        class Fake:
            feature_names_in_ = ["a", "b"]
            classes_ = [0, 1]
        with self.assertRaises(ModelUnavailable):
            ModelService(Fake(), MODEL)

    def test_range_warning_outside_training_data(self):
        self.assertEqual(self.svc.range_warnings(VALID), [])
        self.assertTrue(self.svc.range_warnings({**VALID, "annual_income": 9e9}))


if __name__ == "__main__":
    unittest.main()
