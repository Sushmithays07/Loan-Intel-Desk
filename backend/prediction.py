"""Model service: loads the saved Decision Tree ONCE and wraps predict()/predict_proba().

No hardcoded rules live here. The feature engineering formulas are the same as the
original Streamlit app.py. The model schema is verified against model.feature_names_in_.
"""
from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path
from typing import Any

import joblib
import pandas as pd

logger = logging.getLogger("loan_intel_desk.model")

# Exact feature order used when the saved model was trained (see train_model.py).
EXPECTED_FEATURES = [
    "age", "annual_income", "credit_score", "loan_amount", "loan_term",
    "existing_loans", "existing_loan_amount", "monthly_emi", "dependents",
    "savings", "employment_years", "previous_defaults", "assets",
    "dti", "loan_income_ratio", "savings_loan_ratio",
]
RAW_FIELDS = EXPECTED_FEATURES[:13]
ENGINEERED_FIELDS = EXPECTED_FEATURES[13:]


class ModelUnavailable(Exception):
    """Raised when the model file is missing or does not match the expected schema."""


def compute_engineered_features(inputs: dict[str, Any]) -> dict[str, float]:
    """dti, loan_income_ratio, savings_loan_ratio - same formulas as the original app.

    Raises ValueError if a divisor is not strictly positive.
    """
    income = float(inputs["annual_income"])
    loan = float(inputs["loan_amount"])
    if not income > 0:
        raise ValueError("annual_income must be greater than 0")
    if not loan > 0:
        raise ValueError("loan_amount must be greater than 0")
    return {
        "dti": float(inputs["existing_loan_amount"]) / income,
        "loan_income_ratio": loan / income,
        "savings_loan_ratio": float(inputs["savings"]) / loan,
    }


class ModelService:
    def __init__(self, model, model_path: Path, metrics: dict | None = None):
        names = list(getattr(model, "feature_names_in_", []))
        if names != EXPECTED_FEATURES:
            raise ModelUnavailable(
                "Model feature schema does not match the expected 16 features.\n"
                f"Model has: {names}"
            )
        classes = list(model.classes_)
        if 0 not in classes or 1 not in classes:
            raise ModelUnavailable(f"Model classes must include 0 and 1, got {classes}")
        self.model = model
        self.model_path = Path(model_path)
        self.feature_names = names
        self.metrics = metrics
        digest = hashlib.sha256(self.model_path.read_bytes()).hexdigest()[:8]
        self.version = f"decision_tree-{digest}"

    @classmethod
    def load(cls, model_path: str | Path, metrics_path: str | Path | None = None) -> "ModelService":
        model_path = Path(model_path)
        if not model_path.exists():
            raise ModelUnavailable(
                f"Model file not found: {model_path}. Generate it with: python model/train_model.py"
            )
        try:
            model = joblib.load(model_path)
        except Exception as exc:  # corrupt file / incompatible scikit-learn version
            raise ModelUnavailable(f"Could not load model file ({type(exc).__name__}).") from exc
        metrics = None
        mp = Path(metrics_path) if metrics_path else model_path.with_name("metrics.json")
        if mp.exists():
            try:
                metrics = json.loads(mp.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                logger.warning("metrics.json exists but could not be read")
        return cls(model, model_path, metrics)

    def predict(self, inputs: dict[str, Any]) -> dict[str, Any]:
        engineered = compute_engineered_features(inputs)
        row = {name: inputs[name] for name in RAW_FIELDS}
        row.update(engineered)
        X = pd.DataFrame([row])[self.feature_names]  # enforce exact column order

        label = int(self.model.predict(X)[0])
        proba = self.model.predict_proba(X)[0]
        classes = list(self.model.classes_)
        approval = float(proba[classes.index(1)])
        rejection = float(proba[classes.index(0)])
        return {
            "prediction": label,
            "prediction_label": "Approved" if label == 1 else "Rejected",
            "approval_probability": approval,
            "rejection_probability": rejection,
            "ratios": engineered,
            "model_features": {k: float(X.iloc[0][k]) for k in self.feature_names},
        }

    def range_warnings(self, inputs: dict[str, Any]) -> list[str]:
        """Flag inputs outside the range seen in training data (the tree extrapolates there)."""
        ranges = (self.metrics or {}).get("training_ranges") or {}
        out = []
        for name, (lo, hi) in ranges.items():
            v = inputs.get(name)
            if v == 0 and lo >= 0:  # 0 simply means "none" (no EMI, no savings, ...)
                continue
            if v is not None and not (lo <= float(v) <= hi):
                out.append(f"{name} = {v:g} is outside the training data range ({lo:g} to {hi:g}); "
                           "the prediction is less reliable.")
        return out

    def feature_importances(self) -> dict[str, float]:
        return {n: float(v) for n, v in zip(self.feature_names, self.model.feature_importances_)}

    def info(self) -> dict[str, Any]:
        m = self.model
        return {
            "model_type": type(m).__name__,
            "model_version": self.version,
            "feature_names": self.feature_names,
            "classes": [int(c) for c in m.classes_],
            "depth": int(m.get_depth()),
            "n_leaves": int(m.get_n_leaves()),
            "hyperparameters": {
                "max_depth": m.max_depth,
                "min_samples_leaf": m.min_samples_leaf,
                "criterion": m.criterion,
            },
            "feature_importances": self.feature_importances(),
            "metrics": self.metrics,  # None when model/metrics.json is absent
        }
