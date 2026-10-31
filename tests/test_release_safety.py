"""Fault injection for the v0.2 output and verified-snapshot boundaries."""

import contextlib
import io
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from insuredatagate import cli
from insuredatagate.validator import verify
from tests.helpers import DatasetFixture


class ReleaseSafetyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.data = DatasetFixture(self.root)

    def test_failed_new_output_is_removed(self):
        original_open = Path.open
        for mode in ("write", "close", "interrupt"):
            with self.subTest(mode=mode):
                output = self.root / (mode + ".json")

                class FailedWriter:
                    def __init__(self, handle):
                        self.handle = handle

                    def __enter__(self):
                        return self

                    def write(self, content):
                        self.handle.write(content[:80] if mode != "close" else content)
                        self.handle.flush()
                        if mode == "write":
                            raise OSError("simulated full disk")
                        if mode == "interrupt":
                            raise KeyboardInterrupt

                    def __exit__(self, *args):
                        self.handle.close()
                        if mode == "close":
                            raise OSError("simulated close failure")

                def fault_open(path, file_mode="r", *args, **kwargs):
                    handle = original_open(path, file_mode, *args, **kwargs)
                    return FailedWriter(handle) if file_mode == "x" else handle

                with patch.object(Path, "open", fault_open), contextlib.redirect_stderr(io.StringIO()):
                    code = cli.main(["check", str(self.data.path), "--report", str(output)])
                self.assertEqual(code, 130 if mode == "interrupt" else 2)
                self.assertFalse(output.exists(), "Failed output must not remain as a usable-looking PASS report")

    def test_source_and_gold_changes_after_gate_prevent_export(self):
        for role in ("source", "gold"):
            for mutation in ("append", "delete"):
                with self.subTest(role=role, mutation=mutation):
                    scenario = self.root / f"{role}-{mutation}-data"
                    scenario.mkdir()
                    data = DatasetFixture(scenario)
                    report = verify(data.path)
                    self.assertEqual(report["status"], "PASS")
                    target = data.source if role == "source" else scenario / "gold.jsonl"

                    def changed(_):
                        if mutation == "delete":
                            target.unlink()
                        else:
                            target.write_bytes(target.read_bytes() + b"\n")
                        return report

                    output = self.root / f"{role}-{mutation}.jsonl"
                    with patch.object(cli, "verify", side_effect=changed), contextlib.redirect_stderr(io.StringIO()):
                        code = cli.main(["export-inputs", str(data.path), "--output", str(output)])
                    self.assertEqual(code, 1)
                    self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
