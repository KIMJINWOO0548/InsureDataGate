# Review Workspace Implementation Plan

> For agentic workers: use bounded subagent-driven development with the explicit ownership below. Implementation, focused commits and pushes are already authorized. Browser control remains reserved until allocated.

**Goal:** Complete the case/source comparison and error-recovery workflow with a coherent, usable offline review UI.

**Architecture:** Reuse checked comparison projections for an additive review.v1 report; preserve comparison.v1. Render native HTML controls and grouped dossiers without JS. CLI owns integration and existing exclusive output behavior.

**Tech stack:** Python stdlib, unittest, HTML/CSS; existing optional pinned packaging/browser environments.

**Spec:** docs/superpowers/specs/2026-11-01-review-workspace-design.md

## 1. Verified relationship report — delegated Sol/medium

Ownership: comparison.py and tests/test_review.py. No other writes or Git mutations.

- [x] Independent RED for case+gold grouping, both-side source impact, source-only affected cases, added/removed references, invalid side/identity, snapshot changes, determinism, redaction and unchanged comparison.v1 schema.
- [x] Implement shared checked projections and additive review report.
- [x] Run affected and existing comparison/safety tests, return evidence and stop.

## 2. Native review presentation — delegated Sol/medium

Ownership: reporting.py, test_reporting_workspace.py and necessary presentation-only assertions in current reporting tests. No other writes or Git mutations.

- [x] RED for cause/recovery priority, unique case dossier, linked source impact, filters, compact inventory and full-hash disclosure.
- [x] Implement aligned context/navigation/detail hierarchy, mobile useful-first order, real CSS/native filters and links; preserve escaping/CSP/raw-content boundaries.
- [x] Run presentation unit checks; no browser launch while reserved. Return evidence and stop.

## 3. Integration and provenance — coordinator

- [x] Read the two supervisor records, apply Product Design audit framework and targeted UIPro query; inspect actual primary-source reference images without browser manipulation and document reuse limits.
- [x] Add guidance and review CLI, meaningful regressions, 0.3 version/contract/docs; regenerate real HTML examples and preserve original demo.
- [x] Full suite, build/install and exact comparison.v1 compatibility checks; focused commit/push after the independent screen lease was allocated.

## 4. Fresh visual gate — waits for screen allocation

- [x] Update optional harness for real filters, source/case navigation, first viewport priorities and full hash disclosures.
- [x] After allocation only, capture/inspect desktop, 375/390, error/partial/long values and keyboard; compare current renders with actual references and fix concrete defects.
- [x] Source package, focused commits/pushes and seven-job source CI verified. Final evidence-commit CI, clean local/remote SHA and final distribution hashes are recorded separately after this plan is committed, avoiding a self-referential SHA.
