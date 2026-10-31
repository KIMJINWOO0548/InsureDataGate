"""Exercise the user-facing process and exclusive output guarantees."""

import contextlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from tests.helpers import DatasetFixture


class CliTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.data = DatasetFixture(self.root)

    def run_cli(self, *args):
        env = dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[1] / "src"))
        return subprocess.run(
            [sys.executable, "-m", "insuredatagate", *map(str, args)],
            capture_output=True, text=True, encoding="utf-8", env=env, timeout=15,
        )

    def test_check_json_and_report_are_identical(self):
        output = self.root / "report.json"
        result = self.run_cli("check", self.data.path, "--json", "--report", output)
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report["status"], "PASS")
        self.assertEqual(report, json.loads(output.read_bytes()))

    def test_human_summary(self):
        result = self.run_cli("check", self.data.path)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("PASS", result.stdout)
        self.assertIn("3", result.stdout)

    def test_invalid_dataset_blocks_without_raw_data(self):
        self.data.gold[0]["review_status"] = "DRAFT"
        self.data.save()
        result = self.run_cli("check", self.data.path, "--json")
        self.assertEqual(result.returncode, 1)
        self.assertEqual(json.loads(result.stdout)["status"], "BLOCK")
        self.assertNotIn("PRIVATE_GOLD_DEMO", result.stdout + result.stderr)
        self.assertNotIn("RAW_INPUT_CASE", result.stdout + result.stderr)

    def test_export_only_allowlisted_fields(self):
        output = self.root / "model-inputs.jsonl"
        result = self.run_cli("export-inputs", self.data.path, "--output", output)
        self.assertEqual(result.returncode, 0, result.stderr)
        rows = [json.loads(line) for line in output.read_text(encoding="utf-8").splitlines()]
        self.assertEqual([row["case_id"] for row in rows], [row["case_id"] for row in self.data.cases])
        self.assertTrue(all(set(row) == {"case_id", "input", "source_ids"} for row in rows))
        self.assertNotIn("PRIVATE_GOLD_DEMO", output.read_text(encoding="utf-8"))
        self.assertEqual(result.stdout, "")

    def test_blocked_export_creates_nothing(self):
        output = self.root / "inputs.jsonl"
        self.data.cases[0]["input"] = self.data.cases[1]["input"]
        self.data.save()
        result = self.run_cli("export-inputs", self.data.path, "--output", output)
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertFalse(output.exists())

    def test_existing_outputs_preserved(self):
        for command in ("check", "export-inputs"):
            with self.subTest(command=command):
                output = self.root / "existing.txt"
                output.write_bytes(b"KEEP_EXISTING_BYTES")
                option = "--report" if command == "check" else "--output"
                result = self.run_cli(command, self.data.path, option, output)
                self.assertEqual(result.returncode, 2, result.stderr)
                self.assertEqual(output.read_bytes(), b"KEEP_EXISTING_BYTES")

    def test_missing_parent_output_error(self):
        result = self.run_cli("check", self.data.path, "--report", self.root / "missing" / "report.json")
        self.assertEqual(result.returncode, 2)
        self.assertNotIn("Traceback", result.stderr)

    def test_missing_and_malformed_manifest_block(self):
        for raw in (None, b'{"SECRET_INVALID_DATA":'):
            with self.subTest(raw=raw):
                if raw is None:
                    self.data.path.unlink()
                else:
                    self.data.path.write_bytes(raw)
                result = self.run_cli("check", self.data.path, "--json")
                self.assertEqual(result.returncode, 1, result.stderr)
                self.assertEqual(json.loads(result.stdout)["status"], "BLOCK")
                self.assertNotIn("SECRET_INVALID_DATA", result.stdout + result.stderr)

    def test_version_and_usage(self):
        version = self.run_cli("--version")
        self.assertEqual(version.returncode, 0)
        self.assertIn("0.1.0", version.stdout)
        self.assertEqual(self.run_cli().returncode, 2)

    def test_changed_cases_between_verify_and_export_block(self):
        from insuredatagate import cli
        from insuredatagate.validator import verify
        report = verify(self.data.path)

        def changed(_):
            cases = self.root / "cases.jsonl"
            cases.write_bytes(cases.read_bytes() + b"\n")
            return report

        output = self.root / "stale.jsonl"
        with patch.object(cli, "verify", side_effect=changed), contextlib.redirect_stderr(io.StringIO()):
            code = cli.main(["export-inputs", str(self.data.path), "--output", str(output)])
        self.assertEqual(code, 1)
        self.assertFalse(output.exists())

    def test_changed_manifest_between_verify_and_export_block(self):
        from insuredatagate import cli
        from insuredatagate.validator import verify
        report = verify(self.data.path)

        def changed(_):
            self.data.manifest["dataset_id"] = "changed-after-check"
            self.data.write_manifest()
            return report

        output = self.root / "stale.jsonl"
        with patch.object(cli, "verify", side_effect=changed), contextlib.redirect_stderr(io.StringIO()):
            code = cli.main(["export-inputs", str(self.data.path), "--output", str(output)])
        self.assertEqual(code, 1)
        self.assertFalse(output.exists())

    def test_export_accepts_carriage_return_json_whitespace(self):
        cases = self.root / "cases.jsonl"
        cases.write_bytes(cases.read_bytes().replace(b'{"case_id"', b'{\r"case_id"'))
        self.data.repin()
        output = self.root / "carriage-return-inputs.jsonl"
        result = self.run_cli("export-inputs", self.data.path, "--output", output)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(len(output.read_bytes().splitlines()), 3)

    def test_json_stdout_supports_legacy_encoding(self):
        from insuredatagate import cli
        self.data.manifest["version"] = "version-\U0001f600"
        self.data.write_manifest()
        buffer = io.BytesIO()
        stream = io.TextIOWrapper(buffer, encoding="cp949")
        with contextlib.redirect_stdout(stream):
            code = cli.main(["check", str(self.data.path), "--json"])
        stream.flush()
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(buffer.getvalue().decode("cp949"))["version"], "version-\U0001f600")


if __name__ == "__main__":
    unittest.main()
