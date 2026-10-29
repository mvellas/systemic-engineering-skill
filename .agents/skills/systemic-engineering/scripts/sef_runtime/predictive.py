"""Supervised baselines, differentiable surrogate search, and optional official BDH."""

from __future__ import annotations
from pathlib import Path
import importlib.util, math, hashlib
from . import store as s


def dataset(project, c):
    payload = s.read(s.inside(project, c["dataset"]))
    rows = payload.get("rows", [])
    features = c.get("features", [])
    if not features or len(set(features)) != len(features) or len(features) > 30:
        raise s.Invalid("Defina 1–30 features sem repetição.")
    if len(rows) < 30 or len(rows) > 100000:
        raise s.Invalid(
            "Dataset exige 30–100.000 registros para este experimento de referência."
        )
    if not payload.get("source_ids") or payload.get("classification") not in {
        "observed",
        "synthetic",
    }:
        raise s.Invalid("Dataset exige fontes e classificação observed/synthetic.")
    from datetime import date

    dates = []
    ids = []
    for row in rows:
        try:
            date.fromisoformat(row["date"])
        except (KeyError, TypeError, ValueError):
            raise s.Invalid("Cada linha exige date ISO e ordem temporal verificável.")
        dates.append(row["date"])
        ids.append(row["id"])
        for f in features:
            s.finite(row["features"].get(f), f)
        s.finite(row["target"], "target")
    if dates != sorted(dates) or len(set(ids)) != len(ids):
        raise s.Invalid("Dataset deve estar em ordem temporal e sem IDs duplicados.")
    unique = sorted(set(dates))
    cut = unique[max(1, int(len(unique) * 0.7))] if len(unique) > 1 else None
    if not cut:
        raise s.Invalid("Sem períodos distintos para separar treino e teste.")
    train = [r for r in rows if r["date"] < cut]
    test = [r for r in rows if r["date"] >= cut]
    if len(train) < 20 or len(test) < 5:
        raise s.Invalid(
            "Treino/teste insuficientes; não ajustar a divisão para melhorar a métrica."
        )
    return payload, features, train, test


def ml(project, c):
    try:
        import numpy as np
    except ImportError:
        raise s.Invalid(
            "ML requer numpy instalado no executor; nenhum download automático."
        )
    payload, features, train, test = dataset(project, c)
    rng = np.random.default_rng(c.get("seed", 42))
    x = np.array([[r["features"][f] for f in features] for r in train])
    y = np.array([r["target"] for r in train])
    xt = np.array([[r["features"][f] for f in features] for r in test])
    yt = np.array([r["target"] for r in test])
    mean = x.mean(axis=0)
    scale = x.std(axis=0)
    scale[scale == 0] = 1
    ym = y.mean()
    ys = y.std() or 1.0
    xs = (x - mean) / scale
    xs_test = (xt - mean) / scale
    yn = (y - ym) / ys
    hidden = c.get("hidden_units", 8)
    steps = c.get("training_steps", 300)
    lr = c.get("learning_rate", 0.02)
    if (
        not isinstance(hidden, int)
        or not 1 <= hidden <= 64
        or not isinstance(steps, int)
        or not 1 <= steps <= 10000
    ):
        raise s.Invalid("Rede de referência: 1–64 unidades e 1–10.000 passos.")
    s.finite(lr, "learning_rate", 1e-6, 0.1)
    w1 = rng.normal(0, 0.2, (len(features), hidden))
    b1 = np.zeros(hidden)
    w2 = rng.normal(0, 0.2, hidden)
    b2 = 0.0
    losses = []
    for step in range(steps):
        h = np.tanh(xs @ w1 + b1)
        pred = h @ w2 + b2
        err = pred - yn
        g = 2 * err / len(y)
        gw2 = h.T @ g
        gb2 = g.sum()
        gh = g[:, None] * w2[None, :] * (1 - h * h)
        gw1 = xs.T @ gh
        gb1 = gh.sum(axis=0)
        w1 = w1 - lr * np.clip(gw1, -10, 10)
        b1 = b1 - lr * np.clip(gb1, -10, 10)
        w2 = w2 - lr * np.clip(gw2, -10, 10)
        b2 = b2 - lr * float(gb2)
        if step % max(1, steps // 20) == 0:
            losses.append({"step": step, "mse_train": float(np.mean(err**2) * ys**2)})
    pred = (np.tanh(xs_test @ w1 + b1) @ w2 + b2) * ys + ym
    mae = float(np.mean(abs(pred - yt)))
    rmse = float(np.sqrt(np.mean((pred - yt) ** 2)))
    baseline = float(np.mean(abs(ym - yt)))
    candidate = None
    if c.get("optimize"):
        opt = c["optimize"]
        bounds = opt["bounds"]
        start = opt["start"]
        z = np.array([start[f] for f in features], dtype=float)
        origin = z.copy()
        if set(bounds) != set(features) or set(start) != set(features):
            raise s.Invalid("Otimização exige início e limites para cada variável.")
        for i, f in enumerate(features):
            low, high = bounds[f]
            s.finite(low, f)
            s.finite(high, f)
            if not x[:, i].min() <= low <= high <= x[:, i].max():
                raise s.Invalid(
                    "Busca fora da faixa observada no treino não permitida."
                )
            if not low <= z[i] <= high:
                raise s.Invalid("Ponto inicial fora dos limites.")
        if opt.get("direction") not in {"maximize", "minimize"}:
            raise s.Invalid("Objetivo de busca exige maximize/minimize.")
        sign = 1 if opt["direction"] == "maximize" else -1
        for _ in range(100):
            h = np.tanh(((z - mean) / scale) @ w1 + b1)
            grad = (w1 @ ((1 - h * h) * w2)) * ys / scale
            z = z + sign * 0.01 * scale * grad / max(
                float(np.linalg.norm(grad * scale)), 1
            )
            z = np.array([np.clip(z[i], *bounds[f]) for i, f in enumerate(features)])
        predict = lambda zz: float(
            (np.tanh(((zz - mean) / scale) @ w1 + b1) @ w2 + b2) * ys + ym
        )
        candidate = {
            "before": dict(zip(features, origin.tolist())),
            "candidate": dict(zip(features, z.tolist())),
            "surrogate_before": predict(origin),
            "surrogate_candidate": predict(z),
            "interpretation": "Candidato encontrado por gradiente do substituto. Não demonstra efeito causal nem ótimo do mercado; testar em cenário independente e experimento real.",
            "eligible_for_test": mae < baseline,
        }
    return {
        "engine": "ml",
        "classification": "exploratory-supervised"
        if payload["classification"] == "observed"
        else "synthetic-software-smoke",
        "train_rows": len(train),
        "test_rows": len(test),
        "test_period_start": test[0]["date"],
        "mae_holdout": mae,
        "rmse_holdout": rmse,
        "baseline_mean_mae": baseline,
        "improves_baseline": mae < baseline,
        "training_curve": losses,
        "candidate": candidate,
        "feature_order": features,
        "parameters": {
            "mean": mean.tolist(),
            "scale": scale.tolist(),
            "target_mean": float(ym),
            "target_scale": float(ys),
            "w1": w1.tolist(),
            "b1": b1.tolist(),
            "w2": w2.tolist(),
            "b2": b2,
        },
        "test_predictions": [
            {"id": r["id"], "observed": r["target"], "predicted": float(v)}
            for r, v in zip(test, pred)
        ],
        "source_ids": payload["source_ids"],
        "limitation": "Normalização aprendida só no treino; corte temporal sem compartilhar período. Holdout único não mede toda incerteza; associação preditiva não demonstra causalidade nem probabilidade calibrada de sucesso.",
    }


def bdh(project, c):
    try:
        import torch
    except ImportError:
        raise s.Invalid(
            "BDH exige PyTorch no executor selecionado; não houve fallback para outro modelo."
        )
    source = s.inside(project, c["bdh_source"])
    if s.file_hash(source) != c.get("bdh_source_sha256"):
        raise s.Invalid("Implementação BDH diverge do hash autorizado.")
    if not c.get("bdh_license_acknowledged"):
        raise s.Invalid(
            "Confirme a licença da implementação BDH upstream antes de carregar código."
        )
    payload, features, train, test = dataset(project, c)
    labels = sorted(set(int(r["target"]) for r in train))
    if (
        len(labels) < 2
        or len(labels) > 8
        or any(
            r["target"] != int(r["target"]) or int(r["target"]) not in labels
            for r in train + test
        )
    ):
        raise s.Invalid(
            "Adapter BDH experimental exige 2–8 classes de resultado previamente definidas."
        )
    # This source is executable code, explicitly authorized and hash-bound, never a pickle checkpoint.
    spec = importlib.util.spec_from_file_location("sef_authorized_bdh", source)
    module = importlib.util.module_from_spec(spec)
    import sys, ast

    sys.modules[spec.name] = module
    compatibility = "none"
    if hasattr(torch.nn, "Buffer"):
        spec.loader.exec_module(module)
    else:
        # PyTorch <2.5 exposes register_buffer rather than nn.Buffer. Preserve the
        # official tensor expression and state_dict registration, without changing learning equations.
        class LegacyBuffer(ast.NodeTransformer):
            def visit_Assign(self, node):
                self.generic_visit(node)
                if (
                    len(node.targets) == 1
                    and isinstance(node.targets[0], ast.Attribute)
                    and node.targets[0].attr == "freqs"
                    and isinstance(node.value, ast.Call)
                    and isinstance(node.value.func, ast.Attribute)
                    and node.value.func.attr == "Buffer"
                ):
                    return ast.copy_location(
                        ast.Expr(
                            value=ast.Call(
                                func=ast.Attribute(
                                    value=ast.Name(id="self", ctx=ast.Load()),
                                    attr="register_buffer",
                                    ctx=ast.Load(),
                                ),
                                args=[ast.Constant(value="freqs"), node.value.args[0]],
                                keywords=[],
                            )
                        ),
                        node,
                    )
                return node

        tree = LegacyBuffer().visit(ast.parse(source.read_text()))
        ast.fix_missing_locations(tree)
        exec(compile(tree, str(source), "exec"), module.__dict__)
        compatibility = "nn.Buffer assignment translated to register_buffer; official tensor expression unchanged"

    torch.manual_seed(c.get("seed", 42))
    torch.set_num_threads(1)
    net = module.BDH(
        module.BDHConfig(
            n_layer=1,
            n_embd=8,
            n_head=2,
            mlp_internal_dim_multiplier=4,
            vocab_size=256,
            dropout=0.0,
        )
    )
    optimizer = torch.optim.Adam(net.parameters(), lr=0.002)
    steps = c.get("training_steps", 5)
    if not isinstance(steps, int) or not 1 <= steps <= 1000:
        raise s.Invalid("BDH experimental: 1–1.000 passos.")

    def encode(row):
        text = ";".join(f"{f}={row['features'][f]:.3g}" for f in features)
        return torch.tensor([list(text.encode()[:128])], dtype=torch.long)

    losses = []
    label_tokens = torch.tensor([240 + i for i in range(len(labels))])
    for step in range(steps):
        row = train[step % len(train)]
        optimizer.zero_grad()
        logits, _ = net(encode(row))
        choice = logits[0, -1, label_tokens]
        target = torch.tensor([labels.index(int(row["target"]))])
        loss = torch.nn.functional.cross_entropy(choice.unsqueeze(0), target)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(net.parameters(), 1.0)
        optimizer.step()
        losses.append(float(loss.detach()))
    correct = 0
    predictions = []
    net.eval()
    with torch.no_grad():
        for row in test:
            logits, _ = net(encode(row))
            scores = torch.softmax(logits[0, -1, label_tokens], dim=-1)
            choice = labels[int(scores.argmax())]
            correct += choice == int(row["target"])
            predictions.append(
                {
                    "id": row["id"],
                    "class": choice,
                    "softmax_scores": scores.tolist(),
                    "observed_class": int(row["target"]),
                }
            )
    majority = max(labels, key=lambda k: sum(int(r["target"]) == k for r in train))
    baseline = sum(int(r["target"]) == majority for r in test) / len(test)
    return {
        "engine": "bdh",
        "classification": "experimental-sequence-adaptation",
        "source_sha256": s.file_hash(source),
        "train_rows": len(train),
        "test_rows": len(test),
        "holdout_accuracy": correct / len(test),
        "baseline_majority_accuracy": baseline,
        "loss_curve": losses,
        "test_predictions": predictions,
        "backpropagation_executed": True,
        "compatibility_adapter": compatibility,
        "torch_version": torch.__version__,
        "limitation": "Implementação BDH oficial carregada por hash e treinada com backpropagation em codificação experimental de registros. Scores softmax não são probabilidades calibradas. O motor não demonstra superioridade, causalidade ou previsão de mercado; otimização numérica de variáveis pertence ao substituto ML e requer reteste independente.",
    }
