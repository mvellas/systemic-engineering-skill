"""Bounded experimental designs. Planning never authorizes or runs a simulation."""

from __future__ import annotations
from copy import deepcopy
from itertools import product
from math import prod, sqrt
from . import engines, store as s

SCENARIO_FIELDS = {
    "price",
    "variable_cost",
    "fixed_cost",
    "conversion",
    "churn",
    "capacity",
    "acquisition_spend",
    "initial_cash",
    "market_size",
}
CONFIG_FIELDS = {"interaction_strength", "network_topology", "agents"}


def plan(spec):
    if not isinstance(spec, dict) or not isinstance(spec.get("base_config"), dict):
        raise s.Invalid("Forneça base_config como objeto.")
    base = deepcopy(spec["base_config"])
    engines.validate_config(base)
    if base["engine"] != "agents" or len(base["scenarios"]) != 1:
        raise s.Invalid(
            "Planejamento multiagente exige engine=agents e um cenário base."
        )
    if base.get("estimated_cost", 0) or base.get("cost_limit", 0):
        raise s.Invalid(
            "Planejador prepara somente o motor local sem cobrança externa."
        )
    factors = spec.get("factors", [])
    if not isinstance(factors, list) or not 1 <= len(factors) <= 8:
        raise s.Invalid("Declare de 1 a 8 fatores explícitos.")
    paths = []
    for factor in factors:
        if not isinstance(factor, dict):
            raise s.Invalid("Cada fator deve ser um objeto.")
        path = factor.get("parameter", "")
        if not isinstance(path, str):
            raise s.Invalid("Nome do fator deve ser texto.")
        valid = path.startswith("scenario.") and path[9:] in SCENARIO_FIELDS
        valid |= path.startswith("config.") and path[7:] in CONFIG_FIELDS
        if not valid or path in paths:
            raise s.Invalid("Fator desconhecido ou repetido: " + path)
        values = factor.get("values")
        if not isinstance(values, list) or not 1 <= len(values) <= 10:
            raise s.Invalid("Cada fator exige de 1 a 10 valores.")
        refs = factor.get("source_ids")
        if (
            not isinstance(refs, list)
            or not refs
            or any(not isinstance(x, str) or not x.strip() for x in refs)
            or not isinstance(factor.get("rationale"), str)
            or not factor["rationale"].strip()
        ):
            raise s.Invalid(
                "Cada fator exige source_ids e justificativa; hipóteses devem ser identificadas."
            )
        if factor.get("classification") not in {"hypothesis", "estimated", "observed"}:
            raise s.Invalid(
                "Classifique o fator como hypothesis, estimated ou observed."
            )
        if len({s.digest(v) for v in values}) != len(values):
            raise s.Invalid("Valores repetidos não são cenários adicionais.")
        if factor.get("role") not in {None, "decision", "uncertainty", "structural"}:
            raise s.Invalid("role inválido no fator.")
        paths.append(path)
    size = prod(len(f["values"]) for f in factors)
    if size > 256:
        raise s.Invalid(
            "Máximo de 256 combinações por plano; reduza fatores ou níveis."
        )
    trials = spec.get("replicas_per_case", base.get("trials", 100))
    if (
        isinstance(trials, bool)
        or not isinstance(trials, int)
        or not 2 <= trials <= 100000
    ):
        raise s.Invalid("replicas_per_case deve ser inteiro entre 2 e 100000.")
    cases = []
    work = 0
    for index, combination in enumerate(product(*(f["values"] for f in factors)), 1):
        c = deepcopy(base)
        c["trials"] = trials
        assignments = dict(zip(paths, combination))
        for path, value in assignments.items():
            target = c["scenarios"][0] if path.startswith("scenario.") else c
            target[path.split(".")[1]] = value
        c["scenarios"][0]["source_ids"] = sorted(
            set(c["scenarios"][0]["source_ids"])
            | {ref for f in factors for ref in f["source_ids"]}
        )
        engines.validate_config(c)
        operations = trials * c.get("ticks", 12) * c.get("agents", 100)
        if operations > 20_000_000:
            raise s.Invalid(
                "Uma combinação excede 20 milhões de operações de referência."
            )
        work += operations
        cases.append(
            {
                "id": f"CASE-{index:03d}",
                "assignments": assignments,
                "config_hash": s.digest(c),
                "config": c,
            }
        )
    if work > 100_000_000:
        raise s.Invalid(
            "Plano excede 100 milhões de operações de referência; dividir em rodadas."
        )
    return {
        "schema": "sef-agent-experiment-plan-v1",
        "classification": "planned-not-executed",
        "design": "full-factorial",
        "factors": factors,
        "case_count": size,
        "replicas_per_case": trials,
        "trajectory_count": size * trials,
        "operations_upper_reference": work,
        "cases": cases,
        "seed_policy": "Mesma sequência de sementes entre configurações; comparação pareada, sem garantir trajetórias idênticas.",
        "precision_note": {
            "worst_case_success_fraction_standard_error": 0.5 / sqrt(trials),
            "scope": "Apenas variação Monte Carlo para réplicas independentes; não inclui erro do modelo, mercado ou seleção da melhor estratégia.",
        },
        "execution_authorized": False,
        "next_action": "Revisar fatores e fontes; extrair cada config para preflight, aprovação metodológica e autorização de execução específicas.",
        "limitations": [
            "Mais réplicas reduzem ruído numérico, sem validar comportamento humano.",
            "Preço não altera conversão automaticamente: declarar combinações coerentes ou estimar a relação com evidências.",
            "Validar candidatos em novas sementes e condições não usadas para escolher a estratégia.",
            "Comparar múltiplas regras plausíveis e resultados reais antes de alegar previsão de mercado.",
        ],
    }
