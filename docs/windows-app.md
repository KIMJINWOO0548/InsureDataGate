# InsureDataGate Windows 앱

Windows x64 ZIP을 전부 푼 뒤 `InsureDataGate.exe`를 실행한다. .NET Desktop과 검사에 필요한 Python이 ZIP에 포함된다. 매니페스트를 선택하거나 창에 놓으면 기존 오프라인 검사기가 실행된다. `검사 항목`에서 규칙·입력 위치를 검색하고 해당 항목의 이유와 검사 시점의 버전·매니페스트 SHA-256을 확인한다. `확인한 파일`에서는 개별 파일의 상대 경로와 SHA-256을 확인할 수 있다.

- `Ctrl+O`로 매니페스트를 연다. `Esc`로 진행 중인 검사를 취소할 수 있다.
- `Ctrl+S`로 표시 중인 검사 결과를 새 JSON에 저장한다. 같은 이름의 파일이 있으면 저장을 거절한다.
- `Ctrl+Shift+O`로 저장 보고서를 연다. 저장한 보고서에는 `보관된 PASS` 또는 `보관된 BLOCK`이 표시된다. 현재 상태와 내보내기 가능 여부를 확인하려면 매니페스트를 연다.
- 진행 중인 검사 결과가 PASS이면 `모델 입력 JSONL 저장`을 사용할 수 있다. 기존 CLI가 같은 매니페스트와 모든 참조 파일을 재검사해 사례 ID·입력·출처 ID만 새 파일에 저장한다. 스냅샷이 달라지면 매니페스트를 다시 검사해야 한다. 같은 이름의 출력은 보존한다.
- 글자 배율과 가운데 분할을 조절할 수 있다. 로컬 검사와 사람 검토 상태를 각각 표시한다. 출처의 사용 권리와 정답 정확성은 사람이 확인한다.

설치된 x64 Python 3.12, .NET 10 SDK와 로컬 NuGet 캐시의 .NET Desktop Runtime 10.0.12로 빌드할 수 있다. 기존 파일을 피해서 새 경로를 지정한다.

```powershell
python scripts/build_windows_app.py --output C:\package\InsureDataGate-Windows-x64.zip
```

합성 예제만 사용한다. CLI와 오프라인 HTML 보고서도 기존 명령으로 사용할 수 있다.
