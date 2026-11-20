# InsureDataGate Windows 앱

Windows x64 ZIP을 전부 푼 뒤 `InsureDataGate.exe`를 실행한다. .NET Desktop과 검사에 필요한 Python이 ZIP에 포함된다. 매니페스트를 선택하거나 창에 놓으면 기존 오프라인 검사기가 실행된다. `검사 항목`에서 규칙·입력 위치·이유를, `확인한 파일`에서 크기·SHA-256을 확인한다. 내보내기용 모델 입력은 기존 CLI에서만 생성한다.

- `Ctrl+O`로 매니페스트를 연다. `Esc`로 진행 중인 검사를 취소할 수 있다.
- `Ctrl+S`로 표시 중인 검사 결과를 새 JSON에 저장한다. 같은 이름의 파일이 있으면 저장을 거절한다.
- `Ctrl+Shift+O`로 저장 보고서를 연다. 이 화면의 상태는 보고서를 작성했을 때의 결과다. 현재 데이터셋의 상태를 확인하려면 매니페스트를 다시 검사한다.
- 글자 배율과 가운데 분할을 조절할 수 있다. 자동 검사는 파일·형식·해시와 기록된 선언을 확인한다. 사용 권리와 정답 정확성은 사람이 확인한다.

설치된 x64 Python 3.12, .NET 10 SDK와 로컬 NuGet 캐시의 .NET Desktop Runtime 10.0.12로 빌드할 수 있다. 기존 파일을 피해서 새 경로를 지정한다.

```powershell
python scripts/build_windows_app.py --output C:\package\InsureDataGate-Windows-x64.zip
```

합성 예제만 사용한다. CLI와 오프라인 HTML 보고서도 기존 명령으로 사용할 수 있다.
