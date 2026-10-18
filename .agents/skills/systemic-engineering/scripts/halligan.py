#!/usr/bin/env python3
"""Halligan requirements quality metrics (IRQ, RQ, QF1-QF10, omission, RTBD) for SEF.

Reads 04-requirements/quality.csv, scored by a human or a model with human review, and
04-requirements/requirements.csv. Source: Halligan, Requirements Quality Metrics (CSESAW 1993;
PPA-005330-9, 2014) including the 2014 addendum on omission.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path


DEFAULT_THRESHOLD = 0.85
ELEMENT_FIELDS = (
    "e1_actor", "e2_conditions", "e3_action", "e4_object", "e5_constraints",
    "e6_refinement_source", "e7_refinement_destination",
)
IQF_FIELDS = (
    "iqf1_correctness", "iqf2_completeness", "iqf3_consistency", "iqf4_clarity", "iqf5_non_ambiguity",
    "iqf6_connectivity", "iqf7_singularity", "iqf8_testability", "iqf9_modifiability", "iqf10_feasibility",
)
QUALITY_COLUMNS = ("requirement_id", "scorer", *ELEMENT_FIELDS, *IQF_FIELDS, "omission_ratio", "notes", "rewrite")
TBD_RE = re.compile(r"\bTBD\b|\bto be determined\b", re.I)
# Table 2 of the paper: (upper bound exclusive, label).
BANDS = (
    (0.3, "very poor (0.01-0.3): needs substantial development"),
    (0.7, "fair (0.3-0.7): may suit solicitation, depending on the contract"),
    (0.85, "between fair and SRR (0.7-0.85): not tabulated in the paper"),
    (0.99, "adequate for SRR (0.85-0.99): may proceed to development"),
)
FUNCTIONAL_TYPES = {"functional", "funcional", "function"}
INTERFACE_TYPES = {"interface", "external-interface", "external_interface", "interface-externa", "interface externa"}
SAFETY_TYPES = {"safety", "seguranca", "segurança", "safety-constraint"}
GAP_POINTS = 10.0  # functional and external interface should be within ~10 points (addendum, method 2)
OTHER_RANGE = (5.0, 10.0)  # "other qualities" share for small systems
SMALL_SYSTEM = 100
BAND_CRITICAL = "critical development (0.99+): may proceed to critical development"


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    if not path.exists():
        return [], []
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
        return list(reader.fieldnames or []), rows


def parse_flag(value: str, allow_na: bool) -> int | None:
    text = (value or "").strip().upper()
    if text in {"1", "0"}:
        return int(text)
    if allow_na and text == "NA":
        return None
    raise ValueError(f"invalid value {value!r}; expected {'1, 0 or NA' if allow_na else '1 or 0'}")


def parse_row(line: int, row: dict[str, str]) -> tuple[dict | None, list[str]]:
    """Parse one quality.csv row into typed values; return (row or None, errors)."""
    req_id = (row.get("requirement_id") or "").strip().upper()
    errors: list[str] = []
    if not req_id:
        return None, [f"quality.csv:{line}:missing-requirement_id"]
    if not (row.get("scorer") or "").strip():
        errors.append(f"quality.csv:{line}:{req_id}:missing-scorer")
    elements: dict[str, int | None] = {}
    iqf: dict[str, int] = {}
    for field in ELEMENT_FIELDS:
        try:
            elements[field] = parse_flag(row.get(field, ""), allow_na=True)
        except ValueError as exc:
            errors.append(f"quality.csv:{line}:{req_id}:{field}:{exc}")
    for field in IQF_FIELDS:
        try:
            iqf[field] = parse_flag(row.get(field, ""), allow_na=False)  # type: ignore[assignment]
        except ValueError as exc:
            errors.append(f"quality.csv:{line}:{req_id}:{field}:{exc}")
    omission = 0.0
    try:
        omission = float((row.get("omission_ratio") or "").strip())
        if omission < 0:
            raise ValueError("negative")
    except ValueError:
        errors.append(f"quality.csv:{line}:{req_id}:omission_ratio:expected a number >= 0, got {row.get('omission_ratio')!r}")
    if not errors and all(value is None for value in elements.values()):
        errors.append(f"quality.csv:{line}:{req_id}:no-applicable-elements (IRQ would divide by zero)")
    if errors:
        return None, errors
    return {
        "requirement_id": req_id, "scorer": row["scorer"].strip(), "elements": elements, "iqf": iqf,
        "omission_ratio": omission, "notes": (row.get("notes") or "").strip(), "rewrite": (row.get("rewrite") or "").strip(),
    }, []


def parse_quality(headers: list[str], raw_rows: list[dict[str, str]], requirement_ids: set[str]) -> tuple[list[dict], list[str]]:
    missing = [column for column in QUALITY_COLUMNS if column not in headers]
    if missing:
        return [], [f"quality.csv:schema:missing:{','.join(missing)}"]
    parsed: list[dict] = []
    errors: list[str] = []
    seen: set[str] = set()
    for line, raw in enumerate(raw_rows, start=2):
        row, row_errors = parse_row(line, raw)
        errors.extend(row_errors)
        if row is None:
            continue
        req_id = row["requirement_id"]
        if req_id in seen:
            errors.append(f"quality.csv:{line}:duplicate:{req_id}")
            continue
        seen.add(req_id)
        if req_id not in requirement_ids:
            errors.append(f"quality.csv:{line}:unknown-requirement:{req_id}")
            continue
        parsed.append(row)
    if not raw_rows:
        errors.append("quality.csv:empty:no scored requirements")
    return parsed, errors


def irq(row: dict) -> float:
    """IRQ = elements scored 1 / applicable elements (elements marked NA are excluded)."""
    applicable = [value for value in row["elements"].values() if value is not None]
    if not applicable:
        raise ZeroDivisionError(f"no applicable elements for {row['requirement_id']}")
    return sum(applicable) / len(applicable)


def mean(values: list[float]) -> float:
    if not values:
        raise ZeroDivisionError("mean of an empty list")
    return sum(values) / len(values)


def band_for(rq: float) -> str:
    for upper, label in BANDS:
        if rq < upper:
            return label
    return BAND_CRITICAL


def compute_metrics(rows: list[dict]) -> dict:
    """Set metrics from parsed rows: RQ, QF1-QF10, QF2' (completeness), primary RQ, rewrite candidates."""
    scores = {row["requirement_id"]: irq(row) for row in rows}
    rq = mean(list(scores.values()))
    qf = {f"QF{index}": mean([row["iqf"][field] for row in rows]) for index, field in enumerate(IQF_FIELDS, start=1)}
    omissions = [row["omission_ratio"] for row in rows]
    completeness = qf["QF2"] - mean(omissions)
    # Addendum: missing requirements enter the average at quality zero.
    rq_primary = sum(scores.values()) / (len(rows) + sum(omissions))
    candidates = [
        {
            "requirement_id": row["requirement_id"], "irq": round(scores[row["requirement_id"]], 4),
            "failed_elements": [name for name, value in row["elements"].items() if value == 0],
            "failed_factors": [name for name, value in row["iqf"].items() if value == 0],
            "rewrite": row["rewrite"],
        }
        for row in rows if scores[row["requirement_id"]] < 1
    ]
    return {
        "requirements_scored": len(rows), "irq": {key: round(value, 4) for key, value in scores.items()},
        "rq": round(rq, 4), "rq_primary": round(rq_primary, 4), "band": band_for(rq),
        "qf": {key: round(value, 4) for key, value in qf.items()},
        "completeness_qf2_prime": round(completeness, 4), "omission_total": round(sum(omissions), 4),
        "rewrite_candidates": candidates,
    }


NO_BLOCKER = {"", "-", "none", "n/a", "na", "not-applicable"}


def is_tbd(row: dict[str, str]) -> bool:
    """RTBD rule: a requirement is TBD when its statement says TBD, its status is blocked, or `blocked_by` is filled."""
    blocked_by = (row.get("blocked_by") or "").strip().lower()
    return bool(TBD_RE.search(row.get("statement") or "")) or (row.get("status") or "").strip().lower() == "blocked" or blocked_by not in NO_BLOCKER


def rtbd_percent(requirement_rows: list[dict[str, str]]) -> float:
    """Percentage of requirements that are still TBD (see is_tbd)."""
    if not requirement_rows:
        return 0.0
    return round(100.0 * sum(1 for row in requirement_rows if is_tbd(row)) / len(requirement_rows), 2)


def type_group(kind: str) -> str:
    value = (kind or "").strip().lower()
    if value in FUNCTIONAL_TYPES:
        return "functional"
    if value in INTERFACE_TYPES:
        return "interface"
    return "safety" if value in SAFETY_TYPES else "other"


def _share(count: int, total: int) -> float:
    return round(100.0 * count / total, 2) if total else 0.0


def type_mix(requirement_rows: list[dict[str, str]]) -> dict:
    """Count and percentage per value of the `type` column, plus the functional/interface/safety/other groups."""
    total = len(requirement_rows)
    counts: dict[str, int] = {}
    groups = {"functional": 0, "interface": 0, "safety": 0, "other": 0}
    for row in requirement_rows:
        kind = (row.get("type") or "").strip().lower() or "unset"
        counts[kind] = counts.get(kind, 0) + 1
        groups[type_group(kind)] += 1
    return {
        "total": total,
        "by_type": {kind: {"count": n, "percent": _share(n, total)} for kind, n in sorted(counts.items())},
        "groups": {name: {"count": n, "percent": _share(n, total)} for name, n in groups.items()},
    }


def completeness_hints(mix: dict) -> list[dict]:
    """Hints (never errors) from the addendum, method 2. Skipped while every requirement is STPA-derived (safety)."""
    groups, total = mix["groups"], mix["total"]
    if total == 0 or total == groups["safety"]["count"]:
        return []
    functional, interface, other = (groups[name]["percent"] for name in ("functional", "interface", "other"))
    hints: list[dict] = []
    if abs(functional - interface) > GAP_POINTS:
        direction = "interface exceeds functional" if interface > functional else "functional far exceeds interface"
        hints.append({
            "code": "functional-interface-gap",
            "message": f"{direction}: functional {functional}% vs interface {interface}% (expected within ~{GAP_POINTS:g} points, functional slightly larger)",
            "observed": {"functional": functional, "interface": interface},
        })
    if total <= SMALL_SYSTEM and not OTHER_RANGE[0] <= other <= OTHER_RANGE[1]:
        low = other < OTHER_RANGE[0]
        hints.append({
            "code": "other-qualities-low" if low else "other-qualities-high",
            "message": f"other qualities are {other}% (expected {OTHER_RANGE[0]:g}-{OTHER_RANGE[1]:g}% in systems up to {SMALL_SYSTEM} requirements)",
            "observed": {"other": other},
        })
    return hints


def completeness_info(requirement_rows: list[dict[str, str]]) -> dict:
    mix = type_mix(requirement_rows)
    return {"type_mix": mix, "completeness_hints": completeness_hints(mix)}


def build_report(project: Path, threshold: float = DEFAULT_THRESHOLD) -> dict:
    directory = project.resolve() / ".systemic-engineering" / "04-requirements"
    _, requirement_rows = read_csv(directory / "requirements.csv")
    requirement_ids = {(row.get("requirement_id") or "").strip().upper() for row in requirement_rows} - {""}
    quality_path = directory / "quality.csv"
    if not quality_path.exists():
        return {"ok": False, "threshold": threshold, "errors": ["quality-missing:quality.csv not found"],
                "missing_from_quality": sorted(requirement_ids), "rtbd_percent": rtbd_percent(requirement_rows),
                **completeness_info(requirement_rows)}
    headers, raw_rows = read_csv(quality_path)
    parsed, errors = parse_quality(headers, raw_rows, requirement_ids)
    base = {"threshold": threshold, "rtbd_percent": rtbd_percent(requirement_rows), **completeness_info(requirement_rows)}
    if errors:
        return {**base, "ok": False, "errors": errors, "missing_from_quality": sorted(requirement_ids - {r["requirement_id"] for r in parsed})}
    metrics = compute_metrics(parsed)
    missing = sorted(requirement_ids - set(metrics["irq"]))
    return {
        **base, **metrics, "ok": True, "errors": [], "missing_from_quality": missing,
        "meets_threshold": metrics["rq"] >= threshold,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", help="project directory containing .systemic-engineering/")
    parser.add_argument("--threshold", type=float, default=DEFAULT_THRESHOLD, help="minimum RQ (default 0.85)")
    parser.add_argument("--json", action="store_true", help="print machine-readable JSON")
    args = parser.parse_args(argv)
    report = build_report(Path(args.project), args.threshold)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(render_text(report))
    if not report["ok"]:
        return 1
    return 0 if report["meets_threshold"] else 2


def render_text(report: dict) -> str:
    if not report["ok"]:
        return "\n".join(["Quality report invalid:", *[f"  - {error}" for error in report["errors"]]])
    lines = [
        f"RQ = {report['rq']} (threshold {report['threshold']}; {'meets' if report['meets_threshold'] else 'BELOW'})",
        f"RQ primary (omission counted at quality zero) = {report['rq_primary']}",
        f"Band: {report['band']}",
        "QF: " + ", ".join(f"{key}={value}" for key, value in report["qf"].items()),
        f"Completeness QF2' = {report['completeness_qf2_prime']}",
        f"RTBD = {report['rtbd_percent']}%",
        *[f"Hint [{h['code']}]: {h['message']}" for h in report.get("completeness_hints", [])],
    ]
    if report["rewrite_candidates"]:
        lines.append("Rewrite candidates (IRQ < 1):")
        lines.extend(f"  - {c['requirement_id']} IRQ={c['irq']} elements={c['failed_elements']} factors={c['failed_factors']}" for c in report["rewrite_candidates"])
    if report["missing_from_quality"]:
        lines.append("Requirements without a quality row: " + ", ".join(report["missing_from_quality"]))
    return "\n".join(lines)


if __name__ == "__main__":
    sys.exit(main())
