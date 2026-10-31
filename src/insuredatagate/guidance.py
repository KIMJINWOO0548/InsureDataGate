"""Fixed recovery guidance; never interpolate untrusted data into instructions."""

_RECOVERY = {
    "VERSION_REUSED": ("Give the changed candidate a distinct version", (
        "Confirm that this content change is intended, then declare a distinct candidate version. Versions are opaque labels; no ordering is required.",
    )),
    "FILE_READ": ("Restore a readable local snapshot", (
        "Check that the declared file exists, is a regular file, stays within the documented size limit, and is readable with your existing access.",
        "Use local files inside the dataset directory; symlinks, junctions and unsafe ancestor paths are refused. Do not weaken filesystem protections to pass the check.",
    )),
    "HASH_MISMATCH": ("Confirm the intended file before updating its hash", (
        "Compare the intended revision with the local file before changing a declared hash. A different hash can mean the wrong file or an unintended edit.",
        "Only after confirming an intended candidate change, update its declared SHA-256 from those exact bytes.",
    )),
    "SNAPSHOT_CHANGED": ("Check one stable snapshot", (
        "Stop edits to the candidate files, confirm the intended bytes and manifest references, then retry the complete comparison.",
        "No relationship or export is trusted from a snapshot that changed during the check.",
    )),
    "DATASET_ID_MISMATCH": ("Select two releases of the same dataset", (
        "Choose baseline and candidate manifests for the same dataset identity. Do not rename unrelated datasets just to make the comparison pass.",
    )),
    "INVALID_JSON": ("Repair the manifest JSON", (
        "Use strict UTF-8 JSON with unique keys, finite values and the documented manifest fields. Check the original file locally; report text does not include its contents.",
    )),
    "INVALID_JSONL": ("Repair the indicated original JSONL record", (
        "Open the indicated original line locally. Each LF-delimited record must be one strict UTF-8 JSON object; reject duplicate keys, non-finite values and broken encoding.",
    )),
    "INVALID_UTF8": ("Save the source as valid UTF-8", (
        "Confirm the source is the intended text file, save valid UTF-8 without a BOM, then update its candidate hash only if that revision is intended.",
    )),
    "SCHEMA": ("Match the documented file contract", (
        "Check the indicated file or record against docs/FORMAT.md: exact field names, allowed types, bounded values and synthetic true. Do not insert customer data.",
    )),
    "UNSAFE_PATH": ("Use a confined relative file path", (
        "Replace absolute, parent-traversing or otherwise unsafe references with a portable relative path inside this dataset. Do not fetch a remote URL as a workaround.",
    )),
    "DUPLICATE_ROLE": ("Assign a distinct file to each manifest role", (
        "Check source, cases and gold references. The same file cannot occupy multiple roles; keep case inputs and gold records separate.",
    )),
    "DUPLICATE_SOURCE": ("Resolve the duplicated source identifier", (
        "Give each intended source one unique source_id and update the candidate case references consistently. Preserve existing release identifiers.",
    )),
    "SOURCE_REFERENCE": ("Repair the case's declared source links", (
        "Use unique source IDs that are actually declared in this manifest. Confirm the intended source relationships locally before editing references.",
    )),
    "SOURCE_APPROVAL": ("Resolve the source rights declaration", (
        "Obtain the independent review required by your process before recording an approval declaration. Do not invent an approver or set APPROVED merely to silence this finding.",
        "This checker cannot authenticate the reviewer or verify the legal right to use a source.",
    )),
    "GOLD_APPROVAL": ("Resolve the gold review declaration", (
        "Obtain the independent review required by your process before recording a review declaration. Do not invent a reviewer or set APPROVED merely to silence this finding.",
    )),
    "SELF_REVIEW": ("Use an independent reviewer declaration", (
        "Have an independent person review under your process. Do not invent a different identity or rename the same creator merely to pass this check.",
    )),
    "GROUP_LEAKAGE": ("Keep the related group in one split", (
        "Correct candidate split assignments using the intended experimental design. Related group IDs must not cross train, validation and test; preserve the released baseline.",
    )),
    "INPUT_LEAKAGE": ("Resolve normalized duplicate inputs across splits", (
        "Inspect the related cases locally and correct the candidate split design. Normalized identical inputs must stay in one split; do not hide duplication by superficial text edits.",
    )),
    "EMPTY_SPLIT": ("Restore the intended split coverage", (
        "Confirm the candidate's intended experimental design and valid case assignments. Train, validation and test each require a case; keep related cases together.",
    )),
    "RECORD_COUNT": ("Check the JSONL record limits", (
        "Use between one and 10000 LF-delimited records per cases/gold file, within the documented byte limit. Confirm that the correct local file is referenced.",
    )),
    "DUPLICATE_CASE": ("Resolve the duplicated case identifier", (
        "Inspect the duplicate case IDs locally and retain a unique intended case-to-gold relationship. Do not silently merge different inputs.",
    )),
    "DUPLICATE_GOLD": ("Resolve the duplicated gold record", (
        "Inspect gold case IDs locally. Each case must have exactly one corresponding gold record; do not choose an answer automatically.",
    )),
    "UNMATCHED_GOLD": ("Match the gold record to an intended case", (
        "Check the gold case_id against this candidate's cases. Correct the intended relationship locally; do not fabricate a case or answer.",
    )),
    "MISSING_GOLD": ("Restore the intended case-to-gold relationship", (
        "Check missing case IDs locally. Each case requires one corresponding independently reviewed gold record; do not fabricate an answer to pass the gate.",
    )),
}


def recovery(code: str) -> dict:
    """Return new guidance values for a known code or a safe fixed fallback."""
    title, steps = _RECOVERY.get(code, ("Resolve this finding before continuing", (
        "Inspect the indicated location locally and consult docs/FORMAT.md and docs/CONTRACT.md. This report never changes data or approves a release.",
    )))
    return {"title": title, "steps": [*steps,
        "Run the check again and write a new report file; preserve the released baseline and previous output.",
    ]}
