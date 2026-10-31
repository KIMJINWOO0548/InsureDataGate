# Verification record

## 0.2.0 — release comparison and offline review

2026-11-01 KST. Implementation and local browser validation are complete; this section's remote 0.2 CI status is recorded after its actual run, independently of historical 0.1 CI below.

| Check | Observed result |
| --- | --- |
| Core/CLI regression after reference UX | 83 run, 80 passed, three local symlink permission skips; no failures |
| New comparison/reporting/CLI/safety subset | Initial 22 passed; fresh independent Astra review reran that subset successfully before the reference UX addition. Refined HTML/review subset: nine passed |
| Failure flow | Seven ordinary write/close/interrupt and source/gold modification/deletion scenarios failed before the stronger behavior; now pass |
| Review usability | Missing baseline version and missing-side counts shown as zero reproduced, then fixed with tests |
| Actual native keyboard | First rendered run failed Enter-to-main focus; focusable main fix passed the same browser regression |
| Actual Chrome 156, final reference UX | Six states × 375x812/390x844/844x390/1440x900 = 24 passed observations; no horizontal overflow or page external requests/resources, escaped metadata, native skip and issue-link navigation, 44px issue targets, captions/scopes; sampled text contrast minimum 5.4896:1 |
| Rendered inspection | Actual final desktop/mobile and partial/long-metadata captures inspected; balanced desktop grid and long values wrap. Skill evidence checker passed |
| 0.2 wheel/sdist | Local isolated installation passed compare, HTML, export and module/console commands; final source bundle checked separately after docs finalize |
| Optional development supply chain | Four exact browser release versions plus separate setuptools 84.2.1 build lock, upstream wheel SHA-256 values, actual require-hashes download/install; all environments are under this project; CLI wheel has zero runtime Requires-Dist |
| Remote 0.2 CI | Awaiting actual first 0.2 push/run; configuration adds an isolated Linux Chromium job and retained PNG/JSON evidence |

Rendered records: failed `reports/runs/20261031T162109Z-browser-fa89cf66/evidence.json`; final local pass `reports/runs/20261031T164901Z-browser-59646818/evidence.json`. Portable copies are in `docs/evidence/0.2.0/browser-red` and `browser-pass`, with the actual captures; the evidence checker passes the successful copy. Original 0.1 data and evidence are preserved. Screenshots in docs/images and deterministic HTML in docs/examples are generated from the real synthetic data. The Chrome MCP profile lock was a tool failure; official Playwright in a separate environment performed the successful render checks.

UI/UX Pro Max's Web-specific search and official GX Data Docs/DVC diff/GitHub Actions references, code-license headers and adaptation decisions are recorded in [UI_REFERENCES.md](docs/UI_REFERENCES.md). No external assets were copied. The initial raw safety test fixture cleanup issue was corrected; an isolated honest replay of the final independent test against preserved c09025e source confirms seven failures with no fixture errors (`reports/runs/20261031T163445Z-v020-red-replay-84d14e`). Current implementation passes those cases.

0.2 adds the scoped quality gates in docs/QUALITY_UPGRADE.md. No overall superiority score, external review, authenticated approval, semantic leakage discovery, real insurance accuracy or operational certification is claimed. Failed-write cleanup cannot make process kills, hardlinks or filesystem deletion denial atomic.

## 0.1.0 — preserved baseline evidence

The post-0.1 safety checkpoint `96b0ffd` is distinct from the initial 58-test release below: 60 local tests ran, 57 passed and three symlink checks were skipped. Two new test methods cover seven output/snapshot failure situations. Its [actual CI](https://github.com/KIMJINWOO0548/InsureDataGate/actions/runs/41218195507) completed successfully; the coordinating chat independently confirmed all six jobs. This checkpoint did not claim the later 0.2 comparison/HTML features.

2026-11-01 KST. Candidate 0.1.0. This file records observed checks; it is not a certification.

| Check | Observed result |
| --- | --- |
| Independent verifier red | exit 1 before validator implementation; missing module |
| CLI red | 11 tests, failures/errors before CLI implementation |
| Windows / Python 3.12.10 full suite after review fixes | 58 run, 55 passed, 3 symlink tests skipped: account cannot create symlinks |
| CLI subset before review | 11 passed, exit 0; two subsequent review regressions failed first, then passed |
| Windows directory junction | Real junction created without admin; validator returned BLOCK |
| Distribution build + isolated install | exit 0: wheel/sdist, matching wheel/source bytes, zero runtime Requires-Dist, contents checks, fresh venv with no-index/no-deps install, console/module commands outside checkout |
| Demo and safe export | PASS: six cases, two per split; export has exactly case_id/input/source_ids; existing output unchanged |
| GitHub Actions on ac01d9c | [Actual run](https://github.com/KIMJINWOO0548/InsureDataGate/actions/runs/41215644275): six jobs succeeded (Linux 3.11/3.12/3.13/3.14, Windows 3.12, package) |
| Remote Linux 3.12 logs | 58 run, 57 passed; one Windows-only junction skip; all three real symlink tests passed |
| Remote Windows 3.12 logs | 58 passed, no skips; real junction and all symlinks passed |
| Independent internal code review | Two reproduced CLI findings fixed with independent red-to-green regressions; no external human review |

Commands actually run: `py -3.12 -m unittest discover -s tests -v`, `py -3.12 -m unittest tests.test_cli -v`. Tests use temporary synthetic datasets. No CaseProof socket workaround was needed: this standalone CLI opens no HTTP server or database.

The filesystem tests that cannot run on this Windows account are explicitly skipped. The actual Linux and GitHub-hosted Windows logs were read through GitHub MCP and confirm real symlink execution. No source distribution or package has been published to a package registry. The build emits two harmless messages that no excluded `*.py[cod]` files were found; those are not suppressed or reported as failures.

Public source hashes, command exits and red/green evidence are in [docs/evidence/0.1.0](https://github.com/KIMJINWOO0548/InsureDataGate/tree/main/docs/evidence/0.1.0). Full local final execution: `reports/runs/20261031T154134Z-b96173/`. Later final Git HEAD, remote and CI metadata are recorded in a separate ignored completion report, avoiding a self-referential commit hash inside its own source.

SPECIFIED: requirements/contract/plan. IMPLEMENTED: CLI 0.1.0 and examples. VERIFIED: the checks above; final-tip CI is checked separately after the evidence commit. PRESENTABLE: Korean-first README, install instructions, fictional demo, tests, license, review and limitations. Repository is public at [KIMJINWOO0548/InsureDataGate](https://github.com/KIMJINWOO0548/InsureDataGate), branch `main`.

The source manifest's declared demo license was aligned with the repository's Apache-2.0 license; it remains a declaration checked for presence, not legal verification. Failed implementation/red runs, the first Git credential-helper wait and the one-shot retry with existing GitHub CLI authentication are retained in local execution history. No global credential configuration changed.

Declared rights and reviewer IDs are not authenticated; semantic leakage, personal-data discovery, legal accuracy and hostile concurrent filesystem replacement are outside this version's checks. The public demo is not a blind benchmark. PASS describes only the checks in [CONTRACT.md](docs/CONTRACT.md).

The coordinating chat also reported a separate read-only check: 58 tests, 54 passed and four environment skips, six-case demo PASS, plus independent confirmation of all six CI jobs and three Linux symlink passes. Its evidence remains in the coordinating project's `reports/runs/20261031T153844Z-insure-readonly-1d3cca96`; those reported results are separate from this chat's local 55-pass/three-skip run and are not external human review.
