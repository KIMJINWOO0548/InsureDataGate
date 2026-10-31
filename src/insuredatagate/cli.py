"""Command line validation and gold-free model input export."""

import argparse
import json
from pathlib import Path
import sys

from . import __version__
from .comparison import compare
from .reporting import render_html
from .validator import read_snapshot, verify


def _write_new(path: Path, content: str) -> None:
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
    for command in (check, comparison):
        command.add_argument("--json", action="store_true", help="Print the JSON report")
        formats = command.add_mutually_exclusive_group()
        formats.add_argument("--report", type=Path, help="Create a new JSON report file")
        formats.add_argument("--html", type=Path, help="Create an offline HTML review")
    export = commands.add_parser("export-inputs", help="Export validated inputs without gold")
    export.add_argument("manifest", type=Path)
    export.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    report = compare(args.baseline, args.candidate) if args.command == "compare" else verify(args.manifest)

    try:
        if args.command in ("check", "compare"):
            serialized = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
            if args.report is not None:
                _write_new(args.report, serialized)
            if args.html is not None:
                _write_new(args.html, render_html(report))
            if args.json:
                print(json.dumps(report, ensure_ascii=True, indent=2))
            elif args.command == "compare":
                change = {True: "changed", False: "unchanged", None: "unavailable"}[report["content_changed"]]
                review = "required" if report["review_required"] else "not indicated"
                print(f"{report['status']}: content {change}; change review {review}")
                for issue in report["issues"]:
                    print(f"  {issue['code']} at {issue['location']}: {issue['message']}")
            else:
                print(f"{report['status']}: {report['counts']['cases']} cases; {len(report['issues'])} issue(s)")
                for issue in report["issues"]:
                    print(f"  {issue['code']} at {issue['location']}: {issue['message']}")
            return 0 if report["status"] == "PASS" else 1

        if report["status"] != "PASS":
            print("BLOCK: validation failed; no inputs exported.", file=sys.stderr)
            return 1
        try:
            rows = read_snapshot(args.manifest, report)["cases"]
        except (ValueError, OSError):
            print("BLOCK: dataset changed or became unreadable; recheck before export.", file=sys.stderr)
            return 1
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
