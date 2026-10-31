# InsureDataGate Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans to implement this plan task-by-task. The user authorized execution, model routing, parallel work and milestone pushes in this chat.

**Goal:** 합성 보험 AI 데이터의 출처·파일·검수·분할을 검증하고 정답 없는 입력을 내보내는 CLI 0.1을 완성한다.

**Architecture:** 독립 Python 패키지. `validator.verify(Path) -> dict`가 파일을 읽고 결정적 보고서를 만들며, `cli.main(argv) -> int`만 출력 파일을 생성한다. 계약과 테스트를 분리하고 기존 CaseProof와 런타임 의존성을 만들지 않는다.

**Tech Stack:** Python 3.11+, standard library, setuptools 84.2.1 build backend, unittest, GitHub Actions.

**Spec:** `docs/CONTRACT.md`, `docs/REQUIREMENTS.md`. 초기 계약·red 증거 뒤에 작성한 보강 계획이며 날짜·승인·검증 이력을 소급 생성하지 않는다.

## Global constraints

- Runtime standard-library only; synthetic must be exactly true.
- Manifest/source 1 MiB; cases/gold 10 MiB; 10,000 records and 100 sources maximum.
- Inputs unchanged; outputs exclusive creation; no network/model call.
- Report PASS/BLOCK; CLI exits 0/1/2. Raw input/gold never appears in diagnostics.
- No unauthenticated identity/rights declaration becomes an authenticated approval claim.

## Review focus

1. Windows junction/reparse and manifest-parent links must block; own tests in Task 1.
2. Malformed enum/list/object types must return BLOCK instead of traceback; Task 1 adversarial cases.
3. File changes between verification and export must create nothing; Task 2 race regression.
4. Output already exists or disk write fails: preserve existing data and report failure; Task 2 output tests.
5. Wheel must execute outside checkout, while docs and demo survive sdist; Task 3 isolated install.

## File map

`src/insuredatagate/validator.py`: parsing, safe reads, contract/semantic checks. `cli.py`, `__main__.py`, `__init__.py`: commands and version. `tests/helpers.py`: independent synthetic fixture. `tests/test_validator.py`, `tests/test_cli.py`: contract/process tests. `examples/insurance-demo`: fictional source, cases, separate gold and pinned manifest. `pyproject.toml`, `MANIFEST.in`: distribution. `.github/workflows/ci.yml`: remote matrix. `README.md`, `docs/FORMAT.md`, `SECURITY.md`, `LICENSE`: usage/provenance. `VALIDATION.md`: observed results.

## Task 1 — Offline validation contract

Produces `verify(Path) -> dict`, `safe_read(Path, int) -> bytes`, `strict_json(bytes) -> object` for Task 2.

- [x] Write independent fixture and tests for strict inputs, hashes, rights/reviews and split leakage.
- [x] Run `py -3.12 -m unittest discover -s tests -p test_validator.py -v`; record real import failure before implementation.
- [x] Implement parsing and validation in validator.py with generic redacted errors and deterministic sorting.
- [x] Run validator suite; test group reuse gives BLOCK, valid three-split fixture gives PASS, size boundary accepts exactly the limit.
- [x] Review R01–R07, add reproducible platform/path failures, fix root cause once, commit and push verified core.

## Task 2 — Safe command line and input export

Consumes Task 1 report and safe read/parser. Produces `main(argv: list[str] | None = None) -> int` and console/module entrypoints.

- [x] Write tests/test_cli.py; run `py -3.12 -m unittest tests.test_cli -v` and preserve missing CLI failures.
- [x] Implement check/report/allowlist export, exclusive output creation, second manifest/cases digest checks.
- [x] Run CLI tests: output rows have exactly case_id/input/source_ids; existing output bytes unchanged; changed manifest/cases bytes block export.
- [x] Run full `py -3.12 -m unittest discover -s tests -v`, fix reproduced failures, commit and push.

## Task 3 — Installable portfolio artifact

Consumes Tasks 1–2. Produces wheel/sdist, examples, documentation and CI.

- [ ] Validate sample six-case manifest and gold-free export via actual CLI.
- [ ] Build with existing installed setuptools backend; create fresh venv and install only this local wheel with no index/dependencies. Run installed console outside checkout.
- [ ] Inspect archive contents: source, docs/demo in sdist; no environments, credentials, runtime reports in either archive.
- [ ] Add pinned Actions matrix on Linux Python 3.11–3.14 and Windows 3.12; push, read actual remote results, fix failures.
- [ ] Perform fresh independent internal review using Ponytail principles; reproduce actionable findings before fixes. This is not external human review.
- [ ] Record actual commands/exits/versions/failures/skips in VALIDATION.md and concise evidence; update this plan, commit/push, verify clean tree and matching remote HEAD.

Self-review: R01–R12 map to the three tasks; helper names match Task 2 imports. Platform-specific symlink skips must stay explicit and Linux CI must exercise real links. No unimplemented future subsystems are required for 0.1 completion.
