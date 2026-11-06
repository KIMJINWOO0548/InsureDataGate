"""Small fixed synthetic detection matrix; not a production accuracy estimate."""
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from insuredatagate.validator import verify
from tests.helpers import DatasetFixture


def injection(fixture, name):
    if name == "hash":
        fixture.source.write_bytes(b"SYNTHETIC unintended bytes")
        return
    if name == "gold":
        fixture.gold[0]["review_status"] = "DRAFT"
    elif name == "self":
        fixture.gold[0]["reviewed_by"] = fixture.cases[0]["created_by"]
    elif name == "group":
        fixture.cases[1]["group_id"] = fixture.cases[0]["group_id"]
    elif name == "duplicate":
        fixture.cases[1]["input"] = fixture.cases[0]["input"].upper()
    elif name == "missing_gold":
        fixture.gold.pop()
    elif name == "source":
        fixture.manifest["sources"][0]["status"] = "DRAFT"
    elif name == "valid_version":
        fixture.manifest["version"] = "fictional-label-2"
    elif name == "valid_unicode":
        fixture.cases[0]["input"] += " 합성 확인 😀"
    fixture.save()


MATRIX = (("valid", None), ("valid_version", None), ("valid_unicode", None),
          ("hash", "HASH_MISMATCH"), ("gold", "GOLD_APPROVAL"), ("self", "SELF_REVIEW"),
          ("group", "GROUP_LEAKAGE"), ("duplicate", "INPUT_LEAKAGE"),
          ("missing_gold", "MISSING_GOLD"), ("source", "SOURCE_APPROVAL"))


class InjectionMatrixTests(unittest.TestCase):
    def test_fixed_ten_case_matrix_without_false_positives_or_missed_injected_codes(self):
        for name, expected in MATRIX:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as temporary:
                fixture = DatasetFixture(Path(temporary))
                injection(fixture, name)
                report = verify(fixture.path)
                if expected:
                    self.assertEqual(report["status"], "BLOCK")
                    self.assertIn(expected, {issue["code"] for issue in report["issues"]})
                else:
                    self.assertEqual(report["status"], "PASS")
                    self.assertEqual(report["issues"], [])


if __name__ == "__main__":
    unittest.main()
