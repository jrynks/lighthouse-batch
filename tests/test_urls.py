import os
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from lighthouse_batch.cli import main
from lighthouse_batch.output import build_summary
from lighthouse_batch.models import Categories, Metrics, UrlResult
from lighthouse_batch.urls import collect_urls, parse_url_lines, normalize_url


class UrlParseTest(unittest.TestCase):
    def test_skips_blanks_and_comments(self):
        text = """
        # homepage
        https://example.com

        https://example.com/pricing
        # trailing
        """
        urls = parse_url_lines(text)
        self.assertEqual(urls, ["https://example.com", "https://example.com/pricing"])

    def test_dedupes_preserving_order(self):
        urls = parse_url_lines("https://a.com\nhttps://b.com\nhttps://a.com\n")
        self.assertEqual(urls, ["https://a.com", "https://b.com"])

    def test_normalize_rejects_non_http(self):
        self.assertIsNone(normalize_url("ftp://x.com"))
        self.assertIsNone(normalize_url("javascript:alert(1)"))
        self.assertIsNone(normalize_url("file:///etc/passwd"))
        self.assertIsNone(normalize_url("not a url"))
        self.assertEqual(normalize_url("https://ok.com/a"), "https://ok.com/a")

    def test_empty_file_warning_exit_0(self):
        with TemporaryDirectory() as tmp:
            urls = Path(tmp) / "urls.txt"
            urls.write_text("# only comments\n\n", encoding="utf-8")
            out = Path(tmp) / "out"
            code = main(
                [
                    "run",
                    "--urls",
                    str(urls),
                    "--out",
                    str(out),
                ]
            )
            self.assertEqual(code, 0)
            summaries = list(out.glob("summary-*.json"))
            self.assertEqual(len(summaries), 1)

    def test_collect_from_file_and_args(self):
        with TemporaryDirectory() as tmp:
            p = Path(tmp) / "u.txt"
            p.write_text("https://a.com\n", encoding="utf-8")
            urls = collect_urls(file=str(p), args=["https://b.com", "https://a.com"])
            self.assertEqual(urls, ["https://a.com", "https://b.com"])


class AveragesTest(unittest.TestCase):
    def _r(self, status, **cats):
        return UrlResult(
            url="https://x",
            strategy="mobile",
            source="psi",
            categories=Categories(**cats),
            metrics=Metrics(),
            fetched_at="t",
            status=status,
        )

    def test_averages_omit_when_zero_ok(self):
        s = build_summary(
            [self._r("FAILED")],
            strategy="mobile",
            generated_at="t",
        )
        self.assertIsNone(s.averages)

    def test_averages_skip_nulls_and_failed(self):
        s = build_summary(
            [
                self._r("OK", performance=80, accessibility=None),
                self._r("OK", performance=100, accessibility=50),
                self._r("FAILED", performance=0, accessibility=0),
            ],
            strategy="mobile",
            generated_at="t",
        )
        self.assertEqual(s.averages["performance"], 90.0)
        self.assertEqual(s.averages["accessibility"], 50.0)
        self.assertNotIn("seo", s.averages)


class DoctorSecretTest(unittest.TestCase):
    def test_doctor_never_prints_key(self):
        from lighthouse_batch.doctor import collect, emit
        from lighthouse_batch.config import Config

        cfg = Config(
            psi_api_key="SUPER-SECRET-KEY-DO-NOT-LEAK",
            strategy="mobile",
            output_dir="/tmp/lighthouse-batch",
            concurrency=2,
            timeout_sec=120,
            config_path=None,
        )
        info = collect(cfg)
        text = emit(info, as_json=True) + emit(info, as_json=False)
        self.assertTrue(info["psi_key_configured"])
        self.assertNotIn("SUPER-SECRET-KEY-DO-NOT-LEAK", text)
        self.assertNotIn("psi_api_key", text)


if __name__ == "__main__":
    unittest.main()
