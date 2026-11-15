import tempfile
import unittest
from pathlib import Path
from insuredatagate.validator import verify
from tests.helpers import DatasetFixture


class DuplicateCreatorTests(unittest.TestCase):
    def test_self_review_detected_for_each_duplicate_order(self):
        for reverse in (False, True):
            with self.subTest(reverse=reverse), tempfile.TemporaryDirectory() as temp:
                data = DatasetFixture(Path(temp))
                duplicate = dict(data.cases[0], created_by=' DEMO-REVIEWER ')
                data.cases.append(duplicate)
                if reverse:
                    data.cases.reverse()
                data.save()
                result = verify(data.path)
                codes = {issue['code'] for issue in result['issues']}
                self.assertEqual(result['status'], 'BLOCK')
                self.assertIn('DUPLICATE_CASE', codes)
                self.assertIn('SELF_REVIEW', codes)
                self.assertNotIn('demo-reviewer', str(result))

    def test_unrelated_duplicate_creators_are_not_self_review(self):
        with tempfile.TemporaryDirectory() as temp:
            data = DatasetFixture(Path(temp))
            data.cases.append(dict(data.cases[0], created_by='other-author'))
            data.save()
            codes = {issue['code'] for issue in verify(data.path)['issues']}
            self.assertIn('DUPLICATE_CASE', codes)
            self.assertNotIn('SELF_REVIEW', codes)
