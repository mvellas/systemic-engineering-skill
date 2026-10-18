---
date: 2026-10-16
type: skill-reference
tags: [skill-reference, stpa, requirements]
sensitivity: personal
ai-first: true
---

## For future Claude
STPA analysis sequence and transformation into well-formed, verifiable, and validatable requirements.

# STPA and requirements

Roadmap of seven steps from Aula 10 (TE-251 2026.2, slides 55-64), with the Halligan metrics (slides 24-31; Halligan, CSESAW 1993, PPA-005330-9, 2014 and addendum). Templates: `assets/templates/STPA.md` (steps 1-5 and their registry rows) and `assets/templates/REQUIREMENTS-LOG.md` (steps 6, 6b, 7 and registry rows 6-7, copied to `04-requirements/requirements-log.md` when the project enters the requirements phase). Steps 6-7 live there because they happen after the STPA gate; writing them into the approved `stpa-analysis.md` would make that approval stale (`upstream-artifact-changed`). Legacy projects that still hold steps 6-7 in `stpa-analysis.md` are read as a fallback when `requirements-log.md` is absent. Never assert a source section you did not read.

## ID mapping

Slides use display labels; the project and the validator use prefixed IDs. Write the project IDs in files.

| Slide label | Project ID | Meaning |
|---|---|---|
| L-n | `LOSS-n` | loss |
| H-n | `HAZ-n` | hazard |
| SC-n | `SC-n` | system / controller safety constraint |
| (control action) | `CA-n` | control action |
| UCA-n | `UCA-n` | unsafe control action |
| cenario n | `CS-n` | loss scenario |

## The seven steps

For each step the model proposes and cites; a person checks and approves (HITL). Record prompt, output, and decision in the "Registro de etapas" table (steps 1-5 in `STPA.md`, steps 6-7 in `requirements-log.md`).

1. **System Overview (one page)**: purpose, boundary (inside/outside), actors (who operates, who is affected), interfaces. It is the only input of the analysis.
2. **Losses, hazards, constraints**: list `LOSS-n`, `HAZ-n` linked to losses, `SC-n`. Mark every item `[overview: "quoted excerpt"]` or `[suposicao]`. A hazard is a state, not a cause; each SC inverts one hazard. The person approves or cuts every suposicao.
3. **Control structure**: table controller / control action / controlled process / feedback, plus a Mermaid diagram (control actions down, feedback up). Check: does every control action have feedback? Is any controller of the overview missing? Does every arrow exist in the overview?
4. **UCAs**: examine the FOUR types for each control action: (a) not provided; (b) provided; (c) too early / too late / out of order; (d) stopped too soon / applied too long. Five fields per UCA: source (controller), type, control action, concrete context, hazard `HAZ-n`. A UCA without a hazard is cut. Each UCA yields one SC. Check that the context is concrete and that no type was left unexamined.
5. **Loss scenarios**: numbered per UCA. Class 1: why the UCA happens. Class 2: why the correct control action is not executed. Each scenario names the control-structure element involved and describes the cause, not the solution. Check that no UCA is left without a scenario and that the cause fits this system.
6. **Requirements** in the Halligan template: condition, actor, action, object, constraint, plus refinements (source of object, destination of action). Table with an Origin column (`SC-n`, `UCA-n`, or `CS-n`): no origin, no requirement. One sentence, one requirement, one objective test criterion. Reword vague terms. Record in `04-requirements/requirements.csv` using `origin`, `actor`, `condition`, `action`, `object`, `constraint`, `refinement`.
6b. **Requirements not derived from STPA**: STPA yields safety requirements, not the complete set. After the SC/UCA/CS requirements, generate functional, external-interface, performance, quality/non-functional (accessibility, privacy, availability, maintainability), data, and operation/maintenance/periodic-test requirements from the System Overview, the VFT objectives, and the intake sheet/interview. Each has `origin` pointing to an `OBJ-`, `VAL-`, `STK-`, or `SRC-` ID (traceable) and a `type` value that reflects its kind. Fill the coverage matrix objective -> requirements (`requirements-log.md`, Step 6b). `halligan.py` reports `type_mix` and `completeness_hints` (functional and external interface within ~10 points, functional slightly larger; other qualities 5-10% up to 100 requirements; hints, not errors). `sef.py` raises SOFT `completeness-mix` and `objective-uncovered` (an OBJ-/VAL- in 01-vft or 02-ssm/reconcile that no requirement cites in `source_ids`, `origin`, or `validation_link`, unless a decision in `decisions.csv` says it is out of scope). In safety-critical they stay SOFT: coverage is not proof.
7. **Measurement**: score every requirement with the ten factors (below), compute RQ with `scripts/halligan.py`, rewrite requirements with IRQ < 1, and repeat until RQ >= 0.85. The person redoes three scores by hand and looks for missing requirements.

Do not omit organizational controls or lifecycle stages. STPA does not replace FMEA, FTA, HAZOP, security, privacy, or assurance cases; a line that belongs to another method is not STPA.

## Three locks (every step)

1. **Origin**: every item cites the overview excerpt or declares itself a suposicao.
2. **Person**: no step advances without human approval (HITL).
3. **Record**: keep the prompt, the output, and the decision of each step (Registro de etapas: etapa, prompt/entrada, saida, decisao, aprovador, data). A step without a decision is a warning (blocking in safety-critical): the STPA gate checks steps 1-5, the requirements gate checks steps 6-7 (6b included in 6).

## Three failures to avoid

- Inventing a UCA that the source does not contain.
- Paraphrasing the handbook without naming the section.
- Treating as STPA a line that belongs to another method.

All three yield text that looks safe. The model never signs conformity and never declares "STPA concluded": acceptance is human and recorded with name, authority, and date.

## Requirement quality (Halligan)

Template parts: actor, conditions, action, object, constraints, refinement/source of object, refinement/destination of action. Score each applicable part 1 or 0 (`NA` when not applicable); IRQ = parts at 1 / applicable parts. RQ = mean of IRQ.

Ten factors per requirement (1/0): IQF1 correctness, IQF2 completeness, IQF3 consistency, IQF4 clarity, IQF5 non-ambiguity, IQF6 connectivity, IQF7 singularity, IQF8 testability, IQF9 modifiability, IQF10 feasibility. QFn = mean of IQFn. Completeness accounts for unwritten requirements: QF2' = mean(IQF2) - mean(omission ratio), possibly negative. The primary RQ of the addendum counts the estimated missing requirements at quality zero: sum(IRQ) / (n + sum(omission)). RTBD is the percentage of requirements still TBD: statement with TBD, status `blocked`, or a filled `blocked_by`.

Interpretive bands (Table 2): 0.01-0.3 very poor; 0.3-0.7 fair; 0.85-0.99 adequate for SRR; 0.99+ critical development. The range 0.7-0.85 is not tabulated. Gate threshold: 0.85.

```bash
python3 <skill-dir>/scripts/halligan.py <project-dir> [--threshold 0.85] [--json]
```

The report also carries `type_mix` (count and percent per `type` value, grouped as functional / interface / safety / other) and `completeness_hints`. The gate also warns SOFT `rq-addendum-below-threshold` when the primary RQ of the addendum, sum(IRQ)/(n+sum(omission)), is below 0.85, in every risk class; `rq-below-threshold` (simple RQ) is unchanged.

Exit codes: 0 meets the threshold, 1 invalid or missing data, 2 below threshold. Scores come from `04-requirements/quality.csv` (template in `assets/templates/quality.csv`); an LLM may score, but a person must redo samples and approve.

## Requirement rows

Use `REQ-*` and `shall` only for agreed obligations. Each row includes:

- statement with responsible subject, active voice, explicit condition, one obligation, and defined terms;
- type and level;
- origin (`SC-`, `UCA-`, `CS-`, or another registered source) and source IDs, parent requirement;
- rationale and assumptions;
- allocation and interfaces;
- verification method and success criterion;
- validation link to stakeholder need/objective;
- risk, priority, owner, status, and change history.
- constraint class, waiver policy, threshold source, blockers, and decision IDs. A non-compensable constraint uses `waiver_policy=none`; thresholds cite an approved `SRC-*` or `DEC-*`, or use `not-applicable`. Empty `blocked_by` and `decision_ids` count as not-applicable.

Register every `DEC-*` referenced by a requirement in `04-requirements/decisions.csv`, with status, owner, authority/evidence, affected IDs, and rationale. An approved decision requires a registered active authority, matching evidence, and decision/requirements scope. A blocked requirement names its pending decisions in `blocked_by`. An approved/baselined/accepted requirement cannot reference any pending, rejected, or superseded decision, whether through `decision_ids`, `threshold_source`, or `blocked_by`, and must have actor, action, and object filled when those columns exist.

Check individual requirements for necessary, appropriate, unambiguous, complete, singular, feasible, verifiable, correct, and conforming. Check sets for completeness, consistency, feasibility, comprehensibility, correctness, and ability to be validated.

Before baselining, compare each requirement against non-compensable values and constraints. Exceptions, waivers, fallbacks, or manual overrides may not bypass them. If a requirement depends on an undecided threshold, authority, glossary term, dataset, or oracle, list the relevant IDs in `blocked_by` and do not label it approved or executable.

Verification asks whether the implementation satisfies requirements. Validation asks whether the resulting system satisfies stakeholder expectations and intended use. Maintain both paths.

Generate tests from normal behavior, boundaries, states/modes, interfaces, degraded/adverse conditions, UCAs, and causal scenarios.
