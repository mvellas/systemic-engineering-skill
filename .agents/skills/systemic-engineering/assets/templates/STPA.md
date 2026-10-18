# STPA analysis - {{project_name}}

Seven-step roadmap (steps 1-5 here) of Aula 10 (TE-251). Display labels L-n, H-n, SC-n, UCA-n, CS-n map to the project IDs LOSS-n, HAZ-n, SC-n, UCA-n, CS-n; write the project IDs in this file. Every item cites the overview excerpt or is marked [suposicao]. Nothing here is a conformity or "STPA concluded" statement: acceptance is human and recorded in the step registry.

## Step 1 - System Overview (one page, the only input)

- Purpose: {{purpose}}
- Boundary (inside / outside): {{boundary}}
- Actors (who operates, who is affected): {{actors}}
- Interfaces (data exchanged with the environment): {{interfaces}}

## Step 2 - Losses, hazards, and system constraints

Hazard is a state, not a cause. Each SC inverts one hazard. Mark each item [overview: "quoted excerpt"] or [suposicao].

| ID | Statement | Links (LOSS / HAZ) | Basis ([overview: "excerpt"] or [suposicao]) |
|---|---|---|---|

## Step 3 - Hierarchical control structure

| Controller | Control action (CA-n) | Controlled process | Feedback |
|---|---|---|---|

```mermaid
flowchart TD
  %% controllers on top, controlled process at the bottom; control actions down, feedback up
```

Check: does every control action have feedback? Is any controller of the overview missing? Does every arrow exist in the overview?

## Step 4 - Unsafe control actions (four types per control action)

Types: not provided; provided; too early / too late / out of order; stopped too soon / applied too long. A UCA without a hazard is cut. Each UCA yields one SC (controller constraint).

| UCA ID | Source (controller) | Type | Control action | Concrete context | Hazard (HAZ) | Constraint (SC) |
|---|---|---|---|---|---|---|

## Step 5 - Loss scenarios (cause, not solution)

Class 1: why the UCA happens. Class 2: why the correct control action is not executed. Point to the control-structure element involved.

| Scenario ID (CS) | UCA | Class (1 or 2) | Control-structure element | Cause |
|---|---|---|---|---|

## Steps 6, 6b and 7 - requirements, non-STPA requirements, measurement

These steps happen after this analysis is approved, so they live in `04-requirements/requirements-log.md` (template REQUIREMENTS-LOG.md, copied when the project enters the requirements phase). Do not write them here: editing this file after the STPA gate makes its approval stale.

## Registro de etapas

One row per step: the prompt/input given, the output received, the human decision, who approved, and the date. A step without a decision is reported as a warning by `sef.py` (hard in safety-critical): this gate checks steps 1-5; steps 6-7 are registered in 04-requirements/requirements-log.md.

| Etapa | Prompt/entrada | Saida | Decisao | Aprovador | Data |
|---|---|---|---|---|---|
| 1 | | | | | |
| 2 | | | | | |
| 3 | | | | | |
| 4 | | | | | |
| 5 | | | | | |

## Coverage gaps and complementary analyses

{{gaps_fmea_fta_hazop_security_privacy_assurance}}
