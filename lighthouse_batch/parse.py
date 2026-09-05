"""Extract category scores and CWV metrics from a Lighthouse or PSI JSON.

Invent-guard:
- Category scores come only from lighthouseResult.categories.<id>.score
- Lighthouse scores are 0–1; we emit 0–100. Anything else → null.
- Metrics come only from audits.<id>.numericValue. Missing → null.
- Never parse displayValue strings. Never fill defaults. Never guess.
"""

from __future__ import annotations

from typing import Any

from lighthouse_batch.categories import TO_SCHEMA
from lighthouse_batch.models import Categories, Metrics

AUDIT_TO_METRIC = {
    "largest-contentful-paint": "lcp_ms",
    "cumulative-layout-shift": "cls",
    "total-blocking-time": "tbt_ms",
    "first-contentful-paint": "fcp_ms",
    "speed-index": "si",
}


def extract_lhr(payload: Any) -> dict[str, Any] | None:
    """Return the Lighthouse result object, or None if this is not a report."""
    if not isinstance(payload, dict):
        return None
    inner = payload.get("lighthouseResult")
    if isinstance(inner, dict) and (
        "categories" in inner or "audits" in inner or inner.get("lighthouseVersion")
    ):
        return inner
    if "categories" in payload or payload.get("lighthouseVersion"):
        return payload
    return None


def score_to_100(raw: Any) -> float | None:
    """Convert a Lighthouse category score (0–1) to 0–100. Never invent."""
    if raw is None or isinstance(raw, bool):
        return None
    if not isinstance(raw, (int, float)):
        return None
    value = float(raw)
    if value != value:  # NaN
        return None
    if value < 0 or value > 1:
        return None
    return round(value * 100, 1)


def numeric_or_none(raw: Any) -> float | None:
    if raw is None or isinstance(raw, bool):
        return None
    if not isinstance(raw, (int, float)):
        return None
    value = float(raw)
    if value != value:
        return None
    return value


def parse_categories(lhr: dict[str, Any], wanted: list[str] | None = None) -> Categories:
    cats_raw = lhr.get("categories")
    cats = cats_raw if isinstance(cats_raw, dict) else {}
    wanted_ids = set(wanted) if wanted else set(TO_SCHEMA.keys())
    fields: dict[str, float | None] = {
        "performance": None,
        "accessibility": None,
        "best_practices": None,
        "seo": None,
    }
    for lh_id, schema_key in TO_SCHEMA.items():
        if wanted is not None and lh_id not in wanted_ids:
            fields[schema_key] = None
            continue
        entry = cats.get(lh_id)
        if not isinstance(entry, dict):
            fields[schema_key] = None
            continue
        fields[schema_key] = score_to_100(entry.get("score"))
    return Categories(**fields)


def parse_metrics(lhr: dict[str, Any]) -> Metrics:
    audits_raw = lhr.get("audits")
    audits = audits_raw if isinstance(audits_raw, dict) else {}
    fields: dict[str, float | None] = {
        "lcp_ms": None,
        "cls": None,
        "tbt_ms": None,
        "fcp_ms": None,
        "si": None,
    }
    for audit_id, metric_key in AUDIT_TO_METRIC.items():
        entry = audits.get(audit_id)
        if not isinstance(entry, dict):
            fields[metric_key] = None
            continue
        fields[metric_key] = numeric_or_none(entry.get("numericValue"))
    return Metrics(**fields)


def parse_report(
    payload: Any, wanted: list[str] | None = None
) -> tuple[Categories, Metrics] | None:
    lhr = extract_lhr(payload)
    if lhr is None:
        return None
    return parse_categories(lhr, wanted=wanted), parse_metrics(lhr)
