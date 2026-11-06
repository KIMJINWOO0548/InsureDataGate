# Gate finding types — public reference and original implementation

2026-11-06 UTC. Scope: recurring-blocker navigation in the existing static offline
HTML report; base `37aa133`. No validator/JSON-schema/digest change.

## Sources and confidence

| Source | Actual observation |
| --- | --- |
| [GX Core result formats](https://docs.greatexpectations.io/docs/core/trigger_actions_based_on_results/choose_a_result_format/) | Public documentation distinguishes summary feedback from detailed diagnostics and controls excess/raw result data. |
| REA 6.8.0 browser capture of that URL | Actual documentation heading, format options and reference tables. This is docs observation, not a GX Cloud account or validation run. |

REA exited 0; owned Chromium 156.0.8078.80 cleanup reported
`terminated-owned-process`. Local accessibility artifact SHA-256:
`a2084729d50893c0e7d8c52d7c14c185b197923c72ae5c1590a66254b3d39e68`.
Reference screenshots/raw captures remain outside the repository. No dataset,
case/gold/source body or private identifier was sent to GX.

## Recon and implementation

- S01: public result-format documentation / summary-to-detail explanation.
- S02: existing offline report / gate findings and safe locations.
- F01: total findings and types → choose type → inspect locations/reasons → return.
- Edges: no findings, repeated codes, one finding, malicious metadata, partial
  comparison, narrow viewport, keyboard-only navigation.

The transferred pattern is an overview before details. **Issue-code grouping and
native return links are this project's original adaptation**, not a claim that
GX uses this layout. Count findings rather than unique records, severity or
certified risk. Keep every detail visible, preserve the input report, and use
numeric safe anchor IDs instead of embedding untrusted codes in selectors/URLs.
No JavaScript/network runtime; existing raw-content redaction and CSP remain.

## Replica and checks

Applied installed `replica-recon/SKILL.md` and `replica-diff/SKILL.md`. Actually
executed local `replica-diff/parity.py features.csv --json`, exit 0;
[parity.json](parity.json) measures only one selected pattern in a self-authored
matrix, not whole-product parity, external assessment or release approval.
No layout score is claimed.

- RED: 3 new tests, 2 expected failures for missing counts/groups.
- GREEN: 22 affected/fixture tests passed: counts/targets, retained
  locations/messages, determinism, nonmutation, escaping, redaction, empty
  navigation and preserved eight-state fixture generation. Fixture tests are
  not actual browser execution.
- Full Windows sandbox: 147 tests, no assertion failures, 10 symlink privilege
  errors, 4 OS capability skips; exit 1. Baseline 144 tests had the same errors
  and skips. This is not a passing whole suite.
- Existing browser runner additionally checks counts and native focus into a
  type and back, across its eight states/four viewports. Coordinator execution
  evidence is separate.

Python 3.12 used `TEMP`/`TMP` in an ignored local run directory because default
sandbox temp was unwritable. Logs/summary remain in ignored
`reports/runs/reference-improvements-20261106/`. No dependencies/global settings,
data bytes, approval declarations, publication or production access changed.

## Coordinator host verification

The existing `.runtime/browser-env` environment was reused without installation. `scripts/check_report_browser.py --output reports/runs/reference-browser-20261106 --channel chrome` passed all eight states/four viewports (**32 captures**, exit0), including native keyboard navigation from finding types into details and back, overflow, privacy, CSP and accessibility structure checks. Exact evidence is in that run's `evidence.json`.

The full host unittest run remains **147 tests, 10 errors, 3 skipped**, exit1. All ten errors are Windows symlink privilege 1314 in existing safety fixtures. No assertion failure was hidden, and OS security settings were not changed. The host skip count differs from the sandbox count above; neither run is a whole-suite PASS. Relevant behavior tests are **22/22 PASS**.
