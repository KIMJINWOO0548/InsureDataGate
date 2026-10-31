"""Render redacted, deterministic offline validation and review workspaces."""

from html import escape

from .guidance import recovery


_STYLE = """
:root{color-scheme:light;--ink:#20252b;--muted:#626a74;--line:#dfe2e6;--paper:#fafbfc;--green:#216744;--red:#a22c35;--amber:#785622}
*{box-sizing:border-box}html{background:var(--paper);scroll-padding-top:1rem}body{margin:0;color:var(--ink);font:14px/1.55 system-ui,-apple-system,"Segoe UI",sans-serif}a{color:#345b87;text-underline-offset:3px;overflow-wrap:anywhere}a:hover{text-decoration-thickness:2px}a:focus-visible,summary:focus-visible{outline:3px solid #426a9e;outline-offset:3px}p{margin:.4rem 0;overflow-wrap:anywhere}h1{font-size:clamp(1.25rem,2.5vw,1.7rem);line-height:1.25;margin:.4rem 0 .65rem;font-weight:650;letter-spacing:-.025em;overflow-wrap:anywhere}h2{font-size:1rem;margin:0 0 .65rem;font-weight:650}h3{font-size:1rem;margin:0;overflow-wrap:anywhere}.eyebrow{font-size:.69rem;letter-spacing:.1em;text-transform:uppercase;color:var(--muted)}.meta,.empty{color:var(--muted)}code,.hash,.identity{font: .82rem/1.55 ui-monospace,SFMono-Regular,Consolas,monospace;overflow-wrap:anywhere;word-break:break-word}.skip{position:absolute;left:-9999px;top:.5rem;background:white;padding:.7rem}.skip:focus{left:1rem;z-index:5}main{max-width:1240px;margin:auto;padding:1.5rem 2rem}header{padding-bottom:1rem;border-bottom:1px solid var(--line)}.context{display:flex;gap:.55rem 1rem;align-items:center;flex-wrap:wrap}.status{display:inline-flex;align-items:center;gap:.35rem;font-size:.75rem;font-weight:700;color:var(--green)}.status:before{content:"";width:6px;height:6px;border-radius:50%;background:currentColor}.status.block{color:var(--red)}.human-state{color:var(--amber);font-size:.8rem}.context .meta{font-size:.8rem}.issue-link{display:inline-flex;align-items:center;min-height:44px;font-size:.8rem}.workspace{display:grid;grid-template-columns:180px minmax(0,1fr);gap:2rem;margin-top:1.4rem}.rail{border-right:1px solid var(--line);padding-right:1.2rem}.rail nav{position:sticky;top:1.5rem}.rail-label{margin:0 0 .7rem;font-size:.68rem;text-transform:uppercase;letter-spacing:.09em;color:var(--muted)}.rail a{display:block;min-height:44px;padding:.6rem 0;text-decoration:none;font-size:.82rem;color:var(--muted)}.rail a:hover{color:var(--ink)}.rail .index-count{float:right;font-variant-numeric:tabular-nums}.detail{min-width:0}.section-heading{display:flex;justify-content:space-between;align-items:baseline;gap:1rem;margin-bottom:.6rem}.section-heading p{font-size:.78rem}.work-intro{margin-bottom:1rem}.work-intro .tally{font-size:.85rem}.notice{border-left:3px solid var(--red);background:#fff5f4;padding:1rem 1.2rem;margin-top:1rem}.notice h2{color:var(--red)}.notice ol{margin:.45rem 0 .8rem;padding-left:1.25rem}.notice li{margin:.25rem 0}.recovery-item+.recovery-item{border-top:1px solid #ead4d5;padding-top:.75rem;margin-top:.75rem}.recovery-title{font-weight:650}.recovery-item code{color:var(--red);margin-right:.5rem}.filter-scope{min-width:0}.filter-state{display:none;font-size:.82rem;margin:0 0 .6rem;color:var(--muted)}.filter-state:target{display:block;outline:2px solid #426a9e;outline-offset:3px}.filters{display:flex;flex-wrap:wrap;gap:.2rem;border-bottom:1px solid var(--line);padding-bottom:.6rem;margin-bottom:1.2rem}.filters a{min-height:44px;display:inline-flex;align-items:center;padding:.4rem .75rem;font-size:.8rem;border:1px solid transparent;border-radius:4px;color:var(--muted);text-decoration:none}.filters a:hover{background:#eef0f3;color:var(--ink)}
.filter-scope:not(:has(>.filter-state:target))>.filters a[href="#view-all"],#view-all:target~.filters a[href="#view-all"],#view-direct:target~.filters a[href="#view-direct"],#view-affected:target~.filters a[href="#view-affected"],#view-sources:target~.filters a[href="#view-sources"]{background:#e9edf2;border-color:#c4ccd6;color:var(--ink);font-weight:650}
#view-direct:target~.dossiers>.group:not(.direct),#view-affected:target~.dossiers>.group:not(.affected),#view-sources:target~.dossiers>.group:not(.sources){display:none}
.group.empty-group{display:none}#view-direct:target~.dossiers>.group.direct,#view-affected:target~.dossiers>.group.affected,#view-sources:target~.dossiers>.group.sources{display:block}
.group{margin-bottom:2rem}.group>p{font-size:.82rem;color:var(--muted);margin-bottom:.8rem}.dossier{background:white;border:1px solid var(--line);margin:.65rem 0;scroll-margin-top:1rem}.dossier:target{outline:3px solid #6583a8;outline-offset:2px}.dossier-top{padding:.8rem 1rem;display:flex;align-items:center;gap:1rem;justify-content:space-between;border-bottom:1px solid var(--line)}.change-kind{font-size:.68rem;letter-spacing:.06em;text-transform:uppercase;color:var(--muted);flex-shrink:0}.dossier dl{margin:0;padding:.25rem 1rem .7rem}.dossier dl>div{display:grid;grid-template-columns:145px minmax(0,1fr);gap:1rem;padding:.5rem 0;border-bottom:1px solid #edf0f2}.dossier dl>div:last-child{border:0}.dossier dt{font-size:.78rem;color:var(--muted)}.dossier dd{margin:0;overflow-wrap:anywhere;font-size:.83rem}.links{display:flex;flex-wrap:wrap;gap:.25rem .7rem}.links a{display:inline-flex;align-items:center;min-height:44px}.impact-list{list-style:none;margin:0;padding:0}.impact-row{display:grid;grid-template-columns:minmax(0,1.6fr) minmax(0,1fr) minmax(0,1fr);gap:.75rem;padding:.5rem 0;border-bottom:1px solid var(--line);align-items:center}.impact-row:last-child{border:0}.impact-row a{display:inline-flex;align-items:center;min-height:44px}.impact-row small{display:block;color:var(--muted);font-size:.68rem}.relation-sides{display:grid;grid-template-columns:1fr 1fr;gap:1.4rem}.side-label{font-size:.68rem;color:var(--muted);text-transform:uppercase;letter-spacing:.04em;margin-bottom:.2rem}.case-ref{display:flex;align-items:baseline;gap:.5rem;padding:.25rem 0}.case-ref small{color:var(--muted)}details{border-top:1px solid var(--line);padding:.8rem 0}summary{cursor:pointer;font-size:.82rem;font-weight:600;min-height:44px;padding:.3rem 0}details[open]>summary{margin-bottom:.6rem}.inventory{margin-top:1.5rem}.inventory-row{display:flex;flex-wrap:wrap;gap:.4rem 1.1rem;font-size:.8rem;color:var(--muted)}.inventory-row strong{color:var(--ink);font-weight:550}.fingerprints{font-size:.76rem;color:var(--muted);margin:.5rem 0}.fingerprints code{font-size:.74rem}table{border-collapse:collapse;width:100%;table-layout:fixed;background:white}caption{text-align:left;font-size:.8rem;color:var(--muted);padding:.5rem 0}th,td{text-align:left;vertical-align:top;border-bottom:1px solid var(--line);padding:.6rem .5rem;overflow-wrap:anywhere}th{font-size:.75rem;color:var(--muted);font-weight:550}td{font-size:.82rem}.findings{margin:1.6rem 0}.findings td:first-child{font-family:ui-monospace,Consolas,monospace}footer{margin-top:1.5rem;padding-top:1rem;border-top:1px solid var(--line);font-size:.76rem;color:var(--muted);max-width:85ch}
@media(max-width:700px){main{padding:1rem}.workspace{display:block;margin-top:1rem}.rail{display:none}header{padding-bottom:.65rem}.eyebrow{font-size:.64rem}h1{margin:.3rem 0 .55rem}.context{gap:.3rem .8rem}.notice{padding:.8rem;margin-top:.8rem}.dossier-top{padding:.7rem .8rem}.dossier dl{padding:.2rem .8rem .6rem}.dossier dl>div{grid-template-columns:96px minmax(0,1fr);gap:.7rem}.relation-sides{grid-template-columns:1fr;gap:.8rem}.filters{gap:0;margin-bottom:1rem}.filters a{padding:.3rem .55rem;font-size:.75rem}.section-heading{display:flex}.section-heading>p{margin:0}.group{margin-bottom:1.4rem}.integrity th,.integrity td{display:block;width:100%;padding:.3rem .5rem}.integrity thead{display:none}.integrity tr{display:block;border-bottom:1px solid var(--line);padding:.4rem 0}.integrity td{border:0}.inventory-row{gap:.4rem .85rem}th,td{padding:.5rem .3rem;font-size:.76rem}}
.rail nav{max-height:calc(100vh - 3rem);overflow:auto;padding:0 .3rem}.rail .entity-heading{margin:1.25rem 0 .25rem}.rail .rail-entity{border-left:2px solid transparent;border-radius:3px;padding:.45rem .5rem;font-size:.75rem}.rail-entity code{font-size:.73rem}.filters a{gap:.3rem}.filters a span{font-variant-numeric:tabular-nums}.impact-row span{min-width:0;overflow-wrap:anywhere}.dossier.compact{display:grid;grid-template-columns:minmax(0,1.1fr) minmax(0,1fr);gap:.5rem 1.25rem;background:transparent;border:0;border-bottom:1px solid var(--line);margin:0;padding:.7rem .8rem}.compact h3{font-size:.82rem}.compact-heading{min-width:0}.compact-split{font-size:.75rem;margin:.2rem 0 0}.compact-split small{display:block;color:var(--muted);font-size:.68rem}.compact-links{font-size:.75rem}.compact-links>.meta{display:block}.compact-links .links a{font-size:.78rem}.compact-links code{font-size:inherit}
body:has(#view-direct:target) .rail .nav-sources,body:has(#view-direct:target) .rail .nav-affected,body:has(#view-affected:target) .rail .nav-direct,body:has(#view-affected:target) .rail .nav-sources,body:has(#view-sources:target) .rail .nav-direct,body:has(#view-sources:target) .rail .nav-affected{display:none}
@media(max-width:700px){.dossier dl>.relation-row{display:block}.relation-row>dd{padding-top:.5rem}.dossier.compact{display:block;padding:.7rem .5rem}.compact-heading{display:flex;align-items:baseline;justify-content:space-between;gap:.5rem}.compact-split{flex-shrink:0;margin:0}.compact-split small{font-size:.6rem}.compact-links{margin-top:.25rem}.compact-links>.meta{display:inline}.compact-links .links{display:inline-flex;vertical-align:middle;margin-left:.5rem}.filters{justify-content:space-between}}
@media print{html,body{background:white}main{max-width:none;padding:0}.rail,.filters,.filter-state,.skip{display:none}.workspace{display:block}.detail .dossiers>.group{display:block!important}.dossier{break-inside:avoid}a{color:inherit}}
"""


def _e(value):
    return escape(str(value), quote=True)


def _value(value):
    return "—" if value is None else _e(value)


def _status(value):
    value = value if value in ("PASS", "BLOCK") else "BLOCK"
    return f'<span class="status {"block" if value == "BLOCK" else "pass"}">{value}</span>'


def _issues(issues):
    rows = "".join(f'<tr><td>{_value(item.get("code"))}</td><td>{_value(item.get("location"))}</td><td>{_value(item.get("message"))}</td></tr>' for item in issues if type(item) is dict)
    if not rows:
        return '<p class="empty">No issues were recorded.</p>'
    return '<table><caption>Gate issues</caption><thead><tr><th scope="col">Code</th><th scope="col">Location</th><th scope="col">Reason</th></tr></thead><tbody>' + rows + '</tbody></table>'


def _recovery(issues):
    entries = []
    seen = set()
    priority = ("SNAPSHOT_CHANGED", "FILE_READ", "UNSAFE_PATH", "HASH_MISMATCH", "INVALID_JSON", "INVALID_JSONL", "INVALID_UTF8", "SCHEMA", "DATASET_ID_MISMATCH", "VERSION_REUSED")
    rank = {code: index for index, code in enumerate(priority)}
    for issue in sorted((item for item in issues if type(item) is dict), key=lambda item: rank.get(item.get("code"), len(priority))):
        if type(issue) is not dict or issue.get("code") in seen:
            continue
        code = issue.get("code")
        seen.add(code)
        guide = recovery(code)
        steps = "".join(f'<li>{_e(step)}</li>' for step in guide["steps"])
        entries.append(f'<div class="recovery-item"><p class="recovery-title"><code>{_value(code)}</code>{_e(guide["title"])}</p><ol>{steps}</ol></div>')
    if not entries:
        entries.append('<p>Inspect the gate findings and validate both datasets again before distribution.</p>')
    remaining = (f'<details><summary>{len(entries) - 1} other finding types · recovery steps</summary>' + "".join(entries[1:]) + '</details>') if len(entries) > 1 else ""
    return '<section class="notice" aria-labelledby="recovery"><h2 id="recovery" tabindex="-1">Recovery · local gate blocked</h2>' + entries[0] + remaining + '</section>'


def _inventory(base, candidate=None):
    keys = (("sources", "Sources"), ("cases", "Cases"), ("gold", "Gold"), ("train", "Train"), ("validation", "Validation"), ("test", "Test"))
    def count(side, key):
        return _value(side.get("counts", {}).get(key, 0)) if side.get("status") == "PASS" else "not checked"
    values = "".join(f'<span>{title} <strong>{count(base, key)}' + (f' → {count(candidate, key)}' if candidate is not None else '') + '</strong></span>' for key, title in keys)
    return '<details class="inventory" id="inventory"><summary>Inventory' + (' · baseline → candidate' if candidate is not None else '') + '</summary><div class="inventory-row">' + values + '</div></details>'


def _integrity(base, candidate=None):
    sides = (("Baseline", base), ("Candidate", candidate)) if candidate is not None else (("Dataset", base),)
    short = []
    rows = []
    for title, side in sides:
        hashes = []
        for key in ("manifest_sha256", "content_sha256"):
            digest = side.get(key)
            hashes.append(_value(digest))
            short.append(f'{title} {"manifest" if key == "manifest_sha256" else "content"} <code>{_e(digest[:12])}…</code>' if type(digest) is str else f'{title} {"manifest" if key == "manifest_sha256" else "content"} not checked')
        rows.append(f'<tr><th scope="row">{title}</th><td class="hash">{hashes[0]}</td><td class="hash">{hashes[1]}</td></tr>')
    return '<div class="fingerprints">Shortened fingerprints · display only<p>' + ' · '.join(short) + '</p></div><details id="integrity"><summary>Full integrity hashes</summary><p class="meta">Recorded consistency fingerprints, not independent authenticity.</p><table class="integrity"><caption>Manifest and semantic content SHA-256</caption><thead><tr><th scope="col">Side</th><th scope="col">Manifest</th><th scope="col">Content</th></tr></thead><tbody>' + ''.join(rows) + '</tbody></table></details>'


def _files(files):
    rows = "".join(f'<tr><th scope="row">{_value(row.get("path"))}</th><td class="hash">{_value(row.get("sha256"))}</td><td>{_value(row.get("bytes"))}</td></tr>' for row in files if type(row) is dict)
    if not rows:
        return '<p class="empty">No file hashes were observed.</p>'
    return '<table><caption>Observed files · full SHA-256</caption><thead><tr><th scope="col">Relative path</th><th scope="col">SHA-256</th><th scope="col">Bytes</th></tr></thead><tbody>' + rows + '</tbody></table>'


def _changes(changes):
    if changes is None:
        return '<p class="empty">Comparison is partial: change details are unavailable until both datasets pass validation and can be safely read. Counts are not checked.</p>'
    rows = []
    for key, title, id_key in (("cases_added", "Cases added", None), ("cases_removed", "Cases removed", None), ("cases_changed", "Cases changed", "case_id"), ("gold_changed", "Gold changed", "case_id"), ("sources_added", "Sources added", None), ("sources_removed", "Sources removed", None), ("sources_changed", "Sources changed", "source_id")):
        for item in changes.get(key, []):
            ident = item.get(id_key) if id_key and type(item) is dict else item if not id_key else None
            fields = ", ".join(_e(field) for field in item.get("fields", []) if type(field) is str) if id_key and type(item) is dict else "—"
            rows.append(f'<tr><td>{title}</td><td class="identity">{_value(ident)}</td><td>{fields}</td></tr>')
    if not rows:
        return '<p class="empty">No changes were recorded.</p>'
    return '<table><caption>Recorded changes (identifiers and field names only)</caption><thead><tr><th scope="col">Type</th><th scope="col">ID</th><th scope="col">Fields</th></tr></thead><tbody>' + ''.join(rows) + '</tbody></table><p class="meta">Case/source relationships are unavailable in comparison.v1. Generate a review report to inspect declared references.</p>'


def _links(ids, anchors):
    return '<div class="links">' + (' '.join(f'<a href="#{anchors[ident]}"><code>{_e(ident)}</code></a>' if ident in anchors else f'<code>{_e(ident)}</code>' for ident in ids) or '<span class="empty">None</span>') + '</div>'


def _field_row(label, content, wide=False):
    return ('<div class="relation-row">' if wide else '<div>') + f'<dt>{label}</dt><dd>{content}</dd></div>'


def _fields(values):
    labels = {"input": "Input text", "expected": "Gold answer", "source_ids": "Source links", "split": "Split assignment", "group_id": "Related-case group", "created_by": "Creator declaration", "reviewed_by": "Reviewer declaration", "review_status": "Review declaration", "sha256": "File fingerprint", "license": "Rights declaration", "status": "Source approval declaration", "approved_by": "Source reviewer declaration"}
    return ', '.join(_e(labels.get(value, value)) for value in values) or '<span class="empty">No direct field changes</span>'


def _review_index(review):
    """Build native destinations; CSS selectors use generated numeric IDs only."""
    if not review.get("available"):
        return "", ""
    links, styles = [], []
    for collection, key, prefix, title in (("cases", "case_id", "case", "Cases"), ("sources", "source_id", "source", "Sources")):
        if review[collection]:
            links.append(f'<p class="rail-label entity-heading">{title}</p>')
        for index, item in enumerate(review[collection]):
            target = f"{prefix}-{index}"
            kind = "sources" if prefix == "source" else "affected" if item["status"] == "affected" else "direct"
            links.append(f'<a class="rail-entity nav-{kind}" href="#{target}"><code>{_e(item[key])}</code></a>')
            styles.append(f'body:has(#{target}:target) .rail-entity[href="#{target}"]' + '{background:#e9edf2;color:var(--ink);font-weight:650;border-color:#b4c2d2}')
    return "".join(links), "".join(styles)


def _review_workspace(review):
    if not review.get("available"):
        return '<section class="group"><h2>Review details unavailable</h2><p>Comparison is partial or dataset identities differ. Cases, sources and impact counts: not checked. Resolve the findings before regenerating this review.</p></section>'
    cases, sources = review["cases"], review["sources"]
    case_anchors = {case["case_id"]: f'case-{index}' for index, case in enumerate(cases)}
    source_anchors = {source["source_id"]: f'source-{index}' for index, source in enumerate(sources)}
    groups = {"direct": [], "affected": [], "sources": []}
    for case in cases:
        fields, refs, splits = case["fields"], case["sources"], case["splits"]
        if case["status"] == "affected":
            groups["affected"].append(
                f'<article class="dossier compact" id="{case_anchors[case["case_id"]]}" tabindex="-1">'
                f'<div class="compact-heading"><h3><code>{_e(case["case_id"])}</code></h3>'
                f'<p class="compact-split"><small>Split · baseline → candidate</small><code>{_value(splits["baseline"])} → {_value(splits["candidate"])}</code></p></div>'
                '<div class="compact-links"><span class="meta">Changed source</span>' + _links(refs["changed"], source_anchors) + '</div></article>')
            continue
        rows = (_field_row("Why review", "A declared source changed; case and gold fields are unchanged.") if case["status"] == "affected" else _field_row("Case changes", _fields(fields["case"])) + _field_row("Gold changes", _fields(fields["gold"])))
        if case["status"] in ("added", "removed"):
            rows = _field_row("Record", f'{_e(case["status"].capitalize())} case and matching gold record; field-level comparison does not apply.')
        rows += _field_row("Split", f'Baseline <code>{_value(splits["baseline"])}</code> → Candidate <code>{_value(splits["candidate"])}</code>')
        rows += _field_row("Changed sources", _links(refs["changed"], source_anchors))
        rows += _field_row("Declared references", '<details' + (' open' if "source_ids" in fields["case"] or case["status"] in ("added", "removed") else '') + '><summary>All source links</summary><div class="relation-sides"><div><p class="side-label">Baseline</p>' + _links(refs["baseline"], source_anchors) + '</div><div><p class="side-label">Candidate</p>' + _links(refs["candidate"], source_anchors) + '</div></div></details>')
        group = "affected" if case["status"] == "affected" else "direct"
        kind = "source impact" if group == "affected" else case["status"]
        groups[group].append(f'<article class="dossier" id="{case_anchors[case["case_id"]]}" tabindex="-1"><div class="dossier-top"><h3><code>{_e(case["case_id"])}</code></h3><span class="change-kind">{_e(kind)}</span></div><dl>{rows}</dl></article>')
    for source in sources:
        splits = {side: {case["case_id"]: case["split"] for case in source["cases"][side]} for side in ("baseline", "candidate")}
        impact = []
        for ident in source["affected_case_ids"]:
            link = (f'<a href="#{case_anchors[ident]}"><code>{_e(ident)}</code></a>'
                    if ident in case_anchors else f'<code>{_e(ident)}</code>')
            memberships = ''.join(f'<span><small>{side.capitalize()}</small>{_e(splits[side].get(ident, "not referenced"))}</span>' for side in ("baseline", "candidate"))
            impact.append(f'<li class="impact-row">{link}{memberships}</li>')
        rows = _field_row("Source changes", _fields(source["fields"]) if source["status"] == "modified" else _e(source["status"].capitalize()) + ' source record')
        rows += _field_row("Linked cases", f'{len(source["affected_case_ids"])} unique case references; not causal proof.')
        rows += _field_row("Declared references", '<ul class="impact-list">' + ''.join(impact) + '</ul>' if impact else '<span class="empty">No declared references in either snapshot</span>', wide=True)
        groups["sources"].append(f'<article class="dossier" id="{source_anchors[source["source_id"]]}" tabindex="-1"><div class="dossier-top"><h3><code>{_e(source["source_id"])}</code></h3><span class="change-kind">{_e(source["status"])}</span></div><dl>{rows}</dl></article>')
    summary = review["summary"]
    if not summary["direct_case_count"] and not summary["source_count"]:
        return '<section class="empty-review"><h2>No content differences</h2><p>Both checked releases contain the same dataset content. The version and human review state remain visible above.</p></section>'
    case_word = "case" if summary["direct_case_count"] == 1 else "cases"
    source_word = "source" if summary["source_count"] == 1 else "sources"
    intro = f'<div class="work-intro"><h2>Changes to review</h2><p class="tally"><strong>{_value(summary["direct_case_count"])} {case_word} changed</strong> · <strong>{_value(summary["source_count"])} {source_word} changed</strong></p><p class="meta">{_value(summary["source_only_case_count"])} additional cases linked to changed sources. {_value(summary["case_count"])} unique cases in this review.</p></div>'
    controls, targets = [], []
    for ident, title, count in (("all", "All items", summary["case_count"] + summary["source_count"]), ("direct", "Cases", summary["direct_case_count"]), ("affected", "Linked", summary["source_only_case_count"]), ("sources", "Sources", summary["source_count"])):
        targets.append(f'<p class="filter-state" id="view-{ident}" tabindex="-1">Showing {title.lower()} ({_value(count)})</p>')
        controls.append(f'<a href="#view-{ident}" aria-controls="dossier-list">{title} <span>({_value(count)})</span></a>')
    sections = []
    for kind, ident, title, description in (("direct", "direct-cases", "Direct case changes", "Case and gold changes are grouped together; contents remain private."), ("sources", "changed-sources", "Changed sources", "Case membership and split from both checked snapshots; references do not prove causality or correctness."), ("affected", "affected-cases", "Source-only impact", "These cases have no direct field changes. A declared source reference changed.")):
        entries = ''.join(groups[kind]) or '<p class="empty">No changes in this group.</p>'
        empty = " empty-group" if not groups[kind] else ""
        sections.append(f'<section class="group {kind}{empty}" aria-labelledby="{ident}"><div class="section-heading"><h2 id="{ident}" tabindex="-1">{title}</h2><p>{len(groups[kind])} {"item" if len(groups[kind]) == 1 else "items"}</p></div><p>{description}</p>{entries}</section>')
    return intro + '<div class="filter-scope">' + ''.join(targets) + '<nav class="filters" aria-label="Filter review dossiers">' + ''.join(controls) + '</nav><div class="dossiers" id="dossier-list">' + ''.join(sections) + '</div></div>'


def render_html(report: dict) -> str:
    """Return UTF-8 HTML with only allowlisted report metadata and native controls."""
    comparison = report.get("schema_version") in ("insuredatagate.comparison.v1", "insuredatagate.review.v1")
    enriched = report.get("schema_version") == "insuredatagate.review.v1"
    base = report.get("baseline") or {} if comparison else report
    candidate = report.get("candidate") or {} if comparison else None
    dataset = (candidate.get("dataset_id") or base.get("dataset_id")) if comparison else base.get("dataset_id")
    issues = report.get("issues") or []
    status = report.get("status")
    if comparison:
        versions = f'Baseline <code>{_value(base.get("version"))}</code> → Candidate <code>{_value(candidate.get("version"))}</code>'
        if report.get("changes") is None:
            human = "Review required; comparison is partial."
        elif report.get("review_required"):
            human = "Review required because dataset content changed." if report.get("content_changed") else "Review required because the version changed."
        else:
            human = "No review required; content and version are unchanged."
    else:
        versions = f'Version <code>{_value(base.get("version"))}</code>'
        human = "Human review remains separate from local checks."
    issue_count = sum(type(item) is dict for item in issues)
    findings = f'<a class="issue-link" href="#issues">{issue_count} {"issue" if issue_count == 1 else "issues"} · View findings</a>' if issue_count else '<span class="meta">0 validation issues</span>'
    context = f'<div class="context"><span class="meta">{versions}</span><span>Local gate {_status(status)}</span><span class="human-state">{_e(human)}</span>{findings}</div>'
    recovery_html = _recovery(issues) if status != "PASS" else ''
    entity_links, entity_styles = _review_index(report.get("review") or {}) if enriched else ("", "")
    if enriched:
        work = _review_workspace(report.get("review") or {"available": False})
        summary = (report.get("review") or {}).get("summary") or {}
        links = ''.join(f'<a href="#{target}">{title}</a>' for key, target, title in (
            ("direct_case_count", "direct-cases", "Direct cases"),
            ("source_count", "changed-sources", "Changed sources"),
            ("source_only_case_count", "affected-cases", "Source impact"),
        ) if summary.get(key))
    elif comparison:
        work = '<section id="changes"><h2>Changes</h2>' + _changes(report.get("changes")) + '</section>'
        changes = report.get("changes")
        if type(changes) is dict:
            count = lambda keys: sum(len(changes.get(key, [])) for key in keys)
            work = f'<p class="meta">Change entries: {count(("cases_added", "sources_added"))} added · {count(("cases_removed", "sources_removed"))} removed · {count(("cases_changed", "gold_changed", "sources_changed"))} modified</p>' + work
        links = '<a href="#changes">Recorded changes</a>'
    else:
        files = report.get("files") or []
        work = f'<section id="files"><h2>Validation evidence</h2><p class="meta">{len(files)} local file fingerprints recorded. Contents remain private.</p><details id="file-evidence"><summary>Observed files · full fingerprints</summary>' + _files(files) + '</details></section>'
        links = '<a href="#files">Observed files</a>'
    rail = '<aside class="rail"><nav aria-label="Review sections"><p class="rail-label">Workspace</p>' + ('<a href="#recovery">Recovery</a>' if recovery_html else '') + links + entity_links + ('<a href="#issues">Gate findings</a>' if issue_count else '') + '<a href="#inventory">Inventory</a><a href="#integrity">Integrity hashes</a></nav></aside>'
    return ('<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">'
            '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'unsafe-inline\'; base-uri \'none\'; form-action \'none\'">'
            f'<title>{_value(dataset)} — InsureDataGate review</title><style>{_STYLE}{entity_styles}</style></head><body><a class="skip" href="#main">Skip to review</a><main id="main" tabindex="-1">'
            f'<header><div class="eyebrow">InsureDataGate / offline review</div><h1>{_value(dataset)}</h1>{context}</header>{recovery_html}'
            f'<div class="workspace">{rail}<div class="detail">{work}<section class="findings"><h2 id="issues" tabindex="-1">Gate findings</h2>{_issues(issues)}</section>'
            + _inventory(base, candidate) + _integrity(base, candidate) + '</div></div>'
            '<footer>PASS confirms local checks, not release approval. Rights and reviewer identities are unverified declarations. Review dataset identifiers, versions and relative paths before sharing. Case input, gold answers and source bodies are omitted.</footer></main></body></html>')
