"""Claim-level external evidence, provenance, triangulation and bounded public capture."""

from __future__ import annotations
from datetime import date
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit, urljoin
import csv, io, ipaddress, http.client, socket, ssl, hashlib
from . import store as s

REQUIRED = (
    "id",
    "title",
    "url",
    "published_at",
    "accessed_at",
    "evidence",
    "confidence",
    "limitations",
    "independence_group",
)


def public_url(url):
    u = urlsplit(url)
    if (
        u.scheme not in {"http", "https"}
        or not u.hostname
        or u.username
        or u.password
        or u.fragment
    ):
        raise s.Invalid("Fonte exige URL pública http(s), sem credencial ou fragmento.")
    if u.port and u.port not in {80, 443}:
        raise s.Invalid("Porta de captura não permitida.")
    return u


def validate_source(src):
    missing = [k for k in REQUIRED if not src.get(k)]
    if missing:
        raise s.Invalid("Fonte incompleta: " + ", ".join(missing))
    if not str(src["id"]).startswith("SRC-"):
        raise s.Invalid("Fonte exige ID SRC-.")
    u = public_url(src["url"])
    if u.hostname in {"github.com", "raw.githubusercontent.com"} and any(
        x in u.path.lower()
        for x in (
            "mvellas/systemic-engineering-skill",
            "mvellas/disruptive-venture-lab",
        )
    ):
        raise s.Invalid(
            "Os próprios repositórios/documentos não são evidência externa para fundamentar a análise."
        )
    for k in ("published_at", "accessed_at"):
        if src[k] != "unknown":
            try:
                date.fromisoformat(src[k])
            except (ValueError, TypeError):
                raise s.Invalid("Data de fonte inválida; use YYYY-MM-DD ou unknown.")
    if src["confidence"] not in {"low", "medium", "high"}:
        raise s.Invalid(
            "Confiança exige low, medium ou high e justificativa em limitations."
        )
    if src.get("source_type") == "internal" or src.get("self_authored"):
        raise s.Invalid("Documento interno não serve como prova externa.")
    if len(src["evidence"]) > 5000:
        raise s.Invalid(
            "Registre evidência curta, localizada, não reprodução integral."
        )
    if not src.get("location"):
        raise s.Invalid("Informe seção, página ou localização da evidência.")
    return {
        **src,
        "evidence_hash": hashlib.sha256(src["evidence"].encode()).hexdigest(),
    }


def add_source(project, payload):
    src = validate_source(payload)
    with s.lock(project):
        s.integrity(project)
        m = s.model(project)
        if src["id"] in {x["id"] for x in m["sources"]}:
            raise s.Invalid(
                "ID de fonte já existe; preserve histórico com novo ID e relação supersedes."
            )
        sources = [*m["sources"], src]
        s.save(
            project, {**m, "sources": sources}, "source-added", {"source_id": src["id"]}
        )
        path = s.root(project).parent / "00-intake/source-register.csv"
        with path.open(newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            fields = reader.fieldnames
            old = list(reader)
        if src["id"] not in {x["source_id"] for x in old}:
            row = {
                "source_id": src["id"],
                "title": src["title"],
                "authority": src.get("authority", urlsplit(src["url"]).hostname),
                "url_or_path": src["url"],
                "published_at": src["published_at"],
                "accessed_at": src["accessed_at"],
                "claim": src["evidence"],
                "limitations": src["limitations"],
                "confidence": src["confidence"],
                "relation": src.get("relation", "supports"),
            }
            out = io.StringIO()
            writer = csv.DictWriter(out, fieldnames=fields)
            writer.writeheader()
            writer.writerows([*old, {k: row.get(k, "") for k in fields}])
            s.atomic(path, out.getvalue())
    return src


def add_claim(project, payload):
    if (
        not payload.get("id")
        or not payload.get("text")
        or payload.get("kind")
        not in {"observed", "hypothesis", "inference", "simulated"}
    ):
        raise s.Invalid("Afirmação exige ID, texto e tipo.")
    with s.lock(project):
        s.integrity(project)
        m = s.model(project)
        ids = set(payload.get("source_ids", []))
        known = {x["id"] for x in m["sources"]}
        if not ids or ids - known:
            raise s.Invalid(
                "Toda afirmação precisa de fontes externas registradas; hipótese também registra a origem metodológica e seus limites."
            )
        if payload["id"] in {x["id"] for x in m["claims"]}:
            raise s.Invalid("ID de afirmação repetido.")
        if payload["kind"] == "simulated" and not payload.get("run_id"):
            raise s.Invalid("Afirmação simulada exige run_id e configuração.")
        if not payload.get("limitations"):
            raise s.Invalid("Afirmação exige limites explícitos.")
        s.save(
            project,
            {
                **m,
                "claims": [*m["claims"], payload],
                "relations": [
                    *m["relations"],
                    *[
                        {
                            "from": i,
                            "to": payload["id"],
                            "relationship": "supports",
                            "status": "registered",
                        }
                        for i in ids
                    ],
                ],
            },
            "claim-added",
            {"claim_id": payload["id"]},
        )
    return payload


def audit(project, as_of=None, max_age=365):
    m = s.model(project)
    today = date.fromisoformat(as_of) if as_of else date.today()
    issues = []
    rows = []
    for src in m["sources"]:
        try:
            validate_source(src)
        except s.Invalid as e:
            issues.append(f"{src.get('id')}: {e}")
            continue
        if src.get("capture_path"):
            f = s.inside(project, src["capture_path"])
            if not f.is_file() or s.file_hash(f) != src.get("capture_sha256"):
                issues.append(src["id"] + ": captura ausente ou alterada")
        accessed = src["accessed_at"]
        published = src["published_at"]
        age = (
            (today - date.fromisoformat(accessed)).days
            if accessed != "unknown"
            else None
        )
        content_age = (
            (today - date.fromisoformat(published)).days
            if published != "unknown"
            else None
        )
        if age is not None and age < 0:
            issues.append(src["id"] + ": consulta futura em relação à data-base")
        if age is None or age > max_age:
            issues.append(
                src["id"] + ": consulta ausente ou antiga; revisar atualidade"
            )
        rows.append(
            {
                "source_id": src["id"],
                "days_since_access": age,
                "days_since_publication": content_age,
                "freshness_note": "Data de consulta não comprova atualidade do conteúdo; validade depende do assunto.",
            }
        )
    for claim in m["claims"]:
        sources = [x for x in m["sources"] if x["id"] in claim.get("source_ids", [])]
        groups = {x["independence_group"] for x in sources}
        if not sources:
            issues.append(claim["id"] + ": sem evidência externa")
        if len(groups) < 2:
            issues.append(
                claim["id"] + ": fonte única ou dependente; triangulação pendente"
            )
    issues.extend(
        c["id"] + ": contradição não resolvida"
        for c in m["conflicts"]
        if c["status"] == "pending"
    )
    return {
        "as_of": today.isoformat(),
        "sources": rows,
        "issues": issues,
        "conclusion": "Fontes verificadas estruturalmente; credibilidade e adequação da interpretação exigem revisão humana.",
    }


def plan(project):
    m = s.model(project)
    return {
        "question": m["problem"],
        "tasks": [
            {
                "topic": x,
                "questions": q,
                "preferred_sources": p,
                "capture": "Somente material público autorizado; registrar URL, data, trecho, limite e grupo de independência.",
            }
            for x, q, p in [
                (
                    "mercado",
                    "Quem enfrenta o problema, com que frequência e alternativas?",
                    "Estatísticas oficiais e estudos com método explícito",
                ),
                (
                    "concorrentes",
                    "Produtos, preço, unidade cobrada, condições, diferencial e reclamações?",
                    "Páginas oficiais datadas e avaliações independentes",
                ),
                (
                    "fornecedores",
                    "Capacidade, preço, dependência, suporte e disponibilidade?",
                    "Catálogos, termos públicos e propostas autorizadas",
                ),
                (
                    "regulação",
                    "Qual obrigação se aplica a qual atividade, território e vigência?",
                    "Órgão regulador e texto primário; revisão por especialista",
                ),
                (
                    "comunicação",
                    "Que promessa, criativo, público e etapa do funil são visíveis?",
                    "Website, redes e bibliotecas de anúncios acessíveis; nunca inferir gasto, CAC ou ROAS do criativo",
                ),
                (
                    "contraprova",
                    "O que poderia falsificar a recomendação ou explicar outro resultado?",
                    "Fontes independentes e resultados desfavoráveis",
                ),
            ]
        ],
        "execution": "O harness pesquisa com suas ferramentas disponíveis e importa evidências com research source. Sem navegador, exporte um pacote de investigação; não alegue pesquisa executada.",
    }


class VisibleText(HTMLParser):
    def __init__(self):
        super().__init__()
        self.skip = 0
        self.parts = []

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style", "noscript"}:
            self.skip += 1

    def handle_endtag(self, tag):
        if tag in {"script", "style", "noscript"} and self.skip:
            self.skip -= 1

    def handle_data(self, data):
        if not self.skip and data.strip():
            self.parts.append(data.strip())


def fetch_public(url, limit=2_000_000):
    """Resolve once and connect to checked IP, preserving TLS hostname; redirects rechecked."""
    allowed_origin = urlsplit(url).netloc
    for redirect in range(5):
        if urlsplit(url).netloc != allowed_origin:
            raise s.Invalid(
                "Redirecionamento para outra origem exige autorização própria."
            )
        u = public_url(url)
        port = u.port or (443 if u.scheme == "https" else 80)
        records = socket.getaddrinfo(u.hostname, port, type=socket.SOCK_STREAM)
        addresses = [x[4][0] for x in records]
        if not addresses or any(
            not ipaddress.ip_address(x).is_global for x in addresses
        ):
            raise s.Invalid("Captura bloqueou endereço privado, local ou reservado.")
        raw = socket.create_connection((addresses[0], port), timeout=15)
        try:
            conn = http.client.HTTPConnection(u.hostname, port, timeout=15)
            conn.sock = (
                ssl.create_default_context().wrap_socket(
                    raw, server_hostname=u.hostname
                )
                if u.scheme == "https"
                else raw
            )
            conn.request(
                "GET",
                (u.path or "/") + ("?" + u.query if u.query else ""),
                headers={
                    "Host": u.netloc,
                    "User-Agent": "SEF-research/0.1 (+authorized-public-research)",
                    "Accept": "text/html,text/plain",
                },
            )
            res = conn.getresponse()
            if res.status in {301, 302, 303, 307, 308}:
                url = urljoin(url, res.getheader("Location", ""))
                continue
            if res.status != 200:
                raise s.Invalid(
                    f"Captura retornou HTTP {res.status}; não contornar acesso."
                )
            if "text/" not in res.getheader("Content-Type", ""):
                raise s.Invalid("Captura básica aceita apenas texto/HTML.")
            data = res.read(limit + 1)
            if len(data) > limit:
                raise s.Invalid("Captura excedeu o limite de tamanho.")
            return url, data
        finally:
            raw.close()
    raise s.Invalid("Número de redirecionamentos excedido.")


def capture(project, config, grant):
    if config.get("engine") != "capture" or not config.get("url"):
        raise s.Invalid("Configuração exige engine=capture e URL autorizada.")
    # A redirect is a new target, so validate publicness and require its final origin to be explicitly allowed.
    with s.lock(project):
        s.consume(project, config, grant)
    final, data = fetch_public(config["url"])
    if urlsplit(final).netloc != urlsplit(config["url"]).netloc:
        raise s.Invalid(
            "Redirecionamento para outra origem exige nova autorização; conteúdo não será registrado."
        )
    directory = (
        s.root(project)
        / "captures"
        / ("CAP-" + s.digest({"url": final, "at": s.now()})[:16])
    )
    directory.mkdir(parents=True)
    path = directory / "page.html"
    s.atomic(path, data.decode("utf-8", errors="replace"))
    parser = VisibleText()
    parser.feed(path.read_text())
    s.atomic(directory / "text.txt", "\n".join(parser.parts))
    receipt = {
        "url": final,
        "requested_url": config["url"],
        "captured_at": s.now(),
        "sha256": s.file_hash(path),
        "path": str(path.relative_to(Path(project).resolve())),
        "classification": "external_capture_not_yet_interpreted",
        "screenshot": "Use research screenshot para renderizar offline o snapshot; não é screenshot da página viva.",
    }
    s.atomic(directory / "receipt.json", receipt)
    with s.lock(project):
        s.append(project, "capture-completed", receipt)
    return receipt


def screenshot(project, capture_path):
    # Render archived text as plain content, never execute page scripts or fetch remote assets.
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        raise s.Invalid(
            "Screenshot requer extra playwright e navegador instalado; captura textual permanece disponível."
        )
    p = s.inside(project, capture_path)
    parser = VisibleText()
    parser.feed(p.read_text())
    text = "\n".join(parser.parts)
    from html import escape

    dest = p.parent / "snapshot-text.png"
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(
            java_script_enabled=False, viewport={"width": 1280, "height": 900}
        )
        page.route("**/*", lambda route: route.abort())
        page.set_content(
            '<meta charset="utf-8"><h1>Snapshot textual arquivado</h1><pre style="white-space:pre-wrap">'
            + escape(text[:100000])
            + "</pre>"
        )
        page.screenshot(path=str(dest), full_page=True)
        browser.close()
    return {
        "path": str(dest.relative_to(Path(project).resolve())),
        "sha256": s.file_hash(dest),
        "limitation": "Representação do texto capturado; não é reprodução visual do website original.",
    }


def browser_capture(project, config, grant):
    """Optional read-only screenshot with explicit origin scope; no cookies or JS by default."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        raise s.Invalid(
            "Captura visual requer playwright e Chromium no executor; não houve captura simulada."
        )
    u = public_url(config["url"])
    allowed = config.get("allowed_origins", [])
    origin = u.scheme + "://" + u.netloc
    if origin not in allowed or config.get("engine") != "browser-capture":
        raise s.Invalid("Origem exata e engine=browser-capture são obrigatórios.")
    if config.get("javascript_enabled"):
        raise s.Invalid(
            "Captura básica de pesquisa não executa JavaScript remoto. Use executor isolado específico para esse caso."
        )

    def permitted(url):
        try:
            v = public_url(url)
            if v.scheme + "://" + v.netloc not in allowed:
                return False
            addresses = socket.getaddrinfo(
                v.hostname, v.port or 443, type=socket.SOCK_STREAM
            )
            return bool(addresses) and all(
                ipaddress.ip_address(x[4][0]).is_global for x in addresses
            )
        except Exception:
            return False

    if not permitted(config["url"]):
        raise s.Invalid("Alvo visual não é uma origem pública permitida.")
    with s.lock(project):
        s.consume(project, config, grant)
    folder = (
        s.root(project)
        / "captures"
        / ("CAP-" + s.digest({"url": config["url"], "at": s.now()})[:16])
    )
    folder.mkdir(parents=True)
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        context = browser.new_context(
            java_script_enabled=False,
            accept_downloads=False,
            service_workers="block",
            viewport={"width": 1280, "height": 900},
        )
        page = context.new_page()

        def route(request):
            if request.request.method not in {"GET", "HEAD"} or not permitted(
                request.request.url
            ):
                request.abort()
            else:
                request.continue_()

        context.route("**/*", route)
        page.on("dialog", lambda dialog: dialog.dismiss())
        page.goto(config["url"], wait_until="domcontentloaded", timeout=30000)
        if not permitted(page.url):
            browser.close()
            raise s.Invalid("Origem final não autorizada.")
        page.screenshot(path=str(folder / "page.png"), full_page=False)
        s.atomic(folder / "page.html", page.content())
        final = page.url
        browser.close()
    receipt = {
        "url": final,
        "captured_at": s.now(),
        "path": str((folder / "page.png").relative_to(Path(project).resolve())),
        "sha256": s.file_hash(folder / "page.png"),
        "classification": "public-page-screenshot",
        "limitations": "Sem JavaScript, sessão autenticada ou recursos de origens não autorizadas. Filtro do navegador não equivale a isolamento de rede certificado contra DNS rebinding; para alvos adversariais usar executor com egress firewall.",
    }
    s.atomic(folder / "receipt.json", receipt)
    with s.lock(project):
        s.append(project, "visual-capture-completed", receipt)
    return receipt
