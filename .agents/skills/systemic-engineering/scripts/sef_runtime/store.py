"""Bounded local documents, immutable events and scoped human execution grants."""

from __future__ import annotations
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
import csv, hashlib, json, math, os, re, tempfile, uuid


class Invalid(ValueError):
    pass


def now():
    return datetime.now(timezone.utc).isoformat()


def canonical(value):
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        allow_nan=False,
        separators=(",", ":"),
    )


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def file_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    p = Path(path)
    if p.stat().st_size > 20_000_000:
        raise Invalid("Arquivo excede o limite de 20 MB.")

    def bad(value):
        raise Invalid("Número não finito no JSON.")

    return json.loads(p.read_text(encoding="utf-8"), parse_constant=bad)


def atomic(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".write-")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(value if isinstance(value, str) else canonical(value) + "\n")
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def inside(root, value):
    root = Path(root).resolve()
    p = (root / str(value)).resolve()
    if not p.is_relative_to(root):
        raise Invalid("Caminho fora do projeto.")
    return p


def root(project):
    p = Path(project).resolve() / ".systemic-engineering"
    if not (p / "state.json").is_file():
        raise Invalid(
            "Inicialize o projeto com sef.py init antes de habilitar consultoria."
        )
    return p / "08-consulting"


def model(project):
    p = root(project) / "model.json"
    if not p.exists():
        raise Invalid("Habilite com consult enable.")
    return read(p)


@contextmanager
def lock(project):
    p = root(project)
    p.mkdir(parents=True, exist_ok=True)
    d = p / ".writer-lock"
    try:
        d.mkdir()
    except FileExistsError:
        raise Invalid(
            "Há outra escrita ou um lock interrompido. Inspecione antes de recuperar."
        )
    try:
        yield
    finally:
        d.rmdir()


def fresh(project):
    return {
        "schema_version": 1,
        "project_name": read(root(project).parent / "state.json")["project_name"],
        "language": "pt-BR",
        "enabled_at": now(),
        "revision": 0,
        "problem": None,
        "stakeholders": [],
        "objectives": [],
        "rounds": [],
        "answers": [],
        "conflicts": [],
        "sources": [],
        "claims": [],
        "alternatives": [],
        "criteria": [],
        "actions": [],
        "risks": [],
        "relations": [],
        "artifacts": {},
        "analysis": {},
        "runs": [],
        "decisions": [],
    }


def enable(project):
    with lock(project):
        p = root(project) / "model.json"
        if p.exists():
            raise Invalid("Consultoria já habilitada; estado existente preservado.")
        atomic(p, fresh(project))
        atomic(root(project) / "audit.jsonl", "")
    return {
        "enabled": True,
        "phase": read(root(project).parent / "state.json")["phase"],
    }


def events(project):
    path = root(project) / "audit.jsonl"
    result = []
    previous = "0" * 64
    if not path.exists():
        return []
    for line in path.read_text().splitlines():
        item = json.loads(line)
        expected = digest({k: v for k, v in item.items() if k != "hash"})
        if item.get("previous") != previous or item.get("hash") != expected:
            raise Invalid("Auditoria foi alterada ou truncada internamente.")
        previous = item["hash"]
        result.append(item)
    return result


def append(project, kind, payload):
    records = events(project)
    base = {
        "id": str(uuid.uuid4()),
        "at": now(),
        "kind": kind,
        "payload": payload,
        "previous": records[-1]["hash"] if records else "0" * 64,
    }
    item = {**base, "hash": digest(base)}
    with (root(project) / "audit.jsonl").open("a", encoding="utf-8") as f:
        f.write(canonical(item) + "\n")
        f.flush()
        os.fsync(f.fileno())
    return item


def save(project, data, kind, details=None):
    old = model(project)
    new = {**data, "revision": old["revision"] + 1, "updated_at": now()}
    # Immutable snapshots preserve the prior state even if materialized JSON is replaced.
    snap = root(project) / "revisions" / f"{old['revision']:06}-{digest(old)[:12]}.json"
    if not snap.exists():
        atomic(snap, old)
    journal = {
        "before": digest(old),
        "after": new,
        "kind": kind,
        "details": details or {},
    }
    atomic(root(project) / "pending-write.json", journal)
    append(
        project,
        kind,
        {"revision": new["revision"], "input_hash": digest(new), **(details or {})},
    )
    atomic(root(project) / "model.json", new)
    (root(project) / "pending-write.json").unlink()
    return new


def integrity(project):
    if (root(project) / "pending-write.json").exists():
        raise Invalid("Escrita interrompida: recupere com consult recover.")
    log = events(project)
    changes = [x for x in log if "revision" in x["payload"]]
    if changes and changes[-1]["payload"]["input_hash"] != digest(model(project)):
        raise Invalid(
            "Modelo diverge da auditoria; não editar model.json diretamente. Use consult import."
        )
    if not changes and model(project)["revision"] != 0:
        raise Invalid("Modelo sem histórico de revisão correspondente.")
    return log


def recover(project):
    with lock(project):
        p = root(project) / "pending-write.json"
        if not p.exists():
            return {"recovered": False}
        j = read(p)
        data = j["after"]
        log = events(project)
        h = digest(data)
        if not any(e["payload"].get("input_hash") == h for e in log):
            append(
                project,
                j["kind"],
                {"revision": data["revision"], "input_hash": h, **j["details"]},
            )
        atomic(root(project) / "model.json", data)
        p.unlink()
        integrity(project)
        return {"recovered": True, "revision": data["revision"]}


def finite(value, name, lo=None, hi=None):
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
    ):
        raise Invalid(f"{name}: número finito obrigatório.")
    if lo is not None and value < lo or hi is not None and value > hi:
        raise Invalid(f"{name}: valor fora do intervalo permitido.")
    return value


def authority(project, authority_id, by, scope):
    p = root(project).parent / "00-intake/authorities.csv"
    with p.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    a = next((x for x in rows if x["authority_id"] == authority_id), None)
    if not a or a["status"] != "active" or a["name"] != by:
        raise Invalid("Autoridade ativa e identidade correspondente são obrigatórias.")
    if a.get("role") not in {
        "user",
        "domain-expert",
        "safety-authority",
        "independent-reviewer",
    }:
        raise Invalid(
            "O papel registrado não é uma autoridade humana aprovadora reconhecida."
        )
    scopes = set(re.split(r"[,;\s]+", a["scope"].lower()))
    if not scopes.intersection(
        {"all", "*", scope, "consulting"}
        | ({"execution"} if scope == "simulation" else set())
    ):
        raise Invalid("Autoridade não cobre este escopo.")
    return a


def binding(project, config):
    copies = {}
    for key in ("dataset", "profile_path", "recipe", "bdh_source", "tokenizer_path"):
        if config.get(key):
            p = inside(Path(project), config[key])
            if not p.is_file():
                raise Invalid(f"Arquivo ausente: {key}")
            copies[key] = file_hash(p)
    if config.get("python_executable"):
        exe = Path(config["python_executable"]).resolve()
        if not exe.is_file():
            raise Invalid("Runtime executável ausente.")
        copies["python_executable"] = file_hash(exe)
    state = read(root(project).parent / "state.json")
    governance = {
        "risk_class": state["risk_class"],
        "mode": state["mode"],
        "authorities": file_hash(root(project).parent / "00-intake/authorities.csv"),
    }
    return digest(
        {
            "config": config,
            "files": copies,
            "model": digest(model(project)),
            "governance": governance,
            "implementation": {
                p.name: file_hash(p) for p in Path(__file__).parent.glob("*.py")
            },
        }
    ), copies


def authorize(
    project, config, kind, by, authority_id, evidence, attestation, fixture=False
):
    if not evidence.strip() or len(attestation.strip()) < 12:
        raise Invalid("Informe referência da declaração humana e seu escopo explícito.")
    a = authority(
        project,
        authority_id,
        by,
        "research"
        if config.get("engine") in {"capture", "browser-capture"}
        else "simulation",
    )
    state = read(root(project).parent / "state.json")
    if state["risk_class"] == "unset":
        raise Invalid("Defina a classe de risco antes de registrar autorização.")
    if fixture and state["mode"] != "fixture":
        raise Invalid("Aprovação fictícia só vale em projeto fixture.")
    if state["mode"] == "fixture" and not fixture:
        raise Invalid("Projeto fixture não recebe autorização real.")
    if (
        kind == "method"
        and state["risk_class"] in {"high", "safety-critical"}
        and a["role"] not in {"domain-expert", "safety-authority"}
    ):
        raise Invalid(
            "Revisão de método de alto impacto exige especialista registrado."
        )
    if state["risk_class"] == "safety-critical" and a["role"] not in {
        "domain-expert",
        "safety-authority",
    }:
        raise Invalid(
            "Execução crítica exige autoridade qualificada; aprovação de fase continua independente."
        )
    h, files = binding(project, config)
    with lock(project):
        log = integrity(project)
        if kind == "execution" and not any(
            x["kind"] == "authorization"
            and x["payload"]["kind"] == "method"
            and x["payload"]["input_hash"] == h
            for x in log
        ):
            raise Invalid("Revisão metodológica específica ausente ou desatualizada.")
        record = {
            "grant_id": "GRANT-" + uuid.uuid4().hex[:16],
            "kind": kind,
            "input_hash": h,
            "files": files,
            "authority_id": authority_id,
            "by": by,
            "role": a["role"],
            "evidence": evidence,
            "attestation": attestation,
            "fixture": fixture,
            "config_cost_limit": config.get("cost_limit", 0),
        }
        append(project, "authorization", record)
    return record


def consume(project, config, grant_id):
    h, _ = binding(project, config)
    log = integrity(project)
    item = next(
        (
            x["payload"]
            for x in log
            if x["kind"] == "authorization" and x["payload"]["grant_id"] == grant_id
        ),
        None,
    )
    if not item or item["kind"] != "execution" or item["input_hash"] != h:
        raise Invalid(
            "Autorização de execução ausente, de outro escopo ou desatualizada."
        )
    authority(
        project,
        item["authority_id"],
        item["by"],
        "research"
        if config.get("engine") in {"capture", "browser-capture"}
        else "simulation",
    )
    if any(
        x["kind"] == "grant-consumed" and x["payload"]["grant_id"] == grant_id
        for x in log
    ):
        raise Invalid(
            "Autorização já consumida; a tentativa anterior permanece registrada."
        )
    if item["fixture"] and (
        config.get("engine")
        not in {"monte-carlo", "agents", "dynamics", "failure", "mcmc", "ml"}
        or config.get("external")
        or config.get("cost_limit", 0) > 0
        or config.get("agents", 1) > 100
        or config.get("ticks", 1) > 12
        or config.get("trials", 1) > 200
    ):
        raise Invalid(
            "Fixture limitada a smoke local, sem serviço externo, BDH ou custo."
        )
    append(project, "grant-consumed", {"grant_id": grant_id, "input_hash": h})
    return item
