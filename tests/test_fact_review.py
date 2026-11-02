"""Independent profile behavior tests against temporary checked datasets."""
import hashlib
import importlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from insuredatagate.validator import verify
from tests.helpers import DatasetFixture

ROOT = Path(__file__).resolve().parents[1]
CONTEXT = 'Period: 2025 annual. Basis: separate. Currency: USD. Amount unit: millions. '
MULTI = ('Basis: separate. Amounts in KRW billions. Revenue for 2025: 17; '
         'revenue for 2024: 16. Extract only the 2025 revenue with its period, currency, amount unit and scope.')


class FactReviewTests(unittest.TestCase):
    def api(self):
        self.assertIsNotNone(importlib.util.find_spec('insuredatagate.fact_review'),
                             'bounded review_facts API is missing')
        return importlib.import_module('insuredatagate.fact_review')

    def fixture(self, directory, text=CONTEXT + 'Revenue: 95.', expected=None):
        fixture = DatasetFixture(Path(directory))
        fixture.cases[0]['input'] = text
        fixture.gold[0]['expected'] = json.dumps(expected if expected is not None else {'revenue': '95'})
        # Unsupported claims in unrelated cases must abstain, not masquerade as reviewed facts.
        for row in fixture.gold[1:]:
            row['expected'] = '{}'
        fixture.save()
        return fixture

    def field(self, report, name):
        return next(row for row in report['cases'][0]['fields'] if row['field'] == name)

    def run_cli(self, *args):
        return subprocess.run([sys.executable, '-m', 'insuredatagate', *map(str, args)],
                              env=dict(os.environ, PYTHONPATH=str(ROOT / 'src')),
                              capture_output=True, text=True, timeout=15)

    def test_both_preserved_disclosures_support_all_fourteen_assertions(self):
        for name in ('disclosure-demo', 'disclosure-demo-v2'):
            with self.subTest(name=name):
                report = self.api().review_facts(ROOT / 'examples' / name / 'manifest.json')
                self.assertEqual(report['status'], 'SUPPORTED')
                self.assertEqual(report['schema_version'], 'insuredatagate.fact-review.v1')
                self.assertEqual(report['profile'], 'disclosure-facts.v1')
                fields = [field for case in report['cases'] for field in case['fields']]
                self.assertEqual(len(fields), 14)
                self.assertEqual({field['status'] for field in fields}, {'SUPPORTED'})

    def test_prior_year_and_wrong_gold_period_cannot_select_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            fixture = self.fixture(directory, MULTI, {'revenue': '16', 'period': '2024'})
            self.assertEqual(verify(fixture.path)['status'], 'PASS')
            report = self.api().review_facts(fixture.path)
            self.assertEqual(report['status'], 'CONFLICT')
            for name in ('revenue', 'period'):
                field = self.field(report, name)
                self.assertEqual(field['status'], 'CONFLICT')
                spans = [MULTI[item['start']:item['end']] for item in field['evidence']]
                self.assertTrue(any('2025' in span for span in spans))
            revenue_spans = [MULTI[item['start']:item['end']] for item in self.field(report, 'revenue')['evidence']]
            self.assertTrue(any('17' in span for span in revenue_spans))

    def test_wrong_currency_unit_scope_and_profit_are_conflicts(self):
        for expected in ({'currency': 'EUR'}, {'amount_unit': 'thousands'},
                         {'scope': 'consolidated'}, {'revenue': '12'}):
            with self.subTest(expected_field=next(iter(expected))), tempfile.TemporaryDirectory() as directory:
                fixture = self.fixture(directory, CONTEXT + 'Revenue: 95; operating profit: 12.', expected)
                self.assertEqual(self.field(self.api().review_facts(fixture.path), next(iter(expected)))['status'], 'CONFLICT')

    def test_unsupported_numeric_tokens_never_match_prefix(self):
        for number in ('9e5', '95,000', '95.0.1', '.95', '95%', '95 USD', '95/2', '９５', '9' * 65):
            with self.subTest(number=number), tempfile.TemporaryDirectory() as directory:
                fixture = self.fixture(directory, CONTEXT + 'Revenue: ' + number + '.', {'revenue': '95'})
                self.assertEqual(self.field(self.api().review_facts(fixture.path), 'revenue')['status'], 'ABSTAIN')

    def test_revenue_requires_all_unique_context(self):
        texts = [CONTEXT.replace(label, '') + 'Revenue: 95.' for label in
                 ('Period: 2025 annual. ', 'Basis: separate. ', 'Currency: USD. ', 'Amount unit: millions. ')]
        texts += [CONTEXT + 'Revenue: 95. Revenue: 95.', CONTEXT + 'Currency: USD. Revenue: 95.',
                  CONTEXT.replace('2025 annual', '2025 half-year') + 'Revenue: 95.',
                  CONTEXT + 'Amount unit: unsupported. Revenue: 95.']
        for text in texts:
            with self.subTest(case=texts.index(text)), tempfile.TemporaryDirectory() as directory:
                fixture = self.fixture(directory, text)
                self.assertEqual(self.field(self.api().review_facts(fixture.path), 'revenue')['status'], 'ABSTAIN')

    def test_missing_duplicate_contradictory_and_unsupported_targets_abstain(self):
        texts = [MULTI.split('Extract')[0], MULTI + ' Extract only the 2025 revenue.',
                 MULTI + ' Extract only the 2024 revenue.', MULTI.replace('2025 revenue with', '2026 revenue with'),
                 MULTI.replace('2025 revenue with', '2025 Q1 revenue with'),
                 MULTI.replace('Revenue for 2025: 17', 'Revenue for 2025: 17; revenue for 2025: 17')]
        for index, text in enumerate(texts):
            with self.subTest(case=index), tempfile.TemporaryDirectory() as directory:
                fixture = self.fixture(directory, text, {'revenue': '17', 'period': '2025'})
                report = self.api().review_facts(fixture.path)
                self.assertEqual(self.field(report, 'revenue')['status'], 'ABSTAIN')
                self.assertEqual(self.field(report, 'period')['status'], 'ABSTAIN')

    def test_null_requires_explicit_absence_without_positive_unit(self):
        for text, status in [('The amount unit is absent.', 'SUPPORTED'), ('No unit label.', 'ABSTAIN'),
                             ('Amount unit: unsupported.', 'ABSTAIN'),
                             ('The amount unit is absent. Amount unit: millions.', 'ABSTAIN')]:
            with self.subTest(status=status, text_index=len(text)), tempfile.TemporaryDirectory() as directory:
                fixture = self.fixture(directory, text, {'amount_unit': None})
                self.assertEqual(self.field(self.api().review_facts(fixture.path), 'amount_unit')['status'], status)

    def test_scope_only_does_not_require_supported_unasserted_period(self):
        with tempfile.TemporaryDirectory() as directory:
            fixture = self.fixture(directory, 'Period: 2025 half-year. Basis: consolidated.', {'scope': 'consolidated'})
            self.assertEqual(self.field(self.api().review_facts(fixture.path), 'scope')['status'], 'SUPPORTED')

    def test_invalid_expected_json_and_types_abstain_without_echo(self):
        values = ['PRIVATE_EXPECTED_ONLY', '{"currency":"USD","currency":"USD"}',
                  '{"revenue":NaN}', '{"currency":"\\ud800"}', '[]',
                  '{"private_unknown":"PRIVATE_EXPECTED_ONLY"}', '{"revenue":95}', '{}']
        for index, value in enumerate(values):
            with self.subTest(case=index), tempfile.TemporaryDirectory() as directory:
                fixture = self.fixture(directory)
                fixture.gold[0]['expected'] = value
                fixture.save()
                report = self.api().review_facts(fixture.path)
                self.assertEqual(report['cases'][0]['status'], 'ABSTAIN')
                serialized = json.dumps(report)
                self.assertNotIn('PRIVATE_EXPECTED_ONLY', serialized)
                self.assertNotIn('private_unknown', serialized)

    def test_unicode_offsets_hashes_replay_and_no_raw_values(self):
        text = '비공개🔎 e\u0301 PRIVATE_INPUT_ONLY. ' + MULTI
        with tempfile.TemporaryDirectory() as directory:
            fixture = self.fixture(directory, text, {'revenue': '17', 'period': '2025'})
            report = self.api().review_facts(fixture.path)
            case = report['cases'][0]
            self.assertEqual(case['record_index'], 1)
            self.assertEqual(case['input_sha256'], hashlib.sha256(text.encode()).hexdigest())
            self.assertEqual(case['source_ids'], ['fictional-rules-v1'])
            for field in case['fields']:
                self.assertTrue(field['evidence'])
                for item in field['evidence']:
                    self.assertEqual(item['field'], 'input')
                    span = text[item['start']:item['end']]
                    self.assertTrue(span)
                    self.assertEqual(item['sha256'], hashlib.sha256(span.encode()).hexdigest())
            encoded = json.dumps(report)
            for secret in ('PRIVATE_INPUT_ONLY', 'SYNTHETIC_SOURCE_BODY_ONLY', 'expected', 'quote'):
                self.assertNotIn(secret, encoded)
            self.assertEqual(report, self.api().review_facts(fixture.path))

    def test_each_checked_role_changed_or_deleted_after_verify_is_unavailable(self):
        module = self.api()
        for role in ('manifest', 'cases', 'gold', 'source'):
            for delete in (False, True):
                with self.subTest(role=role, delete=delete), tempfile.TemporaryDirectory() as directory:
                    fixture = self.fixture(directory)
                    target = {'manifest': fixture.path, 'cases': fixture.root / 'cases.jsonl',
                              'gold': fixture.root / 'gold.jsonl', 'source': fixture.source}[role]
                    def change(path):
                        gate = verify(path)
                        if delete:
                            target.unlink()
                        else:
                            target.write_bytes(target.read_bytes() + b' ')
                        return gate
                    with patch.object(module, 'verify', side_effect=change):
                        report = module.review_facts(fixture.path)
                    self.assertEqual(report['status'], 'UNAVAILABLE')
                    self.assertEqual(report['cases'], [])

    def test_validation_failure_has_no_trusted_facts(self):
        with tempfile.TemporaryDirectory() as directory:
            report = self.api().review_facts(Path(directory) / 'absent.json')
            self.assertEqual(report['status'], 'UNAVAILABLE')
            self.assertEqual(report['cases'], [])

    def test_lexical_amount_equality_and_string_claim_types(self):
        for value, status in [('17', 'SUPPORTED'), ('17.0', 'CONFLICT'), ('+17', 'CONFLICT'),
                              ('017', 'CONFLICT'), (17, 'ABSTAIN'), (True, 'ABSTAIN')]:
            with self.subTest(value=value), tempfile.TemporaryDirectory() as directory:
                fixture = self.fixture(directory, CONTEXT + 'Revenue: 17.', {'revenue': value})
                self.assertEqual(self.field(self.api().review_facts(fixture.path), 'revenue')['status'], status)

    def test_malformed_relevant_duplicate_labels_and_targets_poison_only_dependencies(self):
        for suffix in ('Currency: ???.', 'Currency: EUR.', 'Basis: invalid.',
                       'Period: 2025 half-year.', 'Revenue: unsupported.',
                       'Amount unit: ???.'):
            with self.subTest(suffix=suffix), tempfile.TemporaryDirectory() as directory:
                fixture = self.fixture(directory, CONTEXT + 'Revenue: 95. ' + suffix)
                self.assertEqual(self.field(self.api().review_facts(fixture.path), 'revenue')['status'], 'ABSTAIN')
        with tempfile.TemporaryDirectory() as directory:
            fixture = self.fixture(directory, MULTI + ' Extract only the 2025 Q1 revenue.', {'revenue': '17'})
            self.assertEqual(self.field(self.api().review_facts(fixture.path), 'revenue')['status'], 'ABSTAIN')

    def test_revenue_evidence_covers_all_dependencies_and_original_target(self):
        with tempfile.TemporaryDirectory() as directory:
            fixture = self.fixture(directory, '🔎. ' + MULTI, {'revenue': '17'})
            evidence = self.field(self.api().review_facts(fixture.path), 'revenue')['evidence']
            self.assertEqual({item['kind'] for item in evidence}, {'revenue', 'target', 'currency', 'amount_unit', 'scope'})
        with tempfile.TemporaryDirectory() as directory:
            fixture = self.fixture(directory)
            evidence = self.field(self.api().review_facts(fixture.path), 'revenue')['evidence']
            self.assertEqual({item['kind'] for item in evidence}, {'revenue', 'period', 'currency', 'amount_unit', 'scope'})

    def test_mixed_unknown_claim_abstains_and_period_granularity_is_explicit(self):
        with tempfile.TemporaryDirectory() as directory:
            fixture = self.fixture(directory, CONTEXT, {'scope': 'separate', 'unknown_private_key': 'hidden'})
            report = self.api().review_facts(fixture.path)
            self.assertEqual(self.field(report, 'scope')['status'], 'SUPPORTED')
            self.assertEqual(report['cases'][0]['status'], 'ABSTAIN')
            self.assertNotIn('unknown_private_key', json.dumps(report))
        for label, expected in [('2025 annual', '2025'), ('2025 Q3', '2025 Q3')]:
            with self.subTest(label=label), tempfile.TemporaryDirectory() as directory:
                fixture = self.fixture(directory, 'Period: ' + label + '.', {'period': expected})
                self.assertEqual(self.field(self.api().review_facts(fixture.path), 'period')['status'], 'SUPPORTED')

    def test_separate_report_schema_matches_all_output_shapes(self):
        schema_path = ROOT / 'docs/schemas/fact-review.v1.schema.json'
        self.assertTrue(schema_path.is_file(), 'separate fact-review report schema fixture missing')
        schema = json.loads(schema_path.read_text())
        def check(value, rule):
            if '$ref' in rule:
                rule = schema['$defs'][rule['$ref'].split('/')[-1]]
            if 'enum' in rule:
                self.assertIn(value, rule['enum'])
            if 'const' in rule:
                self.assertEqual(value, rule['const'])
            types = rule.get('type', [])
            types = types if isinstance(types, list) else [types]
            if value is None:
                self.assertIn('null', types)
                return
            if 'object' in types:
                self.assertIsInstance(value, dict)
                self.assertEqual(set(value), set(rule['required']))
                for key, item in value.items():
                    check(item, rule['properties'][key])
            elif 'array' in types:
                self.assertIsInstance(value, list)
                for item in value:
                    check(item, rule['items'])
            elif 'integer' in types:
                self.assertIs(type(value), int)
                self.assertGreaterEqual(value, rule.get('minimum', 0))
            else:
                self.assertIsInstance(value, str)
                if 'pattern' in rule:
                    self.assertRegex(value, rule['pattern'])
        module = self.api()
        check(module.review_facts(ROOT / 'examples/disclosure-demo/manifest.json'), schema)
        with tempfile.TemporaryDirectory() as directory:
            fixture = self.fixture(directory, MULTI, {'revenue': '16', 'period': '2024'})
            check(module.review_facts(fixture.path), schema)
            fixture.gold[0]['expected'] = 'plain unsupported text'
            fixture.save()
            check(module.review_facts(fixture.path), schema)
            check(module.review_facts(Path(directory) / 'absent.json'), schema)

    def test_date_order_valid_dates_and_iso_range_period_is_not_inferred(self):
        for value in ('2025-02-30 to 2025-12-31', '2025-12-31 to 2025-01-01',
                      '2025-1-1 to 2025-12-31'):
            with self.subTest(value=value), tempfile.TemporaryDirectory() as directory:
                fixture = self.fixture(directory, 'Reporting period: ' + value + '.', {'period_start': '2025-01-01'})
                self.assertEqual(self.field(self.api().review_facts(fixture.path), 'period_start')['status'], 'ABSTAIN')
        with tempfile.TemporaryDirectory() as directory:
            fixture = self.fixture(directory, 'Reporting period: 2025-01-01 to 2025-12-31.', {'period': '2025'})
            self.assertEqual(self.field(self.api().review_facts(fixture.path), 'period')['status'], 'ABSTAIN')

    def test_currency_prefix_contradiction_cannot_support_revenue(self):
        with tempfile.TemporaryDirectory() as directory:
            text = CONTEXT.replace('Amount unit: millions', 'Amount unit: KRW millions') + 'Revenue: 95.'
            fixture = self.fixture(directory, text, {'revenue': '95', 'currency': 'USD', 'amount_unit': 'KRW millions'})
            report = self.api().review_facts(fixture.path)
            self.assertEqual(self.field(report, 'revenue')['status'], 'ABSTAIN')
            self.assertEqual(self.field(report, 'currency')['status'], 'ABSTAIN')

    def test_embedded_relevant_declaration_cannot_bypass_poisoning(self):
        for suffix in ('Commentary Currency: ???.', 'Prefix Basis: consolidated.',
                       'Narrative Amount unit: millions.', 'Embedded Revenue: 12.',
                       'Prose Period: 2024 annual.'):
            with self.subTest(suffix=suffix), tempfile.TemporaryDirectory() as directory:
                fixture = self.fixture(directory, CONTEXT + 'Revenue: 95. ' + suffix)
                self.assertEqual(self.field(self.api().review_facts(fixture.path), 'revenue')['status'], 'ABSTAIN')

    def test_target_cannot_accept_arbitrary_contradictory_continuation(self):
        base = MULTI.split('Extract')[0]
        tails = (' with the 2024 value instead', ' with its period',
                 ' with its period, currency, amount unit and scope instead',
                 ' with Currency: USD')
        for index, tail in enumerate(tails):
            with self.subTest(variant=index), tempfile.TemporaryDirectory() as directory:
                text = base + 'Extract only the 2025 revenue' + tail + '.'
                fixture = self.fixture(directory, text, {'revenue': '17', 'period': '2025'})
                self.assertEqual(verify(fixture.path)['status'], 'PASS')
                report = self.api().review_facts(fixture.path)
                self.assertEqual(report['cases'][0]['status'], 'ABSTAIN')
                self.assertEqual(self.field(report, 'revenue')['status'], 'ABSTAIN')
                self.assertEqual(self.field(report, 'period')['status'], 'ABSTAIN')

    def test_target_accepts_only_bare_or_exact_preserved_request_tail(self):
        base = MULTI.split('Extract')[0]
        for tail in ('', ' with its period, currency, amount unit and scope'):
            with self.subTest(bare=not tail), tempfile.TemporaryDirectory() as directory:
                text = base + 'Extract only the 2025 revenue' + tail + '.'
                fixture = self.fixture(directory, text, {'revenue': '17', 'period': '2025'})
                report = self.api().review_facts(fixture.path)
                self.assertEqual(report['cases'][0]['status'], 'SUPPORTED')

    def test_embedded_malformed_labels_do_not_require_colons_to_poison_context(self):
        variants = (('Currency EUR', 'currency', 'USD'), ('Revenue = 12', 'revenue', '95'),
                    ('Basis separate', 'scope', 'separate'),
                    ('Amount unit millions', 'amount_unit', 'millions'),
                    ('Period 2025 annual', 'period', '2025'))
        for declaration, field, value in variants:
            for prefix in ('', 'Commentary '):
                with self.subTest(field=field, embedded=bool(prefix)), tempfile.TemporaryDirectory() as directory:
                    fixture = self.fixture(directory, CONTEXT + 'Revenue: 95. ' + prefix + declaration + '.',
                                           {field: value, 'revenue': '95'})
                    self.assertEqual(verify(fixture.path)['status'], 'PASS')
                    report = self.api().review_facts(fixture.path)
                    self.assertEqual(self.field(report, field)['status'], 'ABSTAIN')
                    self.assertEqual(self.field(report, 'revenue')['status'], 'ABSTAIN')
        with tempfile.TemporaryDirectory() as directory:
            fixture = self.fixture(directory, CONTEXT + 'Revenue: 95. Commentary Revenue = 12.', {'scope': 'separate'})
            self.assertEqual(self.field(self.api().review_facts(fixture.path), 'scope')['status'], 'SUPPORTED')

    def test_cli_text_json_report_and_exclusive_output(self):
        manifest = ROOT / 'examples/disclosure-demo-v2/manifest.json'
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / 'fact-report.json'
            args = ['review-facts', manifest, '--profile', 'disclosure-facts.v1']
            human = self.run_cli(*args)
            self.assertEqual(human.returncode, 0, human.stderr)
            self.assertIn('SUPPORTED', human.stdout)
            result = self.run_cli(*args, '--json', '--report', target)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout), json.loads(target.read_text()))
            original = target.read_bytes()
            self.assertEqual(self.run_cli(*args, '--report', target).returncode, 2)
            self.assertEqual(target.read_bytes(), original)
            link = Path(directory) / 'link.json'
            link.symlink_to(target)
            self.assertEqual(self.run_cli(*args, '--report', link).returncode, 2)
            self.assertEqual(target.read_bytes(), original)
            dangling = Path(directory) / 'dangling.json'
            dangling.symlink_to(Path(directory) / 'missing.json')
            self.assertEqual(self.run_cli(*args, '--report', dangling).returncode, 2)
            self.assertFalse((Path(directory) / 'missing.json').exists())

    def test_cli_profile_required_unknown_and_error_diagnostics_are_safe(self):
        manifest = ROOT / 'examples/disclosure-demo/manifest.json'
        self.assertEqual(self.run_cli('review-facts', manifest).returncode, 2)
        self.assertEqual(self.run_cli('review-facts', manifest, '--profile', 'unknown').returncode, 2)
        with tempfile.TemporaryDirectory() as directory:
            fixture = self.fixture(directory, 'PRIVATE_INPUT_ONLY. ' + CONTEXT + 'Revenue: 95.', {'revenue': 'PRIVATE_EXPECTED_ONLY'})
            for extra in ([], ['--json']):
                result = self.run_cli('review-facts', fixture.path, '--profile', 'disclosure-facts.v1', *extra)
                self.assertEqual(result.returncode, 1)
                self.assertNotIn('PRIVATE_INPUT_ONLY', result.stdout + result.stderr)
                self.assertNotIn('PRIVATE_EXPECTED_ONLY', result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
