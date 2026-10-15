"""FastAPI backend for Loan Intel Desk.

Run from the project root:  uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
"""
from __future__ import annotations

import logging
import math
import os
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware

from backend.analytics import compute_analytics
from backend.database import PredictionStore, StorageUnavailable
from backend.prediction import ModelService, ModelUnavailable
from backend.schemas import HistoryResponse, LoanApplication, PredictionResponse

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("loan_intel_desk.api")

DISCLAIMER = ("Model output for demonstration only. It is not a real lending decision and has not been "
              "independently validated for banking use.")


def _load_model_service() -> Optional[ModelService]:
    path = os.getenv("MODEL_PATH", str(ROOT / "model" / "loan_model.pkl"))
    try:
        svc = ModelService.load(path)
        logger.info("Model loaded (%s)", svc.version)
        return svc
    except ModelUnavailable as exc:
        logger.error("Model not loaded: %s", exc)
        return None


def create_app(model_service: Optional[ModelService] = None, store=None) -> FastAPI:
    """App factory. Tests inject a fake store / model; production loads both from the environment."""

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.model_service = model_service or _load_model_service()   # loaded ONCE
        app.state.store = store or PredictionStore.from_env()               # one client, reused
        try:
            app.state.store.ensure_indexes()
        except StorageUnavailable as exc:
            logger.warning("Indexes not created at startup (%s). Will retry on first save.", exc)
        yield
        close = getattr(app.state.store, "close", None)
        if close:
            close()

    app = FastAPI(title="Loan Intel Desk API", version="1.0.0", lifespan=lifespan)

    origins = [o.strip() for o in os.getenv(
        "CORS_ORIGINS", "http://localhost:8501,http://127.0.0.1:8501").split(",") if o.strip()]
    app.add_middleware(CORSMiddleware, allow_origins=origins, allow_methods=["GET", "POST"],
                       allow_headers=["Content-Type"])

    def _model(request: Request) -> ModelService:
        svc = request.app.state.model_service
        if svc is None:
            raise HTTPException(503, "Model is not loaded. Check that model/loan_model.pkl exists "
                                     "(python model/train_model.py) and restart the backend.")
        return svc

    def _db_call(fn, *args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except StorageUnavailable as exc:
            raise HTTPException(503, f"Database unavailable: {exc}")

    @app.get("/health")
    def health(request: Request):
        db_ok = request.app.state.store.is_available()
        model_ok = request.app.state.model_service is not None
        return {"status": "ok" if (db_ok and model_ok) else "degraded",
                "model_loaded": model_ok, "database_connected": db_ok}

    @app.post("/predict", response_model=PredictionResponse)
    def predict(application: LoanApplication, request: Request):
        svc = _model(request)
        inputs = application.model_dump()
        try:
            result = svc.predict(inputs)
        except ValueError as exc:  # defensive: divisors already guarded by schema (gt=0)
            raise HTTPException(422, str(exc))
        except Exception:
            logger.exception("Prediction failed")
            raise HTTPException(500, "Prediction failed due to an internal error.")

        application_id = f"LID-{datetime.now(timezone.utc):%Y%m%d}-{uuid.uuid4().hex[:8].upper()}"
        created_at = datetime.now(timezone.utc)
        record = {
            "application_id": application_id,
            "created_at": created_at,
            "inputs": inputs,
            "prediction": result["prediction"],
            "prediction_label": result["prediction_label"],
            "approval_probability": result["approval_probability"],
            "rejection_probability": result["rejection_probability"],
            "ratios": result["ratios"],
            "model_version": svc.version,
            "source": "api",
        }
        try:
            request.app.state.store.insert_prediction(record)
            storage = {"saved": True, "message": "Prediction saved to MongoDB."}
        except StorageUnavailable as exc:
            storage = {"saved": False,
                       "message": f"Prediction was NOT saved: {exc} It will not appear in History or Analytics."}

        return {
            "application_id": application_id, "created_at": created_at,
            "prediction": result["prediction"], "prediction_label": result["prediction_label"],
            "approval_probability": result["approval_probability"],
            "rejection_probability": result["rejection_probability"],
            "ratios": result["ratios"], "model_features": result["model_features"],
            "model_version": svc.version, "storage": storage,
            "warnings": svc.range_warnings(inputs), "disclaimer": DISCLAIMER,
        }

    @app.get("/history", response_model=HistoryResponse)
    def history(request: Request, page: int = Query(1, ge=1), page_size: int = Query(10, ge=1, le=100),
                status: Optional[str] = Query(None, pattern="^(approved|rejected)$"),
                search: Optional[str] = Query(None, max_length=64)):
        docs, total = _db_call(request.app.state.store.list_predictions, page, page_size, status, search)
        items = [{
            "application_id": d["application_id"], "created_at": d["created_at"],
            "loan_amount": (d.get("inputs") or {}).get("loan_amount"),
            "credit_score": (d.get("inputs") or {}).get("credit_score"),
            "loan_term": (d.get("inputs") or {}).get("loan_term"),
            "prediction_label": d["prediction_label"],
            "approval_probability": d["approval_probability"],
        } for d in docs]
        return {"items": items, "total": total, "page": page, "page_size": page_size,
                "total_pages": max(1, math.ceil(total / page_size))}

    @app.get("/history/{application_id}")
    def history_item(application_id: str, request: Request):
        doc = _db_call(request.app.state.store.get_prediction, application_id[:64])
        if doc is None:
            raise HTTPException(404, "Application not found.")
        return doc

    @app.get("/analytics")
    def analytics(request: Request, days: int = Query(7, ge=1, le=90)):
        records = _db_call(request.app.state.store.fetch_for_analytics)
        return compute_analytics(records, days=days)

    @app.get("/model-info")
    def model_info(request: Request):
        return _model(request).info()

    return app


app = create_app()
