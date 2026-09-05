# lighthouse-batch

Local Linux CLI for agent **Site Audit**. URL list → real Lighthouse scores as compact JSON + a short table.

Prefers [PageSpeed Insights](https://developers.google.com/speed/docs/insights/v5/get-started) when a key is configured. On HTTP 429 / quota / 5xx after retries, falls back to local `lighthouse` against headless Chrome. **Never invents scores, metrics, or dates.** Failed runs are `status=FAILED` with `error` and `null` categories.

Designed so an agent shells this once, reads `/tmp/lighthouse-batch/summary-*.json`, and moves on — not browserUse loops, not pasting HTML into chat.

## Install

```bash
pip install -e .
# optional, for local fallback:
#   node + npm i -g lighthouse
#   Chromium / Google Chrome (or Playwright Chrome for Testing)
```

Python 3.11+. No runtime Python dependencies.

```bash
lighthouse-batch doctor
```

Doctor prints python version, whether `lighthouse` / Chromium were found, whether a PSI key is configured (**bool only — the key is never printed**), default strategy, and output dir.

## PSI key

Do not store keys in the repo.

```bash
export PSI_API_KEY=your_key
```

or `~/.config/lighthouse-batch/config.toml`:

```toml
# psi_api_key = "YOUR_KEY"
strategy = "mobile"
output_dir = "/tmp/lighthouse-batch"
```

Create a key in [Google Cloud Console](https://developers.google.com/speed/docs/insights/v5/get-started) with the PageSpeed Insights API enabled.

## Local Chromium

If PSI is unset or quota-exhausted, the CLI runs:

```text
lighthouse URL --output=json --chrome-flags=--headless --no-sandbox …
```

Install notes:

```bash
# Debian/Ubuntu
sudo apt-get install -y chromium
npm i -g lighthouse

# Playwright Chrome for Testing (also fine)
npx playwright install chromium
# CHROME_PATH is auto-detected from PATH and common Playwright cache paths
```

`CHROME_PATH` / `LIGHTHOUSE_CHROME_PATH` override detection.

## Commands

```bash
lighthouse-batch doctor

lighthouse-batch --json run --urls ./example/urls.txt --strategy mobile

lighthouse-batch run https://example.com https://example.com/pricing

lighthouse-batch run --urls urls.txt --categories perf,a11y,bp,seo \
  --concurrency 2 --timeout-sec 120 --keep-raw --out /tmp/lighthouse-batch

lighthouse-batch show --run /tmp/lighthouse-batch/summary-YYYYMMDD-HHMMSS.json
```

| Flag | Default | Notes |
|---|---|---|
| `--strategy` | `mobile` | `mobile` or `desktop` |
| `--categories` | `perf,a11y,bp,seo` | Lighthouse categories |
| `--concurrency` | `2` | be gentle to PSI |
| `--timeout-sec` | `120` | per URL |
| `--keep-raw` | off | save full reports under `output_dir/raw/` |
| `--json` | off | stdout is the summary JSON; files are always written |

This tool audits the URLs you give it. It does not crawl. Crawling is axe-crawl’s job.

## Output contract

Always written under `/tmp/lighthouse-batch/` (or `--out`):

- `summary-YYYYMMDD-HHMMSS.json`
- `results/NNN-….json` per URL
- `raw/` if `--keep-raw`

Stdout: short table `(url, perf, a11y, bp, seo, source)` unless `--json`.

Per-URL schema `lighthouse-batch/v1`:

```json
{
  "schema": "lighthouse-batch/v1",
  "url": "https://example.com",
  "strategy": "mobile",
  "source": "psi",
  "categories": { "performance": 95.0, "accessibility": 88.0, "best_practices": 100.0, "seo": 92.0 },
  "metrics": { "lcp_ms": 1234.5, "cls": 0.05, "tbt_ms": 80, "fcp_ms": 900, "si": 1500 },
  "fetched_at": "2026-09-05T06:00:00+00:00",
  "status": "OK",
  "error": null,
  "raw_path": null
}
```

Missing category / metric → `null`. Never `0` as a stand-in. A real score of `0` is preserved.

Batch summary schema `lighthouse-batch/v1-summary`. `averages` is omitted when there are zero OK runs with numeric scores.

Exit codes:

- `0` — at least one URL `OK`, or empty input (warning)
- `2` — all failed / skipped, bad args, or tooling missing when required

## Agent shell examples

```bash
pip install -e .
export PSI_API_KEY=…
lighthouse-batch doctor
lighthouse-batch --json run --urls ./urls.txt --strategy mobile
# then read /tmp/lighthouse-batch/summary-*.json
```

Retries: PSI 429 waits `Retry-After` or exponential backoff (max 3 attempts) then local lighthouse.

## Tests

```bash
python3.11 -m unittest discover -s tests -v
```

No network. Covers PSI fixture parse, local Lighthouse fixture parse, 429 → fallback (mock), invent-guard (missing category → null), empty URL file warning.

## Site Audit UI

This repo also ships a TanStack Start dashboard that calls the same PageSpeed / local Lighthouse path and renders the v1 summary. Scores still only come from real reports.
