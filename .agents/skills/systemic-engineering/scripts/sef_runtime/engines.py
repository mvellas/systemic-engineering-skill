"""Reference numerical engines. Conditional exploration, never calibrated market forecasts."""

from __future__ import annotations
import math, random, statistics as st
from . import store as s, finance

LIMIT = "Resultados condicionais às premissas. Frequência simulada não é probabilidade calibrada de sucesso real."


def quantile(values, q):
    v = sorted(values)
    pos = (len(v) - 1) * q
    lo = int(pos)
    hi = min(lo + 1, len(v) - 1)
    return v[lo] + (v[hi] - v[lo]) * (pos - lo)


def summary(values):
    return {
        "p10": quantile(values, 0.1),
        "median": quantile(values, 0.5),
        "p90": quantile(values, 0.9),
        "mean": st.fmean(values),
    }


def validate_config(c):
    if c.get("engine") not in {
        "monte-carlo",
        "agents",
        "dynamics",
        "failure",
        "mcmc",
        "ml",
        "bdh",
        "oasis",
        "matraix",
    }:
        raise s.Invalid("Motor desconhecido.")
    for key, default, lo, hi in [
        ("agents", 100, 1, 1_000_000),
        ("ticks", 12, 1, 1200),
        ("trials", 100, 1, 100_000),
        ("seed", 42, 0, 2**32 - 1),
    ]:
        value = c.get(key, default)
        s.finite(value, key, lo, hi)
        if not isinstance(value, int):
            raise s.Invalid(key + ": inteiro obrigatório.")
    s.finite(c.get("cost_limit", 0), "cost_limit", 0, 1_000_000)
    s.finite(c.get("estimated_cost", 0), "estimated_cost", 0)
    s.finite(c.get("timeout_seconds", 120), "timeout_seconds", 1, 3600)
    if c.get("estimated_cost", 0) > c.get("cost_limit", 0):
        raise s.Invalid("Estimativa excede teto autorizado.")
    if c.get("engine") not in {"oasis", "matraix"} and c.get("cost_limit", 0) != 0:
        raise s.Invalid(
            "Motores locais não cobram API; custo externo só pertence aos adapters."
        )
    if c.get("engine") == "agents":
        if c.get("network_topology", "hybrid") not in {"hybrid", "ring", "random"}:
            raise s.Invalid("network_topology: use hybrid, ring ou random.")
        s.finite(c.get("interaction_strength", 0), "interaction_strength", 0, 1)
    if c.get("engine") in {"monte-carlo", "agents", "dynamics"}:
        if not c.get("scenarios"):
            raise s.Invalid(
                "Forneça cenários explícitos; o motor não inventa preços, custos ou conversão."
            )
        if len(c["scenarios"]) > 30:
            raise s.Invalid("Máximo de 30 cenários por execução.")
        names = []
        for a in c["scenarios"]:
            if "finance" in a:
                finance.validate(a["finance"], c.get("ticks", 12))
            response = a.get("price_response")
            if response is not None:
                if (
                    not isinstance(response, dict)
                    or not response.get("source_ids")
                    or response.get("classification")
                    not in {"hypothesis", "estimated", "observed"}
                ):
                    raise s.Invalid("price_response exige fontes e classificação.")
                s.finite(response.get("reference_price"), "preço de referência", 1e-9)
                s.finite(response.get("elasticity"), "elasticidade", -10, 0)
                if a.get("price", 0) <= 0 or a.get("regions"):
                    raise s.Invalid(
                        "Resposta a preço exige preço positivo e cenário sem modelo regional."
                    )
            for key in (
                "id",
                "price",
                "variable_cost",
                "fixed_cost",
                "initial_cash",
                "market_size",
                "conversion",
                "churn",
                "capacity",
                "acquisition_spend",
                "initial_customers",
                "unit",
                "currency",
                "period",
                "source_ids",
            ):
                if key not in a:
                    raise s.Invalid(f"Cenário sem {key}.")
            if not a["source_ids"]:
                raise s.Invalid("Cenário precisa de fontes/premissas rastreáveis.")
            names.append(a["id"])
            for k in (
                "price",
                "variable_cost",
                "fixed_cost",
                "market_size",
                "capacity",
                "acquisition_spend",
                "initial_customers",
            ):
                s.finite(a[k], k, 0)
            s.finite(a["initial_cash"], "initial_cash")
            for k in ("conversion", "churn", "uncertainty"):
                s.finite(a.get(k, 0), k, 0, 1)
            if a["initial_customers"] > a["market_size"]:
                raise s.Invalid("Clientes iniciais excedem mercado declarado.")
            regions = a.get("regions", [])
            if regions:
                if c["engine"] == "agents":
                    raise s.Invalid(
                        "Este modelo regional exige Monte Carlo ou estoques/fluxos; não inventa comportamento regional dos agentes."
                    )
                if len(regions) > 200 or len({r["id"] for r in regions}) != len(
                    regions
                ):
                    raise s.Invalid("Regiões repetidas ou quantidade excessiva.")
                for r in regions:
                    if not r.get("source_ids"):
                        raise s.Invalid("Região exige fonte/premissa registrada.")
                    s.finite(r.get("market_size"), "mercado regional", 0)
                    s.finite(
                        r.get("initial_customers"),
                        "clientes regionais iniciais",
                        0,
                        r["market_size"],
                    )
                    s.finite(r.get("conversion"), "conversão regional", 0, 1)
                if (
                    abs(sum(r["market_size"] for r in regions) - a["market_size"])
                    > 1e-8
                    or abs(
                        sum(r["initial_customers"] for r in regions)
                        - a["initial_customers"]
                    )
                    > 1e-8
                ):
                    raise s.Invalid(
                        "Mercado e clientes regionais devem reconciliar com o cenário total."
                    )
            if not a["currency"] or not a["period"] or not a["unit"]:
                raise s.Invalid("Unidade, moeda e período obrigatórios.")
        if len({(x["currency"], x["period"], x["unit"]) for x in c["scenarios"]}) != 1:
            raise s.Invalid(
                "Cenários devem usar a mesma moeda, período e unidade para comparação. Faça conversão explícita antes."
            )
        if len(set(names)) != len(names):
            raise s.Invalid("IDs de cenário repetidos.")
        success = c.get("success")
        if not success or success.get("metric") not in {
            "cash",
            "cumulative_profit",
            "customers",
        }:
            raise s.Invalid(
                "Defina success.metric (cash, cumulative_profit ou customers) e threshold antes de executar."
            )
        s.finite(success.get("threshold"), "success.threshold")
    return c


def trajectory(a, c, rng, engine):
    ticks = c.get("ticks", 12)
    n = c.get("agents", 100)
    market = a["market_size"]
    customers = a["initial_customers"]
    cash = finance.initial(a)
    receipts, payments = {}, {}
    profit_total = 0
    rows = []
    statuses = [rng.random() < (customers / max(1, market)) for _ in range(n)]
    regional = {r["id"]: r["initial_customers"] for r in a.get("regions", [])}
    baseline_conversion = a["conversion"]
    conversion = (
        min(1, max(0, rng.gauss(baseline_conversion, a.get("uncertainty", 0))))
        if engine == "monte-carlo"
        or (engine == "agents" and a.get("uncertainty", 0) > 0)
        else baseline_conversion
    )
    for tick in range(1, ticks + 1):
        start = cash
        before = customers
        conversion_t = conversion
        cost_t = a["variable_cost"]
        price_t = a["price"]
        for shock in c.get("shocks", []):
            if shock.get("scenario") not in {None, a["id"]}:
                continue
            if shock["start"] <= tick < shock["start"] + shock["duration"]:
                if shock["parameter"] == "conversion":
                    conversion_t = max(0, min(1, conversion_t * shock["multiplier"]))
                if shock["parameter"] == "variable_cost":
                    cost_t *= shock["multiplier"]
                if shock["parameter"] == "price":
                    price_t *= shock["multiplier"]
        if a.get("price_response"):
            response = a["price_response"]
            if price_t <= 0:
                raise s.Invalid("Resposta de preço não aceita preço zero.")
            conversion_t = min(
                1,
                max(
                    0,
                    conversion_t
                    * (price_t / response["reference_price"]) ** response["elasticity"],
                ),
            )
        if regional:
            multiplier = (
                conversion_t / baseline_conversion if baseline_conversion > 0 else 1
            )
            for r in a["regions"]:
                before_region = regional[r["id"]]
                rate = min(1, max(0, r["conversion"] * multiplier))
                regional[r["id"]] = max(
                    0,
                    min(
                        r["market_size"],
                        before_region * (1 - a["churn"])
                        + (r["market_size"] - before_region) * rate,
                    ),
                )
            customers = sum(regional.values())
        elif engine == "agents":
            previous = list(statuses)
            active = sum(previous) / n
            social = c.get("interaction_strength", 0)
            peers = [rng.randrange(n) for _ in previous]
            topology = c.get("network_topology", "hybrid")
            if topology == "ring":
                contacts = [((i - 1) % n, (i + 1) % n) for i in range(n)]
            elif topology == "random":
                contacts = [(peers[i], rng.randrange(n)) for i in range(n)]
            else:
                contacts = [((i - 1) % n, peers[i]) for i in range(n)]
            statuses = [
                (rng.random() >= a["churn"])
                if yes
                else (
                    rng.random()
                    < max(
                        0,
                        min(
                            1,
                            conversion_t * (0.5 + (i + 1) / n)
                            + social * sum(previous[j] for j in contacts[i]) / 2,
                        ),
                    )
                )
                for i, yes in enumerate(previous)
            ]
            customers = min(market, market * sum(statuses) / n)
        elif engine == "dynamics":
            customers = max(
                0,
                min(
                    market,
                    customers
                    + (market - customers) * conversion_t
                    - customers * a["churn"],
                ),
            )
        else:
            acquired = max(0, (market - customers) * conversion_t)
            retained = customers * (1 - a["churn"])
            customers = max(0, min(market, retained + acquired))
        units = min(customers, a["capacity"])
        unserved = max(0, customers - a["capacity"])
        revenue = units * price_t
        variable = units * cost_t
        outflow = variable + a["fixed_cost"] + a["acquisition_spend"]
        profit = revenue - outflow
        profit_total += profit
        ledger = None
        if a.get("finance"):
            ledger = finance.ledger(
                a["finance"], tick, revenue, outflow, receipts, payments
            )
            profit_total -= profit
            profit = ledger["net_operating_result"]
            profit_total += profit
            cash += ledger["inflows"] - ledger["outflows"]
        else:
            cash += profit
        rows.append(
            {
                "scenario": a["id"],
                "tick": tick,
                "customers": customers,
                "new_net_customers": customers - before,
                "served_units": units,
                "unserved_units": unserved,
                "revenue": revenue,
                "variable_cost": variable,
                "fixed_cost": a["fixed_cost"],
                "acquisition_spend": a["acquisition_spend"],
                "profit": profit,
                "cumulative_profit": profit_total,
                "opening_cash": start,
                "inflows": revenue,
                "outflows": outflow,
                "cash": cash,
                "currency": a["currency"],
                "period": a["period"],
                "classification": "simulated",
            }
        )
        if ledger is not None:
            rows[-1].update(ledger)
            rows[-1]["profit"] = profit
            rows[-1]["cumulative_profit"] = profit_total
        if regional:
            rows[-1]["regional_customers"] = [
                {
                    "region": r["id"],
                    "value": regional[r["id"]],
                    "source_ids": r["source_ids"],
                    "classification": "simulated",
                }
                for r in a["regions"]
            ]
        if engine == "agents":
            rows[-1] = {
                **rows[-1],
                "agent_states": statuses[:80],
                "agent_edges": [
                    {"from": peer, "to": i}
                    for i in range(min(n, 80))
                    for peer in contacts[i]
                    if peer < 80
                ],
            }
        if c.get("stop_cash_below") is not None and cash < c["stop_cash_below"]:
            break
    return rows


def binomial_interval(successes, trials):
    """Wilson 95% interval for conditional Monte Carlo frequency, not market truth."""
    p = successes / trials
    z = 1.959963984540054
    den = 1 + z * z / trials
    centre = (p + z * z / (2 * trials)) / den
    radius = z * math.sqrt(p * (1 - p) / trials + z * z / (4 * trials * trials)) / den
    return {
        "low": max(0, centre - radius),
        "high": min(1, centre + radius),
        "method": "Wilson 95%; apenas erro de amostragem das réplicas condicionais; não inclui incerteza do modelo.",
    }


def business(c):
    engine = c["engine"]
    trials = c.get("trials", 100) if engine in {"monte-carlo", "agents"} else 1
    rng = random.Random(c.get("seed", 42))
    summaries = []
    all_rows = []
    interactions = []
    for a in c["scenarios"]:
        trajectories = [
            trajectory(a, c, random.Random(c.get("seed", 42) + i), engine)
            for i in range(trials)
        ]
        finals = [rows[-1] for rows in trajectories]
        rule = c["success"]
        success = (
            sum(
                x["tick"] == c.get("ticks", 12)
                and x[rule["metric"]] >= rule["threshold"]
                for x in finals
            )
            / trials
        )
        for tick in range(max(len(x) for x in trajectories)):
            existing = [x[tick] for x in trajectories if len(x) > tick]
            # Averages are an ensemble view; terminal values are always summarized separately.
            all_rows.append(
                {
                    **existing[0],
                    **{
                        k: st.fmean(row[k] for row in existing)
                        for k in (
                            "customers",
                            "new_net_customers",
                            "served_units",
                            "unserved_units",
                            "revenue",
                            "variable_cost",
                            "profit",
                            "cumulative_profit",
                            "opening_cash",
                            "inflows",
                            "outflows",
                            "cash",
                        )
                    },
                    "tick": tick + 1,
                    "replicas_present": len(existing),
                }
            )
        if a.get("finance"):
            financial = [finance.metrics(a, rows) for rows in trajectories]
            for mean_row in [r for r in all_rows if r["scenario"] == a["id"]]:
                matching = [
                    traj[mean_row["tick"] - 1]
                    for traj in trajectories
                    if len(traj) >= mean_row["tick"]
                ]
                for key in (
                    "tax_on_revenue",
                    "capital_expenditure",
                    "operating_payments",
                    "accounts_receivable",
                    "accounts_payable",
                    "project_cash_flow",
                    "net_operating_result",
                ):
                    mean_row[key] = st.fmean(row[key] for row in matching)
        if a.get("regions"):
            # Regional means use the same replicas as the total for each period.
            for mean_row in [r for r in all_rows if r["scenario"] == a["id"]]:
                matching = [
                    traj[mean_row["tick"] - 1]
                    for traj in trajectories
                    if len(traj) >= mean_row["tick"]
                ]
                mean_row["regional_customers"] = [
                    {
                        **item,
                        "value": st.fmean(
                            next(
                                x["value"]
                                for x in rr["regional_customers"]
                                if x["region"] == item["region"]
                            )
                            for rr in matching
                        ),
                    }
                    for item in mean_row["regional_customers"]
                ]
        summaries.append(
            {
                "scenario": a["id"],
                "final_cash": summary([x["cash"] for x in finals]),
                "final_profit": summary([x["cumulative_profit"] for x in finals]),
                "final_customers": summary([x["customers"] for x in finals]),
                "conditional_success_fraction": success,
                "monte_carlo_precision": binomial_interval(
                    round(success * trials), trials
                )
                if engine in {"agents", "monte-carlo"}
                else None,
                "success_rule": rule,
                "horizon_completed_replicas": sum(
                    x["tick"] == c.get("ticks", 12) for x in finals
                ),
                "early_stopped_replicas": sum(
                    x["tick"] < c.get("ticks", 12) for x in finals
                ),
                "trials": trials,
                "currency": a["currency"],
                "period": a["period"],
                "source_ids": a["source_ids"],
            }
        )
        if a.get("finance"):
            summaries[-1]["financial"] = {
                **{
                    key: summary([x[key] for x in financial])
                    for key in (
                        "net_present_value",
                        "minimum_cash",
                        "additional_funding_required",
                        "final_accounts_receivable",
                        "final_accounts_payable",
                    )
                },
                "conditional_negative_npv_fraction": sum(
                    x["net_present_value"] < 0 for x in financial
                )
                / trials,
                "conditional_cash_shortfall_fraction": sum(
                    x["minimum_cash"] < 0 for x in financial
                )
                / trials,
                "payback_reached_fraction": sum(x["payback_reached"] for x in financial)
                / trials,
                "payback_period_when_reached": summary(
                    [x["payback_period"] for x in financial if x["payback_reached"]]
                )
                if any(x["payback_reached"] for x in financial)
                else None,
                "break_even_units_per_period": financial[0][
                    "break_even_units_per_period"
                ],
                "break_even_scope": financial[0]["break_even_scope"],
                "scope": financial[0]["scope"],
                "discount_rate_per_period": a["finance"]["discount_rate_per_period"],
            }
        if engine == "agents":
            # Aggregate influence was used in the transition rule, not invented interpersonal messages.
            interactions.append(
                {
                    "scenario": a["id"],
                    "network_topology": c.get("network_topology", "hybrid"),
                    "mechanism": {
                        "hybrid": "influência do vizinho anterior e de um contato amostrado; propensão heterogênea por agente",
                        "ring": "influência dos dois vizinhos no anel; propensão heterogênea por agente",
                        "random": "influência de dois contatos amostrados por período; propensão heterogênea por agente",
                    }[c.get("network_topology", "hybrid")],
                    "interaction_strength": c.get("interaction_strength", 0),
                    "represented_agents": c.get("agents", 100),
                    "weight": a["market_size"] / c.get("agents", 100),
                    "individual_trajectories_available": True,
                    "display_sample_limit": 80,
                }
            )
    sensitivities = []
    for item in c.get("sensitivity", []):
        if item.get("parameter") not in {
            "price",
            "variable_cost",
            "fixed_cost",
            "conversion",
            "churn",
            "capacity",
            "acquisition_spend",
        }:
            raise s.Invalid("Parâmetro de sensibilidade não suportado.")
        for a in c["scenarios"]:
            base = trajectory(
                a, {**c, "engine": "dynamics"}, random.Random(0), "dynamics"
            )[-1]["cash"]
            for value in item["values"]:
                s.finite(
                    value,
                    "sensitivity",
                    0,
                    1 if item["parameter"] in {"conversion", "churn"} else None,
                )
                changed = {**a, item["parameter"]: value}
                out = trajectory(changed, c, random.Random(0), "dynamics")[-1]["cash"]
                sensitivities.append(
                    {
                        "scenario": a["id"],
                        "parameter": item["parameter"],
                        "value": value,
                        "cash": out,
                        "delta_cash": out - base,
                        "method": "one-at-a-time deterministic stock-flow; not MC uncertainty",
                    }
                )
    return {
        "engine": engine,
        "classification": "synthetic-conditional",
        "limitation": LIMIT,
        "accounting_scope": "Finance opcional: investimento, CAPEX, taxa sobre receita e defasagens explícitas. Sem finance, recebimento e pagamento no mesmo período. Não inclui financiamento, estoque, depreciação ou legislação tributária automática; resultado operacional modelado não é lucro contábil certificado.",
        "summary": summaries,
        "timeseries": all_rows,
        "regional_timeseries": [
            {
                **region,
                "scenario": row["scenario"],
                "tick": row["tick"],
                "unit": "clientes ativos representados",
                "metric": "Adoção regional sob premissas",
            }
            for row in all_rows
            for region in row.get("regional_customers", [])
        ],
        "sensitivity": sensitivities,
        "interactions": interactions,
        "reconciliation_max_error": max(
            abs(row["opening_cash"] + row["inflows"] - row["outflows"] - row["cash"])
            for row in all_rows
        ),
    }


def failure(c):
    nodes = c.get("nodes", [])
    edges = c.get("edges", [])
    if not nodes or len(nodes) > 500:
        raise s.Invalid("Defina 1–500 componentes.")
    names = [n["id"] for n in nodes]
    if len(set(names)) != len(names):
        raise s.Invalid("Componente repetido.")
    for n in nodes:
        s.finite(n["failure_probability"], "failure_probability", 0, 1)
        s.finite(n["recovery_probability"], "recovery_probability", 0, 1)
    for e in edges:
        if e["from"] not in names or e["to"] not in names:
            raise s.Invalid("Aresta de falha tem componente desconhecido.")
        s.finite(e["probability"], "edge probability", 0, 1)
    rows = []
    totals = []
    for trial in range(c.get("trials", 100)):
        rng = random.Random(c.get("seed", 42) + trial)
        failed = set()
        for tick in range(c.get("ticks", 12)):
            previous = set(failed)
            failed = {
                n["id"]
                for n in nodes
                if (
                    rng.random() >= n["recovery_probability"]
                    if n["id"] in previous
                    else rng.random() < n["failure_probability"]
                )
            }
            failed |= {
                e["to"]
                for e in edges
                if e["from"] in previous and rng.random() < e["probability"]
            }
            rows.append(
                {
                    "trial": trial,
                    "tick": tick + 1,
                    "failed": sorted(failed),
                    "count": len(failed),
                }
            )
        totals.append(len(failed))
    return {
        "engine": "failure",
        "classification": "synthetic-conditional",
        "limitation": "Propagação probabilística de referência; não substitui STPA, teste de segurança ou aceite por autoridade. "
        + LIMIT,
        "summary": summary(totals),
        "timeseries": rows,
        "edges": edges,
    }


def mcmc(c):
    d = c.get("observations", {})
    success = d.get("successes")
    n = d.get("trials")
    s.finite(success, "successes", 0)
    s.finite(n, "observed trials", 1)
    if int(success) != success or int(n) != n or success > n:
        raise s.Invalid("Contagens observadas inválidas.")
    if not d.get("source_ids"):
        raise s.Invalid("MCMC exige origem das observações; não inventar amostra.")
    alpha = s.finite(c.get("prior_alpha", 1), "prior_alpha", 0.001)
    beta = s.finite(c.get("prior_beta", 1), "prior_beta", 0.001)
    steps = c.get("trials", 2000)
    warm = c.get("warmup", steps // 2)
    chains = c.get("chains", 4)
    if (
        not isinstance(warm, int)
        or not 0 <= warm < steps - 10
        or chains not in range(2, 9)
    ):
        raise s.Invalid("MCMC exige 2–8 cadeias e ao menos 10 amostras após warmup.")
    sd = s.finite(c.get("proposal_sd", 0.08), "proposal_sd", 0.00001, 1)

    def target(p):
        return (success + alpha - 1) * math.log(p) + (
            n - success + beta - 1
        ) * math.log1p(-p)

    samples = []
    acceptance = []
    for chain in range(chains):
        rng = random.Random(c.get("seed", 42) + chain)
        p = (chain + 1) / (chains + 1)
        arr = []
        accepted = 0
        for t in range(steps):
            proposal = p + rng.gauss(0, sd)
            if 0 < proposal < 1 and math.log(max(rng.random(), 1e-300)) < target(
                proposal
            ) - target(p):
                p = proposal
                accepted += 1
            if t >= warm:
                arr.append(p)
        samples.append(arr)
        acceptance.append(accepted / steps)
    half = len(samples[0]) // 2
    split = [part for a in samples for part in (a[:half], a[-half:])]
    means = [st.fmean(a) for a in split]
    W = st.fmean(st.variance(a) for a in split)
    B = half * st.variance(means)
    varhat = (half - 1) / half * W + B / half
    rhat = math.sqrt(varhat / W) if W else None
    # Conservative initial-positive-sequence estimate, not rank-normalized Stan diagnostics.
    taus = []
    for arr in samples:
        mean = st.fmean(arr)
        var = sum((v - mean) ** 2 for v in arr) / len(arr)
        rho = []
        for lag in range(1, min(300, len(arr) // 2)):
            corr = (
                sum(
                    (arr[i] - mean) * (arr[i + lag] - mean)
                    for i in range(len(arr) - lag)
                )
                / ((len(arr) - lag) * var)
                if var
                else 1
            )
            if corr <= 0:
                break
            rho.append(corr)
        taus.append(1 + 2 * sum(rho))
    ess = sum(len(a) / tau for a, tau in zip(samples, taus))
    flat = [v for a in samples for v in a]
    diagnostic = (
        "insufficient"
        if rhat is None or rhat > 1.01 or ess < 400
        else "preliminary-pass"
    )
    return {
        "engine": "mcmc",
        "classification": "posterior-under-binomial-model",
        "posterior": summary(flat),
        "analytical_beta_mean": (success + alpha) / (n + alpha + beta),
        "diagnostics": {
            "split_rhat": rhat,
            "approximate_ess": ess,
            "acceptance": acceptance,
            "status": diagnostic,
        },
        "chains": samples,
        "observations": d,
        "limitation": "Modelo binomial com prior Beta e Metropolis-Hastings. R-hat simples e ESS aproximado não substituem diagnóstico rank-normalizado robusto. Posterior de uma taxa não equivale a sucesso comercial; adequação depende da amostragem.",
    }
