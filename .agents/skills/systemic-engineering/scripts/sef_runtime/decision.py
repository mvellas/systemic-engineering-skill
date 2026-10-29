"""Transparent additive MCDA with explicit vetoes and weight sensitivity."""

from . import store as s


def compare(project):
    m = s.model(project)
    criteria = m["criteria"]
    alts = m["alternatives"]
    sources = {x["id"] for x in m["sources"]}
    if not criteria or len(alts) < 2:
        raise s.Invalid(
            "Comparação exige critérios e pelo menos duas alternativas, incluindo status quo quando pertinente."
        )
    if len({x["id"] for x in criteria}) != len(criteria) or len(
        {a["id"] for a in alts}
    ) != len(alts):
        raise s.Invalid("IDs repetidos na comparação.")
    for c in criteria:
        s.finite(c.get("weight"), "weight", 0, 1)
        s.finite(c.get("min"), "min")
        s.finite(c.get("max"), "max")
        if (
            c["max"] <= c["min"]
            or c.get("direction") not in {"min", "max"}
            or not c.get("judgment_by")
            or not c.get("weight_reason")
        ):
            raise s.Invalid("Critério exige escala, direção e origem humana do peso.")
    if abs(sum(c["weight"] for c in criteria) - 1) > 1e-8:
        raise s.Invalid("Pesos devem somar 1; não serão preenchidos automaticamente.")
    matrix = []
    for a in alts:
        vals = {}
        veto = []
        for c in criteria:
            x = a.get("scores", {}).get(c["id"])
            if not x or not x.get("source_ids") or set(x["source_ids"]) - sources:
                raise s.Invalid(
                    "Toda avaliação exige fonte externa registrada e interpretação específica."
                )
            value = s.finite(x.get("value"), "score", c["min"], c["max"])
            if not x.get("explanation"):
                raise s.Invalid("Avaliação exige explicação em linguagem comum.")
            vals[c["id"]] = (
                (value - c["min"]) / (c["max"] - c["min"])
                if c["direction"] == "max"
                else (c["max"] - value) / (c["max"] - c["min"])
            )
            if c.get("veto_below") is not None and value < c["veto_below"]:
                veto.append(c["id"])
            if c.get("veto_above") is not None and value > c["veto_above"]:
                veto.append(c["id"])
        score = sum(c["weight"] * vals[c["id"]] for c in criteria)
        matrix.append(
            {
                "alternative": a["id"],
                "title": a.get("title", a["id"]),
                "normalized": vals,
                "weighted_score": score,
                "vetoes": veto,
                "eligible": not veto,
                "benefits": a.get("benefits"),
                "losses": a.get("losses"),
                "affected_objectives": a.get("objective_ids", []),
                "source_ids": sorted(
                    {i for x in a["scores"].values() for i in x["source_ids"]}
                ),
            }
        )
    ranking = sorted(
        (a for a in matrix if a["eligible"]),
        key=lambda a: a["weighted_score"],
        reverse=True,
    )
    sensitivity = []
    for c in criteria:
        for delta in (-0.1, 0.1):
            w = min(1, max(0, c["weight"] + delta))
            other = 1 - c["weight"]
            if other == 0:
                continue
            scores = {
                a["alternative"]: sum(
                    (w if k["id"] == c["id"] else k["weight"] * (1 - w) / other)
                    * a["normalized"][k["id"]]
                    for k in criteria
                )
                for a in ranking
            }
            best = max(scores, key=scores.get) if scores else None
            sensitivity.append(
                {"criterion": c["id"], "weight": w, "winner": best, "scores": scores}
            )
    return {
        "method": "additive-value-model",
        "external_source": "https://www.gov.uk/government/publications/multi-criteria-analysis-manual-for-making-government-policy",
        "ranking": ranking,
        "excluded": [a for a in matrix if not a["eligible"]],
        "sensitivity": sensitivity,
        "advisory_candidate": ranking[0]["alternative"] if ranking else None,
        "human_decision": "pending",
        "limitations": [
            "Pontuações são uma síntese dependente dos dados e juízos registrados; não são probabilidade de sucesso.",
            "Verificar independência preferencial e evitar contar o mesmo efeito em dois critérios.",
            "Veto representa condição não compensável, que não pode ser superada por bom desempenho em outro critério.",
            "Variação dos pesos é análise local, não prova de robustez global.",
        ],
    }


def impact(project):
    m = s.model(project)
    root = s.root(project)
    current = s.digest(m)
    stale = []
    for p in (root / "exports").glob("*/manifest.json"):
        old = s.read(p)
        if old.get("model_hash") != current:
            stale.append(str(p.relative_to(root)))
    pending = [x["id"] for x in m["conflicts"] if x["status"] == "pending"]
    return {
        "revision": m["revision"],
        "model_hash": current,
        "stale_exports": stale,
        "pending_conflicts": pending,
        "note": "A mudança material entra também nos hashes dos gates existentes. Regenerar documentos não renova aprovação humana.",
    }
