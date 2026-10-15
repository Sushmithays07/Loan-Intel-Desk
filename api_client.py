"""HTTP client used by every Streamlit page. Streamlit never touches MongoDB or the model directly."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")

PREDICT_TIMEOUT = 15
DEFAULT_TIMEOUT = 10


class ApiError(Exception):
    """A user-friendly error. `kind` is one of: connection, timeout, validation, server, client, invalid_response."""

    def __init__(self, message: str, kind: str = "server", status_code: int | None = None):
        super().__init__(message)
        self.message = message
        self.kind = kind
        self.status_code = status_code


def base_url() -> str:
    return os.getenv("API_BASE_URL", "http://127.0.0.1:8000").rstrip("/")


def _format_validation(detail: Any) -> str:
    if isinstance(detail, list):
        parts = []
        for d in detail:
            loc = ".".join(str(x) for x in d.get("loc", []) if x != "body")
            parts.append(f"{loc}: {d.get('msg', 'invalid value')}")
        return "Please correct these fields - " + "; ".join(parts)
    return str(detail)


def _request(method: str, path: str, timeout: int = DEFAULT_TIMEOUT, **kwargs) -> Any:
    url = f"{base_url()}{path}"
    try:
        resp = requests.request(method, url, timeout=timeout, **kwargs)
    except requests.exceptions.ConnectionError:
        raise ApiError(f"Cannot reach the backend at {base_url()}. Start it with: "
                       "uvicorn backend.main:app --host 127.0.0.1 --port 8000", kind="connection")
    except requests.exceptions.Timeout:
        raise ApiError("The backend took too long to respond. Please try again.", kind="timeout")
    except requests.exceptions.RequestException:
        raise ApiError("Unexpected network error while contacting the backend.", kind="connection")

    if resp.status_code >= 400:
        try:
            detail = resp.json().get("detail", "")
        except ValueError:
            detail = ""
        if resp.status_code == 422:
            raise ApiError(_format_validation(detail) or "Invalid input.", "validation", 422)
        if resp.status_code >= 500 or resp.status_code == 503:
            raise ApiError(str(detail) or "The server reported an error.", "server", resp.status_code)
        raise ApiError(str(detail) or f"Request failed ({resp.status_code}).", "client", resp.status_code)

    try:
        return resp.json()
    except ValueError:
        raise ApiError("The backend returned an invalid (non-JSON) response.", kind="invalid_response")


def get_health() -> dict:
    return _request("GET", "/health", timeout=5)


def predict(payload: dict) -> dict:
    return _request("POST", "/predict", timeout=PREDICT_TIMEOUT, json=payload)


def get_history(page: int = 1, page_size: int = 10, status: str | None = None, search: str | None = None) -> dict:
    params: dict[str, Any] = {"page": page, "page_size": page_size}
    if status:
        params["status"] = status
    if search:
        params["search"] = search
    return _request("GET", "/history", params=params)


def get_history_item(application_id: str) -> dict:
    return _request("GET", f"/history/{application_id}")


def get_analytics(days: int = 7) -> dict:
    return _request("GET", "/analytics", params={"days": days})


def get_model_info() -> dict:
    return _request("GET", "/model-info")
