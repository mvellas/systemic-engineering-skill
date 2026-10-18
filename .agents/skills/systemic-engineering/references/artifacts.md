---
date: 2026-10-16
type: skill-reference
tags: [skill-reference, artifacts, planning]
sensitivity: personal
ai-first: true
---

## For future Claude
Contracts for PRD, SPEC, TESTS, SPRINTS, and TASKS at system and module levels.

# Project artifacts

Generate first at system level, then recursively for each material module. Declare modules in `05-planning/modules.csv`; prefer `sef.py create-module` so their paths and five artifacts are deterministic. A module inherits project purpose, values, global constraints, and parent requirements by reference; it owns allocated requirements, interfaces, local design, tests, sprint work, and evidence. Reference inherited content instead of duplicating it.

## PRD

Problem situation, decision statement, stakeholders, values and outcomes, users/use cases, ConOps, scope/non-scope, alternatives and decision, success measures, constraints, risks, assumptions, dependencies, acceptance and open questions.

## SPEC

Context and boundaries, architecture, components, interfaces, data, behaviors, states/modes, error/degraded behavior, security/safety/privacy/NFRs, allocated requirements, decisions, observability, deployment/operation, verification hooks, and unresolved design questions.

## TESTS

Test strategy, environments, oracles, fixtures, requirement coverage, interface/contract tests, state and boundary tests, STPA-derived tests, negative/adversarial tests, performance/reliability tests, validation scenarios, entry/exit criteria, evidence retention, and independent review.

## SPRINTS

Outcome and demo, included requirement IDs, capacity, dependencies, risks, task order, verification plan, gate, rollback/recovery, and carryover policy. A sprint is not a bag of unrelated tasks.

## TASKS

One bounded change with owner, source requirements, inputs, files/interfaces in scope, output, deterministic checks, reviewer, risk, definition of done, and evidence path. Executors must not share write ownership without an integrator.

Requirement quality data lives in `04-requirements/quality.csv` (template `assets/templates/quality.csv`, metrics via `scripts/halligan.py`); see [stpa-requirements.md](stpa-requirements.md).

Requirements from step 6b (recorded in `04-requirements/requirements-log.md`) (non-STPA) and the objective coverage matrix feed the PRD (outcomes, scope) and TESTS (requirement coverage). If planning exposes a missing requirement, use `sef.py reopen --phase requirements` instead of editing around the gate; `sef.py pending` lists the open questions for the user.

Use templates under `assets/templates/`. Keep parent-child links and avoid narrative duplication.
