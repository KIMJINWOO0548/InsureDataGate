import unittest
from insuredatagate.validator import portable_path


class PortableWindowsPathTests(unittest.TestCase):
    def test_rejects_windows_aliases_and_device_names(self):
        for path in ('sources/rules.txt.', 'sources /rules.txt', 'CON', 'nul.txt',
                     'sources/COM1.txt', 'LPT9/data', 'aux.json', 'a?/b', 'a*/b',
                     'a|b', 'a<b', 'a>b', 'a"b'):
            with self.subTest(path=path):
                self.assertFalse(portable_path(path))

    def test_preserves_ordinary_portable_names(self):
        for path in ('sources/rules.txt', 'company/COM10.txt', 'context.json'):
            self.assertTrue(portable_path(path))
