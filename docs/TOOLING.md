# 실제 도구 사용

이 문서는 설치 목록이 아니라 이번 구현에서 호출하거나 읽고 적용한 도구의 역할을 기록한다. 사용자 PC의 전역 설정·훅을 수정하거나 새 MCP/플러그인을 설치하지 않았다.

| 도구 / 스킬 | 실제 역할 |
| --- | --- |
| GitHub MCP | 연결 계정 로그인 확인, Linux/Windows 실제 Actions 로그를 읽어 통과·건너뛰기와 파일 경계 검사 확인 |
| GitHub CLI / Git | 새 저장소 생성, 요청에 따라 공개 전환, 단계별 commit/push, Actions 조회 |
| Context7 MCP | setuptools 공식 문서에서 src 레이아웃·console entrypoint·build backend 확인 |
| Plugin Management MCP | Superpowers 플러그인의 설치·활성 상태 검색 확인 |
| Superpowers Writing Plans | 요구사항을 파일·인터페이스·검증 명령·완료 기준으로 나눈 실행 계획 작성 |
| Superpowers Verification Before Completion | 실행 결과를 확인한 뒤에만 통과로 기록 |
| Ponytail full / Review | 표준 라이브러리 우선, 서버·DB·LLM 의존성 배제, 실제 데이터 흐름·실패 입력 중심 리뷰 |
| ECC Python Patterns / Git Workflow | Python 패키지 구성, 범위가 분명한 커밋, 원격 이력 보존 |
| Auto Model Router | 프로젝트별 decide/plan 실행 후 모델별 leaf agent 실제 호출 |

Router 실행은 조정자 모델 자체를 변경하지 않는다. 검증기 구현은 GPT-6.1 Sol/medium, 문서·예제는 GPT-6 Luna/high가 담당했다. 독립 내부 리뷰는 GPT-6 Astra/low에 배정했다. 최초 독립 테스트는 Router 요청 이전에 시작한 작업이므로 소급해서 자동 라우팅으로 표시하지 않는다. 모델 선정과 병렬 실행을 관찰했지만 속도 향상을 비교 측정하지 않았다.

계획 보강은 사용자의 추가 요청에 따라 초기 계약·red 테스트·일부 구현 뒤에 이뤄졌다. [계획서](superpowers/plans/2026-11-01-insuredatagate.md)와 [검증 기록](../VALIDATION.md)은 이 순서를 보존한다. 별도의 기획 승인 대기는 추가하지 않고 사용자가 이미 승인한 구현을 계속했다.

0.1 포장 설정은 [setuptools 공식 quickstart](https://setuptools.pypa.io/en/latest/userguide/quickstart.html)와 [build backend 문서](https://setuptools.pypa.io/en/latest/build_meta.html)를 Context7으로 조회했다. 해당 단계에서는 기존 빌드 도구를 읽어 사용했고, 격리 설치 환경에는 이 프로젝트의 로컬 wheel만 설치했다.

## 0.2 품질 보강

- Auto Model Router의 새 plan 결과로 비교 구현 Sol/medium, HTML 구현 Luna/high, 독립 실패 흐름·최종 리뷰 Astra/low, 브라우저 검증 Sol/medium을 실제 배정했다. 조정자 모델 자체를 전환했다고 주장하지 않는다.
- Superpowers 계획/검증과 Ponytail의 최소 구현 원칙으로 stdlib snapshot·comparison·reporting을 분리했다. 별도 서버·DB·사용자 인증 체계를 추가하지 않았다.
- ECC Frontend Design Direction을 적용해 검토용 정적 보고서의 상태·반응형·초점·대비 기준을 먼저 기록했다. 번들 check-evidence.js를 실제 브라우저 기록에 실행했으며 렌더 화면도 직접 확인했다.
- Chrome DevTools MCP는 다른 세션의 프로필 잠금으로 실패했다. 브라우저/전역 설정을 변경하지 않고 공식 Playwright Python을 별도 `.runtime/browser-env`에 설치했다. 사용자가 필요한 공식 도구 설치를 허용한 뒤 수행했으며, CLI wheel 실행 의존성은 0개다.
- Playwright 1.64.1 및 직접/전이 개발 의존성 3종은 실제 설치 보고서와 PyPI의 해당 버전 wheel SHA-256으로 고정했다. `pip download --require-hashes`를 실제 실행했다. [공식 브라우저/CI 문서](https://playwright.dev/python/docs/browsers)는 Context7으로 조회했다.
- 고립된 headless Chrome 156에서 오프라인 5상태×2화면·네이티브 Tab/Enter·긴 metadata·HTML 주입·대비·넘침을 검사했다. 최초 초점 이동 실패와 수정 후 PASS를 구분해 보존한다. Linux Chromium CI는 별도 실행 결과로 기록한다.
- 후속 사용자 지시에 따라 UI/UX Pro Max SKILL을 실제 읽고 `error summary validation --domain ux`를 실행해 Web 상위 결과를 확인했다. 정적 문서에 필요한 이슈 개수·native anchor만 채택했다. GX/GitHub 공식 문서를 web 도구로, DVC command·세 프로젝트 라이선스 헤더를 연결된 GitHub MCP로 실제 읽었다. [적용·불채택 기록](UI_REFERENCES.md)을 공개한다.
- 최종 실제 렌더는 버전 재사용을 포함한 6상태×4화면(375/390/landscape/1440) 24건으로 확대했고, issue 링크의 44px 높이·가시 초점·native Enter 이동까지 확인했다. 기존 5×2 결과와 구분한다. 빌드 환경도 프로젝트 내부의 별도 hash 고정 환경으로 분리했다.
