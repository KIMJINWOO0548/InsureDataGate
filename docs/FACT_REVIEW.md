# Opt-in disclosure annotation support review

`insuredatagate review-facts MANIFEST --profile disclosure-facts.v1 [--json] [--report NEW_JSON]`

The standard-library Python API is
`insuredatagate.fact_review.review_facts(manifest_path: pathlib.Path) -> dict`.
It first calls the existing `verify` and `read_snapshot`. Validation failure or a
changed/unreadable checked manifest, source, cases or gold produces `UNAVAILABLE`
with no facts. The reread boundary is the existing checked-file consistency
check, not an atomic snapshot against hostile concurrent filesystem replacement.

This optional profile checks support for asserted expected-JSON fields against
finite, explicit declarations in the checked case input. It does not change
`check`, `compare`, `review` or the exact gold-free `export-inputs` allowlist.
Declared rules source IDs are context, not issuer-document evidence, independent
truth, authenticated review, rights verification or release approval.

## Finite grammar

Declarations begin at the start of input or after a period, semicolon or newline.
A period ends a clause only before whitespace or end of input; decimal points
remain part of the token. Each relevant declaration must be consumed completely.
Labels are case-insensitive; currency codes and unit values follow the grammar
below. Surrounding/internal whitespace is normalized for comparison only.
Duplicate or malformed relevant declarations abstain, even beside a valid one.
Known label/target occurrences embedded after prose are unsupported declarations
and also prevent that dependency from being supported, including missing or
alternative punctuation. Discovery uses the same label vocabulary at every
location. The exact extraction requests in the preserved fixtures declare no
facts; their field-name mentions are excluded from declaration discovery only
when the whole request matches that finite form.
The parser never treats source text as instructions and performs no URL fetch.

| Declaration | Supported value |
| --- | --- |
| `Reporting period: YYYY-MM-DD to YYYY-MM-DD` | Real ordered ISO dates; `period_start` and `period_end` only |
| `Period: YYYY annual` or `Reporting period: YYYY annual` | `period` is `YYYY` |
| `Period: YYYY Q1` through `Q4` (also `Reporting period`) | `period` retains `YYYY Qn` granularity |
| `Basis: consolidated` or `Basis: separate` | Explicit `scope` |
| `Currency: CUR` | Three uppercase ASCII letters; no external currency lookup |
| `Amount unit: UNIT` or `Amount unit: CUR UNIT` | Whole stated label, including currency prefix |
| `Amounts in CUR UNIT` | Separate currency and unit facts |
| `The amount unit is absent.` | Explicit null unit only if no positive/malformed unit declaration exists |
| `Revenue: DECIMAL` or `Revenue for YYYY: DECIMAL` | At most 64 characters: optional sign, ASCII digits, optional fractional digits |
| `Extract only the YYYY revenue` | Explicit input-derived target; optional exact tail `with its period, currency, amount unit and scope` |

Units are lowercase `thousand(s)`, `million(s)` or `billion(s)`. There is no scaling,
FX, exponent, grouping, float-prefix parsing or date/period inference. Revenue
requires unique period, currency, unit and scope context plus a unique bound
amount. Multiple years require exactly one explicit target; expected `period`
never selects the year. A sole labelled revenue year can supply period context.
Missing, duplicate, contradictory or unsupported targeting abstains. Only the
bare target or its exact enumerated optional tail is accepted; all other
continuations (including arbitrary `with ...` prose) abstain. A currency
prefix in the whole unit label must agree with independently stated currency;
contradiction abstains for currency and revenue without discarding the unit label. An explicit
period alongside a labelled year must agree with that year. Unasserted unrelated
unsupported context does not invalidate an independently supported field.

Supported keys are `period_start`, `period_end`, `period`, `currency`,
`amount_unit`, `scope`, `revenue`. Values must be strings; only `amount_unit` also
allows null. Revenue comparison is lexical after whitespace normalization:
`17`, `17.0`, `+17` and `017` differ. Strict JSON rejects duplicate keys,
nonfinite values and invalid Unicode. Unknown keys contribute a case abstention
without exposing the unknown key/value. Empty/non-object/non-JSON claims abstain.
Silence or an unparsed unit label never proves null.

## Report and evidence

The separate [JSON schema fixture](schemas/fact-review.v1.schema.json) describes
`insuredatagate.fact-review.v1` / `disclosure-facts.v1`. Case rows preserve input
record order and use one-based `record_index`; recognized asserted fields use a
fixed order. Field statuses are `SUPPORTED`, `CONFLICT`, `ABSTAIN`. Case/top
status prioritizes conflict, then abstention (including zero assertions), then
support. Snapshot/validation failure overrides all facts with `UNAVAILABLE`.
Exit codes: 0 only for `SUPPORTED`; 1 for conflict/abstain/unavailable; 2 for
argument/output errors. Profile is required; unknown profiles are argparse errors.

Reports include checked manifest/cases/gold SHA-256 and each case input UTF-8
SHA-256. Evidence contains `field: input`, a dependency `kind`, half-open
`start`/`end` Unicode code-point offsets and exact substring UTF-8 SHA-256.
Replay with `text[start:end]` against the checked input and hash its UTF-8 bytes.
Revenue evidence covers its declaration/year, explicit target when present and
every required period/currency/unit/scope dependency. Shared declarations can
appear under multiple dependency kinds; ordering is by start, end, kind. Offsets
always refer to original text, including Unicode prefixes. ABSTAIN evidence is
recognized context only and is not a guessed fact.

No raw input, source or gold bodies, expected values or evidence quotes are
included. Field reasons are fixed: `MATCH`, `MISMATCH`, `MISSING_CONTEXT`,
`AMBIGUOUS_CONTEXT`, `UNSUPPORTED_CONTEXT`, `UNSUPPORTED_CLAIM`. Case reasons
add `INVALID_CLAIMS` or `UNSUPPORTED_CLAIM`. Unavailable issues are
`VALIDATION_FAILED` or `SNAPSHOT_UNAVAILABLE` with null artifact hashes.
Reports have no timestamps or automatic fixes. Report creation is exclusive;
existing files and file symlinks, including dangling symlinks, are refused.

Use temporary repinned copies to review deliberately changed annotations; do not
edit preserved example bytes. Passing this finite profile is bounded annotation
support, not extraction accuracy, financial/legal certification or a release
recommendation. Generic prose, OCR/PDF, alternative layouts and broader language
understanding are outside this profile.
