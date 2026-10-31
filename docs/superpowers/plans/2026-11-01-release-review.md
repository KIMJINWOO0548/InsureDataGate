# Dataset Release Review Implementation Plan

> **For agentic workers:** Use the approved parallel task boundaries and explicit interfaces below. User authorized implementation, internal review, commits and pushes. Read docs/QUALITY_UPGRADE.md and AGENTS.md first.

**Goal:** 데이터셋 버전 비교·정적 HTML 검토·실패 보존을 갖춘 0.2를 완성한다.

**Architecture:** 기존 validator에 안전한 snapshot 재읽기를 추가하고 comparison/reporting을 독립 모듈로 둔다. CLI는 파싱·출력만 조정한다. 실행 의존성은 표준 라이브러리만 유지한다.

**Tech stack:** Python 3.11+, unittest, HTML/CSS, 기존 setuptools와 GitHub Actions.

**Spec:** docs/QUALITY_UPGRADE.md; 기존 docs/CONTRACT.md와 호환되는 확장이다.

## Review focus

- write 및 close 실패 후 성공처럼 보이는 새 파일이 남지 않는가.
- export/compare가 source와 gold 변경까지 감지하는가.
- 표현 순서·파일 위치와 실제 의미 변경을 구분하는가.
- HTML이 악성 metadata를 실행하거나 정답을 노출하지 않는가.
- 비교 한쪽 BLOCK에서 빈 diff를 변경 없음으로 제시하지 않는가.

## Task 1 — Verified snapshot / 실패한 출력 정리

Files: validator.py, cli.py, tests/test_release_safety.py. Produces read_snapshot(Path, report)->dict.

- [x] 부분 write·close·interrupt, source/gold 변경·삭제의 독립 실패 테스트 작성·실패 관찰.
- [x] 안전한 전체 참조 재읽기와 LF 레코드 경계를 공유하고 export에 연결.
- [x] exclusive create 성공 뒤 실패한 출력만 제거; 기존 파일은 보존.
- [x] 해당 검사와 전체 회귀 실행, 증거 기록·커밋·푸시.

## Task 2 — 의미적 버전 비교

Files: comparison.py, tests/test_comparison.py, examples/insurance-demo-v2/. Consumes verify/read_snapshot. Produces compare(Path,Path)->dict.

- [x] 독립 red 테스트: 형식/순서/위치만 다른 동일성, 각 entity 추가·삭제·field 변경, version 재사용, 잘못된 side와 변경된 snapshot.
- [x] exact redacted schema, semantic digest, 정렬된 ID/field diff와 gate 구현.
- [x] 합성 v2 예제를 별도로 작성하고 원본 0.1 사례·정답은 보존.
- [x] 해당 검사·CLI 통합·전체 회귀, 증거 기록·커밋·푸시.

## Task 3 — Offline HTML review

Files: reporting.py, tests/test_reporting.py. Consumes verifier/comparison reports. Produces render_html(dict)->str.

- [x] red 테스트: escape·본문 비노출·CSP·결정성·빈/부분/BLOCK/변경 상태.
- [x] 정적 CSS·의미적 표·status/issue/diff/hash 렌더링 구현.
- [x] CLI check/compare --html 연결; 기존 파일 보존과 인수 오류 검사.
- [x] 실제 Chrome에서 390x844·1440x900, 키보드·초점·텍스트 대비·긴 값 확인; 화면과 JSON 증거 기록.

## Task 4 — Portfolio release gate

Files: __init__.py, pyproject.toml, README, VALIDATION, CHANGELOG, check_distribution.py, CI, docs/evidence/0.2.0.

- [x] 0.2 version·명령·계약·정확한 구현/검증 상태 정리.
- [x] 신규 wheel/sdist 내용·소스 일치·격리 설치·실제 새 명령 확인.
- [x] 새 내부 독립 리뷰의 재현된 결함을 red/green으로 수정, 전체 suite와 실제 CI 확인.
- [x] 선택적 hash 고정 Playwright 환경으로 Linux Chromium CI의 6상태×4화면 회귀를 실행한다. CLI 실행 의존성에는 포함하지 않는다.
- [x] 비교 기준의 달성·미달을 기록한다. 코드 checkpoint의 공개 main/SHA/CI를 확인했으며, 최종 증거 커밋의 main/local/remote 일치·clean tree·CI는 별도 completion 기록으로 확정한다.

Self-review: 세 모듈의 인터페이스와 소유권은 분리되어 있고 CLI만 통합을 소유한다. 성능/모델/인증/프로덕션 기능을 이 계획에 추가하지 않는다. 새 기능 수로 전체 프로젝트 우열을 주장하지 않는다.

검증 결과: 최종 코드 f26ecf7의 7개 CI job 성공, 로컬 84개(81 PASS/3 환경 SKIP), 원격 Windows 84 PASS, Linux 3.12 83 PASS/1 Windows 전용 SKIP, 실제 브라우저 6상태×4화면 24 PASS. 초기 83개 기록·58개 baseline·60개 안전성 checkpoint와 혼합하지 않는다. 최종 문서 tip의 상태는 VALIDATION에 설명한 별도 completion 기록을 기준으로 한다.
