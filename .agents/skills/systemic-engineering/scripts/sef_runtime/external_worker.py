"""Executed by the explicitly selected optional-engine Python, never by a shell."""

from __future__ import annotations
import asyncio, contextlib, importlib.metadata, json, os, sqlite3, subprocess, sys
from pathlib import Path


def version(name):
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return None


async def oasis_run(c, out):
    import oasis
    from oasis import ActionType, ManualAction, LLMAction
    from camel.models import ModelFactory
    from camel.types import ModelPlatformType

    profiles = json.loads(Path(c["profile_path"]).read_text())
    actions = [ActionType.CREATE_POST, ActionType.CREATE_COMMENT, ActionType.LIKE_POST]
    if c.get("smoke"):
        model = ModelFactory.create(
            model_platform=ModelPlatformType.OPENAI,
            model_type="gpt-4o-mini",
            api_key="engine-smoke-placeholder-not-a-real-key",
        )
    else:
        model = ModelFactory.create(
            model_platform=ModelPlatformType.VLLM,
            model_type=c["model"],
            url=c["base_url"],
        )
    if c.get("smoke"):
        graph = oasis.AgentGraph()
        for i, item in enumerate(profiles):
            name = item.get("name", f"agent-{i}")
            info = oasis.UserInfo(
                user_name=f"sef_agent_{i}",
                name=name,
                profile=None,
                recsys_type="reddit",
            )
            graph.add_agent(
                oasis.SocialAgent(i, info, model=model, available_actions=actions)
            )
    else:
        graph = await oasis.generate_reddit_agent_graph(
            profile_path=c["profile_path"], model=model, available_actions=actions
        )
    database = out / "oasis.db"
    os.environ["OASIS_DB_PATH"] = str(database)
    env = oasis.make(
        agent_graph=graph,
        platform=oasis.DefaultPlatformType.REDDIT,
        database_path=str(database),
    )
    await env.reset()
    try:
        await env.step(
            {
                env.agent_graph.get_agent(0): ManualAction(
                    ActionType.CREATE_POST, {"content": c["initial_post"]}
                )
            }
        )
        if not c.get("smoke"):
            for _ in range(c.get("ticks", 1)):
                await env.step(
                    {a: LLMAction() for _, a in env.agent_graph.get_agents()}
                )
    finally:
        await env.close()
    connection = sqlite3.connect(f"file:{database}?mode=ro", uri=True)
    tables = [
        x[0]
        for x in connection.execute("select name from sqlite_master where type='table'")
    ]
    counts = {}
    examples = {}
    for t in tables:
        if not all(ch.isalnum() or ch == "_" for ch in t):
            continue
        counts[t] = connection.execute(f'SELECT count(*) FROM "{t}"').fetchone()[0]
        if t.lower() in {"post", "posts", "comment", "comments"}:
            cursor = connection.execute(f'SELECT * FROM "{t}" LIMIT 10')
            columns = [x[0] for x in cursor.description]
            examples[t] = [dict(zip(columns, row)) for row in cursor.fetchall()]
    connection.close()
    return {
        "engine": "oasis",
        "engine_version": version("camel-oasis"),
        "classification": "engine-smoke"
        if c.get("smoke")
        else "synthetic-social-behavior",
        "database": "oasis.db",
        "counts": counts,
        "examples": examples,
        "limitation": "Posts e interações sintéticas não são opiniões observadas de clientes; interpretar objeções e trajetórias com denominadores e exemplos.",
    }


def recipe_contract(c):
    import yaml

    payload = yaml.safe_load(Path(c["recipe"]).read_text())
    if (
        not isinstance(payload, dict)
        or not payload.get("agents")
        or not payload.get("tasks")
    ):
        raise ValueError("Recipe requires agents and tasks")
    count = (
        len(payload["agents"])
        * len(payload["tasks"])
        * int(payload.get("n_attempts", 1))
    )
    if count != c["agents"]:
        raise ValueError(
            "Agent/task/attempt count differs from authorized configuration"
        )
    providers = {
        "openai": "OPENAI_API_KEY",
        "anthropic": "ANTHROPIC_API_KEY",
        "google": "GEMINI_API_KEY",
        "dashscope": "DASHSCOPE_API_KEY",
        "openrouter": "OPENROUTER_API_KEY",
    }
    references = set()
    for agent in payload["agents"]:
        model = str(agent.get("model_name", ""))
        provider = model.split("/", 1)[0]
        if provider not in providers or model != c["model"]:
            raise ValueError("Recipe must use the declared supported provider/model")
        references.add(providers[provider])

    def inspect(value):
        if isinstance(value, dict):
            for k, v in value.items():
                if (
                    any(
                        x in str(k).lower()
                        for x in ("api_key", "password", "secret", "access_token")
                    )
                    and v
                ):
                    raise ValueError("Raw credentials in recipe are forbidden")
                inspect(v)
        elif isinstance(value, list):
            for v in value:
                inspect(v)

    inspect(payload)
    if not references.issubset(set(c.get("credential_refs", []))):
        raise ValueError("Recipe provider requires explicit credential references")
    if (
        c.get("cost_limit", 0) <= 0
        or "estimated_cost" not in c
        or c["estimated_cost"] <= 0
    ):
        raise ValueError(
            "Provider job requires explicit positive cost limit and estimate"
        )
    return {
        "agents": count,
        "required_credential_refs": sorted(references),
        "recipe_validated": True,
    }


def matraix_run(c, out):
    import yaml

    runtime = Path(c["runtime_root"])
    exe = (
        runtime
        / ".venv"
        / ("Scripts/matraix.exe" if os.name == "nt" else "bin/matraix")
    )
    if not exe.is_file():
        raise ValueError("MatrAIx não instalado no runtime indicado.")
    if c.get("smoke"):
        task = runtime / "application/tasks/example-survey_product-feedback"
        command = [str(exe), "smoke", str(task)]
    else:
        recipe_contract(c)
        payload = yaml.safe_load(Path(c["recipe"]).read_text())
        agents = payload.get("agents", [])
        tasks = payload.get("tasks", [])
        count = len(agents) * len(tasks) * int(payload.get("n_attempts", 1))
        if count != c["agents"]:
            raise ValueError(
                "Quantidade de agentes/tarefas/tentativas diverge do preflight."
            )
        command = [
            str(exe),
            "run",
            "-c",
            c["recipe"],
            "--max-cost-usd",
            str(c["cost_limit"]),
        ]
    before = set((runtime / "jobs").glob("*"))
    result = subprocess.run(
        command,
        cwd=runtime,
        env=os.environ.copy(),
        capture_output=True,
        text=True,
        timeout=c.get("timeout_seconds", 120),
    )
    # Raw provider output can contain private content; never emit stdout/stderr automatically.
    if result.returncode:
        raise ValueError("MatrAIx retornou falha; revisar logs no runtime autorizado.")
    created = sorted(set((runtime / "jobs").glob("*")) - before)
    if not c.get("smoke") and not created:
        raise ValueError(
            "Nenhuma evidência de job nova; processo concluído não é resultado comportamental."
        )
    files = []
    for job in created:
        for p in job.rglob("*.json"):
            if p.stat().st_size <= 1_000_000:
                # Keep actual task results as immutable copies, not a fabricated score.
                import shutil

                dst = out / "matraix-job" / job.name / p.relative_to(job)
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(p, dst)
                files.append(str(dst.relative_to(out)))
    return {
        "engine": "matraix",
        "engine_version": version("matraix"),
        "classification": "engine-smoke"
        if c.get("smoke")
        else "synthetic-persona-evaluation",
        "job_directories": [p.name for p in created],
        "task_evidence": files,
        "interpretation_pending": not c.get("smoke"),
        "limitation": "Examinar respostas e trajetórias antes de recomendar; recibo e smoke não validam mercado. Evidências podem conter dados da tarefa e exigem revisão antes de publicação.",
    }


def main():
    request = json.load(sys.stdin)
    c = request["config"]
    out = Path(request["output"])
    out.mkdir(parents=True, exist_ok=True)
    os.chdir(out)
    if c.get("tokenizer_path"):
        os.environ["TIKTOKEN_CACHE_DIR"] = str(Path(c["tokenizer_path"]).parent)
    if c.get("smoke") and c["engine"] == "oasis":
        import socket

        def deny(*args, **kwargs):
            raise RuntimeError("Smoke blocks all provider/network connections.")

        socket.create_connection = deny
        socket.socket.connect = deny
    if request.get("operation") == "preflight":
        result = (
            recipe_contract(c)
            if c["engine"] == "matraix" and not c.get("smoke")
            else {
                "smoke": True,
                "engine_version": version(
                    "matraix" if c["engine"] == "matraix" else "camel-oasis"
                ),
            }
        )
        print(json.dumps({"ok": True, "result": result}))
        return
    # Redirect third-party diagnostics to a local file, stdout is protocol-only.
    with (
        open(os.devnull, "w") as log,
        contextlib.redirect_stdout(log),
        contextlib.redirect_stderr(log),
    ):
        if c["engine"] == "oasis":
            result = asyncio.run(oasis_run(c, out))
        else:
            result = matraix_run(c, out)
    print(json.dumps({"ok": True, "result": result}, ensure_ascii=False))


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        import traceback

        stages = [
            Path(x.filename).name + ":" + x.name + ":" + str(x.lineno)
            for x in traceback.extract_tb(error.__traceback__)
        ]
        print(
            json.dumps(
                {
                    "ok": False,
                    "error_type": type(error).__name__,
                    "error_stages": stages,
                    "message": "Motor opcional falhou; não houve fallback nem resultado inventado.",
                }
            )
        )
        sys.exit(1)
