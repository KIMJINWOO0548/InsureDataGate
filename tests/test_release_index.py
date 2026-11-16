import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from insuredatagate import cli
from tests.helpers import DatasetFixture


class ReleaseIndexTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.data = DatasetFixture(self.root)

    def run_index(self, output):
        with contextlib.redirect_stderr(io.StringIO()):
            return cli.main(['release-index', str(self.data.path), '--output', str(output)])

    def test_deterministic_redacted_index(self):
        a, b = self.root / 'a.json', self.root / 'b.json'
        self.assertEqual(self.run_index(a), 0)
        self.assertEqual(self.run_index(b), 0)
        self.assertEqual(a.read_bytes(), b.read_bytes())
        text = a.read_text(encoding='utf-8')
        report = json.loads(text)
        self.assertEqual(report['schema_version'], 'insuredatagate.release-index.v1')
        self.assertEqual(len(report['lineage']), 3)
        self.assertEqual(report['lineage'][0]['source_ids'], ['fictional-rules-v1'])
        self.assertEqual(len(report['files']), 3)
        self.assertEqual(report['sources'][0]['sha256'], self.data.manifest['sources'][0]['sha256'])
        self.assertEqual(report['assurance']['rights'], 'DECLARATIONS_ONLY')
        for secret in ('RAW_INPUT_CASE', 'PRIVATE_GOLD_DEMO', 'SYNTHETIC_SOURCE_BODY', 'demo-curator', 'demo-reviewer'):
            self.assertNotIn(secret, text)

    def test_invalid_dataset_creates_nothing(self):
        self.data.source.write_bytes(b'tampered')
        target = self.root / 'index.json'
        self.assertEqual(self.run_index(target), 1)
        self.assertFalse(target.exists())

    def test_change_after_check_creates_nothing(self):
        verify = cli.verify
        def mutate(path):
            report = verify(path)
            self.data.source.write_bytes(b'changed after check')
            return report
        target = self.root / 'index.json'
        with patch.object(cli, 'verify', side_effect=mutate):
            self.assertEqual(self.run_index(target), 1)
        self.assertFalse(target.exists())

    def test_existing_output_preserved(self):
        target = self.root / 'index.json'
        target.write_bytes(b'preserve')
        self.assertEqual(self.run_index(target), 2)
        self.assertEqual(target.read_bytes(), b'preserve')

    def test_repinning_changes_snapshot_identity(self):
        a, b = self.root / 'a.json', self.root / 'b.json'
        self.assertEqual(self.run_index(a), 0)
        self.data.source.write_bytes(b'new synthetic source')
        self.data.repin()
        self.assertEqual(self.run_index(b), 0)
        before, after = json.loads(a.read_bytes()), json.loads(b.read_bytes())
        self.assertNotEqual(before['manifest_sha256'], after['manifest_sha256'])
        self.assertNotEqual(before['sources'], after['sources'])
