"""PageSpeed Insights client. Retries 429/5xx; never invents a body on failure."""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Callable

from lighthouse_batch.categories import PSI_CATEGORY

PSI_ENDPOINT = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"
USER_AGENT = "lighthouse-batch/1.0 (+https://github.com/jrynks/lighthouse-batch)"


class PsiError(Exception):
    def __init__(
        self,
        message: str,
        *,
        status: int | None = None,
        retry_after: float | None = None,
        quota: bool = False,
        fallback: bool = False,
        body: Any = None,
    ) -> None:
        super().__init__(message)
        self.status = status
        self.retry_after = retry_after
        self.quota = quota
        self.fallback = fallback
        self.body = body


def _parse_retry_after(header: str | None) -> float | None:
    if not header:
        return None
    header = header.strip()
    try:
        return max(0.0, float(header))
    except ValueError:
        return None


def _quotaish(status: int | None, payload: Any) -> bool:
    if status == 429:
        return True
    text = ""
    if isinstance(payload, dict):
        err = payload.get("error") if isinstance(payload.get("error"), dict) else payload
        text = json.dumps(err)
    else:
        text = str(payload or "")
    lowered = text.lower()
    return any(
        token in lowered
        for token in (
            "rate limit",
            "quota",
            "resource_exhausted",
            "ratelimitexceeded",
            "user_rate_limit",
        )
    )


class PsiClient:
    def __init__(
        self,
        api_key: str | None,
        *,
        opener: Callable[..., Any] | None = None,
        timeout: int = 120,
    ) -> None:
        self.api_key = api_key
        self._opener = opener or urllib.request.urlopen
        self.timeout = timeout

    def fetch(
        self,
        url: str,
        *,
        strategy: str,
        categories: list[str],
    ) -> dict[str, Any]:
        params: list[tuple[str, str]] = [
            ("url", url),
            ("strategy", strategy),
        ]
        for cat in categories:
            params.append(("category", PSI_CATEGORY.get(cat, cat.upper())))
        if self.api_key:
            params.append(("key", self.api_key))
        endpoint = f"{PSI_ENDPOINT}?{urllib.parse.urlencode(params)}"
        req = urllib.request.Request(endpoint, headers={"User-Agent": USER_AGENT})
        try:
            with self._opener(req, timeout=self.timeout) as resp:
                status = getattr(resp, "status", 200)
                raw = resp.read()
        except urllib.error.HTTPError as exc:
            raw = exc.read() if exc.fp else b""
            payload = _decode_json(raw)
            retry_after = _parse_retry_after(exc.headers.get("Retry-After") if exc.headers else None)
            quota = _quotaish(exc.code, payload)
            fallback = quota or (exc.code >= 500) or exc.code in (401, 403, 429)
            message = _error_message(payload) or f"PSI HTTP {exc.code}"
            raise PsiError(
                message,
                status=exc.code,
                retry_after=retry_after,
                quota=quota,
                fallback=fallback,
                body=payload,
            ) from exc
        except urllib.error.URLError as exc:
            raise PsiError(
                f"PSI network error: {exc.reason}",
                fallback=True,
            ) from exc
        except TimeoutError as exc:
            raise PsiError("PSI timed out", fallback=True) from exc

        payload = _decode_json(raw)
        if not isinstance(payload, dict):
            raise PsiError("PSI returned non-JSON", fallback=True)
        if "error" in payload and "lighthouseResult" not in payload:
            err = payload.get("error")
            status = err.get("code") if isinstance(err, dict) else status
            quota = _quotaish(status if isinstance(status, int) else None, payload)
            raise PsiError(
                _error_message(payload) or "PSI error",
                status=status if isinstance(status, int) else None,
                quota=quota,
                fallback=quota or (isinstance(status, int) and status >= 500),
                body=payload,
            )
        if "lighthouseResult" not in payload:
            raise PsiError(
                "PSI response missing lighthouseResult",
                fallback=False,
                body=payload,
            )
        return payload


def _decode_json(raw: bytes) -> Any:
    if not raw:
        return None
    try:
        return json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None


def _error_message(payload: Any) -> str | None:
    if not isinstance(payload, dict):
        return None
    err = payload.get("error")
    if isinstance(err, dict) and isinstance(err.get("message"), str):
        return err["message"]
    if isinstance(err, str):
        return err
    return None
