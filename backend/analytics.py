"""Pure functions that turn stored prediction records into dashboard statistics."""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Any

MAX_DISTRIBUTION_POINTS = 5000


def _as_utc(dt: datetime) -> datetime:
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt.astimezone(timezone.utc)


def compute_analytics(records: list[dict[str, Any]], days: int = 7, now: datetime | None = None) -> dict[str, Any]:
    now = _as_utc(now) if now else datetime.now(timezone.utc)
    total = len(records)
    approved = sum(1 for r in records if r.get("prediction") == 1)
    rejected = total - approved
    seeded = sum(1 for r in records if r.get("source") == "seed_demo")

    today = now.date()
    buckets = {today - timedelta(days=i): {"applications": 0, "approved": 0} for i in range(days)}
    for r in records:
        created = r.get("created_at")
        if not isinstance(created, datetime):
            continue
        b = buckets.get(_as_utc(created).date())
        if b is not None:
            b["applications"] += 1
            b["approved"] += 1 if r.get("prediction") == 1 else 0
    trend = [
        {"date": d.isoformat(), "applications": v["applications"], "approved": v["approved"],
         "rejected": v["applications"] - v["approved"]}
        for d, v in sorted(buckets.items())
    ]

    loan_amounts, credit_scores, terms = [], [], Counter()
    for r in records[:MAX_DISTRIBUTION_POINTS]:
        inp = r.get("inputs") or {}
        if "loan_amount" in inp:
            loan_amounts.append(inp["loan_amount"])
        if "credit_score" in inp:
            credit_scores.append(inp["credit_score"])
    for r in records:
        t = (r.get("inputs") or {}).get("loan_term")
        if t is not None:
            terms[str(t)] += 1

    return {
        "total": total,
        "approved": approved,
        "rejected": rejected,
        "approval_rate": round(100 * approved / total, 2) if total else None,
        "seeded_count": seeded,
        "days": days,
        "trend": trend,
        "distributions": {
            "loan_amount": loan_amounts,
            "credit_score": credit_scores,
            "loan_term": dict(sorted(terms.items(), key=lambda kv: int(kv[0]))),
        },
    }
