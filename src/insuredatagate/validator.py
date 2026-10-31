"""Offline validation for the synthetic dataset manifest v1 contract."""

import hashlib
import json
import math
import os
from pathlib import Path
import re
import stat
import unicodedata


SMALL_LIMIT = 1024 * 1024
RECORD_LIMIT = 10 * SMALL_LIMIT
ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}\Z")
SHA256 = re.compile(r"[0-9a-f]{64}\Z")
SPLITS = ("train", "validation", "test")


def _unicode_valid(value):
    if isinstance(value, str):
        return not any(0xD800 <= ord(char) <= 0xDFFF for char in value)
    if isinstance(value, list):
        return all(_unicode_valid(item) for item in value)
    if isinstance(value, dict):
        return all(_unicode_valid(key) and _unicode_valid(item) for key, item in value.items())
    return not isinstance(value, float) or math.isfinite(value)


def strict_json(raw: bytes):
    """Parse UTF-8 JSON without duplicate keys, BOMs, nonfinite values or surrogates."""
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("Duplicate JSON key")
            result[key] = value
        return result

    def constant(_value):
        raise ValueError("Nonfinite JSON value")

    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=pairs, parse_constant=constant)
        if not _unicode_valid(value):
            raise ValueError("Invalid JSON text")
        return value
    except (UnicodeError, ValueError, RecursionError):
        raise ValueError("Invalid JSON") from None


def portable_path(value) -> bool:
    """Whether a reference uses the contract's portable relative path syntax."""
    return (
        type(value) is str
        and bool(value)
        and _unicode_valid(value)
        and not any(char in value for char in "\\:")
        and not any(ord(char) < 32 or ord(char) == 127 for char in value)
        and all(part not in ("", ".", "..") for part in value.split("/"))
    )


def safe_read(path: Path, max_bytes: int) -> bytes:
    """Read a bounded regular file, rejecting symlink/reparse components and errors.

    Callers confine declared paths to their dataset root before calling this helper.
    Concurrent replacement and hardlinks are outside the contract's threat model.
    """
    try:
        # Preserve '..' until components are checked so it cannot hide a link.
        path = Path(path)
        absolute = path if path.is_absolute() else Path.cwd() / path
        for component in (*reversed(absolute.parents), absolute):
            info = component.lstat()
            if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
                raise ValueError("Unsafe file")
        if not stat.S_ISREG(info.st_mode) or info.st_size > max_bytes:
            raise ValueError("Invalid file size or type")
        with absolute.open("rb") as handle:
            raw = handle.read(max_bytes + 1)
        if len(raw) > max_bytes:
            raise ValueError("File too large")
        return raw
    except (OSError, ValueError, RuntimeError):
        raise ValueError("File cannot be safely read") from None


def _text(value, maximum=128):
    return type(value) is str and 1 <= len(value) <= maximum and bool(value.strip())


def _id(value):
    return type(value) is str and ID.fullmatch(value) is not None


def _keys(value, fields):
    return type(value) is dict and set(value) == set(fields.split())


def verify(manifest_path: Path) -> dict:
    """Return a deterministic, redacted report; never modify dataset files."""
    report = {
        "schema_version": "insuredatagate.report.v1",
        "status": "BLOCK",
        "dataset_id": None,
        "version": None,
        "manifest_sha256": None,
        "files": [],
        "counts": {key: 0 for key in ("sources", "cases", "gold", *SPLITS)},
        "issues": [],
    }

    def issue(code, location, message):
        report["issues"].append({"code": code, "location": location, "message": message})

    def finish():
        report["files"].sort(key=lambda item: item["path"])
        report["issues"].sort(key=lambda item: (item["code"], item["location"], item["message"]))
        report["status"] = "BLOCK" if report["issues"] else "PASS"
        return report

    try:
        manifest_path = Path(manifest_path)
        raw = safe_read(manifest_path, SMALL_LIMIT)
    except (ValueError, TypeError):
        issue("FILE_READ", "manifest", "Manifest cannot be safely read within its size limit.")
        return finish()
    report["manifest_sha256"] = hashlib.sha256(raw).hexdigest()
    try:
        manifest = strict_json(raw)
    except ValueError:
        issue("INVALID_JSON", "manifest", "Manifest must be strict UTF-8 JSON.")
        return finish()
    if type(manifest) is dict:
        if _id(manifest.get("dataset_id")):
            report["dataset_id"] = manifest["dataset_id"]
        if _text(manifest.get("version")):
            report["version"] = manifest["version"]
    if not _keys(manifest, "schema_version dataset_id version synthetic sources cases gold"):
        issue("SCHEMA", "manifest", "Manifest fields must match schema v1 exactly.")
        return finish()
    if (manifest["schema_version"] != "insuredatagate.manifest.v1"
            or not _id(manifest["dataset_id"]) or not _text(manifest["version"])
            or manifest["synthetic"] is not True):
        issue("SCHEMA", "manifest", "Manifest requires valid metadata and synthetic true.")
    sources = manifest["sources"]
    if type(sources) is not list or not 1 <= len(sources) <= 100:
        issue("SCHEMA", "manifest.sources", "Provide between one and 100 sources.")
        return finish()
    report["counts"]["sources"] = len(sources)
    refs = []
    source_ids = set()
    for index, source in enumerate(sources, 1):
        location = f"manifest.sources[{index}]"
        if not _keys(source, "source_id path sha256 license status approved_by"):
            issue("SCHEMA", location, "Source fields must match schema v1 exactly.")
            continue
        if not _id(source["source_id"]) or not _text(source["license"]) or not _text(source["approved_by"]):
            issue("SCHEMA", location, "Source IDs and rights declarations must be valid text.")
        else:
            if source["source_id"] in source_ids:
                issue("DUPLICATE_SOURCE", location, "Source IDs must be unique.")
            source_ids.add(source["source_id"])
        if source["status"] != "APPROVED":
            issue("SOURCE_APPROVAL", location, "Source must declare APPROVED status.")
        refs.append((location, source, SMALL_LIMIT, "source"))
    for role in ("cases", "gold"):
        ref = manifest[role]
        if not _keys(ref, "path sha256"):
            issue("SCHEMA", f"manifest.{role}", "File references require exactly path and sha256.")
        else:
            refs.append((f"manifest.{role}", ref, RECORD_LIMIT, role))

    root = manifest_path.absolute().parent.resolve()
    used = {os.path.normcase(str(manifest_path.resolve()))}
    records = {}
    for location, ref, limit, role in refs:
        if not portable_path(ref["path"]):
            issue("UNSAFE_PATH", location, "File path must be a portable relative path.")
            continue
        if type(ref["sha256"]) is not str or SHA256.fullmatch(ref["sha256"]) is None:
            issue("SCHEMA", location, "SHA-256 must be 64 lowercase hexadecimal characters.")
            continue
        path = root.joinpath(*ref["path"].split("/"))
        try:
            # Read checks every component before resolving; resolution also enforces confinement.
            file_raw = safe_read(path, limit)
            resolved = path.resolve()
            if not resolved.is_relative_to(root):
                raise ValueError("Outside root")
            identity = os.path.normcase(str(resolved))
            if identity in used:
                issue("DUPLICATE_ROLE", location, "A file may occupy only one manifest role.")
                continue
            used.add(identity)
        except (ValueError, OSError, RuntimeError):
            issue("FILE_READ", location, "Declared file cannot be safely read within its size limit.")
            continue
        digest = hashlib.sha256(file_raw).hexdigest()
        report["files"].append({"path": ref["path"], "sha256": digest, "bytes": len(file_raw)})
        if digest != ref["sha256"]:
            issue("HASH_MISMATCH", location, "Declared SHA-256 does not match file bytes.")
        if role == "source":
            try:
                text = file_raw.decode("utf-8")
                if text.startswith("\ufeff") or not _unicode_valid(text):
                    raise ValueError("Invalid text")
            except (UnicodeError, ValueError):
                issue("INVALID_UTF8", location, "Source must contain UTF-8 text without a BOM.")
            continue
        lines = file_raw.split(b"\n")
        if lines[-1:] == [b""]:
            lines.pop()
        if not 1 <= len(lines) <= 10000:
            issue("RECORD_COUNT", location, "JSONL requires between one and 10000 records.")
            continue
        rows = []
        for index, line in enumerate(lines, 1):
            try:
                row = strict_json(line)
                if type(row) is not dict:
                    raise ValueError("Object required")
                rows.append(row)
            except ValueError:
                issue("INVALID_JSONL", f"{role}[{index}]", "Each line must be one strict UTF-8 JSON object.")
        report["counts"][role] = len(lines)
        records[role] = rows

    cases = {}
    groups = {}
    inputs = {}
    for index, case in enumerate(records.get("cases", []), 1):
        location = f"cases[{index}]"
        if not _keys(case, "case_id group_id split source_ids input created_by"):
            issue("SCHEMA", location, "Case fields must match schema v1 exactly.")
            continue
        ids = case["source_ids"]
        if (not _id(case["case_id"]) or not _id(case["group_id"])
                or type(case["split"]) is not str or case["split"] not in SPLITS
                or not _text(case["input"], 10000) or not _text(case["created_by"])
                or type(ids) is not list or not ids or not all(_id(item) for item in ids)):
            issue("SCHEMA", location, "Case fields have invalid types or values.")
            continue
        if len(set(ids)) != len(ids) or not set(ids) <= source_ids:
            issue("SOURCE_REFERENCE", location, "Case source IDs must be unique known sources.")
        if case["case_id"] in cases:
            issue("DUPLICATE_CASE", location, "Case IDs must be unique.")
        else:
            cases[case["case_id"]] = case
        split = case["split"]
        report["counts"][split] += 1
        normalized = " ".join(unicodedata.normalize("NFKC", case["input"]).casefold().split())
        for seen, key, code in ((groups, case["group_id"], "GROUP_LEAKAGE"), (inputs, normalized, "INPUT_LEAKAGE")):
            if key in seen and seen[key] != split:
                issue(code, location, "Related cases must remain in one split.")
            else:
                seen[key] = split
    for split in SPLITS:
        if not report["counts"][split]:
            issue("EMPTY_SPLIT", f"counts.{split}", "Every split requires at least one case.")
    gold_ids = set()
    for index, gold in enumerate(records.get("gold", []), 1):
        location = f"gold[{index}]"
        if not _keys(gold, "case_id expected review_status reviewed_by"):
            issue("SCHEMA", location, "Gold fields must match schema v1 exactly.")
            continue
        if (not _id(gold["case_id"]) or not _text(gold["expected"], 10000)
                or not _text(gold["reviewed_by"])):
            issue("SCHEMA", location, "Gold fields have invalid types or values.")
            continue
        if gold["review_status"] != "APPROVED":
            issue("GOLD_APPROVAL", location, "Gold must declare APPROVED review status.")
        case_id = gold["case_id"]
        if case_id in gold_ids:
            issue("DUPLICATE_GOLD", location, "Gold case IDs must be unique.")
        gold_ids.add(case_id)
        if case_id not in cases:
            issue("UNMATCHED_GOLD", location, "Gold requires a corresponding case.")
        elif gold["reviewed_by"].strip().casefold() == cases[case_id]["created_by"].strip().casefold():
            issue("SELF_REVIEW", location, "Reviewer and creator declarations must differ.")
    if set(cases) - gold_ids:
        issue("MISSING_GOLD", "gold", "Every case requires a corresponding gold record.")
    return finish()
