---
date: 2026-10-16
type: skill-reference
tags: [skill-reference, vft, interview]
sensitivity: personal
ai-first: true
---

## For future Claude
Project-adaptive VFT interview using Vieira et al.'s integrated process and decision-tree rounds.

# VFT interview

Use Vieira et al.'s integrated VFT process as the backbone, with project-specific quick questions.

## Round structure

Ask only the unblocked frontier. Each question includes 2-4 concrete alternatives and one recommendation grounded in current evidence. Wait for the answers before recomputing the tree.

## Phase 1 - Initial Decision Frame

Establish:

- purpose: why decide, by when, and which consequences matter;
- perspective: whose values define good;
- scope: decision boundary, authority, constraints, status quo, and excluded alternatives;
- decision statement: `Decide + action verb + object + material constraints`.

Identify decision-makers, users, operators, maintainers, suppliers, affected non-users, regulators, adversaries, future stakeholders, and lifecycle owners. Give each `STK-*`.

## Phase 2 - Values and objectives

Use the ten devices adaptively:

1. wish list: perfect outcome;
2. alternatives: what makes one option better;
3. problems: what must be prevented;
4. consequences: desirable and undesirable outcomes;
5. goals and constraints;
6. perspectives of other stakeholders;
7. strategic alignment;
8. generic values such as cost, time, quality, risk, resilience, safety, privacy, maintainability, and sustainability;
9. structuring: means-to-ends relationships;
10. quantifying: observable attributes and scales.

Convert raw statements into `VAL-*` and action-oriented `OBJ-*`. Preserve the speaker and source.

For each objective ask WITI: "Why is this important in this decision context?"

- an answer pointing to another objective suggests a means objective;
- an intrinsic reason suggests a candidate fundamental objective;
- mission-level reasoning suggests a strategic objective.

Apply control-of-consequences and scope tests before confirming fundamental objectives. Record uncertainty; do not force every statement into the hierarchy.

## Quality gate

Check the set for essentiality, controllability, completeness, measurability, operational meaning, decomposability, non-redundancy, concision, and comprehensibility. Attributes must be unambiguous, comprehensive enough, direct where possible, operational, and understandable.

## Phase 3 - Alternatives

Generate alternatives only after objectives are visible: per objective, pairs/triples, means-ends network, constraints relaxed as explicit scenarios, and status quo. Build a consequence matrix and test dominance. Do not let early alternatives redefine values invisibly.

The VFT baseline is provisional until SSM reconciliation.
