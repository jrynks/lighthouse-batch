"""Run local `lighthouse` / `npx lighthouse` against headless Chrome.

Chrome flags include --headless --no-sandbox as required. JSON reporter only.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

CHROME_CANDIDATES = (
    "google-chrome",
    "google-chrome-stable",
    "chromium",
    "chromium-browser",
    "chrome",
)

PLAYWRIGHT_CHROME_GLOBS = (
    "/opt/pw-browsers/chromium-*/chrome-linux*/chrome",
    "/opt/pw-browsers/chromium_headless_shell-*/chrome-headless-shell-linux*/chrome-headless-shell",
    str(Path.home() / ".cache/ms-playwright/chromium-*/chrome-linux*/chrome"),
)


class LocalLighthouseError(Exception):
    def __init__(self, message: str, *, missing: bool = False) -> None:
        super().__init__(message)
        self.missing = missing


def which_lighthouse() -> str | None:
    found = shutil.which("lighthouse")
    if found:
        return found
    local = Path.cwd() / "node_modules" / ".bin" / "lighthouse"
    if local.is_file() and os.access(local, os.X_OK):
        return str(local)
    # Workspace install (Grok Build / this repo)
    ws = Path("/workspace/node_modules/.bin/lighthouse")
    if ws.is_file() and os.access(ws, os.X_OK):
        return str(ws)
    return None


def which_npx() -> str | None:
    return shutil.which("npx")


def which_chromium() -> str | None:
    env = os.environ.get("CHROME_PATH") or os.environ.get("LIGHTHOUSE_CHROME_PATH")
    if env and Path(env).is_file():
        return env
    for name in CHROME_CANDIDATES:
        found = shutil.which(name)
        if found:
            return found
    import glob

    for pattern in PLAYWRIGHT_CHROME_GLOBS:
        matches = sorted(glob.glob(pattern))
        if matches:
            return matches[-1]
    return None


def lighthouse_available() -> bool:
    return which_lighthouse() is not None or which_npx() is not None


def chromium_available() -> bool:
    return which_chromium() is not None


def run_local(
    url: str,
    *,
    strategy: str,
    categories: list[str],
    timeout_sec: int,
) -> dict[str, Any]:
    binary = which_lighthouse()
    argv: list[str]
    if binary:
        argv = [binary]
    else:
        npx = which_npx()
        if not npx:
            raise LocalLighthouseError(
                "lighthouse CLI not found on PATH (install: npm i -g lighthouse)",
                missing=True,
            )
        argv = [npx, "--yes", "lighthouse"]

    chrome = which_chromium()
    extra_env = os.environ.copy()
    if chrome:
        extra_env["CHROME_PATH"] = chrome
        extra_env["LIGHTHOUSE_CHROMIUM_PATH"] = chrome

    with tempfile.TemporaryDirectory(prefix="lh-batch-") as tmp:
        out_json = str(Path(tmp) / "report.json")
        chrome_flags = "--headless --no-sandbox --disable-gpu --disable-dev-shm-usage"
        argv.extend(
            [
                url,
                "--output=json",
                f"--output-path={out_json}",
                "--quiet",
                "--disable-full-page-screenshot",
                "--no-enable-error-reporting",
                f"--only-categories={','.join(categories)}",
                f"--chrome-flags={chrome_flags}",
            ]
        )
        if strategy == "desktop":
            argv.extend(
                [
                    "--form-factor=desktop",
                    "--screenEmulation.mobile=false",
                    "--preset=desktop",
                ]
            )
        else:
            argv.extend(
                [
                    "--form-factor=mobile",
                    "--screenEmulation.mobile=true",
                ]
            )
        try:
            proc = subprocess.run(
                argv,
                env=extra_env,
                capture_output=True,
                text=True,
                timeout=timeout_sec,
                check=False,
            )
        except FileNotFoundError as exc:
            raise LocalLighthouseError(
                f"lighthouse executable missing: {exc}", missing=True
            ) from exc
        except subprocess.TimeoutExpired as exc:
            raise LocalLighthouseError(
                f"local lighthouse timed out after {timeout_sec}s"
            ) from exc

        if Path(out_json).is_file():
            try:
                payload = json.loads(Path(out_json).read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                raise LocalLighthouseError(
                    f"local lighthouse wrote invalid JSON: {exc}"
                ) from exc
            if isinstance(payload, dict):
                return payload

        err = (proc.stderr or proc.stdout or "").strip()
        snippet = err[-800:] if err else f"exit {proc.returncode}"
        raise LocalLighthouseError(f"local lighthouse failed: {snippet}")
