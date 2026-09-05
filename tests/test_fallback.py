import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock

from lighthouse_batch.config import Config
from lighthouse_batch.psi import PsiError
from lighthouse_batch.runner import Runner, MAX_PSI_ATTEMPTS

FIXTURES = Path(__file__).parent / "fixtures"


def _config(tmp: str) -> Config:
    return Config(
        psi_api_key="test-key",
        strategy="mobile",
        output_dir=tmp,
        concurrency=1,
        timeout_sec=30,
        config_path=None,
    )


def _psi_ok():
    return json.loads((FIXTURES / "psi_ok.json").read_text(encoding="utf-8"))


def _lh_ok():
    return json.loads((FIXTURES / "lighthouse_ok.json").read_text(encoding="utf-8"))


def _local(_url, **_kwargs):
    return _lh_ok()


class FallbackTest(unittest.TestCase):
    def test_429_retries_then_local(self):
        sleeps: list[float] = []
        psi = MagicMock()
        psi.fetch.side_effect = PsiError(
            "quota", status=429, retry_after=0, quota=True, fallback=True
        )
        local_calls = []

        def local_fn(url, **kwargs):
            local_calls.append(url)
            return _lh_ok()

        with TemporaryDirectory() as tmp:
            runner = Runner(
                _config(tmp),
                categories=["performance", "accessibility", "best-practices", "seo"],
                psi_client=psi,
                local_fn=local_fn,
                sleep=lambda s: sleeps.append(s),
            )
            result = runner.audit_one("https://example.com", index=0, out_dir=Path(tmp), stamp="t")

        self.assertEqual(result.status, "OK")
        self.assertEqual(result.source, "local_lighthouse")
        self.assertEqual(result.categories.performance, 42.0)
        self.assertEqual(psi.fetch.call_count, MAX_PSI_ATTEMPTS)
        self.assertEqual(len(local_calls), 1)
        self.assertTrue(sleeps)

    def test_5xx_then_local(self):
        psi = MagicMock()
        psi.fetch.side_effect = PsiError("boom", status=503, fallback=True)
        with TemporaryDirectory() as tmp:
            runner = Runner(
                _config(tmp),
                categories=["performance", "accessibility", "best-practices", "seo"],
                psi_client=psi,
                local_fn=_local,
                sleep=lambda s: None,
            )
            result = runner.audit_one("https://example.com", index=0, out_dir=Path(tmp), stamp="t")
        self.assertEqual(result.source, "local_lighthouse")
        self.assertEqual(result.status, "OK")

    def test_400_does_not_fallback(self):
        psi = MagicMock()
        psi.fetch.side_effect = PsiError("bad url", status=400, fallback=False)
        local = MagicMock()
        with TemporaryDirectory() as tmp:
            runner = Runner(
                _config(tmp),
                categories=["performance"],
                psi_client=psi,
                local_fn=local,
                sleep=lambda s: None,
            )
            result = runner.audit_one("https://example.com", index=0, out_dir=Path(tmp), stamp="t")
        local.assert_not_called()
        self.assertEqual(result.status, "FAILED")
        self.assertIsNone(result.categories.performance)
        self.assertIn("psi:", result.error)

    def test_psi_success_skips_local(self):
        psi = MagicMock()
        psi.fetch.return_value = _psi_ok()
        local = MagicMock()
        with TemporaryDirectory() as tmp:
            runner = Runner(
                _config(tmp),
                categories=["performance", "accessibility", "best-practices", "seo"],
                psi_client=psi,
                local_fn=local,
            )
            result = runner.audit_one("https://example.com", index=0, out_dir=Path(tmp), stamp="t")
        local.assert_not_called()
        self.assertEqual(result.source, "psi")
        self.assertEqual(result.categories.seo, 92.0)


if __name__ == "__main__":
    unittest.main()
