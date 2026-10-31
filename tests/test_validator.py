"""Behavioral tests derived from CONTRACT.md, independent of implementation."""

import copy
import hashlib
import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from insuredatagate.validator import verify
from tests.helpers import DatasetFixture, encode_json, encode_jsonl


class ValidatorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.data = DatasetFixture(self.root)

    def report(self):
        return verify(self.data.path)

    def assert_block(self):
        result = self.report()
        self.assertEqual(result["status"], "BLOCK")
        self.assertTrue(result["issues"])
        for issue in result["issues"]:
            self.assertEqual(set(issue), {"code", "location", "message"})
            self.assertRegex(issue["code"], r"^[A-Z][A-Z0-9_]*$")
        return result

    def test_valid_fixture_has_complete_report(self):
        report = self.report()
        self.assertEqual(
            set(report),
            {"schema_version", "status", "dataset_id", "version", "manifest_sha256", "files", "counts", "issues"},
        )
        self.assertEqual(report["schema_version"], "insuredatagate.report.v1")
        self.assertEqual(report["status"], "PASS")
        self.assertEqual(report["dataset_id"], self.data.manifest["dataset_id"])
        self.assertEqual(report["version"], "0.1.0")
        self.assertEqual(report["issues"], [])
        self.assertEqual(report["manifest_sha256"], hashlib.sha256(self.data.path.read_bytes()).hexdigest())
        self.assertEqual(report["counts"], {"sources": 1, "cases": 3, "gold": 3, "train": 1, "validation": 1, "test": 1})
        self.assertEqual(len(report["files"]), 3)
        self.assertEqual(report["files"], sorted(report["files"], key=lambda item: item["path"]))
        for item in report["files"]:
            self.assertEqual(set(item), {"path", "sha256", "bytes"})
            raw = (self.root / item["path"]).read_bytes()
            self.assertEqual(item["sha256"], hashlib.sha256(raw).hexdigest())
            self.assertEqual(item["bytes"], len(raw))

    def test_verification_is_deterministic_silent_and_read_only(self):
        before = {str(path.relative_to(self.root)): path.read_bytes() for path in self.root.rglob("*") if path.is_file()}
        output, error = io.StringIO(), io.StringIO()
        with redirect_stdout(output), redirect_stderr(error):
            first, second = self.report(), self.report()
        self.assertEqual(first, second)
        self.assertEqual(output.getvalue(), "")
        self.assertEqual(error.getvalue(), "")
        after = {str(path.relative_to(self.root)): path.read_bytes() for path in self.root.rglob("*") if path.is_file()}
        self.assertEqual(before, after)

    def test_invalid_report_never_echoes_case_gold_or_source_contents(self):
        self.data.gold[0]["review_status"] = "DRAFT"
        self.data.save()
        rendered = json.dumps(self.assert_block(), ensure_ascii=False)
        for forbidden in ["PRIVATE_GOLD_DEMO_1", "RAW_INPUT_CASE_ONE", "SYNTHETIC_SOURCE_BODY_ONLY", str(self.root)]:
            self.assertNotIn(forbidden, rendered)

    def test_file_hash_tampering_blocks_for_every_role(self):
        for name in ["sources/rules.txt", "cases.jsonl", "gold.jsonl"]:
            with self.subTest(name=name):
                path = self.root / name
                original = path.read_bytes()
                if name == "cases.jsonl":
                    changed = original.replace(b"demo-author", b"demo-writer", 1)
                elif name == "gold.jsonl":
                    changed = original.replace(b"PRIVATE_GOLD_DEMO_1", b"CHANGED_GOLD_DEMO_1", 1)
                else:
                    changed = original + b" "
                path.write_bytes(changed)
                self.assert_block()
                path.write_bytes(original)

    def test_missing_manifest_returns_block_without_absolute_path(self):
        self.data.path.unlink()
        report = self.assert_block()
        self.assertIsNone(report["manifest_sha256"])
        self.assertNotIn(str(self.root), json.dumps(report))

    def test_missing_declared_file_blocks(self):
        self.data.source.unlink()
        self.assert_block()

    def test_manifest_requires_exact_keys(self):
        original = copy.deepcopy(self.data.manifest)
        for key in original:
            with self.subTest(missing=key):
                self.data.manifest = {k: v for k, v in original.items() if k != key}
                self.data.write_manifest()
                self.assert_block()
        self.data.manifest = {**original, "tenant_id": "untrusted"}
        self.data.write_manifest()
        self.assert_block()

    def test_manifest_wrong_types_and_values_block(self):
        original = copy.deepcopy(self.data.manifest)
        invalid = [
            ("schema_version", "unknown"), ("schema_version", 1),
            ("dataset_id", ""), ("dataset_id", "../dataset"), ("dataset_id", "a" * 129),
            ("version", "  "), ("version", 1), ("synthetic", False), ("synthetic", 1),
            ("synthetic", "true"), ("sources", []), ("sources", {}),
            ("cases", []), ("gold", None), ("dataset_id", {}),
        ]
        for key, value in invalid:
            with self.subTest(key=key, value=value):
                self.data.manifest = copy.deepcopy(original)
                self.data.manifest[key] = value
                self.data.write_manifest()
                self.assert_block()

    def test_manifest_malformed_and_nonobject_json_block(self):
        for raw in [b"{", b"null", b"[]", b"true", b'"text"', b'\xef\xbb\xbf{}', b'\xff', b"[" * 1200 + b"]" * 1200]:
            with self.subTest(raw=raw):
                self.data.path.write_bytes(raw)
                self.assert_block()

    def test_manifest_duplicate_json_keys_are_rejected(self):
        raw = encode_json(self.data.manifest).decode()
        raw = raw.replace('"version": "0.1.0"', '"version": "bad", "version": "0.1.0"')
        self.data.path.write_text(raw, encoding="utf-8")
        self.assert_block()

    def test_nested_manifest_duplicate_json_keys_are_rejected(self):
        raw = encode_json(self.data.manifest).decode()
        raw = raw.replace('"status": "APPROVED"', '"status": "DRAFT", "status": "APPROVED"')
        self.data.path.write_text(raw, encoding="utf-8")
        self.assert_block()

    def test_nonfinite_numbers_and_surrogates_block(self):
        for value in [float("nan"), float("inf"), -float("inf"), "\ud800"]:
            with self.subTest(value=repr(value)):
                original = copy.deepcopy(self.data.manifest)
                self.data.manifest["version"] = value
                self.data.path.write_bytes(json.dumps(self.data.manifest, ensure_ascii=True).encode())
                self.assert_block()
                self.data.manifest = original

    def test_source_declaration_requires_valid_exact_fields(self):
        original = copy.deepcopy(self.data.manifest["sources"][0])
        invalid = [("source_id", ""), ("license", " "), ("license", "a" * 129), ("approved_by", ""), ("approved_by", False), ("status", "DRAFT"), ("status", "REVOKED"), ("status", "anything"), ("status", []), ("sha256", "A" * 64), ("sha256", "0" * 63), ("path", True)]
        for key, value in invalid:
            with self.subTest(key=key, value=value):
                self.data.manifest["sources"] = [{**original, key: value}]
                self.data.write_manifest()
                self.assert_block()
        for missing in original:
            with self.subTest(missing=missing):
                self.data.manifest["sources"] = [{k: v for k, v in original.items() if k != missing}]
                self.data.write_manifest()
                self.assert_block()
        self.data.manifest["sources"] = [{**original, "untrusted": True}]
        self.data.write_manifest()
        self.assert_block()

    def test_file_reference_extra_fields_block(self):
        self.data.manifest["cases"]["extra"] = True
        self.data.write_manifest()
        self.assert_block()

    def test_source_ids_must_be_unique(self):
        self.data.manifest["sources"].append(copy.deepcopy(self.data.manifest["sources"][0]))
        self.data.write_manifest()
        self.assert_block()

    def test_file_roles_cannot_share_path(self):
        self.data.manifest["gold"] = copy.deepcopy(self.data.manifest["cases"])
        self.data.write_manifest()
        self.assert_block()

    def test_unsafe_paths_block_without_echoing_absolute_paths(self):
        paths = ["../outside.txt", "/outside.txt", "C:/outside.txt", self.data.source.as_posix(), "sources\\rules.txt", "./sources/rules.txt", "sources/../sources/rules.txt", "sources//rules.txt", "sources/rules.txt/", "https://example.invalid/rules", ""]
        for path in paths:
            with self.subTest(path=path):
                self.data.manifest["sources"][0]["path"] = path
                self.data.write_manifest()
                report = self.assert_block()
                self.assertNotIn("C:/outside.txt", json.dumps(report))

    def test_existing_parent_traversal_file_is_not_accepted(self):
        nested = self.root / "nested"
        nested.mkdir()
        data = DatasetFixture(nested)
        outside = self.root / "outside.txt"
        outside.write_bytes(data.source.read_bytes())
        data.manifest["sources"][0]["path"] = "../outside.txt"
        data.write_manifest()
        self.assertEqual(verify(data.path)["status"], "BLOCK")

    def test_directory_instead_of_file_blocks(self):
        self.data.manifest["sources"][0]["path"] = "sources"
        self.data.write_manifest()
        self.assert_block()

    def test_symlink_source_blocks_when_platform_allows_creation(self):
        link = self.root / "linked.txt"
        try:
            link.symlink_to(self.data.source)
        except (OSError, NotImplementedError):
            self.skipTest("OS does not permit symlink creation for this account")
        self.data.manifest["sources"][0]["path"] = "linked.txt"
        self.data.write_manifest()
        self.assert_block()

    def test_symlink_manifest_blocks_when_platform_allows_creation(self):
        link = self.root / "linked-manifest.json"
        try:
            link.symlink_to(self.data.path)
        except (OSError, NotImplementedError):
            self.skipTest("OS does not permit symlink creation for this account")
        self.assertEqual(verify(link)["status"], "BLOCK")

    def test_cases_require_exact_fields_and_reject_gold_field(self):
        original = copy.deepcopy(self.data.cases[0])
        for missing in original:
            with self.subTest(missing=missing):
                self.data.cases[0] = {k: v for k, v in original.items() if k != missing}
                self.data.save()
                self.assert_block()
        self.data.cases[0] = {**original, "expected": "PRIVATE_GOLD_NOT_ALLOWED"}
        self.data.save()
        self.assert_block()

    def test_case_wrong_types_and_values_block(self):
        original = copy.deepcopy(self.data.cases[0])
        invalid = [("case_id", 1), ("case_id", "not valid"), ("group_id", ""), ("split", "dev"), ("split", []), ("input", " "), ("input", "a" * 10001), ("input", {}), ("created_by", ""), ("source_ids", []), ("source_ids", "fictional-rules-v1"), ("source_ids", ["fictional-rules-v1", "fictional-rules-v1"]), ("source_ids", ["unknown"]), ("source_ids", [1]), ("source_ids", [{}]), ("source_ids", [["fictional-rules-v1"]])]
        for key, value in invalid:
            with self.subTest(key=key, value=str(value)[:30]):
                self.data.cases[0] = {**original, key: value}
                self.data.save()
                self.assert_block()

    def test_case_duplicate_ids_block(self):
        self.data.cases[1]["case_id"] = self.data.cases[0]["case_id"]
        self.data.save()
        self.assert_block()

    def test_gold_requires_exact_fields(self):
        original = copy.deepcopy(self.data.gold[0])
        for missing in original:
            with self.subTest(missing=missing):
                self.data.gold[0] = {k: v for k, v in original.items() if k != missing}
                self.data.save()
                self.assert_block()
        self.data.gold[0] = {**original, "tenant_id": "extra"}
        self.data.save()
        self.assert_block()

    def test_gold_review_requirements_block(self):
        original = copy.deepcopy(self.data.gold[0])
        invalid = [("expected", ""), ("expected", None), ("expected", "a" * 10001), ("review_status", "DRAFT"), ("review_status", "REJECTED"), ("review_status", "unknown"), ("review_status", []), ("reviewed_by", ""), ("reviewed_by", True), ("reviewed_by", "  DEMO-AUTHOR  ")]
        for key, value in invalid:
            with self.subTest(key=key, value=str(value)[:30]):
                self.data.gold[0] = {**original, key: value}
                self.data.save()
                self.assert_block()

    def test_missing_gold_blocks(self):
        self.data.gold.pop()
        self.data.save()
        self.assert_block()

    def test_unmatched_gold_blocks(self):
        self.data.gold[0]["case_id"] = "unknown-case"
        self.data.save()
        self.assert_block()

    def test_duplicate_gold_blocks(self):
        self.data.gold.append(copy.deepcopy(self.data.gold[0]))
        self.data.save()
        self.assert_block()

    def test_all_splits_required(self):
        self.data.cases[0]["split"] = "test"
        self.data.save()
        self.assert_block()

    def test_group_leakage_across_splits_blocks(self):
        self.data.cases[1]["group_id"] = self.data.cases[0]["group_id"]
        self.data.save()
        self.assert_block()

    def test_normalized_input_leakage_across_splits_blocks(self):
        self.data.cases[0]["input"] = "Policy\tA   Window"
        self.data.cases[1]["input"] = "  ＰＯＬＩＣＹ a\nwindow  "
        self.data.save()
        self.assert_block()

    def test_same_split_repetition_is_allowed(self):
        extra = {**self.data.cases[0], "case_id": "case-4"}
        self.data.cases.append(extra)
        self.data.gold.append({**self.data.gold[0], "case_id": "case-4"})
        self.data.save()
        self.assertEqual(self.report()["status"], "PASS")

    def test_jsonl_invalid_encodings_and_shapes_block(self):
        for filename in ["cases.jsonl", "gold.jsonl"]:
            original = (self.root / filename).read_bytes()
            for raw in [b"", b"\n", b"{}\n\n", b"[]\n", b"null\n", b"{}", b"{\n", b"\xff", b"\xef\xbb\xbf{}\n"]:
                with self.subTest(filename=filename, raw=raw):
                    (self.root / filename).write_bytes(raw)
                    self.data.repin()
                    self.assert_block()
            (self.root / filename).write_bytes(original)
            self.data.repin()

    def test_jsonl_duplicate_keys_are_rejected(self):
        for filename, records, field, value in [
            ("cases.jsonl", self.data.cases, "case_id", "case-1"),
            ("gold.jsonl", self.data.gold, "case_id", "case-1"),
        ]:
            with self.subTest(filename=filename):
                raw = encode_jsonl(records).decode()
                raw = raw.replace(f'"{field}": "{value}"', f'"{field}": "discarded", "{field}": "{value}"', 1)
                (self.root / filename).write_text(raw, encoding="utf-8")
                self.data.repin()
                self.assert_block()
                (self.root / filename).write_bytes(encode_jsonl(records))
                self.data.repin()

    def test_jsonl_rejects_nonfinite_and_surrogate(self):
        for filename, records, field in [("cases.jsonl", self.data.cases, "input"), ("gold.jsonl", self.data.gold, "expected")]:
            for value in [float("nan"), float("inf"), "\udfff"]:
                with self.subTest(filename=filename, value=repr(value)):
                    changed = copy.deepcopy(records)
                    changed[0][field] = value
                    (self.root / filename).write_bytes(b"".join((json.dumps(row, ensure_ascii=True) + "\n").encode() for row in changed))
                    self.data.repin()
                    self.assert_block()
            (self.root / filename).write_bytes(encode_jsonl(records))
            self.data.repin()

    def test_final_newline_is_optional(self):
        for filename in ["cases.jsonl", "gold.jsonl"]:
            path = self.root / filename
            path.write_bytes(path.read_bytes().rstrip(b"\n"))
        self.data.repin()
        self.assertEqual(self.report()["status"], "PASS")

    def test_oversize_manifest_blocks_without_digest(self):
        self.data.path.write_bytes(b" " * (1024 * 1024 + 1))
        self.assertIsNone(self.assert_block()["manifest_sha256"])

    def test_oversize_source_blocks(self):
        self.data.source.write_bytes(b"a" * (1024 * 1024 + 1))
        self.data.repin()
        self.assert_block()

    def test_source_at_size_limit_passes(self):
        self.data.source.write_bytes(b"a" * (1024 * 1024))
        self.data.repin()
        self.assertEqual(self.report()["status"], "PASS")

    def test_oversize_cases_and_gold_block(self):
        for filename in ["cases.jsonl", "gold.jsonl"]:
            with self.subTest(filename=filename):
                path = self.root / filename
                original = path.read_bytes()
                path.write_bytes(b" " * (10 * 1024 * 1024 + 1))
                self.data.repin()
                self.assert_block()
                path.write_bytes(original)
                self.data.repin()

    def test_more_than_ten_thousand_records_block(self):
        for i in range(4, 10002):
            self.data.cases.append({**self.data.cases[0], "case_id": f"case-{i}"})
            self.data.gold.append({**self.data.gold[0], "case_id": f"case-{i}"})
        self.data.save()
        self.assert_block()
        self.data.cases.pop()
        self.data.gold.pop()
        self.data.save()
        self.assertEqual(self.report()["status"], "PASS")

    def test_more_than_one_hundred_sources_block(self):
        source = self.data.manifest["sources"][0]
        for i in range(1, 101):
            name = f"sources/extra-{i}.txt"
            (self.root / name).write_bytes(self.data.source.read_bytes())
            self.data.manifest["sources"].append({**source, "source_id": f"source-{i}", "path": name})
        self.data.write_manifest()
        self.assert_block()
        self.data.manifest["sources"].pop()
        self.data.write_manifest()
        self.assertEqual(self.report()["status"], "PASS")


if __name__ == "__main__":
    unittest.main()
