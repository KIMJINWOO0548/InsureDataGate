# Release review workspace — 0.3

기존 `check`, `compare`, `export-inputs`와 `insuredatagate.comparison.v1` JSON은 유지한다. 새 명령은 `insuredatagate review BASELINE CANDIDATE --html NEW_HTML`이며 `--json` / `--report NEW_JSON`도 지원한다. 출력은 항상 새 파일에만 쓰고 기존 파일을 덮어쓰지 않는다.

## 명시적 스키마 경계

새 보고서는 `insuredatagate.review.v1`이다. 비교 v1의 모든 필드를 유지하되 schema_version이 새 이름이고 `review` 객체를 추가한다. v1의 필드나 hash 의미를 조용히 바꾸지 않는다. 입력 manifest 형식은 계속 `insuredatagate.manifest.v1`이다.

`review`는 비교에 사용한 **동일한 검증 완료 snapshot**에서 도출한다. 데이터셋 ID 불일치·한쪽 입력 오류·검증 후 파일 변경에서는 `available: false`, `cases`, `sources`, `summary`는 null이다. 0건/변경 없음으로 표시하지 않는다. 내용이 달라 같은 버전을 재사용한 경우는 BLOCK이지만, 양쪽 snapshot을 검증할 수 있었으므로 변경 관계는 제공한다.

| 필드 | 의미 |
| --- | --- |
| cases | case_id로 정렬한 검토 단위. 같은 ID의 사례 필드와 gold 필드 변경을 한 항목에 묶는다 |
| cases[].status | added / removed / modified / affected. affected는 직접 사례·gold 변경은 없고 참조한 source가 변경됐다는 뜻이다 |
| cases[].fields | case / gold의 변경 **필드 이름**만 제공한다. 추가·삭제 항목은 빈 목록이며 status로 구별한다 |
| cases[].sources | baseline / candidate의 출처 ID와 그중 변경된 source ID의 합집합 |
| cases[].splits | 양쪽의 split 이름; 해당 case가 없는 쪽은 null |
| sources | 추가·삭제·수정된 source만 source_id로 정렬. 양쪽의 선언된 case_id/split 관계와 영향 ID 합집합을 제공한다 |
| summary | case_count, direct_case_count, source_count, source_only_case_count. case/gold 행을 중복해서 사례 수로 세지 않는다 |

관계는 선언된 참조와 검증된 파일 일관성을 나타낸다. 출처 변경이 실제 답변 오류를 일으켰다는 인과 추론이나 보험 정확도 검증이 아니다. 사례 input·gold expected·source 본문·검토자 값은 새 보고서에 추가하지 않는다. 새로 공개되는 split 이름과 참조 관계도 공유 전 확인해야 한다.

## 검토 순서

1. 데이터셋과 두 버전, 로컬 PASS/BLOCK을 확인한다. 사람의 검토·승인은 별개다.
2. BLOCK이면 상단 원인·일반 복구 안내를 읽는다. 원본 파일·권한·승인자를 자동 변경하지 않는다. candidate를 고친 뒤 **새 결과 파일**로 전체 검사를 다시 수행한다.
3. 직접 변경된 사례에서 사례·gold 변경 종류를 같이 읽는다. 연결 source로 이동해 baseline/candidate 양쪽의 case·split 관계를 확인한다.
4. source-only 영향은 직접 내용이 바뀐 사례와 구분한다. 필터와 native anchor로 필요한 검토 대상을 찾는다.
5. 총량과 전체 hash는 부차적 근거로 펼쳐 본다. 짧은 fingerprint는 명시적 축약 표시이며 전체 SHA-256을 대체하지 않는다.

정적 HTML/CSS이며 JavaScript, 외부 폰트·이미지·네트워크 요청이 없다. 저장되는 사용자 체크 상태나 인증된 승인 버튼은 없다. 로컬 검토 확인 파일 기능은 후속 후보로 남긴다. 이번 추가 요구는 사례/source 관계와 복구 동선에 집중한다.

## 실제 검증 상태

기존 0.2의 58dc7a5 / 7-job CI와 캡처는 이번 화면의 fresh 검증이 아니다. 화면 제어가 예약된 동안은 브라우저를 실행하지 않았고, 사용자가 독립 headless 세션을 배정한 뒤 새 0.3 캡처와 실제 키보드/필터 검증을 수행했다. 단계별 결과와 최종 source SHA/CI는 VALIDATION과 별도 completion 기록을 따른다.

상태는 URL fragment 하나로 표현한다. All items는 사례 검토 단위와 source 검토 단위의 합이다. Cases는 직접 변경된 사례, Linked는 직접 변경이 없지만 변경 source를 참조한 사례, Sources는 변경 출처다. 연결 항목으로 이동하면 All 상태로 돌아가 해당 대상과 rail을 강조한다. native filter 링크의 결과가 존재하지 않는 경우에는 해당 그룹의 명시적 빈 상태를 보여 준다. 일반 All 화면에서는 빈 그룹을 숨긴다.
