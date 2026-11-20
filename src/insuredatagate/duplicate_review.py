"""Redacted duplicate diagnostics for a verified synthetic dataset."""

from itertools import combinations, product
from pathlib import Path
from typing import Literal, TypedDict

from . import validator

SCHEMA_VERSION = "insuredatagate.duplicate-review.v1"
MAX_PAIRS = 50_000
MAX_CHARACTERS = 200_000
MAX_MATCHES = 1_000
MIN_LENGTH = 12


class Location(TypedDict):
    case_id: str
    split: str
    line: int


class ExactGroup(TypedDict):
    split: str
    members: list[Location]


class Score(TypedDict):
    numerator: int
    denominator: int


class NearPair(TypedDict):
    left: Location
    right: Location
    score: Score


class Counts(TypedDict):
    case_rows: int | None
    short_rows: int | None
    exact_groups: int | None
    exact_rows: int | None
    eligible_cross_pairs: int | None
    compared_cross_pairs: int | None
    near_pairs: int | None


class DuplicateReview(TypedDict):
    schema_version: str
    status: Literal["COMPLETE", "EXACT_ONLY", "UNAVAILABLE"]
    reason: Literal["LIMIT_EXCEEDED", "GATE_BLOCKED", "SNAPSHOT_CHANGED"] | None
    counts: Counts
    exact_groups: list[ExactGroup]
    near_pairs: list[NearPair]


def review_duplicates(manifest_path: Path) -> DuplicateReview:
    gate = validator.verify(manifest_path)
    reason: Literal["GATE_BLOCKED", "SNAPSHOT_CHANGED"] = "GATE_BLOCKED"
    if gate["status"] == "PASS":
        try:
            snapshot = validator.read_snapshot(manifest_path, gate)
        except (ValueError, OSError):
            reason = "SNAPSHOT_CHANGED"
        else:
            return _scan_checked_cases(snapshot["cases"])
    return {
        "schema_version": SCHEMA_VERSION, "status": "UNAVAILABLE", "reason": reason,
        "counts": dict.fromkeys(Counts.__annotations__), "exact_groups": [], "near_pairs": [],
    }


def _scan_checked_cases(cases: list[dict]) -> DuplicateReview:
    grouped: dict[str, dict[str, list[Location]]] = {split: {} for split in validator.SPLITS}
    eligible: dict[str, list[tuple[Location, str]]] = {split: [] for split in validator.SPLITS}
    for line, row in enumerate(cases, 1):
        split = row["split"]
        normalized = validator._normalize_input(row["input"])
        location = Location(case_id=row["case_id"], split=split, line=line)
        grouped[split].setdefault(normalized, []).append(location)
        if len(normalized) >= MIN_LENGTH:
            eligible[split].append((location, normalized))

    exact_groups = [
        ExactGroup(split=split, members=members)
        for split, groups in grouped.items()
        for members in groups.values()
        if len(members) > 1
    ]
    cross_splits = list(combinations(validator.SPLITS, 2))
    pair_count = sum(len(eligible[left]) * len(eligible[right]) for left, right in cross_splits)
    eligible_length = sum(len(value) for rows in eligible.values() for _, value in rows)
    report = DuplicateReview(
        schema_version=SCHEMA_VERSION, status="EXACT_ONLY", reason="LIMIT_EXCEEDED",
        counts=Counts(
            case_rows=len(cases), short_rows=len(cases) - sum(map(len, eligible.values())),
            exact_groups=len(exact_groups), exact_rows=sum(len(group["members"]) for group in exact_groups),
            eligible_cross_pairs=pair_count, compared_cross_pairs=None, near_pairs=None,
        ),
        exact_groups=exact_groups, near_pairs=[],
    )
    if pair_count > MAX_PAIRS or eligible_length > MAX_CHARACTERS:
        return report

    grams = {
        split: [(location, {value[index:index + 3] for index in range(len(value) - 2)})
                for location, value in rows]
        for split, rows in eligible.items()
    }
    near_pairs: list[NearPair] = []
    for left_split, right_split in cross_splits:
        for (left, a), (right, b) in product(grams[left_split], grams[right_split]):
            numerator, denominator = 2 * len(a & b), len(a) + len(b)
            if 5 * numerator >= 4 * denominator:
                if len(near_pairs) == MAX_MATCHES:
                    return report
                near_pairs.append(NearPair(left=left, right=right, score=Score(
                    numerator=numerator, denominator=denominator,
                )))

    report.update(status="COMPLETE", reason=None, near_pairs=near_pairs)
    report["counts"].update(compared_cross_pairs=pair_count, near_pairs=len(near_pairs))
    return report
