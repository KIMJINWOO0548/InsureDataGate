"""Offline Chrome check using the product CLI and independent fixture answers."""

import json
from pathlib import Path
import subprocess
import sys
import tempfile
from time import perf_counter
from unittest.mock import patch

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))
from insuredatagate import cli, validator
from tests.helpers import DatasetFixture
from tests.test_duplicate_review import set_inputs


def run(output):
    results = []
    output.mkdir(exist_ok=False)
    with tempfile.TemporaryDirectory() as tmp, sync_playwright() as playwright:
        root = Path(tmp)
        browser = playwright.chromium.launch(channel="chrome")
        examples = [
            ("exact-near-1", [("train", "Ａ   B"), ("test", "abcdefgxijklmnopq"),
              ("train", "a b"), ("validation", "PRIVATE_INPUT_MARKER"), ("train", "abcdefghijklmnopq")],
             ("case-1", "case-3", "case-5", "case-2"), (1, 3, 5, 2)),
            ("exact-near-2", [("validation", "PRIVATE_INPUT_MARKER"), ("train", "z y"),
              ("train", "abcdefghijklmnopq"), ("test", "abcdefgxijklmnopq"), ("train", "Ｚ  Y")],
             ("case-2", "case-5", "case-3", "case-4"), (2, 5, 3, 4)),
            ("exact-near-3", [("test", "abcdefgxijklmnopq"), ("train", "m n"),
              ("validation", "PRIVATE_INPUT_MARKER"), ("train", "ｍ   N"), ("train", "abcdefghijklmnopq")],
             ("case-2", "case-4", "case-5", "case-1"), (2, 4, 5, 1)),
            ("empty", [("train", "one"), ("validation", "two"), ("test", "three")], (), ()),
            ("limit", [*((split, f"{split} fictional row {n}") for split in ("train", "test") for n in range(225)),
                       ("validation", "brief")], (), ()),
            ("gate", [("train", "one"), ("validation", "one"), ("test", "three")], (), ()),
            ("snapshot", [("train", "one"), ("validation", "two"), ("test", "three")], (), ()),
        ]
        for name, rows, ids, lines in examples:
            fixture_path = root / name
            fixture_path.mkdir()
            fixture = DatasetFixture(fixture_path)
            set_inputs(fixture, rows)
            report = output / f"{name}.html"
            args = ["review-duplicates", str(fixture.path), "--json", "--html", str(report)]
            status = {"limit": "EXACT_ONLY", "gate": "UNAVAILABLE", "snapshot": "UNAVAILABLE"}.get(name, "COMPLETE")
            if name == "snapshot":
                original = validator.read_snapshot

                def mutate(path, clean_report):
                    fixture.source.write_bytes(b"PRIVATE_SOURCE_CHANGED")
                    return original(path, clean_report)

                with patch.object(validator, "read_snapshot", side_effect=mutate):
                    assert cli.main(args) == 1
            else:
                result = subprocess.run([sys.executable, "-m", "insuredatagate", *args], cwd=ROOT,
                                        capture_output=True, text=True, check=False)
                assert result.returncode == (0 if status == "COMPLETE" else 1), result.stderr
                assert json.loads(result.stdout)["status"] == status
                assert result.stderr == ""
            html = report.read_text(encoding="utf-8")
            for marker in ("PRIVATE_INPUT_MARKER", "PRIVATE_GOLD_DEMO", "SYNTHETIC_SOURCE_BODY_ONLY",
                           "PRIVATE_SOURCE_CHANGED", "abcdefghijklmnopq", str(root)):
                assert marker not in html, marker
            assert {"gate": "GATE_BLOCKED", "snapshot": "SNAPSHOT_CHANGED",
                    "limit": "LIMIT_EXCEEDED"}.get(name, status) in html
            for width, height in ((375, 812), (1440, 900)):
                page = browser.new_page(viewport={"width": width, "height": height})
                page.goto(report.resolve().as_uri())
                assert page.evaluate("document.documentElement.scrollWidth === document.documentElement.clientWidth")
                assert page.locator("header strong").inner_text() == status
                started = perf_counter()
                found = []
                if ids:
                    page.keyboard.press("Tab")
                    page.keyboard.press("Enter")
                    assert page.evaluate("document.activeElement.id") == "exact-train"
                    found += page.locator("#exact-train + ol li li code").all_text_contents()
                    page.keyboard.press("Tab")
                    page.keyboard.press("Enter")
                    assert page.evaluate("document.activeElement.id") == "summary"
                    for _ in range(4):
                        page.keyboard.press("Tab")
                    page.keyboard.press("Enter")
                    assert page.evaluate("document.activeElement.id") == "near-pairs"
                    found += page.locator("#near-pairs ~ ol li code").all_text_contents()
                    assert found[::2] == list(ids)
                    assert found[1::2] == [f"cases[{line}]" for line in lines]
                elapsed = perf_counter() - started
                assert elapsed < 120
                page.screenshot(path=output / f"{name}-{width}.png", full_page=True)
                results.append({"fixture": name, "width": width, "status": status,
                                "automated_keyboard_seconds": elapsed if ids else None,
                                "verified_labels": found})
                page.close()
    (output / "checks.json").write_text(json.dumps(results, indent=2), encoding="utf-8")


if __name__ == "__main__":
    run(Path(sys.argv[1]).resolve())
