"""Load config from env and ~/.config/lighthouse-batch/config.toml.

Never logs or returns the raw PSI key except to the HTTP client.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    tomllib = None  # type: ignore[assignment]

DEFAULT_OUTPUT_DIR = "/tmp/lighthouse-batch"
DEFAULT_STRATEGY = "mobile"
DEFAULT_CONCURRENCY = 2
DEFAULT_TIMEOUT_SEC = 120
CONFIG_DIRNAME = "lighthouse-batch"


def xdg_config_path() -> Path:
    xdg = os.environ.get("XDG_CONFIG_HOME")
    if xdg:
        return Path(xdg) / CONFIG_DIRNAME / "config.toml"
    return Path.home() / ".config" / CONFIG_DIRNAME / "config.toml"


def _read_toml(path: Path) -> dict:
    if not path.is_file() or tomllib is None:
        return {}
    try:
        with path.open("rb") as fh:
            data = tomllib.load(fh)
    except (OSError, tomllib.TOMLDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


@dataclass
class Config:
    psi_api_key: str | None
    strategy: str
    output_dir: str
    concurrency: int
    timeout_sec: int
    config_path: str | None

    @property
    def psi_configured(self) -> bool:
        return bool(self.psi_api_key)

    def key_for_request(self) -> str | None:
        return self.psi_api_key or None


def load_config(
    *,
    strategy: str | None = None,
    output_dir: str | None = None,
    concurrency: int | None = None,
    timeout_sec: int | None = None,
) -> Config:
    path = xdg_config_path()
    data = _read_toml(path)
    env_key = os.environ.get("PSI_API_KEY")
    file_key = data.get("psi_api_key")
    key = (env_key or file_key or "").strip() or None

    strat = (
        strategy
        or os.environ.get("LIGHTHOUSE_BATCH_STRATEGY")
        or data.get("strategy")
        or DEFAULT_STRATEGY
    )
    strat = str(strat).strip().lower()
    if strat not in ("mobile", "desktop"):
        strat = DEFAULT_STRATEGY

    out = (
        output_dir
        or os.environ.get("LIGHTHOUSE_BATCH_OUT")
        or data.get("output_dir")
        or DEFAULT_OUTPUT_DIR
    )

    conc = concurrency
    if conc is None:
        raw = os.environ.get("LIGHTHOUSE_BATCH_CONCURRENCY", data.get("concurrency"))
        try:
            conc = int(raw) if raw is not None else DEFAULT_CONCURRENCY
        except (TypeError, ValueError):
            conc = DEFAULT_CONCURRENCY
    conc = max(1, min(int(conc), 8))

    tsec = timeout_sec
    if tsec is None:
        raw = os.environ.get("LIGHTHOUSE_BATCH_TIMEOUT", data.get("timeout_sec"))
        try:
            tsec = int(raw) if raw is not None else DEFAULT_TIMEOUT_SEC
        except (TypeError, ValueError):
            tsec = DEFAULT_TIMEOUT_SEC
    tsec = max(10, int(tsec))

    return Config(
        psi_api_key=key,
        strategy=strat,
        output_dir=str(out),
        concurrency=conc,
        timeout_sec=tsec,
        config_path=str(path) if path.is_file() else None,
    )
