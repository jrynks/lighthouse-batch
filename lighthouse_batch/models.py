"""Typed result objects. Scores are only stored when a report provided them."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal

from lighthouse_batch import SCHEMA, SCHEMA_SUMMARY

Strategy = Literal["mobile", "desktop"]
Source = Literal["psi", "local_lighthouse"]
Status = Literal["OK", "FAILED", "SKIPPED"]

CATEGORY_KEYS = ("performance", "accessibility", "best_practices", "seo")
METRIC_KEYS = ("lcp_ms", "cls", "tbt_ms", "fcp_ms", "si")


def _clean(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: _clean(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_clean(v) for v in value]
    return value


@dataclass
class Categories:
    performance: float | None = None
    accessibility: float | None = None
    best_practices: float | None = None
    seo: float | None = None

    def to_dict(self) -> dict[str, float | None]:
        return {
            "performance": self.performance,
            "accessibility": self.accessibility,
            "best_practices": self.best_practices,
            "seo": self.seo,
        }

    def numeric_values(self) -> dict[str, float]:
        return {k: v for k, v in self.to_dict().items() if isinstance(v, (int, float))}


@dataclass
class Metrics:
    lcp_ms: float | None = None
    cls: float | None = None
    tbt_ms: float | None = None
    fcp_ms: float | None = None
    si: float | None = None

    def to_dict(self) -> dict[str, float | None]:
        return {
            "lcp_ms": self.lcp_ms,
            "cls": self.cls,
            "tbt_ms": self.tbt_ms,
            "fcp_ms": self.fcp_ms,
            "si": self.si,
        }


@dataclass
class UrlResult:
    url: str
    strategy: str
    source: str | None
    categories: Categories
    metrics: Metrics
    fetched_at: str
    status: str
    error: str | None = None
    raw_path: str | None = None
    schema: str = SCHEMA

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "schema": self.schema,
            "url": self.url,
            "strategy": self.strategy,
            "source": self.source,
            "categories": self.categories.to_dict(),
            "metrics": self.metrics.to_dict(),
            "fetched_at": self.fetched_at,
            "status": self.status,
            "error": self.error,
            "raw_path": self.raw_path,
        }
        return _clean(payload)

    def summary_row(self) -> dict[str, Any]:
        return {
            "url": self.url,
            "status": self.status,
            "categories": self.categories.to_dict(),
            "source": self.source,
        }


@dataclass
class BatchSummary:
    generated_at: str
    strategy: str
    total: int
    ok: int
    failed: int
    skipped: int
    results: list[dict[str, Any]] = field(default_factory=list)
    averages: dict[str, float] | None = None
    schema: str = SCHEMA_SUMMARY
    output_dir: str | None = None
    summary_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": self.schema,
            "generated_at": self.generated_at,
            "strategy": self.strategy,
            "total": self.total,
            "ok": self.ok,
            "failed": self.failed,
            "skipped": self.skipped,
            "results": self.results,
        }
        if self.averages:
            payload["averages"] = self.averages
        if self.output_dir:
            payload["output_dir"] = self.output_dir
        if self.summary_path:
            payload["summary_path"] = self.summary_path
        return payload


def averages_from_ok(results: list[UrlResult]) -> dict[str, float] | None:
    """Averages only over OK runs with numeric scores. Omit if zero OK."""
    ok = [r for r in results if r.status == "OK"]
    if not ok:
        return None
    out: dict[str, float] = {}
    for key in CATEGORY_KEYS:
        vals = [
            getattr(r.categories, key)
            for r in ok
            if isinstance(getattr(r.categories, key), (int, float))
        ]
        if vals:
            out[key] = round(sum(vals) / len(vals), 1)
    return out or None
