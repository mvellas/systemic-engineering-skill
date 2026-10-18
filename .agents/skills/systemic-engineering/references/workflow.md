---
date: 2026-10-16
type: skill-reference
tags: [skill-reference, workflow, systems-engineering]
sensitivity: personal
ai-first: true
---

## For future Claude
Phase sequence, gate packet, risk classes, and change-control rules for the framework.

# Workflow and gates

## Phase sequence

1. `intake`: define system of interest, use case, lifecycle, authority, risk class, must-nevers, outputs, evidence policy, and research plan.
2. `vft`: elicit stakeholders, values, objectives, attributes, and provisional alternatives while open-source research runs alongside the interview.
3. `ssm`: express the problematical situation, surface social and political structure, formulate root definitions, model purposeful activity, and debate change.
4. `reconcile`: compare SSM findings against VFT. Add, revise, split, supersede, or explicitly retain stakeholders, values, objectives, boundaries, and assumptions.
5. `stpa`: define losses, hazards, constraints, control structure, unsafe control actions, and causal scenarios.
6. `requirements`: transform approved needs and constraints into well-formed, allocated, verifiable requirements and validation expectations.
7. `planning`: create system-level and module-level PRD, SPEC, TESTS, SPRINTS, and TASKS.
8. `execution`: implement in bounded increments; verify every increment and preserve evidence.
9. `closure`: validate outcomes against stakeholder values, record residual risk, operation, maintenance, disposal, debt, and learning.

Phases are iterative, not a one-way waterfall. Backward movement must create a delta record and invalidate downstream baselines affected by the change.

## Gate packet

Every gate packet contains:

- decision requested and decision owner;
- artifacts and immutable versions/hashes;
- claims with source IDs;
- deterministic validation results;
- favorable, adversarial, and neutral findings;
- unresolved dissent and assumptions;
- risk and downstream impact;
- recommendation: approve, approve with conditions, revise, or stop.

## Risk classes

- `low`: reversible, limited impact, ordinary engineering review.
- `medium`: meaningful cost, data, security, or operational impact; an authority-registered independent reviewer is required from the requirements gate onward.
- `high`: substantial harm, regulated context, irreversible decision, or critical business dependency; an authority-registered domain expert is required at STPA and later gates.
- `safety-critical`: credible physical harm or mission loss; both an authority-registered domain expert and safety authority are required at STPA and later gates. The skill cannot certify.

`sef.py status` reports the next action, artifact blockers, execution blockers, required roles, missing roles, and gate readiness. Failed advances and validations are recorded as immutable timestamped files under `gates/<phase>/`, with `latest.json` as a convenience pointer; they must not disappear from the audit trail.

Risk class is mandatory before leaving intake and is part of every approval fingerprint. Once intake is passed it cannot be lowered or changed in place; a changed risk assessment requires an explicit reconciled baseline instead of a silent downgrade.

Fixture approvals are evaluation data, not execution authority. Initialize test projects with `sef.py init ... --mode fixture`; they may exercise gates through planning, but `planning -> execution` requires non-fixture approvals for every required role and executable statuses for every in-scope requirement.

## Hard and soft gates

Every blocker has a code and is HARD or SOFT according to the risk class.

- Always HARD: `risk-class:unset`; invalid state or schema; unregistered or inactive authority or divergent evidence; missing placeholders or required artifacts; traceability errors; missing `user` role; invalid `quality.csv`.
- SOFT in every class (including `safety-critical`, they inform): `completeness-mix`, `objective-uncovered`, `rq-addendum-below-threshold` (primary RQ of the addendum < 0.85), `pending-requirements-high` (more than 5% of requirements blocked/proposed/draft at the requirements gate).
- SOFT in `low` and `medium` (HARD in `safety-critical`), also `upstream-artifact-changed` (an artifact of an already approved earlier phase changed since its latest approval): `missing-role:independent-reviewer`, `fixture-only-approval` (planning -> execution runs on simulated approval), `requirement-not-executable` (blocked/draft/proposed), `rq-below-threshold` (RQ < 0.85), `quality-missing` (no `quality.csv` or unscored requirements, checked at the requirements gate), `stpa-step-undecided` (registry rows without decision: steps 1-5 at the STPA gate, steps 6-7 at the requirements gate, read from `04-requirements/requirements-log.md`, with fallback to `stpa-analysis.md` for legacy projects). The requirements log is an artifact of the requirements phase, so writing steps 6, 6b and 7 never makes the STPA approval stale.
- `high`: `missing-role:domain-expert` is HARD; the SOFT codes above stay SOFT.
- `safety-critical`: everything is HARD, including RQ < 0.85, a missing domain expert, and a missing safety authority. This does not change DEC-007: no LLM approves a safety-critical gate.

`advance` behavior:

- HARD present: exit 1, JSON with `hard_blockers` and `alternatives`, state unchanged. No flag bypasses it.
- Only SOFT: exit 2, JSON with `warnings` (each has `code`, `message`, `severity`, `details`, `alternatives`), phase unchanged, attempt stored as `gates/<phase>/<timestamp>-warned.json`.
- `advance --acknowledge-warnings "<decision text>"`: advances with exit 0 and records in the history event the acknowledged codes, the text, and the time.

The agent MUST show the warnings and alternatives to the user and pass the flag only after an explicit user decision (in fixture mode the Scenario User decides). The agent never invents the decision text. `status` shows `hard_blockers`, `warnings`, `alternatives`, and `quality` (RQ and QF1-QF10 when `quality.csv` exists).

## Pending questions, stale approvals, and reopening

- `sef.py pending <project> [--json] [--write]` lists every decision that depends on the user in one list: pending decisions in `decisions.csv`, blocked/proposed/draft requirements with their `blocked_by`/`decision_ids`, and statements with TBD. Exit 0 when clean, 2 otherwise. `--write` saves `04-requirements/pending-questions.md` (never over a file containing `@user`). Deliver the list to the user in a single round.
- `status`, `validate`, and `advance` report `stale_approvals` ({phase, files}) for earlier phases whose own artifacts changed after their latest approval.
- `sef.py reopen <project> --phase <earlier-or-current> --by "<name>" --reason "<text>" [--by-role <role>]` returns to an earlier phase without losing work: it records the `reopened` event, writes the immutable `gates/<current>/<timestamp>-reopened.json`, and marks the approvals of phases >= target as `superseded` (they no longer count). Files and directories of later phases stay. In `safety-critical`, reopening from `execution` or `closure` needs `--by-role safety-authority|domain-expert` matching an active authority; the requirement is recorded in `reopen_requires`. Backward movement is the delta record promised by the phase sequence.

## Change control

Use `DEC-*` records. State what changed, why, source, impacted IDs, invalidated artifacts, migration/retest work, and approving authority. Approved decisions require a registered active authority and matching evidence. The latest approval or rejection from the same authority supersedes its earlier gate vote. Never silently rewrite history.
