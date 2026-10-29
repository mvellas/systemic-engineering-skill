#!/usr/bin/env python3
"""Run an explicitly synthetic, zero-cost consulting example. Never approve a live project."""

from __future__ import annotations
from pathlib import Path
from datetime import date, timedelta
import argparse, csv, io, json, subprocess, sys

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / ".agents/skills/systemic-engineering"
sys.path.insert(0, str(SKILL / "scripts"))
import sef
from sef_runtime import store as s, interview, research, simulation, reports, decision

PROJECTS = {
    "business": (
        "Oficina de reparos — estudo demonstrativo",
        "Comparar atendimento por agendamento com expansão imediata, reduzindo espera sem comprometer caixa.",
        "serviço de reparo",
    ),
    "software": (
        "Fila de suporte — estudo demonstrativo",
        "Comparar triagem assistida com contratação imediata, preservando revisão humana e prazo de atendimento.",
        "atendimento concluído",
    ),
    "critical": (
        "Intertravamento de bomba — estudo demonstrativo",
        "Comparar monitoramento e intertravamento de uma bomba em ambiente de teste; execução física depende de especialista e autoridade de segurança.",
        "ciclo de teste",
    ),
}


def call(*args, allowed=(0,)):
    r = subprocess.run(
        [sys.executable, str(SKILL / "scripts/sef.py"), *map(str, args)],
        capture_output=True,
        text=True,
    )
    if r.returncode not in allowed:
        raise RuntimeError(r.stdout + r.stderr)
    try:
        return json.loads(r.stdout) if r.stdout else {}
    except json.JSONDecodeError:
        return {"message": r.stdout.strip()}


def write_csv(path, fields, rows):
    out = io.StringIO()
    w = csv.DictWriter(out, fieldnames=fields)
    w.writeheader()
    w.writerows(rows)
    s.atomic(path, out.getvalue())


def phases(project, kind):
    """Curated synthetic phase packets. No actual stakeholder or expert approves anything."""
    control = project / ".systemic-engineering"
    name = PROJECTS[kind][0]
    texts = {
        "intake": "# Escopo da fixture\n\nSRC-MODEL STK-001 Patrocinador sintético. VAL-001 Continuidade. OBJ-001 Comparar alternativas sem ultrapassar limites de caixa e segurança. Ambiente de demonstração, sem implantação, clientes reais, dados pessoais ou autorização externa. A decisão humana real permanece pendente.",
        "vft": "# Valores e objetivos — fixture\n\nSTK-001 Patrocinador simulado; VAL-001 Continuidade; OBJ-001 manter operação e aprender antes de expandir. A medida é o caixa e a capacidade por período, nos cenários declarados. OBJ-002 reduzir tempo sem retirar revisão humana. Status quo e piloto são alternativas. Pesos são hipóteses didáticas, não preferências de um cliente entrevistado.",
        "ssm": "# Visões e transformação — fixture\n\nSSM-001 transformar atendimento sem agenda em fluxo acompanhado; cliente recebe serviço, equipe realiza a transformação e patrocinador pode pará-la. A equipe quer reduzir sobrecarga; patrocinador quer caixa. Não se presume consenso. OBJ-001 e VAL-001 são provisórios. Limites externos e necessidades de acessibilidade exigem pesquisa posterior.",
        "reconcile": "# Reconciliação VFT/SSM — fixture\n\nSSM-001 acrescenta OBJ-002 proteção contra sobrecarga da equipe. OBJ-001 é retido com dissenso sobre velocidade de expansão; os pesos da demonstração não são decisão real. STK-001 mantém VAL-001 como prioridade simulada. Em projeto real, revalidar objetivos e obter aprovação humana antes da análise de controle.",
        "stpa": "# Análise de controle — fixture de software\n\nLOSS-001 interrupção do atendimento. HAZ-001 solicitações sem revisão enquanto carga supera capacidade. SC-001 limitar carga e preservar revisão humana. CA-001 liberar atendimento; UCA-001 liberar quando não há capacidade; CS-001 informação de carga atrasada induz liberação inadequada. Controlador recebe estado da fila, compara com capacidade e bloqueia liberação até atualização. Ação insegura deve ser tratada no contexto e tempo, não apenas como falha de componente. Esta fixture não certifica segurança.\n\n| Etapa | Prompt/entrada | Saida | Decisao | Aprovador | Data |\n|---|---|---|---|---|---|\n"
        + "".join(
            f"| {i} | fixture | análise de controle | approved | Fixture Human | 2026-10-29 |\n"
            for i in range(1, 6)
        ),
    }
    if kind == "critical":
        texts["intake"] = (
            "# Escopo da fixture crítica\n\nSRC-MODEL STK-001 Operador da bancada; VAL-001 proteção contra atuação insegura; OBJ-001 evitar liberação indevida da bomba. Apenas análise documental e simulação seriam consideradas; nenhum ensaio físico foi autorizado. Especialista e autoridade de segurança permanecem não designados."
        )
        texts["vft"] = (
            "# Valores — fixture crítica\n\nSTK-001 considera VAL-001 evitar dano e OBJ-001 impedir atuação em condição desconhecida como prioridades não compensáveis. OBJ-002 compreender limites e feedback antes de qualquer teste. Valores e medidas são propostas didáticas; limites numéricos dependem de especialista. Não há decisão de implantação."
        )
        texts["ssm"] = (
            "# Perspectivas — fixture crítica\n\nSSM-001 transformar uma proposta de ensaio sem limites em análise revisável antes de atuação. Operador executaria, pessoa próxima seria afetada e autoridade pode interromper. A perspectiva de aprendizado precisa ser confrontada com exposição física. Nenhum consenso nem competência de domínio foi presumido."
        )
        texts["reconcile"] = (
            "# Reconciliação — fixture crítica\n\nSSM-001 reforça OBJ-001 e VAL-001. OBJ-002 é necessário antes de planejar teste físico. Manter dissenso sobre cronograma: urgência do patrocinador não reduz necessidade de especialista. A baseline desta fixture serve apenas para mostrar o bloqueio, não para legitimar um ensaio."
        )
        texts["stpa"] = (
            "# Proposta STPA — fixture crítica bloqueada\n\nLOSS-001 dano por atuação indevida. HAZ-001 bomba energizada em manutenção ou condição de fluxo desconhecida. SC-001 impedir liberação sem estado válido e autorização. CA-001 energizar; UCA-001 energizar com condição inadequada; CS-001 feedback atrasado indica disponibilidade inexistente. Controlador, sensor e atuador precisam de análise de tempo e contexto. Parâmetros físicos e aceite dependem de especialista; esta análise não foi aprovada por autoridade qualificada."
        )
    for phase in sef.PHASES:
        if phase == "closure":
            break
        if phase in texts:
            path = control / sef.REQUIRED[phase][0]
            s.atomic(path, texts[phase])
        if phase == "stpa" and kind == "critical":
            # The entire point of this fixture is to show the qualified-authority stop.
            return {
                "phase": "stpa",
                "blocked_as_designed": True,
                "gate": call("status", project),
            }
        if phase == "requirements":
            template = SKILL / "assets/templates/requirements.csv"
            fields = next(csv.reader(template.open()))
            row = {k: "" for k in fields}
            row.update(
                {
                    "requirement_id": "REQ-001",
                    "level": "system",
                    "statement": "The controller shall reject a new request when measured workload exceeds configured capacity.",
                    "type": "functional",
                    "source_ids": "CS-001 OBJ-001",
                    "origin": "OBJ-001",
                    "rationale": "Preserve capacity and safe review in this fixture.",
                    "assumptions": "Synthetic fixture only",
                    "allocation": "controller",
                    "interfaces": "queue sensor",
                    "verification_method": "test",
                    "verification_criterion": "Rejected for overloaded fixture; allowed within capacity.",
                    "validation_link": "OBJ-001 VAL-001",
                    "priority": "must",
                    "risk": "medium",
                    "owner": "STK-001",
                    "status": "approved",
                    "constraint_class": "ordinary",
                    "waiver_policy": "controlled",
                    "threshold_source": "not-applicable",
                    "blocked_by": "none",
                    "decision_ids": "DEC-001",
                    "actor": "controller",
                    "condition": "workload above configured capacity",
                    "action": "reject",
                    "object": "new request",
                    "constraint": "fixture capacity",
                    "refinement": "not-applicable",
                }
            )
            write_csv(control / "04-requirements/requirements.csv", fields, [row])
            write_csv(
                control / "04-requirements/decisions.csv",
                [
                    "decision_id",
                    "title",
                    "status",
                    "owner",
                    "authority_id",
                    "evidence",
                    "affected_ids",
                    "rationale",
                ],
                [
                    {
                        "decision_id": "DEC-001",
                        "title": "Synthetic scope decision",
                        "status": "approved",
                        "owner": "STK-001",
                        "authority_id": "AUTH-U",
                        "evidence": "fixture-only",
                        "affected_ids": "REQ-001 OBJ-002",
                        "rationale": "OBJ-002 fora do escopo desta implementação de demonstração.",
                    }
                ],
            )
            links = [
                ("OBJ-001", "CS-001", "frames"),
                ("CS-001", "REQ-001", "mitigated_by"),
                ("REQ-001", "TST-001", "verified_by"),
            ]
            write_csv(
                control / "04-requirements/traceability.csv",
                [
                    "from_id",
                    "to_id",
                    "relationship",
                    "rationale",
                    "source_id",
                    "status",
                ],
                [
                    dict(
                        zip(
                            [
                                "from_id",
                                "to_id",
                                "relationship",
                                "rationale",
                                "source_id",
                                "status",
                            ],
                            (*v, "Synthetic trace", "SRC-MODEL", "planned"),
                        )
                    )
                    for v in links
                ],
            )
            s.atomic(
                control / "04-requirements/requirements-log.md",
                "# Registro de requisitos — fixture\n\nTST-001 é teste da rejeição por carga. Avaliação de qualidade da fixture demonstra formato, não auditoria profissional.\n\n| Etapa | Prompt/entrada | Saida | Decisao | Aprovador | Data |\n|---|---|---|---|---|---|\n| 6 | fixture | requisito | approved | Fixture Human | 2026-10-29 |\n| 7 | fixture | revisão | approved | Fixture Human | 2026-10-29 |\n",
            )
            fields = next(csv.reader((SKILL / "assets/templates/quality.csv").open()))
            score = {k: "1" for k in fields}
            score.update(
                requirement_id="REQ-001",
                scorer="synthetic-fixture-not-human-quality-review",
                omission_ratio="0",
                notes="Pontuações demonstrativas; não são avaliação humana real.",
                rewrite="",
            )
            write_csv(control / "04-requirements/quality.csv", fields, [score])
        if phase == "planning":
            write_csv(
                control / "05-planning/modules.csv",
                ["module_id", "name", "path", "material", "rationale"],
                [
                    {
                        "module_id": "SYS",
                        "name": "Single bounded demonstrator",
                        "path": "",
                        "material": "false",
                        "rationale": "No separately material modules in this isolated fixture.",
                    }
                ],
            )
            for artifact in ("PRD", "SPEC", "TESTS", "SPRINTS", "TASKS"):
                s.atomic(
                    control / f"05-planning/system/{artifact}.md",
                    f"# {artifact} — {name}\n\nREQ-001 is allocated to SPEC-001; TST-001 verifies overloaded rejection. SPR-001 contains TSK-001. Scope is an isolated software demonstrator with no physical execution. EVD-001 stores the actual local condition check; rollback removes only the temporary demonstration. A real project requires independent domain validation.",
                )
        if phase == "execution":
            observed = 3 > 2 and not 1 > 2
            s.atomic(
                control / "06-execution/test-result.json",
                {
                    "test": "TST-001",
                    "overloaded_rejected": 3 > 2,
                    "within_capacity_rejected": 1 > 2,
                    "pass": observed,
                    "limitation": "Boolean fixture, not implementation certification.",
                },
            )
            write_csv(
                control / "06-execution/evidence-register.csv",
                [
                    "evidence_id",
                    "task_id",
                    "requirement_ids",
                    "command_or_method",
                    "result",
                    "artifact_path",
                    "observed_at",
                    "reviewer",
                ],
                [
                    {
                        "evidence_id": "EVD-001",
                        "task_id": "TSK-001",
                        "requirement_ids": "REQ-001",
                        "command_or_method": "local boolean fixture condition check",
                        "result": "pass" if observed else "fail",
                        "artifact_path": "06-execution/test-result.json",
                        "observed_at": "2026-10-29",
                        "reviewer": "synthetic-fixture",
                    }
                ],
            )
        call(
            "approve",
            project,
            "--phase",
            phase,
            "--by",
            "Fixture Human",
            "--role",
            "user",
            "--authority-id",
            "AUTH-U",
            "--evidence",
            "fixture-only",
            "--fixture",
            "--decision",
            "approved",
            "--note",
            "Synthetic evaluation only; no real human or safety approval.",
        )
        result = call("advance", project, allowed=(0, 2))
        if result.get("status") == "warnings":
            result = call(
                "advance",
                project,
                "--acknowledge-warnings",
                "Fixture actor accepts warnings for isolated software demonstration, not a real project.",
            )
    if kind != "critical":
        s.atomic(
            control / "07-closure/acceptance.md",
            "# Encerramento da fixture\n\nA cadeia de fases foi exercitada com aprovações fictícias rotuladas. O resultado demonstra integração de ferramentas e bloqueios; não aceita nenhum sistema ou estratégia real. O usuário real ainda precisa revisar os achados e fontes.",
        )
        s.atomic(
            control / "07-closure/residual-risk.md",
            "# Risco residual\n\nDados de adoção, preços, custos e critérios desta fixture são sintéticos. Teste real, análise profissional e consentimentos permanecem pendentes; os resultados não justificam implantação física ou comprometimento financeiro.",
        )
    return {"phase": call("status", project)["phase"], "blocked_as_designed": False}


def run(output, kind, viability=False):
    project = Path(output).resolve()
    if project.exists():
        raise ValueError(
            "Choose a new directory; examples never overwrite existing projects."
        )
    title, problem, unit = PROJECTS[kind]
    call("init", project, "--name", title, "--mode", "fixture")
    control = project / ".systemic-engineering"
    write_csv(
        control / "00-intake/authorities.csv",
        ["authority_id", "name", "role", "scope", "evidence", "status"],
        [
            {
                "authority_id": "AUTH-U",
                "name": "Fixture Human",
                "role": "user",
                "scope": "all",
                "evidence": "fixture-only",
                "status": "active",
            }
        ],
    )
    call(
        "set-risk",
        project,
        "--class",
        "safety-critical" if kind == "critical" else "low",
        "--rationale",
        "Isolated synthetic demonstration; critical example remains blocked without specialists.",
    )
    s.enable(project)
    external = [
        (
            "SRC-MODEL",
            "NASA — Model credibility",
            "https://standards.nasa.gov/standard/NASA/NASA-STD-7009",
            "2024-03-05",
            "NASA",
            "Acceptance criteria and credibility apply to the intended use of a model.",
        ),
        (
            "SRC-MCDA",
            "UK — Comparing options",
            "https://www.gov.uk/government/publications/multi-criteria-analysis-manual-for-making-government-policy",
            "2009-01-28",
            "UK government",
            "Structured comparison supports appraisal of options, with explicit criteria and judgments.",
        ),
        (
            "SRC-ODD",
            "ODD — Describing agent models",
            "https://www.jasss.org/23/2/7.html",
            "2020-03-31",
            "JASSS",
            "Document purpose, entities, processes and evaluation so a model can be understood and replicated.",
        ),
    ]
    if kind == "business":
        external.append(
            (
                "SRC-GEO",
                "IBGE — malhas territoriais",
                "https://servicodados.ibge.gov.br/api/docs/malhas?versao=3",
                "unknown",
                "IBGE",
                "A API fornece contornos territoriais. Isso não informa demanda ou adoção comercial.",
            )
        )
    for id, t, url, published, group, claim in external:
        research.add_source(
            project,
            {
                "id": id,
                "title": t,
                "url": url,
                "published_at": published,
                "accessed_at": "2026-10-29",
                "location": "Scope / abstract",
                "evidence": claim,
                "confidence": "high",
                "limitations": "Fonte metodológica, não evidência de demanda ou de números desta fixture.",
                "independence_group": group,
                "source_type": "primary",
            },
        )
    for _ in range(2):
        r = interview.next_round(project)
        if r.get("complete"):
            break
        replies = {
            "problem": problem,
            "success": "Comparar caixa e sobrecarga por seis períodos antes de planejar implantação.",
            "boundary": "Somente fixture local com custo externo zero e sem dados pessoais.",
            "stakeholders": "Patrocinador decide, equipe executa, clientes são afetados pelo tempo de espera.",
        }
        if kind == "critical":
            replies["success"] = (
                "Identificar condições de liberação e lacunas antes de qualquer energização; decisão física só após especialistas."
            )
            replies["boundary"] = (
                "Nenhuma energização, alteração de equipamento ou aceitação de risco físico nesta demonstração."
            )
            replies["stakeholders"] = (
                "Operador e pessoas próximas são afetados; especialista e autoridade de segurança ainda precisam ser designados."
            )
        interview.answer(
            project,
            {
                "round_id": r["id"],
                "speaker": "Patrocinador sintético",
                "answers": [
                    {
                        "question_id": q["id"],
                        "kind": "hipotese",
                        "text": replies.get(
                            q["topic"],
                            "A comparação deve preservar revisão humana e limites de capacidade durante todo o teste.",
                        ),
                    }
                    for q in r["questions"]
                ],
            },
        )
    common = {
        "price": 120,
        "variable_cost": 65,
        "fixed_cost": 800,
        "initial_cash": 5000,
        "market_size": 200,
        "conversion": 0.02,
        "churn": 0.08,
        "capacity": 60,
        "initial_customers": 5,
        "acquisition_spend": 100,
        "uncertainty": 0.006,
        "unit": unit,
        "currency": "BRL",
        "period": "mês sintético",
        "source_ids": ["SRC-MODEL"],
    }
    config = {
        "engine": "monte-carlo",
        "seed": 27,
        "agents": 60,
        "ticks": 6,
        "trials": 150,
        "timeout_seconds": 60,
        "cost_limit": 0,
        "success": {"metric": "cash", "threshold": 0},
        "scenarios": [
            {"id": "Piloto limitado", **common},
            {
                "id": "Expandir imediatamente",
                **common,
                "fixed_cost": 1700,
                "capacity": 120,
                "conversion": 0.03,
            },
            {
                "id": "Manter operação",
                **common,
                "conversion": 0.01,
                "acquisition_spend": 0,
            },
        ],
        "sensitivity": [
            {"parameter": "conversion", "values": [0.01, 0.02, 0.03]},
            {"parameter": "price", "values": [100, 120, 140]},
        ],
    }
    if kind == "business":
        for scenario in config["scenarios"]:
            rate = scenario["conversion"]
            scenario["regions"] = [
                {
                    "id": "35",
                    "market_size": 120,
                    "initial_customers": 3,
                    "conversion": rate * 0.8,
                    "source_ids": ["SRC-MODEL"],
                },
                {
                    "id": "53",
                    "market_size": 80,
                    "initial_customers": 2,
                    "conversion": rate * 1.2,
                    "source_ids": ["SRC-MODEL"],
                },
            ]
    authored = {
        "arquitetura-empresarial": "Separar decisão de capacidade, execução do atendimento e revisão de qualidade evita atribuir ao mesmo indicador funções diferentes.",
        "modelo-b2b": "Contratação por lote permite ao comprador comparar prazo, escopo e custo; não há contrato nem preço validado nesta fixture.",
        "modelo-b2c": "Pessoa usuária precisa conhecer prazo, custo total e caminho de suporte antes de assumir o compromisso.",
        "business-model-canvas": "Receita depende de atendimentos efetivamente concluídos; disponibilidade de capacidade não equivale a demanda.",
        "jornada-cliente": "A passagem entre solicitação e confirmação de atendimento é o recorte prioritário para medir abandono e espera.",
        "carta-empatia": "A preocupação com atraso é uma hipótese de pesquisa; nenhuma fala foi obtida de clientes reais.",
        "momentos-verdade": "Confirmar ou renegociar prazo antes da espera pode alterar confiança; esse mecanismo ainda precisa de observação.",
        "persona": "O perfil é uma pessoa que precisa de resolução previsível; trata-se de proto-persona, sem demografia inventada.",
        "pestel": "Mudanças de renda, custo de trabalho e disponibilidade de insumos podem afetar procura e margem; faltam dados territoriais.",
        "cinco-forcas": "Fazer internamente, adiar e escolher outro prestador são alternativas a investigar; não foi medida sua frequência.",
        "pbs": "O resultado inclui confirmação, atendimento concluído e comprovante de entrega; não se confunde com a lista de atividades.",
        "ciclo-vida-projeto": "O piloto precisa de preparação, execução controlada, revisão e decisão explícita antes de ampliar o escopo.",
        "roadmap": "As três primeiras semanas são reservadas a medir situação atual, testar fluxo e avaliar evidências; são datas didáticas.",
        "raci": "O patrocinador responde pela decisão de expansão, enquanto a equipe executa e o revisor verifica qualidade.",
        "gestao-riscos": "Expansão aumenta custo fixo antes de provar volume; o gatilho é caixa projetado abaixo do mínimo definido pelo responsável.",
        "swot-tows": "A limitação de capacidade pode orientar um piloto focalizado; demanda e vantagem competitiva permanecem desconhecidas.",
        "service-blueprint": "A confirmação visível ao cliente depende de capacidade real nos bastidores; divergência entre ambas pode produzir promessa inexequível.",
        "estrategia-integrada": "Comparar um piloto limitado com expansão e manutenção explicita a opção de aprender antes de elevar custo fixo.",
        "estrutura-institucional": "Uma única operação e uma oferta bastam para o recorte; não há holding, participação societária ou parceiros comprovados.",
        "wbs": "Preparar medição, operar o piloto e revisar evidência são pacotes distintos com saídas verificáveis.",
        "analise-viabilidade": "O caixa de cada cenário depende diretamente de conversão, custo fixo e preço; os valores de entrada são premissas sintéticas.",
        "proposta-valor": "A promessa a testar é previsibilidade da resolução; o modelo não demonstra que o usuário pagará mais por ela.",
    }
    artifacts = {}
    for doc in reports.catalog():
        finding = authored[doc["slug"]]
        sections = {
            heading: (
                "No exemplo "
                + title
                + ", "
                + finding
                + " Para esta seção, a informação disponível é uma hipótese didática; a próxima coleta deve verificar: "
                + instruction
            )
            for heading, instruction in doc["sections"]
        }
        artifacts[doc["slug"]] = {
            "applicable": True,
            "finding": finding,
            "mechanism": "No recorte "
            + doc["title"]
            + ", a dependência relevante é entre capacidade disponível, promessa de atendimento e decisão de expansão. A relação está proposta para teste; não foi demonstrada causalmente.",
            "implication": "Usar este documento para limitar o piloto e definir a informação que falta, preservando a opção de manter a operação atual.",
            "source_ids": ["SRC-MODEL", "SRC-ODD"],
            "sections": sections,
        }
    score = lambda v: {
        "value": v,
        "source_ids": ["SRC-MCDA"],
        "explanation": "Pontuação didática de preferência, não desempenho observado.",
    }
    patch = {
        "problem": problem,
        "stakeholders": [
            {
                "id": "STK-001",
                "name": "Patrocinador sintético",
                "role": "decisor",
                "objective": "Preservar caixa e aprender",
                "concern": "Assumir custo fixo antes de medir demanda",
            },
            {
                "id": "STK-002",
                "name": "Equipe sintética",
                "role": "operação",
                "objective": "Carga compatível com capacidade",
                "concern": "Sobrecarga e retrabalho",
            },
        ],
        "objectives": [
            {
                "id": "OBJ-001",
                "title": "Preservar capacidade e caixa",
                "measure": "Saldo, carga e conclusão por período",
                "rationale": "Um crescimento sem recursos pode piorar a entrega.",
            }
        ],
        "criteria": [
            {
                "id": "COST",
                "weight": 0.5,
                "min": 0,
                "max": 10,
                "direction": "max",
                "judgment_by": "Patrocinador sintético",
                "weight_reason": "Hipótese didática de preferência por preservação de recursos.",
            },
            {
                "id": "LEARN",
                "weight": 0.5,
                "min": 0,
                "max": 10,
                "direction": "max",
                "judgment_by": "Patrocinador sintético",
                "weight_reason": "Hipótese didática de preferência por aprendizado antes da escala.",
            },
        ],
        "alternatives": [
            {
                "id": "ALT-PILOT",
                "title": "Piloto limitado",
                "scores": {"COST": score(7), "LEARN": score(8)},
                "benefits": "Aprendizado com custo limitado",
                "losses": "Expansão mais lenta",
                "objective_ids": ["OBJ-001"],
            },
            {
                "id": "ALT-SCALE",
                "title": "Expandir imediatamente",
                "scores": {"COST": score(3), "LEARN": score(5)},
                "benefits": "Capacidade potencial maior",
                "losses": "Mais custo fixo antes de prova",
                "objective_ids": ["OBJ-001"],
            },
            {
                "id": "ALT-STATUS",
                "title": "Manter operação",
                "scores": {"COST": score(9), "LEARN": score(2)},
                "benefits": "Evita compromisso adicional",
                "losses": "Mantém problema sem novo teste",
                "objective_ids": ["OBJ-001"],
            },
        ],
        "artifacts": artifacts,
        "actions": [
            {
                "id": "TSK-C01",
                "title": "Medir espera e conclusão na situação atual",
                "owner": "Responsável pelo piloto",
                "start": "2026-11-02",
                "due": "2026-11-06",
                "criterion": "Registrar denominador, tempo e causas de abandono; meta a aprovar após baseline.",
                "budget": "A definir; nenhum gasto autorizado",
                "stop_rule": "Parar se houver coleta não autorizada de dado pessoal.",
            },
            {
                "id": "TSK-C02",
                "title": "Testar fluxo limitado e revisar capacidade",
                "owner": "Equipe e revisor",
                "start": "2026-11-09",
                "due": "2026-11-20",
                "criterion": "Comparar com a situação atual sem aumentar atraso; limiar sujeito a aprovação humana.",
                "budget": "Teto deve ser aprovado antes de executar",
                "stop_rule": "Interromper se a qualidade ou o caixa ultrapassar limite humano.",
            },
        ],
        "risks": [
            {
                "id": "RISK-1",
                "title": "Custo fixo cresce antes do volume",
                "likelihood": "medium",
                "impact": "high",
                "rubric": "Classificação qualitativa demonstrativa; alta perda significa ultrapassar o caixa autorizado.",
                "response": "Liberar recursos por etapas e medir procura",
                "owner": "Patrocinador",
                "trigger": "Caixa abaixo do mínimo ou espera acima da capacidade",
            }
        ],
        "analysis": {
            "diagnosis": "A decisão compara custo de aprender com risco de expandir cedo. Não existe coleta de mercado nesta fixture.",
            "recommendation": "Preparar um piloto limitado e adiar a expansão até medir procura, prazo e custo real; em sistema crítico, parar antes de teste físico e obter especialista.",
            "rationale": "O piloto mantém reversibilidade e permite confrontar as premissas que dominam o caixa.",
            "alternatives": "Manter operação evita custo novo, mas não testa a melhoria; expansão imediata eleva capacidade e exposição.",
            "reversal": "Se o piloto não produzir aprendizado suficiente ou exceder limites, revisar ou interromper.",
            "next_test": "Observação autorizada de solicitações reais, com baseline e critério aprovados antes da execução.",
            "limitations": "Dados, entrevistas, pesos, datas e resultados de negócio são sintéticos. As fontes citadas sustentam método e não a validade comercial do exemplo.",
            "confidence": "low",
            "confidence_reason": "Sem dados de campo e sem calibração comportamental.",
            "source_ids": ["SRC-MODEL", "SRC-MCDA"],
        },
    }
    if kind == "business":
        geometry = json.loads((ROOT / "examples/data/br-uf.geojson").read_text())
        features = [
            {
                **f,
                "id": f["properties"]["codarea"],
                "properties": {
                    **f["properties"],
                    "name": {"35": "São Paulo", "53": "Distrito Federal"}.get(
                        f["properties"]["codarea"], f["properties"]["codarea"]
                    ),
                },
            }
            for f in geometry["features"]
        ]
        patch["geography"] = {
            "features": features,
            "values": [],
            "metric": "Clientes ativos sob hipóteses regionais",
            "unit": "clientes representados",
            "source_ids": ["SRC-GEO"],
            "date_base": "2026-10-29",
            "limitations": "Apenas os limites são dados geográficos oficiais. Os mercados e as taxas usados nas duas regiões são premissas sintéticas da fixture; demais regiões não foram medidas.",
        }
    if kind == "critical":
        applicable = {
            "arquitetura-empresarial",
            "pbs",
            "wbs",
            "raci",
            "gestao-riscos",
            "ciclo-vida-projeto",
            "roadmap",
            "estrategia-integrada",
            "analise-viabilidade",
        }
        specific = {
            "arquitetura-empresarial": "Separar operador, controlador, sensor e atuador para identificar quem pode liberar a bomba e com qual realimentação.",
            "pbs": "A bancada proposta compreende medição, lógica de controle e corte de energia; nenhuma parte foi instalada ou ensaiada.",
            "wbs": "Mapear limites, desenhar a estrutura de controle e obter revisão qualificada são pacotes anteriores a qualquer energização.",
            "raci": "Não há especialista nem autoridade de segurança registrados; o patrocinador fictício não pode substituí-los.",
            "gestao-riscos": "Liberar a bomba com estado de válvula ou manutenção desconhecido pode criar condição insegura; limites físicos precisam ser definidos por especialista.",
            "ciclo-vida-projeto": "A passagem da análise para ensaio físico depende de revisão e autorização distintas; a fixture deve parar no gate STPA.",
            "roadmap": "Só há cronograma didático para completar informações e obter revisão; nenhum prazo de teste físico foi aprovado.",
            "estrategia-integrada": "Priorizar análise de controle e observação sem atuação, preservando a alternativa de simulação antes de um ensaio.",
            "analise-viabilidade": "Viabilidade de teste físico permanece indeterminada sem limites, procedimentos, instrumentação e autoridades qualificadas.",
        }
        for doc in reports.catalog():
            if doc["slug"] not in applicable:
                patch["artifacts"][doc["slug"]] = {
                    "applicable": False,
                    "reason": "Esta fixture verifica o bloqueio de um sistema crítico em bancada; oferta comercial, jornada de compra e posicionamento estão fora do recorte.",
                    "reviewed_by": "Ator sintético do exemplo, não autoridade de segurança",
                }
                continue
            a = patch["artifacts"][doc["slug"]]
            finding = specific[doc["slug"]]
            a.update(
                finding=finding,
                mechanism="Comando inseguro pode ocorrer por realimentação ausente, incorreta ou atrasada; a hipótese precisa de revisão de domínio antes de teste.",
                implication="Completar informação e obter autoridade qualificada; não energizar nem tratar aprovação fictícia como aceite real.",
                sections={
                    heading: finding
                    + " Informação disponível: somente desenho didático. Lacuna: parâmetros, contexto operacional e critério de verificação precisam ser definidos pelo especialista."
                    for heading, _ in doc["sections"]
                },
            )
        patch["analysis"].update(
            diagnosis="A estrutura de controle e os limites físicos ainda não foram validados por especialista.",
            recommendation="Não energizar a bancada. Completar cenários de comando inseguro e obter especialista e autoridade de segurança antes de ensaio.",
            rationale="Falta de informação sobre estados, realimentação e limites impede justificar teste físico seguro.",
            alternatives="Análise documental, simulação isolada e ensaio físico são alternativas com exposições distintas; nenhuma certificação foi obtida.",
            reversal="Reconsiderar somente após completar limites e procedimentos e obter as aprovações aplicáveis.",
            next_test="Revisão da estrutura de controle e das condições de liberação, sem atuação física.",
        )
        patch["stakeholders"] = [
            {
                "id": "STK-001",
                "name": "Operador da bancada",
                "role": "afetado e executor",
                "objective": "Evitar atuação insegura",
                "concern": "Realimentação incorreta ou manutenção em curso",
            },
            {
                "id": "STK-002",
                "name": "Especialista e autoridade de segurança não designados",
                "role": "revisão e autorização pendentes",
                "objective": "Avaliar condições do ensaio",
                "concern": "Ninguém registrado pode aceitar o risco",
            },
        ]
        patch["objectives"] = [
            {
                "id": "OBJ-001",
                "title": "Evitar atuação insegura",
                "measure": "Condições de liberação e estados verificáveis, a definir por especialista",
                "rationale": "Não presumir que componente funcionando garante controle seguro.",
            }
        ]
        patch["actions"] = [
            {
                "id": "TSK-C01",
                "title": "Completar estrutura de controle e condições de liberação",
                "owner": "Responsável pela análise",
                "start": "2026-11-02",
                "due": "2026-11-06",
                "criterion": "Documentar controlador, ações, feedback e limites desconhecidos para revisão.",
                "budget": "Somente análise; ensaio não autorizado",
                "stop_rule": "Não energizar ou modificar equipamento.",
            },
            {
                "id": "TSK-C02",
                "title": "Designar especialista e autoridade de segurança",
                "owner": "Patrocinador",
                "start": "2026-11-09",
                "due": "2026-11-13",
                "criterion": "Qualificação, escopo e decisão de revisão registrados.",
                "budget": "Contratação exige autorização separada",
                "stop_rule": "Manter gate bloqueado sem autoridades qualificadas.",
            },
        ]
        patch["risks"] = [
            {
                "id": "RISK-1",
                "title": "Liberação da bomba em condição inadequada",
                "likelihood": "unknown",
                "impact": "high",
                "rubric": "Impacto alto representa exposição física potencial; probabilidade ainda não medida e sem aceitação de risco.",
                "response": "Revisar controle, feedback e bloqueios antes de ensaio",
                "owner": "Especialista a designar",
                "trigger": "Estado ou limite desconhecido",
            }
        ]
    if kind == "critical":
        patch["criteria"] = [
            {
                "id": "CONTROL",
                "weight": 0.6,
                "min": 0,
                "max": 10,
                "direction": "max",
                "judgment_by": "Ator sintético",
                "weight_reason": "Preferência didática por evitar exposição física; não substitui restrição de segurança.",
                "veto_below": 5,
            },
            {
                "id": "LEARN",
                "weight": 0.4,
                "min": 0,
                "max": 10,
                "direction": "max",
                "judgment_by": "Ator sintético",
                "weight_reason": "Comparar informação obtida sem autorizar risco.",
            },
        ]
        patch["alternatives"] = [
            {
                "id": "ALT-DOC",
                "title": "Análise documental revisada",
                "scores": {"CONTROL": score(9), "LEARN": score(6)},
                "benefits": "Evita atuação física",
                "losses": "Não mede resposta real da bancada",
                "objective_ids": ["OBJ-001"],
            },
            {
                "id": "ALT-SIM",
                "title": "Simulação isolada",
                "scores": {"CONTROL": score(9), "LEARN": score(7)},
                "benefits": "Permite explorar hipóteses sem energizar",
                "losses": "Depende de validação do modelo",
                "objective_ids": ["OBJ-001"],
            },
            {
                "id": "ALT-PHYSICAL",
                "title": "Ensaio físico imediato sem revisão",
                "scores": {"CONTROL": score(1), "LEARN": score(8)},
                "benefits": "Observação direta potencial",
                "losses": "Exposição não aceita e sem autoridade",
                "objective_ids": ["OBJ-001"],
            },
        ]
    else:
        patch["artifacts"]["jornada-cliente"]["visual"] = {
            "type": "flow",
            "title": "Do pedido à resolução — fluxo proposto",
            "classification": "Hipótese da fixture; não é observação de clientes",
            "source_ids": ["SRC-ODD"],
            "nodes": [
                {"id": "J1", "label": "Receber solicitação"},
                {"id": "J2", "label": "Confirmar capacidade e prazo"},
                {"id": "J3", "label": "Executar e revisar"},
                {"id": "J4", "label": "Confirmar resolução"},
            ],
            "edges": [
                {"from": "J1", "to": "J2"},
                {"from": "J2", "to": "J3"},
                {"from": "J3", "to": "J4"},
            ],
            "caption": "A confirmação depende de capacidade disponível. O piloto deve medir espera, conclusão e falhas, sem tratar este fluxo proposto como desempenho observado.",
        }
        patch["artifacts"]["analise-viabilidade"]["visual"] = {
            "type": "comparison",
            "title": "Custo fixo assumido por cenário",
            "classification": "Premissas sintéticas da demonstração",
            "source_ids": ["SRC-MODEL"],
            "unit": "BRL por período",
            "period": "Seis meses sintéticos",
            "items": [
                {"label": a["id"], "value": a["fixed_cost"]}
                for a in config["scenarios"]
            ],
            "caption": "Expandir carrega custo fixo maior por construção. O gráfico compara entradas do modelo; não prova preço, demanda ou retorno do mercado.",
        }
        patch["artifacts"]["raci"]["visual"] = {
            "type": "matrix",
            "title": "Distribuição de responsabilidades proposta",
            "classification": "Proposta de organização da fixture",
            "source_ids": ["SRC-MODEL"],
            "columns": ["Trabalho", "Responsável", "Quem revisa"],
            "rows": [
                ["Medir situação atual", "Responsável pelo piloto", "Patrocinador"],
                ["Testar fluxo limitado", "Equipe de operação", "Revisor"],
                ["Decidir expansão", "Patrocinador", "Especialista se necessário"],
            ],
            "caption": "Esta síntese identifica papéis para discussão; não presume pessoas contratadas ou autoridades profissionais já designadas.",
        }
    if kind != "critical":
        patch["artifacts"]["estrategia-integrada"]["sections"].update(
            {
                "Comunicação e posicionamento": "Hipótese de posicionamento para testar: resolução com escopo e prazo combinados antes de iniciar. A fixture não demonstra preferência do público; validar em entrevistas autorizadas e comparar com a forma como as pessoas resolvem hoje.",
                "Canais e redes sociais": "Proposta exploratória: explicar o processo no website e em um canal já usado pelo público, cuja escolha depende da pesquisa. Medir solicitações elegíveis e conclusão; não inferir vendas a partir de curtidas. Nenhuma publicação ou campanha foi autorizada.",
                "Discurso comercial proposto": "Texto para teste, não promessa aprovada: ‘Conte o problema. Antes de começar, vamos confirmar o que está incluído, o prazo possível e o custo. Se a equipe não puder atender, você saberá antes de assumir o compromisso.’ Evitar alegar ser o mais rápido ou garantir resultado sem evidência.",
                "Implementação e teste da mensagem": "O responsável pelo piloto deve comparar entendimento de duas mensagens antes de qualquer anúncio pago. Definir público, autorização de contato, orçamento, duração, limiar e decisão de parada; registrar dúvidas e rejeições, não apenas respostas favoráveis. Datas e execução dependem de aprovação específica.",
            }
        )
    from sef_runtime.cli import validate_patch

    validate_patch(project, patch)
    with s.lock(project):
        s.save(project, {**s.model(project), **patch}, "fixture-analysis-authored")
    s.atomic(project / "experiment.json", config)
    if kind != "critical":
        a = dict(
            by="Fixture Human",
            authority_id="AUTH-U",
            evidence="fixture-only",
            attestation="Execução de teste local com dados sintéticos e custo zero, sem projeto real.",
            fixture=True,
        )
        s.authorize(project, config, "method", **a)
        grant = s.authorize(project, config, "execution", **a)
        simulation.run(project, config, grant["grant_id"])
        abm = {**config, "engine": "agents", "interaction_strength": 0.05, "trials": 1}
        abm = {
            **abm,
            "scenarios": [
                {k: v for k, v in scenario.items() if k != "regions"}
                for scenario in abm["scenarios"]
            ],
        }
        s.authorize(project, abm, "method", **a)
        grant = s.authorize(project, abm, "execution", **a)
        simulation.run(project, abm, grant["grant_id"])
        campaign_id = None
        if viability:
            from copy import deepcopy
            from sef_runtime import campaigns

            base = deepcopy(abm)
            base.update(trials=20, sensitivity=[], seed=1729)
            base["scenarios"] = [base["scenarios"][0]]
            scenario = base["scenarios"][0]
            scenario["finance"] = {
                "initial_investment": 1000,
                "discount_rate_per_period": 0.01,
                "revenue_tax_rate": 0.05,
                "collection_lag": 1,
                "operating_payment_lag": 0,
                "capex": [{"tick": 3, "amount": 300}],
                "source_ids": ["SRC-MODEL"],
                "limitations": "Valores artificiais; taxa sobre receita não representa regime tributário nem aconselhamento fiscal.",
            }
            scenario["price_response"] = {
                "reference_price": scenario["price"],
                "elasticity": -0.8,
                "source_ids": ["SRC-MODEL"],
                "classification": "hypothesis",
            }
            spec = {
                "base_config": base,
                "replicas_per_case": 20,
                "factors": [
                    {
                        "parameter": "scenario.price",
                        "values": [100, 140],
                        "source_ids": ["SRC-MODEL"],
                        "classification": "hypothesis",
                        "rationale": "Dois preços artificiais para testar o fluxo, não disposição a pagar observada.",
                        "role": "decision",
                    },
                    {
                        "parameter": "config.network_topology",
                        "values": ["ring", "random"],
                        "source_ids": ["SRC-MODEL"],
                        "classification": "hypothesis",
                        "rationale": "Redes alternativas, sem alegação de correspondência à população.",
                        "role": "structural",
                    },
                ],
            }
            campaign_id = campaigns.register(project, spec)["id"]
            s.atomic(project / "viability-plan.json", spec)
            for _ in range(4):
                experiment = campaigns.next_case(project, campaign_id)["case"]["config"]
                s.authorize(project, experiment, "method", **a)
                permission = s.authorize(project, experiment, "execution", **a)
                simulation.run(project, experiment, permission["grant_id"])
        with s.lock(project):
            m = s.model(project)
            runs = [
                {
                    **r,
                    "interpretation_status": "reviewed",
                    "reviewed_by": "Fixture analyst, not a client reviewer",
                    "source_ids": ["SRC-MODEL"],
                    "interpretation": "A diferença entre alternativas é consequência das premissas declaradas: expansão carrega custo fixo maior; isso não prova sua demanda. Conversão e preço precisam de teste real antes de qualquer recomendação de investimento.",
                }
                for r in m["runs"]
            ]
            s.save(project, {**m, "runs": runs}, "fixture-runs-interpreted")
    if kind != "critical" and viability:
        campaigns.analyze(project, campaign_id)
    phase_result = phases(project, kind)
    report = reports.render(project)
    return {
        "project": str(project),
        "phase_result": phase_result,
        "outputs": report,
        "real_approval": False,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True)
    parser.add_argument("--kind", choices=PROJECTS, default="business")
    parser.add_argument(
        "--viability",
        action="store_true",
        help="Executar quatro casos locais de teste financeiro, todos explicitamente sintéticos.",
    )
    args = parser.parse_args()
    print(
        json.dumps(
            run(args.output, args.kind, args.viability), ensure_ascii=False, indent=2
        )
    )
