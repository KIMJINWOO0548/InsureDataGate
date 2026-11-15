import tempfile
import unittest
from pathlib import Path
from insuredatagate.validator import verify
from tests.helpers import DatasetFixture

class IncompleteValidationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.data = DatasetFixture(Path(self.temp.name))
    def codes(self):
        result = verify(self.data.path)
        self.assertEqual(result['status'], 'BLOCK')
        self.assertNotIn('PRIVATE_GOLD', str(result))
        self.assertNotIn('RAW_INPUT', str(result))
        return {issue['code'] for issue in result['issues']}
    def test_missing_cases(self):
        (self.data.root / 'cases.jsonl').unlink()
        codes = self.codes()
        self.assertIn('FILE_READ', codes)
        self.assertIn('CHECK_NOT_RUN', codes)
        self.assertFalse(codes & {'EMPTY_SPLIT', 'UNMATCHED_GOLD'})
    def test_malformed_gold(self):
        (self.data.root / 'gold.jsonl').write_bytes(b'{broken}\n')
        self.data.repin()
        codes = self.codes()
        self.assertIn('INVALID_JSONL', codes)
        self.assertIn('CHECK_NOT_RUN', codes)
        self.assertNotIn('MISSING_GOLD', codes)
    def test_invalid_case_schema(self):
        del self.data.cases[0]['input']
        self.data.save()
        codes = self.codes()
        self.assertIn('SCHEMA', codes)
        self.assertIn('CHECK_NOT_RUN', codes)
        self.assertNotIn('UNMATCHED_GOLD', codes)
        self.assertNotIn('EMPTY_SPLIT', codes)
    def test_independent_failure(self):
        self.data.gold[0]['review_status'] = 'DRAFT'
        self.data.save()
        (self.data.root / 'cases.jsonl').unlink()
        codes = self.codes()
        self.assertIn('GOLD_APPROVAL', codes)
        self.assertIn('CHECK_NOT_RUN', codes)
    def test_valid_input(self):
        result = verify(self.data.path)
        self.assertEqual(result['status'], 'PASS')
        self.assertEqual(result['issues'], [])
        self.assertEqual(result['schema_version'], 'insuredatagate.report.v1')
    def test_check_not_run_survives_comparison_and_html_without_raw_text(self):
        from insuredatagate.comparison import compare
        from insuredatagate.reporting import render_html
        (self.data.root / 'cases.jsonl').unlink()
        result = compare(self.data.path, self.data.path)
        self.assertEqual(result['status'], 'BLOCK')
        self.assertIsNone(result['changes'])
        self.assertIn('CHECK_NOT_RUN', str(result))
        html = render_html(result)
        self.assertIn('CHECK_NOT_RUN', html)
        self.assertIn('Restore prerequisites', html)
        self.assertNotIn('PRIVATE_GOLD', html)
        self.assertNotIn('RAW_INPUT', html)
