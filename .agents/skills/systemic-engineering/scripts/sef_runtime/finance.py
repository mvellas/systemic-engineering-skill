"""Explicit project cash ledger; excludes debt, inventory and tax advice."""

from __future__ import annotations
from . import store as s


def validate(f, ticks):
    if not isinstance(f, dict):
        raise s.Invalid("finance deve ser objeto com premissas explícitas.")
    required = {
        "initial_investment",
        "discount_rate_per_period",
        "revenue_tax_rate",
        "collection_lag",
        "operating_payment_lag",
        "capex",
        "source_ids",
        "limitations",
    }
    if f.keys() - required:
        raise s.Invalid(
            "Campo financeiro não implementado: "
            + ", ".join(sorted(f.keys() - required))
        )
    if required - f.keys():
        raise s.Invalid("finance incompleto: " + ", ".join(sorted(required - f.keys())))
    if (
        not isinstance(f["source_ids"], list)
        or not f["source_ids"]
        or any(not isinstance(x, str) or not x for x in f["source_ids"])
    ):
        raise s.Invalid("Financeiro exige referências de fonte/premissa.")
    if not isinstance(f["limitations"], str) or not f["limitations"].strip():
        raise s.Invalid("Explicitar limites financeiros e tributários.")
    s.finite(f["initial_investment"], "investimento inicial", 0)
    s.finite(f["discount_rate_per_period"], "desconto por período", 0, 10)
    s.finite(f["revenue_tax_rate"], "taxa sobre receita", 0, 1)
    for k in ("collection_lag", "operating_payment_lag"):
        if (
            isinstance(f[k], bool)
            or not isinstance(f[k], int)
            or not 0 <= f[k] <= ticks
        ):
            raise s.Invalid(k + ": inteiro entre zero e o horizonte.")
    if not isinstance(f["capex"], list) or len(f["capex"]) > ticks:
        raise s.Invalid("capex deve ser lista limitada ao horizonte.")
    used = set()
    for x in f["capex"]:
        if (
            not isinstance(x, dict)
            or isinstance(x.get("tick"), bool)
            or not isinstance(x.get("tick"), int)
            or not 1 <= x["tick"] <= ticks
            or x["tick"] in used
        ):
            raise s.Invalid("CAPEX exige período único dentro do horizonte.")
        s.finite(x.get("amount"), "CAPEX", 0)
        used.add(x["tick"])
    return f


def initial(a):
    f = a.get("finance")
    return a["initial_cash"] - (f["initial_investment"] if f else 0)


def ledger(f, tick, revenue, operating_expense, receipts, payments):
    """Queues contain amounts due at exact periods; no implicit settlement at horizon."""
    receipts[tick + f["collection_lag"]] = revenue
    payments[tick + f["operating_payment_lag"]] = operating_expense
    collected = receipts.pop(tick, 0)
    paid = payments.pop(tick, 0)
    tax = revenue * f["revenue_tax_rate"]
    capex = next((x["amount"] for x in f["capex"] if x["tick"] == tick), 0)
    return {
        "inflows": collected,
        "outflows": paid + tax + capex,
        "tax_on_revenue": tax,
        "capital_expenditure": capex,
        "operating_payments": paid,
        "accounts_receivable": sum(receipts.values()),
        "accounts_payable": sum(payments.values()),
        "project_cash_flow": collected - paid - tax - capex,
        "net_operating_result": revenue - operating_expense - tax,
    }


def metrics(a, rows):
    f = a["finance"]
    investment = f["initial_investment"]
    npv = -investment
    undiscounted = -investment
    payback = 0 if investment == 0 else None
    for row in rows:
        npv += row["project_cash_flow"] / (
            (1 + f["discount_rate_per_period"]) ** row["tick"]
        )
        undiscounted += row["project_cash_flow"]
        if payback is None and undiscounted >= 0:
            payback = row["tick"]
    minimum = min(initial(a), *(r["cash"] for r in rows))
    margin = a["price"] * (1 - f["revenue_tax_rate"]) - a["variable_cost"]
    return {
        "net_present_value": npv,
        "minimum_cash": minimum,
        "additional_funding_required": max(0, -minimum),
        "payback_period": payback,
        "payback_reached": payback is not None,
        "break_even_units_per_period": (a["fixed_cost"] + a["acquisition_spend"])
        / margin
        if margin > 0
        else None,
        "break_even_scope": "Margem e custos do cenário base, antes dos choques; exclui CAPEX, financiamento e recuperação do investimento.",
        "final_accounts_receivable": rows[-1]["accounts_receivable"],
        "final_accounts_payable": rows[-1]["accounts_payable"],
        "discount_rate_per_period": f["discount_rate_per_period"],
        "initial_investment": investment,
        "scope": "VPL do fluxo de caixa do projeto, sem financiamento, estoque, depreciação ou valor terminal. Saldos a receber/pagar são divulgados e não liquidados artificialmente.",
    }
