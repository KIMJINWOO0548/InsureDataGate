# Split-aware release investigation at the documented capacity

This increment starts at `ad5f9d8`. The earlier issue-code overview was useful but did not solve the central release-investigation questions: which evaluation split is affected, whether gold/split/lifecycle changes overlap, and how to navigate thousands of source-linked cases without duplicating a huge directory and CSS selection rule for every entity.

## Explicit references and observation limits

| Source | What it establishes / limitation |
|---|---|
| [GX Expectation Gallery](https://greatexpectations.io/expectations/) → [rule detail](https://greatexpectations.io/expectations/expect_column_distinct_values_to_be_in_set) | Actual complete REA4-step public catalog → existing See more link → rule-detail navigation, Chromium156. Final1440×900 screenshot and accessibility inspected. Supported backend context, arguments, sample table and published passing/failing examples are visible. No search/filter/tab interaction, upload or validation execution; source hashes in `rea-observations.json`. |
| [GX Data Docs overview](https://legacy.017.docs.greatexpectations.io/docs/0.16.16/) | Official description and illustrative screenshot of a human-readable metadata-derived quality report. A documentation page is not an executed GX validation report. |
| [Frictionless validating data](https://framework.frictionlessdata.io/docs/guides/validating-data.html) | Official sample of structured validation errors and report/task organization. Not an executed Frictionless GUI or benchmark. |
| [GX hosting guidance](https://legacy.017.docs.greatexpectations.io/docs/guides/setup/configuring_data_docs/host_and_share_data_docs/) | Data Docs can include sensitive information; do not expose an actual customer's report or upload data. No deployment/configuration instructions were executed. |

The actual catalog→rule public flow is archived outside the repository in workspace `phase2/refs/gx-public-rule-detail`; all4steps completed and owned Chrome cleanup was confirmed. The source-boundary metadata is checked in; public screenshots/brand assets are not shipped. The observed explicit scope→support→example hierarchy informs the own review context and native detail disclosure. A live validation run or actual GX Data Docs result interaction remains NOT_RUN. No login, access bypass, packages, private API calls, source bundles or raw dataset uploads are involved. Code, layout, wording and colors are independently written with the existing stdlib/native HTML stack.

## Own flow and critical design choices

S01: checked local gate plus unchanged declaration/approval boundary. S02: one native initially closed44px review-scope disclosure contains obligations (cases with gold changes, split moves, added/removed cases, source-only cases) and a table separating baseline/candidate direct versus source-only split membership. Counts are neither whole-dataset totals nor additive severity/completion measures. The disclosure keeps first dossiers visible on mobile without omitting metadata. S03: always-visible native split filters for a case present in either checked snapshot, then complete case/source dossiers with original links. A moved case can correctly appear in two split views. S04: all original integrity hashes and findings remain available.

F01: inspect the local result → identify test/validation/train exposure → filter that case scope → follow a case/source link → inspect both snapshot memberships → regenerate a new offline report after an intentional local change. Following a native entity anchor resets the one-fragment filter to All. No report state authenticates a reviewer or approves a release.

The optional rail previews at most20cases and20sources above40review units. Every full dossier, source relationship and numeric anchor is retained; a clear note explains the preview and browser Find in All items. Per-entity CSS is therefore bounded rather than growing to10001selectors. Offscreen compact source-impact rows use native `content-visibility:auto`; target rows explicitly reveal, print restores all dossiers, and fallback browsers still render ordinary complete HTML. Nothing is paginated away or silently dropped.

## Criteria and fair comparison plan

| Dimension | Reproducible criterion |
|---|---|
| Function | Exact separate snapshot counts, either-snapshot split filters, lifecycle absent sides, native deep links, explicit unavailable counts, complete1000/10000case destinations, original input bytes unchanged. |
| Detection | Fixed10synthetic scenarios:7single error injections and3valid controls. Count intended error-code misses and false BLOCKs; this is a regression matrix, not real-world accuracy. Validator/JSON schemas stay unchanged. |
| Performance | Actual checked manifests with1000cases×3unprofiled samples and10000cases×1bounded capacity sample; identical fixture hashes and same redacted report. Historical own renderer and current renderer execute in separate fresh processes. Python peak allocations are measured separately from walltime and labelled as traced allocations, not RSS. Browser comparison uses cold offline contexts and identical1440×900 viewport;390px and last-case navigation separately checked. |
| Accessibility/design | Existing local-gate hierarchy, native links/Tab/Enter/fragment focus, named table captions/scoped headers,44px links, sampled contrast≥4.5 and focus≥3, no page overflow at375/390/844/1440, actual split visibility and print-all. Full screen-reader certification remains unrun. |
| Safety | No raw input/gold/source bodies, no source URL fetch, no scripts/remote assets, no overwriting runtime output, exact3packaged sample HTML regeneration from unchanged inputs. |

An equal-condition GX/Frictionless performance benchmark would require the same supported input contract, rules, full metadata report, privacy settings, hardware and distribution environment. Their broader validation/runtime features are not directly interchangeable with this local synthetic-release checker. No competitor timings or overall superiority score are inferred. Replica parity output is a limited feature checklist that includes material missing capabilities; screenshot layout parity is NOT_RUN because matched result states are unavailable.
