"""Redacted semantic comparison of two verified synthetic datasets."""

import hashlib
import json
from pathlib import Path

from .validator import read_snapshot, verify


def _projection(snapshot: dict) -> dict:
    manifest = snapshot["manifest"]
    return {
        "schema_version": manifest["schema_version"],
        "synthetic": manifest["synthetic"],
        "sources": sorted(
            ({key: source[key] for key in ("source_id", "sha256", "license", "status", "approved_by")}
             for source in manifest["sources"]),
            key=lambda source: source["source_id"],
        ),
        "cases": sorted(
            (dict(case, source_ids=sorted(case["source_ids"])) for case in snapshot["cases"]),
            key=lambda case: case["case_id"],
        ),
        "gold": sorted(snapshot["gold"], key=lambda gold: gold["case_id"]),
    }


def _changes(baseline: dict, candidate: dict) -> dict:
    changes = {}
    for collection, id_key in (("cases", "case_id"), ("gold", "case_id"), ("sources", "source_id")):
        before = {record[id_key]: record for record in baseline[collection]}
        after = {record[id_key]: record for record in candidate[collection]}
        if collection != "gold":
            changes[collection + "_added"] = sorted(after.keys() - before.keys())
            changes[collection + "_removed"] = sorted(before.keys() - after.keys())
        changes[collection + "_changed"] = [
            {id_key: identity, "fields": sorted(
                key for key in before[identity] if before[identity][key] != after[identity][key]
            )}
            for identity in sorted(before.keys() & after.keys())
            if before[identity] != after[identity]
        ]
    return changes


def compare(baseline_path: Path, candidate_path: Path) -> dict:
    """Compare only PASS snapshots; expose field names, never their values."""
    result = {
        "schema_version": "insuredatagate.comparison.v1",
        "status": "BLOCK",
        "baseline": None,
        "candidate": None,
        "content_changed": None,
        "review_required": True,
        "changes": None,
        "issues": [],
    }
    projections = {}
    for name, path in (("baseline", baseline_path), ("candidate", candidate_path)):
        gate = verify(path)
        side = {key: gate[key] for key in ("status", "dataset_id", "version", "manifest_sha256", "counts")}
        side["content_sha256"] = None
        result[name] = side
        result["issues"].extend(
            dict(issue, location=name + "." + issue["location"]) for issue in gate["issues"]
        )
        if gate["status"] == "PASS":
            try:
                projection = _projection(read_snapshot(path, gate))
            except ValueError:
                side["status"] = "BLOCK"
                result["issues"].append({
                    "code": "SNAPSHOT_CHANGED", "location": name + ".snapshot",
                    "message": "Verified dataset snapshot could not be read consistently.",
                })
            else:
                projections[name] = projection
                canonical = json.dumps(projection, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
                side["content_sha256"] = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    if len(projections) == 2:
        if result["baseline"]["dataset_id"] != result["candidate"]["dataset_id"]:
            result["issues"].append({
                "code": "DATASET_ID_MISMATCH", "location": "candidate.dataset_id",
                "message": "Comparison requires matching dataset identities.",
            })
        else:
            changed = result["baseline"]["content_sha256"] != result["candidate"]["content_sha256"]
            version_changed = result["baseline"]["version"] != result["candidate"]["version"]
            result.update(
                status="PASS", content_changed=changed, review_required=changed or version_changed,
                changes=_changes(projections["baseline"], projections["candidate"]),
            )
            if changed and not version_changed:
                result["status"] = "BLOCK"
                result["issues"].append({
                    "code": "VERSION_REUSED", "location": "candidate.version",
                    "message": "Changed content requires a distinct dataset version.",
                })
    result["issues"].sort(key=lambda issue: (issue["code"], issue["location"], issue["message"]))
    return result
