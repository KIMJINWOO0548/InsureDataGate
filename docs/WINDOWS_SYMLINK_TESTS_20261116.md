# Windows symlink test capability (2026-11-16 KST)

Previous 10 errors were WinError 1314 while creating test fixtures, not observed
failures of the application guard. A shared helper now marks only that exact
missing privilege as SKIP / real-link NOT_RUN. Other errors still fail.
No privilege, policy or product behavior changed. Existing assertions execute
unchanged on capable hosts.

Two helper regressions pass, including propagation of FileExistsError.
Windows Python 3.12.10 full discovery: 163 tests, OK (skipped=14), exit 0.
Those skips are NOT passes. A permitted host is needed for real-link checks.
