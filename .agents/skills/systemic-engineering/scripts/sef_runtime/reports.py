"""One snapshot produces client report, dashboard, artifact chapters and quality receipt."""

from __future__ import annotations
from datetime import date
from pathlib import Path
from html import escape as e
import re, shutil, uuid
from . import store as s, decision, research

SKILL = Path(__file__).resolve().parents[2]

PHASE_LABELS = {
    "intake": "Entendimento inicial",
    "vft": "Objetivos e prioridades",
    "ssm": "Perspectivas e mudanças",
    "reconcile": "Reconciliação das perspectivas",
    "stpa": "Análise de controle e segurança",
    "requirements": "Requisitos da solução",
    "planning": "Planejamento",
    "execution": "Execução acompanhada",
    "closure": "Encerramento",
}
STATUS_LABELS = {
    "interim": "Estudo parcial: há informações a completar",
    "authored-awaiting-human-review": "Análise elaborada: aguarda revisão humana",
    "reviewed-for-client": "Conteúdo revisado para entrega",
}
ENGINE_LABELS = {
    "monte-carlo": "Cenários com incerteza",
    "agents": "Clientes e interações simuladas",
    "dynamics": "Evolução da operação",
    "failure": "Falhas e recuperação",
    "mcmc": "Estimativa de taxa com incerteza",
    "ml": "Previsão exploratória",
    "bdh": "Aprendizado experimental BDH",
    "oasis": "Rede social sintética",
    "matraix": "Avaliação com perfis simulados",
}
WORDS = {
    "observed": "Observado na fonte",
    "hypothesis": "Hipótese a testar",
    "inference": "Interpretação analítica",
    "simulated": "Resultado simulado",
    "high": "alta",
    "medium": "média",
    "low": "baixa",
    "unknown": "não informada",
}


def catalog():
    return s.read(SKILL / "references/biblioteca-documental-generalista/catalogo.json")[
        "documents"
    ]


def sources_html(m, ids):
    known = {x["id"]: x for x in m["sources"]}
    return " ".join(
        '<a class="source-ref" href="#source-'
        + e(i)
        + '">'
        + e(known[i]["title"])
        + "</a>"
        for i in ids
        if i in known
    )


def paragraph(value):
    return "<p>" + e(str(value or "Não informado; investigação pendente.")) + "</p>"


def table(headers, rows):
    return (
        '<div class="table-wrap"><table><thead><tr>'
        + "".join("<th>" + e(str(x)) + "</th>" for x in headers)
        + "</tr></thead><tbody>"
        + "".join(
            "<tr>"
            + "".join(
                "<td>" + e(str(x if x is not None else "Não informado")) + "</td>"
                for x in row
            )
            + "</tr>"
            for row in rows
        )
        + "</tbody></table></div>"
    )


def markdown(text):
    """Small safe renderer: escaped text, headings, lists and pipe tables; no raw HTML."""
    result = []
    rows = []
    paras = []
    code = False

    def flush():
        if paras:
            result.append(paragraph(" ".join(paras)))
            paras.clear()
        if rows:
            clean = [
                r
                for r in rows
                if not all(re.fullmatch(r"[:\- ]+", c or " ") for c in r)
            ]
            width = max(map(len, clean))
            clean = [r + [""] * (width - len(r)) for r in clean]
            result.append(table(clean[0], clean[1:]))
            rows.clear()

    for line in text.splitlines():
        if line.startswith("```"):
            flush()
            code = not code
            continue
        if code:
            result.append("<pre>" + e(line) + "</pre>")
            continue
        if line.strip().startswith("|") and line.strip().endswith("|"):
            if paras:
                flush()
            rows.append([v.strip() for v in line.strip().strip("|").split("|")])
            continue
        if rows:
            flush()
        if line.startswith("#"):
            flush()
            title = line.lstrip("# ").strip()
            result.append("<h3>" + e(title) + "</h3>")
        elif line.startswith(("- ", "* ")):
            flush()
            result.append("<p>• " + e(line[2:]) + "</p>")
        elif line.strip():
            paras.append(line)
        else:
            flush()
    flush()
    return "".join(result)


def quality(project, m=None):
    m = m or s.model(project)
    issues = []
    known = {x["id"] for x in m["sources"]}
    for f in ("problem",):
        if not m.get(f):
            issues.append("Definir problema e pergunta de decisão")
    for k in (
        "diagnosis",
        "recommendation",
        "rationale",
        "alternatives",
        "reversal",
        "next_test",
        "limitations",
    ):
        if not m["analysis"].get(k):
            issues.append(
                "Análise executiva pendente: "
                + {
                    "diagnosis": "diagnóstico",
                    "recommendation": "recomendação",
                    "rationale": "justificativa",
                    "alternatives": "alternativas",
                    "reversal": "condição de revisão",
                    "next_test": "próximo teste",
                    "limitations": "limitações",
                }.get(k, k)
            )
    if (
        not m["analysis"].get("source_ids")
        or set(m["analysis"].get("source_ids", [])) - known
    ):
        issues.append("Recomendação sem fontes externas registradas suficientes.")
    if m["analysis"].get("confidence") not in {"low", "medium", "high"}:
        issues.append("Definir confiança e sua justificativa.")
    for d in catalog():
        a = m["artifacts"].get(d["slug"])
        if not a:
            issues.append(d["title"] + ": avaliar aplicabilidade e produzir análise.")
            continue
        if a.get("applicable") is False:
            if not a.get("reason") or not a.get("reviewed_by"):
                issues.append(d["title"] + ": exclusão sem razão ou revisor.")
            continue
        if not a.get("finding") or not a.get("mechanism") or not a.get("implication"):
            issues.append(
                d["title"] + ": falta achado, mecanismo ou implicação para a decisão."
            )
        if not a.get("source_ids") or set(a.get("source_ids", [])) - known:
            issues.append(d["title"] + ": falta fonte externa registrada.")
        if not a.get("sections") or any(
            not str(a["sections"].get(title, "")).strip() for title, _ in d["sections"]
        ):
            issues.append(d["title"] + ": seções incompletas.")
    findings = [
        a.get("finding") for a in m["artifacts"].values() if a.get("applicable", True)
    ]
    if len(findings) > 1 and len(set(findings)) < len(findings):
        issues.append(
            "Há achados idênticos em documentos distintos; revisar se o texto é específico."
        )
    for campaign in m.get("campaigns", []):
        from . import campaigns

        progress = campaigns.status(project, campaign["id"])
        analysis = campaign.get("analysis", {})
        if progress["completed_cases"] != progress["case_count"] or not analysis.get(
            "complete"
        ):
            issues.append(
                campaign["id"]
                + ": campanha incompleta; não apresentar triagem parcial como recomendação concluída."
            )
        current = [
            {k: x[k] for k in ("case_id", "run_id", "result_hash")}
            for x in progress["cases"]
            if x["status"] == "completed"
        ]
        if analysis.get("evidence_hash") != s.digest(current):
            issues.append(
                campaign["id"] + ": comparar os resultados atuais da campanha."
            )
    for r in m["runs"]:
        if r.get("interpretation_status") != "reviewed":
            issues.append(
                r["id"]
                + ": interpretar resultado e registrar limites antes da recomendação final."
            )
    if any(c["status"] == "pending" for c in m["conflicts"]):
        issues.append(
            "Resolver ou preservar como dissenso explícito as contradições abertas."
        )
    if not m["actions"]:
        issues.append("Plano de ação sem tarefas, responsáveis e prazos.")
    review_state = human_reviews(project, m)
    ready = (
        not issues and not review_state["missing_roles"] and not review_state["fixture"]
    )
    return {
        "status": "reviewed-for-client"
        if ready
        else "interim"
        if issues
        else "authored-awaiting-human-review",
        "issues": issues,
        "client_ready": ready,
        "human_review": review_state,
        "note": "Checagem estrutural não autentica fontes nem substitui revisão substantiva humana vinculada ao hash.",
    }


def simulations(project, m):
    values = []
    paths = list((s.root(project) / "runs").glob("RUN-*/manifest.json"))
    for path in sorted(paths, key=lambda p: s.read(p).get("created_at", "")):
        manifest = s.read(path)
        r = {"id": manifest["id"], "manifest": manifest}
        if manifest["status"] == "completed":
            result = path.parent / "result.json"
            if s.file_hash(result) != manifest["result_hash"]:
                raise s.Invalid("Resultado alterado: " + manifest["id"])
            r["result"] = s.read(result)
        else:
            r["result"] = {
                "engine": manifest["engine"],
                "classification": manifest["status"],
                "limitation": "Tentativa não concluída; não é resultado comportamental ou financeiro.",
            }
        values.append(r)
    return values


def charts_panel():
    return """<div class="toolbar"><label>Execução <select id="run-select"></select></label><label>Cenário <select id="scenario-select"></select></label><label>Indicador <select id="metric-select"><option value="cash">Caixa acumulado</option><option value="cumulative_profit">Resultado operacional acumulado</option><option value="customers">Clientes ativos representados</option><option value="accounts_receivable">Valores a receber</option><option value="accounts_payable">Valores a pagar</option><option value="project_cash_flow">Fluxo de caixa do projeto no período</option></select></label></div>
<div class="toolbar"><button id="play" type="button">Reproduzir</button><label><span id="period-label">Período</span> <input id="period-slider" type="range" min="1" max="12" value="12"></label></div>
<p id="run-note" class="callout"></p><div role="tablist" aria-label="Visualizações" class="toolbar"><button class="tab" data-panel="time-panel" role="tab" aria-selected="true">Evolução</button><button class="tab" data-panel="comparison-panel" role="tab" aria-selected="false">Cenários</button><button class="tab" data-panel="agents-panel" role="tab" aria-selected="false">Interações</button><button class="tab" data-panel="map-panel" role="tab" aria-selected="false">Território</button></div>
<div id="time-panel" class="plot-panel" role="tabpanel"><div id="chart-main" class="chart"></div></div><div id="comparison-panel" class="plot-panel" role="tabpanel" hidden><div id="chart-comparison" class="chart"></div></div><div id="agents-panel" class="plot-panel" role="tabpanel" hidden><div id="chart-agents" class="chart"></div></div><div id="map-panel" class="plot-panel" role="tabpanel" hidden><div id="chart-map" class="chart"></div></div>
<details><summary>Tabela equivalente ao gráfico temporal</summary><div class="table-wrap"><table id="visible-table"><thead><tr><th>Período</th><th>Valor</th><th>Unidade</th></tr></thead><tbody></tbody></table></div></details>"""


def render(project):
    s.integrity(project)
    m = s.model(project)
    q = quality(project, m)
    runs = simulations(project, m)
    state = s.read(s.root(project).parent / "state.json")
    data = {
        "runs": runs,
        "geography": m.get("geography"),
        "campaigns": m.get("campaigns", []),
    }
    body = []
    a = m["analysis"]
    catalogue = catalog()
    token = uuid.uuid4().hex[:12]
    folder = s.root(project) / "exports" / ("PACK-" + token)
    folder.mkdir(parents=True)

    def chapter(id, title, content):
        return (
            '<section class="chapter" id="'
            + e(id)
            + '"><p class="sup">'
            + e(id.replace("-", " "))
            + "</p><h2>"
            + e(title)
            + "</h2>"
            + content
            + "</section>"
        )

    executive = (
        paragraph(m["problem"])
        + '<div class="callout"><strong>Recomendação proposta — decisão humana pendente</strong>'
        + paragraph(a.get("recommendation"))
        + "</div>"
        + paragraph(a.get("rationale"))
        + sources_html(m, a.get("source_ids", []))
        + table(
            ["Confiança declarada", "Condição para rever", "Próximo teste"],
            [[a.get("confidence"), a.get("reversal"), a.get("next_test")]],
        )
        + paragraph(a.get("confidence_reason"))
    )
    body.append(
        chapter(
            "decisao", "O que fazer — e o que ainda precisa ser demonstrado", executive
        )
    )
    body.append(
        chapter(
            "diagnostico",
            "Diagnóstico e evidências",
            paragraph(a.get("diagnosis"))
            + paragraph(a.get("limitations"))
            + table(
                ["Afirmação", "Natureza", "Fontes", "Limites"],
                [
                    [
                        x["text"],
                        WORDS.get(x["kind"], x["kind"]),
                        ", ".join(x["source_ids"]),
                        x["limitations"],
                    ]
                    for x in m["claims"]
                ],
            ),
        )
    )
    people = (
        table(
            ["Quem é afetado", "Papel", "Objetivo", "Perdas ou conflitos"],
            [
                [x.get("name"), x.get("role"), x.get("objective"), x.get("concern")]
                for x in m["stakeholders"]
            ],
        )
        + table(
            ["Objetivo", "Como medir", "Por que importa"],
            [
                [x.get("title"), x.get("measure"), x.get("rationale")]
                for x in m["objectives"]
            ],
        )
        + table(
            ["Resposta", "Natureza", "Participante"],
            [
                [x["text"], WORDS.get(x["kind"], x["kind"]), x["speaker"]]
                for x in m["answers"]
            ],
        )
        + table(
            ["Conflito", "Situação", "Motivo"],
            [[x["id"], x["status"], x.get("reason")] for x in m["conflicts"]],
        )
    )
    body.append(chapter("pessoas", "Pessoas, objetivos e discordâncias", people))
    try:
        cmp = decision.compare(project)
        comp = (
            table(
                ["Alternativa", "Pontuação relativa", "Condição", "Ganhos", "Perdas"],
                [
                    [
                        x["title"],
                        round(x["weighted_score"], 3),
                        "Elegível",
                        x["benefits"],
                        x["losses"],
                    ]
                    for x in cmp["ranking"]
                ],
            )
            + table(
                ["Excluída", "Condição não compensável"],
                [[x["title"], ", ".join(x["vetoes"])] for x in cmp["excluded"]],
            )
            + paragraph(
                "A classificação informa a decisão; não seleciona automaticamente a alternativa."
            )
            + paragraph(" ".join(cmp["limitations"]))
            + table(
                ["Peso alterado", "Valor", "Alternativa favorecida"],
                [
                    [x["criterion"], round(x["weight"], 2), x["winner"]]
                    for x in cmp["sensitivity"]
                ],
            )
        )
    except s.Invalid as error:
        cmp = {"status": "incomplete", "reason": str(error)}
        comp = paragraph(str(error))
    body.append(
        chapter(
            "alternativas",
            "Alternativas e consequências",
            comp + paragraph(a.get("alternatives")),
        )
    )
    artifacts = '<label class="no-print">Buscar documento <input id="search" type="search" placeholder="Nome, achado ou assunto"></label>'
    for d in catalogue:
        item = m["artifacts"].get(d["slug"], {})
        applicable = item.get("applicable", True)
        artifacts += (
            '<article class="artifact" id="doc-'
            + e(d["slug"])
            + '"><span class="status">'
            + (
                "Excluído com justificativa"
                if not applicable
                else "Análise aplicada"
                if item.get("finding")
                else "Investigação pendente"
            )
            + "</span><h3>"
            + e(d["title"])
            + "</h3>"
        )
        if not applicable:
            artifacts += paragraph(item.get("reason")) + paragraph(
                "Revisor: " + str(item.get("reviewed_by", "pendente"))
            )
        else:
            for key, label in [
                ("finding", "Achado"),
                ("mechanism", "Por que pode acontecer"),
                ("implication", "O que isso muda na decisão"),
            ]:
                artifacts += "<h4>" + label + "</h4>" + paragraph(item.get(key))
            artifacts += sources_html(m, item.get("source_ids", []))
            for title, instruction in d["sections"]:
                artifacts += (
                    "<h4>"
                    + e(title)
                    + "</h4>"
                    + paragraph(item.get("sections", {}).get(title))
                )
            canonical_headings = {heading for heading, _ in d["sections"]}
            for heading, value in item.get("sections", {}).items():
                if heading not in canonical_headings:
                    artifacts += "<h4>" + e(heading) + "</h4>" + paragraph(value)
            if item.get("visual"):
                from .visuals import (
                    validate as validate_visual,
                    render as render_visual,
                )

                visual = validate_visual(
                    item["visual"], {x["id"] for x in m["sources"]}
                )
                image = folder / "visuais" / (d["slug"] + "-aplicado.svg")
                image.parent.mkdir(exist_ok=True)
                s.atomic(image, render_visual(visual))
                artifacts += (
                    '<figure><img class="diagram" src="visuais/'
                    + e(image.name)
                    + '" alt="'
                    + e(visual["caption"])
                    + '"><figcaption>'
                    + e(visual["caption"])
                    + sources_html(m, visual["source_ids"])
                    + "</figcaption></figure>"
                )
                if visual["type"] == "matrix":
                    artifacts += table(visual["columns"], visual["rows"])
                elif visual["type"] == "comparison":
                    artifacts += table(
                        ["Alternativa", "Valor", "Unidade"],
                        [
                            [x["label"], x["value"], visual["unit"]]
                            for x in visual["items"]
                        ],
                    )
                else:
                    artifacts += table(
                        ["Etapa", "Descrição"],
                        [[x["id"], x["label"]] for x in visual["nodes"]],
                    )
            # Template diagram remains a labeled planning aid, never passed off as populated evidence.
            asset = folder / "visuais" / (d["slug"] + ".svg")
            asset.parent.mkdir(exist_ok=True)
            shutil.copyfile(
                SKILL
                / "references/biblioteca-documental-generalista/visuais"
                / (d["slug"] + ".svg"),
                asset,
            )
            artifacts += (
                '<details><summary>Estrutura visual de referência — ainda preencher com os dados deste projeto</summary><img class="diagram" src="visuais/'
                + e(d["slug"])
                + '.svg" alt="'
                + e(d["visual"][1])
                + '"><p class="note">Wireframe do modelo; não representa evidência deste projeto.</p></details>'
            )
        document = folder / "documentos" / (d["slug"] + ".md")
        content = (
            "# "
            + m["project_name"]
            + " — "
            + d["title"]
            + "\n\n"
            + ("Exemplo sintético.\n\n" if state["mode"] == "fixture" else "")
        )
        if not applicable:
            content += "Não aplicável: " + str(item.get("reason", "justificar")) + "\n"
        else:
            content += (
                "## Achado\n\n"
                + str(item.get("finding", "Investigação pendente"))
                + "\n\n## Significado para a decisão\n\n"
                + str(item.get("implication", "A definir"))
                + "\n\n"
            )
            content += "".join(
                "## "
                + heading
                + "\n\n"
                + str(item.get("sections", {}).get(heading, "Não informado"))
                + "\n\n"
                for heading, _ in d["sections"]
            )
        content += "## Fontes externas\n\n" + "\n".join(
            "- ["
            + src["title"]
            + "]("
            + src["url"]
            + ") — consulta "
            + src["accessed_at"]
            + "; "
            + src["limitations"]
            for src in m["sources"]
            if src["id"] in item.get("source_ids", [])
        )
        s.atomic(document, content)
        artifacts += (
            '<p class="note">Conexões: '
            + ", ".join(
                '<a href="#doc-' + e(slug) + '">' + e(slug) + "</a>"
                for slug in d["deps"]
            )
            + "</p></article>"
        )
    body.append(chapter("documentos", "Documentos que sustentam a decisão", artifacts))
    sim = charts_panel()
    for r in runs:
        result = r["result"]
        entry = next((x for x in m["runs"] if x["id"] == r["id"]), {})
        sim += (
            "<h3>"
            + e(ENGINE_LABELS.get(result["engine"], result["engine"]))
            + "</h3>"
            + paragraph(result.get("limitation"))
            + paragraph(entry.get("interpretation"))
            + sources_html(m, entry.get("source_ids", []))
        )
        if isinstance(result.get("summary"), list):
            sim += table(
                [
                    "Cenário",
                    "Caixa mediano",
                    "Faixa de caixa (10%–90%)",
                    "Fração que atende ao critério no modelo",
                ],
                [
                    [
                        x["scenario"],
                        round(x["final_cash"]["median"], 2),
                        str(round(x["final_cash"]["p10"], 2))
                        + " a "
                        + str(round(x["final_cash"]["p90"], 2)),
                        str(round(100 * x["conditional_success_fraction"], 1))
                        + "% — condicional, sem calibração de mercado",
                    ]
                    for x in result["summary"]
                ],
            )
        financial_rows = (
            [
                x
                for x in result.get("summary", [])
                if isinstance(x, dict) and x.get("financial")
            ]
            if isinstance(result.get("summary"), list)
            else []
        )
        if financial_rows:
            sim += "<h3>Viabilidade financeira sob as premissas</h3>" + table(
                [
                    "Cenário",
                    "Valor presente mediano",
                    "Capital adicional mediano",
                    "Fração com falta de caixa",
                    "Fração que recupera investimento",
                ],
                [
                    [
                        x["scenario"],
                        round(x["financial"]["net_present_value"]["median"], 2),
                        round(
                            x["financial"]["additional_funding_required"]["median"], 2
                        ),
                        str(
                            round(
                                100
                                * x["financial"]["conditional_cash_shortfall_fraction"],
                                1,
                            )
                        )
                        + "% — condicional",
                        str(round(100 * x["financial"]["payback_reached_fraction"], 1))
                        + "% — condicional",
                    ]
                    for x in financial_rows
                ],
            )
            sim += paragraph(financial_rows[0]["financial"]["scope"])
        if result.get("sensitivity"):
            sim += table(
                ["Cenário", "Parâmetro", "Valor testado", "Variação de caixa"],
                [
                    [
                        x["scenario"],
                        x["parameter"],
                        x["value"],
                        round(x["delta_cash"], 2),
                    ]
                    for x in result["sensitivity"]
                ],
            )
        if result.get("diagnostics"):
            sim += table(
                ["Diagnóstico", "Valor"],
                [(k, str(v)) for k, v in result["diagnostics"].items()],
            )
        if "mae_holdout" in result:
            sim += table(
                [
                    "Erro em dados separados",
                    "Erro da referência simples",
                    "Melhorou a referência?",
                ],
                [
                    [
                        result["mae_holdout"],
                        result["baseline_mean_mae"],
                        result["improves_baseline"],
                    ]
                ],
            )
        if result.get("classification") == "engine-smoke":
            sim += paragraph(
                "Este smoke comprova somente o caminho técnico. Não avaliou consumidores ou estratégias."
            )
    for campaign in m.get("campaigns", []):
        analysis = campaign.get("analysis", {})
        sim += "<h3>Campanha " + e(campaign["id"]) + "</h3>"
        sim += paragraph(
            "Cobertura: "
            + analysis.get("coverage", "planejada, sem comparação")
            + ". Combinações não são probabilidades de mercado."
        )
        if analysis.get("ranking"):
            sim += (
                '<div class="chart" id="chart-campaign-'
                + e(campaign["id"])
                + '"></div>'
            )
            sim += table(
                [
                    "Estratégia",
                    "Condições avaliadas",
                    "Pior caixa p10",
                    "Condições com mediana de caixa negativa",
                ],
                [
                    [
                        str(x["strategy"]),
                        x["evaluated_conditions"],
                        round(x["worst_cash_p10"], 2),
                        x["conditions_with_negative_median_cash"],
                    ]
                    for x in analysis["ranking"]
                ],
            )
            sim += paragraph(analysis["candidate_rule"])
        sim += paragraph(
            "Campanha concluída no modelo; exige interpretação e revisão humana."
            if analysis.get("complete")
            else "Campanha incompleta. Não há recomendação final desta comparação."
        )
    body.append(
        chapter("simulacoes", "O que os cenários mostram — e o que não mostram", sim)
    )
    actions = table(
        ["Ação", "Responsável", "Início", "Prazo", "Indicador e limiar", "Orçamento"],
        [
            [
                x.get("title"),
                x.get("owner"),
                x.get("start"),
                x.get("due"),
                x.get("criterion"),
                x.get("budget"),
            ]
            for x in m["actions"]
        ],
    )
    dated = [x for x in m["actions"] if x.get("start") and x.get("due")]
    if dated:
        first = min(date.fromisoformat(x["start"]) for x in dated)
        last = max(date.fromisoformat(x["due"]) for x in dated)
        span = max(1, (last - first).days)
        actions += "<h3>Cronograma de ação</h3>"
        for x in dated:
            start = date.fromisoformat(x["start"])
            end = date.fromisoformat(x["due"])
            left = max(0, (start - first).days / span * 90)
            width = max(1, (end - start).days / span * 90)
            actions += (
                "<p>"
                + e(x["title"])
                + '</p><div class="gantt-bar" style="margin-left:'
                + str(left)
                + "%;width:"
                + str(min(width, 100 - left))
                + '%"></div>'
            )
        actions += paragraph(
            "Eixo de tempo: "
            + str(first)
            + " a "
            + str(last)
            + ". As datas completas estão na tabela."
        )
    for x in m["actions"]:
        actions += (
            '<div class="todo"><label><input type="checkbox"> '
            + e(x.get("title", "Ação"))
            + '</label><p class="note">'
            + e(str(x.get("criterion", "Definir critério")))
            + "</p></div>"
        )
    actions += '<p class="note">Checklist de leitura temporário: marcar não altera o estado do projeto nem registra aceite.</p>'
    body.append(
        chapter("plano", "Plano de ação, prazos e critérios de parada", actions)
    )
    risks = table(
        [
            "Risco",
            "Probabilidade qualitativa",
            "Impacto",
            "Resposta",
            "Dono",
            "Gatilho",
        ],
        [
            [
                x.get("title"),
                WORDS.get(x.get("likelihood"), x.get("likelihood")),
                WORDS.get(x.get("impact"), x.get("impact")),
                x.get("response"),
                x.get("owner"),
                x.get("trigger"),
            ]
            for x in m["risks"]
        ],
    )
    risks += (
        "<h3>Mapa qualitativo de riscos</h3>"
        + table(
            ["Probabilidade / impacto", "Baixo", "Médio", "Alto"],
            [
                [
                    p,
                    *[
                        ", ".join(
                            x["title"]
                            for x in m["risks"]
                            if x.get("likelihood") == p and x.get("impact") == i
                        )
                        or "—"
                        for i in ("low", "medium", "high")
                    ],
                ]
                for p in ("high", "medium", "low")
            ],
        )
        + paragraph(
            "As categorias dependem da rubrica do projeto. Ausência de classificação não é risco zero."
        )
    )
    body.append(chapter("riscos", "Riscos, limites e condições de revisão", risks))
    trace = table(
        ["Origem", "Relação", "Destino", "Situação"],
        [
            [x.get("from"), x.get("relationship"), x.get("to"), x.get("status")]
            for x in m["relations"]
        ],
    ) + paragraph(
        "A seta de rastreabilidade indica dependência documental. Uma relação causal só pode ser afirmada com mecanismo e evidência adequados."
    )
    for p in sorted(s.root(project).parent.rglob("*.md")):
        if "08-consulting" in p.parts or "gates" in p.parts:
            continue
        trace += (
            "<details><summary>"
            + e(str(p.relative_to(s.root(project).parent)))
            + "</summary>"
            + markdown(p.read_text())
            + "</details>"
        )
    body.append(chapter("rastreabilidade", "Da evidência à recomendação", trace))
    refs = '<ol class="sources">'
    for src in m["sources"]:
        refs += (
            '<li id="source-'
            + e(src["id"])
            + '"><a href="'
            + e(src["url"], quote=True)
            + '" target="_blank" rel="noopener noreferrer">'
            + e(src["title"])
            + "</a>"
            + paragraph(src["evidence"])
            + '<p class="note">Publicação: '
            + e(src["published_at"])
            + " · Consulta: "
            + e(src["accessed_at"])
            + " · Localização: "
            + e(src["location"])
            + " · Confiança: "
            + e(WORDS.get(src["confidence"], src["confidence"]))
            + "</p>"
            + paragraph(src["limitations"])
            + "</li>"
        )
    refs += "</ol>"
    audit = research.audit(project)
    refs += "<h3>Qualidade e lacunas</h3>" + table(
        ["Pendência"], [[x] for x in q["issues"] + audit["issues"]]
    )
    body.append(chapter("fontes", "Fontes, contraprovas e lacunas", refs))
    raw = s.canonical(
        {
            "model": m,
            "comparison": cmp,
            "runs": runs,
            "quality": q,
            "state_phase": state["phase"],
        }
    )
    body.append(
        chapter(
            "anexos",
            "Anexo reproduzível",
            "<details><summary>Dados, versões e rastreabilidade técnica</summary><pre>"
            + e(raw)
            + "</pre></details>",
        )
    )
    data = {**data, "comparison": cmp}
    titles = [
        ("decisao", "Decisão proposta"),
        ("diagnostico", "Diagnóstico"),
        ("pessoas", "Pessoas e objetivos"),
        ("alternativas", "Alternativas"),
        ("documentos", "Documentos"),
        ("simulacoes", "Simulações"),
        ("plano", "Plano de ação"),
        ("riscos", "Riscos"),
        ("rastreabilidade", "Rastreabilidade"),
        ("fontes", "Fontes"),
        ("anexos", "Anexos"),
    ]
    nav = (
        '<div class="toc">'
        + "".join('<a href="#' + i + '">' + t + "</a>" for i, t in titles)
        + "</div>"
    )
    css = (SKILL / "assets/report/report.css").read_text()
    js = (SKILL / "assets/report/report.js").read_text()
    data_safe = (
        s.canonical(data)
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("&", "\\u0026")
    )

    def page(title, content):
        return (
            "<!doctype html><html lang=\"pt-BR\"><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width,initial-scale=1\"><meta http-equiv=\"Content-Security-Policy\" content=\"default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; img-src 'self' data:; connect-src 'none'; base-uri 'none'\"><title>"
            + e(title)
            + " — "
            + e(m["project_name"])
            + "</title><style>"
            + css
            + '</style></head><body><header><div class="shell"><a class="brand" href="#inicio">ESTUDO / '
            + e(m["project_name"])
            + '</a><a href="RELATORIO.html">Relatório</a><a href="DASHBOARD.html">Dashboard</a><a href="#fontes">Fontes</a></div></header><section class="cover" id="inicio"><div class="shell"><p class="sup">Engenharia, evidência e decisão · '
            + e(PHASE_LABELS.get(state["phase"], state["phase"]))
            + "</p><h1>"
            + e(m["project_name"])
            + '</h1><div class="rule"></div><p>'
            + e(title)
            + ". "
            + (
                "Exemplo sintético; nenhuma aprovação real."
                if state["mode"] == "fixture"
                else "Análise para decisão humana."
            )
            + '</p></div></section><main class="shell"><div class="ribbon"><div><strong>'
            + str(len(m["sources"]))
            + "</strong><span>fontes registradas</span></div><div><strong>"
            + str(len(runs))
            + "</strong><span>execuções e tentativas</span></div><div><strong>"
            + str(len(q["issues"]))
            + '</strong><span>pendências analíticas</span></div></div><div class="callout">Estado da entrega: '
            + e(STATUS_LABELS.get(q["status"], q["status"]))
            + ". Nenhuma decisão ou autorização de fase é criada pelo relatório.</div>"
            + "".join(
                '<a href="#' + i + '">' + t + "</a> · "
                for i, t in titles
                if 'id="' + i + '"' in content
            )
            + content
            + '</main><footer><div class="shell">Revisão '
            + str(m["revision"])
            + " · "
            + e(m["language"])
            + ' · Hipótese, simulação e observação permanecem distintas.</div></footer><script id="study-data" type="application/json">'
            + data_safe
            + "</script><script>"
            + js
            + "</script></body></html>"
        )

    s.atomic(
        folder / "RELATORIO.html",
        page("Relatório de decisão fundamentada", "".join(body)),
    )
    s.atomic(
        folder / "DASHBOARD.html",
        page(
            "Cenários e evolução ao longo do tempo",
            body[5] + body[6] + body[7] + body[9],
        ),
    )
    s.atomic(
        folder / "study.json",
        {"model": m, "runs": runs, "quality": q, "comparison": cmp},
    )
    s.atomic(folder / "QUALITY.json", q)
    manifest = {
        "id": folder.name,
        "created_at": s.now(),
        "model_hash": s.digest(m),
        "revision": m["revision"],
        "files": {
            str(p.relative_to(folder)): s.file_hash(p)
            for p in folder.rglob("*")
            if p.is_file()
        },
        "quality": q["status"],
    }
    s.atomic(folder / "manifest.json", manifest)
    s.atomic(
        s.root(project) / "latest-export.json",
        {"path": str(folder.relative_to(s.root(project))), "model_hash": s.digest(m)},
    )
    import zipfile

    archive = folder.parent / (folder.name + "-CLIENTE.zip")
    with zipfile.ZipFile(archive, "x", zipfile.ZIP_DEFLATED) as z:
        for f in folder.rglob("*"):
            if f.is_file():
                z.write(f, str(f.relative_to(folder)))
    return {
        "report": str(folder / "RELATORIO.html"),
        "client_package": str(archive),
        "dashboard": str(folder / "DASHBOARD.html"),
        "quality": q,
        "manifest": str(folder / "manifest.json"),
    }


def review_binding(project, m=None):
    m = m or s.model(project)
    code = {
        p.name: s.file_hash(p)
        for p in [
            Path(__file__),
            SKILL / "assets/report/report.css",
            SKILL / "assets/report/report.js",
        ]
    }
    return s.digest(
        {
            "governance": {
                "risk": s.read(s.root(project).parent / "state.json")["risk_class"],
                "mode": s.read(s.root(project).parent / "state.json")["mode"],
                "authorities": s.file_hash(
                    s.root(project).parent / "00-intake/authorities.csv"
                ),
            },
            "model": m,
            "renderer": code,
            "results": [(r["id"], r.get("result_hash")) for r in m["runs"]],
        }
    )


def human_reviews(project, m=None):
    m = m or s.model(project)
    binding = review_binding(project, m)
    state = s.read(s.root(project).parent / "state.json")
    latest = {}
    for event in s.events(project):
        if event["kind"] == "client-review" and event["payload"]["binding"] == binding:
            latest[event["payload"]["authority_id"]] = event["payload"]
    roles = set()
    if state["mode"] != "fixture":
        for item in latest.values():
            try:
                a = s.authority(project, item["authority_id"], item["by"], "consulting")
                if item["decision"] == "approved":
                    roles.add(a["role"])
            except s.Invalid:
                continue
    required = {"user"}
    if state["risk_class"] == "medium":
        required.add("independent-reviewer")
    if state["risk_class"] in {"high", "safety-critical"}:
        required.add("domain-expert")
    if state["risk_class"] == "safety-critical":
        required.add("safety-authority")
    return {
        "binding": binding,
        "missing_roles": sorted(required - roles),
        "fixture": state["mode"] == "fixture",
    }


def review(project, by, authority_id, evidence, attestation, decision_value):
    a = s.authority(project, authority_id, by, "consulting")
    if len(attestation.strip()) < 12 or not evidence.strip():
        raise s.Invalid(
            "Revisão exige referência e declaração humana específica sobre o conteúdo."
        )
    with s.lock(project):
        s.integrity(project)
        m = s.model(project)
        q = quality(project, m)
        if decision_value == "approved" and q["issues"]:
            raise s.Invalid(
                "Há lacunas analíticas: não registrar aprovação de pacote incompleto."
            )
        item = {
            "binding": review_binding(project, m),
            "by": by,
            "authority_id": authority_id,
            "role": a["role"],
            "evidence": evidence,
            "attestation": attestation,
            "decision": decision_value,
            "fixture": s.read(s.root(project).parent / "state.json")["mode"]
            == "fixture",
        }
        s.append(project, "client-review", item)
    return render(project)
