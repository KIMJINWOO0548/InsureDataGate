"""A malformed earlier record must not shift the location of later findings."""

from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from insuredatagate.validator import verify
from tests.helpers import DatasetFixture, encode_jsonl


class DiagnosticLocationTests(unittest.TestCase):
    def test_jsonl_findings_keep_original_record_numbers(self):
        for role, field in (("cases", "input"), ("gold", "expected")):
            with self.subTest(role=role), tempfile.TemporaryDirectory() as directory:
                data = DatasetFixture(Path(directory))
                rows = data.cases if role == "cases" else data.gold
                rows[0][field] = None
                (data.root / f"{role}.jsonl").write_bytes(b"not valid json\n" + encode_jsonl(rows))
                data.repin()
                report = verify(data.path)
                self.assertEqual(report["status"], "BLOCK")
                locations = {(item["code"], item["location"]) for item in report["issues"]}
                self.assertIn(("INVALID_JSONL", f"{role}[1]"), locations)
                self.assertIn(("SCHEMA", f"{role}[2]"), locations)
                self.assertNotIn(("SCHEMA", f"{role}[1]"), locations)


if __name__ == "__main__":
    unittest.main()
