# Verification record

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
