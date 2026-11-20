"""Compare own before/after redacted HTML at equal viewports, offline in Chrome.

Requires the existing optional browser environment. Never regenerates or changes
datasets, uploads anything, or claims an external-product speed comparison.
"""
import argparse
import json
from pathlib import Path
import statistics
from time import perf_counter
from playwright.sync_api import sync_playwright


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--before", type=Path, required=True)
    parser.add_argument("--after", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--repeats", type=int, default=3)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    result = {"scope": "own identical synthetic checked report; cold browser context per sample; offline Chrome",
              "viewport": [1440, 900], "runs": {}, "external_requests": []}
    try:
        with sync_playwright() as playwright:
            with playwright.chromium.launch(channel="chrome", headless=True) as browser:
                result["browser"] = browser.version
                for name, path in (("before", args.before), ("after", args.after)):
                    values = []
                    for sample in range(args.repeats):
                        context = browser.new_context(viewport={"width": 1440, "height": 900}, offline=True, reduced_motion="reduce")
                        context.on("request", lambda request: result["external_requests"].append(request.url) if request.url.startswith(("https:", "http:")) else None)
                        page = context.new_page()
                        page.set_default_timeout(30000)
                        try:
                            started = perf_counter()
                            page.goto(path.resolve().as_uri(), wait_until="load", timeout=30000)
                            metrics = page.evaluate("""() => ({height:document.body.offsetHeight,
                                cases:document.querySelectorAll('.dossier[id^="case-"]').length,
                                sources:document.querySelectorAll('.dossier[id^="source-"]').length,
                                rails:document.querySelectorAll('.rail-entity').length,
                                width:document.documentElement.scrollWidth, client:innerWidth,
                                resources:performance.getEntriesByType('resource').length})""")
                            values.append(perf_counter() - started)
                            assert metrics["width"] <= metrics["client"] and metrics["resources"] == 0
                            if sample == 0:
                                result["runs"][name] = {"metrics": metrics}
                                page.screenshot(path=str(args.output / f"{name}-viewport.png"))
                            if name == "after" and sample == 0:
                                last = f"case-{metrics['cases'] - 1}"
                                page.evaluate("id => location.hash = id", last)
                                page.wait_for_function("id => document.activeElement.id === id || location.hash === '#'+id", arg=last)
                                page.locator("#" + last).scroll_into_view_if_needed()
                                assert page.locator("#" + last).is_visible()
                                result["last_case_anchor"] = last
                                page.screenshot(path=str(args.output / "after-last-case.png"))
                                page.locator('nav.filters a[href="#view-test"]').click()
                                actual = page.locator('.dossier[id^="case-"]:visible').count()
                                expected = sum(i % 3 == 2 for i in range(metrics["cases"]))
                                assert actual == expected
                                result["test_split_cases"] = actual
                                page.set_viewport_size({"width": 390, "height": 844})
                                assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
                                page.screenshot(path=str(args.output / "after-mobile.png"))
                        finally:
                            context.close()
                    result["runs"][name].update(seconds=values, median_seconds=statistics.median(values))
        assert not result["external_requests"]
        result["status"] = "PASS"
        return 0
    except Exception as error:
        result["status"] = "FAIL"
        result["error"] = f"{type(error).__name__}: {error}"
        return 1
    finally:
        (args.output / "result.json").write_bytes(json.dumps(result, indent=2).encode("utf-8"))
        print(json.dumps(result))


if __name__ == "__main__":
    raise SystemExit(main())
