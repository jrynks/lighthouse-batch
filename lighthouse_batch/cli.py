"""lighthouse-batch CLI: run / doctor / show."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

from lighthouse_batch import __version__
from lighthouse_batch.categories import parse_categories
from lighthouse_batch.config import load_config
from lighthouse_batch.doctor import collect as collect_doctor, emit as emit_doctor
from lighthouse_batch.local import lighthouse_available
from lighthouse_batch.output import format_summary_human, format_table, load_summary
from lighthouse_batch.psi import PsiClient
from lighthouse_batch.runner import Runner
from lighthouse_batch.urls import UrlReadError, collect_urls


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="lighthouse-batch",
        description=(
            "Batch Lighthouse performance / accessibility / best-practices / SEO "
            "scores. Prefers PageSpeed Insights when a key is set; falls back to "
            "local lighthouse on 429/quota. Never invents scores."
        ),
    )
    p.add_argument("--json", action="store_true", help="stdout is JSON (files still written)")
    p.add_argument("--version", action="version", version=f"lighthouse-batch {__version__}")
    sub = p.add_subparsers(dest="command")

    run = sub.add_parser("run", help="audit one or more URLs")
    run.add_argument("urls_pos", nargs="*", help="URL arguments")
    run.add_argument("--urls", dest="urls_file", help="file with one URL per line")
    run.add_argument("--strategy", choices=("mobile", "desktop"), default=None)
    run.add_argument(
        "--categories",
        default="perf,a11y,bp,seo",
        help="comma list: perf,a11y,bp,seo (default all four)",
    )
    run.add_argument("--concurrency", type=int, default=None)
    run.add_argument("--out", default=None, help="output directory (default /tmp/lighthouse-batch)")
    run.add_argument("--timeout-sec", type=int, default=None)
    run.add_argument("--keep-raw", action="store_true", help="save full PSI/Lighthouse JSON under raw/")

    doc = sub.add_parser("doctor", help="print environment diagnostics (never prints the PSI key)")
    _ = doc

    show = sub.add_parser("show", help="pretty-print a prior summary")
    show.add_argument("--run", required=True, help="path to summary-YYYYMMDD-HHMMSS.json")
    return p


def _exit_for_results(results: list, empty_input: bool) -> int:
    if empty_input:
        return 0
    if any(r.status == "OK" for r in results):
        return 0
    return 2


def cmd_run(args: argparse.Namespace, as_json: bool) -> int:
    try:
        categories = parse_categories(args.categories)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    try:
        urls = collect_urls(file=args.urls_file, args=args.urls_pos)
    except UrlReadError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    config = load_config(
        strategy=args.strategy,
        output_dir=args.out,
        concurrency=args.concurrency,
        timeout_sec=args.timeout_sec,
    )

    if not urls:
        print("warning: no URLs to audit (empty input)", file=sys.stderr)
        out_dir = Path(config.output_dir)
        runner = Runner(config, categories=categories, keep_raw=args.keep_raw)
        _, summary_path = runner.run([], out_dir=out_dir)
        if as_json:
            print(summary_path.read_text(encoding="utf-8"), end="")
        else:
            print(f"wrote {summary_path}")
        return 0

    tooling_missing = (not config.psi_configured) and (not lighthouse_available())
    if tooling_missing:
        print(
            "error: no PSI API key (PSI_API_KEY or config psi_api_key) and "
            "lighthouse CLI not found",
            file=sys.stderr,
        )
        return 2

    psi_client = None
    if config.psi_configured:
        psi_client = PsiClient(config.key_for_request(), timeout=config.timeout_sec)

    runner = Runner(
        config,
        categories=categories,
        keep_raw=args.keep_raw,
        psi_client=psi_client,
    )
    results, summary_path = runner.run(urls, out_dir=Path(config.output_dir))
    summary = json.loads(summary_path.read_text(encoding="utf-8"))

    if as_json:
        print(json.dumps(summary, indent=2))
    else:
        print(format_table(results))
        print()
        print(f"wrote {summary_path}")
        if summary.get("averages"):
            avg = summary["averages"]
            pretty = "  ".join(f"{k}={v:.1f}" for k, v in avg.items())
            print(f"averages  {pretty}")
        print(f"ok {summary['ok']}  failed {summary['failed']}  skipped {summary.get('skipped', 0)}")

    return _exit_for_results(results, empty_input=False)


def cmd_doctor(as_json: bool) -> int:
    config = load_config()
    info = collect_doctor(config)
    sys.stdout.write(emit_doctor(info, as_json=as_json))
    return 0


def cmd_show(args: argparse.Namespace, as_json: bool) -> int:
    try:
        data = load_summary(args.run)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    if as_json:
        print(json.dumps(data, indent=2))
        return 0
    # Reconstruct a tiny UrlResult-like table from the summary rows.
    from lighthouse_batch.models import Categories, Metrics, UrlResult

    rows = []
    for item in data.get("results") or []:
        cats = item.get("categories") or {}
        rows.append(
            UrlResult(
                url=item.get("url") or "",
                strategy=data.get("strategy") or "mobile",
                source=item.get("source"),
                categories=Categories(
                    performance=cats.get("performance"),
                    accessibility=cats.get("accessibility"),
                    best_practices=cats.get("best_practices"),
                    seo=cats.get("seo"),
                ),
                metrics=Metrics(),
                fetched_at=data.get("generated_at") or "",
                status=item.get("status") or "UNKNOWN",
                error=None,
            )
        )
    print(format_table(rows))
    print()
    from lighthouse_batch.models import BatchSummary

    summary = BatchSummary(
        generated_at=data.get("generated_at") or "",
        strategy=data.get("strategy") or "",
        total=int(data.get("total") or 0),
        ok=int(data.get("ok") or 0),
        failed=int(data.get("failed") or 0),
        skipped=int(data.get("skipped") or 0),
        results=data.get("results") or [],
        averages=data.get("averages"),
        summary_path=str(Path(args.run).resolve()),
    )
    print(format_summary_human(summary))
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    as_json = bool(getattr(args, "json", False))
    command = args.command
    if command is None:
        parser.print_help()
        return 2
    if command == "run":
        return cmd_run(args, as_json)
    if command == "doctor":
        return cmd_doctor(as_json)
    if command == "show":
        return cmd_show(args, as_json)
    parser.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
