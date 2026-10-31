# Review workspace — 0.3 design

The additional user request resumes work after the verified 0.2 release. It asks for a complete comparison-review experience and stronger visual hierarchy, with no new project, server, runtime dependency, scripts or external assets. The existing audit is a review of saved 0.2 captures, not a fresh browser audit.

## Scope and choices

Implement the requested case/source dossier and recovery flow. Preserve `compare()` and the comparison.v1 JSON contract exactly; add `review()` and CLI `review BASE CAND` with `insuredatagate.review.v1`. Static HTML from existing check/compare also gets the clearer hierarchy, but source-impact relationships are available only in the enriched review command. A report generated without relationship data must not invent it.

Approaches considered: (1) recolor the current tables, which does not solve relationship or recovery work; (2) replace the CLI with a JS application, which adds dependencies and weakens the offline contract; (3) native HTML review workspace with explicit verified relationship data, selected here by the implementer within the requested scope. Local persistent review acknowledgements are deferred: the audit calls them a future candidate, and cases/source relationships and recovery take priority.

## Data contract

`comparison.review(baseline_path, candidate_path) -> dict` shares the same verified snapshots used to derive its comparison. Its top-level comparison keys have the existing values, except `schema_version` is `insuredatagate.review.v1`, and a `review` object is added. Legacy `compare` remains comparison.v1 without extra keys.

When comparison details are unavailable, `review` is `{available: false, cases: null, sources: null, summary: null}`. Invalid/different dataset identities do not expose invented relationships or zero counts. VERSION_REUSED retains the complete verified dossier while BLOCK remains BLOCK.

When available:

- `cases`: sorted by case_id. Each `{case_id, status, fields: {case: [field names], gold: [field names]}, sources: {baseline: [source IDs], candidate: [source IDs], changed: [changed linked source IDs]}, splits: {baseline: split or null, candidate: split or null}}`. Status is added, removed, modified, or affected. `affected` means no direct case/gold modification but a declared source reference changed. Added/removed records have empty field-name lists; their status explains the change.
- `sources`: sorted by source_id. Each `{source_id, status, fields: [field names], cases: {baseline: [{case_id, split}], candidate: [{case_id, split}]}, affected_case_ids: [sorted union IDs]}`. Include only added/removed/modified sources. Relationships come from BOTH checked snapshots, including removed references and source-only changes. They describe declared references, never causal proof or insurance correctness.
- `summary`: `{case_count, direct_case_count, source_count, source_only_case_count}`. Count unique review cases, not duplicated case/gold rows.

The only new disclosed values are identifiers, split names and relationship membership. No source body, case input, expected answer, old/new content values, creator or reviewer identities are added. Existing raw digest, snapshot recheck and output-preservation boundaries remain.

## Presentation contract

Dataset identity is the heading; versions and local PASS/BLOCK are a compact context row. Human review is a separate neutral/amber state, never red on a normal PASS and never approved. Put a BLOCK's cause and recovery before the work list. Unavailable counts say not checked; unchanged six-count tiles are replaced with a compact secondary inventory/disclosure. Show grouped direct case changes before source-only affected cases and source dossiers. A changed case must show input/gold field types together and link its changed source; the source lists linked case IDs/splits from both sides.

Use a desktop navigation rail and aligned detail region; on mobile show the first useful dossier or recovery within the first screen instead of six unchanged tiles. Native fragment filters must really hide/show their scoped entries and have visible selected/focus states; native anchors highlight their target. No inert buttons, fake reviewer state, automatic correction, authenticated approval, external assets or JavaScript. Full hashes remain available in native details; truncated fingerprints are explicitly labelled shortened, never verification substitutes. Keep tables only where row/column comparison helps, and restructure dense dossiers for narrow screens.

`guidance.recovery(code) -> {title: str, steps: list[str]}` provides deterministic generic instructions for issue types. Do not repeat unsafe OS errors, suggest weakening permissions, auto-create approvers, force SemVer ordering or alter data. Explain VERSION_REUSED, FILE_READ/partial, SHA mismatch, snapshot change, schema/JSONL, leakage, rights/review declarations and identity mismatch concretely.

## Verification and UI reservation

First independent RED tests, then affected and full unit suite; preserve original 0.1 demo bytes and comparison.v1 golden boundaries. Package and install 0.3 outside checkout, verify new review CLI and old commands, exclusive output safety and zero runtime dependencies. Actual browser control is RESERVED to the supervisor; do not launch CUA, Chrome, Playwright, a UI server or browser CI until allocated. Prepare the capture harness without running it. After allocation use independent disposable browser sessions, never user login tabs.

Capture plan: actual changed, source-only, version-reused BLOCK, unreadable side/partial, unchanged, added/removed and long/malicious values; 1440 desktop, 375 and 390 mobile plus landscape. Check first-screen useful content, selected filter results, native Tab/Enter, source↔case links, recovery visibility, details/full hashes, no overflow/external requests/raw content, CSP and contrast. Save source/renderer hashes, PNGs and honest failed attempts. Record fresh results separately from old 0.2 evidence. A quality claim needs inspected actual renders; test totals alone do not establish beauty.
