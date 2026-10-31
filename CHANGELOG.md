# Changelog

## 0.2.0 — 2026-11-01

- Compare validated releases using semantic hashes and sorted ID/field-only differences; block changed content that reuses a version.
- Generate deterministic offline HTML reviews with escaped metadata, CSP, explicit partial results and separate baseline/candidate versions.
- Add native issue-summary navigation and change-entry totals informed by UI/UX Pro Max, GX Data Docs, DVC diff and GitHub Actions; keep all visual assets original.
- Reread all verified references before export/comparison; discard newly created outputs after ordinary write/close/interrupt failures.
- Preserve the original demo and add a separate synthetic release candidate; extend installation self-checks to comparison and HTML.
- Preserve original JSONL record numbers after malformed earlier lines so findings identify the actual row to fix.

Final source verification: 84 tests (local 81 passed/three environment skips; CI Windows 84 passed), 24 real browser observations, isolated wheel install, seven successful CI jobs. Initial 83-test and historical 58/60-test records remain distinct in VALIDATION.md.

### Post-0.1 safety checkpoint — 96b0ffd

Before the 0.2 feature release, two independent test methods covering seven output/snapshot failure situations extended the local suite from 58 to 60 (57 passed, three environment skips). This checkpoint's six-job CI succeeded. Its counts are separate from the final 0.2 suite.

## 0.1.0 — 2026-11-01

- Offline synthetic-only manifest, source hash/rights declarations, case/gold review and split validation.
- Deterministic redacted PASS/BLOCK report; exclusive report and allowlisted model-input export.
- Separate fictional six-case insurance demo; Python console and module entrypoints.
- Independent unittest suite, build/install self-check, pinned cross-platform CI configuration.

Verification and known limits are recorded in VALIDATION.md; this version is not a certified approval or insurance decision service.
