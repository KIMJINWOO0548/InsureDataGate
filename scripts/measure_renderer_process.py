"""Fresh-process worker for own prior/current offline renderer measurements."""
import argparse
import hashlib
import json
from pathlib import Path
import statistics
import sys
import time
import tracemalloc
import types

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--renderer", type=Path, required=True)
    parser.add_argument("--html", type=Path, required=True)
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--memory", action="store_true")
    args = parser.parse_args()
    source = args.renderer.read_bytes()
    module = types.ModuleType("insuredatagate._measured_own_renderer")
    module.__package__ = "insuredatagate"
    exec(compile(source, str(args.renderer), "exec"), module.__dict__)
    report = json.loads(args.report.read_bytes())
    durations = []
    for _ in range(args.repeats):
        started = time.perf_counter()
        html = module.render_html(report)
        durations.append(time.perf_counter() - started)
    peak = None
    if args.memory:
        tracemalloc.start()
        module.render_html(report)
        peak = tracemalloc.get_traced_memory()[1]
        tracemalloc.stop()
    with args.html.open("xb") as output:
        output.write(html.encode("utf-8"))
    print(json.dumps({"seconds": durations, "median_seconds": statistics.median(durations),
                      "peak_python_bytes": peak, "timings_include_profiler": False,
                      "fresh_process": True, "html_bytes": len(html.encode("utf-8")),
                      "renderer_sha256": hashlib.sha256(source).hexdigest(),
                      "rail_entities": html.count('class="rail-entity'),
                      "entity_target_selectors": html.count(' .rail-entity[href=')}))


if __name__ == "__main__":
    main()
