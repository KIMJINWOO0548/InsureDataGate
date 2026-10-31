import html.parser
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from insuredatagate import reporting, validator
from tests.helpers import DatasetFixture


class Tags(html.parser.HTMLParser):
    def __init__(self, document):
        super().__init__(convert_charrefs=True)
        self.tags = []
        self.text = []
        self.feed(document)

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))

    def handle_data(self, data):
        self.text.append(data)


def comparison(status="PASS", changes=None, review=True, content=True):
    side = {"status": "PASS", "dataset_id": "dataset-demo", "version": "1.0", "manifest_sha256": "a" * 64, "content_sha256": "b" * 64, "counts": {"sources": 1, "cases": 3, "gold": 3, "train": 1, "validation": 1, "test": 1}}
    return {"schema_version": "insuredatagate.comparison.v1", "status": status, "baseline": side, "candidate": dict(side), "content_changed": content, "review_required": review, "changes": changes, "issues": []}


class ReportingTests(unittest.TestCase):
    def test_verifier_report_is_redacted_deterministic_and_semantic(self):
        with tempfile.TemporaryDirectory() as directory:
            report = validator.verify(DatasetFixture(Path(directory)).path)
        doc = reporting.render_html(report)
        parsed = Tags(doc)
        self.assertEqual(doc, reporting.render_html(report))
        self.assertIn("PASS", " ".join(parsed.text))
        self.assertIn("fictional-document-window", " ".join(parsed.text))
        for secret in ("RAW_INPUT_CASE_ONE", "PRIVATE_GOLD_DEMO_1", "SYNTHETIC_SOURCE_BODY_ONLY"):
            self.assertNotIn(secret, doc)
        self.assertIn("Content-Security-Policy", doc)

    def test_comparison_states_changes_partial_and_no_changes(self):
        empty = {key: [] for key in ("cases_added", "cases_removed", "cases_changed", "gold_changed", "sources_added", "sources_removed", "sources_changed")}
        unchanged = reporting.render_html(comparison(changes=empty, review=False, content=False))
        self.assertIn("No changes", unchanged)
        changed = dict(empty, cases_changed=[{"case_id": "case-1", "fields": ["input"]}], sources_changed=[{"source_id": "src-1", "fields": ["sha256"]}])
        changed_doc = reporting.render_html(comparison(changes=changed))
        self.assertIn("case-1", changed_doc)
        self.assertIn("sha256", changed_doc)
        partial = comparison(status="BLOCK", changes=None, content=None)
        partial["candidate"] = dict(partial["candidate"], status="BLOCK", content_sha256=None)
        partial["issues"] = [{"code": "FILE_READ", "location": "candidate.manifest", "message": "Cannot read safely."}]
        partial_doc = reporting.render_html(partial)
        self.assertIn("partial", partial_doc.lower())
        self.assertIn("unavailable", partial_doc.lower())
        self.assertIn("Cannot read safely.", partial_doc)

    def test_escape_all_dynamic_metadata_and_strict_offline_structure(self):
        report = comparison(changes=None)
        report["candidate"] = dict(report["candidate"], dataset_id='x<"&', version="v<svg onload=bad>", manifest_sha256="<" + "a" * 62 + ">", content_sha256=None)
        report["issues"] = [{"code": "<script>", "location": "x&y", "message": "<img src=x onerror=bad>"}]
        doc = reporting.render_html(report)
        parsed = Tags(doc)
        tags = [tag for tag, _ in parsed.tags]
        self.assertFalse(set(tags) & {"script", "iframe", "img", "link", "base", "form"})
        self.assertIn("&lt;script&gt;", doc)
        self.assertNotIn("<script>", doc)
        self.assertIn("default-src 'none'", doc)
        self.assertIn("style-src 'unsafe-inline'", doc)
        self.assertIn("base-uri 'none'", doc)
        self.assertIn("form-action 'none'", doc)
        for tag, attrs in parsed.tags:
            self.assertFalse(any(name.startswith("on") for name in attrs))
            self.assertFalse(any(name in ("src", "href") and value.startswith(("http:", "https:")) for name, value in attrs.items()))
        self.assertIn("lang", dict(next(attrs for tag, attrs in parsed.tags if tag == "html")))
        self.assertTrue(any(tag == "caption" for tag in tags))
        self.assertTrue(any(name == "scope" for _, attrs in parsed.tags for name in attrs))

    def test_block_and_empty_issues_are_explicit(self):
        report = {"schema_version": "insuredatagate.report.v1", "status": "BLOCK", "dataset_id": "dataset-demo", "version": "1.0", "manifest_sha256": None, "files": [], "counts": {"sources": 0, "cases": 0, "gold": 0, "train": 0, "validation": 0, "test": 0}, "issues": []}
        doc = reporting.render_html(report)
        self.assertIn("BLOCK", doc)
        self.assertIn("No issues", doc)


if __name__ == "__main__":
    unittest.main()
