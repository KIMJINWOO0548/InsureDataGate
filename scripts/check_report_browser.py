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
  const contrasts = [...document.querySelectorAll('p,th,td,dd,dt,h1,h2,h3,li,a,label,summary,small,code,.filter-state,.change-kind,.status,.meta,.muted,.empty,.eyebrow,footer,.review')].filter(visible).map(el => {
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
    status:document.querySelector('.status')?.textContent,
    useful:[...document.querySelectorAll('.direct .dossier,.sources .dossier,.notice,.empty-review')].filter(visible).map(el=>{const r=el.getBoundingClientRect();return {className:el.className,top:r.top,bottom:r.bottom,height:r.height}}),
    inventoryClosed:!document.querySelector('#inventory')?.open,
    csp:document.querySelector('meta[http-equiv="Content-Security-Policy"]')?.content, contrasts};
}"""


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def states(output):
    from insuredatagate.comparison import review
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
    source_only = output / "source-only-fixture"
    shutil.copytree(baseline.parent, source_only)
    source_manifest_path = source_only / "manifest.json"
    source_manifest = json.loads(source_manifest_path.read_text(encoding="utf-8"))
    source_manifest["version"] = "browser-source-only"
    source_path = source_only / source_manifest["sources"][0]["path"]
    source_path.write_bytes(source_path.read_bytes() + b"\nSynthetic browser fixture source revision.\n")
    source_manifest["sources"][0]["sha256"] = hashlib.sha256(source_path.read_bytes()).hexdigest()
    source_manifest_path.write_text(json.dumps(source_manifest) + "\n", encoding="utf-8")
    add_remove = output / "added-removed-fixture"
    shutil.copytree(baseline.parent, add_remove)
    add_manifest_path = add_remove / "manifest.json"
    add_manifest = json.loads(add_manifest_path.read_text(encoding="utf-8"))
    add_manifest["version"] = "browser-added-removed"
    for role in ("cases", "gold"):
        path = add_remove / add_manifest[role]["path"]
        records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
        records[0]["case_id"] = "browser-added-train"
        path.write_text("".join(json.dumps(record, ensure_ascii=False) + "\n" for record in records), encoding="utf-8")
        add_manifest[role]["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    add_manifest_path.write_text(json.dumps(add_manifest) + "\n", encoding="utf-8")
    reports = {
        "changed": review(baseline, candidate),
        "unchanged": review(baseline, baseline),
        "partial": review(baseline, missing),
        "blocked": verify(missing),
        "long-malicious": verify(manifest_path),
        "version-reused": review(baseline, reused_path),
        "source-only": review(baseline, source_manifest_path),
        "added-removed": review(baseline, add_manifest_path),
    }
    for name, report in reports.items():
        require(report["status"] == ("BLOCK" if name in ("partial", "blocked", "version-reused") else "PASS"), f"{name}: unexpected gate status")
    require(reports["changed"]["content_changed"] is True, "changed fixture must change content")
    require(reports["unchanged"]["content_changed"] is False and reports["unchanged"]["review_required"] is False, "unchanged fixture mismatch")
    require(reports["partial"]["changes"] is None, "partial fixture must suppress changes")
    require(reports["version-reused"]["content_changed"] and reports["version-reused"]["changes"] is not None, "reused version must block without hiding available changes")
    require(len(reports) * len(VIEWPORTS) == 32, "expected eight states and four viewports")
    source_review = reports["source-only"]["review"]
    require(source_review["summary"] == {"case_count": 6, "direct_case_count": 0, "source_count": 1, "source_only_case_count": 6}, "source-only counts mismatch")
    require(all(case["status"] == "affected" and case["fields"] == {"case": [], "gold": []} for case in source_review["cases"]), "source-only must have no direct changes")
    added_review = reports["added-removed"]["review"]
    require(added_review["summary"] == {"case_count": 2, "direct_case_count": 2, "source_count": 0, "source_only_case_count": 0}, "added/removed counts mismatch")
    require({case["status"] for case in added_review["cases"]} == {"added", "removed"}, "added/removed statuses mismatch")
    require(not reports["partial"]["review"]["available"] and reports["partial"]["review"]["summary"] is None, "partial review must be unavailable")
    require(reports["version-reused"]["review"]["available"], "version reuse must retain relationships")
    # Every private text value must remain absent from the serialized report and HTML.
    forbidden_text = []
    for directory in (baseline.parent, candidate.parent, fixture, reused, source_only, add_remove):
        for filename, field in (("cases.jsonl", "input"), ("gold.jsonl", "expected")):
            forbidden_text.extend(json.loads(line)[field] for line in (directory / filename).read_text(encoding="utf-8").splitlines())
        forbidden_text.append((directory / "sources/rules.txt").read_text(encoding="utf-8"))
    from insuredatagate.reporting import render_html
    for name, report in reports.items():
        serialized, html = json.dumps(report, ensure_ascii=False), render_html(report)
        require(all(private not in serialized and private not in html for private in forbidden_text), f"{name}: private body exposed")
    return reports, forbidden_text


def keyboard_activate(page, selector):
    """Reach the real native control with Tab, then activate with Enter."""
    for _ in range(240):
        if page.evaluate("selector => document.activeElement.matches(selector)", selector):
            page.keyboard.press("Enter")
            return
        page.keyboard.press("Tab")
    raise AssertionError(f"Keyboard cannot reach {selector}")


def check_interactions(page, report, name, viewport, output, evidence, observation):
    prefix = f"{name}/{viewport}"

    def overflow():
        require(page.evaluate("document.documentElement.scrollWidth <= document.documentElement.clientWidth"), prefix + ": interaction overflow")

    def capture(label):
        artifact = f"{name}-{viewport}-{label}.png"
        page.screenshot(path=str(output / artifact), full_page=True)
        evidence["interactionCaptures"].append({"state": name, "viewport": viewport, "interaction": label, "artifact": artifact})

    def select(kind):
        selector = f'nav.filters a[href="#view-{kind}"]'
        keyboard_activate(page, selector)
        result = page.evaluate("""kind => {
          const selected=document.querySelector('nav.filters a[href="#view-'+kind+'"]');
          const style=getComputedStyle(selected);
          const visible=[...document.querySelectorAll('.dossiers>.group')].filter(el=>el.getClientRects().length);
          const target=document.querySelector('.filter-state:target');
          return {target:target?.id,focus:document.activeElement===target,
            selected:style.backgroundColor!=='rgba(0, 0, 0, 0)'&&parseInt(style.fontWeight)>=600,
            visible:visible.map(el=>({kind:['direct','affected','sources'].find(k=>el.classList.contains(k)),empty:el.classList.contains('empty-group'),count:el.querySelectorAll('.dossier').length})),
            controls:selected.getAttribute('aria-controls')};
        }""", kind)
        require(result["target"] == "view-" + kind and result["focus"] and result["selected"], prefix + ": filter selected/focus appearance failed")
        require(result["controls"] == "dossier-list", prefix + ": filter scope missing")
        if kind == "all":
            require(all(not group["empty"] for group in result["visible"]), prefix + ": unselected empty group visible")
        else:
            require(len(result["visible"]) == 1 and result["visible"][0]["kind"] == kind, prefix + ": filter retained another group")
        observation.setdefault("filters", {})[kind] = result
        overflow()

    def linked(selector, target_prefix):
        link = page.locator(selector).first
        target = link.get_attribute("href")[1:]
        require(target.startswith(target_prefix), prefix + ": wrong dossier relationship target")
        keyboard_activate(page, selector + f'[href="#{target}"]')
        require(page.evaluate("target => document.activeElement.id===target && !!document.activeElement.getClientRects().length", target), prefix + ": relationship does not focus visible dossier")
        require(page.locator('.filter-state:target').count() == 0, prefix + ": dossier link must reset fragment filter")
        require(page.locator('.empty-group:visible').count() == 0, prefix + ": reset exposed empty groups")
        selection = page.evaluate("""target => {
          const selected=document.querySelector('.rail-entity[href="#'+target+'"]');
          const all=document.querySelector('nav.filters a[href="#view-all"]');
          return {rail:selected && parseInt(getComputedStyle(selected).fontWeight)>=600,
                  all:all && parseInt(getComputedStyle(all).fontWeight)>=600};
        }""", target)
        require(selection["rail"] and selection["all"], prefix + ": selected dossier or reset All state is inconsistent")
        overflow()
        capture(target_prefix.rstrip('-') + "-linked")
        return target

    review = report.get("review", {})
    summary = review.get("summary") or {}
    if page.locator('nav.filters').count():
        require(page.locator('input[type="radio"]').count() == 0, prefix + ": expected fragment filters")
        require(page.locator('.empty-group:visible').count() == 0, prefix + ": empty groups visible initially")
        for kind in ("direct", "affected", "sources", "all"):
            select(kind)
            capture(kind + "-filtered")
        if summary.get("source_count") and summary.get("case_count"):
            select("sources")
            observation["sourceToCase"] = linked('.sources .dossier a[href^="#case-"]', "case-")
            # Regression: a previous :target dossier must not survive a new filter.
            select("direct")
            require(page.locator('.sources:visible,.affected:visible').count() == 0, prefix + ": linked target leaked through Direct cases filter")
            if summary["direct_case_count"]:
                require(page.locator('.direct .dossier:visible').count() == summary["direct_case_count"], prefix + ": direct dossier count mismatch")
            else:
                require(name == "source-only" and page.locator('.direct.empty-group:visible').count() == 1, prefix + ": source-only empty direct semantics failed")
            capture("direct-after-linked")
            select("all")
            observation["caseToSource"] = linked('.dossiers .group:not(.sources) .dossier a[href^="#source-"]', "source-")
            select("all")
        if name == "source-only":
            require(page.locator('.affected .dossier:visible').count() == 6 and page.locator('.direct:visible').count() == 0, prefix + ": source-only All semantics mismatch")
    inventory = page.locator('#inventory')
    require(inventory.get_attribute('open') is None, prefix + ": inventory unexpectedly opened")
    integrity = page.locator('#integrity')
    require(integrity.get_attribute('open') is None, prefix + ": full hashes must start collapsed")
    keyboard_activate(page, '#integrity > summary')
    require(integrity.get_attribute('open') is not None, prefix + ": keyboard full-hash disclosure failed")
    sides = (report['baseline'], report['candidate']) if 'baseline' in report else (report,)
    digests = [side[key] for side in sides for key in ('manifest_sha256', 'content_sha256') if side.get(key)]
    for digest in digests:
        require(len(digest) == 64 and digest in integrity.inner_text(), prefix + ": full digest missing")
        require(page.evaluate("""digest => [...document.querySelectorAll('#integrity .hash')].some(el => {
          const r=el.getBoundingClientRect(),s=getComputedStyle(el);
          return el.textContent===digest && r.width>0 && r.height>0 && s.overflow!=='hidden' && el.scrollWidth<=el.clientWidth;
        })""", digest), prefix + ": full digest clipped")
    observation["fullHashCount"] = len(digests)
    overflow()
    capture("full-hashes")


def run(output, evidence, channel):
    from playwright.sync_api import sync_playwright
    from insuredatagate.reporting import render_html

    evidence["versions"] = {name: version(name) for name in ("playwright", "pyee", "greenlet", "typing_extensions")}
    evidence["versions"]["python"] = platform.python_version()
    evidence["sourceHashes"] = {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in (*(ROOT / "src/insuredatagate" / (name + ".py") for name in ("validator", "comparison", "guidance", "cli", "reporting")), Path(__file__))}
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
                        viewport_artifact = f"{name}-{viewport}-viewport.png"
                        page.screenshot(path=str(output / viewport_artifact), full_page=False)
                        metrics = page.evaluate(DOM_METRICS)
                        observation = {"state": name, "viewport": viewport, "artifact": artifact, "viewportArtifact": viewport_artifact, "metrics": metrics, "httpRequests": requests, "status": "fail"}
                        evidence["observations"].append(observation)
                        evidence["renderedEvidence"].append({"viewport": viewport, "artifact": artifact, "observation": f"Actual offline {channel} full-page {name} report, gate {report['status']}."})
                        require(metrics["inventoryClosed"], f"{name}/{viewport}: inventory must start closed")
                        require(metrics["csp"] == "default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'", f"{name}/{viewport}: CSP mismatch")
                        if width in (375, 390) and ((report.get("review", {}).get("summary") or {}).get("case_count", 0) or report["status"] == "BLOCK"):
                            require(any(item["top"] >= 0 and item["top"] + min(80, item["height"]) <= height for item in metrics["useful"]), f"{name}/{viewport}: no useful dossier/recovery in first viewport")
                        if report["status"] == "BLOCK":
                            require(page.evaluate("document.querySelector('.notice').compareDocumentPosition(document.querySelector('.workspace')) & Node.DOCUMENT_POSITION_FOLLOWING"), f"{name}/{viewport}: recovery must precede work")
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
                        check_interactions(page, report, name, viewport, output, evidence, observation)
                        observation["status"] = "pass"
                    finally:
                        context.close()
        finally:
            browser.close()
    evidence["accessibility"] = {"status": "pass", "evidence": f"All {len(reports)*len(VIEWPORTS)} DOM checks: lang/captions/th scopes, native Tab/Enter skip-to-main, issue-to-findings, fragment filters, both dossier link directions and full hashes; initially closed inventory and recovery before work, visible outlines, issue target >=44px, sampled contrast >=4.5; no static alerts; reduced-motion context."}
    evidence["responsive"] = {"status": "pass", "evidence": "Eight states at four target sizes including 375px and landscape have scrollWidth <= clientWidth; actual full-page captures retained."}
    for state, trigger in (("success", "PASS changed and malicious-metadata verifier reports"), ("empty", "unchanged comparison without content/version changes"), ("error", "missing manifest BLOCK verifier"), ("partial", "PASS baseline and missing candidate, changes unavailable")):
        evidence["contentStates"][state] = {"status": "pass", "evidence": trigger + "; actual DOM gate state and offline resource checks passed. See observations and screenshots."}
    evidence["baseObservationCount"] = len(evidence["observations"])
    require(evidence["baseObservationCount"] == 32, "expected exactly 32 base observations")
    evidence["reviewStates"] = {name: {"gate": report["status"], "schema": report["schema_version"], "summary": report.get("review", {}).get("summary")} for name, report in reports.items()}
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
    evidence = {"status": "fail", "contract": "docs/REVIEW_WORKSPACE.md (0.3 review workspace contract)", "targetViewports": [f"{w}x{h}" for w, h in VIEWPORTS], "accessibility": {"status": "fail", "evidence": "Checks incomplete; inspect failure."}, "responsive": {"status": "fail", "evidence": "Checks incomplete; inspect failure."}, "contentStates": {"loading": {"status": "not-applicable", "reason": "Static offline result document has no asynchronous loading state."}, "permission": {"status": "not-applicable", "reason": "Static offline review has no authentication or permission action; unreadable input is a BLOCK result."}}, "renderedEvidence": [], "interactionCaptures": [], "observations": []}
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
