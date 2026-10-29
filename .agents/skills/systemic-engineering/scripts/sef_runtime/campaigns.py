"""Campaign lifecycle over individually authorized runs. No batch approval bypass."""

from __future__ import annotations
from . import store as s, experiments, simulation


def register(project, spec):
    planned = experiments.plan(spec)
    for factor in planned["factors"]:
        if factor.get("role") not in {"decision", "uncertainty", "structural"}:
            raise s.Invalid(
                "Campanha exige role=decision, uncertainty ou structural em cada fator."
            )
    if not any(f["role"] == "decision" for f in planned["factors"]):
        raise s.Invalid(
            "Defina pelo menos um fator de decisão para comparar estratégias."
        )
    s.integrity(project)
    # Validate all cases and references before creating any campaign record.
    for case in planned["cases"]:
        simulation.preflight(project, case["config"])
    cid = "CAM-" + s.digest(planned)[:16]
    with s.lock(project):
        m = s.model(project)
        existing = next((x for x in m.get("campaigns", []) if x["id"] == cid), None)
        if existing:
            return {
                "id": cid,
                "status": "already-registered",
                "execution_authorized": False,
            }
        entry = {
            "id": cid,
            "plan": planned,
            "created_at": s.now(),
            "analysis_status": "pending",
        }
        s.save(
            project,
            {**m, "campaigns": [*m.get("campaigns", []), entry]},
            "campaign-registered",
            {"id": cid, "cases": planned["case_count"]},
        )
    return {
        "id": cid,
        "status": "planned",
        "case_count": planned["case_count"],
        "execution_authorized": False,
        "next_action": "sim campaign-next; revisar método e autorizar somente a configuração apresentada.",
    }


def get(project, cid):
    s.integrity(project)
    entry = next(
        (x for x in s.model(project).get("campaigns", []) if x["id"] == cid), None
    )
    if not entry:
        raise s.Invalid("Campanha não registrada.")
    for case in entry["plan"]["cases"]:
        if s.digest(case["config"]) != case["config_hash"]:
            raise s.Invalid("Configuração da campanha alterada.")
    return entry


def status(project, cid):
    entry = get(project, cid)
    registered = s.model(project)["runs"]
    rows = []
    for case in entry["plan"]["cases"]:
        matches = [
            r
            for r in registered
            if r.get("config_hash") == case["config_hash"]
            and r["status"] == "completed"
        ]
        if len(matches) > 1:
            raise s.Invalid(
                "Múltiplas execuções para um caso; crie plano com sementes distintas para reteste, sem escolher o resultado favorável."
            )
        run = matches[0] if matches else None
        row = {
            "case_id": case["id"],
            "assignments": case["assignments"],
            "status": "pending",
        }
        if run:
            folder = s.root(project) / "runs" / run["id"]
            manifest = s.read(folder / "manifest.json")
            if (
                manifest["status"] != "completed"
                or manifest.get("config_hash") != case["config_hash"]
                or s.digest(s.read(folder / "config.json")) != case["config_hash"]
                or s.file_hash(folder / "result.json") != run["result_hash"]
                or manifest["result_hash"] != run["result_hash"]
            ):
                raise s.Invalid("Integridade de execução da campanha falhou.")
            row.update(
                status="completed",
                run_id=run["id"],
                result_hash=run["result_hash"],
                interpretation_status=run.get("interpretation_status"),
            )
        rows.append(row)
    return {
        "id": cid,
        "case_count": len(rows),
        "completed_cases": sum(x["status"] == "completed" for x in rows),
        "cases": rows,
        "execution_authorized": False,
    }


def next_case(project, cid):
    entry = get(project, cid)
    progress = status(project, cid)
    pending = next((x for x in progress["cases"] if x["status"] == "pending"), None)
    if pending is None:
        return {
            "id": cid,
            "status": "calculations-complete",
            "next_action": "Interpretar resultados; sim campaign-analyze; revisão humana da recomendação.",
        }
    case = next(x for x in entry["plan"]["cases"] if x["id"] == pending["case_id"])
    return {
        "id": cid,
        "status": "awaiting-specific-authorization",
        "case": case,
        "execution_authorized": False,
        "next_action": "O agente salva case.config, executa preflight e obtém revisão metodológica e grant de execução antes de sim run. A próxima execução muda o modelo e exige novas autorizações.",
    }


def analyze(project, cid):
    entry = get(project, cid)
    progress = status(project, cid)
    decisions = [
        f["parameter"] for f in entry["plan"]["factors"] if f["role"] == "decision"
    ]
    rows, groups = [], {}
    for item, case in zip(progress["cases"], entry["plan"]["cases"]):
        if item["status"] != "completed":
            continue
        result = s.read(s.root(project) / "runs" / item["run_id"] / "result.json")
        if result.get("engine") != "agents" or len(result.get("summary", [])) != 1:
            raise s.Invalid(
                "Resultado não corresponde ao contrato multiagente da campanha."
            )
        summary = result["summary"][0]
        row = {
            **item,
            "cash_median": summary["final_cash"]["median"],
            "cash_p10": summary["final_cash"]["p10"],
            "cash_p90": summary["final_cash"]["p90"],
            "conditional_success_fraction": summary["conditional_success_fraction"],
            "early_stopped_replicas": summary["early_stopped_replicas"],
            "financial": summary.get("financial"),
            "success_rule": summary["success_rule"],
        }
        rows.append(row)
        strategy = {k: case["assignments"][k] for k in decisions}
        key = s.canonical(strategy)
        groups.setdefault(key, {"strategy": strategy, "rows": []})["rows"].append(row)
    ranking = []
    for g in groups.values():
        ranking.append(
            {
                "strategy": g["strategy"],
                "evaluated_conditions": len(g["rows"]),
                "worst_cash_p10": min(x["cash_p10"] for x in g["rows"]),
                "best_cash_median": max(x["cash_median"] for x in g["rows"]),
                "conditions_with_negative_median_cash": sum(
                    x["cash_median"] < 0 for x in g["rows"]
                ),
                "early_stopped_replicas": sum(
                    x["early_stopped_replicas"] for x in g["rows"]
                ),
            }
        )
    ranking.sort(key=lambda x: x["worst_cash_p10"], reverse=True)
    complete = progress["completed_cases"] == progress["case_count"]
    analysis = {
        "id": cid,
        "classification": "conditional-campaign-comparison",
        "complete": complete,
        "rows": rows,
        "ranking": ranking,
        "candidate": ranking[0]["strategy"] if complete and ranking else None,
        "candidate_rule": "Maior caixa p10 no pior dos casos declarados; critério de triagem, não decisão humana nem otimização universal.",
        "coverage": f"{progress['completed_cases']}/{progress['case_count']}",
        "missing_cases": [
            x["case_id"] for x in progress["cases"] if x["status"] != "completed"
        ],
        "interpretations_pending": [
            x["run_id"] for x in rows if x.get("interpretation_status") != "reviewed"
        ],
        "evidence_hash": s.digest(
            [{k: x[k] for k in ("case_id", "run_id", "result_hash")} for x in rows]
        ),
        "limitations": [
            "Cenários não têm probabilidades implícitas; não calcular chance global a partir da fração de condições favoráveis.",
            "Comparação de robustez entre condições declaradas; não estima demanda real nem substitui validação externa.",
            "Retestar candidatos com novas sementes e condições reservadas antes de recomendar.",
            "Caso ausente ou interrompido não recebe resultado inventado.",
        ],
    }
    with s.lock(project):
        m = s.model(project)
        updated = [
            {**x, "analysis": analysis, "analysis_status": "calculated"}
            if x["id"] == cid
            else x
            for x in m.get("campaigns", [])
        ]
        s.save(
            project,
            {**m, "campaigns": updated},
            "campaign-analyzed",
            {"id": cid, "complete": complete},
        )
    return analysis
