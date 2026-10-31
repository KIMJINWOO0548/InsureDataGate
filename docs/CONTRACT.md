# InsureDataGate 0.1 contract

Status: SPECIFIED. Implementation and evidence are recorded separately in VALIDATION.md.

This is the preserved 0.1 contract. The compatible 0.2 additions and stronger checked-reread/output behavior are specified in [QUALITY_UPGRADE.md](QUALITY_UPGRADE.md).

## Purpose

A dependency-free, offline CLI for maintainers of synthetic insurance AI evaluation datasets. Validate a versioned manifest, source rights declarations, pinned file bytes, case/gold separation, reviews and split isolation. Export allowlisted model inputs only after all checks pass. No LLM, network, customer data, legal/insurance decision, or authenticated approval service. This is independently written companion tooling inspired by CaseProof, without importing its code/database/API.

## Input files

UTF-8 JSON/JSONL only; reject duplicate keys, NaN/Infinity, lone Unicode surrogates, invalid UTF-8, unknown fields and wrong types. A UTF-8 BOM is invalid. JSONL contains one nonempty JSON object per line; a final newline is optional; blank lines are invalid. Reject oversized files before parsing: manifest/source 1 MiB each, cases/gold 10 MiB each; at most 10,000 cases and 10,000 gold records, at most 100 sources. Short text fields are 1–128 non-whitespace characters (case/group/source/dataset IDs match `[A-Za-z0-9][A-Za-z0-9_.-]{0,127}`); input/expected are non-whitespace strings up to 10,000 characters. Text may contain ordinary whitespace; strings containing surrogate code points are rejected throughout.

Manifest exact fields:

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
    "approved_by": "demo-source-curator"
  }],
  "cases": {"path": "cases.jsonl", "sha256": "<sha256>"},
  "gold": {"path": "gold.jsonl", "sha256": "<sha256>"}
}
```

`synthetic` must be exactly true; `sources` is nonempty. Source status enum is APPROVED/DRAFT/REVOKED; only APPROVED passes. All sources need a nonblank license and approved_by declaration. No URL fetch or SPDX/rights verification. IDs and file paths are unique. Cases/gold file refs have exactly path and sha256. Version/license/approved_by are short text.

Paths are portable forward-slash relative paths below the manifest directory, with no backslashes, colon, empty segment, `.` or `..`. Reject absolute paths, symlink/reparse-point files or directories (including the manifest itself), non-files and resolved paths outside the root. No file may occupy two manifest roles. This protects ordinary local validation; concurrent filesystem replacement and hardlink attacks are outside the threat model. Check bytes against declared SHA-256; do not silently repin.

Case exact fields: `case_id`, `group_id`, `split`, `source_ids`, `input`, `created_by`. Split enum: `train`, `validation`, `test`. source_ids is a nonempty, unique list of known source IDs. At least one case in each split is required. Each group_id occurs in only one split. Normalize input with Unicode NFKC, casefold and collapsed whitespace; identical normalized inputs across splits block. Same-split repeats are allowed. This does not detect semantic/paraphrase or undeclared related-group leakage.

Gold exact fields: `case_id`, `expected`, `review_status`, `reviewed_by`. review_status enum: APPROVED/DRAFT/REJECTED; only APPROVED passes. Cases and gold must have a one-to-one correspondence and no duplicate IDs. Reviewed_by must differ from the matching case created_by after stripping/casefold. Identity strings are declarations, not authentication. Demo identities are explicitly fictional. Gold is not model input; unknown case fields (including expected) block. This cannot detect an answer embedded in natural-language input.

## Python API and reports

`insuredatagate.validator.verify(manifest_path: pathlib.Path) -> dict` returns a deterministic report, including invalid/missing input as BLOCK, without printing, writing or exposing raw case/source/gold contents or OS exception paths. It never mutates the dataset. Output fields:

- schema_version = `insuredatagate.report.v1`
- status = PASS or BLOCK
- dataset_id, version: valid manifest strings, otherwise null
- manifest_sha256: raw manifest bytes SHA-256, or null if unreadable/oversized
- files: sorted list of `{path, sha256, bytes}` for safely read declared files
- counts: `{sources, cases, gold, train, validation, test}`
- issues: sorted `{code, location, message}` objects (location is a field pointer or safe filename/record index; no raw text or absolute paths). Codes are stable uppercase identifiers, not API consumers' sole source of truth.

Schema-invalid inputs may stop early; collect useful independent semantic issues when records are structurally valid. No partial PASS; invalid referenced bytes must not be exported. No timestamps/absolute paths in reports. Hashes record consistency, not independent authenticity.

## CLI

`insuredatagate check MANIFEST [--json] [--report NEW_PATH]`: human summary by default, JSON report on stdout with --json, optional pretty UTF-8 JSON file. Exit 0 PASS, 1 BLOCK, 2 argparse/output I/O error. Malformed/missing input is BLOCK/1. Outputs use exclusive creation; existing files remain byte-for-byte unchanged; missing parent is an error. Errors never contain raw input contents.

`insuredatagate export-inputs MANIFEST --output NEW_PATH`: full validation first, exit 1 and create nothing on BLOCK; on PASS export JSONL with EXACTLY `case_id`, `input`, `source_ids` in original case order. Never include expected/review/gold fields. Exclusive creation; output failures exit 2. Recheck the cases bytes SHA-256 after reading them for export to reject stale/tampered bytes between validation and export. Diagnostics to stderr, no model data on stdout. Export file is user-controlled output, not an approval or blind-test certificate.

`insuredatagate --version` and `python -m insuredatagate` supported. Library and CLI are usable without external dependencies on Python 3.11+.

## Completion gates

Independent red tests, full passing tests, successful sample check, split-leakage and tampering demonstrations, model export gold-absence, safe output refusal, wheel/sdist and isolated wheel installation checks, CI configuration with actual remote run distinguished from local evidence, docs/license/provenance, and clean Git tree pushed to the user's new public repository. Runtime data, environments, credentials and generated distributions stay untracked. Progress pushes are milestone commits, not an unattended scheduler.
