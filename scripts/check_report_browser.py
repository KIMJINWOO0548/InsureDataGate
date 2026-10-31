"""Optional offline Chrome self-check; requires requirements-browser.lock.

Run with the optional development environment, never the runtime dependency set.
Existing output directories are refused. Screenshots and honest failure evidence
remain available when any check fails.
"""

import argparse
from datetime import datetime, timezone
import hashlib
from importlib.metadata import version
import json
from pathlib import Path
import platform
import shutil
import sys
import uuid


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
VIEWPORTS = ((375, 812), (390, 844), (844, 390), (1440, 900))

DOM_METRICS = r"""() => {
  const visible = el => el.getClientRects().length && getComputedStyle(el).visibility !== 'hidden';
  const rgba = value => value.match(/[\d.]+/g).map(Number);
  const lum = c => c.slice(0,3).map(v => v/255).map(v => v<=.04045?v/12.92:((v+.055)/1.055)**2.4).reduce((s,v,i)=>s+v*[.2126,.7152,.0722][i],0);
  const contrasts = [...document.querySelectorAll('p,th,td,dd,dt,h1,h2,.status,.meta,.muted,.empty,.eyebrow,footer,.review,a.issue-link')].filter(visible).map(el => {
    let ancestor=el, bg;
    while(ancestor) { bg=rgba(getComputedStyle(ancestor).backgroundColor); if(bg[3]===undefined || bg[3]===1) break; if(bg[3]>0) throw Error('Unsupported translucent background'); ancestor=ancestor.parentElement; }
    bg=ancestor?bg:[255,255,255];
    const fg=rgba(getComputedStyle(el).color); if(fg[3]!==undefined && fg[3]!==1) throw Error('Unsupported translucent text');
    const a=lum(fg), b=lum(bg);
    return {element:el.tagName.toLowerCase(),className:el.className,ratio:(Math.max(a,b)+.05)/(Math.min(a,b)+.05)};
  });
  return {scrollWidth:document.documentElement.scrollWidth,clientWidth:document.documentElement.clientWidth,
    lang:document.documentElement.lang, forbidden:document.querySelectorAll('script,iframe,img,image,link[rel="stylesheet"],object,embed,audio,video,source').length,
    resources:performance.getEntriesByType('resource').map(x=>x.name), xss:typeof window.__idg_xss !== 'undefined',
    missingScopes:document.querySelectorAll('th:not([scope])').length,
    missingCaptions:[...document.querySelectorAll('table')].filter(t=>!t.caption || !t.caption.textContent.trim()).length,
    status:document.querySelector('.status')?.textContent, contrasts};
}"""


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def states(output):
    from insuredatagate.comparison import compare
    from insuredatagate.validator import verify

    baseline = ROOT / "examples/insurance-demo/manifest.json"
    candidate = ROOT / "examples/insurance-demo-v2/manifest.json"
    missing = output / "missing-manifest.json"
    fixture = output / "metadata-fixture"
    shutil.copytree(baseline.parent, fixture)
    manifest_path = fixture / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["dataset_id"] = "d" * 128
    manifest["version"] = '</script><script>window.__idg_xss=1</script> & 한글'
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    reused = output / "reused-version-fixture"
    shutil.copytree(candidate.parent, reused)
    reused_path = reused / "manifest.json"
    reused_manifest = json.loads(reused_path.read_text(encoding="utf-8"))
    reused_manifest["version"] = json.loads(baseline.read_text(encoding="utf-8"))["version"]
    reused_path.write_text(json.dumps(reused_manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    reports = {
        "changed": compare(baseline, candidate),
        "unchanged": compare(baseline, baseline),
        "partial": compare(baseline, missing),
        "blocked": verify(missing),
        "long-malicious": verify(manifest_path),
        "version-reused": compare(baseline, reused_path),
    }
    for name, report in reports.items():
        require(report["status"] == ("BLOCK" if name in ("partial", "blocked", "version-reused") else "PASS"), f"{name}: unexpected gate status")
    require(reports["changed"]["content_changed"] is True, "changed fixture must change content")
    require(reports["unchanged"]["content_changed"] is False and reports["unchanged"]["review_required"] is False, "unchanged fixture mismatch")
    require(reports["partial"]["changes"] is None, "partial fixture must suppress changes")
    require(reports["version-reused"]["content_changed"] and reports["version-reused"]["changes"] is not None, "reused version must block without hiding available changes")
    # Every private text value must remain absent from the serialized report and HTML.
    forbidden_text = []
    for directory in (baseline.parent, candidate.parent):
        for filename, field in (("cases.jsonl", "input"), ("gold.jsonl", "expected")):
            forbidden_text.extend(json.loads(line)[field] for line in (directory / filename).read_text(encoding="utf-8").splitlines())
        forbidden_text.append((directory / "sources/rules.txt").read_text(encoding="utf-8"))
    return reports, forbidden_text


def run(output, evidence, channel):
    from playwright.sync_api import sync_playwright
    from insuredatagate.reporting import render_html

    evidence["versions"] = {name: version(name) for name in ("playwright", "pyee", "greenlet", "typing_extensions")}
    evidence["versions"]["python"] = platform.python_version()
    evidence["sourceHashes"] = {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in (ROOT / "src/insuredatagate/reporting.py", Path(__file__))}
    reports, forbidden_text = states(output)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel=channel, headless=True)
        evidence["versions"]["browser"] = browser.version
        evidence["versions"]["channel"] = channel
        try:
            for name, report in reports.items():
                html = render_html(report)
                serialized = json.dumps(report, ensure_ascii=False)
                for private in forbidden_text:
                    require(private not in html and private not in serialized, f"{name}: private body exposed")
                html_path = output / f"{name}.html"
                html_path.write_text(html, encoding="utf-8")
                (output / f"{name}.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
                for width, height in VIEWPORTS:
                    viewport = f"{width}x{height}"
                    context = browser.new_context(viewport={"width": width, "height": height}, offline=True, reduced_motion="reduce")
                    requests = []
                    context.on("request", lambda request: requests.append(request.url) if request.url.startswith(("http:", "https:")) else None)
                    try:
                        page = context.new_page()
                        page.goto(html_path.as_uri(), wait_until="load")
                        artifact = f"{name}-{viewport}.png"
                        page.screenshot(path=str(output / artifact), full_page=True)
                        metrics = page.evaluate(DOM_METRICS)
                        observation = {"state": name, "viewport": viewport, "artifact": artifact, "metrics": metrics, "httpRequests": requests, "status": "fail"}
                        evidence["observations"].append(observation)
                        evidence["renderedEvidence"].append({"viewport": viewport, "artifact": artifact, "observation": f"Actual offline {channel} full-page {name} report, gate {report['status']}."})
                        require(metrics["scrollWidth"] <= metrics["clientWidth"], f"{name}/{viewport}: horizontal overflow")
                        require(metrics["lang"] and not metrics["missingScopes"] and not metrics["missingCaptions"], f"{name}/{viewport}: semantic markup missing")
                        require(not metrics["forbidden"] and not metrics["resources"] and not requests and not metrics["xss"], f"{name}/{viewport}: active/external content")
                        require(metrics["status"] == report["status"], f"{name}/{viewport}: rendered gate status mismatch")
                        require(metrics["contrasts"] and min(item["ratio"] for item in metrics["contrasts"]) >= 4.5, f"{name}/{viewport}: text contrast below 4.5")
                        page.keyboard.press("Tab")
                        focus = page.evaluate("""() => {const e=document.activeElement,r=e.getBoundingClientRect(),s=getComputedStyle(e);return {skip:e.matches('a.skip'),outline:parseFloat(s.outlineWidth),style:s.outlineStyle,visible:r.left>=0&&r.right<=innerWidth&&r.top>=0&&r.bottom<=innerHeight}}""")
                        observation["skipFocus"] = focus
                        require(focus["skip"] and focus["visible"] and focus["outline"] >= 2 and focus["style"] != "none", f"{name}/{viewport}: skip link keyboard focus not visible")
                        page.keyboard.press("Enter")
                        observation["mainFocused"] = page.evaluate("document.activeElement === document.querySelector('main')")
                        require(observation["mainFocused"], f"{name}/{viewport}: skip Enter does not transfer focus to main")
                        issue_link = page.locator("a.issue-link")
                        if report["issues"]:
                            require(issue_link.count() == 1, f"{name}/{viewport}: issue summary missing")
                            page.keyboard.press("Tab")
                            issue_focus = page.evaluate("""() => {const e=document.activeElement,s=getComputedStyle(e),r=e.getBoundingClientRect();return {target:e.matches('a.issue-link'),outline:parseFloat(s.outlineWidth),height:r.height,visible:r.top>=0&&r.bottom<=innerHeight}}""")
                            observation["issueFocus"] = issue_focus
                            require(issue_focus["target"] and issue_focus["outline"] >= 2 and issue_focus["height"] >= 44 and issue_focus["visible"], f"{name}/{viewport}: issue link focus or target size failed")
                            page.keyboard.press("Enter")
                            observation["findingsFocused"] = page.evaluate("document.activeElement.id === 'issues'")
                            require(observation["findingsFocused"], f"{name}/{viewport}: issue summary does not reach findings")
                        else:
                            require(issue_link.count() == 0, f"{name}/{viewport}: empty issue link should not be interactive")
                        require(page.locator('[role="alert"], [aria-live]').count() == 0, "static reports must not create automatic alert behavior")
                        if name == "long-malicious":
                            require(report["version"] in page.locator("main").inner_text(), "malicious metadata not preserved as text")
                        observation["status"] = "pass"
                    finally:
                        context.close()
        finally:
            browser.close()
    evidence["accessibility"] = {"status": "pass", "evidence": f"All {len(reports)*len(VIEWPORTS)} DOM checks: lang/captions/th scopes, native Tab/Enter skip-to-main and issue-to-findings, visible outlines, issue target >=44px, sampled contrast >=4.5; no static alerts; reduced-motion context."}
    evidence["responsive"] = {"status": "pass", "evidence": "Six states at four target sizes including 375px and landscape have scrollWidth <= clientWidth; actual full-page captures retained."}
    for state, trigger in (("success", "PASS changed and malicious-metadata verifier reports"), ("empty", "unchanged comparison without content/version changes"), ("error", "missing manifest BLOCK verifier"), ("partial", "PASS baseline and missing candidate, changes unavailable")):
        evidence["contentStates"][state] = {"status": "pass", "evidence": trigger + "; actual DOM gate state and offline resource checks passed. See observations and screenshots."}
    evidence["status"] = "pass"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="New directory only (existing paths refused)")
    parser.add_argument("--channel", choices=("chrome", "chromium"), default="chrome", help="Installed Chrome locally; bundled Chromium in CI")
    args = parser.parse_args()
    output = args.output or ROOT / "reports/runs" / (datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-browser-" + uuid.uuid4().hex[:8])
    output = output.absolute()
    try:
        output.mkdir(parents=True, exist_ok=False)
    except FileExistsError:
        parser.error("output directory already exists; choose a new directory")
    evidence = {"status": "fail", "contract": "docs/QUALITY_UPGRADE.md#html-contract (HTML contract and design)", "targetViewports": [f"{w}x{h}" for w, h in VIEWPORTS], "accessibility": {"status": "fail", "evidence": "Checks incomplete; inspect failure."}, "responsive": {"status": "fail", "evidence": "Checks incomplete; inspect failure."}, "contentStates": {"loading": {"status": "not-applicable", "reason": "Static offline result document has no asynchronous loading state."}, "permission": {"status": "not-applicable", "reason": "Static offline review has no authentication or permission action; unreadable input is a BLOCK result."}}, "renderedEvidence": [], "observations": []}
    exit_code = 0
    try:
        run(output, evidence, args.channel)
    except Exception as exc:
        evidence["failure"] = {"type": type(exc).__name__, "message": str(exc)}
        exit_code = 1
    evidence["exitCode"] = exit_code
    evidence_path = output / "evidence.json"
    evidence_path.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{evidence['status'].upper()}: {evidence_path}")
    for artifact in evidence["renderedEvidence"]:
        print(output / artifact["artifact"])
    if exit_code:
        print(evidence["failure"]["message"], file=sys.stderr)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
