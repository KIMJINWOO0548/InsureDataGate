"""Command line validation and gold-free model input export."""

import argparse
import json
from pathlib import Path
import sys

from . import __version__
from .comparison import compare, review
from .fact_review import PROFILE, review_facts
from .reporting import render_html
from .validator import read_snapshot, safe_read, strict_json, verify


def _write_new(path: Path, content: str) -> None:
    # On Windows, exclusive open can follow a dangling file symlink. Refuse
    # every existing directory entry without following it before creation.
    try:
        path.lstat()
    except FileNotFoundError:
        pass
    else:
        raise FileExistsError("Output entry already exists")
    created = False
    try:
        with path.open("x", encoding="utf-8", newline="\n") as output:
            created = True
            output.write(content)
    except BaseException:
        if created:
            path.unlink(missing_ok=True)
        raise


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="insuredatagate", description="Check a synthetic insurance AI dataset offline."
    )
    parser.add_argument("--version", action="version", version=f"InsureDataGate {__version__}")
    commands = parser.add_subparsers(dest="command", required=True)
    check = commands.add_parser("check", help="Validate and report PASS or BLOCK")
    check.add_argument("manifest", type=Path)
    comparison = commands.add_parser("compare", help="Compare two verified dataset releases")
    comparison.add_argument("baseline", type=Path)
    comparison.add_argument("candidate", type=Path)
    workspace = commands.add_parser("review", help="Review grouped case changes and verified source references")
    workspace.add_argument("baseline", type=Path)
    workspace.add_argument("candidate", type=Path)
    for command in (check, comparison, workspace):
        command.add_argument("--json", action="store_true", help="Print the JSON report")
        formats = command.add_mutually_exclusive_group()
        formats.add_argument("--report", type=Path, help="Create a new JSON report file")
        formats.add_argument("--html", type=Path, help="Create an offline HTML review")
    facts = commands.add_parser("review-facts", help="Review bounded disclosure annotation support")
    facts.add_argument("manifest", type=Path)
    facts.add_argument("--profile", required=True, choices=(PROFILE,))
    facts.add_argument("--json", action="store_true", help="Print the JSON report")
    facts.add_argument("--report", type=Path, help="Create a new JSON report file")
    export = commands.add_parser("export-inputs", help="Export validated inputs without gold")
    export.add_argument("manifest", type=Path)
    export.add_argument("--output", type=Path, required=True)
    index = commands.add_parser("release-index", help="Create a redacted checked-snapshot lineage index")
    index.add_argument("manifest", type=Path)
    index.add_argument("--output", type=Path, required=True)
    index_check = commands.add_parser("verify-index", help="Compare a saved index with the current checked snapshot")
    index_check.add_argument("manifest", type=Path)
    index_check.add_argument("index", type=Path)
    args = parser.parse_args(argv)
    if args.command in ("compare", "review"):
        report = (review if args.command == "review" else compare)(args.baseline, args.candidate)
    elif args.command == "review-facts":
        report = review_facts(args.manifest)
    else:
        report = verify(args.manifest)

    try:
        if args.command == "review-facts":
            serialized = json.dumps(report, ensure_ascii=True, indent=2) + "\n"
            if args.report is not None:
                _write_new(args.report, serialized)
            if args.json:
                print(serialized, end="")
            else:
                count = sum(len(case["fields"]) for case in report["cases"])
                print(f"{report['status']}: {len(report['cases'])} cases; {count} asserted fields; {PROFILE}")
            return 0 if report["status"] == "SUPPORTED" else 1
        if args.command in ("check", "compare", "review"):
            serialized = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
            if args.report is not None:
                _write_new(args.report, serialized)
            if args.html is not None:
                _write_new(args.html, render_html(report))
            if args.json:
                print(json.dumps(report, ensure_ascii=True, indent=2))
            elif args.command in ("compare", "review"):
                change = {True: "changed", False: "unchanged", None: "unavailable"}[report["content_changed"]]
                review_state = "required" if report["review_required"] else "not indicated"
                print(f"{report['status']}: content {change}; change review {review_state}")
                for issue in report["issues"]:
                    print(f"  {issue['code']} at {issue['location']}: {issue['message']}")
            else:
                print(f"{report['status']}: {report['counts']['cases']} cases; {len(report['issues'])} issue(s)")
                for issue in report["issues"]:
                    print(f"  {issue['code']} at {issue['location']}: {issue['message']}")
            return 0 if report["status"] == "PASS" else 1

        if report["status"] != "PASS":
            print("BLOCK: validation failed; no release output created.", file=sys.stderr)
            return 1
        try:
            snapshot = read_snapshot(args.manifest, report)
            rows = snapshot["cases"]
        except (ValueError, OSError):
            print("BLOCK: dataset changed or became unreadable; recheck before export.", file=sys.stderr)
            return 1
        if args.command in ("release-index", "verify-index"):
            index = {
                "schema_version": "insuredatagate.release-index.v1",
                "dataset_id": report["dataset_id"],
                "version": report["version"],
                "manifest_sha256": report["manifest_sha256"],
                "files": sorted(report["files"], key=lambda item: item["path"]),
                "counts": report["counts"],
                "sources": sorted(({
                    key: source[key] for key in ("source_id", "path", "sha256", "license", "status")
                } for source in snapshot["manifest"]["sources"]), key=lambda item: item["source_id"]),
                "lineage": sorted(({
                    "case_id": row["case_id"], "group_id": row["group_id"],
                    "split": row["split"], "source_ids": sorted(row["source_ids"]),
                } for row in rows), key=lambda item: item["case_id"]),
                "assurance": {
                    "snapshot": "LOCAL_CHECKS_PASSED",
                    "rights": "DECLARATIONS_ONLY",
                    "reviewer_identity": "NOT_AUTHENTICATED",
                    "semantic_leakage": "NOT_CHECKED",
                },
            }
            if args.command == "verify-index":
                try:
                    saved = strict_json(safe_read(args.index, 64 * 1024 * 1024))
                    # Canonical serialization preserves numeric types (unlike
                    # Python equality, where True == 1 == 1.0).
                    matches = json.dumps(saved, sort_keys=True) == json.dumps(index, sort_keys=True)
                except ValueError:
                    matches = False
                if not matches:
                    print("BLOCK: index is unreadable, invalid or does not match the current checked snapshot.", file=sys.stderr)
                    return 1
                print("PASS: index matches the current checked snapshot; no approval certification.")
                return 0
            _write_new(args.output, json.dumps(index, ensure_ascii=True, indent=2) + "\n")
            print("Created checked-snapshot release index.", file=sys.stderr)
            return 0
        content = "".join(
            json.dumps({key: row[key] for key in ("case_id", "input", "source_ids")}, ensure_ascii=False) + "\n"
            for row in rows
        )
        _write_new(args.output, content)
        print(f"Exported {len(rows)} validated model inputs.", file=sys.stderr)
        return 0
    except OSError:
        print("Output error: choose a new file in an existing writable directory.", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("Interrupted.", file=sys.stderr)
        return 130
