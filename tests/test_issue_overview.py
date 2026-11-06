"""Behavioral contract for navigating recurring redacted gate findings."""

import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from insuredatagate.reporting import render_html
from tests.test_reporting import Tags, comparison


class IssueOverviewTests(unittest.TestCase):
    def test_overview_counts_recurring_codes_and_links_to_each_group(self):
        report = comparison(status="BLOCK")
        report["issues"] = [
            {"code": "SCHEMA", "location": "candidate.cases[1]", "message": "Wrong type."},
            {"code": "HASH_MISMATCH", "location": "baseline.sources[0]", "message": "Bytes differ."},
            {"code": "SCHEMA", "location": "candidate.gold[2]", "message": "Unknown field."},
        ]
        original = copy.deepcopy(report)
        document = render_html(report)
        parsed = Tags(document)
        text = " ".join(parsed.text)
        self.assertIn("3 findings across 2 issue types", text)
        overview = [attrs for tag, attrs in parsed.tags if tag == "nav" and attrs.get("aria-label") == "Finding types"]
        self.assertEqual(len(overview), 1)
        groups = [attrs for tag, attrs in parsed.tags if tag == "section" and attrs.get("class") == "finding-group"]
        self.assertEqual(len(groups), 2)
        anchors = {attrs["href"][1:] for tag, attrs in parsed.tags if tag == "a" and attrs.get("href", "").startswith("#finding-type-")}
        self.assertEqual(anchors, {attrs["id"] for attrs in groups})
        self.assertIn("SCHEMA · 2 findings", text)
        self.assertIn("HASH_MISMATCH · 1 finding", text)
        for value in ("candidate.cases[1]", "candidate.gold[2]", "Bytes differ."):
            self.assertIn(value, text)
        self.assertEqual(report, original)
        self.assertEqual(document, render_html(report))

    def test_untrusted_code_never_becomes_an_anchor_or_executable_markup(self):
        report = comparison(status="BLOCK")
        report["issues"] = [{"code": '<img src=x onerror="bad">', "location": "a&b", "message": "<script>secret</script>", "input": "RAW_CASE", "expected": "RAW_GOLD"}]
        document = render_html(report)
        tags = Tags(document).tags
        self.assertFalse(any(tag in ("img", "script") for tag, _ in tags))
        groups = [attrs["id"] for tag, attrs in tags if tag == "section" and attrs.get("class") == "finding-group"]
        self.assertEqual(groups, ["finding-type-0"])
        self.assertNotIn("RAW_CASE", document)
        self.assertNotIn("RAW_GOLD", document)
        self.assertIn("a&amp;b", document)

    def test_empty_findings_do_not_offer_dead_overview_links(self):
        document = render_html(comparison())
        self.assertNotIn('aria-label="Finding types"', document)
        self.assertIn("No issues were recorded.", document)


if __name__ == "__main__":
    unittest.main()
