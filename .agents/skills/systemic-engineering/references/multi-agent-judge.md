---
date: 2026-10-16
type: skill-reference
tags: [skill-reference, multi-agent, llm-as-judge]
sensitivity: personal
ai-first: true
---

## For future Claude
Role separation, independence protocol, rubric, and evidence-gated execution loop.

# Multi-agent execution and judge panel

## Roles

- Orchestrator: reads approved plan, resolves dependencies, assigns bounded work, and never substitutes for approval.
- Researcher/explorer: read-only evidence packet with source IDs and uncertainty.
- Executor: owns explicit files/components and produces implementation plus evidence.
- Reviewer: independent review against requirements, risks, and tests; does not repair silently.
- Integrator: sole canonical writer/merger when outputs overlap.
- Favorable advocate: steelmans the proposal and states necessary success conditions.
- Adversarial advocate: searches for counterexamples, missing evidence, unsafe assumptions, regressions, and falsifiers.
- Neutral auditor: checks rubric, traceability, scope, and evidence without optimizing for approval or rejection.
- Judge: synthesizes criterion-level verdicts, confidence, dissent, and required action.
- Human authority: decides gates and accepts residual risk.

## Independence protocol

1. Freeze task, rubric, admissible sources, and expected artifacts before opinions.
2. Advocates review independently before seeing one another's conclusions.
3. Hide author/model identity and randomize candidate order when comparing alternatives.
4. Require every finding to cite an artifact, source, diff, log, or test.
5. Debate only contested criteria, at most two rounds unless new evidence appears.
6. Judge emits per-criterion `pass`, `conditional`, `fail`, or `abstain`; no opaque scalar alone.
7. Deterministic failures cannot be overruled by prose.
8. Preserve minority dissent and calibrate confidence.
9. Treat a contradiction to an approved non-compensable value or system constraint as a failing gate until reconciled; strengths elsewhere do not offset it.

## Rubric

- intent and approved scope;
- theoretical/method fidelity;
- source quality and citation validity;
- traceability completeness;
- requirement and interface correctness;
- safety, security, privacy, ethics, and compliance;
- verification and validation evidence;
- operability, maintainability, rollback, and observability;
- user value and acceptance criteria;
- unverified claims, debt, and residual risk.

## Execution loop

Plan packet -> bounded execution -> local deterministic checks -> independent review -> integration -> system tests -> judge panel -> human gate when required -> evidence register and state transition.

Never equate repeated model agreement with independent confirmation. If agents share model, prompt, sources, or context, record correlated-failure risk.
