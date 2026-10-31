"""Command line validation and gold-free model input export."""

import argparse
import hashlib
import json
from pathlib import Path
import sys

from . import __version__
from .validator import safe_read, strict_json, verify


def _write_new(path: Path, content: str) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as output:
        output.write(content)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="insuredatagate", description="Check a synthetic insurance AI dataset offline."
    )
    parser.add_argument("--version", action="version", version=f"InsureDataGate {__version__}")
    commands = parser.add_subparsers(dest="command", required=True)
    check = commands.add_parser("check", help="Validate and report PASS or BLOCK")
    check.add_argument("manifest", type=Path)
    check.add_argument("--json", action="store_true", help="Print the JSON report")
    check.add_argument("--report", type=Path, help="Create a new JSON report file")
    export = commands.add_parser("export-inputs", help="Export validated inputs without gold")
    export.add_argument("manifest", type=Path)
    export.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    report = verify(args.manifest)

    try:
        if args.command == "check":
            serialized = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
            if args.report is not None:
                _write_new(args.report, serialized)
            if args.json:
                print(json.dumps(report, ensure_ascii=True, indent=2))
            else:
                print(f"{report['status']}: {report['counts']['cases']} cases; {len(report['issues'])} issue(s)")
                for issue in report["issues"]:
                    print(f"  {issue['code']} at {issue['location']}: {issue['message']}")
            return 0 if report["status"] == "PASS" else 1

        if report["status"] != "PASS":
            print("BLOCK: validation failed; no inputs exported.", file=sys.stderr)
            return 1
        try:
            manifest_bytes = safe_read(args.manifest, 1024 * 1024)
            if hashlib.sha256(manifest_bytes).hexdigest() != report["manifest_sha256"]:
                raise ValueError("Manifest changed")
            manifest = strict_json(manifest_bytes)
            case_bytes = safe_read(args.manifest.parent / manifest["cases"]["path"], 10 * 1024 * 1024)
            if hashlib.sha256(case_bytes).hexdigest() != manifest["cases"]["sha256"]:
                raise ValueError("Cases changed")
            lines = case_bytes.split(b"\n")
            if lines[-1:] == [b""]:
                lines.pop()
            rows = [strict_json(line) for line in lines]
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
