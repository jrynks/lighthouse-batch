import io
import json
import os
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from lighthouse_batch.cli import main
from lighthouse_batch.models import Categories, Metrics, UrlResult
from lighthouse_batch.output import format_table


class CliShowTest(unittest.TestCase):
    def test_show_pretty_prints(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "summary-20260101-000000.json"
            path.write_text(
                json.dumps(
                    {
                        "schema": "lighthouse-batch/v1-summary",
                        "generated_at": "2026-01-01T00:00:00+00:00",
                        "strategy": "mobile",
                        "total": 1,
                        "ok": 1,
                        "failed": 0,
                        "skipped": 0,
                        "results": [
                            {
                                "url": "https://example.com",
                                "status": "OK",
                                "source": "psi",
                                "categories": {
                                    "performance": 95.0,
                                    "accessibility": 88.0,
                                    "best_practices": 100.0,
                                    "seo": 92.0,
                                },
                            }
                        ],
                        "averages": {"performance": 95.0},
                    }
                ),
                encoding="utf-8",
            )
            buf = io.StringIO()
            err = io.StringIO()
            with redirect_stdout(buf), redirect_stderr(err):
                code = main(["show", "--run", str(path)])
            self.assertEqual(code, 0)
            out = buf.getvalue()
            self.assertIn("https://example.com", out)
            self.assertIn("95", out)
            self.assertIn("psi", out)

    def test_show_missing_file_exit_2(self):
        err = io.StringIO()
        with redirect_stderr(err):
            code = main(["show", "--run", "/tmp/does-not-exist-lh-batch.json"])
        self.assertEqual(code, 2)


class TableTest(unittest.TestCase):
    def test_null_renders_dash(self):
        r = UrlResult(
            url="https://x",
            strategy="mobile",
            source=None,
            categories=Categories(),
            metrics=Metrics(),
            fetched_at="t",
            status="FAILED",
            error="nope",
        )
        table = format_table([r])
        self.assertIn("—", table)
        self.assertIn("FAILED", table)


class RunToolingMissingTest(unittest.TestCase):
    def test_exit_2_when_no_key_and_no_lighthouse(self):
        with TemporaryDirectory() as tmp:
            urls = Path(tmp) / "u.txt"
            urls.write_text("https://example.com\n", encoding="utf-8")
            env = os.environ.copy()
            env.pop("PSI_API_KEY", None)
            err = io.StringIO()
            with patch.dict(os.environ, env, clear=False), patch(
                "lighthouse_batch.cli.lighthouse_available", return_value=False
            ), patch(
                "lighthouse_batch.cli.load_config"
            ) as lc, redirect_stderr(err):
                from lighthouse_batch.config import Config

                lc.return_value = Config(
                    psi_api_key=None,
                    strategy="mobile",
                    output_dir=tmp,
                    concurrency=1,
                    timeout_sec=10,
                    config_path=None,
                )
                code = main(["run", "--urls", str(urls), "--out", tmp])
            self.assertEqual(code, 2)
            self.assertIn("no PSI API key", err.getvalue())


if __name__ == "__main__":
    unittest.main()
