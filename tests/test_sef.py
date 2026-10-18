from __future__ import annotations

import csv
import importlib.util
import json
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SEF = ROOT / ".agents" / "skills" / "systemic-engineering" / "scripts" / "sef.py"
TRACE = ROOT / ".agents" / "skills" / "systemic-engineering" / "scripts" / "validate_traceability.py"
HALLIGAN = ROOT / ".agents" / "skills" / "systemic-engineering" / "scripts" / "halligan.py"
_sef_spec = importlib.util.spec_from_file_location("sef_module", SEF)
sef_module = importlib.util.module_from_spec(_sef_spec)
_sef_spec.loader.exec_module(sef_module)  # type: ignore[union-attr]
_spec = importlib.util.spec_from_file_location("halligan", HALLIGAN)
halligan = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(halligan)  # type: ignore[union-attr]
PHASES = ("intake", "vft", "ssm", "reconcile", "stpa", "requirements", "planning")
REQ_FIELDS = [
    "requirement_id", "level", "parent_requirement_id", "statement", "type", "source_ids", "rationale",
    "assumptions", "allocation", "interfaces", "verification_method", "verification_criterion",
    "validation_link", "priority", "risk", "owner", "status", "constraint_class", "waiver_policy",
    "threshold_source", "blocked_by", "decision_ids",
]


class SefTests(unittest.TestCase):
    def run_cli(self, script: Path, *args: str, ok: bool = True) -> subprocess.CompletedProcess[str]:
        result = subprocess.run(["python3", str(script), *args], capture_output=True, text=True)
        if ok and result.returncode != 0:
            self.fail(result.stdout + result.stderr)
        return result

    def init(self, project: Path, mode: str = "real") -> Path:
        self.run_cli(SEF, "init", str(project), "--name", "Fixture", "--mode", mode)
        return project / ".systemic-engineering"

    def fill_intake(self, root: Path, authorities: str | None = None) -> None:
        (root / "00-intake/scope.md").write_text(
            "# Scope\n\nSystem boundary, lifecycle, risk, evidence, exclusions, authority, outputs, and acceptance are explicit for this isolated fixture.\n",
            encoding="utf-8",
        )
        (root / "00-intake/source-register.csv").write_text(
            "source_id,title,authority,url_or_path,published_at,accessed_at,claim,limitations,confidence,relation\n"
            "SRC-001,Fixture source,Owner,/fixture,2026-01-01,2026-10-16,Supports fixture,None,high,supports\n",
            encoding="utf-8",
        )
        (root / "00-intake/authorities.csv").write_text(
            "authority_id,name,role,scope,evidence,status\n" + (authorities or "AUTH-U,Test User,user,all,/fixture,active\n"),
            encoding="utf-8",
        )

    def set_state(self, root: Path, phase: str, risk: str) -> None:
        path = root / "state.json"
        state = json.loads(path.read_text(encoding="utf-8"))
        path.write_text(json.dumps({**state, "phase": phase, "risk_class": risk}, indent=2) + "\n", encoding="utf-8")

    def fill_markdown_phases(self, root: Path, through: str) -> None:
        mapping = {
            "vft": "01-vft/vft-baseline.md",
            "ssm": "02-ssm/ssm-analysis.md",
            "reconcile": "02-ssm/vft-reconciliation.md",
            "stpa": "03-stpa/stpa-analysis.md",
        }
        for phase, relative in mapping.items():
            if PHASES.index(phase) <= PHASES.index(through):
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(f"# {phase}\n\nFixture with defined IDs SRC-001 STK-001 VAL-001 OBJ-001 SSM-001 LOSS-001 HAZ-001 SC-001 UCA-001 CS-001 and enough substantive text for validation.\n", encoding="utf-8")

    def requirement_row(self, **overrides: str) -> dict[str, str]:
        row = {
            "requirement_id": "REQ-001", "level": "system", "parent_requirement_id": "",
            "statement": "The system shall stop safely when the approved condition occurs.", "type": "safety",
            "source_ids": "CS-001", "rationale": "Controls the causal scenario.", "assumptions": "None",
            "allocation": "controller", "interfaces": "sensor", "verification_method": "test",
            "verification_criterion": "Stops in the approved fixture.", "validation_link": "OBJ-001 VAL-001",
            "priority": "must", "risk": "medium", "owner": "STK-001", "status": "approved",
            "constraint_class": "ordinary", "waiver_policy": "controlled", "threshold_source": "not-applicable",
            "blocked_by": "none", "decision_ids": "DEC-001",
        }
        return {**row, **overrides}

    def write_requirements(self, root: Path, row: dict[str, str] | None = None, trace: str | None = None) -> None:
        directory = root / "04-requirements"
        directory.mkdir(parents=True, exist_ok=True)
        with (directory / "requirements.csv").open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=REQ_FIELDS)
            writer.writeheader(); writer.writerow(row or self.requirement_row())
        (directory / "traceability.csv").write_text(
            "from_id,to_id,relationship,rationale,source_id,status\n" +
            (trace or "OBJ-001,CS-001,frames,Anchor,SRC-001,proposed\nCS-001,REQ-001,mitigated_by,Origin,SRC-001,proposed\n"),
            encoding="utf-8",
        )
        (directory / "decisions.csv").write_text(
            "decision_id,title,status,owner,authority_id,evidence,affected_ids,rationale\n"
            "DEC-001,Fixture decision,approved,STK-001,AUTH-U,/fixture,REQ-001,Supports deterministic fixture\n",
            encoding="utf-8",
        )
        if not (directory / "requirements-log.md").exists():
            (directory / "requirements-log.md").write_text(self.log_text(), encoding="utf-8")

    def log_text(self, decision6: str = "approved", decision7: str = "approved") -> str:
        return (
            "# Requirements log\n\nSteps 6, 6b and 7 of the STPA roadmap, written after the STPA gate in this fixture file.\n\n"
            "## Registro de etapas\n\n| Etapa | Prompt/entrada | Saida | Decisao | Aprovador | Data |\n|---|---|---|---|---|---|\n"
            f"| 6 | p | o | {decision6} | Test User | 2026-10-18 |\n| 7 | p | o | {decision7} | Test User | 2026-10-18 |\n"
        )

    def fill_planning(self, root: Path) -> None:
        system = root / "05-planning/system"
        system.mkdir(parents=True, exist_ok=True)
        for name in ("PRD.md", "SPEC.md", "TESTS.md", "SPRINTS.md", "TASKS.md"):
            extra = " TST-001 SPEC-001 SPR-001 TSK-001 EVD-001" if name in {"TESTS.md", "SPEC.md", "SPRINTS.md", "TASKS.md"} else ""
            (system / name).write_text(f"# {name}\n\nComplete fixture planning artifact with scope, ownership, criteria, risks, checks, recovery, and evidence.{extra}\n", encoding="utf-8")
        (root / "05-planning/modules.csv").write_text(
            "module_id,name,path,material,rationale\nSYS,System only,,false,No separately material module in this fixture\n",
            encoding="utf-8",
        )

    def quality_row(self, **overrides: str) -> dict[str, str]:
        row = {"requirement_id": "REQ-001", "scorer": "human", "omission_ratio": "0", "notes": "", "rewrite": ""}
        row.update({field: "1" for field in (*halligan.ELEMENT_FIELDS, *halligan.IQF_FIELDS)})
        return {**row, **overrides}

    def write_quality(self, root: Path, rows: list[dict[str, str]]) -> None:
        with (root / "04-requirements/quality.csv").open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(halligan.QUALITY_COLUMNS))
            writer.writeheader(); writer.writerows(rows)

    def requirements_gate_project(self, temp: str, risk: str, authorities: str | None = None) -> tuple[Path, Path]:
        project = Path(temp) / "project"; root = self.init(project)
        self.fill_intake(root, authorities)
        self.fill_markdown_phases(root, "stpa"); self.write_requirements(root); self.set_state(root, "requirements", risk)
        return project, root

    def approve_user(self, project: Path, phase: str) -> None:
        self.run_cli(SEF, "approve", str(project), "--phase", phase, "--by", "Test User", "--role", "user", "--authority-id", "AUTH-U", "--evidence", "/fixture", "--decision", "approved", "--note", "Fixture")

    def history(self, root: Path) -> list[dict]:
        return json.loads((root / "state.json").read_text(encoding="utf-8"))["history"]

    def test_scaffolding_is_phase_local_and_blocked_attempt_is_audited(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp) / "project"
            root = self.init(project)
            self.assertEqual(json.loads((root / "state.json").read_text(encoding="utf-8"))["project_root"], ".")
            self.assertFalse((root / "01-vft").exists())
            self.assertFalse((root / "05-planning").exists())
            self.fill_intake(root)
            self.run_cli(SEF, "set-risk", str(project), "--class", "low", "--rationale", "Fixture")
            self.run_cli(SEF, "approve", str(project), "--phase", "intake", "--by", "Test User", "--role", "user", "--authority-id", "AUTH-U", "--evidence", "/fixture", "--decision", "approved", "--note", "Fixture")
            self.run_cli(SEF, "advance", str(project))
            self.assertTrue((root / "01-vft/vft-baseline.md").exists())
            self.assertFalse((root / "02-ssm").exists())
            blocked = self.run_cli(SEF, "advance", str(project), ok=False)
            self.assertIn("Gate blocked", blocked.stderr)
            state = json.loads((root / "state.json").read_text(encoding="utf-8"))
            self.assertEqual(state["history"][-1]["kind"], "advance-blocked")
            status = json.loads(self.run_cli(SEF, "status", str(project)).stdout)
            self.assertFalse(status["gate_ready"])
            self.assertEqual(status["next_action"], "complete or repair artifacts")

    def test_csv_schema_errors_are_reported(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp) / "project"; root = self.init(project)
            self.fill_intake(root)
            (root / "00-intake/source-register.csv").write_text("source_id,title\nSRC-001,Incomplete\n", encoding="utf-8")
            result = self.run_cli(SEF, "validate", str(project), ok=False)
            self.assertIn("schema:00-intake/source-register.csv:missing:", result.stdout)

    def test_safety_critical_requires_registered_domain_and_safety_authorities(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp) / "project"; root = self.init(project)
            self.fill_intake(root, "AUTH-U,Test User,user,all,/fixture,active\nAUTH-D,Domain Expert,domain-expert,stpa,/credential-d,active\nAUTH-S,Safety Authority,safety-authority,stpa,/credential-s,active\n")
            self.fill_markdown_phases(root, "stpa"); self.set_state(root, "stpa", "safety-critical")
            self.run_cli(SEF, "approve", str(project), "--phase", "stpa", "--by", "Test User", "--role", "user", "--authority-id", "AUTH-U", "--evidence", "/fixture", "--decision", "approved", "--note", "Draft")
            self.run_cli(SEF, "approve", str(project), "--phase", "stpa", "--by", "Domain Expert", "--role", "domain-expert", "--authority-id", "AUTH-D", "--evidence", "/credential-d", "--decision", "approved", "--note", "Domain review")
            blocked = self.run_cli(SEF, "advance", str(project), ok=False)
            self.assertIn("missing-role:safety-authority", blocked.stderr)
            self.run_cli(SEF, "approve", str(project), "--phase", "stpa", "--by", "Safety Authority", "--role", "safety-authority", "--authority-id", "AUTH-S", "--evidence", "/credential-s", "--decision", "approved", "--note", "Safety review")
            advanced = json.loads(self.run_cli(SEF, "advance", str(project)).stdout)
            self.assertEqual(advanced["phase"], "requirements")
            self.assertTrue((root / "04-requirements/requirements.csv").exists())
            self.assertFalse((root / "05-planning").exists())

    def test_qualified_approval_rejects_unregistered_or_mismatched_identity(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp) / "project"; root = self.init(project)
            self.fill_intake(root, "AUTH-D,Domain Expert,domain-expert,all,/credential,active\n")
            failed = self.run_cli(SEF, "approve", str(project), "--phase", "intake", "--by", "Wrong Name", "--role", "domain-expert", "--authority-id", "AUTH-D", "--evidence", "/credential", "--decision", "approved", "--note", "No", ok=False)
            self.assertIn("does not match", failed.stderr)

    def test_medium_requirements_gate_requires_registered_independent_reviewer(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp) / "project"; root = self.init(project)
            self.fill_intake(root, "AUTH-U,Test User,user,all,/fixture,active\nAUTH-R,Independent Reviewer,independent-reviewer,requirements,/review,active\n")
            self.fill_markdown_phases(root, "stpa"); self.write_requirements(root); self.set_state(root, "requirements", "medium")
            self.run_cli(SEF, "approve", str(project), "--phase", "requirements", "--by", "Test User", "--role", "user", "--authority-id", "AUTH-U", "--evidence", "/fixture", "--decision", "approved", "--note", "Requirements")
            warned = self.run_cli(SEF, "advance", str(project), ok=False)
            self.assertEqual(warned.returncode, 2)  # SOFT in medium: warns instead of failing
            self.assertIn("missing-role:independent-reviewer", [w["code"] for w in json.loads(warned.stdout)["warnings"]])
            self.run_cli(SEF, "approve", str(project), "--phase", "requirements", "--by", "Independent Reviewer", "--role", "independent-reviewer", "--authority-id", "AUTH-R", "--evidence", "/review", "--decision", "approved", "--note", "Independent review")
            still = self.run_cli(SEF, "advance", str(project), ok=False)  # only the missing quality.csv remains (SOFT)
            self.assertEqual([w["code"] for w in json.loads(still.stdout)["warnings"]], ["quality-missing"])
            self.write_quality(root, [self.quality_row()])
            self.assertEqual(json.loads(self.run_cli(SEF, "advance", str(project)).stdout)["phase"], "planning")

    def test_planning_requires_direct_requirement_to_test_trace(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp) / "project"; root = self.init(project)
            self.fill_intake(root); self.fill_markdown_phases(root, "stpa")
            self.write_requirements(root, trace="OBJ-001,CS-001,frames,Anchor,SRC-001,proposed\nCS-001,REQ-001,mitigated_by,Origin,SRC-001,proposed\nREQ-001,SPEC-001,allocated_to,Allocation,SRC-001,planned\n")
            self.fill_planning(root); self.set_state(root, "planning", "low")
            failed = self.run_cli(TRACE, str(project), ok=False)
            self.assertIn("untraced-requirement-verification:REQ-001", failed.stdout)
            trace = root / "04-requirements/traceability.csv"
            trace.write_text(trace.read_text(encoding="utf-8") + "REQ-001,TST-001,verified_by,Direct test,SRC-001,planned\n", encoding="utf-8")
            result = json.loads(self.run_cli(TRACE, str(project)).stdout)
            self.assertTrue(result["ok"])
            self.assertEqual(result["direct_requirement_tests"], 1)

    def test_non_compensable_constraint_rejects_waiver(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp) / "project"; root = self.init(project)
            self.fill_intake(root); self.fill_markdown_phases(root, "stpa")
            row = self.requirement_row(constraint_class="non-compensable", waiver_policy="authority-exception")
            self.write_requirements(root, row=row); self.set_state(root, "requirements", "low")
            failed = self.run_cli(TRACE, str(project), ok=False)
            self.assertIn("non-compensable-waiver:REQ-001", failed.stdout)

    def test_unregistered_or_pending_decision_cannot_support_approved_threshold(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp) / "project"; root = self.init(project)
            self.fill_intake(root); self.fill_markdown_phases(root, "stpa")
            row = self.requirement_row(status="approved", threshold_source="DEC-THR", decision_ids="DEC-THR", blocked_by="DEC-THR")
            self.write_requirements(root, row=row); self.set_state(root, "requirements", "low")
            decisions = root / "04-requirements/decisions.csv"
            decisions.write_text("decision_id,title,status,owner,authority_id,evidence,affected_ids,rationale\n", encoding="utf-8")
            missing = self.run_cli(TRACE, str(project), ok=False)
            self.assertIn("unregistered-decision:DEC-THR", missing.stdout)
            decisions.write_text(
                "decision_id,title,status,owner,authority_id,evidence,affected_ids,rationale\n"
                "DEC-THR,Threshold choice,pending,STK-001,AUTH-U,/fixture,REQ-001,Awaiting evidence\n",
                encoding="utf-8",
            )
            pending = self.run_cli(TRACE, str(project), ok=False)
            self.assertIn("unapproved-decision:DEC-THR", pending.stdout)
            self.assertIn("unapproved-threshold:DEC-THR", pending.stdout)
            self.assertIn("unresolved-blocker:DEC-THR", pending.stdout)

    def test_risk_is_mandatory_and_cannot_be_downgraded_after_intake(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp) / "project"; root = self.init(project)
            self.fill_intake(root)
            status = json.loads(self.run_cli(SEF, "status", str(project)).stdout)
            self.assertIn("risk-class:unset", status["blockers"])
            blocked = self.run_cli(SEF, "advance", str(project), ok=False)
            self.assertIn("risk-class:unset", blocked.stderr)
            self.set_state(root, "stpa", "safety-critical")
            downgrade = self.run_cli(SEF, "set-risk", str(project), "--class", "low", "--rationale", "Bypass", ok=False)
            self.assertIn("only during intake", downgrade.stderr)

    def test_latest_rejection_revokes_earlier_approval(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp) / "project"; root = self.init(project)
            self.fill_intake(root)
            self.run_cli(SEF, "set-risk", str(project), "--class", "low", "--rationale", "Fixture")
            base = ("--phase", "intake", "--by", "Test User", "--role", "user", "--authority-id", "AUTH-U", "--evidence", "/fixture")
            self.run_cli(SEF, "approve", str(project), *base, "--decision", "approved", "--note", "Initial")
            self.assertTrue(json.loads(self.run_cli(SEF, "status", str(project)).stdout)["gate_ready"])
            self.run_cli(SEF, "approve", str(project), *base, "--decision", "rejected", "--note", "Revoked")
            status = json.loads(self.run_cli(SEF, "status", str(project)).stdout)
            self.assertIn("user", status["missing_roles"])
            self.assertFalse(status["gate_ready"])

    def test_fixture_mode_marks_approval_without_per_approval_flag(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp) / "project"; root = self.init(project, mode="fixture")
            self.fill_intake(root)
            self.run_cli(SEF, "set-risk", str(project), "--class", "low", "--rationale", "Evaluation")
            result = json.loads(self.run_cli(
                SEF, "approve", str(project), "--phase", "intake", "--by", "Test User", "--role", "user",
                "--authority-id", "AUTH-U", "--evidence", "/fixture", "--decision", "approved", "--note", "Evaluation",
            ).stdout)
            self.assertTrue(result["fixture"])

    def test_all_approvals_require_matching_authority_evidence_and_scope(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp) / "project"; root = self.init(project)
            self.fill_intake(root, "AUTH-U,Test User,user,vft,/proof,active\n")
            missing = self.run_cli(SEF, "approve", str(project), "--phase", "intake", "--by", "Test User", "--role", "user", "--decision", "approved", "--note", "No", ok=False)
            self.assertIn("All approvals require", missing.stderr)
            evidence = self.run_cli(SEF, "approve", str(project), "--phase", "intake", "--by", "Test User", "--role", "user", "--authority-id", "AUTH-U", "--evidence", "/wrong", "--decision", "approved", "--note", "No", ok=False)
            self.assertIn("evidence does not match", evidence.stderr)
            scope = self.run_cli(SEF, "approve", str(project), "--phase", "intake", "--by", "Test User", "--role", "user", "--authority-id", "AUTH-U", "--evidence", "/proof", "--decision", "approved", "--note", "No", ok=False)
            self.assertIn("scope does not cover", scope.stderr)

    def test_approved_requirement_rejects_pending_decision_id_and_range_shorthand(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp) / "project"; root = self.init(project)
            self.fill_intake(root); self.fill_markdown_phases(root, "stpa")
            row = self.requirement_row(status="approved", decision_ids="DEC-001", threshold_source="not-applicable", blocked_by="none")
            self.write_requirements(root, row=row); self.set_state(root, "planning", "low"); self.fill_planning(root)
            decisions = root / "04-requirements/decisions.csv"
            decisions.write_text(
                "decision_id,title,status,owner,authority_id,evidence,affected_ids,rationale\n"
                "DEC-001,Pending choice,pending,STK-001,AUTH-U,/fixture,REQ-001,Awaiting approval\n",
                encoding="utf-8",
            )
            (root / "05-planning/system/TASKS.md").write_text("# Tasks\n\nPseudo range TST-001..010 must not be accepted as explicit trace evidence.\n", encoding="utf-8")
            failed = self.run_cli(TRACE, str(project), ok=False)
            self.assertIn("unapproved-decision:DEC-001", failed.stdout)
            self.assertIn("range-shorthand:05-planning/system/TASKS.md:TST-001..010", failed.stdout)

    def test_planning_cannot_advance_with_blocked_requirements_or_fixture_only_approvals(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp) / "project"; root = self.init(project)
            self.fill_intake(root, "AUTH-U,Test User,user,all,/fixture,active\nAUTH-R,Independent Reviewer,independent-reviewer,planning,/review,active\n")
            self.fill_markdown_phases(root, "stpa")
            row = self.requirement_row(status="blocked", blocked_by="DEC-001")
            self.write_requirements(root, row=row, trace="OBJ-001,CS-001,frames,Anchor,SRC-001,proposed\nCS-001,REQ-001,mitigated_by,Origin,SRC-001,proposed\nREQ-001,TST-001,verified_by,Direct test,SRC-001,planned\n")
            self.fill_planning(root); self.set_state(root, "planning", "medium")
            self.run_cli(SEF, "approve", str(project), "--phase", "planning", "--by", "Test User", "--role", "user", "--authority-id", "AUTH-U", "--evidence", "/fixture", "--fixture", "--decision", "approved", "--note", "Fixture")
            self.run_cli(SEF, "approve", str(project), "--phase", "planning", "--by", "Independent Reviewer", "--role", "independent-reviewer", "--authority-id", "AUTH-R", "--evidence", "/review", "--fixture", "--decision", "approved", "--note", "Fixture")
            status = json.loads(self.run_cli(SEF, "status", str(project)).stdout)
            self.assertFalse(status["gate_ready"])
            self.assertIn("requirement-not-executable:REQ-001:blocked", status["execution_blockers"])
            self.assertIn("fixture-only-approval:user", status["execution_blockers"])
            blocked = self.run_cli(SEF, "advance", str(project), ok=False)
            self.assertEqual(blocked.returncode, 2)  # medium risk: both blockers are SOFT warnings
            warned_codes = {w["code"] for w in json.loads(blocked.stdout)["warnings"]}
            self.assertEqual(warned_codes, {"requirement-not-executable", "fixture-only-approval"})
            self.assertEqual(json.loads((root / "state.json").read_text(encoding="utf-8"))["phase"], "planning")

            row["status"] = "approved"; row["blocked_by"] = "none"
            self.write_requirements(root, row=row, trace="OBJ-001,CS-001,frames,Anchor,SRC-001,proposed\nCS-001,REQ-001,mitigated_by,Origin,SRC-001,proposed\nREQ-001,TST-001,verified_by,Direct test,SRC-001,planned\n")
            stale = json.loads(self.run_cli(SEF, "status", str(project)).stdout)
            self.assertEqual(stale["missing_roles"], ["independent-reviewer", "user"])
            self.run_cli(SEF, "approve", str(project), "--phase", "planning", "--by", "Test User", "--role", "user", "--authority-id", "AUTH-U", "--evidence", "/fixture", "--decision", "approved", "--note", "Real test approval")
            self.run_cli(SEF, "approve", str(project), "--phase", "planning", "--by", "Independent Reviewer", "--role", "independent-reviewer", "--authority-id", "AUTH-R", "--evidence", "/review", "--decision", "approved", "--note", "Real test review")
            ready = json.loads(self.run_cli(SEF, "status", str(project)).stdout)
            self.assertTrue(ready["gate_ready"])
            self.assertEqual(json.loads(self.run_cli(SEF, "advance", str(project)).stdout)["phase"], "execution")
            evidence_files = [p for p in (root / "gates/planning").glob("*.json") if p.name != "latest.json"]
            self.assertGreaterEqual(len(evidence_files), 2)

    def test_create_module_registers_and_scaffolds_material_module(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp) / "project"; root = self.init(project)
            self.set_state(root, "planning", "low")
            (root / "05-planning").mkdir(parents=True, exist_ok=True)
            (root / "05-planning/modules.csv").write_text("module_id,name,path,material,rationale\n", encoding="utf-8")
            self.run_cli(SEF, "create-module", str(project), "--id", "MOD-001", "--name", "Control Module", "--path", "control-module", "--rationale", "Owns control behavior")
            for artifact in ("PRD.md", "SPEC.md", "TESTS.md", "SPRINTS.md", "TASKS.md"):
                self.assertTrue((root / "05-planning/modules/control-module" / artifact).exists())
            duplicate = self.run_cli(SEF, "create-module", str(project), "--id", "MOD-002", "--name", "Duplicate", "--path", "control-module", "--rationale", "Duplicate", ok=False)
            self.assertIn("already exists", duplicate.stderr)


    # --- Halligan metrics -------------------------------------------------

    def test_halligan_irq_rq_qf_and_completeness(self) -> None:
        first = self.quality_row(e5_constraints="0", e6_refinement_source="NA", e7_refinement_destination="NA", iqf2_completeness="0", omission_ratio="1")
        second = self.quality_row(requirement_id="REQ-002", e6_refinement_source="NA", e7_refinement_destination="NA", omission_ratio="3")
        rows = []
        for line, raw in enumerate((first, second), start=2):
            parsed, errors = halligan.parse_row(line, raw)
            self.assertEqual(errors, [])
            rows.append(parsed)
        metrics = halligan.compute_metrics(rows)
        self.assertEqual(metrics["irq"], {"REQ-001": 0.8, "REQ-002": 1.0})
        self.assertAlmostEqual(metrics["rq"], 0.9)
        self.assertEqual(metrics["qf"]["QF1"], 1.0)
        self.assertEqual(metrics["qf"]["QF2"], 0.5)
        self.assertAlmostEqual(metrics["completeness_qf2_prime"], 0.5 - 2.0)  # may be negative
        self.assertAlmostEqual(metrics["rq_primary"], 1.8 / (2 + 4))
        self.assertEqual([c["requirement_id"] for c in metrics["rewrite_candidates"]], ["REQ-001"])
        self.assertEqual(metrics["rewrite_candidates"][0]["failed_elements"], ["e5_constraints"])
        self.assertEqual(halligan.band_for(0.2), "very poor (0.01-0.3): needs substantial development")
        self.assertIn("SRR", halligan.band_for(0.85))
        self.assertIn("critical", halligan.band_for(0.99))

    def test_halligan_rejects_bad_values_zero_applicable_duplicates_and_unknown_ids(self) -> None:
        _, errors = halligan.parse_row(2, self.quality_row(e1_actor="2"))
        self.assertTrue(any("e1_actor" in e for e in errors))
        _, errors = halligan.parse_row(2, self.quality_row(iqf3_consistency="NA"))
        self.assertTrue(any("iqf3_consistency" in e for e in errors))
        _, errors = halligan.parse_row(2, self.quality_row(**{f: "NA" for f in halligan.ELEMENT_FIELDS}))
        self.assertTrue(any("no-applicable-elements" in e for e in errors))
        headers = list(halligan.QUALITY_COLUMNS)
        _, errors = halligan.parse_quality(headers, [self.quality_row(), self.quality_row()], {"REQ-001"})
        self.assertTrue(any("duplicate:REQ-001" in e for e in errors))
        _, errors = halligan.parse_quality(headers, [self.quality_row(requirement_id="REQ-009")], {"REQ-001"})
        self.assertTrue(any("unknown-requirement:REQ-009" in e for e in errors))
        _, errors = halligan.parse_quality(headers[:-2], [], {"REQ-001"})
        self.assertTrue(any("schema:missing" in e for e in errors))

    def test_halligan_cli_reports_missing_rtbd_threshold_and_exit_codes(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp) / "project"; root = self.init(project)
            self.write_requirements(root, row=self.requirement_row(statement="The system shall stop within TBD seconds."))
            absent = self.run_cli(HALLIGAN, str(project), "--json", ok=False)
            self.assertEqual(absent.returncode, 1)
            self.assertEqual(json.loads(absent.stdout)["missing_from_quality"], ["REQ-001"])
            self.write_quality(root, [self.quality_row(e4_object="0", e5_constraints="0")])
            low = self.run_cli(HALLIGAN, str(project), "--json", ok=False)
            self.assertEqual(low.returncode, 2)
            report = json.loads(low.stdout)
            self.assertEqual(report["rtbd_percent"], 100.0)
            self.assertFalse(report["meets_threshold"])
            self.assertEqual(report["missing_from_quality"], [])
            relaxed = self.run_cli(HALLIGAN, str(project), "--threshold", "0.7")
            self.assertIn("meets", relaxed.stdout)
            self.assertIn("Rewrite candidates", relaxed.stdout)
            self.run_cli(HALLIGAN, "--help")

    def test_status_shows_quality_when_quality_csv_exists(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            project, root = self.requirements_gate_project(temp, "low")
            self.assertIsNone(json.loads(self.run_cli(SEF, "status", str(project)).stdout)["quality"])
            self.write_quality(root, [self.quality_row()])
            quality = json.loads(self.run_cli(SEF, "status", str(project)).stdout)["quality"]
            self.assertEqual(quality["rq"], 1.0)
            self.assertIn("QF10", quality["qf"])

    # --- Hard / soft gates ------------------------------------------------

    def test_soft_warning_does_not_advance_then_acknowledgement_advances_and_is_recorded(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            project, root = self.requirements_gate_project(temp, "low")
            self.approve_user(project, "requirements")
            self.write_quality(root, [self.quality_row(e4_object="0", e5_constraints="0", rewrite="Add a time limit")])
            warned = self.run_cli(SEF, "advance", str(project), ok=False)
            self.assertEqual(warned.returncode, 2)
            payload = json.loads(warned.stdout)
            warning = payload["warnings"][0]
            self.assertEqual(warning["code"], "rq-below-threshold")
            self.assertEqual(warning["severity"], "soft")
            self.assertTrue(any("REQ-001" in item for item in warning["details"]))
            self.assertGreaterEqual(len(warning["alternatives"]), 3)
            self.assertEqual(json.loads((root / "state.json").read_text(encoding="utf-8"))["phase"], "requirements")
            self.assertEqual(self.history(root)[-1]["kind"], "advance-warned")
            warned_files = list((root / "gates/requirements").glob("*-warned.json"))
            self.assertEqual(len(warned_files), 1)
            status = json.loads(self.run_cli(SEF, "status", str(project)).stdout)
            self.assertEqual(status["hard_blockers"], [])
            self.assertEqual(status["warnings"][0]["code"], "rq-below-threshold")
            self.assertIn("rq-below-threshold", status["alternatives"])
            self.assertFalse(status["gate_ready"])
            self.run_cli(SEF, "advance", str(project), "--acknowledge-warnings", "   ", ok=False)
            advanced = json.loads(self.run_cli(SEF, "advance", str(project), "--acknowledge-warnings", "User accepts rework risk").stdout)
            self.assertEqual(advanced["phase"], "planning")
            last = self.history(root)[-1]
            self.assertEqual(last["kind"], "phase-advanced")
            self.assertEqual(last["acknowledged_codes"], ["rq-below-threshold", "rq-addendum-below-threshold"])
            self.assertEqual(last["acknowledgement"], "User accepts rework risk")
            self.assertTrue(last["acknowledged_at"])

    def test_missing_quality_csv_is_soft_in_low_and_hard_in_safety_critical(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            project, root = self.requirements_gate_project(temp, "low")
            self.approve_user(project, "requirements")
            warned = json.loads(self.run_cli(SEF, "advance", str(project), ok=False).stdout)
            self.assertEqual(warned["warnings"][0]["code"], "quality-missing")
        with tempfile.TemporaryDirectory() as temp:
            auth = "AUTH-U,Test User,user,all,/fixture,active\nAUTH-D,Domain Expert,domain-expert,all,/d,active\nAUTH-S,Safety Authority,safety-authority,all,/s,active\n"
            project, root = self.requirements_gate_project(temp, "safety-critical", auth)
            self.approve_user(project, "requirements")
            for who, role, ident, ev in (("Domain Expert", "domain-expert", "AUTH-D", "/d"), ("Safety Authority", "safety-authority", "AUTH-S", "/s")):
                self.run_cli(SEF, "approve", str(project), "--phase", "requirements", "--by", who, "--role", role, "--authority-id", ident, "--evidence", ev, "--decision", "approved", "--note", "ok")
            self.write_quality(root, [self.quality_row(e4_object="0", e5_constraints="0")])
            blocked = self.run_cli(SEF, "advance", str(project), "--acknowledge-warnings", "try", ok=False)
            self.assertEqual(blocked.returncode, 1)
            self.assertIn("rq-below-threshold", blocked.stderr)
            # v2: the addendum RQ is always SOFT (informs), the simple RQ stays HARD
            self.assertEqual([w["code"] for w in json.loads(blocked.stdout)["warnings"]], ["rq-addendum-below-threshold"])

    def test_high_risk_missing_domain_expert_is_hard_and_lists_alternatives(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            project, root = self.requirements_gate_project(temp, "high")
            self.write_quality(root, [self.quality_row()])
            self.approve_user(project, "requirements")
            blocked = self.run_cli(SEF, "advance", str(project), "--acknowledge-warnings", "skip it", ok=False)
            self.assertEqual(blocked.returncode, 1)
            self.assertIn("missing-role:domain-expert", blocked.stderr)
            alternatives = json.loads(blocked.stdout)["alternatives"]
            self.assertTrue(alternatives["missing-role:domain-expert"])
            self.assertEqual(json.loads((root / "state.json").read_text(encoding="utf-8"))["phase"], "requirements")

    def test_stpa_step_registry_without_decision_is_soft_and_hard_in_safety_critical(self) -> None:
        table = (
            "\n## Registro de etapas\n\n| Etapa | Prompt/entrada | Saida | Decisao | Aprovador | Data |\n|---|---|---|---|---|---|\n"
            "| 1 | p | o | approved | Test User | 2026-10-17 |\n| 2 | p | o |  |  |  |\n"
        )
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp) / "project"; root = self.init(project)
            self.fill_intake(root); self.fill_markdown_phases(root, "stpa"); self.set_state(root, "stpa", "low")
            path = root / "03-stpa/stpa-analysis.md"
            path.write_text(path.read_text(encoding="utf-8") + table, encoding="utf-8")
            self.approve_user(project, "stpa")
            warned = self.run_cli(SEF, "advance", str(project), ok=False)
            self.assertEqual(warned.returncode, 2)
            self.assertEqual(json.loads(warned.stdout)["warnings"][0]["code"], "stpa-step-undecided")
        with tempfile.TemporaryDirectory() as temp:
            auth = "AUTH-U,Test User,user,all,/fixture,active\nAUTH-D,Domain Expert,domain-expert,all,/d,active\nAUTH-S,Safety Authority,safety-authority,all,/s,active\n"
            project = Path(temp) / "project"; root = self.init(project)
            self.fill_intake(root, auth); self.fill_markdown_phases(root, "stpa"); self.set_state(root, "stpa", "safety-critical")
            path = root / "03-stpa/stpa-analysis.md"
            path.write_text(path.read_text(encoding="utf-8") + table, encoding="utf-8")
            self.approve_user(project, "stpa")
            for who, role, ident, ev in (("Domain Expert", "domain-expert", "AUTH-D", "/d"), ("Safety Authority", "safety-authority", "AUTH-S", "/s")):
                self.run_cli(SEF, "approve", str(project), "--phase", "stpa", "--by", who, "--role", role, "--authority-id", ident, "--evidence", ev, "--decision", "approved", "--note", "ok")
            blocked = self.run_cli(SEF, "advance", str(project), ok=False)
            self.assertEqual(blocked.returncode, 1)
            self.assertIn("stpa-step-undecided", blocked.stderr)

    def test_template_stpa_has_seven_step_registry(self) -> None:
        template = (ROOT / ".agents/skills/systemic-engineering/assets/templates/STPA.md").read_text(encoding="utf-8")
        self.assertIn("Registro de etapas", template)
        for step in range(1, 6):
            self.assertIn(f"| {step} |", template)
        self.assertNotIn("| 6 |", template)
        self.assertIn("requirements-log.md", template)
        log = (ROOT / ".agents/skills/systemic-engineering/assets/templates/REQUIREMENTS-LOG.md").read_text(encoding="utf-8")
        for needle in ("Step 6", "Step 6b", "Step 7", "| 6 |", "| 7 |", "Etapa"):
            self.assertIn(needle, log)

    # --- Schema alignment and traceability ------------------------------------

    def test_sef_schema_requires_level_and_type_and_trace_accepts_empty_blocked_and_decisions(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp) / "project"; root = self.init(project)
            self.fill_intake(root); self.fill_markdown_phases(root, "stpa")
            self.write_requirements(root, row=self.requirement_row(blocked_by="", decision_ids=""))
            self.set_state(root, "requirements", "low")
            self.assertTrue(json.loads(self.run_cli(TRACE, str(project)).stdout)["ok"])
            path = root / "04-requirements/requirements.csv"
            lines = path.read_text(encoding="utf-8").splitlines()
            header = [h for h in lines[0].split(",") if h not in {"level", "type"}]
            path.write_text(",".join(header) + "\n", encoding="utf-8")
            result = self.run_cli(SEF, "validate", str(project), ok=False)
            self.assertIn("schema:04-requirements/requirements.csv:missing:level,type", result.stdout)

    def test_zero_requirements_note_and_error_after_requirements_phase(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp) / "project"; root = self.init(project)
            self.set_state(root, "vft", "low")
            result = json.loads(self.run_cli(TRACE, str(project)).stdout)
            self.assertIn("not applicable before the requirements phase", result["note"])
            self.assertFalse(result["applicable"])
            self.set_state(root, "planning", "low")
            late = self.run_cli(TRACE, str(project), ok=False)
            self.assertIn("no-requirements-after-requirements-phase", late.stdout)

    def test_origin_column_is_validated_when_present(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp) / "project"; root = self.init(project)
            self.fill_intake(root); self.fill_markdown_phases(root, "stpa")
            fields = [*REQ_FIELDS, "origin"]
            for origin, expected_ok in (("UCA-001", True), ("", False), ("UCA-777", False)):
                self.write_requirements(root)
                with (root / "04-requirements/requirements.csv").open("w", newline="", encoding="utf-8") as handle:
                    writer = csv.DictWriter(handle, fieldnames=fields)
                    writer.writeheader(); writer.writerow({**self.requirement_row(), "origin": origin})
                self.set_state(root, "requirements", "low")
                result = self.run_cli(TRACE, str(project), ok=expected_ok)
                if not expected_ok:
                    self.assertIn("origin", result.stdout)

    # --- v2: completeness beyond STPA ------------------------------------------

    SC_AUTH = (
        "AUTH-U,Test User,user,all,/fixture,active\nAUTH-D,Domain Expert,domain-expert,all,/d,active\n"
        "AUTH-S,Safety Authority,safety-authority,all,/s,active\nAUTH-R,Independent Reviewer,independent-reviewer,all,/r,active\n"
    )

    def approve_all(self, project: Path, phase: str) -> None:
        self.approve_user(project, phase)
        for who, role, ident, ev in (("Domain Expert", "domain-expert", "AUTH-D", "/d"), ("Safety Authority", "safety-authority", "AUTH-S", "/s")):
            self.run_cli(SEF, "approve", str(project), "--phase", phase, "--by", who, "--role", role, "--authority-id", ident, "--evidence", ev, "--decision", "approved", "--note", "ok")

    def write_requirement_rows(self, root: Path, rows: list[dict[str, str]]) -> None:
        directory = root / "04-requirements"
        with (directory / "requirements.csv").open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=REQ_FIELDS)
            writer.writeheader(); writer.writerows(rows)
        trace = "from_id,to_id,relationship,rationale,source_id,status\nOBJ-001,CS-001,frames,Anchor,SRC-001,proposed\n"
        trace += "".join(f"CS-001,{row['requirement_id']},mitigated_by,Origin,SRC-001,proposed\n" for row in rows)
        (directory / "traceability.csv").write_text(trace, encoding="utf-8")

    def typed_rows(self, spec: dict[str, int], status: str = "approved") -> list[dict[str, str]]:
        rows, index = [], 1
        for kind, count in spec.items():
            for _ in range(count):
                rows.append(self.requirement_row(requirement_id=f"REQ-{index:03d}", type=kind, status=status)); index += 1
        return rows

    def warning_codes(self, project: Path) -> list[str]:
        result = self.run_cli(SEF, "advance", str(project), ok=False)
        return [w["code"] for w in json.loads(result.stdout).get("warnings", [])]

    def test_halligan_type_mix_and_completeness_hints(self) -> None:
        def rows(spec: dict[str, int]) -> list[dict[str, str]]:
            return [{"type": kind} for kind, count in spec.items() for _ in range(count)]
        mix = halligan.type_mix(rows({"functional": 6, "interface": 3, "performance": 1}))
        self.assertEqual(mix["total"], 10)
        self.assertEqual(mix["by_type"]["functional"], {"count": 6, "percent": 60.0})
        self.assertEqual(mix["groups"]["interface"]["percent"], 30.0)
        self.assertEqual(mix["groups"]["other"]["count"], 1)
        codes = [h["code"] for h in halligan.completeness_hints(mix)]
        self.assertEqual(codes, ["functional-interface-gap"])  # 60 vs 30; other = 10% is inside 5-10
        balanced = halligan.type_mix(rows({"functional": 46, "interface": 44, "quality": 5, "performance": 5}))
        self.assertEqual(halligan.completeness_hints(balanced), [])
        low = halligan.type_mix(rows({"functional": 10, "interface": 10}))
        self.assertEqual([h["code"] for h in halligan.completeness_hints(low)], ["other-qualities-low"])
        high = halligan.type_mix(rows({"functional": 5, "interface": 5, "quality": 4}))
        self.assertEqual([h["code"] for h in halligan.completeness_hints(high)], ["other-qualities-high"])
        self.assertEqual(halligan.completeness_hints(halligan.type_mix(rows({"safety": 4}))), [])  # only STPA-derived: no 6b yet
        large = halligan.type_mix(rows({"functional": 60, "interface": 60}))
        self.assertEqual(halligan.completeness_hints(large), [])  # >100 requirements: no 5-10% rule

    def test_halligan_cli_reports_type_mix_and_hints(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            project, root = self.requirements_gate_project(temp, "low")
            self.write_requirement_rows(root, self.typed_rows({"functional": 9, "interface": 1}))
            report = json.loads(self.run_cli(HALLIGAN, str(project), "--json", ok=False).stdout)
            self.assertEqual(report["type_mix"]["by_type"]["functional"]["count"], 9)
            self.assertIn("functional-interface-gap", [h["code"] for h in report["completeness_hints"]])

    def test_completeness_mix_warning_is_soft_in_every_class(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            project, root = self.requirements_gate_project(temp, "low")
            self.write_requirement_rows(root, self.typed_rows({"functional": 9, "interface": 1}))
            self.write_quality(root, [self.quality_row(requirement_id=f"REQ-{i:03d}") for i in range(1, 11)])
            self.approve_user(project, "requirements")
            result = json.loads(self.run_cli(SEF, "advance", str(project), ok=False).stdout)
            warning = next(w for w in result["warnings"] if w["code"] == "completeness-mix")
            self.assertTrue(any("interface" in alt for alt in warning["alternatives"]))
        with tempfile.TemporaryDirectory() as temp:
            project, root = self.requirements_gate_project(temp, "safety-critical", self.SC_AUTH)
            self.write_requirement_rows(root, self.typed_rows({"functional": 9, "interface": 1}))
            self.write_quality(root, [self.quality_row(requirement_id=f"REQ-{i:03d}") for i in range(1, 11)])
            self.approve_all(project, "requirements")
            result = self.run_cli(SEF, "advance", str(project), ok=False)
            self.assertEqual(result.returncode, 2)  # informs, does not block
            payload = json.loads(result.stdout)
            self.assertEqual(payload["hard_blockers"], [])
            self.assertIn("completeness-mix", [w["code"] for w in payload["warnings"]])

    def test_objective_uncovered_warns_and_written_out_of_scope_decision_covers_it(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            project, root = self.requirements_gate_project(temp, "low")
            vft = root / "01-vft/vft-baseline.md"
            vft.write_text(vft.read_text(encoding="utf-8") + "\nAlso OBJ-002 accessibility objective.\n", encoding="utf-8")
            self.write_quality(root, [self.quality_row()])
            self.approve_user(project, "requirements")
            result = json.loads(self.run_cli(SEF, "advance", str(project), ok=False).stdout)
            warning = next(w for w in result["warnings"] if w["code"] == "objective-uncovered")
            self.assertIn("OBJ-002", " ".join(warning["details"]))
            self.assertTrue(any("fora do escopo" in alt or "out of scope" in alt for alt in warning["alternatives"]))
            self.assertNotIn("OBJ-001", " ".join(warning["details"]))
            (root / "04-requirements/decisions.csv").write_text(
                "decision_id,title,status,owner,authority_id,evidence,affected_ids,rationale\n"
                "DEC-001,Fixture decision,approved,STK-001,AUTH-U,/fixture,REQ-001,Supports deterministic fixture\n"
                "DEC-002,OBJ-002 fora do escopo,approved,STK-001,AUTH-U,/fixture,OBJ-002,Accessibility deferred to release 2\n",
                encoding="utf-8",
            )
            self.approve_user(project, "requirements")
            self.assertEqual(json.loads(self.run_cli(SEF, "advance", str(project)).stdout)["phase"], "planning")

    def test_rq_addendum_below_threshold_is_soft_in_all_classes(self) -> None:
        rows = [self.quality_row(omission_ratio="0.5")]  # RQ = 1.0, primary = 1 / 1.5
        with tempfile.TemporaryDirectory() as temp:
            project, root = self.requirements_gate_project(temp, "low")
            self.write_quality(root, rows); self.approve_user(project, "requirements")
            warning = next(w for w in json.loads(self.run_cli(SEF, "advance", str(project), ok=False).stdout)["warnings"] if w["code"] == "rq-addendum-below-threshold")
            self.assertEqual(warning["severity"], "soft")
            self.assertGreaterEqual(len(warning["alternatives"]), 3)
        with tempfile.TemporaryDirectory() as temp:
            project, root = self.requirements_gate_project(temp, "safety-critical", self.SC_AUTH)
            self.write_quality(root, rows); self.approve_all(project, "requirements")
            result = self.run_cli(SEF, "advance", str(project), ok=False)
            self.assertEqual(result.returncode, 2)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["hard_blockers"], [])
            self.assertEqual([w["code"] for w in payload["warnings"]], ["rq-addendum-below-threshold"])

    def test_pending_requirements_high_over_five_percent(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            project, root = self.requirements_gate_project(temp, "low")
            rows = self.typed_rows({"functional": 10, "interface": 10})
            self.write_requirement_rows(root, [{**rows[0], "status": "proposed"}, *rows[1:]])  # exactly 5%: not above
            self.write_quality(root, [self.quality_row(requirement_id=r["requirement_id"]) for r in rows])
            self.approve_user(project, "requirements")
            self.assertNotIn("pending-requirements-high", self.warning_codes(project))
            self.write_requirement_rows(root, [{**rows[0], "status": "proposed"}, {**rows[1], "status": "draft"}, *rows[2:]])
            self.approve_user(project, "requirements")
            result = json.loads(self.run_cli(SEF, "advance", str(project), ok=False).stdout)
            warning = next(w for w in result["warnings"] if w["code"] == "pending-requirements-high")
            self.assertTrue(any("pending" in alt for alt in warning["alternatives"]))

    # --- v2: pending command -----------------------------------------------------

    def pending_project(self, temp: str) -> tuple[Path, Path]:
        project, root = self.requirements_gate_project(temp, "low")
        rows = [
            self.requirement_row(requirement_id="REQ-001", status="blocked", blocked_by="DEC-010", decision_ids="DEC-010", owner="STK-001"),
            self.requirement_row(requirement_id="REQ-002", status="proposed", decision_ids="DEC-010"),
            self.requirement_row(requirement_id="REQ-003", status="approved", statement="The system shall respond within TBD seconds."),
            self.requirement_row(requirement_id="REQ-004", status="draft", decision_ids="", blocked_by=""),
            self.requirement_row(requirement_id="REQ-005", status="approved"),
        ]
        self.write_requirement_rows(root, rows)
        (root / "04-requirements/decisions.csv").write_text(
            "decision_id,title,status,owner,authority_id,evidence,affected_ids,rationale\n"
            "DEC-001,Fixture decision,approved,STK-001,AUTH-U,/fixture,REQ-005,ok\n"
            "DEC-010,Choose response time,pending,Test User,AUTH-U,/fixture,REQ-001,Needs the user\n",
            encoding="utf-8",
        )
        return project, root

    def test_pending_lists_one_grouped_question_list_and_exits_2(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            project, root = self.pending_project(temp)
            text = self.run_cli(SEF, "pending", str(project), ok=False)
            self.assertEqual(text.returncode, 2)
            for needle in ("DEC-010", "Choose response time", "REQ-001", "REQ-002", "REQ-003", "REQ-004", "Test User"):
                self.assertIn(needle, text.stdout)
            payload = json.loads(self.run_cli(SEF, "pending", str(project), "--json", ok=False).stdout)
            by_id = {q["id"]: q for q in payload["questions"]}
            self.assertEqual(sorted(by_id["DEC-010"]["requirements"]), ["REQ-001", "REQ-002"])
            self.assertEqual(by_id["DEC-010"]["authority"], "Test User")
            self.assertIn("REQ-004", by_id)  # no decision: the requirement itself is the question
            self.assertTrue(any(q["type"] == "tbd" and q["requirements"] == ["REQ-003"] for q in payload["questions"]))
            self.assertNotIn("REQ-005", json.dumps(payload["questions"]))
            self.assertFalse((root / "04-requirements/pending-questions.md").exists())

    def test_pending_exits_0_when_clean_and_write_respects_user_marker(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            project, root = self.pending_project(temp)
            self.run_cli(SEF, "pending", str(project), "--write", ok=False)
            target = root / "04-requirements/pending-questions.md"
            self.assertIn("DEC-010", target.read_text(encoding="utf-8"))
            target.write_text("# Mine\n\n@user keep this answer\n", encoding="utf-8")
            result = self.run_cli(SEF, "pending", str(project), "--write", "--json", ok=False)
            self.assertEqual(target.read_text(encoding="utf-8"), "# Mine\n\n@user keep this answer\n")
            self.assertIn("@user", json.loads(result.stdout)["write_skipped"])
        with tempfile.TemporaryDirectory() as temp:
            project, root = self.requirements_gate_project(temp, "low")
            clean = self.run_cli(SEF, "pending", str(project))
            self.assertEqual(clean.returncode, 0)

    # --- v2: STPA step registry split between gates --------------------------------

    def test_steps_1_to_5_checked_at_stpa_gate_and_6_7_at_requirements_gate(self) -> None:
        table = (
            "\n## Registro de etapas\n\n| Etapa | Prompt/entrada | Saida | Decisao | Aprovador | Data |\n|---|---|---|---|---|---|\n"
            + "".join(f"| {n} | p | o | approved | Test User | 2026-10-17 |\n" for n in range(1, 6))
            + "| 6 | p | o |  |  |  |\n| 7 | p | o |  |  |  |\n"
        )
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp) / "project"; root = self.init(project)
            self.fill_intake(root); self.fill_markdown_phases(root, "stpa"); self.set_state(root, "stpa", "low")
            path = root / "03-stpa/stpa-analysis.md"
            path.write_text(path.read_text(encoding="utf-8") + table, encoding="utf-8")
            self.approve_user(project, "stpa")
            self.assertEqual(json.loads(self.run_cli(SEF, "advance", str(project)).stdout)["phase"], "requirements")
            self.write_requirements(root)
            self.write_quality(root, [self.quality_row()])
            self.approve_user(project, "requirements")
            result = json.loads(self.run_cli(SEF, "advance", str(project), ok=False).stdout)
            warning = next(w for w in result["warnings"] if w["code"] == "stpa-step-undecided")
            self.assertIn("6,7", " ".join(warning["details"]))
        with tempfile.TemporaryDirectory() as temp:
            project, root = self.requirements_gate_project(temp, "safety-critical", self.SC_AUTH)
            (root / "04-requirements/requirements-log.md").write_text(self.log_text("", ""), encoding="utf-8")
            self.write_quality(root, [self.quality_row()]); self.approve_all(project, "requirements")
            blocked = self.run_cli(SEF, "advance", str(project), ok=False)
            self.assertEqual(blocked.returncode, 1)
            self.assertIn("stpa-step-undecided", blocked.stderr)

    # --- v2: stale upstream approvals ------------------------------------------------

    def advance_to_requirements(self, temp: str, risk: str = "low") -> tuple[Path, Path]:
        project = Path(temp) / "project"; root = self.init(project)
        self.fill_intake(root); self.fill_markdown_phases(root, "stpa"); self.set_state(root, "stpa", risk)
        self.approve_user(project, "stpa")
        self.run_cli(SEF, "advance", str(project))
        self.write_requirements(root); self.write_quality(root, [self.quality_row()])
        return project, root

    def test_stale_approvals_listed_and_warned_on_advance(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            project, root = self.advance_to_requirements(temp)
            self.assertEqual(json.loads(self.run_cli(SEF, "status", str(project)).stdout)["stale_approvals"], [])
            stpa = root / "03-stpa/stpa-analysis.md"
            stpa.write_text(stpa.read_text(encoding="utf-8") + "\nEdited after approval.\n", encoding="utf-8")
            status = json.loads(self.run_cli(SEF, "status", str(project)).stdout)
            self.assertEqual(status["stale_approvals"], [{"phase": "stpa", "files": ["03-stpa/stpa-analysis.md"]}])
            validated = json.loads(self.run_cli(SEF, "validate", str(project)).stdout)
            self.assertEqual(validated["stale_approvals"][0]["phase"], "stpa")
            self.approve_user(project, "requirements")
            warning = next(w for w in json.loads(self.run_cli(SEF, "advance", str(project), ok=False).stdout)["warnings"] if w["code"] == "upstream-artifact-changed")
            self.assertIn("03-stpa/stpa-analysis.md", " ".join(warning["details"]))
            self.assertTrue(any("reopen" in alt for alt in warning["alternatives"]))
        self.assertEqual(sef_module.severity("upstream-artifact-changed", "low"), "soft")
        self.assertEqual(sef_module.severity("upstream-artifact-changed", "high"), "soft")
        self.assertEqual(sef_module.severity("upstream-artifact-changed", "safety-critical"), "hard")

    # --- v2.1: steps 6, 6b and 7 live in the requirements phase ----------------

    def test_requirements_log_is_scaffolded_and_written_without_stale_upstream_warning(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            project, root = self.advance_to_requirements(temp)
            log = root / "04-requirements/requirements-log.md"
            self.assertTrue(log.exists())  # copied from the template on entering the phase
            log.write_text(self.log_text(), encoding="utf-8")
            self.approve_user(project, "requirements")
            status = json.loads(self.run_cli(SEF, "status", str(project)).stdout)
            self.assertEqual(status["stale_approvals"], [])
            self.assertIn("04-requirements/requirements-log.md", status["required_artifacts"])
            result = self.run_cli(SEF, "advance", str(project))
            self.assertEqual(json.loads(result.stdout)["phase"], "planning")

    def test_requirements_gate_reads_steps_6_7_from_log_with_legacy_fallback(self) -> None:
        legacy = (
            "\n## Step 6 - Requirements (legacy layout)\n\n## Registro de etapas\n\n| Etapa | Prompt/entrada | Saida | Decisao | Aprovador | Data |\n|---|---|---|---|---|---|\n"
            "| 6 | p | o |  |  |  |\n| 7 | p | o | approved | Test User | 2026-10-18 |\n"
        )
        with tempfile.TemporaryDirectory() as temp:  # legacy project: no requirements-log.md, steps in stpa-analysis.md
            project, root = self.requirements_gate_project(temp, "low")
            (root / "04-requirements/requirements-log.md").unlink()
            stpa = root / "03-stpa/stpa-analysis.md"
            stpa.write_text(stpa.read_text(encoding="utf-8") + legacy, encoding="utf-8")
            self.write_quality(root, [self.quality_row()]); self.approve_user(project, "requirements")
            self.assertEqual(self.run_cli(SEF, "validate", str(project)).returncode, 0)  # absent log is not an error
            warning = next(w for w in json.loads(self.run_cli(SEF, "advance", str(project), ok=False).stdout)["warnings"] if w["code"] == "stpa-step-undecided")
            self.assertEqual(warning["details"], ["6"])
        with tempfile.TemporaryDirectory() as temp:  # the log wins over stale rows in stpa-analysis.md
            project, root = self.requirements_gate_project(temp, "low")
            stpa = root / "03-stpa/stpa-analysis.md"
            stpa.write_text(stpa.read_text(encoding="utf-8") + legacy, encoding="utf-8")
            self.write_quality(root, [self.quality_row()]); self.approve_user(project, "requirements")
            self.assertEqual(json.loads(self.run_cli(SEF, "advance", str(project)).stdout)["phase"], "planning")

    def test_missing_role_warning_lists_role_and_registered_candidates(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            project, root = self.requirements_gate_project(temp, "medium", "AUTH-U,Test User,user,all,/fixture,active\nAUTH-R,Independent Reviewer,independent-reviewer,requirements,/review,active\n")
            self.write_quality(root, [self.quality_row()]); self.approve_user(project, "requirements")
            warning = next(w for w in json.loads(self.run_cli(SEF, "advance", str(project), ok=False).stdout)["warnings"] if w["code"] == "missing-role:independent-reviewer")
            text = " ".join(warning["details"])
            self.assertIn("independent-reviewer", text)
            self.assertIn("AUTH-R", text)
        with tempfile.TemporaryDirectory() as temp:
            project, root = self.requirements_gate_project(temp, "medium")
            self.write_quality(root, [self.quality_row()]); self.approve_user(project, "requirements")
            warning = next(w for w in json.loads(self.run_cli(SEF, "advance", str(project), ok=False).stdout)["warnings"] if w["code"] == "missing-role:independent-reviewer")
            self.assertIn("no registered", " ".join(warning["details"]))

    def test_rtbd_counts_tbd_blocked_status_and_blocked_by(self) -> None:
        rows = [
            {"statement": "The system shall react within TBD s.", "status": "approved", "blocked_by": ""},
            {"statement": "A", "status": "blocked", "blocked_by": ""},
            {"statement": "B", "status": "proposed", "blocked_by": "DEC-010"},
            {"statement": "C", "status": "approved", "blocked_by": "none"},
        ]
        self.assertEqual(halligan.rtbd_percent(rows), 75.0)

    def test_pending_does_not_repeat_tbd_requirement_already_under_a_decision(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            project, root = self.requirements_gate_project(temp, "low")
            rows = [self.requirement_row(requirement_id="REQ-001", status="blocked", blocked_by="DEC-010", decision_ids="DEC-010", statement="The system shall respond within TBD seconds.")]
            self.write_requirement_rows(root, rows)
            (root / "04-requirements/decisions.csv").write_text(
                "decision_id,title,status,owner,authority_id,evidence,affected_ids,rationale\n"
                "DEC-010,Choose response time,pending,Test User,AUTH-U,/fixture,REQ-001,Needs the user\n", encoding="utf-8")
            payload = json.loads(self.run_cli(SEF, "pending", str(project), "--json", ok=False).stdout)
            self.assertEqual([q["id"] for q in payload["questions"]], ["DEC-010"])

    # --- v2: reopen ---------------------------------------------------------------------

    def reopen(self, project: Path, *extra: str, ok: bool = True) -> subprocess.CompletedProcess[str]:
        return self.run_cli(SEF, "reopen", str(project), *extra, ok=ok)

    def test_reopen_returns_phase_keeps_work_and_supersedes_approvals(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            project, root = self.advance_to_requirements(temp)
            (root / "04-requirements/requirements-log.md").write_text(self.log_text(), encoding="utf-8")
            self.approve_user(project, "requirements")
            self.assertEqual(json.loads(self.run_cli(SEF, "advance", str(project)).stdout)["phase"], "planning")
            self.assertTrue((root / "05-planning/system/PRD.md").exists())
            self.reopen(project, "--phase", "requirements", "--by", "Test User", "--reason", "Missing interface requirements")
            state = json.loads((root / "state.json").read_text(encoding="utf-8"))
            self.assertEqual(state["phase"], "requirements")
            event = self.history(root)[-1]
            self.assertEqual((event["kind"], event["from_phase"], event["to_phase"]), ("reopened", "planning", "requirements"))
            self.assertEqual((event["by"], event["reason"]), ("Test User", "Missing interface requirements"))
            files = list((root / "gates/planning").glob("*-reopened.json"))
            self.assertEqual(len(files), 1)
            self.assertEqual(json.loads(files[0].read_text(encoding="utf-8"))["outcome"], "reopened")
            self.assertTrue((root / "05-planning/system/PRD.md").exists())  # nothing deleted
            self.assertEqual([a["phase"] for a in state["approvals"]], ["stpa", "requirements"])
            self.assertTrue(state["approvals"][1]["superseded"])
            self.assertFalse(state["approvals"][0].get("superseded", False))
            status = json.loads(self.run_cli(SEF, "status", str(project)).stdout)
            self.assertEqual(status["reopened_from"], "planning")
            self.assertEqual(status["superseded_phases"], ["requirements"])
            self.assertIn("user", status["missing_roles"])  # superseded approvals do not count
            self.assertFalse(status["gate_ready"])
            self.approve_user(project, "requirements")
            self.assertEqual(json.loads(self.run_cli(SEF, "advance", str(project)).stdout)["phase"], "planning")

    def test_reopen_validates_arguments(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            project, root = self.advance_to_requirements(temp)
            self.assertIn("reason", self.reopen(project, "--phase", "stpa", "--by", "Test User", "--reason", "  ", ok=False).stderr)
            self.assertIn("--by", self.reopen(project, "--phase", "stpa", "--by", " ", "--reason", "x", ok=False).stderr)
            self.assertIn("unknown phase", self.reopen(project, "--phase", "nowhere", "--by", "Test User", "--reason", "x", ok=False).stderr)
            self.assertIn("later than", self.reopen(project, "--phase", "planning", "--by", "Test User", "--reason", "x", ok=False).stderr)
            self.assertEqual(json.loads((root / "state.json").read_text(encoding="utf-8"))["phase"], "requirements")
            self.reopen(project, "--phase", "requirements", "--by", "Test User", "--reason", "same phase redo")  # equal phase is allowed

    def test_reopen_execution_in_safety_critical_requires_authorized_role(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp) / "project"; root = self.init(project)
            self.fill_intake(root, self.SC_AUTH); self.fill_markdown_phases(root, "stpa"); self.write_requirements(root)
            self.set_state(root, "execution", "safety-critical")
            denied = self.reopen(project, "--phase", "planning", "--by", "Test User", "--reason", "x", ok=False)
            self.assertIn("safety-authority", denied.stderr)
            wrong = self.reopen(project, "--phase", "planning", "--by", "Test User", "--by-role", "user", "--reason", "x", ok=False)
            self.assertNotEqual(wrong.returncode, 0)
            self.reopen(project, "--phase", "planning", "--by", "Safety Authority", "--by-role", "safety-authority", "--reason", "Hazard found in operation")
            event = self.history(root)[-1]
            self.assertEqual(event["reopen_requires"], ["safety-authority", "domain-expert"])
            self.assertEqual(json.loads((root / "state.json").read_text(encoding="utf-8"))["phase"], "planning")

    def test_templates_and_docs_describe_step_6b(self) -> None:
        base = ROOT / ".agents/skills/systemic-engineering"
        self.assertIn("6b", (base / "assets/templates/STPA.md").read_text(encoding="utf-8"))
        self.assertIn("6b", (base / "references/stpa-requirements.md").read_text(encoding="utf-8"))
        skill = (base / "SKILL.md").read_text(encoding="utf-8")
        for needle in ("6b", "sef.py pending", "sef.py reopen"):
            self.assertIn(needle, skill)


if __name__ == "__main__":
    unittest.main()
