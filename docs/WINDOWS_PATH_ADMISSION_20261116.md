# Windows portable-path admission (2026-11-16 KST)

Based on fetched remote 28ea4ca. Original local checkout 0469707 was clean
and preserved. Reject Windows reserved device basenames, trailing dots/spaces
and forbidden characters before filesystem access to avoid aliasing names.
No input data or published evidence was changed.

Windows/Python 3.12.10: 13 RED subcases reproduced before fix; both new tests
pass after fix. Full discovery attempted 161 tests, with 10 errors from existing
symlink creation tests (WinError 1314), 4 skips. This is not a full PASS.
Browser, live dataset accuracy and cloud rerun remain unverified.

Affected suite (portable paths, validator, snapshot context, diagnostics, injection matrix): 55 tests, OK with 2 skips.
