"""Render redacted, offline HTML review documents for validation reports."""

from html import escape


_STYLE = """
:root{color-scheme:light;--ink:#202b2b;--muted:#536361;--paper:#f5f1e8;--panel:#fffdf8;--line:#d5d2c8;--teal:#086d67;--red:#a52c32}
*{box-sizing:border-box}html{background:var(--paper)}body{margin:0;color:var(--ink);font:16px/1.55 system-ui,-apple-system,"Segoe UI",sans-serif}
a{color:var(--teal)}a:focus-visible{outline:3px solid var(--red);outline-offset:3px}.issue-link{display:inline-flex;align-items:center;min-height:44px;max-width:100%;padding:.2rem .4rem;overflow-wrap:anywhere}.skip{position:absolute;left:-9999px;top:0;background:var(--panel);padding:.7rem}.skip:focus{left:1rem;z-index:2}
main{max-width:1120px;margin:auto;padding:2rem clamp(1rem,4vw,3rem)}header{border-bottom:2px solid var(--ink);padding-bottom:1.2rem;margin-bottom:1.4rem}h1{font-size:clamp(1.8rem,4vw,2.6rem);line-height:1.1;margin:.35rem 0;overflow-wrap:anywhere}.eyebrow{font-size:.78rem;font-weight:750;letter-spacing:.14em;text-transform:uppercase;color:var(--muted)}h2{font-size:1.25rem;margin:2rem 0 .6rem}p{margin:.45rem 0;overflow-wrap:anywhere}.meta{color:var(--muted)}.status{font-weight:800;color:var(--teal)}.status.block{color:var(--red)}.review{font-weight:750;color:var(--red)}
.summary{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:.65rem;margin:1.2rem 0}.summary div{padding:.75rem;border-top:2px solid var(--teal);background:var(--panel)}.summary dt{font-size:.78rem;color:var(--muted)}.summary dd{margin:.1rem 0 0;font-size:1.15rem;font-weight:700}
table{border-collapse:collapse;width:100%;background:var(--panel);table-layout:fixed}caption{text-align:left;font-weight:700;padding:.55rem 0}th,td{text-align:left;vertical-align:top;border-bottom:1px solid var(--line);padding:.55rem .65rem;overflow-wrap:anywhere}th{font-size:.83rem;color:var(--muted)}code,.hash{font: .84rem/1.45 ui-monospace,SFMono-Regular,Consolas,monospace;overflow-wrap:anywhere;word-break:break-word}.notice{border-left:4px solid var(--red);padding:.7rem 1rem;background:#fff8f4}.empty{color:var(--muted)}footer{border-top:1px solid var(--line);margin-top:2.5rem;padding-top:.75rem;color:var(--muted);font-size:.85rem}
@media(max-width:520px){main{padding:1.1rem .85rem}th,td{padding:.45rem .35rem;font-size:.9rem}.summary{grid-template-columns:repeat(2,minmax(0,1fr))}}
@media(min-width:1000px){.summary{grid-template-columns:repeat(6,minmax(0,1fr))}}
@media print{html,body{background:#fff}.skip{display:none}main{max-width:none;padding:0}.summary div,table,.notice{background:#fff;break-inside:avoid}a{color:inherit}}
"""


def _e(value):
    return escape(str(value), quote=True)


def _value(value):
    return "—" if value is None else _e(value)


def _status(value):
    value = value if value in ("PASS", "BLOCK") else "BLOCK"
    return f'<span class="status {"block" if value == "BLOCK" else "pass"}">{value}</span>'


def _summary(counts, label="Dataset"):
    keys = (("sources", "Sources"), ("cases", "Cases"), ("gold", "Gold"), ("train", "Train"), ("validation", "Validation"), ("test", "Test"))
    return f'<h2>{_e(label)} summary</h2><dl class="summary">' + "".join(
        f'<div><dt>{title}</dt><dd>{_value(counts.get(key, 0) if type(counts) is dict else 0)}</dd></div>' for key, title in keys
    ) + "</dl>"


def _issues(issues):
    if not issues:
        return '<p class="empty">No issues were recorded.</p>'
    rows = "".join(f'<tr><td>{_value(item.get("code"))}</td><td>{_value(item.get("location"))}</td><td>{_value(item.get("message"))}</td></tr>' for item in issues if type(item) is dict)
    if not rows:
        return '<p class="empty">No issues were recorded.</p>'
    return '<table><caption>Gate issues</caption><thead><tr><th scope="col">Code</th><th scope="col">Location</th><th scope="col">Reason</th></tr></thead><tbody>' + rows + '</tbody></table>'


def _files(files):
    if not files:
        return '<p class="empty">No file hashes were observed.</p>'
    rows = "".join(f'<tr><th scope="row">{_value(row.get("path"))}</th><td><span class="hash">{_value(row.get("sha256"))}</span></td><td>{_value(row.get("bytes"))}</td></tr>' for row in files if type(row) is dict)
    if not rows:
        return '<p class="empty">No file hashes were observed.</p>'
    return '<table><caption>Observed files</caption><thead><tr><th scope="col">Relative path</th><th scope="col">SHA-256</th><th scope="col">Bytes</th></tr></thead><tbody>' + rows + '</tbody></table>'


def _changes(changes):
    if changes is None:
        return '<p class="notice">Comparison is partial: change details are unavailable until both datasets pass validation and can be safely read.</p>'
    rows = []
    for key, title, id_key in (("cases_added", "Cases added", None), ("cases_removed", "Cases removed", None), ("cases_changed", "Cases changed", "case_id"), ("gold_changed", "Gold changed", "case_id"), ("sources_added", "Sources added", None), ("sources_removed", "Sources removed", None), ("sources_changed", "Sources changed", "source_id")):
        for item in changes.get(key, []) if type(changes) is dict else []:
            ident = item.get(id_key) if id_key and type(item) is dict else item if not id_key else None
            fields = ", ".join(_e(field) for field in item.get("fields", []) if type(field) is str) if id_key and type(item) is dict else "—"
            rows.append(f'<tr><td>{title}</td><td>{_value(ident)}</td><td>{fields}</td></tr>')
    if not rows:
        return '<p class="empty">No changes were recorded.</p>'
    return '<table><caption>Recorded changes (identifiers and field names only)</caption><thead><tr><th scope="col">Type</th><th scope="col">ID</th><th scope="col">Fields</th></tr></thead><tbody>' + "".join(rows) + '</tbody></table>'


def render_html(report: dict) -> str:
    """Return deterministic UTF-8 HTML for a redacted verifier/comparison report."""
    comparison = report.get("schema_version") == "insuredatagate.comparison.v1"
    status = report.get("status")
    if comparison:
        base, candidate = report.get("baseline") or {}, report.get("candidate") or {}
        dataset = candidate.get("dataset_id") or base.get("dataset_id")
        version = candidate.get("version")
        review = report.get("review_required") is True
        partial = report.get("changes") is None
        title = "Dataset comparison review"
        state = "partial comparison; numeric change summary unavailable" if partial else ("review required" if review else "no review required")
        summaries = _summary({
            key: f'{base.get("counts", {}).get(key, 0) if base.get("status") == "PASS" else "—"} → '
                 f'{candidate.get("counts", {}).get(key, 0) if candidate.get("status") == "PASS" else "—"}'
            for key in ("sources", "cases", "gold", "train", "validation", "test")
        }, "Baseline → candidate")
        integrity = '<h2>Integrity hashes</h2><table><caption>Manifest and semantic content hashes</caption><thead><tr><th scope="col">Side</th><th scope="col">Manifest SHA-256</th><th scope="col">Content SHA-256</th></tr></thead><tbody>' + "".join(f'<tr><th scope="row">{side}</th><td class="hash">{_value(data.get("manifest_sha256"))}</td><td class="hash">{_value(data.get("content_sha256"))}</td></tr>' for side, data in (("Baseline", base), ("Candidate", candidate))) + '</tbody></table>'
        content_changed = report.get("content_changed")
        version_changed = base.get("version") != candidate.get("version")
        if partial:
            review_reason = "Review required; comparison is partial."
        elif content_changed:
            review_reason = "Review required because dataset content changed."
        elif version_changed:
            review_reason = "Review required because the version changed."
        else:
            review_reason = "No review required; content and version are unchanged."
        if review:
            state = review_reason
        details = '<h2>Changes</h2>' + _changes(report.get("changes"))
        if not partial and not review:
            details = '<h2>Changes</h2><p class="empty">No changes in content or version were recorded.</p>'
    else:
        dataset, version = report.get("dataset_id"), report.get("version")
        title = "Dataset validation review"
        review = False
        state = "gate result; review required before distribution" if status != "PASS" else "gate passed; reviewer decision remains separate"
        summaries = _summary(report.get("counts", {}))
        integrity = '<h2>Manifest integrity</h2><table><caption>Observed manifest hash</caption><thead><tr><th scope="col">Manifest SHA-256</th></tr></thead><tbody><tr><td class="hash">' + _value(report.get("manifest_sha256")) + '</td></tr></tbody></table>'
        details = '<h2>Observed files</h2>' + _files(report.get("files", []))
    notice = '<p class="review">Review required before distribution.</p>' if review else '<p class="meta">' + _e(state) + '</p>'
    if comparison:
        notice = f'<p class="review">{_e(state)}</p>' if review or partial else f'<p class="meta">{_e(state)}</p>'
    identity = '<p><strong>Dataset:</strong> ' + _value(dataset) + '</p>'
    if comparison:
        identity += '<p class="meta">Baseline version: ' + _value(base.get("version")) + ' → Candidate version: ' + _value(version) + '</p>'
    else:
        identity += '<p><strong>Version:</strong> ' + _value(version) + '</p>'
    issues = report.get("issues", [])
    issue_count = sum(type(item) is dict for item in issues) if type(issues) is list else 0
    findings = (f'<a class="issue-link" href="#issues">{issue_count} {"issue" if issue_count == 1 else "issues"} · View findings</a>'
                if issue_count else '<p class="meta">0 validation issues</p>')
    change_summary = ""
    changes = report.get("changes")
    if comparison and type(changes) is dict:
        count = lambda keys: sum(len(changes.get(key, [])) for key in keys if type(changes.get(key, [])) is list)
        change_summary = (f'<p class="meta">Change entries: {count(("cases_added", "sources_added"))} added · '
                          f'{count(("cases_removed", "sources_removed"))} removed · '
                          f'{count(("cases_changed", "gold_changed", "sources_changed"))} modified</p>')
    return ('<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">'
            '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'unsafe-inline\'; base-uri \'none\'; form-action \'none\'">'
            f'<title>{_e(title)} — {_value(dataset)}</title><style>{_STYLE}</style></head><body><a class="skip" href="#main">Skip to review</a><main id="main" tabindex="-1">'
            f'<header><div class="eyebrow">InsureDataGate · Offline review</div><h1>{_e(title)}</h1>{identity}'
            f'<p>Gate status: {_status(status)}</p>{notice}{findings}{change_summary}</header>{summaries}{details}<h2 id="issues" tabindex="-1">Gate findings</h2>{_issues(issues)}{integrity}'
            '<footer>PASS confirms local checks, not release approval. Rights and reviewer identities are unverified declarations. Review dataset identifiers, versions and relative paths before sharing.</footer></main></body></html>')
