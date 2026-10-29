"""Small declarative visual contract for business-specific diagrams; escaped SVG, no arbitrary HTML."""

from html import escape as e
import textwrap
from . import store as s


def validate(visual, known):
    if (
        visual.get("type") not in {"flow", "comparison", "matrix"}
        or not visual.get("title")
        or not visual.get("source_ids")
        or set(visual["source_ids"]) - known
    ):
        raise s.Invalid(
            "Visual exige tipo suportado, título e fontes externas registradas."
        )
    if not visual.get("classification") or not visual.get("caption"):
        raise s.Invalid("Visual exige natureza dos dados e explicação para o leitor.")
    if visual["type"] == "flow":
        nodes = visual.get("nodes", [])
        ids = {n["id"] for n in nodes}
        if not nodes or len(nodes) > 12 or len(ids) != len(nodes):
            raise s.Invalid("Fluxo exige 1–12 nós distintos.")
        for edge in visual.get("edges", []):
            if edge["from"] not in ids or edge["to"] not in ids:
                raise s.Invalid("Conexão visual aponta para nó ausente.")
    elif visual["type"] == "comparison":
        if not visual.get("unit") or not visual.get("period"):
            raise s.Invalid("Comparação visual exige unidade e período.")
        if not 1 <= len(visual.get("items", [])) <= 12:
            raise s.Invalid("Comparação exige 1–12 itens.")
        for item in visual["items"]:
            s.finite(item["value"], "valor gráfico")
    else:
        rows = visual.get("rows", [])
        cols = visual.get("columns", [])
        if (
            not rows
            or not cols
            or len(rows) > 20
            or len(cols) > 8
            or any(len(row) != len(cols) for row in rows)
        ):
            raise s.Invalid(
                "Matriz deve ter até 20 linhas e oito colunas, com células correspondentes."
            )
    return visual


def render(v):
    parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 580" role="img"><title>'
        + e(v["title"])
        + "</title><desc>"
        + e(v["caption"])
        + '</desc><rect width="1000" height="580" fill="#fffefa"/>'
    ]

    def txt(x, y, value, size=17):
        parts.append(
            f'<text x="{x}" y="{y}" fill="#1c2522" font-family="Trebuchet MS,sans-serif" font-size="{size}">{e(str(value))}</text>'
        )

    txt(30, 38, v["title"], 23)
    txt(30, 65, v["classification"], 13)
    if v["type"] == "flow":
        positions = {
            n["id"]: (40 + (i % 4) * 240, 115 + (i // 4) * 115)
            for i, n in enumerate(v["nodes"])
        }
        for edge in v.get("edges", []):
            x, y = positions[edge["from"]]
            xx, yy = positions[edge["to"]]
            parts.append(
                f'<path d="M{x + 200},{y + 40} L{xx},{yy + 40}" stroke="#668d74" stroke-width="2" fill="none"/>'
            )
        for n in v["nodes"]:
            x, y = positions[n["id"]]
            parts.append(
                f'<rect x="{x}" y="{y}" width="200" height="80" fill="#e9eee7" stroke="#9bada0"/>'
            )
            for i, line in enumerate(textwrap.wrap(n["label"], 23)[:3]):
                txt(x + 12, y + 25 + i * 20, line, 15)
    elif v["type"] == "comparison":
        items = v["items"]
        lo = min(0, *[x["value"] for x in items])
        hi = max(0, *[x["value"] for x in items])
        span = hi - lo or 1
        position = lambda x: 240 + (x - lo) / span * 620
        zero = position(0)
        parts.append(f'<path d="M{zero},95 V470" stroke="#9bada0"/>')
        for i, item in enumerate(items):
            y = 100 + i * 30
            x = position(item["value"])
            txt(30, y + 15, item["label"][:27], 14)
            parts.append(
                f'<rect x="{min(zero, x)}" y="{y}" width="{max(1, abs(x - zero))}" height="20" fill="'
                + ("#ad6656" if item["value"] < 0 else "#668d74")
                + '"/>'
            )
            txt(875, y + 15, round(item["value"], 2), 13)
        txt(240, 490, v["unit"] + " · " + v["period"], 13)
    else:
        cols = v["columns"]
        rows = [cols, *v["rows"]]
        w = 940 / len(cols)
        h = min(36, 400 / len(rows))
        for i, row in enumerate(rows):
            for j, value in enumerate(row):
                x = 30 + j * w
                y = 100 + i * h
                parts.append(
                    f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="'
                    + ("#e9eee7" if i == 0 else "#fffefa")
                    + '" stroke="#d6dbd2"/>'
                )
                txt(x + 7, y + h * 0.65, str(value)[: max(10, int(w / 8) - 1)], 12)
    for i, line in enumerate(textwrap.wrap(v["caption"], 110)[:2]):
        txt(30, 535 + i * 19, line, 13)
    parts.append("</svg>")
    return "".join(parts)
