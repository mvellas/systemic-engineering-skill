"""Additional subcommands attached to the original sef.py parser."""

from __future__ import annotations
from pathlib import Path
from datetime import date
import argparse, json, re, shutil, zipfile
from . import (
    store as s,
    interview,
    research,
    simulation,
    decision,
    reports,
    experiments,
    campaigns,
)


def out(value):
    print(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False))
    return 0


def input_config(args):
    c = s.read(args.config)

    # Never accept embedded secrets. Providers receive only explicit environment names.
    def inspect(v):
        if isinstance(v, dict):
            for k, x in v.items():
                if (
                    any(
                        word in k.lower()
                        for word in ("api_key", "password", "secret", "access_token")
                    )
                    and x
                ):
                    raise s.Invalid(
                        "Segredo embutido não é permitido; use credential_refs."
                    )
                inspect(x)
        elif isinstance(v, list):
            for x in v:
                inspect(x)
        elif isinstance(v, str) and re.search(
            r"(?:sk-[A-Za-z0-9_-]{18,}|gh[pousr]_[A-Za-z0-9]{20,}|-----BEGIN .*PRIVATE KEY)",
            v,
        ):
            raise s.Invalid("Possível credencial no payload; não será registrada.")

    inspect(c)
    return c


def validate_patch(project, patch):
    allowed = {
        "problem",
        "language",
        "stakeholders",
        "objectives",
        "alternatives",
        "criteria",
        "actions",
        "risks",
        "relations",
        "artifacts",
        "analysis",
        "geography",
    }
    if set(patch) - allowed:
        raise s.Invalid("Campos não importáveis: " + ", ".join(set(patch) - allowed))
    if patch.get("language", "pt-BR") != "pt-BR":
        raise s.Invalid(
            "Renderer humano desta versão suporta pt-BR; preserve documentos legados em outros idiomas sem prometer tradução automática."
        )
    known = {x["id"] for x in s.model(project)["sources"]}
    for item in patch.get("actions", []):
        if not all(
            item.get(k)
            for k in ("id", "title", "owner", "start", "due", "criterion", "stop_rule")
        ):
            raise s.Invalid(
                "Ação exige ID, título, dono, datas, critério e regra de parada."
            )
        if date.fromisoformat(item["due"]) < date.fromisoformat(item["start"]):
            raise s.Invalid("Prazo anterior ao início.")
    for item in patch.get("risks", []):
        if item.get("likelihood") not in {
            "low",
            "medium",
            "high",
            "unknown",
        } or item.get("impact") not in {"low", "medium", "high", "unknown"}:
            raise s.Invalid("Risco exige escala qualitativa ou unknown.")
        if not all(item.get(k) for k in ("owner", "response", "trigger", "rubric")):
            raise s.Invalid("Risco exige dono, resposta, gatilho e rubrica.")
    for slug, a in patch.get("artifacts", {}).items():
        if slug not in {d["slug"] for d in reports.catalog()}:
            raise s.Invalid("Documento não corresponde ao catálogo.")
        if a.get("applicable") is False and (
            not a.get("reason") or not a.get("reviewed_by")
        ):
            raise s.Invalid("Exclusão exige justificativa e revisor.")
        if a.get("visual"):
            from .visuals import validate

            validate(a["visual"], known)
        if set(a.get("source_ids", [])) - known:
            raise s.Invalid("Documento referencia fonte não registrada.")
    for section in [patch.get("analysis", {})]:
        if set(section.get("source_ids", [])) - known:
            raise s.Invalid("Análise referencia fonte não registrada.")
    geo = patch.get("geography")
    if geo:
        if not all(
            geo.get(k)
            for k in ("features", "metric", "unit", "source_ids", "date_base")
        ):
            raise s.Invalid(
                "Mapa exige geometria, dados regionais, unidade, data-base e origem."
            )
        if set(geo["source_ids"]) - known:
            raise s.Invalid("Origem geográfica não registrada.")
        regions = {f["id"] for f in geo["features"]}
        for f in geo["features"]:
            if f["geometry"]["type"] not in {"Polygon", "MultiPolygon"}:
                raise s.Invalid("Geometria não suportada.")
        for row in geo.get("values", []):
            if (
                row["region"] not in regions
                or row.get("classification") not in {"observed", "simulated"}
                or not row.get("source_ids")
            ):
                raise s.Invalid("Valor regional exige região, classificação e fonte.")
            s.finite(row["value"], "valor regional")
    return patch


def consult(args):
    action = args.action
    p = args.project
    if action == "enable":
        return out(s.enable(p))
    if action == "review":
        return out(
            reports.review(
                p,
                args.by,
                args.authority_id,
                args.evidence,
                args.attestation,
                args.decision,
            )
        )
    if action == "recover":
        return out(s.recover(p))
    if action == "import":
        patch = validate_patch(p, input_config(args))
        with s.lock(p):
            s.integrity(p)
            m = s.model(p)
            new = s.save(
                p, {**m, **patch}, "analysis-imported", {"fields": sorted(patch)}
            )
        return out({"revision": new["revision"], "impact": decision.impact(p)})
    if action == "status":
        s.integrity(p)
        return out(
            {
                "revision": s.model(p)["revision"],
                "quality": reports.quality(p),
                "impact": decision.impact(p),
            }
        )
    if action == "compare":
        return out(decision.compare(p))
    if action == "report":
        return out(reports.render(p))
    if action == "quality":
        q = reports.quality(p)
        out(q)
        return 0 if not q["issues"] else 1
    if action == "impact":
        return out(decision.impact(p))
    if action == "next":
        phase = s.read(s.root(p).parent / "state.json")["phase"]
        if phase in interview.BANK:
            return out(
                {
                    "phase": phase,
                    "interview": interview.next_round(p, args.limit),
                    "research": research.plan(p),
                    "approval": "Aguardar resposta humana; não avançar automaticamente.",
                }
            )
        return out(
            {
                "phase": phase,
                "quality": reports.quality(p),
                "next": "Reconciliar evidências, executar comparações ou preparar pacote de gate da fase atual. Use pending/status da CLI original.",
            }
        )
    if action == "resolve":
        auth = s.authority(p, args.authority_id, args.by, "consulting")
        with s.lock(p):
            s.integrity(p)
            m = s.model(p)
            item = next((x for x in m["conflicts"] if x["id"] == args.conflict), None)
            if not item:
                raise s.Invalid("Conflito não encontrado.")
            resolved = {
                **item,
                "status": args.resolution,
                "by": args.by,
                "authority_id": args.authority_id,
                "evidence": args.evidence,
                "reason": args.reason,
            }
            s.save(
                p,
                {
                    **m,
                    "conflicts": [
                        resolved if x["id"] == item["id"] else x for x in m["conflicts"]
                    ],
                },
                "conflict-reconciled",
                {"conflict_id": item["id"]},
            )
        return out(resolved)
    if action == "interpret":
        payload = input_config(args)
        if not all(
            payload.get(k)
            for k in (
                "finding",
                "mechanism",
                "consequence",
                "limitations",
                "source_ids",
                "reviewed_by",
            )
        ):
            raise s.Invalid(
                "Interpretação exige achado, mecanismo, consequência, fontes, limites e revisor."
            )
        with s.lock(p):
            s.integrity(p)
            m = s.model(p)
            if set(payload["source_ids"]) - {x["id"] for x in m["sources"]}:
                raise s.Invalid("Fontes da interpretação não registradas.")
            if args.run_id not in {x["id"] for x in m["runs"]}:
                raise s.Invalid("Run não encontrada.")
            text = " ".join(
                str(payload[k])
                for k in ("finding", "mechanism", "consequence", "limitations")
            )
            runs = [
                {
                    **x,
                    "interpretation_status": "reviewed",
                    "interpretation": text,
                    "source_ids": payload["source_ids"],
                    "reviewed_by": payload["reviewed_by"],
                }
                if x["id"] == args.run_id
                else x
                for x in m["runs"]
            ]
            s.save(
                p,
                {**m, "runs": runs},
                "simulation-interpreted",
                {"run_id": args.run_id},
            )
        return out(reports.render(p))
    if action == "bundle":
        return out(bundle(p, args.config, args.output))
    raise s.Invalid("Comando desconhecido.")


def bundle(project, config_path, destination):
    c = input_config(argparse.Namespace(config=str(config_path)))
    simulation.preflight(project, c)
    base = Path(project).resolve()
    target = Path(destination).resolve()
    if target.exists():
        raise s.Invalid("Pacote já existe; não sobrescrever.")
    target.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(target, "x", zipfile.ZIP_DEFLATED) as z:
        for p in reports.SKILL.rglob("*"):
            if p.is_file() and not any(
                x in p.parts for x in ("__pycache__", ".pytest_cache")
            ):
                z.write(p, "skill/" + str(p.relative_to(reports.SKILL)))
        control = s.root(project).parent
        for p in control.rglob("*"):
            if p.is_file() and not set(p.relative_to(control).parts) & {
                "exports",
                "captures",
                "runs",
                ".writer-lock",
            }:
                z.write(
                    p, "project/.systemic-engineering/" + str(p.relative_to(control))
                )
        for key in (
            "dataset",
            "profile_path",
            "recipe",
            "bdh_source",
            "tokenizer_path",
        ):
            if c.get(key):
                p = s.inside(base, c[key])
                z.write(p, "project/" + str(p.relative_to(base)))
        z.writestr("project/experiment.json", s.canonical(c))
        z.writestr(
            "EXECUTOR.txt",
            "Pacote preparado, NÃO executado. No diretório extraído: python3 skill/scripts/sef.py sim preflight project --config project/experiment.json\nRevisar método e obter autorização específica no ambiente executor; nenhuma credencial é incluída. Ver skill/references/consulting-workflow.md.\n",
        )
    return {
        "bundle": str(target),
        "sha256": s.file_hash(target),
        "executed": False,
        "notice": "Configuração e dados declarados incluídos; captures e segredos excluídos. Autorizações são reavaliadas no executor.",
    }


def interview_command(args):
    return out(
        interview.next_round(args.project, args.limit)
        if args.action == "next"
        else interview.answer(args.project, input_config(args))
    )


def research_command(args):
    if args.action == "plan":
        return out(research.plan(args.project))
    if args.action == "source":
        return out(research.add_source(args.project, input_config(args)))
    if args.action == "claim":
        return out(research.add_claim(args.project, input_config(args)))
    if args.action == "audit":
        return out(research.audit(args.project, args.as_of))
    if args.action == "capture":
        return out(research.capture(args.project, input_config(args), args.grant))
    if args.action == "screenshot":
        return out(research.screenshot(args.project, args.capture))
    if args.action == "browser-capture":
        return out(
            research.browser_capture(args.project, input_config(args), args.grant)
        )
    raise s.Invalid("Comando desconhecido.")


def sim_command(args):
    if args.action == "capabilities":
        return out(simulation.capabilities())
    if args.action == "select":
        return out(simulation.select(args.problem))
    if args.action == "campaign-status":
        return out(campaigns.status(args.project, args.campaign_id))
    if args.action == "campaign-next":
        return out(campaigns.next_case(args.project, args.campaign_id))
    if args.action == "campaign-analyze":
        return out(campaigns.analyze(args.project, args.campaign_id))
    c = input_config(args)
    if args.action == "campaign-register":
        return out(campaigns.register(args.project, c))
    if args.action == "plan":
        return out(experiments.plan(c))
    if args.action == "preflight":
        return out(simulation.preflight(args.project, c))
    if args.action == "authorize":
        if c.get("engine") not in {"capture", "browser-capture"}:
            simulation.preflight(args.project, c)
        return out(
            s.authorize(
                args.project,
                c,
                args.kind,
                args.by,
                args.authority_id,
                args.evidence,
                args.attestation,
                args.fixture,
            )
        )
    if args.action == "run":
        return out(simulation.run(args.project, c, args.grant))
    raise s.Invalid("Comando desconhecido.")


def guarded(function):
    def execute(args):
        try:
            return function(args)
        except (s.Invalid, KeyError, ValueError, TypeError, OSError) as error:
            # Do not print raw payloads, environment values, provider exceptions or secrets.
            message = (
                str(error)
                if isinstance(error, s.Invalid)
                else "Entrada inválida ou recurso indisponível; verifique o schema e os caminhos."
            )
            out(
                {
                    "status": "blocked",
                    "reason": message,
                    "error_type": type(error).__name__,
                }
            )
            return 1

    return execute


def attach(commands):
    def group(name, func):
        parser = commands.add_parser(name)
        parser.set_defaults(func=guarded(func))
        return parser.add_subparsers(dest="action", required=True)

    def basic(sub, name, project=True, config=False):
        p = sub.add_parser(name)
        if project:
            p.add_argument("project")
        if config:
            p.add_argument("--config", required=True)
        return p

    sub = group("consult", consult)
    for name in (
        "enable",
        "status",
        "recover",
        "quality",
        "compare",
        "report",
        "impact",
    ):
        basic(sub, name)
    basic(sub, "import", config=True)
    p = basic(sub, "review")
    for k in ("by", "authority-id", "evidence", "attestation"):
        p.add_argument("--" + k, required=True)
    p.add_argument("--decision", choices=("approved", "rejected"), required=True)
    p = basic(sub, "next")
    p.add_argument("--limit", type=int, default=3)
    p = basic(sub, "bundle", config=True)
    p.add_argument("--output", required=True)
    p = basic(sub, "interpret", config=True)
    p.add_argument("--run-id", required=True)
    p = basic(sub, "resolve")
    for k in ("conflict", "by", "authority-id", "evidence", "reason"):
        p.add_argument("--" + k, required=True)
    p.add_argument(
        "--resolution",
        choices=("superseded", "retained-with-dissent", "resolved"),
        required=True,
    )
    sub = group("interview", interview_command)
    p = basic(sub, "next")
    p.add_argument("--limit", type=int, default=3)
    basic(sub, "answer", config=True)
    sub = group("research", research_command)
    basic(sub, "plan")
    basic(sub, "source", config=True)
    basic(sub, "claim", config=True)
    p = basic(sub, "audit")
    p.add_argument("--as-of")
    p = basic(sub, "capture", config=True)
    p.add_argument("--grant", required=True)
    p = basic(sub, "browser-capture", config=True)
    p.add_argument("--grant", required=True)
    p = basic(sub, "screenshot")
    p.add_argument("--capture", required=True)
    sub = group("sim", sim_command)
    basic(sub, "capabilities", project=False)
    p = basic(sub, "select", project=False)
    p.add_argument("--problem", required=True)
    basic(sub, "plan", project=False, config=True)
    basic(sub, "campaign-register", config=True)
    for action in ("campaign-status", "campaign-next", "campaign-analyze"):
        p = basic(sub, action)
        p.add_argument("--campaign-id", required=True)
    basic(sub, "preflight", config=True)
    p = basic(sub, "run", config=True)
    p.add_argument("--grant", required=True)
    p = basic(sub, "authorize", config=True)
    p.add_argument("--kind", choices=("method", "execution"), required=True)
    for k in ("by", "authority-id", "evidence", "attestation"):
        p.add_argument("--" + k, required=True)
    p.add_argument("--fixture", action="store_true")
