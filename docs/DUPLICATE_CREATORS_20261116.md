# Duplicate case creator checks (2026-11-16)

A duplicate case ID retained only its first creator for self-review checking.
Reversing duplicate record order changed whether SELF_REVIEW was reported.
All structurally valid creator declarations for the ID are now checked, using
existing strip/casefold normalization. DUPLICATE_CASE remains a blocking defect;
this does not resolve ambiguous case IDs or authenticate identities.

Independent regression before implementation: 2 tests, 1 failed (forward order).
After implementation: 2/2 passed; full unittest suite 174 tests, 160 passed and
14 skipped because Windows symlink privilege is unavailable. No real-data or
external review claim. Raw input, gold and identity values remain redacted.
