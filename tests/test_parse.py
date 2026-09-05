import json
import unittest
from pathlib import Path

from lighthouse_batch.parse import parse_report, score_to_100, extract_lhr

FIXTURES = Path(__file__).parent / "fixtures"


def load(name: str):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


class ParsePsiTest(unittest.TestCase):
    def test_psi_categories_and_metrics(self):
        cats, metrics = parse_report(load("psi_ok.json"))
        self.assertEqual(cats.performance, 95.0)
        self.assertEqual(cats.accessibility, 88.0)
        self.assertEqual(cats.best_practices, 100.0)
        self.assertEqual(cats.seo, 92.0)
        self.assertEqual(metrics.lcp_ms, 1234.5)
        self.assertEqual(metrics.cls, 0.05)
        self.assertEqual(metrics.tbt_ms, 80)
        self.assertEqual(metrics.fcp_ms, 900)
        self.assertEqual(metrics.si, 1500)


class ParseLighthouseTest(unittest.TestCase):
    def test_local_lighthouse_json(self):
        cats, metrics = parse_report(load("lighthouse_ok.json"))
        self.assertEqual(cats.performance, 42.0)
        self.assertEqual(cats.accessibility, 91.0)
        self.assertEqual(cats.best_practices, 75.0)
        self.assertEqual(cats.seo, 100.0)
        self.assertEqual(metrics.lcp_ms, 4200)


class InventGuardTest(unittest.TestCase):
    def test_missing_category_is_null(self):
        cats, metrics = parse_report(load("missing_category.json"))
        self.assertEqual(cats.performance, 80.0)
        self.assertIsNone(cats.accessibility)
        self.assertIsNone(cats.best_practices)
        self.assertIsNone(cats.seo)
        self.assertIsNone(metrics.lcp_ms)
        self.assertIsNone(metrics.cls)

    def test_display_value_is_not_parsed(self):
        payload = {
            "categories": {},
            "audits": {
                "largest-contentful-paint": {"displayValue": "1.2 s"},
            },
        }
        _, metrics = parse_report(payload)
        self.assertIsNone(metrics.lcp_ms)

    def test_score_zero_is_zero_not_null(self):
        self.assertEqual(score_to_100(0), 0.0)
        self.assertEqual(score_to_100(0.0), 0.0)

    def test_score_outside_0_1_is_null(self):
        self.assertIsNone(score_to_100(1.01))
        self.assertIsNone(score_to_100(85))
        self.assertIsNone(score_to_100(-0.1))
        self.assertIsNone(score_to_100("0.9"))
        self.assertIsNone(score_to_100(True))
        self.assertIsNone(score_to_100(None))

    def test_not_a_report_returns_none(self):
        self.assertIsNone(parse_report({"error": {"code": 429}}))
        self.assertIsNone(parse_report("nope"))
        self.assertIsNone(extract_lhr({"foo": 1}))

    def test_wanted_categories_leave_others_null(self):
        cats, _ = parse_report(load("psi_ok.json"), wanted=["performance"])
        self.assertEqual(cats.performance, 95.0)
        self.assertIsNone(cats.accessibility)
        self.assertIsNone(cats.seo)


if __name__ == "__main__":
    unittest.main()
