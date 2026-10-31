# UI 참조와 적용 — 0.2

2026-11-01 KST. 합성 보험 평가 데이터를 배포하기 전 검증·변경·차단 사유를 읽는 **정적 결과 문서**가 대상이다. 감독자의 비중복 조사 메모로 후보를 선정하고, 소유 작업자가 UI/UX Pro Max를 실제 읽어 UX 검색을 실행한 뒤 아래 1차 문서·공개 소스·라이선스를 재확인했다. 초기 구현이 이 자료에서 출발했다고 소급 주장하지 않는다.

| 확인한 참조 | 채택한 정보 구조와 실제 적용 | 제외한 요소와 이유 | 출처·권리 범위 |
| --- | --- | --- | --- |
| [GX Data Docs 0.18.21](https://docs.greatexpectations.io/docs/0.18/reference/learn/terms/data_docs/) | 기계 검증 결과를 브라우저에서 읽는 문서로 제공하고 요약에서 상세 근거로 이동한다. `reporting.render_html`, `_summary`, `_issues`, `_files`; 새 header issue-count/사유 anchor | GX 의존성·데이터 연결·원격 사이트·생성 템플릿·JS는 추가하지 않았다. 이번 도구는 로컬 합성 자료에 필요한 작은 계약만 실행한다 | 프로젝트 [LICENSE](https://github.com/fivetran/great_expectations/blob/develop/LICENSE)는 Apache-2.0으로 확인. 웹 문서는 버전 고정된 과거 설명이며 현재 API/서비스를 보증하지 않는다. 문서·UI 자산 권리는 별도이며 복사하지 않았다 |
| [DVC diff command source](https://github.com/treeverse/dvc/blob/main/dvc/commands/diff.py) | 상태별 변경과 hash·요약의 분리. 기존 `comparison._projection/_changes/compare`의 의미적 비교를 유지하고 `reporting._changes`와 header의 added/removed/modified entry 수를 연결 | DVC 런타임·캐시·클라우드 remote와 renamed 추정은 추가하지 않았다. 우리의 ID 변경은 추가/삭제이며 파일 위치 이동은 의미 변경과 다르다. 이전/새 정답 값을 보여주지 않는다 | [LICENSE](https://github.com/treeverse/dvc/blob/main/LICENSE) Apache-2.0. 공개 command 소스에서 상태·요약 패턴을 확인했으며 코드를 가져오지 않았다. 감독 조사에서 diff 문서의 429가 보고되어 소유 작업자는 접근 가능한 공개 소스를 확인했다 |
| [GitHub Actions run logs](https://docs.github.com/en/actions/how-tos/monitor-workflows/use-workflow-run-logs) | 결론→문제 위치→실패 근거의 계층. header gate status/issue-count → `#issues` → `_issues`의 code/location/reason; hash 표는 별도 근거 | GitHub의 CSS·아이콘·상표·서비스 화면과 rerun 버튼을 복제하지 않았다. 정적 문서의 gate PASS를 실제 CI 성공이나 사람의 승인으로 합치지 않는다 | GitHub Docs [LICENSE](https://github.com/github/docs/blob/main/LICENSE)는 CC-BY-4.0, [LICENSE-CODE](https://github.com/github/docs/blob/main/LICENSE-CODE)는 MIT로 확인. 문서 라이선스를 GitHub 서비스 UI·로고 복제 허가로 해석하지 않는다 |

## UI/UX Pro Max의 실제 검색과 적용

실행: `python -B <skill>/scripts/search.py "error summary validation" --domain ux -n 3`, exit 0. 원본 기록은 `reports/runs/20261031T163932Z-ui-pro/search.txt`다. Source는 ux-guidelines.csv, 상위 결과는 **Forms / Accessibility / Focusable Error Summary / Web**로 확인했다.

현재 화면에는 입력 폼이나 submit이 없으므로 상단의 요약·대상 연결·키보드 접근 원칙만 적용했다. 이슈가 있으면 정확한 개수와 `#issues` native anchor, 44px 이상의 링크 높이, 가시 초점을 제공하고 Enter로 해당 제목에 이동한다. 이슈 0건에는 작동하지 않는 링크를 만들지 않는다. 완전한 비교에는 변경 entry 수를 보이고 partial에는 수치를 만들지 않는다.

동적 `role=alert`·aria-live·JS 자동 초점, 앱 전용 safe area/haptics/Phosphor·웹폰트·아이콘 라이브러리를 추가하지 않았다. 실제 stack은 plain HTML/CSS이므로 Tailwind/React 스택 검색을 했다고 표시하지 않는다. 고정된 업무 문서 계층과 기존 ink/paper/teal 토큰을 유지한다. 단순히 “AI 느낌이 없다”는 점수나 사용자 선호 개선율을 만들지 않는다.

## 검증과 경계

HTML 단위 회귀, 실제 Chrome의 PASS/BLOCK/동일/변경/partial/악성 metadata/버전 재사용 경로, 좁고 넓은 화면·375px·가로 화면, Tab/Enter·이슈 이동·대비·넘침·본문 비노출을 실제로 검증했다. Chrome 24건과 원격 Chromium 24건이 통과했으며 실제 결과와 CI는 [VALIDATION.md](../VALIDATION.md), 계획은 [release-review plan](superpowers/plans/2026-11-01-release-review.md)에 기록한다. 명시된 원문·정답 경계와 외부 리소스 없는 CSP를 유지한다.

외부 코드·CSS·로고·아이콘·폰트·스크린샷·템플릿을 복사하지 않았다. 저장소의 화면은 우리 합성 예제를 실제 렌더링한 것이다. 출처는 설계 검토 근거이며 독립 전문가 검수나 인기 순위·규제 준수 인증이 아니다. 보안정책상 거절된 경로를 우회하거나 브라우저 잠금을 해제하지 않았다.
