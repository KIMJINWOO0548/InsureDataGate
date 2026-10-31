"""Real filesystem boundaries, including Windows junctions without admin rights."""

import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from insuredatagate.validator import verify
from tests.helpers import DatasetFixture


class FilesystemTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.root = self.base / "dataset"
        self.root.mkdir()
        self.data = DatasetFixture(self.root)

    def test_manifest_parent_symlink_blocks(self):
        link = self.base / "linked-dataset"
        try:
            link.symlink_to(self.root, target_is_directory=True)
        except OSError:
            self.skipTest("OS does not permit directory symlink creation for this account")
        self.assertEqual(verify(link / "manifest.json")["status"], "BLOCK")

    @unittest.skipUnless(os.name == "nt", "Windows junction check")
    def test_windows_source_directory_junction_blocks(self):
        link = self.root / "linked-sources"
        result = subprocess.run(
            ["cmd.exe", "/d", "/c", "mklink", "/J", str(link), str(self.root / "sources")],
            capture_output=True, timeout=10, creationflags=subprocess.CREATE_NO_WINDOW,
        )
        if result.returncode:
            self.skipTest("OS denied junction creation")
        self.data.manifest["sources"][0]["path"] = "linked-sources/rules.txt"
        self.data.write_manifest()
        try:
            self.assertEqual(verify(self.data.path)["status"], "BLOCK")
        finally:
            link.rmdir()


if __name__ == "__main__":
    unittest.main()
