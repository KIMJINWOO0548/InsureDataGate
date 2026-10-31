# Dataset format

InsureDataGate reads UTF-8 JSON and JSONL. A manifest pins the exact bytes of every listed file with lowercase SHA-256 hashes. The parser rejects a UTF-8 BOM, duplicate JSON keys, unknown fields, invalid types, and blank JSONL records. Keep each JSONL record on one physical line.

## Minimal layout

```text
insurance-demo/
├── manifest.json
├── cases.jsonl
├── gold.jsonl
└── sources/
    └── rules.txt
```

The complete synthetic example is in [`examples/insurance-demo/`](../examples/insurance-demo/). The manifest shape and validation rules are normative in [`CONTRACT.md`](CONTRACT.md).

## Manifest

The manifest identifies a synthetic dataset, its version, a source declaration, and the pinned case and gold files. Paths are forward-slash relative paths below the manifest directory. Source status and reviewer fields are declarations; the tool cannot authenticate them or verify license terms.

```json
{
  "schema_version": "insuredatagate.manifest.v1",
  "dataset_id": "fictional-document-window",
  "version": "0.1.0",
  "synthetic": true,
  "sources": [{
    "source_id": "fictional-rules-v1",
    "path": "sources/rules.txt",
    "sha256": "<64 lowercase hex characters>",
    "license": "CC0-1.0",
    "status": "APPROVED",
    "approved_by": "fictional-demo-curator"
  }],
  "cases": {"path": "cases.jsonl", "sha256": "<64 lowercase hex characters>"},
  "gold": {"path": "gold.jsonl", "sha256": "<64 lowercase hex characters>"}
}
```

Hashes cover raw file bytes, including line endings. After changing any pinned file, calculate its new hash and intentionally update the manifest. Do not treat a hash as proof of authorship or approval.

## Cases and gold

A case has exactly `case_id`, `group_id`, `split`, `source_ids`, `input`, and `created_by`. Splits are `train`, `validation`, and `test`. Each split must have cases; a group cannot span splits. NFKC-normalized, case-folded, whitespace-collapsed duplicate inputs across splits block validation.

Gold is stored separately and has exactly `case_id`, `expected`, `review_status`, and `reviewed_by`. Each case must have one gold record, and its reviewer declaration must differ from its creator declaration. Gold is never included in exported model inputs.

All names and examples in this repository's demo are fictional. The demo's checklist is invented solely to exercise the file format; it is not insurance, legal, coverage, or payout guidance. See [the full contract](CONTRACT.md) for field limits, issue handling, export behavior, and security boundaries.
