import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest

from insuredatagate import cli
from tests.helpers import DatasetFixture, create_test_symlink


class VerifyIndexTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.data = DatasetFixture(self.root)
        self.index = self.root / 'index.json'
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(cli.main(['release-index', str(self.data.path), '--output', str(self.index)]), 0)

    def verify(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
            try:
                code = cli.main(['verify-index', str(self.data.path), str(self.index)])
            except SystemExit as exc:
                code = exc.code
        self.assertNotIn('PRIVATE_CANARY', output.getvalue())
        return code

    def test_current_index_matches_without_modification(self):
        before = self.index.read_bytes()
        self.assertEqual(self.verify(), 0)
        self.assertEqual(self.index.read_bytes(), before)

    def test_repinning_invalidates_old_index(self):
        self.data.source.write_bytes(b'new synthetic source')
        self.data.repin()
        self.assertEqual(self.verify(), 1)

    def test_json_formatting_does_not_change_identity(self):
        value = json.loads(self.index.read_bytes())
        self.index.write_text(json.dumps(value, sort_keys=True, separators=(',', ':')), encoding='utf-8')
        self.assertEqual(self.verify(), 0)

    def test_symlink_index_refused(self):
        target = self.root / 'original.json'
        self.index.rename(target)
        create_test_symlink(self.index, target)
        self.assertEqual(self.verify(), 1)

    def test_tampered_scope_and_extra_fields_block(self):
        original = json.loads(self.index.read_bytes())
        for key, value in [('assurance', {}), ('lineage', []), ('extra', 'PRIVATE_CANARY')]:
            with self.subTest(key=key):
                self.index.write_text(json.dumps(dict(original, **{key: value})), encoding='utf-8')
                self.assertEqual(self.verify(), 1)

    def test_numeric_types_are_not_coerced(self):
        original = json.loads(self.index.read_bytes())
        for value in (True, 1.0):
            original['counts']['train'] = value
            self.index.write_text(json.dumps(original), encoding='utf-8')
            self.assertEqual(self.verify(), 1)

    def test_invalid_duplicate_and_missing_index_block(self):
        for raw in (b'PRIVATE_CANARY', b'{"x":1,"x":2}', b'[]'):
            self.index.write_bytes(raw)
            self.assertEqual(self.verify(), 1)
        self.index.unlink()
        self.assertEqual(self.verify(), 1)
