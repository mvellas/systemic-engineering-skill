# Requirements log - {{project_name}}

Steps 6, 6b and 7 of the STPA roadmap (Aula 10). They live in the requirements phase because they happen after the STPA gate; editing 03-stpa/stpa-analysis.md after its approval would make that approval stale. Every item cites its origin. Nothing here is a conformity statement: acceptance is human and recorded in the step registry below.

## Step 6 - Requirements (Halligan template)

Condition, actor, action, object, constraint (+ refinements). No origin, no requirement. One sentence, one requirement, one objective test criterion. The authoritative table is 04-requirements/requirements.csv (column origin); list here only the draft.

| ID | Requirement | Origin (SC / UCA / CS) | Test criterion |
|---|---|---|---|

## Step 6b - Requirements not derived from STPA

STPA derives safety requirements, not the full functional, interface and non-functional set. After the SC/UCA/CS requirements, derive from the System Overview, the VFT objectives and the intake sheet/interview: functional, external interface, performance, quality (accessibility, privacy, availability, maintainability), data, and operation/maintenance/periodic test requirements. Each one has an `origin` pointing to an OBJ-/VAL-/STK-/SRC- ID. Complete the coverage matrix; an objective with no requirement is either covered or recorded as out of scope in 04-requirements/decisions.csv.

| Objective / value (OBJ- / VAL-) | Requirements (REQ-) | Kinds covered (functional, interface, quality, data, operation) | Out of scope? (DEC-) |
|---|---|---|---|

## Step 7 - Measurement

RQ and QF1-QF10 come from `halligan.py` over 04-requirements/quality.csv. Repeat until RQ >= 0.85, rewriting requirements with IRQ < 1. Re-score three requirements by hand and look for missing requirements.

| Round | RQ | Requirements rewritten | Decision |
|---|---|---|---|

## Registro de etapas

Steps 1-5 are registered in 03-stpa/stpa-analysis.md. Same columns here for steps 6 and 7; a step without a decision is reported as a warning by `sef.py` (hard in safety-critical) at the requirements gate.

| Etapa | Prompt/entrada | Saida | Decisao | Aprovador | Data |
|---|---|---|---|---|---|
| 6 | | | | | |
| 7 | | | | | |
