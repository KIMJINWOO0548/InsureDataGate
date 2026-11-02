"""Opt-in, finite-grammar annotation support review over a checked snapshot.

Rules sources are declared context, never evidence of issuer-document truth.
This module returns hashes and original code-point spans, never claim values.
"""

from datetime import date
import hashlib
from pathlib import Path
import re

from .validator import read_snapshot, strict_json, verify

PROFILE = "disclosure-facts.v1"
FIELDS = ("period_start", "period_end", "period", "currency", "amount_unit", "scope", "revenue")
UNIT = r"(?:thousands?|millions?|billions?)"
DECIMAL = re.compile(r"[+-]?[0-9]+(?:\.[0-9]+)?\Z")
# A terminal period is punctuation only before whitespace/end; decimal dots stay
# inside the clause and must pass the complete-value grammar below.
CLAUSES = re.compile(r"(?:\A|(?<=[.;\n]))[ \t]*([^\n;]*?)(?=;|\n|\.(?=\s|\Z)|\Z)")
LABELS = (
    ("period", r"(?:Reporting\s+period|Period)\b"),
    ("scope", r"Basis\b"),
    ("currency", r"Currency\b"),
    ("amount_unit", r"Amount\s+unit\b"),
    ("amounts", r"Amounts\s+in\b"),
    ("absence", r"The\s+amount\s+unit\s+is\s+absent\b"),
    ("revenue", r"Revenue\b"),
    ("target", r"Extract\s+only\s+the\b"),
)


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _normalized(text: str) -> str:
    return " ".join(text.split())


def _year(value: str) -> bool:
    return bool(re.fullmatch(r"[0-9]{4}", value)) and value != "0000"


def _decimal(value: str) -> bool:
    return len(value) <= 64 and DECIMAL.fullmatch(value) is not None


def _period(value: str):
    iso = re.fullmatch(r"Reporting period: ([0-9]{4}-[0-9]{2}-[0-9]{2}) to ([0-9]{4}-[0-9]{2}-[0-9]{2})", value, re.I)
    if iso:
        start, end = iso.groups()
        try:
            if date.fromisoformat(start) <= date.fromisoformat(end):
                return {"period_start": start, "period_end": end}
        except ValueError:
            pass
        return None
    labelled = re.fullmatch(r"(?:Reporting period|Period): ([0-9]{4}) (annual|Q[1-4])", value, re.I)
    if labelled and _year(labelled[1]):
        return {"period": labelled[1] if labelled[2].lower() == "annual" else labelled[1] + " " + labelled[2].upper()}
    return None


def _parse(text: str) -> dict:
    declarations = {kind: [] for kind, _ in LABELS}
    for match in CLAUSES.finditer(text):
        raw = match[1]
        if not raw.strip():
            continue
        start = match.start(1)
        end = match.end(1) - (len(raw) - len(raw.rstrip()))
        value = _normalized(raw)
        for kind, pattern in LABELS:
            if re.match(pattern, value, re.I):
                parsed = None
                if kind == "period":
                    parsed = _period(value)
                elif kind == "scope":
                    found = re.fullmatch(r"Basis: (consolidated|separate)", value, re.I)
                    parsed = found[1].lower() if found else None
                elif kind == "currency":
                    # The label is case-insensitive; CUR remains uppercase ASCII.
                    found = re.fullmatch(r"(?i:Currency): ([A-Z]{3})", value)
                    parsed = found[1] if found else None
                elif kind == "amount_unit":
                    found = re.fullmatch(r"(?i:Amount unit): ((?:[A-Z]{3} )?" + UNIT + ")", value)
                    parsed = found[1] if found else None
                elif kind == "amounts":
                    found = re.fullmatch(r"(?i:Amounts in) ([A-Z]{3}) (" + UNIT + ")", value)
                    parsed = found.groups() if found else None
                elif kind == "absence":
                    parsed = True if re.fullmatch(r"The amount unit is absent", value, re.I) else None
                elif kind == "revenue":
                    found = re.fullmatch(r"Revenue(?: for ([0-9]{4}))?: (.+)", value, re.I)
                    if found and (found[1] is None or _year(found[1])) and _decimal(found[2]):
                        parsed = (found[1], found[2])
                elif kind == "target":
                    found = re.fullmatch(r"Extract only the ([0-9]{4}) revenue(?: with\b.*)?", value, re.I)
                    parsed = found[1] if found and _year(found[1]) else None
                declarations[kind].append({"value": parsed, "start": start, "end": end})
                break
    # Discover declarations outside accepted clause starts too. They cannot
    # supply facts, but must not hide a second relevant (malformed) declaration.
    embedded = (
        ("period", r"(?:Reporting\s+period|Period)\s*:"),
        ("scope", r"Basis\s*:"),
        ("currency", r"Currency\s*:"),
        ("amount_unit", r"Amount\s+unit\s*:"),
        ("amounts", r"Amounts\s+in\b"),
        ("absence", r"The\s+amount\s+unit\s+is\s+absent\b"),
        ("revenue", r"Revenue(?:\s+for\s+[^:;\n]+)?\s*:"),
        ("target", r"Extract\s+only\s+the\b"),
    )
    for kind, pattern in embedded:
        for match in re.finditer(r"(?<!\w)" + pattern, text, re.I):
            if any(item["start"] == match.start() for item in declarations[kind]):
                continue
            boundary = re.search(r";|\n|\.(?=\s|\Z)|\Z", text[match.end():])
            end = match.end() + boundary.start()
            declarations[kind].append({"value": None, "start": match.start(), "end": end})
        declarations[kind].sort(key=lambda item: item["start"])
    return declarations


def _evidence(text, kind, declarations):
    return [{"kind": kind, "field": "input", "start": item["start"], "end": item["end"],
             "sha256": _sha(text[item["start"]:item["end"]])} for item in declarations]


def _unique(text, kind, declarations):
    evidence = _evidence(text, kind, declarations)
    if not declarations:
        return None, "MISSING_CONTEXT", evidence
    if len(declarations) != 1:
        return None, "AMBIGUOUS_CONTEXT", evidence
    if declarations[0]["value"] is None:
        return None, "UNSUPPORTED_CONTEXT", evidence
    return declarations[0]["value"], None, evidence


def _context(text, declarations):
    facts = {}
    facts["scope"] = _unique(text, "scope", declarations["scope"])
    currency = declarations["currency"] + [dict(item, value=item["value"][0] if item["value"] else None)
                                              for item in declarations["amounts"]]
    facts["currency"] = _unique(text, "currency", currency)
    units = declarations["amount_unit"] + [dict(item, value=item["value"][1] if item["value"] else None)
                                            for item in declarations["amounts"]]
    # A currency-prefixed whole unit label is retained as written, while its
    # explicit currency must agree with any independently stated currency.
    prefixes = [item for item in declarations["amount_unit"]
                if item["value"] and re.match(r"[A-Z]{3} ", item["value"])]
    if not facts["currency"][1] and any(item["value"][:3] != facts["currency"][0] for item in prefixes):
        facts["currency"] = (None, "AMBIGUOUS_CONTEXT",
                             facts["currency"][2] + _evidence(text, "currency", prefixes))
    absence = declarations["absence"]
    if absence and units:
        facts["amount_unit"] = (None, "AMBIGUOUS_CONTEXT", _evidence(text, "amount_unit", units + absence))
    elif absence:
        _, reason, evidence = _unique(text, "amount_unit", absence)
        facts["amount_unit"] = (None, reason, evidence)
    else:
        facts["amount_unit"] = _unique(text, "amount_unit", units)
    period, reason, evidence = _unique(text, "period", declarations["period"])
    for field in ("period_start", "period_end", "period"):
        facts[field] = (period.get(field) if period else None,
                        reason or (None if field in period else "UNSUPPORTED_CONTEXT"), evidence)
    return facts


def _binding(text, declarations, facts):
    revenues = declarations["revenue"]
    targets = declarations["target"]
    evidence = _evidence(text, "revenue", revenues)
    evidence += _evidence(text, "target", targets)
    if not revenues:
        return None, None, "MISSING_CONTEXT", evidence
    if any(item["value"] is None for item in revenues):
        return None, None, "UNSUPPORTED_CONTEXT", evidence
    labelled = [item for item in revenues if item["value"][0] is not None]
    selected = None
    if labelled:
        years = [item["value"][0] for item in labelled]
        if len(labelled) != len(revenues) or len(set(years)) != len(years):
            return None, None, "AMBIGUOUS_CONTEXT", evidence
        if targets:
            target, reason, _ = _unique(text, "target", targets)
            if reason or target not in years:
                return None, None, reason or "MISSING_CONTEXT", evidence
            selected = next(item for item in labelled if item["value"][0] == target)
        elif len(labelled) == 1:
            selected = labelled[0]
        else:
            return None, None, "MISSING_CONTEXT", evidence
        year = selected["value"][0]
        if declarations["period"] and (facts["period"][1] or facts["period"][0] != year):
            return None, None, "AMBIGUOUS_CONTEXT", evidence + facts["period"][2]
        period_evidence = _evidence(text, "revenue", [selected]) + _evidence(text, "target", targets)
        period_evidence += facts["period"][2] if declarations["period"] else []
        facts["period"] = (year, None, period_evidence)
    else:
        if len(revenues) != 1:
            return None, None, "AMBIGUOUS_CONTEXT", evidence
        selected = revenues[0]
        if targets:
            target, reason, _ = _unique(text, "target", targets)
            period = facts["period"][0]
            if reason or period != target:
                return None, None, reason or "AMBIGUOUS_CONTEXT", evidence
    # Only the selected revenue is evidence of an observed amount. Earlier-year
    # alternatives are parsed for ambiguity, never used to select by expected.
    evidence = _evidence(text, "revenue", [selected]) + _evidence(text, "target", targets)
    return selected["value"][1], selected["value"][0], None, evidence


def _facts(text):
    declarations = _parse(text)
    facts = _context(text, declarations)
    amount, year, binding_reason, evidence = _binding(text, declarations, facts)
    # A period claim in a multi/labelled revenue case uses the same input binding.
    if any(item["value"] and item["value"][0] for item in declarations["revenue"]):
        if binding_reason:
            facts["period"] = (None, binding_reason, evidence)
    dependencies = ("currency", "amount_unit", "scope")
    reason = binding_reason
    if year is None:
        period_fields = ("period_start", "period_end") if not facts["period_start"][1] else ("period",)
        for field in period_fields:
            reason = reason or facts[field][1]
            evidence += facts[field][2]
    else:
        evidence += facts["period"][2]
    for field in dependencies:
        reason = reason or facts[field][1]
        evidence += facts[field][2]
    facts["revenue"] = (amount, reason, evidence)
    return facts


def _claim_supported(field, value):
    if value is None:
        return field == "amount_unit"
    if type(value) is not str:
        return False
    value = _normalized(value)
    if field == "revenue":
        return _decimal(value)
    if field in ("period_start", "period_end"):
        try:
            return bool(re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value)) and date.fromisoformat(value) is not None
        except ValueError:
            return False
    if field == "period":
        return bool(re.fullmatch(r"[0-9]{4}(?: Q[1-4])?", value)) and _year(value[:4])
    if field == "currency":
        return re.fullmatch(r"[A-Z]{3}", value) is not None
    if field == "amount_unit":
        return re.fullmatch(r"(?:[A-Z]{3} )?" + UNIT, value) is not None
    return value in ("consolidated", "separate")


def _status(statuses):
    if "CONFLICT" in statuses:
        return "CONFLICT"
    if not statuses or "ABSTAIN" in statuses:
        return "ABSTAIN"
    return "SUPPORTED"


def _case(case, expected, index):
    reasons = []
    try:
        claims = strict_json(expected.encode("utf-8"))
    except (ValueError, UnicodeError):
        claims = None
    if type(claims) is not dict or not claims:
        claims = {}
        reasons.append("INVALID_CLAIMS")
    if set(claims) - set(FIELDS):
        reasons.append("UNSUPPORTED_CLAIM")
    facts = _facts(case["input"])
    fields = []
    for name in FIELDS:
        if name not in claims:
            continue
        value, reason, evidence = facts[name]
        if not _claim_supported(name, claims[name]):
            reason = "UNSUPPORTED_CLAIM"
        if reason:
            status = "ABSTAIN"
        else:
            claim = _normalized(claims[name]) if isinstance(claims[name], str) else None
            status = "SUPPORTED" if claim == value else "CONFLICT"
            reason = "MATCH" if status == "SUPPORTED" else "MISMATCH"
        # Dependency spans may be shared; each kind/start/end appears once.
        unique = {(item["start"], item["end"], item["kind"]): item for item in evidence}
        fields.append({"field": name, "status": status, "reason": reason,
                       "evidence": [unique[key] for key in sorted(unique)]})
    status = _status([item["status"] for item in fields] + (["ABSTAIN"] if reasons else []))
    return {"case_id": case["case_id"], "record_index": index,
            "source_ids": sorted(case["source_ids"]), "input_sha256": _sha(case["input"]),
            "status": status, "reasons": reasons, "fields": fields}


def review_facts(manifest_path: Path) -> dict:
    """Review only supported asserted facts after verify and checked reread.

    This profile is opt-in and does not change generic validation/export gates.
    Source IDs name declared rules context, not authenticated document evidence.
    """
    gate = verify(manifest_path)
    result = {"schema_version": "insuredatagate.fact-review.v1", "profile": PROFILE,
              "status": "UNAVAILABLE", "manifest_sha256": None,
              "cases_sha256": None, "gold_sha256": None, "cases": [], "issues": []}
    if gate["status"] != "PASS":
        result["issues"] = ["VALIDATION_FAILED"]
        return result
    try:
        snapshot = read_snapshot(manifest_path, gate)
    except (ValueError, OSError):
        result["issues"] = ["SNAPSHOT_UNAVAILABLE"]
        return result
    manifest = snapshot["manifest"]
    result.update(manifest_sha256=gate["manifest_sha256"], cases_sha256=manifest["cases"]["sha256"],
                  gold_sha256=manifest["gold"]["sha256"])
    gold = {row["case_id"]: row["expected"] for row in snapshot["gold"]}
    result["cases"] = [_case(case, gold[case["case_id"]], index)
                       for index, case in enumerate(snapshot["cases"], 1)]
    result["status"] = _status([case["status"] for case in result["cases"]])
    return result
