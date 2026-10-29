#!/usr/bin/env python3
"""Deterministic state, artifact, authority, and gate manager for SEF."""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import io
import json
import os
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path


PHASES = ("intake", "vft", "ssm", "reconcile", "stpa", "requirements", "planning", "execution", "closure")
REFERENCE = {
    "intake": "references/workflow.md + references/evidence.md",
    "vft": "references/vft-interview.md",
    "ssm": "references/ssm.md",
    "reconcile": "references/ssm.md",
    "stpa": "references/stpa-requirements.md",
    "requirements": "references/stpa-requirements.md",
    "planning": "references/artifacts.md",
    "execution": "references/multi-agent-judge.md",
    "closure": "references/multi-agent-judge.md",
}
REQUIRED = {
    "intake": ("00-intake/scope.md", "00-intake/source-register.csv", "00-intake/authorities.csv"),
    "vft": ("01-vft/vft-baseline.md",),
    "ssm": ("02-ssm/ssm-analysis.md",),
    "reconcile": ("02-ssm/vft-reconciliation.md",),
    "stpa": ("03-stpa/stpa-analysis.md",),
    "requirements": ("04-requirements/requirements.csv", "04-requirements/traceability.csv", "04-requirements/decisions.csv", "04-requirements/requirements-log.md"),
    "planning": (
        "05-planning/modules.csv",
        "05-planning/system/PRD.md", "05-planning/system/SPEC.md", "05-planning/system/TESTS.md",
        "05-planning/system/SPRINTS.md", "05-planning/system/TASKS.md",
    ),
    "execution": ("06-execution/evidence-register.csv",),
    "closure": ("07-closure/acceptance.md", "07-closure/residual-risk.md"),
}
EXPERT_GATES = {"stpa", "requirements", "planning", "execution", "closure"}
REVIEW_GATES = {"requirements", "planning", "execution", "closure"}
QUALIFIED_ROLES = {"domain-expert", "safety-authority", "independent-reviewer"}
APPROVAL_ROLES = {"user", *QUALIFIED_ROLES}
MODULE_ARTIFACTS = ("PRD.md", "SPEC.md", "TESTS.md", "SPRINTS.md", "TASKS.md")
QUALITY_THRESHOLD = 0.85
# Blocker codes that are SOFT for low/medium/high risk and HARD for safety-critical.
# Every other blocker (invalid state/schema, authorities, missing artifacts, traceability, risk unset,
# user / domain-expert / safety-authority roles) is always HARD. The domain-expert role is HARD in high.
SOFT_CODES = {
    "missing-role:independent-reviewer", "fixture-only-approval", "requirement-not-executable",
    "rq-below-threshold", "quality-missing", "stpa-step-undecided", "upstream-artifact-changed",
}
# SOFT in every risk class, safety-critical included: they inform, coverage is not proof.
ALWAYS_SOFT_CODES = {"completeness-mix", "objective-uncovered", "rq-addendum-below-threshold", "pending-requirements-high"}
PENDING_STATUSES = {"blocked", "proposed", "draft"}
PENDING_FRACTION_LIMIT = 0.05
REOPEN_ROLES = ("safety-authority", "domain-expert")
STPA_GATE_STEPS = {"stpa": {"1", "2", "3", "4", "5"}, "requirements": {"6", "7"}}
STPA_RELATIVE = "03-stpa/stpa-analysis.md"
LOG_RELATIVE = "04-requirements/requirements-log.md"
OBJECTIVE_FILES = ("01-vft/vft-baseline.md", "02-ssm/vft-reconciliation.md")
ID_RE = re.compile(r"\b(?:SRC|STK|VAL|OBJ|SSM|LOSS|HAZ|SC|CA|UCA|CS|REQ|SPEC|TST|SPR|TSK|EVD|DEC)-[A-Z0-9][A-Z0-9._-]*\b", re.I)
OUT_OF_SCOPE_RE = re.compile(r"out[- ]of[- ]scope|fora do escopo", re.I)
UNDECIDED = {"", "-", "pending", "pendente", "tbd"}
ALTERNATIVES = {
    "missing-role:independent-reviewer": [
        "register an independent reviewer in 00-intake/authorities.csv and record their approval",
        "run a cross-review by a second agent and attach the opinion as evidence",
        "accept the risk in writing (--acknowledge-warnings with the decision text)",
    ],
    "missing-role:domain-expert": [
        "register an active domain expert in 00-intake/authorities.csv with scope covering this phase and obtain their approval",
        "ask the user to name a qualified domain expert; the agent cannot stand in for one",
    ],
    "missing-role:safety-authority": [
        "register an active safety authority in 00-intake/authorities.csv with scope covering this phase and obtain their approval",
        "no LLM or fixture can substitute for a safety authority (DEC-007)",
    ],
    "missing-role:user": ["record an explicit user approval with sef.py approve for the current artifact hashes"],
    "fixture-only-approval": [
        "obtain a real (non-fixture) approval from the user",
        "treat the execution as a disposable prototype built on simulated approval",
    ],
    "requirement-not-executable": [
        "execute only the approved subset and keep the rest out of the sprint scope",
        "resolve the pending decisions listed in blocked_by and approve the requirements",
        "convert the open requirements into a spike or proof of concept",
    ],
    "rq-below-threshold": [
        "rewrite the requirements with IRQ < 1 listed in the details",
        "run a new measurement round and update 04-requirements/quality.csv",
        "advance assuming the risk of rework (--acknowledge-warnings with the decision text)",
    ],
    "quality-missing": [
        "create 04-requirements/quality.csv from the template and score every requirement (halligan.py)",
        "score a sample first, then extend to all requirements",
        "advance without measurement, accepting the risk (--acknowledge-warnings with the decision text)",
    ],
    "stpa-step-undecided": [
        "record the human decision, approver and date for each step of this gate (STPA gate: 1-5; requirements gate: 6-7) in the STPA step registry",
        "remove the steps that were not performed and say so in the analysis",
        "advance accepting the unreviewed steps (--acknowledge-warnings with the decision text)",
    ],
    "completeness-mix": [
        "generate requirements of the under-represented kind (e.g. interface requirements for the external systems of the System Overview)",
        "generate the missing non-functional requirements (accessibility, privacy, availability, maintainability) from the VFT objectives",
        "record in writing why the mix is acceptable for this system (--acknowledge-warnings with the decision text)",
    ],
    "objective-uncovered": [
        "generate requirements for the uncovered objective and cite it in source_ids, origin or validation_link",
        "register in 04-requirements/decisions.csv (affected_ids = the objective, text 'fora do escopo' / 'out of scope') that the objective is out of scope",
        "advance accepting the gap (--acknowledge-warnings with the decision text)",
    ],
    "rq-addendum-below-threshold": [
        "estimate the omissions again with a domain expert and update omission_ratio in quality.csv",
        "write the omitted requirements and score them, then re-run halligan.py",
        "accept the risk in writing (--acknowledge-warnings with the decision text)",
    ],
    "pending-requirements-high": [
        "run sef.py pending <project> and give the user the single list of questions in one round",
        "resolve the pending decisions and approve the requirements that no longer depend on them",
        "advance accepting the pending requirements (--acknowledge-warnings with the decision text)",
    ],
    "upstream-artifact-changed": [
        "re-approve the affected earlier phase for the current artifact hashes",
        "revert the edit to the earlier-phase artifact",
        "record the delta with sef.py reopen --phase <affected phase> and redo the gates",
    ],
    "risk-class:unset": ["run sef.py set-risk during intake with a rationale"],
}
SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")
CSV_SCHEMAS = {
    "00-intake/source-register.csv": ("source_id", "title", "authority", "url_or_path", "published_at", "accessed_at", "claim", "limitations", "confidence", "relation"),
    "00-intake/authorities.csv": ("authority_id", "name", "role", "scope", "evidence", "status"),
    "04-requirements/requirements.csv": (
        "requirement_id", "level", "statement", "type", "source_ids", "rationale", "allocation",
        "verification_method", "verification_criterion", "validation_link", "priority", "risk", "owner", "status",
        "constraint_class", "waiver_policy", "threshold_source", "blocked_by", "decision_ids",
    ),
    "04-requirements/traceability.csv": ("from_id", "to_id", "relationship", "rationale", "source_id", "status"),
    "04-requirements/decisions.csv": ("decision_id", "title", "status", "owner", "authority_id", "evidence", "affected_ids", "rationale"),
    "05-planning/modules.csv": ("module_id", "name", "path", "material", "rationale"),
    "06-execution/evidence-register.csv": ("evidence_id", "task_id", "requirement_ids", "command_or_method", "result", "artifact_path", "observed_at", "reviewer"),
}


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def timestamp_slug() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")


def control_dir(project: Path) -> Path:
    return project.resolve() / ".systemic-engineering"


def state_path(project: Path) -> Path:
    return control_dir(project) / "state.json"


def read_state(project: Path) -> dict:
    path = state_path(project)
    if not path.exists():
        raise SystemExit(f"State not found: {path}")
    state = json.loads(path.read_text(encoding="utf-8"))
    if state.get("schema_version") != 2:
        raise SystemExit(f"Unsupported state schema_version={state.get('schema_version')}; migrate to schema 2 before continuing")
    return state


def atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)


def write_state(project: Path, state: dict) -> None:
    atomic_write(state_path(project), json.dumps(state, ensure_ascii=False, indent=2) + "\n")


def event(state: dict, kind: str, **payload: object) -> dict:
    item = {"at": now(), "kind": kind, **payload}
    return {**state, "updated_at": item["at"], "history": [*state.get("history", []), item]}


def copy_template(name: str, destination: Path, replacements: dict[str, str] | None = None) -> None:
    source = Path(__file__).resolve().parents[1] / "assets" / "templates" / name
    text = source.read_text(encoding="utf-8")
    for key, value in (replacements or {}).items():
        text = text.replace("{{" + key + "}}", value)
    destination.parent.mkdir(parents=True, exist_ok=True)
    if not destination.exists():
        destination.write_text(text, encoding="utf-8")


def write_if_missing(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text(content, encoding="utf-8")


def scaffold_phase(project: Path, phase: str, name: str) -> None:
    root = control_dir(project)
    if phase == "intake":
        copy_template("SCOPE.md", root / "00-intake/scope.md", {"project_name": name})
        write_if_missing(root / "00-intake/source-register.csv", "source_id,title,authority,url_or_path,published_at,accessed_at,claim,limitations,confidence,relation\n")
        write_if_missing(root / "00-intake/authorities.csv", "authority_id,name,role,scope,evidence,status\n")
    elif phase == "vft":
        copy_template("VFT.md", root / "01-vft/vft-baseline.md", {"project_name": name})
    elif phase == "ssm":
        copy_template("SSM.md", root / "02-ssm/ssm-analysis.md", {"project_name": name})
    elif phase == "reconcile":
        write_if_missing(root / "02-ssm/vft-reconciliation.md", "# VFT reconciliation after SSM\n\n| ID | Action | Before | After | SSM evidence | Rationale |\n|---|---|---|---|---|---|\n")
    elif phase == "stpa":
        copy_template("STPA.md", root / "03-stpa/stpa-analysis.md", {"project_name": name})
    elif phase == "requirements":
        copy_template("requirements.csv", root / "04-requirements/requirements.csv")
        copy_template("traceability.csv", root / "04-requirements/traceability.csv")
        copy_template("decisions.csv", root / "04-requirements/decisions.csv")
        copy_template("quality.csv", root / "04-requirements/quality.csv")
        copy_template("REQUIREMENTS-LOG.md", root / "04-requirements/requirements-log.md", {"project_name": name})
    elif phase == "planning":
        write_if_missing(root / "05-planning/modules.csv", "module_id,name,path,material,rationale\n")
        for template in MODULE_ARTIFACTS:
            copy_template(template, root / "05-planning/system" / template, {"name": name, "system_or_module": "system"})
    elif phase == "execution":
        write_if_missing(root / "06-execution/evidence-register.csv", "evidence_id,task_id,requirement_ids,command_or_method,result,artifact_path,observed_at,reviewer\n")
        (root / "judge").mkdir(parents=True, exist_ok=True)
    elif phase == "closure":
        write_if_missing(root / "07-closure/acceptance.md", "# Acceptance\n\n")
        write_if_missing(root / "07-closure/residual-risk.md", "# Residual risk and open debt\n\n")


def unresolved(path: Path) -> bool:
    if path.suffix.lower() == ".csv":
        rows = [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
        return len(rows) < 2
    text = path.read_text(encoding="utf-8")
    return "{{" in text or len(text.strip()) < 80


def validate_modules(root: Path) -> list[str]:
    path = root / "05-planning/modules.csv"
    if not path.exists() or unresolved(path):
        return []
    errors: list[str] = []
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    seen_ids: set[str] = set()
    seen_paths: set[str] = set()
    for line, row in enumerate(rows, start=2):
        if not all((row.get(field) or "").strip() for field in ("module_id", "name", "material", "rationale")):
            errors.append(f"modules.csv:{line}:incomplete")
            continue
        material = row["material"].strip().lower()
        module_id = row["module_id"].strip()
        module_path = (row.get("path") or "").strip()
        if module_id in seen_ids:
            errors.append(f"modules.csv:{line}:duplicate-id:{module_id}")
        seen_ids.add(module_id)
        if module_path and module_path in seen_paths:
            errors.append(f"modules.csv:{line}:duplicate-path:{module_path}")
        if module_path:
            seen_paths.add(module_path)
        if material not in {"true", "false"}:
            errors.append(f"modules.csv:{line}:invalid-material:{material}")
            continue
        if material == "true":
            slug = module_path
            if not SLUG_RE.fullmatch(slug):
                errors.append(f"modules.csv:{line}:invalid-path:{slug}")
                continue
            for artifact in MODULE_ARTIFACTS:
                artifact_path = root / "05-planning/modules" / slug / artifact
                if not artifact_path.exists():
                    errors.append(f"missing:05-planning/modules/{slug}/{artifact}")
                elif unresolved(artifact_path):
                    errors.append(f"incomplete:05-planning/modules/{slug}/{artifact}")
    return errors


def legacy_steps_in_stpa(root: Path) -> bool:
    path = root / STPA_RELATIVE
    return path.exists() and bool(re.search(r"^#+\s*Step 6\b", path.read_text(encoding="utf-8"), re.M))


def validate_phase(project: Path, phase: str) -> list[str]:
    root = control_dir(project)
    errors: list[str] = []
    for relative in REQUIRED[phase]:
        path = root / relative
        if not path.exists() and relative == LOG_RELATIVE and legacy_steps_in_stpa(root):
            continue  # legacy project: steps 6-7 still live in stpa-analysis.md
        if not path.exists():
            errors.append(f"missing:{relative}")
        elif unresolved(path):
            errors.append(f"incomplete:{relative}")
        if path.exists() and relative in CSV_SCHEMAS:
            with path.open(newline="", encoding="utf-8") as handle:
                header = set(next(csv.reader(handle), []))
            missing_headers = [field for field in CSV_SCHEMAS[relative] if field not in header]
            if missing_headers:
                errors.append(f"schema:{relative}:missing:{','.join(missing_headers)}")
    if phase == "planning":
        errors.extend(validate_modules(root))
    return errors


def validate_reached(project: Path, current: str) -> dict[str, list[str]]:
    return {phase: validate_phase(project, phase) for phase in PHASES[: PHASES.index(current) + 1]}


def approvals_for(state: dict, phase: str) -> list[dict]:
    latest: dict[tuple[str, str, str], dict] = {}
    for item in state.get("approvals", []):
        if item.get("phase") != phase or item.get("superseded"):
            continue
        identity = item.get("authority_id") or item.get("by") or "unknown"
        latest[(phase, item.get("role", ""), identity)] = item
    return [item for item in latest.values() if item.get("decision") == "approved"]


def required_roles(state: dict, phase: str) -> set[str]:
    roles = {"user"}
    risk = state.get("risk_class")
    if risk == "medium" and phase in REVIEW_GATES:
        roles.add("independent-reviewer")
    if risk == "high" and phase in EXPERT_GATES:
        roles.add("domain-expert")
    if risk == "safety-critical" and phase in EXPERT_GATES:
        roles.update({"domain-expert", "safety-authority"})
    return roles


def gate_context_errors(state: dict) -> list[str]:
    return ["risk-class:unset"] if state.get("risk_class") not in {"low", "medium", "high", "safety-critical"} else []


def effective_approvals(project: Path, state: dict, phase: str) -> list[dict]:
    current_hashes = artifact_hashes(project, phase)
    return [item for item in approvals_for(state, phase) if item.get("artifact_hashes") == current_hashes]


def missing_roles(project: Path, state: dict, phase: str) -> list[str]:
    present = {item.get("role") for item in effective_approvals(project, state, phase)}
    return sorted(required_roles(state, phase) - present)


def execution_blockers(project: Path, state: dict, phase: str) -> list[str]:
    if phase not in {"planning", "execution", "closure"}:
        return []
    blockers: list[str] = []
    path = control_dir(project) / "04-requirements/requirements.csv"
    if path.exists():
        with path.open(newline="", encoding="utf-8") as handle:
            for row in csv.DictReader(handle):
                status = (row.get("status") or "").strip().lower()
                if status not in {"approved", "baselined", "accepted"}:
                    blockers.append(f"requirement-not-executable:{(row.get('requirement_id') or 'unknown').upper()}:{status or 'unset'}")
    if phase == "planning":
        by_role: dict[str, list[dict]] = {}
        for approval in effective_approvals(project, state, phase):
            by_role.setdefault(approval.get("role", ""), []).append(approval)
        for role in sorted(required_roles(state, phase)):
            candidates = by_role.get(role, [])
            if candidates and not any(not item.get("fixture", False) for item in candidates):
                blockers.append(f"fixture-only-approval:{role}")
    return blockers


def artifact_hashes(project: Path, phase: str) -> dict[str, str]:
    root = control_dir(project)
    result: dict[str, str] = {}
    for reached in PHASES[: PHASES.index(phase) + 1]:
        for relative in REQUIRED[reached]:
            path = root / relative
            if path.is_file():
                result[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
    if phase == "planning":
        modules = root / "05-planning/modules.csv"
        if modules.exists():
            with modules.open(newline="", encoding="utf-8") as handle:
                for row in csv.DictReader(handle):
                    if (row.get("material") or "").strip().lower() != "true":
                        continue
                    slug = (row.get("path") or "").strip()
                    for artifact in MODULE_ARTIFACTS:
                        relative = f"05-planning/modules/{slug}/{artifact}"
                        path = root / relative
                        if path.is_file():
                            result[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
    consulting = root / "08-consulting/model.json"
    if consulting.is_file():
        result["08-consulting/model.json"] = hashlib.sha256(consulting.read_bytes()).hexdigest()
    path = state_path(project)
    if path.exists():
        state = json.loads(path.read_text(encoding="utf-8"))
        result["@context/risk_class"] = hashlib.sha256(str(state.get("risk_class", "unset")).encode()).hexdigest()
        result["@context/mode"] = hashlib.sha256(str(state.get("mode", "real")).encode()).hexdigest()
    return result


def record_gate_evidence(project: Path, state: dict, phase: str, errors: list[str], missing: list[str], execution: list[str], outcome: str, extra: dict | None = None) -> Path:
    directory = control_dir(project) / "gates" / phase
    path = directory / f"{timestamp_slug()}-{outcome}.json"
    payload = {
        "schema_version": 1, "observed_at": now(), "phase": phase, "risk_class": state.get("risk_class"),
        "outcome": outcome, "artifact_hashes": artifact_hashes(project, phase), "validation_errors": errors,
        "required_roles": sorted(required_roles(state, phase)), "missing_roles": missing, "execution_blockers": execution,
        "approvals": approvals_for(state, phase), "effective_approvals": effective_approvals(project, state, phase),
        **(extra or {}),
    }
    atomic_write(path, json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    atomic_write(directory / "latest.json", json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    return path


def blocker_code(blocker: str) -> str:
    parts = blocker.split(":")
    return ":".join(parts[:2]) if parts[0] == "missing-role" and len(parts) > 1 else parts[0]


def severity(code: str, risk: object) -> str:
    """SOFT only for SOFT_CODES in low/medium/high risk; everything else is HARD."""
    if code in ALWAYS_SOFT_CODES:
        return "soft"
    return "soft" if code in SOFT_CODES and risk in {"low", "medium", "high"} else "hard"


def halligan_module():
    path = Path(__file__).resolve().with_name("halligan.py")
    spec = importlib.util.spec_from_file_location("sef_halligan", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


def quality_summary(project: Path) -> dict | None:
    """Halligan report for status; None when quality.csv does not exist."""
    if not (control_dir(project) / "04-requirements/quality.csv").exists():
        return None
    return halligan_module().build_report(project, QUALITY_THRESHOLD)


def quality_blockers(project: Path, phase: str) -> list[str]:
    if phase != "requirements":
        return []
    path = control_dir(project) / "04-requirements/requirements.csv"
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        total = sum(1 for _ in csv.DictReader(handle))
    if total == 0:
        return []
    quality_path = control_dir(project) / "04-requirements/quality.csv"
    if not quality_path.exists():
        return ["quality-missing:quality.csv"]
    if not halligan_module().read_csv(quality_path)[1]:
        return ["quality-missing:quality.csv has no scored rows"]
    report = halligan_module().build_report(project, QUALITY_THRESHOLD)
    if not report["ok"]:
        return [f"quality-invalid:{error}" for error in report["errors"]]
    found: list[str] = []
    if report["missing_from_quality"]:
        found.append("quality-missing:" + ",".join(report["missing_from_quality"]))
    if not report["meets_threshold"]:
        candidates = ",".join(f"{c['requirement_id']}={c['irq']}" for c in report["rewrite_candidates"])
        found.append(f"rq-below-threshold:RQ={report['rq']}<{QUALITY_THRESHOLD};IRQ<1:{candidates or 'none'}")
    if report["rq_primary"] < QUALITY_THRESHOLD:
        found.append(f"rq-addendum-below-threshold:RQ_primary={report['rq_primary']}<{QUALITY_THRESHOLD};estimated omissions={report['omission_total']}")
    return found


def stpa_step_blockers(project: Path, phase: str) -> list[str]:
    """STPA registry rows without a decision: steps 1-5 at the stpa gate, 6-7 at the requirements gate."""
    root = control_dir(project)
    path = root / (LOG_RELATIVE if phase == "requirements" and (root / LOG_RELATIVE).exists() else STPA_RELATIVE)  # fallback: legacy projects
    if phase not in STPA_GATE_STEPS or not path.exists():
        return []
    gate_steps = STPA_GATE_STEPS[phase]
    lines = path.read_text(encoding="utf-8").splitlines()
    start = next((i for i, line in enumerate(lines) if line.lstrip("# ").lower().startswith("registro de etapas")), None)
    if start is None:
        return []
    rows = []
    for line in lines[start + 1:]:
        if line.startswith("#"):
            break
        if line.strip().startswith("|"):
            rows.append([cell.strip() for cell in line.strip().strip("|").split("|")])
    header = next((row for row in rows if row and row[0].lower().startswith("etapa")), None)
    if not header:
        return []
    column = next((i for i, cell in enumerate(header) if cell.lower().startswith("decis")), None)
    if column is None:
        return []
    undecided = [
        row[0] for row in rows
        if row[0] in gate_steps and (len(row) <= column or row[column].lower() in UNDECIDED)
    ]
    return [f"stpa-step-undecided:{','.join(undecided)}"] if undecided else []


def read_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def requirement_rows(project: Path) -> list[dict[str, str]]:
    return read_rows(control_dir(project) / "04-requirements/requirements.csv")


def completeness_blockers(project: Path, phase: str) -> list[str]:
    if phase != "requirements":
        return []
    hints = halligan_module().completeness_info(requirement_rows(project))["completeness_hints"]
    return [f"completeness-mix:{hint['code']} {hint['message']}" for hint in hints]


def defined_objectives(project: Path) -> set[str]:
    found: set[str] = set()
    for relative in OBJECTIVE_FILES:
        path = control_dir(project) / relative
        if path.exists():
            found.update(item.upper() for item in ID_RE.findall(path.read_text(encoding="utf-8")) if item.upper().startswith(("OBJ-", "VAL-")))
    return found


def objective_blockers(project: Path, phase: str) -> list[str]:
    if phase != "requirements":
        return []
    rows = requirement_rows(project)
    if not rows:
        return []
    cited = {item.upper() for row in rows for field in ("source_ids", "origin", "validation_link") for item in ID_RE.findall(row.get(field) or "")}
    scoped_out = {
        item.upper() for row in read_rows(control_dir(project) / "04-requirements/decisions.csv")
        if OUT_OF_SCOPE_RE.search(f"{row.get('title', '')} {row.get('rationale', '')}")
        for item in ID_RE.findall(row.get("affected_ids") or "")
    }
    missing = sorted(defined_objectives(project) - cited - scoped_out)
    return [f"objective-uncovered:{item}" for item in missing]


def pending_requirement_blockers(project: Path, phase: str) -> list[str]:
    if phase != "requirements":
        return []
    rows = requirement_rows(project)
    pending = [r for r in rows if (r.get("status") or "").strip().lower() in PENDING_STATUSES]
    if not rows or len(pending) / len(rows) <= PENDING_FRACTION_LIMIT:
        return []
    return [f"pending-requirements-high:{len(pending)} of {len(rows)} requirements ({100 * len(pending) / len(rows):.1f}%) are blocked/proposed/draft"]


def phase_owns(phase: str, relative: str) -> bool:
    return relative in REQUIRED[phase] or (phase == "planning" and relative.startswith("05-planning/modules/"))


def stale_approvals(project: Path, state: dict) -> list[dict]:
    """Earlier phases whose own artifacts changed after their most recent live approval."""
    stale: list[dict] = []
    for phase in PHASES[: PHASES.index(state["phase"])]:
        approvals = approvals_for(state, phase)
        if not approvals:
            continue
        recorded = max(approvals, key=lambda item: item.get("at", "")).get("artifact_hashes") or {}
        current = artifact_hashes(project, phase)
        changed = sorted(k for k in {*recorded, *current} if phase_owns(phase, k) and recorded.get(k) != current.get(k))
        if changed:
            stale.append({"phase": phase, "files": changed})
    return stale


def stale_blockers(project: Path, state: dict) -> list[str]:
    return [f"upstream-artifact-changed:{item['phase']}={','.join(item['files'])}" for item in stale_approvals(project, state)]


def soft_checks(project: Path, state: dict, phase: str) -> list[str]:
    return [
        *quality_blockers(project, phase), *stpa_step_blockers(project, phase), *completeness_blockers(project, phase),
        *objective_blockers(project, phase), *pending_requirement_blockers(project, phase), *stale_blockers(project, state),
    ]


def superseded_phases(state: dict) -> list[str]:
    marked = {item.get("phase") for item in state.get("approvals", []) if item.get("superseded")}
    return [phase for phase in PHASES if phase in marked]


def blocker_message(code: str, details: list[str]) -> str:
    shown = "; ".join(details) if details else code
    return f"{code}: {shown}"


def classify(blockers: list[str], risk: object) -> tuple[list[str], list[dict], dict[str, list[str]]]:
    """Split blockers into HARD strings and aggregated SOFT warnings; collect alternatives by code."""
    hard: list[str] = []
    grouped: dict[str, list[str]] = {}
    alternatives: dict[str, list[str]] = {}
    for blocker in blockers:
        code = blocker_code(blocker)
        if code in ALTERNATIVES:
            alternatives[code] = ALTERNATIVES[code]
        if severity(code, risk) == "hard":
            hard.append(blocker)
        else:
            detail = blocker[len(code) + 1:]
            grouped.setdefault(code, [])
            if detail:
                grouped[code].append(detail)
    warnings = [
        {"code": code, "message": blocker_message(code, details), "severity": "soft", "details": details, "alternatives": ALTERNATIVES.get(code, [])}
        for code, details in grouped.items()
    ]
    return hard, warnings, alternatives


def role_detail(project: Path, role: str, phase: str) -> str:
    candidates = [
        f"{r.get('authority_id')} ({r.get('name')}, {r.get('status')}, scope {r.get('scope')})"
        for r in read_rows(control_dir(project) / "00-intake/authorities.csv") if r.get("role") == role
    ]
    listed = "; ".join(candidates) if candidates else f"no registered {role} in 00-intake/authorities.csv"
    return f"role {role} has no live approval for {phase}; candidates: {listed}"


def assess_gate(project: Path, state: dict, phase: str) -> dict:
    per_phase = validate_reached(project, phase)
    errors = [f"{name}:{error}" for name, values in per_phase.items() for error in values]
    errors.extend(gate_context_errors(state))
    if (control_dir(project) / "08-consulting/model.json").is_file():
        from sef_runtime import store as consulting_store
        try:
            consulting_store.integrity(project)
        except (ValueError, OSError) as error:
            errors.append("consulting-integrity:" + type(error).__name__)
    errors.extend(traceability_errors(project, phase)[0])
    missing = missing_roles(project, state, phase)
    execution = execution_blockers(project, state, phase)
    extra = soft_checks(project, state, phase)
    blockers = [*errors, *[f"missing-role:{role}:{role_detail(project, role, phase)}" for role in missing], *execution, *extra]
    hard, warnings, alternatives = classify(blockers, state.get("risk_class"))
    return {
        "errors": errors, "missing": missing, "execution": execution, "blockers": blockers,
        "hard": hard, "warnings": warnings, "alternatives": alternatives,
    }


def traceability_errors(project: Path, phase: str) -> tuple[list[str], dict | None]:
    if PHASES.index(phase) < PHASES.index("requirements"):
        return [], None
    script = Path(__file__).resolve().with_name("validate_traceability.py")
    result = subprocess.run([sys.executable, str(script), str(project)], capture_output=True, text=True)
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError:
        return ["traceability:validator-output-invalid"], None
    return [f"traceability:{error}" for error in payload.get("errors", [])], payload


def authority_record(project: Path, authority_id: str) -> dict[str, str] | None:
    path = control_dir(project) / "00-intake/authorities.csv"
    if not path.exists():
        return None
    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            if (row.get("authority_id") or "").strip() == authority_id:
                return row
    return None


def scope_tokens(value: str) -> set[str]:
    return {item for item in re.split(r"[,;\s]+", value.strip().lower()) if item}


def project_relative(project: Path, path: Path) -> str:
    return path.resolve().relative_to(project.resolve()).as_posix()


def command_init(args: argparse.Namespace) -> int:
    project = Path(args.project).resolve()
    project.mkdir(parents=True, exist_ok=True)
    path = state_path(project)
    if path.exists():
        raise SystemExit(f"Refusing to overwrite existing state: {path}")
    scaffold_phase(project, "intake", args.name)
    timestamp = now()
    state = {
        "schema_version": 2, "project_name": args.name, "project_root": ".", "mode": args.mode,
        "created_at": timestamp, "updated_at": timestamp, "phase": "intake", "risk_class": "unset",
        "approvals": [], "history": [{"at": timestamp, "kind": "initialized", "phase": "intake"}],
    }
    write_state(project, state)
    print(json.dumps({"status": "initialized", "phase": "intake", "reference": REFERENCE["intake"]}, indent=2))
    return 0


def command_status(args: argparse.Namespace) -> int:
    project = Path(args.project)
    state = read_state(project)
    phase = state["phase"]
    gate = assess_gate(project, state, phase)
    errors, missing, execution, blockers = gate["errors"], gate["missing"], gate["execution"], gate["blockers"]
    hard_missing = [role for role in missing if any(item.startswith(f"missing-role:{role}") for item in gate["hard"])]
    if gate["hard"]:
        next_action = "complete or repair artifacts" if errors else ("obtain required approvals" if hard_missing else "resolve hard blockers")
    elif gate["warnings"]:
        next_action = "show warnings and alternatives to the user; advance --acknowledge-warnings only after an explicit decision"
    else:
        next_action = "advance gate"
    output = {
        "project": state["project_name"], "phase": phase, "risk_class": state["risk_class"],
        "reference": REFERENCE[phase], "required_artifacts": list(REQUIRED[phase]),
        "validation_errors": errors, "approvals": approvals_for(state, phase), "effective_approvals": effective_approvals(project, state, phase),
        "required_roles": sorted(required_roles(state, phase)), "missing_roles": missing, "execution_blockers": execution,
        "gate_ready": not blockers, "blockers": blockers, "hard_blockers": gate["hard"], "warnings": gate["warnings"],
        "alternatives": gate["alternatives"], "can_advance": not gate["hard"], "quality": quality_summary(project),
        "next_action": next_action, "stale_approvals": stale_approvals(project, state),
        "reopened_from": state.get("reopened_from"), "superseded_phases": superseded_phases(state),
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0


def command_set_risk(args: argparse.Namespace) -> int:
    project = Path(args.project)
    state = read_state(project)
    if state["phase"] != "intake":
        raise SystemExit("Risk class may be changed only during intake; later changes require reconciliation in a new baseline")
    updated = event({**state, "risk_class": args.risk_class}, "risk-classified", risk_class=args.risk_class, rationale=args.rationale)
    write_state(project, updated)
    print(f"risk_class={args.risk_class}")
    return 0


def command_approve(args: argparse.Namespace) -> int:
    project = Path(args.project)
    state = read_state(project)
    if args.phase != state["phase"]:
        raise SystemExit(f"Current phase is {state['phase']}; refusing approval for {args.phase}")
    if not args.authority_id or not args.evidence:
        raise SystemExit("All approvals require --authority-id and --evidence")
    authority = authority_record(project, args.authority_id)
    if not authority:
        raise SystemExit(f"Authority not registered: {args.authority_id}")
    if authority.get("role") != args.role or authority.get("status", "").lower() != "active":
        raise SystemExit("Authority role/status does not authorize this approval")
    if authority.get("name") != args.by:
        raise SystemExit("Approval name does not match authority register")
    if args.evidence != authority.get("evidence"):
        raise SystemExit("Approval evidence does not match authority register")
    scope = scope_tokens(authority.get("scope") or "")
    if not ({"all", "*", args.phase} & scope):
        raise SystemExit("Authority scope does not cover this phase")
    derived_fixture = state.get("mode", "real") == "fixture" or args.fixture
    record = {
        "at": now(), "phase": args.phase, "by": args.by, "role": args.role,
        "authority_id": args.authority_id, "evidence": args.evidence, "fixture": derived_fixture,
        "decision": args.decision, "note": args.note, "artifact_hashes": artifact_hashes(project, args.phase),
    }
    updated = event({**state, "approvals": [*state.get("approvals", []), record]}, "approval-recorded", **record)
    write_state(project, updated)
    print(json.dumps(record, ensure_ascii=False, indent=2))
    return 0


def command_validate(args: argparse.Namespace) -> int:
    project = Path(args.project)
    state = read_state(project)
    per_phase = validate_reached(project, state["phase"])
    errors = [f"{phase}:{error}" for phase, values in per_phase.items() for error in values]
    errors.extend(gate_context_errors(state))
    if (control_dir(project) / "08-consulting/model.json").is_file():
        from sef_runtime import store as consulting_store
        try:
            consulting_store.integrity(project)
        except (ValueError, OSError) as error:
            errors.append("consulting-integrity:" + type(error).__name__)
    trace_errors, trace_result = traceability_errors(project, state["phase"])
    errors.extend(trace_errors)
    execution = execution_blockers(project, state, state["phase"])
    _, warnings, _ = classify([*execution, *soft_checks(project, state, state["phase"])], state.get("risk_class"))
    result = {"stale_approvals": stale_approvals(project, state), "phase": state["phase"], "ok": not errors, "per_phase": per_phase, "traceability": trace_result, "errors": errors, "execution_blockers": execution, "warnings": warnings}
    if args.record:
        missing = missing_roles(project, state, state["phase"])
        evidence_path = record_gate_evidence(project, state, state["phase"], errors, missing, execution, "validated" if not errors else "invalid")
        result["evidence_path"] = project_relative(project, evidence_path)
    print(json.dumps(result, indent=2))
    return 0 if not errors else 1


def command_advance(args: argparse.Namespace) -> int:
    project = Path(args.project)
    state = read_state(project)
    phase = state["phase"]
    gate = assess_gate(project, state, phase)
    errors, missing, execution = gate["errors"], gate["missing"], gate["execution"]
    acknowledgement = (args.acknowledge_warnings or "").strip()
    if args.acknowledge_warnings is not None and not acknowledgement:
        raise SystemExit("--acknowledge-warnings requires the text of the decision")
    report = {"phase": phase, "risk_class": state.get("risk_class"), "hard_blockers": gate["hard"], "warnings": gate["warnings"], "alternatives": gate["alternatives"]}
    audit = {"hard_blockers": gate["hard"], "warnings": gate["warnings"]}
    if gate["hard"] or (gate["warnings"] and not acknowledgement):
        outcome = "blocked" if gate["hard"] else "warned"
        path = record_gate_evidence(project, state, phase, errors, missing, execution, outcome, audit)
        path_ref = project_relative(project, path)
        kind = "advance-blocked" if gate["hard"] else "advance-warned"
        updated = event(state, kind, phase=phase, validation_errors=errors, missing_roles=missing, execution_blockers=execution,
                        hard_blockers=gate["hard"], warning_codes=[w["code"] for w in gate["warnings"]], evidence_path=path_ref)
        write_state(project, updated)
        if gate["hard"]:
            print(json.dumps({"status": "blocked", **report, "evidence_path": path_ref}, ensure_ascii=False, indent=2))
            raise SystemExit("Gate blocked: " + ", ".join(gate["hard"]))
        hint = f'advance {args.project} --acknowledge-warnings "<decision text>"'
        print(json.dumps({"status": "warnings", **report, "evidence_path": path_ref,
                          "next": "Show these warnings and alternatives to the user. Re-run with " + hint + " only after an explicit user decision."}, ensure_ascii=False, indent=2))
        return 2
    index = PHASES.index(phase)
    if index == len(PHASES) - 1:
        raise SystemExit("Closure is the final phase")
    codes = [w["code"] for w in gate["warnings"]]
    acknowledged_at = now()
    ack = {"acknowledged_codes": codes, "acknowledgement": acknowledgement, "acknowledged_at": acknowledged_at} if codes else {}
    path = record_gate_evidence(project, state, phase, [], [], [], "passed", {"warnings": gate["warnings"], **ack})
    path_ref = project_relative(project, path)
    next_phase = PHASES[index + 1]
    scaffold_phase(project, next_phase, state["project_name"])
    reopened = state.get("reopened_from")
    carried = None if reopened and index + 1 >= PHASES.index(reopened) else reopened
    updated = event({**state, "phase": next_phase, "reopened_from": carried}, "phase-advanced", from_phase=phase, to_phase=next_phase, evidence_path=path_ref, **ack)
    write_state(project, updated)
    print(json.dumps({"phase": next_phase, "reference": REFERENCE[next_phase], "gate_evidence": path_ref, **ack}, indent=2))
    return 0


def authority_label(project: Path, owner: str, authority_id: str) -> str:
    record = authority_record(project, authority_id) if authority_id else None
    return (record or {}).get("name") or owner or authority_id or "unassigned"


def pending_questions(project: Path) -> list[dict]:
    """One question per pending decision, plus requirements without a decision and TBD statements."""
    directory = control_dir(project) / "04-requirements"
    decisions = {(r.get("decision_id") or "").strip().upper(): r for r in read_rows(directory / "decisions.csv")}
    open_decisions = {k for k, r in decisions.items() if (r.get("status") or "").strip().lower() == "pending"}
    requirements = read_rows(directory / "requirements.csv")
    grouped: dict[str, list[str]] = {key: [] for key in sorted(open_decisions)}
    questions: list[dict] = []
    tbd_re = halligan_module().TBD_RE
    tbd_questions: list[dict] = []
    for row in requirements:
        req_id = (row.get("requirement_id") or "").strip().upper()
        status = (row.get("status") or "").strip().lower()
        if status in PENDING_STATUSES:
            refs = {i.upper() for field in ("blocked_by", "decision_ids", "threshold_source") for i in ID_RE.findall(row.get(field) or "") if i.upper().startswith("DEC-")}
            refs = {i for i in refs if i in open_decisions or i not in decisions}
            for ref in sorted(refs):
                grouped.setdefault(ref, []).append(req_id)
            if not refs:
                questions.append({"id": req_id, "type": "requirement", "question": f"{req_id} is {status}: approve it, rewrite it, or say what is missing. {row.get('statement', '').strip()}",
                                  "requirements": [req_id], "authority": row.get("owner", "").strip() or "unassigned"})
        if tbd_re.search(row.get("statement") or ""):
            tbd_questions.append({"id": f"TBD-{req_id}", "type": "tbd", "question": f"Define the value left as TBD in {req_id}: {row.get('statement', '').strip()}",
                              "requirements": [req_id], "authority": row.get("owner", "").strip() or "unassigned"})
    already_grouped = {req for affected in grouped.values() for req in affected}
    questions.extend(q for q in tbd_questions if q["requirements"][0] not in already_grouped)
    decision_questions = []
    for ref, affected in grouped.items():
        row = decisions.get(ref, {})
        owner = (row.get("owner") or "").strip()
        title = (row.get("title") or "").strip() or "decision not registered in decisions.csv"
        decision_questions.append({
            "id": ref, "type": "decision", "question": f"{title}" + (f" ({row['rationale'].strip()})" if row.get("rationale") else ""),
            "requirements": sorted(set(affected)), "authority": authority_label(project, owner, (row.get("authority_id") or "").strip()),
        })
    return [*decision_questions, *sorted(questions, key=lambda q: (q["type"], q["id"]))]


def render_pending(questions: list[dict]) -> str:
    if not questions:
        return "No pending questions."
    lines = [f"{len(questions)} pending question(s) for the user, answer them in one round:", ""]
    for number, q in enumerate(questions, start=1):
        lines.append(f"{number}. [{q['id']}] {q['question']}")
        lines.append(f"   Affects: {', '.join(q['requirements']) or 'none listed'} | Likely authority: {q['authority']}")
    return "\n".join(lines)


def command_pending(args: argparse.Namespace) -> int:
    project = Path(args.project)
    questions = pending_questions(project)
    result: dict = {"pending": len(questions), "questions": questions, "written": None, "write_skipped": None}
    if args.write:
        target = control_dir(project) / "04-requirements/pending-questions.md"
        if target.exists() and "@user" in target.read_text(encoding="utf-8"):
            result["write_skipped"] = f"{project_relative(project, target)} contains an @user marker; not overwritten"
        else:
            header = "# Pending questions\n\nGenerated by `sef.py pending`. Add an @user marker to a line to protect this file from being overwritten.\n\n"
            atomic_write(target, header + render_pending(questions) + "\n")
            result["written"] = project_relative(project, target)
    print(json.dumps(result, ensure_ascii=False, indent=2) if args.json else render_pending(questions) + "".join(f"\n{v}" for v in (result["written"] and f"Written: {result['written']}", result["write_skipped"]) if v))
    return 2 if questions else 0


def reopen_requirements(state: dict, current: str) -> list[str]:
    return list(REOPEN_ROLES) if state.get("risk_class") == "safety-critical" and current in {"execution", "closure"} else []


def check_reopen_authority(project: Path, args: argparse.Namespace, required: list[str]) -> None:
    if not required:
        return
    role = (args.by_role or "").strip()
    if role not in required:
        raise SystemExit(f"Reopening {', '.join(sorted({'execution', 'closure'}))} in safety-critical requires --by-role in: {', '.join(required)}")
    path = control_dir(project) / "00-intake/authorities.csv"
    if not any(r.get("name") == args.by and r.get("role") == role and (r.get("status") or "").lower() == "active" for r in read_rows(path)):
        raise SystemExit(f"No active {role} named {args.by!r} in 00-intake/authorities.csv")


def command_reopen(args: argparse.Namespace) -> int:
    project = Path(args.project)
    state = read_state(project)
    current = state["phase"]
    reason, by = (args.reason or "").strip(), (args.by or "").strip()
    if not reason:
        raise SystemExit("reopen requires a non-empty --reason")
    if not by:
        raise SystemExit("reopen requires a non-empty --by")
    if args.phase not in PHASES:
        raise SystemExit(f"unknown phase: {args.phase}")
    if PHASES.index(args.phase) > PHASES.index(current):
        raise SystemExit(f"target phase {args.phase} is later than the current phase {current}")
    required = reopen_requirements(state, current)
    check_reopen_authority(project, args, required)
    stamp = now()
    cutoff = PHASES.index(args.phase)
    approvals = [{**a, "superseded": True, "superseded_at": stamp} if PHASES.index(a.get("phase", "intake")) >= cutoff and not a.get("superseded") else a
                 for a in state.get("approvals", [])]
    payload = dict(from_phase=current, to_phase=args.phase, reason=reason, by=by, by_role=(args.by_role or "").strip() or None, reopen_requires=required, reopened_at=stamp)
    gate = gate_snapshot(project, state, current)
    path = record_gate_evidence(project, state, current, *gate, "reopened", payload)
    updated = event({**state, "phase": args.phase, "approvals": approvals, "reopened_from": current}, "reopened", evidence_path=project_relative(project, path), **payload)
    write_state(project, updated)
    print(json.dumps({"phase": args.phase, "reopened_from": current, "evidence_path": project_relative(project, path), "superseded_phases": superseded_phases(updated)}, indent=2))
    return 0


def gate_snapshot(project: Path, state: dict, phase: str) -> tuple[list[str], list[str], list[str]]:
    return [], missing_roles(project, state, phase), execution_blockers(project, state, phase)


def command_create_module(args: argparse.Namespace) -> int:
    project = Path(args.project)
    state = read_state(project)
    if state["phase"] not in {"planning", "execution", "closure"}:
        raise SystemExit("Modules may be declared only from planning onward")
    if not SLUG_RE.fullmatch(args.path):
        raise SystemExit("Module path must be a lowercase hyphenated slug")
    root = control_dir(project)
    register = root / "05-planning/modules.csv"
    if register.exists():
        with register.open(newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
    else:
        rows = []
    if any(row.get("module_id") == args.module_id or row.get("path") == args.path for row in rows):
        raise SystemExit("Module id or path already exists")
    fields = ("module_id", "name", "path", "material", "rationale")
    rows.append({"module_id": args.module_id, "name": args.name, "path": args.path, "material": str(args.material).lower(), "rationale": args.rationale})
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=fields)
    writer.writeheader(); writer.writerows(rows)
    atomic_write(register, buffer.getvalue())
    if args.material:
        for template in MODULE_ARTIFACTS:
            copy_template(template, root / "05-planning/modules" / args.path / template, {"name": args.name, "system_or_module": "module"})
    print(json.dumps({"module_id": args.module_id, "path": args.path, "material": args.material}, indent=2))
    return 0


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    commands = root.add_subparsers(dest="command", required=True)
    init = commands.add_parser("init"); init.add_argument("project"); init.add_argument("--name", required=True); init.add_argument("--mode", choices=("real", "fixture"), default="real"); init.set_defaults(func=command_init)
    status = commands.add_parser("status"); status.add_argument("project"); status.set_defaults(func=command_status)
    risk = commands.add_parser("set-risk"); risk.add_argument("project"); risk.add_argument("--class", dest="risk_class", choices=("low", "medium", "high", "safety-critical"), required=True); risk.add_argument("--rationale", required=True); risk.set_defaults(func=command_set_risk)
    approve = commands.add_parser("approve"); approve.add_argument("project"); approve.add_argument("--phase", choices=PHASES, required=True); approve.add_argument("--by", required=True); approve.add_argument("--role", choices=sorted(APPROVAL_ROLES), required=True); approve.add_argument("--authority-id"); approve.add_argument("--evidence"); approve.add_argument("--fixture", action="store_true"); approve.add_argument("--decision", choices=("approved", "rejected"), required=True); approve.add_argument("--note", required=True); approve.set_defaults(func=command_approve)
    validate = commands.add_parser("validate"); validate.add_argument("project"); validate.add_argument("--record", action="store_true"); validate.set_defaults(func=command_validate)
    advance = commands.add_parser("advance"); advance.add_argument("project"); advance.add_argument("--acknowledge-warnings", metavar="DECISION_TEXT", default=None); advance.set_defaults(func=command_advance)
    pending = commands.add_parser("pending"); pending.add_argument("project"); pending.add_argument("--json", action="store_true"); pending.add_argument("--write", action="store_true"); pending.set_defaults(func=command_pending)
    reopen = commands.add_parser("reopen"); reopen.add_argument("project"); reopen.add_argument("--phase", required=True); reopen.add_argument("--by", required=True); reopen.add_argument("--by-role", default=None); reopen.add_argument("--reason", required=True); reopen.set_defaults(func=command_reopen)
    module = commands.add_parser("create-module"); module.add_argument("project"); module.add_argument("--id", dest="module_id", required=True); module.add_argument("--name", required=True); module.add_argument("--path", required=True); module.add_argument("--rationale", required=True); module.add_argument("--material", action=argparse.BooleanOptionalAction, default=True); module.set_defaults(func=command_create_module)
    from sef_runtime.cli import attach
    attach(commands)
    return root


def main() -> int:
    args = parser().parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
