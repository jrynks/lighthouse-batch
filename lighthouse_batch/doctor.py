"""Environment diagnostics. Never prints the PSI key."""

from __future__ import annotations

import json
import platform
import shutil
import sys

from lighthouse_batch import __version__
from lighthouse_batch.config import Config
from lighthouse_batch.local import which_chromium, which_lighthouse, which_npx


def collect(config: Config) -> dict:
    chrome = which_chromium()
    lh = which_lighthouse()
    npx = which_npx()
    return {
        "schema": "lighthouse-batch/v1-doctor",
        "version": __version__,
        "python": platform.python_version(),
        "python_executable": sys.executable,
        "lighthouse": bool(lh or npx),
        "lighthouse_path": lh,
        "npx": bool(npx),
        "npx_path": npx,
        "chromium": bool(chrome),
        "chromium_path": chrome,
        "google_chrome": bool(shutil.which("google-chrome") or shutil.which("google-chrome-stable")),
        "psi_key_configured": bool(config.psi_configured),
        "default_strategy": config.strategy,
        "output_dir": config.output_dir,
        "config_path": config.config_path,
    }


def format_human(info: dict) -> str:
    def yn(flag: bool) -> str:
        return "yes" if flag else "no"

    rows = [
        ("python", f"{info['python']} ({info['python_executable']})"),
        ("lighthouse", yn(info["lighthouse"]) + (f"  {info['lighthouse_path']}" if info.get("lighthouse_path") else "")),
        ("npx", yn(info["npx"]) + (f"  {info['npx_path']}" if info.get("npx_path") else "")),
        ("chromium", yn(info["chromium"]) + (f"  {info['chromium_path']}" if info.get("chromium_path") else "")),
        ("google-chrome", yn(info["google_chrome"])),
        ("psi_key_configured", yn(info["psi_key_configured"])),
        ("default_strategy", str(info["default_strategy"])),
        ("output_dir", str(info["output_dir"])),
    ]
    width = max(len(k) for k, _ in rows)
    lines = [f"{k.ljust(width)}  {v}".rstrip() for k, v in rows]
    return "\n".join(lines) + "\n"


def emit(info: dict, *, as_json: bool) -> str:
    if as_json:
        return json.dumps(info, indent=2) + "\n"
    return format_human(info)
