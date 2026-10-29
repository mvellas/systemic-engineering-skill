---
name: systemic-engineering
description: Investigate and develop business, software and systems projects through Intake, VFT, SSM, STPA, evidence-led research, feasibility analysis, multi-agent experiments, traceable requirements and human-gated delivery. Use for consequential discovery, market or investment decisions, requirements and supervised implementation; not for a trivial one-file edit.
metadata:
  short-description: Evidence-led engineering and business decisions
---

## For future Claude
Portable entrypoint for the phase-gated Systemic Engineering Framework. Route by current state and load only the reference needed for that phase.

# Systemic Engineering

Turn an ambiguous project into traceable evidence and controlled execution. Keep facts, stakeholder judgments, model proposals, deterministic checks, and human approvals distinct.

## Start

1. If the target already contains `.systemic-engineering/state.json`, run:

   ```bash
   python3 <skill-dir>/scripts/sef.py status <project-dir>
   ```

   Resume the reported phase. Do not recreate or silently advance state.

2. Otherwise read [workflow.md](references/workflow.md), discuss scope, evidence authorities, failure modes, outputs, and risk class. Initialize only after the user agrees:

   ```bash
   python3 <skill-dir>/scripts/sef.py init <project-dir> --name "<project-name>"
   ```

3. For high-impact or safety-critical work, require a qualified human authority. The skill may structure analysis and evidence; it may not certify safety, legal compliance, medical suitability, or financial suitability.

## Phase router

Load only the reference for the current phase:

| Phase | Read |
|---|---|
| `intake` | [workflow.md](references/workflow.md), [evidence.md](references/evidence.md) |
| `vft` | [vft-interview.md](references/vft-interview.md) |
| `ssm` or `reconcile` | [ssm.md](references/ssm.md) |
| `stpa` or `requirements` | [stpa-requirements.md](references/stpa-requirements.md) (7-step STPA of Aula 10, step 6b for requirements outside STPA, and Halligan quality) |
| `planning` | [artifacts.md](references/artifacts.md) |
| `execution` or `closure` | [multi-agent-judge.md](references/multi-agent-judge.md) |

For theoretical provenance or deeper RAG, use [source-map.md](references/source-map.md) and retrieve only the named source note.

## Evidence-led consulting extension

For business/consulting investigations, executable interviews, OSINT, decision comparison, experiments or client deliverables, read [consulting-workflow.md](references/consulting-workflow.md). Enable the optional module with `sef.py consult enable <project>` only in the intended project; existing projects remain compatible without it. Follow [scientific-method.md](references/scientific-method.md) for claim-level external provenance and [simulation-engines.md](references/simulation-engines.md) for engine selection, actual capability limits and authorization.

Use `consult next` to drive progressive questions and research; perform available public research through the current harness, register concrete external evidence, author business-specific analyses and resolve contradictions. Internal templates and generated reports are not external proof. The client needs clear decisions, alternatives, charts, actions, owners and dates, with technical theory in annexes.

Use the 22 [general document models](references/biblioteca-documental-generalista/INDICE.md) for applicable business documents. Generate both human outputs with `consult report`; inspect `consult quality` and interpret every persisted simulation. An empty template, engine smoke, completed process or structurally valid document is never a completed client study. Do not turn general recommendations from a template into facts.

Method review, original phase approval, specific experiment execution and final client review remain different acts. New simulation grants are hash-bound and one-use; fixture approval cannot authorize a real external or costly run. Changes in consultation data participate in existing phase hashes. Without a terminal, prepare a reproducible executor packet and say that it was not executed.

## Market, feasibility and multi-agent campaigns

For launch, pricing, expansion or investment decisions, read [market-feasibility.md](references/market-feasibility.md) and [agent-experiments.md](references/agent-experiments.md). Connect demand and agent behavior to capacity and cash; separate operating result, liquidity and return on investment. Use explicit sources and assumptions for price response, discounting and payment delays.

Distinguish repeated seeds, market conditions and alternative behavioral structures. Prepare `sim plan`, register the intended campaign with `sim campaign-register`, and use `sim campaign-next` to coordinate each case through existing method and execution approvals. Run `sim campaign-status` and `sim campaign-analyze`, interpret every result and regenerate both human outputs. Incomplete campaigns cannot support a final recommendation. Never infer a market-success probability from the proportion of grid scenarios that look favorable.

The financial module is optional; enable it only with explicit inputs and explain excluded mechanisms. LLM personas are synthetic; demand evidence requires research or observation. Train ML/BDH only for a justified question with independent evaluation, preserving negative results.

## Interview contract

- Map decisions as a tree. Ask the whole currently unblocked frontier in one round.
- Number questions, give project-specific alternatives, and state a recommended answer with evidence.
- Research facts; ask the user for values, choices, boundaries, priorities, and approvals.
- A later answer that changes an earlier artifact triggers reconciliation. Never hide the delta.
- Do not execute the approved plan until the user explicitly authorizes execution.

## Evidence and traceability

Use stable IDs and maintain:

```text
SRC -> STK -> VAL -> OBJ -> SSM -> LOSS -> HAZ -> SC -> CA -> UCA -> CS
    -> REQ -> SPEC -> TST -> SPR -> TSK -> EVD -> DEC
```

Every external claim needs a source, access date, supported claim, confidence, and conflict status. Every requirement needs origin, rationale, allocation, verification method, validation link, priority, risk, and status.

Run before every gate. `validate` checks every phase already reached; `--record` persists immutable timestamped evidence under `gates/<phase>/`, while `latest.json` is only a convenience pointer:

```bash
python3 <skill-dir>/scripts/validate_traceability.py <project-dir>
python3 <skill-dir>/scripts/sef.py validate <project-dir> --record
```

Measure requirement quality (Halligan) with `halligan.py`; `sef.py status` shows RQ and QF1-QF10 when `04-requirements/quality.csv` exists:

```bash
python3 <skill-dir>/scripts/halligan.py <project-dir> [--threshold 0.85] [--json]
```

## Completeness beyond STPA (step 6b)

STPA derives safety requirements only. After the SC/UCA/CS requirements, do step 6b of [stpa-requirements.md](references/stpa-requirements.md): generate functional, external-interface, performance, quality/non-functional, data, and operation/maintenance/test requirements from the System Overview, the VFT objectives, and the intake interview, each with `origin` = OBJ-/VAL-/STK-/SRC-, and fill the objective -> requirements coverage matrix. Steps 6, 6b and 7 (and registry rows 6-7) are written in `04-requirements/requirements-log.md`, never in the approved `03-stpa/stpa-analysis.md`. `halligan.py` reports `type_mix` and `completeness_hints`; the requirements gate warns `completeness-mix` and `objective-uncovered` (SOFT in every class).

## Pending questions, stale approvals, reopen

Before each user gate run `sef.py pending <project> [--json] [--write]` and hand the user its single list of questions in one round (do not ask decision by decision). `status`/`advance`/`validate` show `stale_approvals`; `advance` warns `upstream-artifact-changed` (HARD in safety-critical). To go back without losing work:

```bash
python3 <skill-dir>/scripts/sef.py reopen <project-dir> --phase <earlier-or-current-phase> --by "<name>" --reason "<why>" [--by-role <role>]
```

Approvals of the target phase and later become `superseded`; redo the gates normally. Reopening `execution`/`closure` in safety-critical needs `--by-role safety-authority|domain-expert` of an active authority.

## Human gates

The agent may prepare a gate packet and recommendation. Record approval only after an explicit human statement:

```bash
python3 <skill-dir>/scripts/sef.py approve <project-dir> --phase <phase> --by "<name>" --role user --authority-id <AUTH-ID> --evidence "<registered-evidence>" --decision approved --note "<scope of approval>"
python3 <skill-dir>/scripts/sef.py advance <project-dir>
```

### Hard and soft blockers

Each blocker has a code and is HARD or SOFT by risk class (details in [workflow.md](references/workflow.md)). HARD blockers (unset risk, invalid state/schema, bad authority or evidence, missing artifacts, traceability errors; in `high` also a missing domain expert; in `safety-critical` everything, including RQ < 0.85) exit 1 and no flag bypasses them. In `low`/`medium`/`high`, SOFT blockers (missing independent reviewer, fixture-only approval, non-executable requirements, RQ < 0.85, missing `quality.csv`, undecided STPA steps [1-5 at the STPA gate, 6-7 at the requirements gate], `upstream-artifact-changed`) make `advance` print JSON `warnings` with concrete `alternatives`, exit 2, and leave the phase unchanged. Show the warnings and alternatives to the user. Only after an explicit user decision (in fixture mode, the Scenario User decides) re-run:

```bash
python3 <skill-dir>/scripts/sef.py advance <project-dir> --acknowledge-warnings "<decision text>"
```

Always-SOFT warnings (`completeness-mix`, `objective-uncovered`, `rq-addendum-below-threshold`, `pending-requirements-high`) appear in every class, safety-critical included, and also need an explicit user decision to advance. The acknowledged codes, text, and time are written to the history. This does not change DEC-007: no LLM approves a safety-critical gate.

Register every approving authority in `00-intake/authorities.csv`. Every approval requires matching identity, role, phase scope, active status, `--authority-id`, and exact `--evidence`. `high` gates require a domain expert; `safety-critical` gates require both a domain expert and a safety authority. Medium-risk requirements and later gates expect an independent reviewer (SOFT warning when absent). These records improve provenance but do not authenticate identity outside the harness. Never manufacture an approval record.

Initialize isolated evaluations with `--mode fixture`; `--fixture` remains an explicit per-approval marker. Fixture approvals can exercise analytical gates; for `planning -> execution` they raise the SOFT warning `fixture-only-approval` (execution would rest on simulated approval; HARD in `safety-critical`). Before execution, every in-scope requirement should be `approved`, `baselined`, or `accepted`; `blocked`, `draft`, and `proposed` requirements raise the SOFT warning `requirement-not-executable` (HARD in `safety-critical`).

At planning, declare every material module through `sef.py create-module`; this creates the five module templates and a registry entry. If the system has no material modules, record one explicit non-material row in `05-planning/modules.csv` with the rationale.

## Multi-agent execution

After planning approval, use one orchestrator, bounded executors with non-overlapping ownership, independent reviewers, and the judge panel described in [multi-agent-judge.md](references/multi-agent-judge.md). Explorers and judges do not write canonical artifacts. One integrator owns merges.

LLM judgments are advisory. Deterministic checks outrank model opinion; observed evidence outranks completion claims; unresolved dissent remains visible.

## Completion

Done means required artifacts exist at system and applicable module levels, traceability validates, tests/evidence were actually run, judge claims match evidence, human gates are recorded, open risks and debt are explicit, and no safety or compliance claim exceeds the named authority.
