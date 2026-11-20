"""Independent contracts for split-aware, bounded review presentation."""
import copy
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from insuredatagate.reporting import render_html
from tests.test_reporting import Tags
from tests.test_reporting_workspace import workspace


class ReviewExposureTests(unittest.TestCase):
    def test_split_exposure_counts_each_snapshot_separately_and_labels_scope(self):
        doc = render_html(workspace())
        self.assertIn('id="split-exposure"', doc)
        self.assertIn("Either snapshot", doc)
        self.assertIn('href="#view-test"', doc)
        self.assertIn('href="#view-validation"', doc)
        self.assertIn("Cases with gold changes", doc)
        self.assertIn("Cases moved between splits", doc)
        tags = Tags(doc).tags
        dossier = next(attrs for tag, attrs in tags if tag == "article" and attrs.get("id") == "case-0")
        self.assertIn("split-train", dossier["class"].split())
        self.assertIn("split-test", dossier["class"].split())
        second = next(attrs for tag, attrs in tags if tag == "article" and attrs.get("id") == "case-1")
        self.assertIn("split-validation", second["class"].split())
        self.assertIn("not release approval", doc)
        disclosure = next(attrs for tag, attrs in tags if tag == "details" and attrs.get("class") == "split-membership")
        self.assertNotIn("open", disclosure)
        for split, counts in (("train", (1, 0, 0, 0)), ("validation", (0, 1, 0, 1)), ("test", (0, 0, 1, 0))):
            row = f'<a href="#view-{split}">{split.capitalize()} cases</a></th>' + ''.join(f'<td>{n}</td>' for n in counts)
            self.assertIn(row, doc)

    def test_large_review_bounds_rail_css_without_dropping_case_anchors_or_privacy(self):
        report = workspace()
        case = report["review"]["cases"][1]
        report["review"]["cases"] = [dict(copy.deepcopy(case), case_id=f"case-{i:05}") for i in range(1000)]
        report["review"]["summary"].update(case_count=1000, direct_case_count=0, source_only_case_count=1000)
        doc = render_html(report)
        tags = Tags(doc).tags
        ids = {attrs["id"] for _, attrs in tags if "id" in attrs}
        self.assertTrue(all(f"case-{i}" in ids for i in range(1000)))
        rail = [a for tag, a in tags if tag == "a" and "rail-entity" in a.get("class", "").split()]
        self.assertLessEqual(len(rail), 40)
        self.assertLessEqual(doc.count(' .rail-entity[href='), 40)
        self.assertIn("Full dossier list is preserved", doc)
        self.assertNotIn("PRIVATE_CASE_VALUE", doc)
        self.assertNotIn("<script", doc)

    def test_partial_review_has_no_invented_zero_exposure(self):
        report = workspace()
        report["review"] = {"available": False, "cases": None, "sources": None, "summary": None}
        doc = render_html(report)
        self.assertNotIn('id="split-exposure"', doc)
        self.assertFalse(any(tag == "a" and attrs.get("href") == "#view-test" for tag, attrs in Tags(doc).tags))
        self.assertIn("not checked", doc)


if __name__ == "__main__":
    unittest.main()
