---
date: 2026-10-16
type: skill-reference
tags: [skill-reference, evidence, research]
sensitivity: personal
ai-first: true
---

## For future Claude
Evidence authority, open-source research, and retrieval rules for intake and all later gates.

# Evidence and open-source research

## Source register

Record `SRC-ID`, title, author/authority, URL or local path, publication date, access date, source type, supported claims, limitations, confidence, and relation to other sources (`supports`, `contradicts`, `supersedes`). Preserve raw sources.

Authority order:

1. direct statement by the accountable stakeholder;
2. primary local artifact or live system state;
3. regulation, standard, official documentation, original paper, or official dataset;
4. reputable secondary analysis;
5. model inference, explicitly labeled.

## Research loop

1. Turn open interview questions into factual queries.
2. Search primary sources first and note recency.
3. Extract claim-sized evidence, not decorative citations.
4. Search for counter-evidence and affected stakeholders.
5. Bring only decision-relevant deltas into the next interview frontier.
6. Freeze the admissible evidence packet before judge debate.

Do not ask the user to find public facts the agent can research. Do ask which authority and risk posture they accept when sources conflict.

## Retrieval

Retrieve by phase, artifact ID, source ID, and topic. Do not load the whole corpus. Prefer a source note's routing summary, then open its cited page range only if the decision needs detail.
