"""Tiny synthetic dataset fixture; all identities and policies are fictional."""

import hashlib
import json
from pathlib import Path


def encode_json(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False) + "\n").encode("utf-8")


def encode_jsonl(values: list[dict]) -> bytes:
    return b"".join(encode_json(value) for value in values)


class DatasetFixture:
    def __init__(self, root: Path):
        self.root = root
        self.path = root / "manifest.json"
        (root / "sources").mkdir()
        self.source = root / "sources" / "rules.txt"
        self.source.write_bytes(b"SYNTHETIC_SOURCE_BODY_ONLY: fictional evaluation rules.\n")
        self.cases = [
            {
                "case_id": f"case-{i}",
                "group_id": f"group-{i}",
                "split": split,
                "source_ids": ["fictional-rules-v1"],
                "input": prompt,
                "created_by": "demo-author",
            }
            for i, (split, prompt) in enumerate(
                [
                    ("train", "RAW_INPUT_CASE_ONE: fictional document window?"),
                    ("validation", "RAW_INPUT_CASE_TWO: fictional required form?"),
                    ("test", "RAW_INPUT_CASE_THREE: fictional effective date?"),
                ],
                start=1,
            )
        ]
        self.gold = [
            {
                "case_id": case["case_id"],
                "expected": f"PRIVATE_GOLD_DEMO_{i}",
                "review_status": "APPROVED",
                "reviewed_by": "demo-reviewer",
            }
            for i, case in enumerate(self.cases, start=1)
        ]
        self.manifest = {
            "schema_version": "insuredatagate.manifest.v1",
            "dataset_id": "fictional-document-window",
            "version": "0.1.0",
            "synthetic": True,
            "sources": [
                {
                    "source_id": "fictional-rules-v1",
                    "path": "sources/rules.txt",
                    "sha256": "",
                    "license": "CC0-1.0",
                    "status": "APPROVED",
                    "approved_by": "demo-curator",
                }
            ],
            "cases": {"path": "cases.jsonl", "sha256": ""},
            "gold": {"path": "gold.jsonl", "sha256": ""},
        }
        self.save()

    def write_manifest(self):
        self.path.write_bytes(encode_json(self.manifest))

    def repin(self):
        for ref in [*self.manifest["sources"], self.manifest["cases"], self.manifest["gold"]]:
            ref["sha256"] = hashlib.sha256((self.root / ref["path"]).read_bytes()).hexdigest()
        self.write_manifest()

    def save(self):
        (self.root / "cases.jsonl").write_bytes(encode_jsonl(self.cases))
        (self.root / "gold.jsonl").write_bytes(encode_jsonl(self.gold))
        self.repin()
