"""Independent presentation contract checks for the native review workspace."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from insuredatagate.reporting import render_html
from tests.test_reporting import Tags, comparison


def workspace():
    report = comparison(changes={}, content=True)
    report["schema_version"] = "insuredatagate.review.v1"
    report["review"] = {
        "available": True,
        "cases": [
            {"case_id": "case-1", "status": "modified", "fields": {"case": ["input"], "gold": ["expected"]}, "sources": {"baseline": ["source-1"], "candidate": ["source-1"], "changed": ["source-1"]}, "splits": {"baseline": "train", "candidate": "test"}},
            {"case_id": "case-2", "status": "affected", "fields": {"case": [], "gold": []}, "sources": {"baseline": ["source-1"], "candidate": [], "changed": ["source-1"]}, "splits": {"baseline": "validation", "candidate": "validation"}},
        ],
        "sources": [{"source_id": "source-1", "status": "modified", "fields": ["sha256"], "cases": {"baseline": [{"case_id": "case-1", "split": "train"}, {"case_id": "case-2", "split": "validation"}], "candidate": [{"case_id": "case-1", "split": "test"}]}, "affected_case_ids": ["case-1", "case-2"]}],
        "summary": {"case_count": 2, "direct_case_count": 1, "source_count": 1, "source_only_case_count": 1},
    }
    return report


class WorkspaceTests(unittest.TestCase):
    def test_filter_and_dossier_navigation_share_one_fragment_state(self):
        doc = render_html(workspace())
        parsed = Tags(doc)
        links = [attrs.get("href") for tag, attrs in parsed.tags if tag == "a"]
        for view in ("all", "direct", "affected", "sources"):
            self.assertIn("#view-" + view, links)
        self.assertFalse(any(tag == "input" and attrs.get("type") == "radio"
                             for tag, attrs in parsed.tags))

    def test_grouped_dossiers_and_both_side_links(self):
        doc = render_html(workspace())
        parsed = Tags(doc)
        ids = [attrs.get("id") for _, attrs in parsed.tags if "id" in attrs]
        self.assertEqual(ids.count("case-0"), 1)
        self.assertEqual(ids.count("case-1"), 1)
        self.assertIn('href="#source-0"', doc)
        self.assertIn('href="#case-0"', doc)
        self.assertIn('href="#case-1"', doc)
        self.assertIn("Case changes", doc)
        self.assertIn("Gold changes", doc)
        self.assertIn("Input text", doc)
        self.assertIn("Gold answer", doc)
        self.assertIn("Source-only impact", doc)
        self.assertIn("Declared references", doc)
        self.assertLess(doc.index('id="direct-cases"'), doc.index('id="affected-cases"'))
        self.assertIn("train", doc)
        self.assertIn("test", doc)

    def test_real_native_filters_compact_inventory_and_hash_disclosure(self):
        doc = render_html(workspace())
        parsed = Tags(doc)
        filters = [attrs for tag, attrs in parsed.tags if tag == "a" and attrs.get("aria-controls") == "dossier-list"]
        self.assertEqual(len(filters), 4)
        self.assertIn(":focus-visible", doc)
        self.assertIn("Inventory", doc)
        self.assertNotIn('class="summary"', doc)
        self.assertIn("Shortened fingerprints", doc)
        self.assertIn("Full integrity hashes", doc)
        self.assertIn("a" * 64, doc)
        self.assertFalse(any(tag in ("button", "script") for tag, _ in parsed.tags))
        self.assertIn('<h1>dataset-demo</h1>', doc)

    def test_source_membership_is_one_row_per_case_and_empty_work_has_no_filters(self):
        doc = render_html(workspace())
        rows = [attrs for tag, attrs in Tags(doc).tags if tag == "li" and attrs.get("class") == "impact-row"]
        self.assertEqual(len(rows), 2)
        self.assertIn("not referenced", doc)
        report = workspace()
        report["review"] = {"available": True, "cases": [], "sources": [],
                            "summary": {"case_count": 0, "direct_case_count": 0, "source_count": 0, "source_only_case_count": 0}}
        doc = render_html(report)
        self.assertIn("No content differences", doc)
        self.assertNotIn('aria-label="Filter review dossiers"', doc)

    def test_source_only_cases_use_compact_linked_rows_and_entity_navigation(self):
        doc = render_html(workspace())
        tags = Tags(doc).tags
        compact = [attrs for tag, attrs in tags if tag == "article" and "compact" in attrs.get("class", "").split()]
        self.assertEqual(len(compact), 1)
        self.assertEqual(compact[0]["id"], "case-1")
        nav_links = [attrs["href"] for tag, attrs in tags if tag == "a" and "rail-entity" in attrs.get("class", "").split()]
        self.assertCountEqual(nav_links, ["#case-0", "#case-1", "#source-0"])

    def test_validator_file_hashes_start_in_a_closed_disclosure(self):
        report = {"schema_version": "insuredatagate.report.v1", "status": "PASS",
                  "dataset_id": "demo", "version": "1", "manifest_sha256": "a" * 64,
                  "counts": {}, "issues": [], "files": [{"path": "cases.jsonl", "sha256": "b" * 64, "bytes": 4}]}
        doc = render_html(report)
        details = [attrs for tag, attrs in Tags(doc).tags if tag == "details" and attrs.get("id") == "file-evidence"]
        self.assertEqual(len(details), 1)
        self.assertNotIn("open", details[0])
        self.assertIn("b" * 64, doc)

    def test_block_recovery_precedes_work_and_partial_counts_are_not_checked(self):
        report = workspace()
        report["status"] = "BLOCK"
        report["issues"] = [{"code": "VERSION_REUSED", "location": "candidate.version", "message": "Version reused."}]
        doc = render_html(report)
        self.assertLess(doc.index('id="recovery"'), doc.index('id="direct-cases"'))
        self.assertIn("Recovery", doc)
        self.assertIn("VERSION_REUSED", doc)
        report["review"] = {"available": False, "cases": None, "sources": None, "summary": None}
        report["changes"] = None
        doc = render_html(report)
        self.assertIn("not checked", doc)
        self.assertIn("unavailable", doc)
        self.assertNotIn('id="case-0"', doc)

    def test_unreadable_file_recovery_precedes_downstream_empty_split(self):
        report = workspace()
        report["status"] = "BLOCK"
        report["issues"] = [
            {"code": "EMPTY_SPLIT", "location": "candidate.counts.train", "message": "Empty split"},
            {"code": "FILE_READ", "location": "candidate.cases", "message": "File unreadable"},
        ]
        doc = render_html(report)
        self.assertLess(doc.index("Restore a readable local snapshot"), doc.index("Restore the intended split coverage"))
        self.assertIn("other finding", doc)

    def test_metadata_escaping_and_no_hidden_content_disclosure(self):
        report = workspace()
        report["review"]["cases"][0]["case_id"] = '<img src=x onerror=bad>'
        report["review"]["cases"][0]["input"] = "PRIVATE_CASE_VALUE"
        report["review"]["sources"][0]["body"] = "PRIVATE_SOURCE_BODY"
        doc = render_html(report)
        self.assertIn("&lt;img", doc)
        self.assertNotIn("<img", doc)
        self.assertNotIn("PRIVATE_CASE_VALUE", doc)
        self.assertNotIn("PRIVATE_SOURCE_BODY", doc)
        self.assertIn("default-src 'none'", doc)


if __name__ == "__main__":
    unittest.main()
