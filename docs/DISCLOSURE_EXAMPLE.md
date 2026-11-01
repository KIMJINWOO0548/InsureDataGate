# Synthetic disclosure extraction example

The existing offline release gate also accepts a dataset about document extraction outside insurance. This example uses **the same `insuredatagate.manifest.v1` contract**, package name and check/compare/export commands. No runtime, schema or report format changes are required.

`examples/disclosure-demo` and `examples/disclosure-demo-v2` are two releases of **one** invented dataset, `fictional-disclosure-extraction`. Six cases cover reporting period, currency/amount unit, consolidated or separate scope, a stated revenue value, a missing unit, and separation of current/prior periods. There are two distinct declared groups per split: train, validation and test. The source guide, issuer names, amounts, dates and curator/author/reviewer identities are fictional. `APPROVED` is an unauthenticated example declaration.

Each case asks for explicitly stated fields from a supplied synthetic excerpt. Gold answers remain in `gold.jsonl`; their `expected` value is a JSON object encoded as an ordinary string, as already permitted by manifest.v1. There is no new nested schema or automatic extraction engine. The checker validates dataset release structure and consistency; it does not score the truth or accuracy of an answer.

## Intentional release difference

The candidate 0.2.0 release revises only `disclosure-train-unit`: its input and expected answer preserve the explicit `KRW millions` unit text, including the currency prefix. The synthetic source guide adds a corresponding revision note. Candidate file hashes are pinned to those intended bytes. All validation/test cases and gold records remain unchanged. The comparison must report one changed case input, one changed gold answer and one changed source digest; it still requires review.

The original insurance examples remain separate datasets with unchanged bytes. Comparing an insurance release with a disclosure release returns `DATASET_ID_MISMATCH`; renaming datasets to force a comparison is inappropriate.

## Reproduce offline

From the repository root on Linux/macOS, with Python 3.11+:

```sh
export PYTHONPATH=src
python3 -m insuredatagate check examples/disclosure-demo/manifest.json --json
python3 -m insuredatagate check examples/disclosure-demo-v2/manifest.json --json
python3 -m insuredatagate compare examples/disclosure-demo/manifest.json examples/disclosure-demo-v2/manifest.json --json
output_dir=$(mktemp -d)
python3 -m insuredatagate review examples/disclosure-demo/manifest.json examples/disclosure-demo-v2/manifest.json --html "$output_dir/disclosure-review.html"
python3 -m insuredatagate export-inputs examples/disclosure-demo-v2/manifest.json --output "$output_dir/disclosure-inputs.jsonl"
python3 -m unittest tests.test_disclosure_example -v
python3 -m unittest discover -s tests -v
```

Keep the generated model input file separate from gold. Its records contain exactly `case_id`, `input` and `source_ids`, in case order. Exporting to an existing path fails with exit 2 and preserves its bytes; a tampered referenced gold file blocks export with exit 1 and creates no output. Use fresh output paths rather than overwriting a report or dataset.

## Limits

The six visible synthetic cases demonstrate the release workflow; they are not a blind extraction benchmark, a representative securities corpus or a model evaluation. Declared group isolation and normalized duplicate checks do not establish semantic independence. No real issuer documents or regulations are used. PASS does not establish authenticated approval, source rights, extraction accuracy, regulatory compliance, investment suitability or permission to trade. The tool performs no investment recommendations, valuation, order placement or network requests.

This increment was verified locally on Linux/Python 3.12. The local branch was not pushed, and no new remote CI run, Windows check or deployment was performed. Exact commands, results, original HTML, attempted-browser logs and restoration artifacts accompany the local evidence package. Fresh browser capture was blocked/unverified; `set_content` images are excluded. Historical captures and CI evidence remain historical.
