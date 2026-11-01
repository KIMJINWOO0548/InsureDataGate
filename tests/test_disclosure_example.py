"""A published synthetic disclosure release must use the existing offline gate."""

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from insuredatagate.comparison import compare
from insuredatagate.validator import verify


ROOT = Path(__file__).resolve().parents[1]
BASELINE = ROOT / "examples" / "disclosure-demo" / "manifest.json"
CANDIDATE = ROOT / "examples" / "disclosure-demo-v2" / "manifest.json"


def records(manifest, role):
    metadata = json.loads(manifest.read_text(encoding="utf-8"))
    return [json.loads(line) for line in
            (manifest.parent / metadata[role]["path"]).read_text(encoding="utf-8").splitlines()]


class DisclosureExampleTests(unittest.TestCase):
    def run_cli(self, *args):
        env = dict(os.environ, PYTHONPATH=str(ROOT / "src"), PYTHONUTF8="1")
        return subprocess.run([sys.executable, "-m", "insuredatagate", *map(str, args)],
                              env=env, capture_output=True, text=True, encoding="utf-8", timeout=15)

    def test_disclosure_and_preserved_insurance_releases_pass_manifest_v1(self):
        for manifest in (BASELINE, CANDIDATE, ROOT / "examples/insurance-demo/manifest.json",
                         ROOT / "examples/insurance-demo-v2/manifest.json"):
            with self.subTest(example=manifest.parent.name):
                metadata = json.loads(manifest.read_text(encoding="utf-8"))
                self.assertEqual(metadata["schema_version"], "insuredatagate.manifest.v1")
                self.assertIs(metadata["synthetic"], True)
                report = verify(manifest)
                self.assertEqual(report["schema_version"], "insuredatagate.report.v1")
                self.assertEqual(report["status"], "PASS", report["issues"])
                self.assertEqual(report["counts"], {"sources": 1, "cases": 6, "gold": 6,
                                                   "train": 2, "validation": 2, "test": 2})

    def test_comparison_identifies_only_the_documented_training_revision(self):
        report = compare(BASELINE, CANDIDATE)
        self.assertEqual(report["status"], "PASS", report["issues"])
        self.assertEqual(report["schema_version"], "insuredatagate.comparison.v1")
        self.assertTrue(report["content_changed"])
        self.assertTrue(report["review_required"])
        self.assertEqual(report["changes"], {
            "cases_added": [], "cases_removed": [],
            "cases_changed": [{"case_id": "disclosure-train-unit", "fields": ["input"]}],
            "gold_changed": [{"case_id": "disclosure-train-unit", "fields": ["expected"]}],
            "sources_added": [], "sources_removed": [],
            "sources_changed": [{"source_id": "fictional-extraction-guide", "fields": ["sha256"]}],
        })
        before = {case["case_id"]: case for case in records(BASELINE, "cases")}
        after = {case["case_id"]: case for case in records(CANDIDATE, "cases")}
        unchanged = {identity for identity, case in before.items() if case["split"] != "train"}
        self.assertEqual(len(unchanged), 4)
        old_gold = {row["case_id"]: row for row in records(BASELINE, "gold")}
        new_gold = {row["case_id"]: row for row in records(CANDIDATE, "gold")}
        for identity in unchanged:
            self.assertEqual(before[identity], after[identity])
            self.assertEqual(old_gold[identity], new_gold[identity])

    def test_check_compare_then_export_uses_exact_existing_allowlist(self):
        with tempfile.TemporaryDirectory() as directory:
            for manifest in (BASELINE, CANDIDATE):
                checked = self.run_cli("check", manifest, "--json")
                self.assertEqual(checked.returncode, 0, checked.stderr)
                self.assertEqual(json.loads(checked.stdout)["status"], "PASS")
            compared = self.run_cli("compare", BASELINE, CANDIDATE, "--json")
            self.assertEqual(compared.returncode, 0, compared.stderr)
            self.assertTrue(json.loads(compared.stdout)["review_required"])
            target = Path(directory) / "inputs.jsonl"
            exported = self.run_cli("export-inputs", CANDIDATE, "--output", target)
            self.assertEqual(exported.returncode, 0, exported.stderr)
            self.assertEqual(exported.stdout, "")
            rows = [json.loads(line) for line in target.read_text(encoding="utf-8").splitlines()]
            self.assertEqual(len(rows), 6)
            self.assertTrue(all(set(row) == {"case_id", "input", "source_ids"} for row in rows))
            self.assertEqual(rows, [{key: case[key] for key in ("case_id", "input", "source_ids")}
                                    for case in records(CANDIDATE, "cases")])
            original = target.read_bytes()
            repeated = self.run_cli("export-inputs", CANDIDATE, "--output", target)
            self.assertEqual(repeated.returncode, 2)
            self.assertEqual(target.read_bytes(), original)

    def test_tampered_disclosure_gold_blocks_export_without_echoing_contents(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            shutil.copytree(CANDIDATE.parent, root / "candidate")
            manifest = root / "candidate" / "manifest.json"
            metadata = json.loads(manifest.read_text(encoding="utf-8"))
            gold = manifest.parent / metadata["gold"]["path"]
            gold.write_text(gold.read_text(encoding="utf-8") + "TAMPERED_GOLD_DO_NOT_ECHO\n",
                            encoding="utf-8")
            target = root / "blocked-inputs.jsonl"
            result = self.run_cli("export-inputs", manifest, "--output", target)
            self.assertEqual(result.returncode, 1)
            self.assertFalse(target.exists())
            self.assertNotIn("TAMPERED_GOLD_DO_NOT_ECHO", result.stdout + result.stderr)

    def test_domain_examples_cannot_be_compared_as_one_dataset(self):
        report = compare(ROOT / "examples/insurance-demo/manifest.json", BASELINE)
        self.assertEqual(report["status"], "BLOCK")
        self.assertIn("DATASET_ID_MISMATCH", {issue["code"] for issue in report["issues"]})
        self.assertIsNone(report["changes"])
        self.assertIsNone(report["content_changed"])


if __name__ == "__main__":
    unittest.main()
