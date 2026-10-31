"""End-to-end CLI contract for release comparison and offline HTML."""

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from tests.helpers import DatasetFixture


class ReleaseCommandTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for name in ("baseline", "candidate"):
            (self.root / name).mkdir()
        self.baseline = DatasetFixture(self.root / "baseline")
        self.candidate = DatasetFixture(self.root / "candidate")

    def run_cli(self, *args):
        env = dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[1] / "src"), PYTHONUTF8="1")
        return subprocess.run([sys.executable, "-m", "insuredatagate", *map(str, args)],
                              env=env, capture_output=True, text=True, encoding="utf-8", timeout=15)

    def test_check_creates_redacted_html(self):
        target = self.root / "check.html"
        result = self.run_cli("check", self.baseline.path, "--html", target)
        self.assertEqual(result.returncode, 0, result.stderr)
        text = target.read_text(encoding="utf-8")
        self.assertIn("PASS", text)
        self.assertIn("fictional-document-window", text)
        self.assertNotIn("PRIVATE_GOLD_DEMO", text)
        self.assertNotIn("RAW_INPUT_CASE", text)

    def test_compare_identical_json(self):
        result = self.run_cli("compare", self.baseline.path, self.candidate.path, "--json")
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report["schema_version"], "insuredatagate.comparison.v1")
        self.assertFalse(report["content_changed"])
        self.assertFalse(report["review_required"])

    def test_compare_changed_gold_and_version_json_file(self):
        self.candidate.manifest["version"] = "0.2.0"
        self.candidate.gold[0]["expected"] = "NEW_EXPECTED_PRIVATE_TEXT"
        self.candidate.save()
        target = self.root / "compare.json"
        result = self.run_cli("compare", self.baseline.path, self.candidate.path, "--json", "--report", target)
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertTrue(report["content_changed"])
        self.assertTrue(report["review_required"])
        self.assertEqual(report["changes"]["gold_changed"], [{"case_id": "case-1", "fields": ["expected"]}])
        self.assertEqual(report, json.loads(target.read_bytes()))
        self.assertNotIn("NEW_EXPECTED_PRIVATE_TEXT", result.stdout + target.read_text(encoding="utf-8"))

    def test_same_version_changed_content_blocks_with_html(self):
        self.candidate.gold[0]["expected"] = "DIFFERENT_GOLD_CANARY"
        self.candidate.save()
        target = self.root / "blocked.html"
        result = self.run_cli("compare", self.baseline.path, self.candidate.path, "--html", target)
        self.assertEqual(result.returncode, 1, result.stderr)
        text = target.read_text(encoding="utf-8")
        self.assertIn("BLOCK", text)
        self.assertIn("VERSION_REUSED", text)
        self.assertNotIn("DIFFERENT_GOLD_CANARY", text)

    def test_invalid_side_has_no_comparison_metrics(self):
        self.candidate.path.write_bytes(b"not json")
        result = self.run_cli("compare", self.baseline.path, self.candidate.path, "--json")
        self.assertEqual(result.returncode, 1)
        report = json.loads(result.stdout)
        self.assertIsNone(report["changes"])
        self.assertIsNone(report["content_changed"])

    def test_report_formats_are_mutually_exclusive(self):
        json_path, html_path = self.root / "report.json", self.root / "report.html"
        for args in (("check", self.baseline.path), ("compare", self.baseline.path, self.candidate.path)):
            with self.subTest(args=args):
                result = self.run_cli(*args, "--report", json_path, "--html", html_path)
                self.assertEqual(result.returncode, 2)
                self.assertFalse(json_path.exists())
                self.assertFalse(html_path.exists())

    def test_existing_html_never_overwritten(self):
        target = self.root / "existing.html"
        target.write_bytes(b"PRESERVE_ME")
        for args in (("check", self.baseline.path), ("compare", self.baseline.path, self.candidate.path)):
            with self.subTest(args=args):
                result = self.run_cli(*args, "--html", target)
                self.assertEqual(result.returncode, 2, result.stderr)
                self.assertEqual(target.read_bytes(), b"PRESERVE_ME")


if __name__ == "__main__":
    unittest.main()
