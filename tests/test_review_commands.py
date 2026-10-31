"""Process-level review command, privacy, failure and compatibility checks."""

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from tests.helpers import DatasetFixture


class ReviewCommandTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        for side in ("old", "new"):
            (self.root / side).mkdir()
        self.old = DatasetFixture(self.root / "old")
        self.new = DatasetFixture(self.root / "new")

    def run_cli(self, *args):
        env = dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[1] / "src"), PYTHONUTF8="1")
        return subprocess.run([sys.executable, "-m", "insuredatagate", *map(str, args)],
                              env=env, capture_output=True, text=True, encoding="utf-8", timeout=15)

    def change(self):
        self.new.manifest["version"] = "0.3.0"
        self.new.cases[0]["input"] += " CHANGED_INPUT_CANARY"
        self.new.gold[0]["expected"] = "CHANGED_GOLD_CANARY"
        self.new.source.write_bytes(b"CHANGED_SOURCE_CANARY")
        self.new.save()

    def test_review_groups_changes_and_writes_equal_redacted_json(self):
        self.change()
        path = self.root / "review.json"
        result = self.run_cli("review", self.old.path, self.new.path, "--json", "--report", path)
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report, json.loads(path.read_bytes()))
        self.assertEqual(report["schema_version"], "insuredatagate.review.v1")
        self.assertEqual(report["review"]["summary"], {"case_count": 3, "direct_case_count": 1,
                         "source_count": 1, "source_only_case_count": 2})
        self.assertEqual(report["review"]["cases"][0]["fields"], {"case": ["input"], "gold": ["expected"]})
        self.assertNotIn("CANARY", result.stdout + path.read_text(encoding="utf-8"))
        legacy = self.run_cli("compare", self.old.path, self.new.path, "--json")
        before = json.loads(legacy.stdout)
        self.assertEqual(before["schema_version"], "insuredatagate.comparison.v1")
        self.assertNotIn("review", before)
        report.pop("review")
        report["schema_version"] = "insuredatagate.comparison.v1"
        self.assertEqual(before, report)

    def test_real_html_has_offline_review_entities_without_raw_values(self):
        self.change()
        path = self.root / "review.html"
        result = self.run_cli("review", self.old.path, self.new.path, "--html", path)
        self.assertEqual(result.returncode, 0, result.stderr)
        html = path.read_text(encoding="utf-8")
        for text in ("case-1", "fictional-rules-v1", "Content-Security-Policy", 'aria-label="Filter review dossiers"', "<details"):
            self.assertIn(text, html)
        for text in ("CANARY", "RAW_INPUT", "PRIVATE_GOLD", "<script"):
            self.assertNotIn(text, html)

    def test_unreadable_side_blocks_without_invented_relationship_counts(self):
        self.new.path.unlink()
        result = self.run_cli("review", self.old.path, self.new.path, "--json")
        self.assertEqual(result.returncode, 1, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report["review"], {"available": False, "cases": None, "sources": None, "summary": None})
        self.assertIsNone(report["content_changed"])

    def test_version_reuse_blocks_but_keeps_verified_dossier(self):
        self.new.gold[0]["expected"] = "PRIVATE_CHANGED_GOLD"
        self.new.save()
        result = self.run_cli("review", self.old.path, self.new.path, "--json")
        self.assertEqual(result.returncode, 1, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report["issues"][0]["code"], "VERSION_REUSED")
        self.assertTrue(report["review"]["available"])
        self.assertEqual(report["review"]["summary"]["case_count"], 1)

    def test_existing_outputs_remain_byte_exact_and_formats_exclusive(self):
        for option in ("--html", "--report"):
            with self.subTest(option=option):
                target = self.root / (option[2:] + ".existing")
                target.write_bytes(b"PRESERVE_EXISTING")
                result = self.run_cli("review", self.old.path, self.new.path, option, target)
                self.assertEqual(result.returncode, 2, result.stderr)
                self.assertEqual(target.read_bytes(), b"PRESERVE_EXISTING")
        a, b = self.root / "new.json", self.root / "new.html"
        result = self.run_cli("review", self.old.path, self.new.path, "--report", a, "--html", b)
        self.assertEqual(result.returncode, 2)
        self.assertFalse(a.exists())
        self.assertFalse(b.exists())


if __name__ == "__main__":
    unittest.main()
