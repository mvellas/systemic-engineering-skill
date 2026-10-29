"""Progressive, bounded rounds. The harness supplies contextual reasoning; humans decide."""

from __future__ import annotations
import csv, io, re
from . import store as s

BANK = {
    "intake": [
        (
            "problem",
            "Qual problema precisa ser resolvido, para quem e em qual situação?",
            [
                "Reduzir uma perda atual",
                "Atender uma necessidade ainda não atendida",
                "Comparar caminhos antes de investir",
            ],
            "Defina o problema antes da solução; sem evidência externa ainda não há recomendação de caminho.",
            "declaracao",
        ),
        (
            "success",
            "Qual resultado observável faria você considerar o projeto bem-sucedido e até quando?",
            [
                "Uma medida de resultado",
                "Uma condição mínima aceitável",
                "Ainda não sabemos medir",
            ],
            "Uma medida com prazo permite testar a proposta; não escolha metas arbitrárias.",
            "desejo",
        ),
        (
            "boundary",
            "Qual limite de dinheiro, tempo ou exposição não pode ser ultrapassado?",
            [
                "Limite obrigatório",
                "Preferência negociável",
                "Preciso comparar impactos antes de decidir",
            ],
            "Separe obrigação de preferência: uma preferência não deve eliminar alternativas sem debate.",
            "restricao",
        ),
        (
            "stakeholders",
            "Quem decide, quem usa, quem opera e quem pode ser prejudicado?",
            [
                "Papéis diferentes",
                "Uma pessoa acumula papéis",
                "Há pessoas afetadas ainda não ouvidas",
            ],
            "Não presumir consenso entre comprador, usuário e pessoa afetada.",
            "declaracao",
        ),
    ],
    "vft": [
        (
            "values",
            "Por que esse resultado é importante? O que seria perdido se ele não fosse alcançado?",
            [
                "Resultado final desejado",
                "Meio para outro resultado",
                "Obrigação que não pode ser compensada",
            ],
            "Identifique o valor final antes de atribuir peso a uma solução.",
            "preferencia",
        ),
        (
            "measure",
            "Como compararíamos duas opções quanto a esse objetivo, usando a mesma escala?",
            [
                "Medida diretamente observável",
                "Escala qualitativa com critérios",
                "Precisamos pesquisar um indicador",
            ],
            "Explicite unidade e limites de interpretação.",
            "hipotese",
        ),
        (
            "tradeoff",
            "Se uma opção custar menos, mas entregar menos resultado, que troca você aceitaria?",
            [
                "Posso negociar esta troca",
                "Existe um mínimo obrigatório",
                "Não posso decidir sem ver cenários",
            ],
            "Não sugerir pesos sem conhecer preferência e intervalo de consequências.",
            "preferencia",
        ),
    ],
    "ssm": [
        (
            "transformation",
            "O que entra na situação atual e o que deve mudar na vida das pessoas?",
            [
                "Mudar um processo",
                "Mudar acesso ou experiência",
                "Rever o problema antes da solução",
            ],
            "Descreva antes/depois no mesmo nível; ferramenta não é transformação.",
            "hipotese",
        ),
        (
            "worldviews",
            "Quem discorda dessa mudança e por quais motivos?",
            [
                "Discordância sobre o objetivo",
                "Discordância sobre quem ganha ou perde",
                "Ainda não ouvimos essa pessoa",
            ],
            "Preserve discordância; não substituir ausência de entrevista por consenso.",
            "declaracao",
        ),
        (
            "catwoe",
            "Quem recebe o efeito, faz o trabalho, pode parar a mudança e impõe limites externos?",
            [
                "Papéis identificados",
                "Há conflito de autoridade",
                "Há pessoas ainda não representadas",
            ],
            "Separar cliente afetado, ator, dono e ambiente evita atribuir poder que a pessoa não possui.",
            "declaracao",
        ),
        (
            "feasible",
            "Qual mudança é desejável, mas as pessoas ou a operação podem não aceitar hoje?",
            [
                "Precisa de negociação",
                "Precisa de teste pequeno",
                "Não é viável neste momento",
            ],
            "Distinguir desejabilidade e viabilidade cultural antes de recomendar execução.",
            "hipotese",
        ),
    ],
}
KINDS = {
    "fato",
    "declaracao",
    "desejo",
    "preferencia",
    "restricao",
    "hipotese",
    "decisao",
}


def phase(project, requested=None):
    current = s.read(s.root(project).parent / "state.json")["phase"]
    chosen = requested or current
    if chosen not in BANK:
        raise s.Invalid("Entrevista está disponível em intake, vft e ssm.")
    if chosen != current:
        raise s.Invalid(
            "A entrevista não pode pular a fase atual. Use os gates existentes."
        )
    return chosen


def next_round(project, limit=3):
    if not 1 <= limit <= 4:
        raise s.Invalid("Rodada limitada a 1–4 perguntas.")
    with s.lock(project):
        s.integrity(project)
        m = s.model(project)
        p = phase(project)
        pending = [r for r in m["rounds"] if r["phase"] == p and not r.get("answered")]
        if pending:
            return pending[-1]
        answered = {a["topic"] for a in m["answers"] if a["phase"] == p}
        prior = m["answers"][-1] if m["answers"] else None
        qs = []
        for a in m["answers"]:
            if (
                a["phase"] != p
                or not a.get("needs_followup")
                or a.get("followup_resolved")
            ):
                continue
            depth = a.get("depth", 0)
            if depth >= 5:
                continue
            qs.append(
                {
                    "id": f"Q-{p}-{a['topic']}-why{depth + 1}-{len(m['rounds']) + 1}",
                    "topic": a["topic"],
                    "prompt": f"Você disse “{a['text'][:180]}”. Pode dar um exemplo concreto e explicar por que isso importa, quem é afetado e como verificar?",
                    "technique": "5-whys / esclarecimento",
                    "alternatives": [
                        "Tenho um exemplo ou uma fonte",
                        "É uma preferência minha",
                        "Ainda é uma hipótese e precisa de pesquisa",
                    ],
                    "recommendation": "Não tratar uma resposta vaga como fato; registrar o exemplo ou a lacuna.",
                    "recommendation_sources": a.get("source_ids", [])
                    or [
                        "https://www.nasa.gov/wp-content/uploads/2018/09/nasa_systems_engineering_handbook_0.pdf"
                    ],
                    "kind_hint": a["kind"],
                    "parent_answer": a["id"],
                    "depth": depth + 1,
                }
            )
        for topic, prompt, options, why, kind in BANK[p]:
            if topic in answered:
                continue
            qs.append(
                {
                    "id": f"Q-{p}-{topic}",
                    "topic": topic,
                    "prompt": prompt,
                    "technique": "VFT/WITI"
                    if p == "vft"
                    else "CATWOE / pressupostos"
                    if p == "ssm"
                    else "contexto e restrições",
                    "alternatives": options,
                    "recommendation": why,
                    "recommendation_sources": [
                        "https://doi.org/10.1590/0101-7438.2023.043.00276110"
                        if p == "vft"
                        else "https://doi.org/10.3233/HSM-1989-8405"
                        if p == "ssm"
                        else "https://www.nasa.gov/wp-content/uploads/2018/09/nasa_systems_engineering_handbook_0.pdf"
                    ],
                    "kind_hint": kind,
                    "depth": 0,
                }
            )
        if not qs:
            return {
                "complete": True,
                "phase": p,
                "next": "Revise conflitos e fontes; a aprovação da fase continua sendo humana.",
            }
        r = {
            "id": f"ROUND-{len(m['rounds']) + 1:03}",
            "phase": p,
            "context": m.get("problem"),
            "questions": qs[:limit],
            "answered": False,
            "at": s.now(),
        }
        s.save(
            project,
            {**m, "rounds": [*m["rounds"], r]},
            "interview-round",
            {"round_id": r["id"]},
        )
        return r


def answer(project, payload):
    with s.lock(project):
        s.integrity(project)
        m = s.model(project)
        r = next((r for r in m["rounds"] if r["id"] == payload.get("round_id")), None)
        if not r or r.get("answered"):
            raise s.Invalid("Rodada inexistente ou já respondida.")
        if r["phase"] != phase(project):
            raise s.Invalid("Rodada pertence a outra fase.")
        replies = payload.get("answers", [])
        questions = {q["id"]: q for q in r["questions"]}
        if len(replies) != len(questions) or set(
            a["question_id"] for a in replies
        ) != set(questions):
            raise s.Invalid(
                "Responda exatamente uma vez a cada pergunta da rodada; registre desconhecido em vez de omitir."
            )
        proposals = list(m.get("proposals", []))
        answers = list(m["answers"])
        conflicts = list(m["conflicts"])
        relations = list(m["relations"])
        decisions = list(m["decisions"])
        for reply in replies:
            q = questions[reply["question_id"]]
            kind = reply.get("kind")
            text = reply.get("text", "").strip()
            if kind not in KINDS or not text:
                raise s.Invalid(
                    "Resposta exige texto e tipo: fato, declaração, desejo, preferência, restrição, hipótese ou decisão."
                )
            ids = reply.get("source_ids", [])
            if kind == "fato" and not ids:
                raise s.Invalid(
                    "Fato exige fonte; relato do participante é declaração, não fato externo verificado."
                )
            if any(i not in {src["id"] for src in m["sources"]} for i in ids):
                raise s.Invalid("Fonte de resposta não registrada.")
            for a in answers:
                if (
                    a["phase"] == r["phase"]
                    and a["topic"] == q["topic"]
                    and a["kind"] in {"fato", "restricao", "decisao"}
                    and a["text"] != text
                ):
                    conflicts.append(
                        {
                            "id": f"CON-{len(conflicts) + 1:03}",
                            "before": a["id"],
                            "after": f"ANS-{len(answers) + 1:03}",
                            "status": "pending",
                            "reason": "Mudança de resposta material: confirmar se substitui, complementa ou contradiz.",
                        }
                    )
            a = {
                "id": f"ANS-{len(answers) + 1:03}",
                "phase": r["phase"],
                "topic": q["topic"],
                "text": text,
                "kind": kind,
                "speaker": payload.get("speaker", "não informado"),
                "source_ids": ids,
                "at": s.now(),
                "depth": q.get("depth", 0),
                "needs_followup": len(text.split()) < 7
                or bool(
                    re.search(
                        r"\b(melhor|rápido|barato|depende|não sei|inovador)\b",
                        text,
                        re.I,
                    )
                )
                and not re.search(r"\d", text),
            }
            if q.get("parent_answer"):
                answers = [
                    {**old, "followup_resolved": True}
                    if old["id"] == q["parent_answer"]
                    else old
                    for old in answers
                ]
            target = (
                "OBJ-"
                if r["phase"] == "vft"
                else "SSM-"
                if r["phase"] == "ssm"
                else "STK-"
            ) + f"{len(answers) + 1:03}"
            proposals.append(
                {
                    "id": target,
                    "kind": "candidate-objective"
                    if r["phase"] == "vft"
                    else "candidate-system-view"
                    if r["phase"] == "ssm"
                    else "candidate-context",
                    "statement": text,
                    "answer_id": a["id"],
                    "status": "proposed-not-approved",
                }
            )
            relations.extend(
                [
                    {
                        "from": a["id"],
                        "to": target,
                        "relationship": "informs",
                        "status": "proposed",
                    },
                    *[
                        {
                            "from": i,
                            "to": a["id"],
                            "relationship": "supports",
                            "status": "registered",
                        }
                        for i in ids
                    ],
                ]
            )
            if kind == "decisao":
                decisions.append(
                    {
                        "id": f"DEC-C{len(decisions) + 1:03}",
                        "text": text,
                        "speaker": a["speaker"],
                        "answer_id": a["id"],
                        "status": "human-statement-not-phase-approval",
                        "at": a["at"],
                    }
                )
            answers.append(a)
        rounds = [
            {**old, "answered": True} if old["id"] == r["id"] else old
            for old in m["rounds"]
        ]
        new = {
            **m,
            "proposals": proposals,
            "rounds": rounds,
            "answers": answers,
            "conflicts": conflicts,
            "relations": relations,
            "decisions": decisions,
        }
        if not m["problem"]:
            first = next((a for a in answers if a["topic"] == "problem"), None)
            if first:
                new = {**new, "problem": first["text"]}
        s.save(project, new, "interview-answers", {"round_id": r["id"]})
        for name, rows in [
            ("interview-trace.csv", relations),
            ("interview-decisions.csv", decisions),
        ]:
            fields = list(dict.fromkeys(k for row in rows for k in row))
            if fields:
                out = io.StringIO()
                w = csv.DictWriter(out, fieldnames=fields)
                w.writeheader()
                w.writerows(rows)
                s.atomic(s.root(project) / name, out.getvalue())
        return {
            "recorded": len(replies),
            "conflicts": len([x for x in conflicts if x["status"] == "pending"]),
            "phase_approval_created": False,
        }
