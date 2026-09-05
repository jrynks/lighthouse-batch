"""Write per-URL JSON + batch summary; render the short human table."""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from lighthouse_batch.models import BatchSummary, UrlResult, averages_from_ok

SAFE_URL = re.compile(r"[^a-zA-Z0-9._-]+")


def stamp_now(when: datetime | None = None) -> str:
    when = when or datetime.now()
    return when.strftime("%Y%m%d-%H%M%S")


def iso_now(when: datetime | None = None) -> str:
    dt = when or datetime.now().astimezone()
    return dt.isoformat(timespec="seconds")


def ensure_dir(path: str | Path) -> Path:
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def slug_url(url: str, index: int) -> str:
    trimmed = url.replace("https://", "").replace("http://", "")
    slug = SAFE_URL.sub("-", trimmed).strip("-")[:80] or "url"
    return f"{index:03d}-{slug}"


def write_url_result(out_dir: Path, result: UrlResult, index: int) -> Path:
    folder = ensure_dir(out_dir / "results")
    path = folder / f"{slug_url(result.url, index)}.json"
    path.write_text(json.dumps(result.to_dict(), indent=2) + "\n", encoding="utf-8")
    return path


def write_raw(out_dir: Path, url: str, index: int, payload: Any, stamp: str) -> Path:
    folder = ensure_dir(out_dir / "raw")
    path = folder / f"{stamp}-{slug_url(url, index)}.json"
    path.write_text(json.dumps(payload) + "\n", encoding="utf-8")
    return path


def write_summary(out_dir: Path, summary: BatchSummary, stamp: str) -> Path:
    ensure_dir(out_dir)
    path = out_dir / f"summary-{stamp}.json"
    summary.summary_path = str(path)
    summary.output_dir = str(out_dir)
    path.write_text(json.dumps(summary.to_dict(), indent=2) + "\n", encoding="utf-8")
    return path


def build_summary(
    results: list[UrlResult],
    *,
    strategy: str,
    generated_at: str,
) -> BatchSummary:
    ok = sum(1 for r in results if r.status == "OK")
    failed = sum(1 for r in results if r.status == "FAILED")
    skipped = sum(1 for r in results if r.status == "SKIPPED")
    return BatchSummary(
        generated_at=generated_at,
        strategy=strategy,
        total=len(results),
        ok=ok,
        failed=failed,
        skipped=skipped,
        results=[r.summary_row() for r in results],
        averages=averages_from_ok(results),
    )


def _cell(score: float | None) -> str:
    if score is None:
        return "   —"
    return f"{score:5.1f}"


def format_table(results: list[UrlResult]) -> str:
    if not results:
        return "(no results)"
    headers = ("URL", "PERF", "A11Y", "BP", "SEO", "SOURCE", "STATUS")
    rows: list[tuple[str, ...]] = []
    for r in results:
        source = r.source or "—"
        rows.append(
            (
                r.url,
                _cell(r.categories.performance).strip(),
                _cell(r.categories.accessibility).strip(),
                _cell(r.categories.best_practices).strip(),
                _cell(r.categories.seo).strip(),
                source,
                r.status,
            )
        )
    widths = [len(h) for h in headers]
    for row in rows:
        for i, col in enumerate(row):
            widths[i] = max(widths[i], len(col))
    widths[0] = min(max(widths[0], 12), 64)

    def fmt(row: tuple[str, ...]) -> str:
        cells = []
        for i, col in enumerate(row):
            if i == 0:
                cells.append(col[: widths[0]].ljust(widths[0]))
            elif i in (1, 2, 3, 4):
                cells.append(col.rjust(widths[i]))
            else:
                cells.append(col.ljust(widths[i]))
        return "  ".join(cells)

    lines = [fmt(headers), "  ".join("-" * w for w in widths)]
    lines.extend(fmt(row) for row in rows)
    return "\n".join(lines)


def format_summary_human(summary: BatchSummary) -> str:
    lines = [
        f"schema        {summary.schema}",
        f"generated_at  {summary.generated_at}",
        f"strategy      {summary.strategy}",
        f"total {summary.total}  ok {summary.ok}  failed {summary.failed}  skipped {summary.skipped}",
    ]
    if summary.averages:
        avg = summary.averages
        lines.append(
            "averages      "
            + "  ".join(
                f"{k}={v:.1f}"
                for k, v in avg.items()
            )
        )
    else:
        lines.append("averages      (omitted — zero OK runs with numeric scores)")
    if summary.summary_path:
        lines.append(f"summary_path  {summary.summary_path}")
    return "\n".join(lines)


def load_summary(path: str | Path) -> dict[str, Any]:
    p = Path(path)
    if not p.is_file():
        raise FileNotFoundError(f"run file not found: {p}")
    data = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("run file is not a JSON object")
    schema = data.get("schema")
    if schema not in ("lighthouse-batch/v1-summary", "lighthouse-batch/v1"):
        raise ValueError(f"unrecognized schema: {schema!r}")
    return data
