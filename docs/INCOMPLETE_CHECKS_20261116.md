# Incomplete prerequisite diagnostics (2026-11-16 KST)

## Original requirements and gap

R04 case/gold correspondence, R05 split coverage and R07 accurate redacted diagnostics were implemented, but missing/invalid prerequisite records produced misleading absence failures. For example, an unreadable cases file caused three EMPTY_SPLIT findings and UNMATCHED_GOLD for all gold records. A malformed gold file caused MISSING_GOLD even though its contents were not inspectable.

## Change

Track case and gold structural completeness internally. Withhold absence claims that need a complete collection; emit CHECK_NOT_RUN with a fixed reason/location instead. The release stays BLOCK and exports/comparisons remain unavailable. Independent approval, duplicate and leakage findings from valid records remain failures. The same fixed recovery guidance flows into existing HTML without a design change. No input, declared rights, reviewers, source hashes or versions are rewritten.

## Validation

- Before implementation: four new regression cases failed; ordinary PASS control succeeded.
- After implementation: final full unittest discovery ran 169 tests, OK with 14 Windows symlink-privilege skips (155 executed without failure).
- Focused verification: 6/6 passed, including comparison and HTML propagation/redaction.
- git diff --check passed. Independent reviewer found no scoped blocker and independently reran focused 6/6 and full 169 tests OK (14 Windows symlink-privilege skips). This is an internal code review, not external certification.
- All fixtures synthetic. No raw input or gold body appears in the new diagnostic.

## Scope

This does not add authenticated lineage, rights verification or semantic leakage detection. Source/version/declared relationship comparison was already present; this change specifically corrects failure versus unavailable-check reporting. It is not a full per-rule execution ledger. The v1 report envelope and successful report behavior are unchanged.

## Source-reference prerequisites follow-up

A valid declared source ID was previously discarded when its license or reviewer text was invalid, causing unrelated SOURCE_REFERENCE failures. ID registration is now separate from the rights-text check; invalid rights metadata still blocks the dataset. A structurally incomplete source declaration or invalid source ID prevents proof of an unknown reference, so that absence check is CHECK_NOT_RUN at checks.source_references. Duplicate case source references remain independently detectable failures.

Verification: three new tests failed before implementation. After the change, focused 9/9 passed; full unittest ran 172 tests OK with 14 Windows symlink-privilege skips (158 executed without failure). git diff --check passed. Independent follow-up review found no blocking defect and directly reran focused 9/9, full 172 tests OK (14 skips), plus five temporary source-declaration edge scenarios. This is internal review, not rights certification. No source content, declared identity, version, hash or rights approval is repaired automatically.
