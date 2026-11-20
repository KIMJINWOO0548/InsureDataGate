"""A checked reread must retain its report contract and observed input context."""
import contextlib
from copy import deepcopy
import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from insuredatagate import cli, comparison, fact_review
from insuredatagate.validator import read_snapshot, verify
from tests.helpers import DatasetFixture


class SnapshotContextTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.data = DatasetFixture(self.root)
        self.report = verify(self.data.path)
        self.assertEqual(self.report['status'], 'PASS')
        self.original_hashes = self.hashes()

    def hashes(self):
        return {path.relative_to(self.root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
                for path in self.root.rglob('*') if path.is_file()}

    def rejected(self, report):
        before = deepcopy(report)
        with self.assertRaisesRegex(ValueError, '^Verified dataset snapshot changed or became unreadable$') as caught:
            read_snapshot(self.data.path, report)
        self.assertNotIn('PRIVATE_CONTEXT', str(caught.exception))
        self.assertNotIn(str(self.root), str(caught.exception))
        self.assertEqual(report, before)
        self.assertEqual(self.hashes(), self.original_hashes)

    def test_report_schema_dataset_and_version_must_match_checked_contract(self):
        for field in ('schema_version', 'dataset_id', 'version'):
            with self.subTest(field=field):
                report = deepcopy(self.report)
                report[field] = 'PRIVATE_CONTEXT_unrecognized'
                self.rejected(report)

    def test_pass_report_requires_an_empty_issue_list(self):
        for issues in ([{'code': 'PRIVATE_CONTEXT', 'location': 'manifest', 'message': 'not checked'}], None, {}):
            with self.subTest(shape=type(issues).__name__):
                report = deepcopy(self.report)
                report['issues'] = issues
                self.rejected(report)

    def test_file_inventory_must_be_unique_and_complete(self):
        for duplicate in (True, False):
            with self.subTest(duplicate=duplicate):
                report = deepcopy(self.report)
                if duplicate:
                    report['files'].append(deepcopy(report['files'][0]))
                else:
                    report['files'].pop()
                self.rejected(report)

    def test_inventory_byte_counts_and_shape_cannot_be_unchecked(self):
        for mutation in ('wrong-size', 'boolean-size', 'float-size', 'missing-size', 'extra-field'):
            with self.subTest(mutation=mutation):
                report = deepcopy(self.report)
                item = report['files'][0]
                if mutation == 'wrong-size':
                    item['bytes'] += 1
                elif mutation == 'boolean-size':
                    item['bytes'] = True
                elif mutation == 'float-size':
                    item['bytes'] = float(item['bytes'])
                elif mutation == 'missing-size':
                    del item['bytes']
                else:
                    item['unchecked'] = 'PRIVATE_CONTEXT'
                self.rejected(report)

    def test_counts_are_exact_integers_for_the_observed_snapshot(self):
        for mutation in ('wrong-count', 'boolean-count', 'float-count', 'moved-split', 'missing-count', 'extra-count'):
            with self.subTest(mutation=mutation):
                report = deepcopy(self.report)
                if mutation == 'wrong-count':
                    report['counts']['cases'] += 1
                elif mutation == 'boolean-count':
                    report['counts']['train'] = True
                elif mutation == 'float-count':
                    report['counts']['cases'] = float(report['counts']['cases'])
                elif mutation == 'moved-split':
                    report['counts']['train'] -= 1
                    report['counts']['validation'] += 1
                elif mutation == 'missing-count':
                    del report['counts']['gold']
                else:
                    report['counts']['unchecked'] = 0
                self.rejected(report)

    def test_normal_json_roundtrip_and_inventory_order_remain_accepted(self):
        report = json.loads(json.dumps(self.report))
        report['files'].reverse()
        before = deepcopy(report)
        snapshot = read_snapshot(self.data.path, report)
        self.assertEqual(snapshot['manifest']['dataset_id'], report['dataset_id'])
        self.assertEqual(snapshot['manifest']['version'], report['version'])
        self.assertEqual(len(snapshot['cases']), report['counts']['cases'])
        self.assertEqual(len(snapshot['gold']), report['counts']['gold'])
        self.assertEqual(report, before)
        self.assertEqual(self.hashes(), self.original_hashes)

    def test_comparison_and_review_do_not_publish_metrics_for_wrong_context(self):
        report = deepcopy(self.report)
        report['version'] = 'PRIVATE_CONTEXT_wrong-version'
        for operation in (comparison.compare, comparison.review):
            with self.subTest(operation=operation.__name__), patch.object(comparison, 'verify', return_value=report):
                result = operation(self.data.path, self.data.path)
                self.assertEqual(result['status'], 'BLOCK')
                self.assertIsNone(result['changes'])
                self.assertIsNone(result['content_changed'])
                self.assertIsNone(result['baseline']['content_sha256'])
                self.assertIn('SNAPSHOT_CHANGED', {issue['code'] for issue in result['issues']})

    def test_export_and_fact_review_treat_unknown_report_contract_as_unavailable(self):
        report = deepcopy(self.report)
        report['schema_version'] = 'PRIVATE_CONTEXT_future-report'
        output = self.root / 'must-not-exist.jsonl'
        diagnostics = io.StringIO()
        with patch.object(cli, 'verify', return_value=report), contextlib.redirect_stderr(diagnostics):
            code = cli.main(['export-inputs', str(self.data.path), '--output', str(output)])
        self.assertEqual(code, 1)
        self.assertFalse(output.exists())
        self.assertNotIn('PRIVATE_CONTEXT', diagnostics.getvalue())
        with patch.object(fact_review, 'verify', return_value=report):
            result = fact_review.review_facts(self.data.path)
        self.assertEqual(result['status'], 'UNAVAILABLE')
        self.assertEqual(result['cases'], [])
        self.assertIsNone(result['manifest_sha256'])
        self.assertEqual(result['issues'], ['SNAPSHOT_UNAVAILABLE'])
        self.assertEqual(self.hashes(), self.original_hashes)


if __name__ == '__main__':
    unittest.main()
