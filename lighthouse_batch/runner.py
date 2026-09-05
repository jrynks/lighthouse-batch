"""Batch orchestration: PSI first (if keyed), 429 → backoff → local fallback."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from lighthouse_batch.config import Config
from lighthouse_batch.local import LocalLighthouseError, lighthouse_available, run_local
from lighthouse_batch.models import Categories, Metrics, UrlResult
from lighthouse_batch.output import iso_now, stamp_now, write_raw, write_summary, write_url_result, build_summary
from lighthouse_batch.parse import parse_report
from lighthouse_batch.psi import PsiClient, PsiError
from lighthouse_batch.urls import normalize_url

MAX_PSI_ATTEMPTS = 3


def _backoff(attempt: int, retry_after: float | None) -> float:
    if retry_after is not None:
        return min(max(0.0, retry_after), 60.0)
    return min(2 ** attempt, 16)


class Runner:
    def __init__(
        self,
        config: Config,
        *,
        categories: list[str],
        keep_raw: bool = False,
        psi_client: PsiClient | None = None,
        local_fn: Callable[..., dict[str, Any]] | None = None,
        sleep: Callable[[float], None] | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self.config = config
        self.categories = categories
        self.keep_raw = keep_raw
        self.psi_client = psi_client
        self.local_fn = local_fn or run_local
        self.sleep = sleep or __import__("time").sleep
        self.clock = clock or (lambda: datetime.now().astimezone())

    def _now(self) -> str:
        return iso_now(self.clock())

    def _empty(self, url: str, status: str, error: str | None, source: str | None = None) -> UrlResult:
        return UrlResult(
            url=url,
            strategy=self.config.strategy,
            source=source,
            categories=Categories(),
            metrics=Metrics(),
            fetched_at=self._now(),
            status=status,
            error=error,
            raw_path=None,
        )

    def _from_payload(
        self,
        url: str,
        payload: Any,
        source: str,
        raw_path: str | None,
    ) -> UrlResult:
        parsed = parse_report(payload, wanted=self.categories)
        if parsed is None:
            return self._empty(
                url,
                "FAILED",
                "report did not contain a Lighthouse result; scores not invented",
                source=source,
            )
        cats, metrics = parsed
        return UrlResult(
            url=url,
            strategy=self.config.strategy,
            source=source,
            categories=cats,
            metrics=metrics,
            fetched_at=self._now(),
            status="OK",
            error=None,
            raw_path=raw_path,
        )

    def _try_psi(self, url: str) -> tuple[dict[str, Any] | None, PsiError | None]:
        if self.psi_client is None:
            return None, None
        last: PsiError | None = None
        for attempt in range(MAX_PSI_ATTEMPTS):
            try:
                return self.psi_client.fetch(
                    url, strategy=self.config.strategy, categories=self.categories
                ), None
            except PsiError as exc:
                last = exc
                if not exc.fallback:
                    return None, exc
                if attempt < MAX_PSI_ATTEMPTS - 1 and (exc.quota or (exc.status or 0) >= 500 or exc.status == 429):
                    self.sleep(_backoff(attempt, exc.retry_after))
                    continue
                return None, exc
        return None, last

    def _try_local(self, url: str) -> tuple[dict[str, Any] | None, str | None]:
        try:
            return self.local_fn(
                url,
                strategy=self.config.strategy,
                categories=self.categories,
                timeout_sec=self.config.timeout_sec,
            ), None
        except LocalLighthouseError as exc:
            return None, str(exc)
        except Exception as exc:  # pragma: no cover - defensive
            return None, f"local lighthouse crashed: {exc}"

    def audit_one(self, url: str, *, index: int, out_dir: Path, stamp: str) -> UrlResult:
        normalized = normalize_url(url)
        if normalized is None:
            return self._empty(url, "SKIPPED", "not an http(s) URL")

        payload: dict[str, Any] | None = None
        source: str | None = None
        errors: list[str] = []

        if self.psi_client is not None:
            payload, psi_err = self._try_psi(normalized)
            if payload is not None:
                source = "psi"
            elif psi_err is not None:
                errors.append(f"psi: {psi_err}")
                if psi_err.fallback:
                    loc, loc_err = self._try_local(normalized)
                    if loc is not None:
                        payload, source = loc, "local_lighthouse"
                    elif loc_err:
                        errors.append(f"local_lighthouse: {loc_err}")
                # non-fallback PSI errors stay FAILED without local
        else:
            loc, loc_err = self._try_local(normalized)
            if loc is not None:
                payload, source = loc, "local_lighthouse"
            elif loc_err:
                errors.append(f"local_lighthouse: {loc_err}")

        if payload is None:
            if not errors:
                if self.psi_client is None and not lighthouse_available():
                    errors.append(
                        "no PSI API key configured and lighthouse CLI not found"
                    )
                else:
                    errors.append("audit produced no report")
            return self._empty(normalized, "FAILED", "; ".join(errors))

        raw_path = None
        if self.keep_raw:
            raw_path = str(write_raw(out_dir, normalized, index, payload, stamp))

        result = self._from_payload(normalized, payload, source or "psi", raw_path)
        return result

    def run(self, urls: list[str], *, out_dir: Path) -> tuple[list[UrlResult], Path]:
        out_dir.mkdir(parents=True, exist_ok=True)
        stamp = stamp_now(self.clock())
        results: list[UrlResult | None] = [None] * len(urls)

        def job(i: int, u: str) -> tuple[int, UrlResult]:
            return i, self.audit_one(u, index=i, out_dir=out_dir, stamp=stamp)

        if not urls:
            summary = build_summary([], strategy=self.config.strategy, generated_at=self._now())
            path = write_summary(out_dir, summary, stamp)
            return [], path

        workers = min(self.config.concurrency, len(urls))
        if workers <= 1:
            for i, u in enumerate(urls):
                results[i] = self.audit_one(u, index=i, out_dir=out_dir, stamp=stamp)
        else:
            with ThreadPoolExecutor(max_workers=workers) as pool:
                futs = [pool.submit(job, i, u) for i, u in enumerate(urls)]
                for fut in as_completed(futs):
                    i, res = fut.result()
                    results[i] = res

        final = [r for r in results if r is not None]
        for i, res in enumerate(final):
            write_url_result(out_dir, res, i)
        summary = build_summary(final, strategy=self.config.strategy, generated_at=self._now())
        path = write_summary(out_dir, summary, stamp)
        return final, path
