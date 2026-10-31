"""Independent semantic comparison contracts; all fixture content is fictional."""

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from insuredatagate.comparison import compare
from insuredatagate.validator import verify
from tests.helpers import DatasetFixture


class ComparisonTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for name in ("old", "new"):
            (self.root / name).mkdir()
        self.old = DatasetFixture(self.root / "old")
        self.new = DatasetFixture(self.root / "new")

    def report(self):
        return compare(self.old.path, self.new.path)

    def test_identical_schema_counts_and_determinism(self):
        result = self.report()
        self.assertEqual(set(result), {"schema_version", "status", "baseline", "candidate", "content_changed", "review_required", "changes", "issues"})
        self.assertEqual(result["schema_version"], "insuredatagate.comparison.v1")
        self.assertEqual(result["status"], "PASS")
        self.assertFalse(result["content_changed"])
        self.assertFalse(result["review_required"])
        self.assertTrue(all(value == [] for value in result["changes"].values()))
        for side in ("baseline", "candidate"):
            self.assertEqual(set(result[side]), {"status", "dataset_id", "version", "manifest_sha256", "content_sha256", "counts"})
            self.assertEqual(result[side]["counts"]["cases"], 3)
            self.assertRegex(result[side]["content_sha256"], "^[0-9a-f]{64}$")
        self.assertEqual(result, self.report())

    def test_add_remove_case_gold_and_source(self):
        self.new.manifest["version"] = "0.2.0"
        self.new.cases[0]["case_id"] = "case-added"
        self.new.gold[0]["case_id"] = "case-added"
        source = self.new.manifest["sources"][0]
        source["source_id"] = "source-added"
        for case in self.new.cases:
            case["source_ids"] = ["source-added"]
        self.new.save()
        result = self.report()
        self.assertEqual(result["status"], "PASS")
        self.assertTrue(result["review_required"])
        self.assertEqual(result["changes"]["cases_added"], ["case-added"])
        self.assertEqual(result["changes"]["cases_removed"], ["case-1"])
        self.assertEqual(result["changes"]["sources_added"], ["source-added"])
        self.assertEqual(result["changes"]["sources_removed"], ["fictional-rules-v1"])
        self.assertEqual(result["changes"]["gold_changed"], [])

    def test_field_changes_are_sorted_redacted_and_version_reuse_blocks(self):
        self.new.cases[2]["input"] += " SECRET_INPUT"
        self.new.cases[2]["created_by"] = "SECRET_AUTHOR"
        self.new.gold[1]["expected"] = "SECRET_GOLD"
        self.new.gold[1]["reviewed_by"] = "SECRET_REVIEWER"
        self.new.source.write_bytes(b"SECRET_SOURCE")
        self.new.manifest["sources"][0]["license"] = "SECRET_LICENSE"
        self.new.save()
        result = self.report()
        self.assertEqual(result["status"], "BLOCK")
        self.assertEqual(result["changes"]["cases_changed"], [{"case_id": "case-3", "fields": ["created_by", "input"]}])
        self.assertEqual(result["changes"]["gold_changed"], [{"case_id": "case-2", "fields": ["expected", "reviewed_by"]}])
        self.assertEqual(result["changes"]["sources_changed"], [{"source_id": "fictional-rules-v1", "fields": ["license", "sha256"]}])
        self.assertEqual([issue["code"] for issue in result["issues"]], ["VERSION_REUSED"])
        encoded = json.dumps(result)
        for secret in ("SECRET_", "RAW_INPUT", "PRIVATE_GOLD", str(self.root), "SYNTHETIC_SOURCE_BODY"):
            self.assertNotIn(secret, encoded)
        self.assertEqual(result, self.report())

    def test_format_record_source_order_paths_and_version_are_nonsemantic(self):
        for fixture in (self.old, self.new):
            second = copy.deepcopy(fixture.manifest["sources"][0])
            second.update(source_id="another-source", path="sources/second.txt")
            (fixture.root / second["path"]).write_bytes(b"another fictional source")
            fixture.manifest["sources"].append(second)
            for case in fixture.cases:
                case["source_ids"].append("another-source")
            fixture.save()
        self.new.manifest["version"] = "opaque-other-version"
        self.new.manifest["sources"].reverse()
        self.new.cases.reverse()
        self.new.gold.reverse()
        for case in self.new.cases:
            case["source_ids"].reverse()
        self.new.save()
        for ref in [*self.new.manifest["sources"], self.new.manifest["cases"], self.new.manifest["gold"]]:
            old = self.new.root / ref["path"]
            ref["path"] = "renamed-" + old.name
            old.rename(self.new.root / ref["path"])
        for key in ("cases", "gold"):
            path = self.new.root / self.new.manifest[key]["path"]
            records = self.new.cases if key == "cases" else self.new.gold
            path.write_text("\n".join(json.dumps(r, indent=None, separators=(",", ":")) for r in records), encoding="utf-8")
        self.new.repin()
        self.new.path.write_text(json.dumps(self.new.manifest, indent=4), encoding="utf-8")
        result = self.report()
        self.assertEqual(result["status"], "PASS")
        self.assertFalse(result["content_changed"])
        self.assertTrue(result["review_required"])
        self.assertEqual(result["baseline"]["content_sha256"], result["candidate"]["content_sha256"])
        self.assertNotEqual(result["baseline"]["manifest_sha256"], result["candidate"]["manifest_sha256"])

    def test_every_case_and_gold_field_preserves_exact_text(self):
        for target, field, value in (("cases", "group_id", "new-group"), ("cases", "split", "test"), ("cases", "input", "ＲＡＷ_INPUT_CASE_ONE: fictional document window?"), ("gold", "expected", " PRIVATE_GOLD_DEMO_1 "), ("sources", "approved_by", "new-curator")):
            with self.subTest(target=target, field=field):
                original = copy.deepcopy((self.new.cases, self.new.gold, self.new.manifest))
                if field == "split":
                    self.new.cases[0]["split"], self.new.cases[2]["split"] = "test", "train"
                elif target == "sources":
                    self.new.manifest["sources"][0][field] = value
                else:
                    getattr(self.new, target)[0][field] = value
                self.new.manifest["version"] = "0.2.0"
                self.new.save()
                self.assertTrue(self.report()["content_changed"])
                self.new.cases, self.new.gold, self.new.manifest = original
                self.new.save()

    def test_invalid_missing_or_different_dataset_has_no_diff(self):
        self.new.manifest["dataset_id"] = "different"
        self.new.write_manifest()
        result = self.report()
        self.assertEqual(result["status"], "BLOCK")
        self.assertIsNone(result["changes"])
        self.assertIsNone(result["content_changed"])
        self.new.path.write_text("invalid SECRET_RAW", encoding="utf-8")
        result = self.report()
        self.assertEqual(result["candidate"]["status"], "BLOCK")
        self.assertIsNone(result["candidate"]["content_sha256"])
        self.assertIsNone(result["changes"])
        self.assertTrue(result["review_required"])
        self.assertTrue(all(i["location"].startswith("candidate.") for i in result["issues"]))
        self.assertNotIn("SECRET_RAW", json.dumps(result))
        self.new.path.unlink()
        self.assertEqual(self.report()["status"], "BLOCK")

    def test_tamper_between_verify_and_snapshot_blocks_every_role(self):
        for role in ("manifest", "source", "cases", "gold"):
            with self.subTest(role=role):
                self.new.save()
                def gate(path):
                    result = verify(path)
                    if path == self.new.path:
                        target = {"manifest": self.new.path, "source": self.new.source, "cases": self.new.root / "cases.jsonl", "gold": self.new.root / "gold.jsonl"}[role]
                        target.write_bytes(target.read_bytes() + b" ")
                    return result
                with patch("insuredatagate.comparison.verify", side_effect=gate):
                    result = self.report()
                self.assertEqual(result["status"], "BLOCK")
                self.assertEqual(result["candidate"]["status"], "BLOCK")
                self.assertIsNone(result["candidate"]["content_sha256"])
                self.assertIsNone(result["changes"])
                self.new.source.write_bytes(b"SYNTHETIC_SOURCE_BODY_ONLY: fictional evaluation rules.\n")


if __name__ == "__main__":
    unittest.main()
