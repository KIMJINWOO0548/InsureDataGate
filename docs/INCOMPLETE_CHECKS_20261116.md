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
