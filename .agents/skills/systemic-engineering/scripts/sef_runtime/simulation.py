"""Capability discovery, preflight, one-use authorization and immutable experiment records."""

from __future__ import annotations
from pathlib import Path
from urllib.parse import urlsplit
import importlib.util, importlib.metadata, os, platform, shutil, signal, subprocess, sys, time, uuid, csv, io
from . import store as s, engines

WHY = {
    "monte-carlo": (
        "Variar premissas e comparar distribuições condicionais.",
        "https://standards.nasa.gov/standard/NASA/NASA-STD-7009",
    ),
    "agents": (
        "Representar heterogeneidade e influência entre unidades ponderadas.",
        "https://www.jasss.org/23/2/7.html",
    ),
    "dynamics": (
        "Explorar estoques, fluxos, capacidade e realimentação ao longo do tempo.",
        "https://ocw.mit.edu/courses/15-871-introduction-to-system-dynamics-fall-2013/",
    ),
    "failure": (
        "Explorar propagação e recuperação em uma rede de dependências.",
        "https://csrc.nist.gov/pubs/sp/800/30/r1/final",
    ),
    "mcmc": (
        "Explorar taxa binomial com prior explícito e diagnóstico. Neste caso simples há solução analítica exata, preferível para uso decisório; MCMC serve como experimento ou base de uma extensão justificada.",
        "https://mc-stan.org/docs/reference-manual/analysis.html",
    ),
    "ml": (
        "Testar previsão supervisionada com corte temporal e baseline antes de usar um substituto na busca.",
        "https://scikit-learn.org/stable/common_pitfalls.html",
    ),
    "bdh": (
        "Experimento com implementação oficial BDH; não presume utilidade comercial.",
        "https://github.com/pathwaycom/bdh",
    ),
    "oasis": (
        "Explorar interações em rede social sintética com o engine OASIS real.",
        "https://github.com/camel-ai/oasis",
    ),
    "matraix": (
        "Avaliar tarefas com personas sintéticas usando a CLI oficial MatrAIx.",
        "https://github.com/MatrAIx-ai/MatrAIx-Persona-8B",
    ),
}


def capabilities():
    packages = {}
    for key in ("numpy", "torch", "playwright", "camel-oasis", "matraix"):
        try:
            packages[key] = importlib.metadata.version(key)
        except importlib.metadata.PackageNotFoundError:
            packages[key] = None
    runtimes = {}
    for name, relative in [
        ("oasis", "venvs/oasis/bin/python"),
        ("matraix", "matraix/.venv/bin/python"),
    ]:
        candidates = [
            Path.home() / ".local/share/systemic-engineering" / relative,
            Path.home() / ".local/share/disruptive-venture-lab" / relative,
        ]
        runtimes[name] = next((str(p) for p in candidates if p.is_file()), None)
    try:
        memory = os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES")
    except (ValueError, OSError, AttributeError):
        memory = None
    return {
        "physical_memory_bytes": memory,
        "discovered_optional_runtimes": runtimes,
        "machine": platform.machine(),
        "python": platform.python_version(),
        "platform": platform.platform(),
        "cpu_count": os.cpu_count(),
        "packages": packages,
        "tools": {k: bool(shutil.which(k)) for k in ("docker", "uv", "nvidia-smi")},
        "model_availability": "Nenhum checkpoint ou servidor foi presumido disponível. BDH exige fonte identificada e treinamento; LLM exige runtime explícito.",
        "local_engines": ["monte-carlo", "agents", "dynamics", "failure", "mcmc"],
        "optional_engines": ["ml", "bdh", "oasis", "matraix"],
        "gpu": "Não verificada por importação pesada; usar executor e benchmark específicos.",
        "network_calls": 0,
    }


def select(problem):
    mapping = {
        "uncertainty": "monte-carlo",
        "adoption": "agents",
        "stocks": "dynamics",
        "failures": "failure",
        "rate-estimation": "mcmc",
        "prediction": "ml",
        "sequence-research": "bdh",
        "social-network": "oasis",
        "persona-task": "matraix",
    }
    if problem not in mapping:
        raise s.Invalid("Tipo de problema desconhecido: " + ", ".join(mapping))
    engine = mapping[problem]
    why, source = WHY[engine]
    return {
        "engine": engine,
        "reason": why,
        "external_source": source,
        "human_review_required": True,
    }


def preflight(project, c):
    engines.validate_config(c)
    s.integrity(project)
    registered = {x["id"] for x in s.model(project)["sources"]}
    for entry in [
        *c.get("scenarios", []),
        *c.get("shocks", []),
        c.get("observations", {}),
    ]:
        if set(entry.get("source_ids", [])) - registered:
            raise s.Invalid("Experimento referencia fonte não registrada.")
    for scenario in c.get("scenarios", []):
        for region in scenario.get("regions", []):
            if set(region.get("source_ids", [])) - registered:
                raise s.Invalid("Região referencia fonte não registrada.")
    for scenario in c.get("scenarios", []):
        for component in ("finance", "price_response"):
            if set(scenario.get(component, {}).get("source_ids", [])) - registered:
                raise s.Invalid(
                    "Premissa financeira/comportamental referencia fonte não registrada."
                )
    h, files = s.binding(project, c)
    engine = c["engine"]
    agents = c.get("agents", 100)
    ticks = c.get("ticks", 12)
    trials = c.get("trials", 100)
    scenarios = len(c.get("scenarios", [])) or 1
    work = (
        agents * ticks * trials
        if engine == "agents"
        else trials * ticks
        if engine in {"monte-carlo", "failure"}
        else ticks
    ) * scenarios
    work *= max([len(x.get("regions", [])) for x in c.get("scenarios", [])] or [1]) or 1
    if engine == "failure":
        work *= max(1, len(c.get("nodes", [])) + len(c.get("edges", [])))
    if engine == "mcmc":
        work = trials * c.get("chains", 4)
    if engine in {"ml", "bdh"}:
        from .predictive import dataset

        payload, features, train, test = dataset(project, c)
        work = (
            (len(train) + len(test))
            * c.get("training_steps", 300 if engine == "ml" else 5)
            * len(features)
        )
    if work > 20_000_000:
        raise s.Invalid(
            "Escopo excede limite operacional de referência; reduza o plano e faça benchmark independente."
        )
    if engine in {"oasis", "matraix"}:
        exe = Path(c.get("python_executable", ""))
        if not exe.is_absolute() or not exe.is_file():
            raise s.Invalid(
                "Selecione o Python absoluto do runtime opcional instalado; não há instalação/fallback automático."
            )
        if not c.get("smoke") and not c.get("model"):
            raise s.Invalid("Execução comportamental exige modelo declarado.")
        if engine == "oasis":
            if c.get("cost_limit", 0) != 0:
                raise s.Invalid(
                    "OASIS pago ainda não tem medição rígida de custo neste adapter; use LLM local ou outro runtime com orçamento verificável."
                )
            u = urlsplit(c.get("base_url", "http://127.0.0.1:8000/v1"))
            if (
                u.scheme != "http"
                or u.hostname not in {"127.0.0.1", "localhost", "::1"}
                or u.username
                or u.password
            ):
                raise s.Invalid(
                    "OASIS inicial aceita apenas servidor LLM local loopback, sem credenciais na URL."
                )
            profiles = s.read(s.inside(project, c["profile_path"]))
            if len(profiles) != agents or not c.get("initial_post"):
                raise s.Invalid(
                    "Perfis e tema inicial devem corresponder ao experimento."
                )
        if engine == "matraix":
            runtime = Path(c.get("runtime_root", ""))
            if not runtime.is_absolute() or not (runtime / "pyproject.toml").is_file():
                raise s.Invalid("Runtime MatrAIx ausente.")
            if not c.get("smoke") and not c.get("recipe"):
                raise s.Invalid(
                    "MatrAIx comportamental exige recipe da tarefa/personas."
                )
    if engine == "matraix" and not c.get("smoke"):
        config = {**c, "recipe": str(s.inside(project, c["recipe"]))}
        worker = Path(__file__).with_name("external_worker.py")
        check = subprocess.run(
            [c["python_executable"], str(worker)],
            input=s.canonical(
                {
                    "operation": "preflight",
                    "config": config,
                    "output": str(s.root(project) / "preflight-work"),
                }
            ),
            capture_output=True,
            text=True,
            timeout=15,
            env={
                k: v
                for k, v in os.environ.items()
                if k in {"PATH", "HOME", "TMPDIR", "LANG", "LC_ALL", "SYSTEMROOT"}
            },
        )
        try:
            checked = __import__("json").loads(check.stdout)
        except ValueError:
            raise s.Invalid("Runtime opcional não validou o contrato da tarefa.")
        if check.returncode or not checked.get("ok"):
            raise s.Invalid(
                "Recipe MatrAIx inválida: conferir modelo, número de agentes/tarefas, referências de credencial e teto/estimativa de custo. Nenhum provedor foi chamado."
            )
    if engine == "bdh":
        if not c.get("bdh_source") or not c.get("bdh_source_sha256"):
            raise s.Invalid("BDH exige fonte oficial e SHA256.")
    for shock in c.get("shocks", []):
        if shock.get("parameter") not in {
            "price",
            "variable_cost",
            "conversion",
        } or not shock.get("source_ids"):
            raise s.Invalid("Choque exige parâmetro permitido e origem explícita.")
        for k in ("start", "duration", "multiplier"):
            s.finite(shock.get(k), k, 0)
    s.finite(c.get("interaction_strength", 0), "interaction_strength", 0, 1)
    return {
        "input_hash": h,
        "file_hashes": files,
        "engine": engine,
        "reason": WHY[engine][0],
        "method_source": WHY[engine][1],
        "operations_upper_reference": work,
        "memory_estimate_bytes": max(16384, agents * 32 + ticks * scenarios * 2048),
        "memory_estimate_limitation": "Estimativa estrutural dos motores locais; não é benchmark de Python nem memória de LLM/GPU. Engines opcionais exigem medição no runtime.",
        "cost_limit": c.get("cost_limit", 0),
        "estimated_cost": c.get("estimated_cost", 0),
        "timeout_seconds": c.get("timeout_seconds", 120),
        "requires": ["method-review", "specific-execution-grant"],
        "capabilities": capabilities(),
    }


def external(project, c, out):
    config = {**c}
    for key in ("profile_path", "recipe"):
        if config.get(key):
            config[key] = str(s.inside(project, config[key]))
    env = {
        k: v
        for k, v in os.environ.items()
        if k in {"PATH", "HOME", "TMPDIR", "SYSTEMROOT", "LANG", "LC_ALL"}
    }
    for name in c.get("credential_refs", []):
        if name not in {
            "OPENAI_API_KEY",
            "ANTHROPIC_API_KEY",
            "GEMINI_API_KEY",
            "DASHSCOPE_API_KEY",
            "OPENROUTER_API_KEY",
        }:
            raise s.Invalid("Referência de credencial não permitida.")
        if not os.environ.get(name):
            raise s.Invalid(
                "Uma referência de credencial está ausente; configure no terminal, nunca no chat."
            )
        env[name] = os.environ[name]
    worker = Path(__file__).with_name("external_worker.py")
    proc = subprocess.Popen(
        [c["python_executable"], str(worker)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env,
        start_new_session=os.name != "nt",
        cwd=out,
    )
    try:
        stdout, stderr = proc.communicate(
            s.canonical({"config": config, "output": str(out)}),
            timeout=c.get("timeout_seconds", 120),
        )
    except subprocess.TimeoutExpired:
        if os.name != "nt":
            os.killpg(proc.pid, signal.SIGKILL)
        else:
            proc.kill()
        proc.communicate()
        raise s.Invalid(
            "Engine interrompido pelo limite de tempo; tentativa preservada sem resultado."
        )
    try:
        payload = __import__("json").loads(stdout)
    except ValueError:
        raise s.Invalid("Engine não retornou protocolo válido; sem fallback.")
    if proc.returncode or not payload.get("ok"):
        raise s.Invalid(
            "Execução opcional falhou; diagnóstico local não é validação do experimento."
        )
    return payload["result"]


def run(project, c, grant):
    pre = preflight(project, c)
    with s.lock(project):
        authorization = s.consume(project, c, grant)
        authorized_model = s.model(project)
    folder = s.root(project) / "runs" / ("RUN-" + uuid.uuid4().hex[:16])
    folder.mkdir(parents=True)
    start = time.monotonic()
    s.atomic(folder / "config.json", c)
    s.atomic(folder / "preflight.json", pre)
    s.atomic(folder / "authorization.json", authorization)
    manifest = {
        "id": folder.name,
        "input_hash": pre["input_hash"],
        "config_hash": s.digest(c),
        "seed": c.get("seed", 42),
        "created_at": s.now(),
        "engine": c["engine"],
        "status": "running",
        "code_hashes": {
            p.name: s.file_hash(p) for p in Path(__file__).parent.glob("*.py")
        },
        "environment": capabilities(),
        "synthetic": True,
    }
    s.atomic(folder / "manifest.json", manifest)
    try:
        s.atomic(folder / "model-input.json", authorized_model)
        execution_config = {**c}
        for key in (
            "dataset",
            "profile_path",
            "recipe",
            "bdh_source",
            "tokenizer_path",
        ):
            if c.get(key):
                src = s.inside(project, c[key])
                dst = folder / "inputs" / key / src.name
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(src, dst)
                if s.file_hash(dst) != pre["file_hashes"][key]:
                    raise s.Invalid("Arquivo mudou durante o congelamento dos dados.")
                execution_config[key] = str(dst)
        s.atomic(folder / "execution-config.json", execution_config)
        if c["engine"] in {"oasis", "matraix"}:
            result = external(project, execution_config, folder)
        else:
            worker = Path(__file__).with_name("local_worker.py")
            proc = subprocess.run(
                [sys.executable, str(worker)],
                input=s.canonical(
                    {
                        "config": execution_config,
                        "project": str(Path(project).resolve()),
                    }
                ),
                text=True,
                capture_output=True,
                env={
                    **{
                        k: v
                        for k, v in os.environ.items()
                        if k
                        in {"PATH", "HOME", "TMPDIR", "SYSTEMROOT", "LANG", "LC_ALL"}
                    },
                    "OMP_NUM_THREADS": "1",
                    "MKL_NUM_THREADS": "1",
                    "OPENBLAS_NUM_THREADS": "1",
                },
                timeout=c.get("timeout_seconds", 120),
            )
            try:
                payload = __import__("json").loads(proc.stdout)
            except ValueError:
                raise s.Invalid("Executor local não retornou resultado válido.")
            if proc.returncode or not payload.get("ok"):
                raise s.Invalid(
                    "Experimento local falhou: "
                    + payload.get("message", "sem resultado")
                )
            result = payload["result"]
        if time.monotonic() - start > c.get("timeout_seconds", 120):
            raise s.Invalid("Execução excedeu o tempo; resultado não aceito.")
        s.atomic(folder / "result.json", result)
        if result.get("timeseries"):
            rows = result["timeseries"]
            fields = list(dict.fromkeys(key for row in rows for key in row))
            buffer = io.StringIO()
            w = csv.DictWriter(buffer, fieldnames=fields)
            w.writeheader()
            w.writerows(rows)
            s.atomic(folder / "timeseries.csv", buffer.getvalue())
        manifest = {
            **manifest,
            "status": "completed",
            "elapsed_seconds": time.monotonic() - start,
            "result_hash": s.file_hash(folder / "result.json"),
        }
        s.atomic(folder / "manifest.json", manifest)
        with s.lock(project):
            m = s.model(project)
            s.save(
                project,
                {
                    **m,
                    "runs": [
                        *m["runs"],
                        {
                            "id": folder.name,
                            "engine": c["engine"],
                            "input_hash": pre["input_hash"],
                            "config_hash": s.digest(c),
                            "result_hash": manifest["result_hash"],
                            "status": "completed",
                            "interpretation_status": "pending",
                        },
                    ],
                },
                "simulation-completed",
                {"run_id": folder.name},
            )
        # Coordinated refresh keeps both outputs coherent; interpretation remains pending until authored.
        from .reports import render

        try:
            render(project)
            manifest = {**manifest, "export_status": "refreshed"}
        except Exception as export_error:
            manifest = {
                **manifest,
                "export_status": "failed",
                "export_error_type": type(export_error).__name__,
            }
            with s.lock(project):
                s.append(
                    project,
                    "export-refresh-failed",
                    {"run_id": folder.name, "error_type": type(export_error).__name__},
                )
        s.atomic(folder / "manifest.json", manifest)
        return manifest
    except Exception as error:
        manifest = {
            **manifest,
            "status": "failed",
            "elapsed_seconds": time.monotonic() - start,
            "error_type": type(error).__name__,
        }
        s.atomic(folder / "manifest.json", manifest)
        with s.lock(project):
            s.append(
                project,
                "simulation-failed",
                {"run_id": folder.name, "error_type": type(error).__name__},
            )
        raise
