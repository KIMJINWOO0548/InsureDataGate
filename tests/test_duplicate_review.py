import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from insuredatagate import cli, validator
from insuredatagate.duplicate_review import _scan_checked_cases, review_duplicates
from tests.helpers import DatasetFixture


def set_inputs(fixture, inputs):
    case, gold = fixture.cases[0].copy(), fixture.gold[0].copy()
    fixture.cases = [
        dict(case, case_id=f"case-{line}", group_id=f"group-{line}", split=split, input=value)
        for line, (split, value) in enumerate(inputs, 1)
    ]
    fixture.gold = [dict(gold, case_id=row["case_id"]) for row in fixture.cases]
    fixture.save()


class DuplicateReviewTests(unittest.TestCase):
    def fixture(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        return DatasetFixture(Path(temp.name))

    def test_checked_snapshot_only(self):
        fixture = self.fixture()
        set_inputs(fixture, [("train", "Ａ  B"), ("validation", "different"), ("test", "a b")])
        self.assertIn("INPUT_LEAKAGE", {issue["code"] for issue in validator.verify(fixture.path)["issues"]})
        with patch.object(validator, "read_snapshot") as reread:
            report = review_duplicates(fixture.path)
            reread.assert_not_called()
        self.assertEqual((report["status"], report["reason"]), ("UNAVAILABLE", "GATE_BLOCKED"))
        self.assertEqual(set(report["counts"].values()), {None})
        output = fixture.root / "export.jsonl"
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(cli.main(["export-inputs", str(fixture.path), "--output", str(output)]), 1)
        self.assertFalse(output.exists())

        for filename in ("manifest.json", "cases.jsonl", "gold.jsonl", "sources/rules.txt"):
            with self.subTest(filename=filename):
                fixture = self.fixture()
                original = validator.read_snapshot

                def mutate(path, report):
                    amended = fixture.root / filename
                    amended.write_bytes(amended.read_bytes() + b"\n")
                    return original(path, report)

                with patch.object(validator, "read_snapshot", side_effect=mutate):
                    report = review_duplicates(fixture.path)
                self.assertEqual(report["reason"], "SNAPSHOT_CHANGED")
                self.assertEqual(set(report["counts"].values()), {None})
                self.assertEqual((report["exact_groups"], report["near_pairs"]), ([], []))

    def test_exact_and_near_threshold(self):
        fixture = self.fixture()
        set_inputs(fixture, [
            ("train", "Ａ  B"), ("validation", "abcdezzhijklmnopq"),
            ("test", "abcdefgxijklmnopq"), ("train", "a b"),
            ("train", "abcdefghijklmnopq"), ("test", "aaaaaaaaaaa"),
            ("validation", "aaaaaaaaaaaa"), ("train", "aaaaaaaaaaaaa"),
        ])
        report = review_duplicates(fixture.path)
        self.assertEqual(report["status"], "COMPLETE")
        self.assertEqual(report["counts"], {
            "case_rows": 8, "short_rows": 3, "exact_groups": 1, "exact_rows": 2,
            "eligible_cross_pairs": 8, "compared_cross_pairs": 8, "near_pairs": 2,
        })
        self.assertEqual([member["line"] for member in report["exact_groups"][0]["members"]], [1, 4])
        self.assertEqual([
            (pair["left"]["line"], pair["right"]["line"], pair["score"]) for pair in report["near_pairs"]
        ], [(8, 7, {"numerator": 2, "denominator": 2}), (5, 3, {"numerator": 24, "denominator": 30})])

    def test_limits_discard_partial_near_results(self):
        fixture = self.fixture()
        set_inputs(fixture, [
            *((split, f"{split} fictional entry {n}") for split in ("train", "test") for n in range(225)),
            ("validation", "brief"),
        ])
        report = review_duplicates(fixture.path)
        self.assertEqual(report["counts"]["eligible_cross_pairs"], 50_625)
        self.assertEqual((report["status"], report["reason"]), ("EXACT_ONLY", "LIMIT_EXCEEDED"))
        self.assertIsNone(report["counts"]["compared_cross_pairs"])
        self.assertEqual(report["near_pairs"], [])

        def rows(train, test):
            return [
                dict(case_id=f"case-{i}", split=split, input=value)
                for i, (split, value) in enumerate(
                    [*(("train", value) for value in train), *(("test", value) for value in test)], 1
                )
            ]

        self.assertEqual(_scan_checked_cases(rows(["a" * 12] * 200, ["z" * 12] * 250))["status"], "COMPLETE")
        self.assertEqual(_scan_checked_cases(rows(["a" * 12] * 201, ["z" * 12] * 250))["status"], "EXACT_ONLY")
        self.assertEqual(_scan_checked_cases(rows(["a" * 100_000], ["z" * 100_000]))["status"], "COMPLETE")
        self.assertEqual(_scan_checked_cases(rows(["a" * 100_000], ["z" * 100_001]))["status"], "EXACT_ONLY")
        for n, status, pairs in ((1_000, "COMPLETE", 1_000), (1_001, "EXACT_ONLY", 0)):
            result = _scan_checked_cases(rows(["a" * 12], ["a" * 13] * n))
            self.assertEqual((result["status"], len(result["near_pairs"])), (status, pairs))
        set_inputs(fixture, [("train", "one"), ("validation", "two"), ("test", "three")])
        empty = review_duplicates(fixture.path)
        self.assertEqual((empty["status"], empty["counts"]["compared_cross_pairs"]), ("COMPLETE", 0))


class DuplicateReviewCliTests(unittest.TestCase):
    def test_partial_report_is_removed(self):
        with tempfile.TemporaryDirectory() as temp:
            fixture = DatasetFixture(Path(temp))
            report = fixture.root / "review.json"
            real_open = Path.open

            @contextlib.contextmanager
            def fails_after_partial_write(path, *args, **kwargs):
                with real_open(path, *args, **kwargs) as stream:
                    if path == report:
                        class Output:
                            def write(self, content):
                                stream.write(content[:10])
                                raise OSError("PRIVATE_WRITE_ERROR")

                        yield Output()
                    else:
                        yield stream

            stdout, stderr = io.StringIO(), io.StringIO()
            with patch.object(Path, "open", fails_after_partial_write):
                with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                    result = cli.main(["review-duplicates", str(fixture.path), "--json", "--report", str(report)])
            self.assertEqual(result, 2)
            self.assertFalse(report.exists())
            self.assertEqual(stdout.getvalue(), "")
            self.assertNotIn("PRIVATE_WRITE_ERROR", stderr.getvalue())

    def test_allowlist_output_and_exclusive_write(self):
        with tempfile.TemporaryDirectory() as temp:
            fixture = DatasetFixture(Path(temp))
            set_inputs(fixture, [
                ("train", "Ａ  B"), ("validation", "SENSITIVE_INPUT_MARKER"),
                ("test", "abcdefgxijklmnopq"), ("train", "a b"), ("train", "abcdefghijklmnopq"),
            ])
            args = ["review-duplicates", str(fixture.path), "--json"]
            report_path, html_path = fixture.root / "review.json", fixture.root / "review.html"
            stdout, stderr = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                self.assertEqual(cli.main([*args, "--report", str(report_path)]), 0)
            data = json.loads(stdout.getvalue())
            self.assertEqual(data, json.loads(report_path.read_bytes()))
            schema = json.loads((Path(__file__).parents[1] / "docs/schemas/duplicate-review.v1.schema.json").read_bytes())
            for value, contract in (
                (data, schema), (data["counts"], schema["properties"]["counts"]),
                (data["exact_groups"][0], schema["properties"]["exact_groups"]["items"]),
                (data["near_pairs"][0], schema["properties"]["near_pairs"]["items"]),
                (data["near_pairs"][0]["left"], schema["$defs"]["location"]),
                (data["near_pairs"][0]["score"], schema["properties"]["near_pairs"]["items"]["properties"]["score"]),
            ):
                self.assertEqual(set(value), set(contract["required"]))
                self.assertEqual(set(value), set(contract["properties"]))
                self.assertIs(contract["additionalProperties"], False)
            self.assertEqual(stderr.getvalue(), "")
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(stderr):
                self.assertEqual(cli.main([*args, "--html", str(html_path)]), 0)
                self.assertEqual(cli.main([*args, "--html", str(report_path)]), 2)
            self.assertEqual(data, json.loads(report_path.read_bytes()))
            html = html_path.read_text(encoding="utf-8")
            for expected in ("COMPLETE", "cases[1]", "cases[3]", "cases[4]", "cases[5]", "80.0%"):
                self.assertIn(expected, html)
            for forbidden in (temp, "SENSITIVE_INPUT_MARKER", "PRIVATE_GOLD_DEMO", "SYNTHETIC_SOURCE_BODY_ONLY", "abcdefghijklmnopq"):
                for output in (stdout.getvalue(), stderr.getvalue(), html):
                    self.assertNotIn(forbidden, output)
