# Original acceptance scope: evidence and remaining gaps

This is a scoped product assessment, not a claim that every original ambition is complete. Baseline: `e4b2945` (release inventory generation and verification).

| Requirement | Implemented boundary | Remaining gap |
| --- | --- | --- |
| Human review and source rights | Declared approval states, required reviewer metadata and creator/reviewer separation; duplicates retain all creators for self-review checks | No identity provider, independent rights evidence verification or authenticated approval. Local PASS does not certify permission |
| Duplicate and split isolation | Normalized identical inputs and declared groups cannot cross splits | Paraphrase/semantic similarity and undeclared related groups are not detected |
| Lineage and scope | Verified source references and case/split relationships, source-change impact inventory, finite disclosure annotation review with replayable input evidence spans | Declared references are not proof of causal influence or issuer-document truth; unsupported grammar abstains |
| Release inventory | Deterministic manifest/file digest, declared source and case/split index; verify-index reconstructs the current checked inventory and rejects stale/tampered fields | No signature, trusted registry, historical approval chain or automatic publishing |
| Change after check | Checked reread binds manifest and all declared bytes before export, comparison, annotation review and indexing | No atomic protection against hostile concurrent filesystem replacement or hardlinks |
| PASS and coverage | Invalid/incomplete checks block or abstain; missing prerequisites distinguish unexecuted dependent checks from demonstrated defects | Skipped platform tests are not passing coverage. Local tests do not establish remote CI success |

## Direct recheck

`PYTHONPATH=src python -m unittest tests.test_fact_review tests.test_snapshot_context tests.test_duplicate_creators tests.test_review tests.test_comparison tests.test_release_index tests.test_verify_index -q`

Result on Windows: 61 tests, OK with 2 skipped, 8.999 seconds. This focused run is not a fresh full-suite run; prior full-suite and independent-review evidence are recorded separately. No new runtime defect was reproduced in this review, and no unrelated product feature was added to inflate completion.

## Work requiring a new scope decision

Authenticated human/rights assurance needs a defined identity and evidence trust model, revocation behavior and authorization boundary. Semantic leakage assessment needs an agreed corpus, thresholds, evaluation evidence and runtime/dependency policy. These are open product gaps, not silently satisfied by reviewer-name strings, source hashes or a similarity heuristic. The existing standard-library-only offline synthetic-data contract remains in force until such a scope is defined.
