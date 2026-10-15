"""Optional: fill MongoDB with demo history so the dashboard is not empty on stage.

Each record is a REAL model prediction on a row sampled from data/loan_dataset.csv (synthetic data).
Timestamps are spread over the last N days so the trend chart has a shape. Records are tagged
source="seed_demo" so the app labels them and they can be removed again.

Run from the project root:
    python -m scripts.seed_demo --count 150 --days 7
    python -m scripts.seed_demo --clear
"""
import argparse
import random
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

from backend.database import PredictionStore, StorageUnavailable
from backend.prediction import RAW_FIELDS, ModelService

ROOT = Path(__file__).resolve().parent.parent
INT_FIELDS = {"age", "credit_score", "loan_term", "existing_loans", "dependents", "employment_years", "previous_defaults"}


def main() -> None:
    load_dotenv(ROOT / ".env")
    ap = argparse.ArgumentParser()
    ap.add_argument("--count", type=int, default=150)
    ap.add_argument("--days", type=int, default=7)
    ap.add_argument("--clear", action="store_true", help="delete previously seeded records and exit")
    args = ap.parse_args()

    store = PredictionStore.from_env()
    try:
        if args.clear:
            print(f"Deleted {store.delete_seeded()} seeded records.")
            return
        svc = ModelService.load(ROOT / "model" / "loan_model.pkl")
        df = pd.read_csv(ROOT / "data" / "loan_dataset.csv").sample(n=args.count, random_state=42)
        rng = random.Random(42)
        now = datetime.now(timezone.utc)
        for _, row in df.iterrows():
            inputs = {k: (int(row[k]) if k in INT_FIELDS else float(row[k])) for k in RAW_FIELDS}
            r = svc.predict(inputs)
            created = now - timedelta(days=rng.uniform(0, args.days - 0.01), seconds=rng.randint(0, 3600))
            store.insert_prediction({
                "application_id": f"LID-{created:%Y%m%d}-{uuid.uuid4().hex[:8].upper()}",
                "created_at": created, "inputs": inputs,
                "prediction": r["prediction"], "prediction_label": r["prediction_label"],
                "approval_probability": r["approval_probability"], "rejection_probability": r["rejection_probability"],
                "ratios": r["ratios"], "model_version": svc.version, "source": "seed_demo",
            })
        print(f"Inserted {len(df)} seeded predictions spread over the last {args.days} days.")
    except StorageUnavailable as exc:
        raise SystemExit(f"Database problem: {exc} Check MONGODB_URI in .env and your Atlas network access.")


if __name__ == "__main__":
    main()
