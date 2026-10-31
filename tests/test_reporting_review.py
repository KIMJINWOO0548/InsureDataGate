"""Reviewers need both versions and must not mistake missing data for zero."""

from pathlib import Path
import sys
import tempfile
import unittest
from html.parser import HTMLParser

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from insuredatagate.comparison import compare
from insuredatagate.reporting import render_html
from tests.helpers import DatasetFixture


class _Elements(HTMLParser):
    def __init__(self):
        super().__init__()
        self.elements = []

    def handle_starttag(self, tag, attrs):
        self.elements.append((tag, dict(attrs)))


class ReviewPresentationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        (root / "old").mkdir()
        (root / "new").mkdir()
        self.old = DatasetFixture(root / "old")
        self.new = DatasetFixture(root / "new")

    def test_both_versions_and_approval_boundary_are_visible(self):
        self.new.manifest["version"] = "release-two"
        self.new.write_manifest()
        document = render_html(compare(self.old.path, self.new.path))
        self.assertIn("0.1.0", document)
        self.assertIn("release-two", document)
        self.assertIn("local checks", document)
        self.assertIn("declarations", document)

    def test_unreadable_side_counts_are_not_presented_as_zero(self):
        self.new.path.write_bytes(b"not json")
        document = render_html(compare(self.old.path, self.new.path))
        self.assertNotIn("<dd>0</dd>", document)
        self.assertIn("unavailable", document.lower())

    def test_findings_summary_links_to_focusable_findings_heading(self):
        report = {
            "status": "BLOCK", "issues": [
                {"code": "A", "location": "manifest", "message": "First"},
                {"code": "B", "location": "cases", "message": "Second"},
            ],
        }
        document = render_html(report)
        elements = _Elements()
        elements.feed(document)
        self.assertIn('<a class="issue-link" href="#issues">2 issues · View findings</a>', document)
        self.assertIn(("h2", {"id": "issues", "tabindex": "-1"}), elements.elements)
        self.assertNotIn("alert(", document)
        self.assertNotIn("aria-live", document)

    def test_validation_summary_and_change_entry_counts(self):
        report = {
            "schema_version": "insuredatagate.comparison.v1", "status": "PASS",
            "baseline": {"status": "PASS", "dataset_id": "sample", "version": "1", "counts": {}},
            "candidate": {"status": "PASS", "dataset_id": "sample", "version": "2", "counts": {}},
            "review_required": True, "content_changed": True,
            "changes": {
                "cases_added": ["a", "b"], "cases_removed": ["c"],
                "cases_changed": [{"case_id": "d", "fields": ["input"]}],
                "gold_changed": [], "sources_added": [], "sources_removed": ["s"],
                "sources_changed": [{"source_id": "t", "fields": ["license"]}],
            }, "issues": [],
        }
        document = render_html(report)
        self.assertIn("Change entries: 2 added · 2 removed · 2 modified", document)
        self.assertIn("0 validation issues", document)
        self.assertNotIn('href="#issues"', document)

    def test_partial_comparison_has_no_change_entry_summary(self):
        report = {
            "schema_version": "insuredatagate.comparison.v1", "status": "BLOCK",
            "baseline": {"status": "PASS", "dataset_id": "sample", "version": "1", "counts": {}},
            "candidate": {"status": "BLOCK", "dataset_id": "sample", "version": "2", "counts": {}},
            "review_required": True, "content_changed": None, "changes": None, "issues": [],
        }
        document = render_html(report)
        self.assertNotIn("Change entries:", document)
        self.assertIn("Comparison is partial", document)


if __name__ == "__main__":
    unittest.main()
