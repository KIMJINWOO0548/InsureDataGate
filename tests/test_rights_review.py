import contextlib
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from insuredatagate import cli, validator
from insuredatagate.rights_review import review_rights
from tests.helpers import DatasetFixture, create_test_symlink, encode_json


class RightsReviewTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.fixture = DatasetFixture(Path(temp.name))
        self.records_path = self.fixture.root / 'rights.json'
        self.manifest = self.fixture.path
        self.record = {
            'source_id': 'fictional-rules-v1',
            'source_sha256': hashlib.sha256(self.fixture.source.read_bytes()).hexdigest(),
            'purpose': 'internal-eval',
            'declaration': 'SUPPORTS_USE',
            'reviewer_id': 'PRIVATE_REVIEWER_MARKER',
            'evidence': {'document_id': 'fictional-license', 'version': '1.2', 'section': '4.1'},
        }
        self.records = {
            'schema_version': 'insuredatagate.rights-records.v1',
            'manifest_sha256': hashlib.sha256(self.manifest.read_bytes()).hexdigest(),
            'records': [self.record],
        }
        self.save_records()

    def save_records(self):
        self.records_path.write_bytes(encode_json(self.records))

    def report(self, purpose='internal-eval'):
        result = review_rights(self.manifest, self.records_path, purpose)
        if result['status'] == 'UNAVAILABLE':
            self.assertIsNone(result['counts'])
            self.assertEqual(result['sources'], [])
        return result

    def assert_source(self, purpose, state, reason, evidence=None):
        report = self.report(purpose)
        self.assertEqual(report['status'], 'COMPLETE')
        self.assertIsNone(report['reason'])
        self.assertEqual(report['sources'], [{
            'source_id': self.record['source_id'], 'source_sha256': self.fixture.manifest['sources'][0]['sha256'],
            'state': state, 'reason': reason, 'evidence': evidence,
        }])
        self.assertEqual(report['counts'], dict(
            sources=1, declared_support=int(state == 'DECLARED_SUPPORT'),
            declared_restriction=int(state == 'DECLARED_RESTRICTION'),
            manual_review_required=int(state == 'MANUAL_REVIEW_REQUIRED'),
        ))
        self.assertEqual(report['records_sha256'], hashlib.sha256(self.records_path.read_bytes()).hexdigest())

    def test_purpose_and_evidence_are_independent(self):
        self.assert_source('internal-eval', 'DECLARED_SUPPORT', None, self.record['evidence'])
        self.assert_source('external-redistribution', 'MANUAL_REVIEW_REQUIRED', 'MISSING_RECORD')
        self.records['records'].append(dict(self.record, purpose='external-redistribution', declaration='RESTRICTS_USE'))
        self.save_records()
        self.assert_source('external-redistribution', 'DECLARED_RESTRICTION', None, self.record['evidence'])
        self.record['evidence'] = None
        self.save_records()
        self.assert_source('internal-eval', 'MANUAL_REVIEW_REQUIRED', 'MISSING_EVIDENCE')

    def test_different_manifest_and_source_hashes_revoke_declaration(self):
        source_sha256 = self.record['source_sha256']
        self.record['source_sha256'] = '0' * 64
        self.save_records()
        self.assert_source('internal-eval', 'MANUAL_REVIEW_REQUIRED', 'SOURCE_CHANGED')
        self.record['source_sha256'] = source_sha256
        self.save_records()
        self.fixture.source.write_bytes(b'Updated synthetic declaration.\n')
        self.assertEqual(self.report()['reason'], 'GATE_BLOCKED')
        self.fixture.repin()
        self.assert_source('internal-eval', 'MANUAL_REVIEW_REQUIRED', 'MANIFEST_CHANGED')
        self.record['source_id'] = 'removed-source'
        self.save_records()
        self.assertEqual(self.report()['sources'][0]['reason'], 'MANIFEST_CHANGED')
        self.records['manifest_sha256'] = hashlib.sha256(self.manifest.read_bytes()).hexdigest()
        self.save_records()
        self.assertEqual(self.report()['reason'], 'RECORDS_INVALID')
        self.assertEqual(validator.verify(self.manifest)['status'], 'PASS')

    def test_detects_change_between_verification_and_checked_reread(self):
        reread = validator.read_snapshot

        def mutate(path, report):
            self.manifest.write_bytes(self.manifest.read_bytes() + b' ')
            return reread(path, report)

        with patch.object(validator, 'read_snapshot', side_effect=mutate):
            self.assertEqual(self.report()['reason'], 'SNAPSHOT_CHANGED')

    def test_read_and_schema_failures_are_redacted(self):
        original = self.records_path.read_bytes()
        for invalid in (b'\xff', b'{"records": [], "records": []}', b'{"path": "RAW_MARKER"}',
                        original.replace(b'"version": "1.2"', b'"version": "https://example.invalid"')):
            with self.subTest(invalid=invalid):
                self.records_path.write_bytes(invalid)
                report = self.report()
                self.assertEqual(report['reason'], 'RECORDS_INVALID')
                self.assertNotIn('RAW_MARKER', json.dumps(report))
        self.records['records'].append(self.record.copy())
        self.save_records()
        self.assertEqual(self.report()['reason'], 'RECORDS_INVALID')
        self.records_path.write_bytes(b' ' * ((256 * 1024) + 1))
        self.assertEqual(self.report()['reason'], 'RECORDS_UNREADABLE')
        self.records_path.unlink()
        self.assertEqual(self.report()['reason'], 'RECORDS_UNREADABLE')

    def test_review_file_does_not_follow_symlinks(self):
        target = self.records_path.with_name('target-rights.json')
        self.records_path.replace(target)
        create_test_symlink(self.records_path, target)
        self.assertEqual(self.report()['reason'], 'RECORDS_UNREADABLE')

    def test_cli_boundary_preserves_originals_and_existing_outputs(self):
        paths = (self.manifest, self.records_path, self.fixture.source)
        original = {path: path.read_bytes() for path in paths}
        args = ['review-rights', str(self.manifest), '--records', str(self.records_path), '--purpose', 'internal-eval']
        report_path = self.fixture.root / 'report.json'
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            self.assertEqual(cli.main([*args, '--json', '--report', str(report_path)]), 0)
        saved = report_path.read_bytes()
        self.assertEqual(json.loads(stdout.getvalue()), json.loads(saved))
        self.assertEqual(self.report()['snapshot']['manifest_sha256'], self.records['manifest_sha256'])
        for marker in (str(self.fixture.root), 'PRIVATE_REVIEWER_MARKER', 'SYNTHETIC_SOURCE_BODY_ONLY',
                       'RAW_INPUT_CASE_ONE', 'PRIVATE_GOLD_DEMO', 'sources/rules.txt'):
            self.assertNotIn(marker, stdout.getvalue() + stderr.getvalue() + saved.decode())
        with contextlib.redirect_stdout(io.StringIO()) as human, contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(cli.main(args), 0)
            self.assertIn('local snapshot checks', human.getvalue())
            self.assertIn('reviewer declarations', human.getvalue())
            self.assertEqual(cli.main([*args, '--report', str(report_path)]), 2)
        self.assertEqual(saved, report_path.read_bytes())
        self.assertEqual(original, {path: path.read_bytes() for path in paths})
        new_path = report_path.with_name('unavailable.json')
        self.records_path.write_bytes(b'bad')
        with contextlib.redirect_stdout(io.StringIO()) as failure:
            self.assertEqual(cli.main([*args, '--json', '--report', str(new_path)]), 1)
        self.assertEqual(json.loads(failure.getvalue())['reason'], 'RECORDS_INVALID')
        self.assertFalse(new_path.exists())
