# Verification record

2026-11-01 KST. Candidate 0.1.0. This file records observed checks; it is not a certification.

| Check | Observed result |
| --- | --- |
| Independent verifier red | exit 1 before validator implementation; missing module |
| CLI red | 11 tests, failures/errors before CLI implementation |
| Windows / Python 3.12.10 full suite after review fixes | 58 run, 55 passed, 3 symlink tests skipped: account cannot create symlinks |
| CLI subset before review | 11 passed, exit 0; two subsequent review regressions failed first, then passed |
| Windows directory junction | Real junction created without admin; validator returned BLOCK |
| Distribution build + isolated install | In progress; no success claimed yet |
| GitHub Actions | Configured; execution not yet checked |
| Independent internal code review | Two reproduced CLI findings fixed with independent red-to-green regressions; no external human review |

Commands actually run: `py -3.12 -m unittest discover -s tests -v`, `py -3.12 -m unittest tests.test_cli -v`. Tests use temporary synthetic datasets. No CaseProof socket workaround was needed: this standalone CLI opens no HTTP server or database.

The filesystem tests that cannot run on this Windows account are explicitly skipped. Linux CI must execute real symlinks before the release gate is complete. No source distribution or package has been published to a package registry.

Declared rights and reviewer IDs are not authenticated; semantic leakage, personal-data discovery, legal accuracy and hostile concurrent filesystem replacement are outside this version's checks. The public demo is not a blind benchmark. PASS describes only the checks in [CONTRACT.md](docs/CONTRACT.md).
