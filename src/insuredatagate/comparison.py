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


def _compare(baseline_path: Path, candidate_path: Path) -> tuple[dict, dict]:
    """Retain the checked projections for callers needing relationship data."""
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
    return result, projections


def compare(baseline_path: Path, candidate_path: Path) -> dict:
    """Compare only PASS snapshots; expose field names, never their values."""
    return _compare(baseline_path, candidate_path)[0]


def review(baseline_path: Path, candidate_path: Path) -> dict:
    """Add declared case/source relationships from the same checked snapshots."""
    result, projections = _compare(baseline_path, candidate_path)
    result["schema_version"] = "insuredatagate.review.v1"
    result["review"] = {"available": False, "cases": None, "sources": None, "summary": None}
    if result["changes"] is None:
        return result

    changes = result["changes"]
    before = {case["case_id"]: case for case in projections["baseline"]["cases"]}
    after = {case["case_id"]: case for case in projections["candidate"]["cases"]}
    case_fields = {item["case_id"]: item["fields"] for item in changes["cases_changed"]}
    gold_fields = {item["case_id"]: item["fields"] for item in changes["gold_changed"]}
    source_fields = {item["source_id"]: item["fields"] for item in changes["sources_changed"]}
    changed_sources = set(changes["sources_added"]) | set(changes["sources_removed"]) | source_fields.keys()
    direct_cases = set(changes["cases_added"]) | set(changes["cases_removed"]) | case_fields.keys() | gold_fields.keys()

    # These are declared references, not evidence of semantic or causal impact.
    relations = {side: {} for side in ("baseline", "candidate")}
    for side, cases in (("baseline", before), ("candidate", after)):
        for identity, case in cases.items():
            for source_id in case["source_ids"]:
                relations[side].setdefault(source_id, []).append({"case_id": identity, "split": case["split"]})
    sources = []
    affected_cases = set()
    for source_id in sorted(changed_sources):
        linked = {side: relations[side].get(source_id, []) for side in relations}
        affected = sorted({case["case_id"] for cases in linked.values() for case in cases})
        affected_cases.update(affected)
        sources.append({
            "source_id": source_id,
            "status": "added" if source_id in changes["sources_added"] else
                      "removed" if source_id in changes["sources_removed"] else "modified",
            "fields": source_fields.get(source_id, []),
            "cases": linked,
            "affected_case_ids": affected,
        })

    cases = []
    for identity in sorted(direct_cases | affected_cases):
        old, new = before.get(identity), after.get(identity)
        old_sources = old["source_ids"] if old else []
        new_sources = new["source_ids"] if new else []
        added_or_removed = old is None or new is None
        cases.append({
            "case_id": identity,
            "status": "added" if old is None else "removed" if new is None else
                      "modified" if identity in direct_cases else "affected",
            "fields": {
                "case": [] if added_or_removed else case_fields.get(identity, []),
                "gold": [] if added_or_removed else gold_fields.get(identity, []),
            },
            "sources": {"baseline": old_sources, "candidate": new_sources,
                        "changed": sorted((set(old_sources) | set(new_sources)) & changed_sources)},
            "splits": {"baseline": old["split"] if old else None,
                       "candidate": new["split"] if new else None},
        })
    result["review"] = {
        "available": True, "cases": cases, "sources": sources,
        "summary": {"case_count": len(cases), "direct_case_count": len(direct_cases),
                    "source_count": len(sources), "source_only_case_count": len(affected_cases - direct_cases)},
    }
    return result
