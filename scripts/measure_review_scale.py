"""Reproducible local synthetic capacity measurement; no competitor benchmark.

Uses the documented 10,000-case limit, unique groups and balanced split coverage.
Output contains metadata and redacted reports only. Existing outputs are refused.
Python peak allocations are traced memory, not whole-process RSS.
"""
import argparse
import hashlib
import json
from pathlib import Path
import statistics
import sys
import time
import tracemalloc
import subprocess

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT)]
from insuredatagate.comparison import review
from insuredatagate.validator import verify
from tests.helpers import DatasetFixture


def fixture(root, count):
    root.mkdir()
    dataset = DatasetFixture(root)
    dataset.cases = [{"case_id": f"case-{i:05}", "group_id": f"group-{i:05}",
                      "split": ("train", "validation", "test")[i % 3],
                      "source_ids": ["fictional-rules-v1"],
                      "input": f"SYNTHETIC capacity case {i:05}; fictional local rule?",
                      "created_by": "fictional-author"} for i in range(count)]
    dataset.gold = [{"case_id": c["case_id"], "expected": f"PRIVATE_SYNTHETIC_ANSWER_{i:05}",
                     "review_status": "APPROVED", "reviewed_by": "fictional-reviewer"}
                    for i, c in enumerate(dataset.cases)]
    dataset.save()
    return dataset


def measure(call, repeats, memory=False):
    durations = []
    for _ in range(repeats):
        started = time.perf_counter()
        result = call()
        durations.append(time.perf_counter() - started)
    peak = None
    if memory:
        tracemalloc.start()
        call()
        peak = tracemalloc.get_traced_memory()[1]
        tracemalloc.stop()
    return result, {"seconds": durations, "median_seconds": statistics.median(durations),
                    "peak_python_bytes": peak, "timings_include_profiler": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--cases", type=int, default=1000)
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--memory", action="store_true", help="One separate traced-memory pass per operation")
    parser.add_argument("--baseline-revision", help="Compare own prior renderer from a local Git revision against the identical checked report")
    args = parser.parse_args()
    if not 3 <= args.cases <= 10000 or not 1 <= args.repeats <= 7:
        parser.error("cases must be 3..10000; repeats must be 1..7")
    args.output.mkdir(parents=True, exist_ok=False)
    baseline = fixture(args.output / "baseline", args.cases)
    candidate = fixture(args.output / "candidate", args.cases)
    candidate.source.write_bytes(b"SYNTHETIC capacity source: intentionally revised.\n")
    candidate.manifest["version"] = "capacity-2"
    candidate.repin()
    checked, validation_metrics = measure(lambda: verify(candidate.path), args.repeats, args.memory)
    print("validation complete", flush=True)
    report, review_metrics = measure(lambda: review(baseline.path, candidate.path), args.repeats, args.memory)
    print("review complete", flush=True)
    report_path = args.output / "redacted-review.json"
    report_path.write_bytes(json.dumps(report).encode("utf-8"))
    def isolated_renderer(source_path, html_path):
        command = [sys.executable, str(ROOT / "scripts/measure_renderer_process.py"),
                   "--report", str(report_path), "--renderer", str(source_path),
                   "--html", str(html_path), "--repeats", str(args.repeats)]
        if args.memory:
            command.append("--memory")
        return json.loads(subprocess.check_output(command, cwd=ROOT, timeout=120))
    baseline_metrics = None
    if args.baseline_revision:
        source = subprocess.check_output(["git", "show", f"{args.baseline_revision}:src/insuredatagate/reporting.py"], cwd=ROOT)
        source_path = args.output / "own-prior-renderer.py"
        source_path.write_bytes(source)
        baseline_metrics = isolated_renderer(source_path, args.output / "before.html")
        baseline_metrics["revision"] = args.baseline_revision
    render_metrics = isolated_renderer(ROOT / "src/insuredatagate/reporting.py", args.output / "review.html")
    html = (args.output / "review.html").read_text(encoding="utf-8")
    print("render complete", flush=True)
    assert checked["status"] == report["status"] == "PASS"
    assert report["review"]["summary"]["source_only_case_count"] == args.cases
    assert "SYNTHETIC capacity case" not in html
    assert "PRIVATE_SYNTHETIC_ANSWER_" not in html
    assert "SYNTHETIC capacity source" not in html
    assert "SYNTHETIC_SOURCE_BODY_ONLY" not in html
    output_bytes = html.encode("utf-8")
    metrics = {"scope": "own offline synthetic source-only change; no external product timings",
               "cases_per_snapshot": args.cases, "repeats": args.repeats,
               "fixture_sha256": {"baseline": hashlib.sha256(baseline.path.read_bytes()).hexdigest(),
                                   "candidate": hashlib.sha256(candidate.path.read_bytes()).hexdigest()},
               "validation": validation_metrics, "review": review_metrics, "render": render_metrics,
               "prior_renderer": baseline_metrics,
               "html_bytes": len(output_bytes), "rail_entities": html.count('class="rail-entity'),
               "entity_target_selectors": html.count(' .rail-entity[href='),
               "source_only_count": report["review"]["summary"]["source_only_case_count"],
               "private_body_absent": True, "python": sys.version.split()[0]}
    (args.output / "metrics.json").write_bytes(json.dumps(metrics, indent=2).encode("utf-8"))
    print(json.dumps(metrics))


if __name__ == "__main__":
    main()
