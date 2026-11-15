import unittest
from pathlib import Path
from unittest.mock import patch
from tests.helpers import create_test_symlink

class SymlinkCapabilityTests(unittest.TestCase):
    def test_only_missing_windows_privilege_is_skipped(self):
        error = OSError('privilege unavailable')
        error.winerror = 1314
        with patch.object(Path, 'symlink_to', side_effect=error):
            with self.assertRaises(unittest.SkipTest):
                create_test_symlink(Path('link'), Path('target'))

    def test_unexpected_filesystem_errors_are_not_hidden(self):
        with patch.object(Path, 'symlink_to', side_effect=FileExistsError('exists')):
            with self.assertRaises(FileExistsError):
                create_test_symlink(Path('link'), Path('target'))
