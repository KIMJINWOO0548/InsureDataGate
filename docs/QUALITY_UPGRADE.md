# 0.2 — 검토 가능한 데이터셋 릴리스

사용자의 추가 요구: 기존 프로젝트보다 높은 완성도를 목표로 한다. 비교를 위해 CaseProof의 현행 README/STATUS와 MotorClaimLab의 README를 읽었으며 다른 프로젝트 파일은 변경하지 않는다. 서로 목적이 달라 전체 우열 점수는 만들지 않는다. 아래 InsureDataGate 고유 작업 흐름을 구현하고 관찰 가능한 결과로 평가한다.

| 품질 축 | 0.1 상태 | 0.2 완료 기준 |
| --- | --- | --- |
| 변경 검토 | 단일 manifest PASS/BLOCK | 두 검증된 데이터셋의 의미적 변경·버전 재사용 검출 |
| 사람의 검토 | CLI/JSON | 네트워크·스크립트 없는 단일 HTML, 390/1440px 실제 화면 검사 |
| 데이터 경계 | cases/manifest export 재확인 | 검증한 모든 참조 파일 재확인, 해당 cases 바이트만 export |
| 출력 실패 | 기존 파일 보호·exit 2 | 생성한 파일의 write/close/interrupt 실패 정리, 원래 파일 보존 |
| 재현성 | 독립 red/green·wheel 설치·CI | 기존 계약 회귀 + 새 비교/HTML/실패 테스트, 새 wheel 격리 설치와 실제 CI |

기존 CaseProof는 서버·승인 워크플로가 강점이며 MotorClaimLab은 연구 분석 목적이다. 이번 범위는 데이터셋 변경 검토와 휴대 가능한 결과물에 집중한다. 기능 수·테스트 수로 보험 업무 정확성이나 프로젝트 전체 우위를 주장하지 않는다.

## 공통 강화

`validator.read_snapshot(manifest_path: Path, report: dict) -> dict`는 verify가 생성한 PASS 보고서만 소비한다. manifest SHA-256과 모든 source/cases/gold 파일의 관찰 hash 및 선언 hash를 안전한 재읽기로 재확인한다. 결과는 내부용 `{manifest, cases, gold}`이며 raw source는 반환하지 않는다. 불일치/누락/읽기 실패는 generic ValueError다. compare와 export가 공유한다. JSONL은 LF만 레코드 구분자로 사용한다.

이는 검증 후 일반적인 파일 수정도 차단하기 위한 강화다. 파일시스템 트랜잭션이나 공격자의 동시 교체·hardlink 방어를 제공하지 않는다.

exclusive 출력 생성에 성공한 후 write/close/interrupt가 실패하면 자신이 생성한 출력만 제거하고 실패를 반환한다. open이 거절된 기존 파일은 제거하지 않는다. 강제 프로세스 종료·삭제 권한 상실·디스크 자체 고장까지 원자성을 보장하지 않는다.

## Compare 계약

API: `comparison.compare(baseline_path: Path, candidate_path: Path) -> dict`. CLI: `compare BASELINE CANDIDATE [--json] [--report NEW_JSON | --html NEW_HTML]`. check에도 `--html NEW_HTML`을 추가하며 --report와 상호 배타다. 기존 check/export 호출은 유지한다. exit 0=검사/비교 성공, 1=BLOCK, 2=인수/출력 오류. PASS는 릴리스 승인과 다르다.

비교 보고서 정확한 최상위 필드:

`schema_version="insuredatagate.comparison.v1", status, baseline, candidate, content_changed, review_required, changes, issues`.

각 side: `{status, dataset_id, version, manifest_sha256, content_sha256, counts}`. counts는 verify 보고서와 같다. gate 미통과 또는 snapshot 읽기 실패 시 content_sha256=null. issues는 안전한 `{code,location,message}`이고 side의 위치를 baseline./candidate.로 접두한다.

changes: `{cases_added:[id],cases_removed:[id],cases_changed:[{case_id,fields}],gold_changed:[{case_id,fields}],sources_added:[id],sources_removed:[id],sources_changed:[{source_id,fields}]}`. 모든 목록과 fields는 사전순 정렬한다. gold 추가/삭제는 일대일 cases 추가/삭제로 표시한다. 양쪽 PASS·동일 dataset_id·재읽기 성공 전에는 changes=null, content_changed=null, review_required=true다.

의미적 projection은 고정 schema/synthetic, source의 source_id/실제 byte hash/license/status/approved_by, 모든 case/gold 필드다. version·ref path·cases/gold byte hash·레코드 순서·source 배열 순서·source_ids 순서는 제외한다. source_ids는 정렬하고 ID 기준으로 레코드를 정렬해 canonical JSON(sort_keys,compact separators,UTF-8)의 SHA-256을 계산한다. input/expected 문자열은 정확히 보존하며 Unicode 누수 정규화를 의미 비교에 적용하지 않는다. source의 공백 변경도 byte hash 변경이다.

양쪽 gate PASS + 같은 dataset_id가 필요하다. content_changed=true인데 version 문자열이 같으면 VERSION_REUSED로 BLOCK하고 계산한 changes는 유지한다. 버전 비교는 opaque equality뿐이며 SemVer 순서를 강제하지 않는다. version만 바뀌면 content_changed=false, changes는 빈 목록이다. review_required는 content 변경 또는 version 변경이면 true다. 자동 승인하지 않는다. 보고서는 이전/새 field 값이나 input/expected/source 본문을 반환하지 않는다.

## HTML 계약과 디자인

API `reporting.render_html(report: dict) -> str`. verifier 보고서 또는 위 comparison 보고서를 받아 결정적 UTF-8 HTML을 반환한다. 동적 값은 html.escape(quote=True)로 처리한다. raw JSON/script/외부 리소스/이미지/폰트/네트워크/JS를 포함하지 않는다. CSP는 default-src none, style-src unsafe-inline, base-uri none, form-action none이다.

사용자: 데이터를 배포하기 전에 gate·변경 목록·근거 해시를 검토하는 개발자. 첫 화면: 제품 이름, 데이터셋/버전, PASS/BLOCK 및 review required, 사례·분할 요약. 아래: 비교 변경 목록(해당할 때), 차단 사유, 관찰된 파일 hash. dataset/version/ID/상대 파일명은 보고서에 포함되므로 공유 전 검토한다. case/input/gold/source 본문은 포함하지 않는다.

디자인: 조용한 업무 검토 문서, 잉크색 본문·크림 배경·청록/적색 상태, 표 위주, 긴 hash 줄바꿈, 시스템 폰트, 단일 문서. semantic heading/table caption/scope, skip link와 visible focus, 색 이외 상태 텍스트, print CSS를 제공한다. 표·목록은 390x844 및 1440x900에서 넘치지 않아야 한다.

상태: success=PASS 요약; error=BLOCK와 사유·원본 수정 후 재검사; partial=side BLOCK일 때 비교 수치 미제공을 명시; empty=변경 없음 또는 issue 없음 설명. loading/permission은 정적 오프라인 결과물이라 해당 없음. OS 읽기 거절은 BLOCK이며 권한 변경을 자동 실행하지 않는다.

## 인수 기준

기존 전체 회귀 + 의미적 동일성/추가/삭제/수정/정답/출처/버전 재사용/잘못된 입력 비교 + 모든 파일 snapshot 변경 + write/close/interrupt + HTML escaping/본문 비노출/CSP/결정성 + CLI 기존 파일 보존. 실제 브라우저의 PASS/BLOCK/동일/변경/partial 상태와 좁고 넓은 화면을 확인한다. 새 버전 package와 실제 CI를 확인하고 원격 SHA 및 clean tree를 남긴다. 전문가/운영 인증은 별도다.
