"""State fixtures are independently verifiable without importing Playwright."""
import hashlib
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.check_report_browser import states, VIEWPORTS


class BrowserStatesTests(unittest.TestCase):
    def test_eight_real_redacted_states_preserve_examples(self):
        paths = sorted((ROOT / "examples").rglob("*"))
        before = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in paths if p.is_file()}
        with tempfile.TemporaryDirectory() as temporary:
            reports, private = states(Path(temporary))
            self.assertEqual(len(reports) * len(VIEWPORTS), 32)
            self.assertTrue(private)
            self.assertEqual(reports["source-only"]["review"]["summary"]["direct_case_count"], 0)
            cases = reports["added-removed"]["review"]["cases"]
            self.assertEqual({c["status"] for c in cases}, {"added", "removed"})
            self.assertEqual({c["case_id"] for c in cases}, {"browser-added-train", "demo-train-001"})
            self.assertTrue(all(not c["fields"]["case"] and not c["fields"]["gold"] for c in cases))
            self.assertEqual(reports["long-malicious"]["status"], "PASS")
            self.assertIn("</script>", reports["long-malicious"]["version"])
            self.assertTrue(reports["version-reused"]["review"]["available"])
            self.assertIsNone(reports["partial"]["review"]["summary"])
        self.assertEqual(before, {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in before})
        self.assertNotIn("playwright.sync_api", sys.modules)


if __name__ == "__main__":
    unittest.main()
