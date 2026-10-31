"""Independent contracts for redacted, checked review relationships."""

import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from insuredatagate import comparison
from insuredatagate.validator import verify
from tests.helpers import DatasetFixture


class ReviewTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        for name in ("old", "new"):
            (self.root / name).mkdir()
        self.old = DatasetFixture(self.root / "old")
        self.new = DatasetFixture(self.root / "new")

    def report(self):
        return comparison.review(self.old.path, self.new.path)

    def add_source(self, fixture):
        source = copy.deepcopy(fixture.manifest["sources"][0])
        source.update(source_id="other-source", path="sources/other.txt")
        (fixture.root / source["path"]).write_bytes(b"fictional other source")
        fixture.manifest["sources"].append(source)

    def test_case_and_gold_grouping_and_version_reuse_dossier(self):
        self.new.cases[0]["input"] += " SECRET_INPUT"
        self.new.gold[0]["expected"] = "SECRET_EXPECTED"
        self.new.save()
        result = self.report()
        self.assertEqual(result["status"], "BLOCK")
        self.assertEqual(result["schema_version"], "insuredatagate.review.v1")
        self.assertEqual(result["review"], {
            "available": True,
            "cases": [{"case_id": "case-1", "status": "modified",
                       "fields": {"case": ["input"], "gold": ["expected"]},
                       "sources": {"baseline": ["fictional-rules-v1"],
                                   "candidate": ["fictional-rules-v1"], "changed": []},
                       "splits": {"baseline": "train", "candidate": "train"}}],
            "sources": [],
            "summary": {"case_count": 1, "direct_case_count": 1,
                        "source_count": 0, "source_only_case_count": 0}})

    def test_both_side_relations_removed_references_and_split_membership(self):
        for fixture in (self.old, self.new):
            self.add_source(fixture)
            fixture.save()
        self.new.source.write_bytes(b"changed fictional source")
        self.new.cases[0]["source_ids"] = ["other-source"]
        self.new.cases[0]["split"], self.new.cases[2]["split"] = "test", "train"
        self.new.manifest["version"] = "0.3.0"
        self.new.save()
        dossier = self.report()["review"]
        self.assertEqual(dossier["sources"], [{
            "source_id": "fictional-rules-v1", "status": "modified", "fields": ["sha256"],
            "cases": {
                "baseline": [{"case_id": "case-1", "split": "train"},
                             {"case_id": "case-2", "split": "validation"},
                             {"case_id": "case-3", "split": "test"}],
                "candidate": [{"case_id": "case-2", "split": "validation"},
                              {"case_id": "case-3", "split": "train"}]},
            "affected_case_ids": ["case-1", "case-2", "case-3"]}])
        self.assertEqual([case["status"] for case in dossier["cases"]],
                         ["modified", "affected", "modified"])
        self.assertEqual(dossier["cases"][0]["sources"]["changed"], ["fictional-rules-v1"])
        self.assertEqual(dossier["summary"], {"case_count": 3, "direct_case_count": 2,
                                              "source_count": 1, "source_only_case_count": 1})

    def test_source_only_change_affects_unchanged_cases(self):
        self.new.source.write_bytes(b"changed fictional source")
        self.new.save()
        dossier = self.report()["review"]
        self.assertEqual([case["status"] for case in dossier["cases"]], ["affected"] * 3)
        self.assertTrue(all(case["fields"] == {"case": [], "gold": []} for case in dossier["cases"]))
        self.assertEqual(dossier["summary"], {"case_count": 3, "direct_case_count": 0,
                                              "source_count": 1, "source_only_case_count": 3})

    def test_added_removed_case_and_sources(self):
        self.new.cases[0]["case_id"] = "case-added"
        self.new.gold[0]["case_id"] = "case-added"
        self.new.manifest["sources"][0]["source_id"] = "source-added"
        for case in self.new.cases:
            case["source_ids"] = ["source-added"]
        self.new.manifest["version"] = "0.3.0"
        self.new.save()
        dossier = self.report()["review"]
        cases = {case["case_id"]: case for case in dossier["cases"]}
        for identity, status, absent in (("case-1", "removed", "candidate"),
                                         ("case-added", "added", "baseline")):
            self.assertEqual(cases[identity]["status"], status)
            self.assertEqual(cases[identity]["fields"], {"case": [], "gold": []})
            self.assertIsNone(cases[identity]["splits"][absent])
            self.assertEqual(cases[identity]["sources"][absent], [])
        self.assertEqual([(source["source_id"], source["status"], source["fields"])
                          for source in dossier["sources"]],
                         [("fictional-rules-v1", "removed", []), ("source-added", "added", [])])
        self.assertEqual(dossier["sources"][0]["affected_case_ids"], ["case-1", "case-2", "case-3"])
        self.assertEqual(dossier["summary"], {"case_count": 4, "direct_case_count": 4,
                                              "source_count": 2, "source_only_case_count": 0})

    def test_unavailable_invalid_identity_and_snapshot_mutation(self):
        unavailable = {"available": False, "cases": None, "sources": None, "summary": None}
        self.new.manifest["dataset_id"] = "different"
        self.new.save()
        self.assertEqual(self.report()["review"], unavailable)
        self.new.path.write_text("invalid SECRET_RAW", encoding="utf-8")
        self.assertEqual(self.report()["review"], unavailable)
        self.new.manifest["dataset_id"] = self.old.manifest["dataset_id"]
        self.new.save()
        def gate(path):
            result = verify(path)
            if path == self.new.path:
                self.new.source.write_bytes(b"changed after verify")
            return result
        with patch("insuredatagate.comparison.verify", side_effect=gate):
            result = self.report()
        self.assertEqual(result["review"], unavailable)
        self.assertIn("SNAPSHOT_CHANGED", [issue["code"] for issue in result["issues"]])

    def test_deterministic_redaction_and_single_checked_snapshot_per_side(self):
        self.new.cases[0]["created_by"] = "SECRET_CREATOR"
        self.new.gold[0]["reviewed_by"] = "SECRET_REVIEWER"
        self.new.gold[0]["expected"] = "SECRET_GOLD"
        self.new.source.write_bytes(b"SECRET_SOURCE")
        self.new.save()
        with patch("insuredatagate.comparison.read_snapshot", wraps=comparison.read_snapshot) as reader:
            result = self.report()
        self.assertEqual(reader.call_count, 2)
        self.assertEqual(result, self.report())
        encoded = json.dumps(result)
        for forbidden in ("SECRET_", "RAW_INPUT", "PRIVATE_GOLD", "demo-author", "demo-reviewer", str(self.root)):
            self.assertNotIn(forbidden, encoded)
        self.new.cases.reverse()
        self.new.gold.reverse()
        self.new.save()
        self.assertEqual(result["review"], self.report()["review"])

    def test_compare_contract_and_golden_values_remain_exact(self):
        baseline = comparison.compare(self.old.path, self.new.path)
        self.assertEqual(set(baseline), {"schema_version", "status", "baseline", "candidate",
                         "content_changed", "review_required", "changes", "issues"})
        self.assertEqual(baseline["schema_version"], "insuredatagate.comparison.v1")
        self.assertEqual(baseline["baseline"]["content_sha256"],
                         "a066a5961d2a8315fbaab60d771cf604a3182c7819eeeb1fdb58c95f11f7acc2")
        enriched = self.report()
        enriched.pop("review")
        enriched["schema_version"] = "insuredatagate.comparison.v1"
        self.assertEqual(enriched, baseline)
        self.assertEqual(self.report()["review"]["summary"],
                         {"case_count": 0, "direct_case_count": 0, "source_count": 0, "source_only_case_count": 0})


if __name__ == "__main__":
    unittest.main()
