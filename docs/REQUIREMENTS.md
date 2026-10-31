# 요구사항과 인수 기준

제품: InsureDataGate 0.1. 사용자: 합성 보험 AI 평가 데이터를 배포하는 개발자. 문제: 출처 파일, 검수 선언, 정답 파일 또는 분할이 바뀌어도 배포자가 일관성을 확인하기 어렵다. 사용자가 승인한 범위는 독립적인 데스크톱 프로젝트, 공개 GitHub 저장소, 단계별 커밋·푸시, 설치 가능한 도구와 실제 검증이다.

초기 계약은 구현 전에 작성했다. 이 요구사항·실행계획 문서는 사용자의 추가 요청에 따라 초기 red 테스트 및 구현 착수 후 보강했다. 사후 작성 문서를 사전 승인 기록으로 표현하지 않는다.

| ID | 요구사항 / 완료 기준 | 담당 파일 | 검증 |
| --- | --- | --- | --- |
| R01 | 합성 데이터만 수용; 정확한 v1 필드·타입·버전 | validator.py | manifest_wrong_types_and_values, exact_keys |
| R02 | 원문 hash 불일치·미승인 출처·권리 선언 누락 차단 | validator.py | file_hash_tampering, source_declaration |
| R03 | 상대 경로 경계·심볼릭 링크·Windows reparse 차단 | validator.py | unsafe_paths, symlink_source/manifest, 추가 리뷰 |
| R04 | case/gold 일대일, 미검수·자기 검수 선언 차단 | validator.py | gold_review, missing/unmatched/duplicate_gold |
| R05 | 세 split 존재, 그룹 및 정규화 동일 입력의 분할 누수 차단 | validator.py | all_splits, group_leakage, normalized_input_leakage |
| R06 | 중복 JSON 키·인코딩·surrogate·크기 및 레코드 제한 | validator.py | malformed, duplicate, nonfinite, oversize, limits |
| R07 | 결정적이며 원문·정답을 노출하지 않는 보고서, 입력 무수정 | validator.py | deterministic_silent_read_only, never_echoes |
| R08 | 검사 PASS 후 allowlist 입력만 JSONL export; 변경 시 차단 | cli.py | export_only_allowlisted, changed_cases/manifest |
| R09 | 보고서·export가 기존 파일을 덮어쓰지 않음; 오류 exit 구분 | cli.py | existing_outputs_preserved, missing_parent, usage |
| R10 | 표준 라이브러리만으로 실행; wheel/sdist 및 새 환경 실행 | pyproject.toml | 실제 build 및 격리 설치/entrypoint 검사 |
| R11 | 합성 예제, 한국어 사용법, 라이선스, 보안 범위 공개 | README/docs/examples | 예제 PASS 및 패키지 내용 검사 |
| R12 | 공개 원격 저장소, 단계별 push, 실제 CI 상태 확인 | .github/workflows | git remote/HEAD 및 GitHub Actions 실행 |

테스트 열은 `tests/test_validator.py`, `tests/test_cli.py`의 메서드명 일부다. 실제 명령·환경·결과는 `VALIDATION.md`가 정본이다. 문서의 요구사항과 테스트 수는 운영 적합성이나 인증을 증명하지 않는다.

## 선택한 설계와 대안

- 선택: Python 표준 라이브러리 CLI + 파일 기반 계약. 서버·DB·로그인 없이 로컬 파일의 일관성을 검사한다.
- JSON Schema 의존성: 이번에는 추가하지 않는다. strict JSON 파서와 명시적 필드 검사가 wire/type 경계와 의미 검사를 함께 담당한다.
- CaseProof 재사용: 제품 개념과 분리된 정답·증거 원칙을 계승한다. 기존 코드·DB·API를 복사하거나 의존하지 않는다.
- 모델 평가 플랫폼 연동: 첫 버전에는 필요하지 않다. 결과 JSON과 입력 JSONL을 사람이 검토하고 다른 도구에 전달할 수 있다.

## 위협과 한계

검증 대상은 신뢰할 수 없는 로컬 파일이다. JSON/경로/크기를 검증하고 출력은 새 파일만 생성한다. 실행 중 파일 교체·hardlink 공격, 자연어 정답 암기·의미적 중복, 실제 저작권·개인정보·본인 인증·법적 판단은 검증하지 않는다. APPROVED와 reviewer는 데이터의 선언이며 인증된 사람의 서명이 아니다. 공개 예제는 모두 미노출 benchmark로 사용할 수 없다. PASS는 명시된 검사에 대한 통과다.

## 완료 판단

사용자의 추가 상위 품질 요구에 따른 0.2 비교·HTML·실패 보강은 [QUALITY_UPGRADE.md](QUALITY_UPGRADE.md)와 [별도 계획](superpowers/plans/2026-11-01-release-review.md)에 기록한다. 위 R01–R12와 0.1 결과를 소급 변경하지 않는다.

R01–R12를 관찰 가능한 증거에 연결하고, 독립 내부 코드 리뷰의 실제 결함을 수정한다. 로컬 결과와 원격 CI, 구현과 외부 인증을 구분한다. 신규 기능을 더해 완료 기준을 계속 확대하지 않는다.
