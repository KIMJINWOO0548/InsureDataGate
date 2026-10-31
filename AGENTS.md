# InsureDataGate contributor contract

- This is a standalone, synthetic-only, offline Python dataset release checker. Read `docs/CONTRACT.md` first.
- Keep the runtime standard-library only. Do not install tools or modify global settings without authorization.
- Preserve input files. Never overwrite an existing report/export, follow dataset symlinks, fetch source URLs, or print case/gold contents in diagnostic output.
- PASS means these local checks passed. Recorded reviewers and rights are declarations, not authenticated approvals or legal certification. No insurance decisions.
- Write independent failing tests for behavior changes, then run the affected tests and full `unittest` suite. Use temporary directories.
- Work in focused commits; the user authorized milestone pushes for this project. Never force push or publish packages without explicit approval.
- Record actual verification and limitations. Do not fabricate CI, independent review, or usage results.
