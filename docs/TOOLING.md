# 실제 도구 사용

이 문서는 설치 목록이 아니라 이번 구현에서 호출하거나 읽고 적용한 도구의 역할을 기록한다. 사용자 PC의 전역 설정·훅을 수정하거나 새 MCP/플러그인을 설치하지 않았다.

| 도구 / 스킬 | 실제 역할 |
| --- | --- |
| GitHub MCP | 연결 계정 로그인 확인 |
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
