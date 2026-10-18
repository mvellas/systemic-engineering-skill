#!/usr/bin/env python3
"""Validate SEF requirement schemas, ID references, and trace semantics."""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from collections import defaultdict, deque
from pathlib import Path


ID_RE = re.compile(r"\b(?:SRC|STK|VAL|OBJ|SSM|LOSS|HAZ|SC|CA|UCA|CS|REQ|SPEC|TST|SPR|TSK|EVD|DEC)-[A-Z0-9][A-Z0-9._-]*\b", re.I)
RANGE_RE = re.compile(r"\b(?:REQ|SPEC|TST|SPR|TSK|EVD)-[A-Z0-9._-]*\.\.[A-Z0-9._-]+\b", re.I)
REQUIRED_REQUIREMENT_FIELDS = (
    "requirement_id", "level", "statement", "type", "source_ids", "rationale", "allocation",
    "verification_method", "verification_criterion", "validation_link", "priority", "risk", "owner", "status",
    "constraint_class", "waiver_policy", "threshold_source",
)  # blocked_by and decision_ids may be empty, equivalent to not-applicable
TEMPLATE_FIELDS = ("actor", "action", "object")  # Halligan template parts required once approved, if the columns exist
PHASE_ORDER = ("intake", "vft", "ssm", "reconcile", "stpa", "requirements", "planning", "execution", "closure")
UPSTREAM_PREFIXES = ("SRC-", "STK-", "VAL-", "OBJ-", "SSM-", "LOSS-", "HAZ-", "SC-", "CA-", "UCA-", "CS-")
ANCHOR_PREFIXES = ("SRC-", "STK-", "VAL-", "OBJ-")
VERIFICATION_RELATIONS = {"verified_by", "verified-by", "verification", "tested_by", "tested-by"}
NON_COMPENSABLE = {"non-compensable", "noncompensable", "hard-constraint"}
NO_WAIVER = {"none", "prohibited", "not-allowed"}
NA_VALUES = {"n/a", "na", "not-applicable", "none"}
DECISION_STATUSES = {"pending", "approved", "rejected", "superseded"}


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def split_ids(value: str) -> list[str]:
    return [item.upper() for item in ID_RE.findall(value or "")]


def ids_outside_trace(root: Path, trace_path: Path, *also_excluded: Path) -> set[str]:
    found: set[str] = set()
    for path in root.rglob("*"):
        if not path.is_file() or path == trace_path or path in also_excluded or path.name == "state.json" or "gates" in path.parts:
            continue
        if path.suffix.lower() not in {".md", ".csv", ".json", ".yaml", ".yml", ".txt"}:
            continue
        try:
            found.update(match.upper() for match in ID_RE.findall(path.read_text(encoding="utf-8")))
        except UnicodeDecodeError:
            continue
    return found


def range_shorthands(root: Path) -> list[str]:
    found: list[str] = []
    for path in root.rglob("*"):
        if not path.is_file() or path.name == "state.json" or "gates" in path.parts:
            continue
        if path.suffix.lower() not in {".md", ".csv", ".json", ".yaml", ".yml", ".txt"}:
            continue
        try:
            for match in RANGE_RE.findall(path.read_text(encoding="utf-8")):
                found.append(f"range-shorthand:{path.relative_to(root).as_posix()}:{match.upper()}")
        except UnicodeDecodeError:
            continue
    return found


def has_upstream_path(req_id: str, reverse: dict[str, set[str]]) -> bool:
    queue = deque([req_id])
    seen = {req_id}
    while queue:
        current = queue.popleft()
        for parent in reverse.get(current, set()):
            if parent.startswith(ANCHOR_PREFIXES):
                return True
            if parent.startswith(UPSTREAM_PREFIXES) and parent not in seen:
                seen.add(parent)
                queue.append(parent)
    return False


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project")
    args = parser.parse_args()
    project = Path(args.project).resolve()
    root = project / ".systemic-engineering"
    req_path = root / "04-requirements" / "requirements.csv"
    trace_path = root / "04-requirements" / "traceability.csv"
    decision_path = root / "04-requirements" / "decisions.csv"
    authority_path = root / "00-intake" / "authorities.csv"
    state_path = root / "state.json"
    errors: list[str] = []

    authorities = read_csv(authority_path)
    authority_map = {(row.get("authority_id") or "").strip(): row for row in authorities}
    decisions = read_csv(decision_path)
    decision_map: dict[str, dict[str, str]] = {}
    for line, row in enumerate(decisions, start=2):
        decision_id = (row.get("decision_id") or "").upper()
        missing = [field for field in ("decision_id", "title", "status", "owner", "affected_ids", "rationale") if not (row.get(field) or "").strip()]
        if missing:
            errors.append(f"decisions.csv:{line}:missing:{','.join(missing)}")
        if decision_id in decision_map:
            errors.append(f"decisions.csv:{line}:duplicate:{decision_id}")
        if decision_id and not decision_id.startswith("DEC-"):
            errors.append(f"decisions.csv:{line}:invalid-id:{decision_id}")
        status = (row.get("status") or "").strip().lower()
        if status not in DECISION_STATUSES:
            errors.append(f"decisions.csv:{line}:invalid-status:{status or 'unset'}")
        if status == "approved":
            authority_id = (row.get("authority_id") or "").strip()
            evidence = (row.get("evidence") or "").strip()
            authority = authority_map.get(authority_id)
            if not authority_id or not evidence:
                errors.append(f"decisions.csv:{line}:approved-without-authority-evidence:{decision_id}")
            elif not authority:
                errors.append(f"decisions.csv:{line}:unregistered-authority:{authority_id}")
            elif (authority.get("status") or "").strip().lower() != "active":
                errors.append(f"decisions.csv:{line}:inactive-authority:{authority_id}")
            elif evidence != (authority.get("evidence") or "").strip():
                errors.append(f"decisions.csv:{line}:authority-evidence-mismatch:{authority_id}")
            else:
                scopes = {item for item in re.split(r"[,;\s]+", (authority.get("scope") or "").strip().lower()) if item}
                if not ({"all", "*", "decisions", "requirements"} & scopes):
                    errors.append(f"decisions.csv:{line}:authority-scope-mismatch:{authority_id}")
        decision_map[decision_id] = row

    requirements = read_csv(req_path)
    seen: set[str] = set()
    rows_by_id: dict[str, dict[str, str]] = {}
    for line, row in enumerate(requirements, start=2):
        missing = [field for field in REQUIRED_REQUIREMENT_FIELDS if not (row.get(field) or "").strip()]
        if missing:
            errors.append(f"requirements.csv:{line}:missing:{','.join(missing)}")
        req_id = (row.get("requirement_id") or "").upper()
        if req_id and not req_id.startswith("REQ-"):
            errors.append(f"requirements.csv:{line}:invalid-id:{req_id}")
        if req_id in seen:
            errors.append(f"requirements.csv:{line}:duplicate:{req_id}")
        seen.add(req_id)
        rows_by_id[req_id] = row
        if (row.get("constraint_class") or "").strip().lower() in NON_COMPENSABLE:
            waiver = (row.get("waiver_policy") or "").strip().lower()
            if waiver not in NO_WAIVER:
                errors.append(f"requirements.csv:{line}:non-compensable-waiver:{req_id}")
        threshold_source = (row.get("threshold_source") or "").strip()
        if threshold_source and threshold_source.lower() not in NA_VALUES and not split_ids(threshold_source):
            errors.append(f"requirements.csv:{line}:threshold-source-not-id:{req_id}")
        referenced_decisions = {
            item for field in ("decision_ids", "threshold_source", "blocked_by")
            for item in split_ids(row.get(field) or "") if item.startswith("DEC-")
        }
        for decision_id in sorted(referenced_decisions):
            if decision_id not in decision_map:
                errors.append(f"requirements.csv:{line}:unregistered-decision:{decision_id}")
        status = (row.get("status") or "").strip().lower()
        blockers = [item for item in split_ids(row.get("blocked_by") or "") if item.startswith("DEC-")]
        if status == "blocked" and not blockers:
            errors.append(f"requirements.csv:{line}:blocked-without-decision:{req_id}")
        if status in {"approved", "baselined", "accepted"}:
            for decision_id in sorted(referenced_decisions):
                if (decision_map.get(decision_id, {}).get("status") or "").strip().lower() != "approved":
                    errors.append(f"requirements.csv:{line}:unapproved-decision:{decision_id}")
            for decision_id in blockers:
                if (decision_map.get(decision_id, {}).get("status") or "").strip().lower() != "approved":
                    errors.append(f"requirements.csv:{line}:unresolved-blocker:{decision_id}")
            for decision_id in (item for item in split_ids(threshold_source) if item.startswith("DEC-")):
                if (decision_map.get(decision_id, {}).get("status") or "").strip().lower() != "approved":
                    errors.append(f"requirements.csv:{line}:unapproved-threshold:{decision_id}")

    known = ids_outside_trace(root, trace_path)
    defined_elsewhere = ids_outside_trace(root, trace_path, req_path)  # origin must be defined outside requirements.csv itself
    errors.extend(range_shorthands(root))
    for line, row in enumerate(decisions, start=2):
        for affected_id in split_ids(row.get("affected_ids") or ""):
            if affected_id not in known:
                errors.append(f"decisions.csv:{line}:undefined-affected-id:{affected_id}")
    traces = read_csv(trace_path)
    inbound: dict[str, set[str]] = defaultdict(set)
    outbound: dict[str, set[str]] = defaultdict(set)
    relations: dict[tuple[str, str], set[str]] = defaultdict(set)
    for line, row in enumerate(traces, start=2):
        source = (row.get("from_id") or "").upper()
        target = (row.get("to_id") or "").upper()
        relation = (row.get("relationship") or "").strip().lower()
        if not source or not target or not relation:
            errors.append(f"traceability.csv:{line}:incomplete-link")
            continue
        if source not in known:
            errors.append(f"traceability.csv:{line}:undefined-from:{source}")
        if target not in known:
            errors.append(f"traceability.csv:{line}:undefined-to:{target}")
        outbound[source].add(target)
        inbound[target].add(source)
        relations[(source, target)].add(relation)

    phase = "requirements"
    if state_path.exists():
        phase = json.loads(state_path.read_text(encoding="utf-8")).get("phase", phase)
    notes: list[str] = []
    if not requirements:
        if phase in PHASE_ORDER and PHASE_ORDER.index(phase) < PHASE_ORDER.index("requirements"):
            notes.append("no requirements yet; chain not applicable before the requirements phase")
        elif phase == "requirements":
            notes.append("requirements phase in progress; no requirement rows yet")
        else:
            errors.append("no-requirements-after-requirements-phase")
    require_tests = phase in {"planning", "execution", "closure"}
    for req_id, row in rows_by_id.items():
        if not req_id:
            continue
        for field in ("source_ids", "validation_link", "parent_requirement_id", "decision_ids", "threshold_source", "blocked_by"):
            for referenced in split_ids(row.get(field) or ""):
                if referenced not in known:
                    errors.append(f"requirements.csv:{req_id}:undefined-{field}:{referenced}")
        if "origin" in row:
            origin_ids = split_ids(row.get("origin") or "")
            if not origin_ids:
                errors.append(f"requirements.csv:{req_id}:missing-origin")
            for referenced in origin_ids:
                if referenced not in defined_elsewhere:
                    errors.append(f"requirements.csv:{req_id}:undefined-origin:{referenced}")
        if (row.get("status") or "").strip().lower() in {"approved", "baselined", "accepted"}:
            empty = [field for field in TEMPLATE_FIELDS if field in row and not (row.get(field) or "").strip()]
            if empty:
                errors.append(f"requirements.csv:{req_id}:incomplete-template:{','.join(empty)}")
        if not has_upstream_path(req_id, inbound):
            errors.append(f"untraced-requirement-origin:{req_id}")
        tests = [target for target in outbound.get(req_id, set()) if target.startswith("TST-") and relations[(req_id, target)] & VERIFICATION_RELATIONS]
        if require_tests and not tests:
            errors.append(f"untraced-requirement-verification:{req_id}")

    result = {
        "ok": not errors, "phase": phase, "requirements": len(requirements), "trace_links": len(traces),
        "known_ids": len(known), "registered_decisions": len(decision_map), "direct_requirement_tests": sum(
            1 for req_id in rows_by_id if any(target.startswith("TST-") and relations[(req_id, target)] & VERIFICATION_RELATIONS for target in outbound.get(req_id, set()))
        ),
        "applicable": bool(requirements) or phase in {"requirements", "planning", "execution", "closure"},
        "note": "; ".join(notes) if notes else None, "errors": errors,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
