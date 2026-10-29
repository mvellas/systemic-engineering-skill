from __future__ import annotations
import contextlib, io, json, os, sys, tempfile, unittest, subprocess, csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / ".agents/skills/systemic-engineering"
sys.path.insert(0, str(SKILL / "scripts"))
import sef
from sef_runtime import (
    store as s,
    interview,
    research,
    engines,
    simulation,
    decision,
    reports,
    cli,
)


def source(i="SRC-1", group="nasa"):
    return {
        "id": i,
        "title": "NASA — Standard for Models and Simulations",
        "url": "https://standards.nasa.gov/standard/NASA/NASA-STD-7009",
        "published_at": "2024-03-05",
        "accessed_at": "2026-10-29",
        "location": "Scope",
        "evidence": "Model credibility and acceptance criteria must be assessed for the intended use.",
        "confidence": "high",
        "limitations": "Fonte metodológica; não demonstra demanda, receita ou segurança deste exemplo.",
        "independence_group": group,
        "source_type": "standard",
    }


def config(engine="monte-carlo"):
    return {
        "engine": engine,
        "seed": 17,
        "agents": 40,
        "ticks": 6,
        "trials": 100,
        "timeout_seconds": 30,
        "cost_limit": 0,
        "success": {"metric": "cash", "threshold": 0},
        "scenarios": [
            {
                "id": "A",
                "price": 20,
                "variable_cost": 10,
                "fixed_cost": 100,
                "initial_cash": 200,
                "market_size": 100,
                "conversion": 0.03,
                "churn": 0.1,
                "capacity": 100,
                "initial_customers": 0,
                "acquisition_spend": 20,
                "uncertainty": 0.01,
                "unit": "unidade por cliente por período",
                "currency": "BRL",
                "period": "mês",
                "source_ids": ["SRC-1"],
            }
        ],
        "sensitivity": [{"parameter": "price", "values": [15, 20, 25]}],
    }


class ConsultingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.project = Path(self.temp.name) / "project"
        with contextlib.redirect_stdout(io.StringIO()):
            sef.command_init(
                __import__("argparse").Namespace(
                    project=str(self.project),
                    name="Exemplo <script>alert(1)</script>",
                    mode="fixture",
                )
            )
        self.control = self.project / ".systemic-engineering"
        self.control.joinpath("00-intake/authorities.csv").write_text(
            "authority_id,name,role,scope,evidence,status\nAUTH-U,Fixture Human,user,all,/fixture,active\n"
        )
        s.enable(self.project)
        state = sef.read_state(self.project)
        sef.write_state(self.project, {**state, "risk_class": "low"})
        research.add_source(self.project, source())

    def tearDown(self):
        self.temp.cleanup()

    def grants(self, c):
        a = dict(
            by="Fixture Human",
            authority_id="AUTH-U",
            evidence="fixture-statement",
            attestation="Somente smoke local demonstrativo; não autoriza projeto real.",
            fixture=True,
        )
        s.authorize(self.project, c, "method", **a)
        return s.authorize(self.project, c, "execution", **a)["grant_id"]

    def patch(self, data):
        cli.validate_patch(self.project, data)
        with s.lock(self.project):
            return s.save(
                self.project, {**s.model(self.project), **data}, "test-import"
            )

    def test_legacy_phase_does_not_advance_with_consulting_commands(self):
        interview.next_round(self.project)
        reports.render(self.project)
        self.assertEqual(s.read(self.control / "state.json")["phase"], "intake")
        self.assertEqual(s.read(self.control / "state.json")["approvals"], [])

    def test_round_reused_until_answered_and_ambiguous_answers_followed_up(self):
        r = interview.next_round(self.project)
        self.assertEqual(r, interview.next_round(self.project))
        interview.answer(
            self.project,
            {
                "round_id": r["id"],
                "speaker": "Patrocinador",
                "answers": [
                    {
                        "question_id": q["id"],
                        "kind": "hipotese",
                        "text": "Quero algo melhor",
                    }
                    for q in r["questions"]
                ],
            },
        )
        next_round = interview.next_round(self.project)
        self.assertTrue(all(q.get("parent_answer") for q in next_round["questions"]))
        self.assertTrue((s.root(self.project) / "interview-trace.csv").is_file())
        self.assertEqual(len(s.model(self.project)["rounds"]), 2)

    def test_answer_not_fact_without_registered_source_and_round_not_consumed(self):
        r = interview.next_round(self.project)
        with self.assertRaises(s.Invalid):
            interview.answer(
                self.project,
                {
                    "round_id": r["id"],
                    "answers": [
                        {"question_id": q["id"], "kind": "fato", "text": "x"}
                        for q in r["questions"]
                    ],
                },
            )
        self.assertFalse(s.model(self.project)["rounds"][-1]["answered"])

    def test_cannot_interview_vft_before_gate(self):
        with self.assertRaises(s.Invalid):
            interview.phase(self.project, "vft")

    def test_external_source_rejects_self_authored_and_bad_url(self):
        for patch in [
            {"self_authored": True},
            {"url": "javascript:alert(1)"},
            {"url": "https://user:password@example.org"},
            {"location": ""},
        ]:
            with self.subTest(patch=patch), self.assertRaises(s.Invalid):
                research.add_source(self.project, {**source("SRC-2"), **patch})

    def test_claim_needs_external_registered_evidence(self):
        with self.assertRaises(s.Invalid):
            research.add_claim(
                self.project,
                {
                    "id": "CL-1",
                    "kind": "observed",
                    "text": "Demanda existe",
                    "source_ids": ["SRC-X"],
                    "limitations": "desconhecido",
                },
            )

    def test_triangulation_does_not_count_same_source_group_twice(self):
        research.add_source(self.project, source("SRC-2"))
        research.add_claim(
            self.project,
            {
                "id": "CL-1",
                "kind": "inference",
                "text": "Revisar validade do modelo",
                "source_ids": ["SRC-1", "SRC-2"],
                "limitations": "sem observação de mercado",
            },
        )
        self.assertTrue(
            any(
                "fonte única" in x
                for x in research.audit(self.project, "2026-10-29")["issues"]
            )
        )

    def test_canonical_tamper_detected_and_gate_hard_blocked(self):
        m = s.model(self.project)
        s.atomic(
            s.root(self.project) / "model.json", {**m, "problem": "alteração por fora"}
        )
        with self.assertRaises(s.Invalid):
            s.integrity(self.project)
        gate = sef.assess_gate(self.project, sef.read_state(self.project), "intake")
        self.assertTrue(any("consulting-integrity" in x for x in gate["errors"]))

    def test_hashes_invalidate_existing_approval_on_changed_consultation(self):
        old = sef.artifact_hashes(self.project, "intake")
        self.patch({"problem": "Problema diferente e verificável"})
        self.assertNotEqual(old, sef.artifact_hashes(self.project, "intake"))

    def test_method_approval_is_not_execution_permission(self):
        c = config()
        s.authorize(
            self.project,
            c,
            "method",
            "Fixture Human",
            "AUTH-U",
            "fixture",
            "Declaração humana para teste isolado",
            True,
        )
        with self.assertRaises(s.Invalid):
            simulation.run(self.project, c, "missing")

    def test_scope_and_use_once_and_changed_configuration(self):
        c = config()
        grant = self.grants(c)
        with self.assertRaises(s.Invalid):
            s.consume(self.project, {**c, "seed": 18}, grant)
        with s.lock(self.project):
            s.consume(self.project, c, grant)
        with self.assertRaises(s.Invalid):
            s.consume(self.project, c, grant)

    def test_file_change_invalidates_grant(self):
        file = self.project / "profiles.json"
        s.atomic(file, [])
        c = {**config(), "profile_path": "profiles.json"}
        grant = self.grants(c)
        s.atomic(file, [{}])
        with self.assertRaises(s.Invalid):
            s.consume(self.project, c, grant)

    def test_fixture_never_calls_external_service(self):
        c = {**config(), "engine": "oasis", "external": True}
        grant = self.grants(c)
        with self.assertRaises(s.Invalid):
            s.consume(self.project, c, grant)

    def test_core_monte_carlo_reproducible_and_cash_reconciles(self):
        one = engines.business(config())
        two = engines.business(config())
        self.assertEqual(one, two)
        self.assertLess(one["reconciliation_max_error"], 1e-9)
        self.assertTrue(0 <= one["summary"][0]["conditional_success_fraction"] <= 1)

    def test_sensitivity_changes_price_and_cash_in_same_model(self):
        r = engines.business(config())
        v = [x["cash"] for x in r["sensitivity"]]
        self.assertLess(v[0], v[-1])

    def test_abm_stores_actual_state_and_interaction_sample(self):
        r = engines.business({**config("agents"), "interaction_strength": 0.1})
        self.assertEqual(len(r["timeseries"][0]["agent_states"]), 40)
        self.assertEqual(len(r["timeseries"][0]["agent_edges"]), 80)

    def test_failure_propagation_lag_and_recovery(self):
        c = {
            "engine": "failure",
            "ticks": 2,
            "trials": 1,
            "seed": 1,
            "nodes": [
                {"id": "A", "failure_probability": 1, "recovery_probability": 0},
                {"id": "B", "failure_probability": 0, "recovery_probability": 0},
            ],
            "edges": [{"from": "A", "to": "B", "probability": 1}],
        }
        r = engines.failure(c)
        self.assertEqual(r["timeseries"][0]["failed"], ["A"])
        self.assertEqual(set(r["timeseries"][1]["failed"]), {"A", "B"})

    def test_mcmc_checked_against_analytical_posterior(self):
        c = {
            "engine": "mcmc",
            "trials": 6000,
            "warmup": 1000,
            "chains": 4,
            "seed": 44,
            "observations": {"successes": 20, "trials": 100, "source_ids": ["SRC-1"]},
        }
        r = engines.mcmc(c)
        self.assertAlmostEqual(r["posterior"]["mean"], 21 / 102, delta=0.02)
        self.assertIsNotNone(r["diagnostics"]["split_rhat"])

    def test_preflight_refuses_unbounded_work_and_nonfinite_values(self):
        with self.assertRaises(s.Invalid):
            simulation.preflight(
                self.project, {**config("agents"), "agents": 1000000, "ticks": 100}
            )
        with self.assertRaises(s.Invalid):
            engines.validate_config({**config(), "cost_limit": float("nan")})

    def test_run_grant_records_result_and_refreshes_both_human_outputs(self):
        c = config()
        manifest = simulation.run(self.project, c, self.grants(c))
        self.assertEqual(manifest["status"], "completed")
        p = s.read(s.root(self.project) / "latest-export.json")
        folder = s.root(self.project) / p["path"]
        self.assertTrue((folder / "RELATORIO.html").is_file())
        self.assertTrue((folder / "DASHBOARD.html").is_file())
        self.assertTrue(s.read(folder / "QUALITY.json")["issues"])
        self.assertEqual(
            s.model(self.project)["runs"][0]["interpretation_status"], "pending"
        )

    def test_report_escapes_html_and_has_22_documents_and_sources(self):
        self.patch({"problem": "<script>alert(2)</script>"})
        r = reports.render(self.project)
        body = Path(r["report"]).read_text()
        self.assertNotIn("<script>alert(2)</script>", body)
        self.assertIn("&lt;script&gt;", body)
        self.assertEqual(body.count('class="artifact"'), 22)
        self.assertIn("https://standards.nasa.gov/", body)
        self.assertIn('data-panel="map-panel"', body)

    def test_empty_report_cannot_be_client_ready(self):
        q = reports.quality(self.project)
        self.assertFalse(q["client_ready"])
        self.assertGreater(len(q["issues"]), 22)

    def test_research_private_targets_block_before_connect(self):
        from unittest.mock import patch

        with (
            patch(
                "socket.getaddrinfo", return_value=[(2, 1, 6, "", ("127.0.0.1", 80))]
            ),
            patch("socket.create_connection") as connect,
        ):
            with self.assertRaises(s.Invalid):
                research.fetch_public("https://example.com")
            connect.assert_not_called()

    def test_secrets_are_rejected_before_persistence(self):
        p = self.project / "input.json"
        s.atomic(p, {"api_key": "do-not-record"})
        with self.assertRaises(s.Invalid):
            cli.input_config(__import__("argparse").Namespace(config=str(p)))

    def test_mcda_veto_cannot_be_compensated(self):
        criteria = [
            {
                "id": "C1",
                "weight": 0.5,
                "min": 0,
                "max": 10,
                "direction": "max",
                "judgment_by": "Fixture Human",
                "weight_reason": "Exemplo de preferência declarada",
                "veto_below": 5,
            },
            {
                "id": "C2",
                "weight": 0.5,
                "min": 0,
                "max": 10,
                "direction": "max",
                "judgment_by": "Fixture Human",
                "weight_reason": "Exemplo de preferência declarada",
            },
        ]
        score = lambda n: {
            "value": n,
            "source_ids": ["SRC-1"],
            "explanation": "Hipótese de avaliação no exemplo, não medição real.",
        }
        self.patch(
            {
                "criteria": criteria,
                "alternatives": [
                    {
                        "id": "A",
                        "title": "Barata, mas viola limite",
                        "scores": {"C1": score(4), "C2": score(10)},
                    },
                    {
                        "id": "B",
                        "title": "Atende limite",
                        "scores": {"C1": score(6), "C2": score(2)},
                    },
                ],
            }
        )
        r = decision.compare(self.project)
        self.assertEqual(r["advisory_candidate"], "B")
        self.assertEqual(r["excluded"][0]["alternative"], "A")
        self.assertEqual(r["human_decision"], "pending")

    def test_path_traversal_rejected(self):
        with self.assertRaises(s.Invalid):
            s.inside(self.project, "../outside")

    def test_bundle_does_not_include_secret_or_claim_execution(self):
        c = config()
        p = self.project / "config.json"
        s.atomic(p, c)
        (self.project / ".env").write_text("SECRET=not-exportable")
        out = cli.bundle(self.project, p, Path(self.temp.name) / "executor.zip")
        self.assertFalse(out["executed"])
        import zipfile

        with zipfile.ZipFile(out["bundle"]) as z:
            self.assertFalse(any(".env" in name for name in z.namelist()))
            self.assertIn("EXECUTOR.txt", z.namelist())

    def test_authority_registry_change_invalidates_grant(self):
        c = config()
        grant = self.grants(c)
        path = self.control / "00-intake/authorities.csv"
        path.write_text(path.read_text().replace("active", "inactive"))
        with self.assertRaises(s.Invalid):
            s.consume(self.project, c, grant)

    def test_unset_risk_cannot_authorize_experiment(self):
        state = sef.read_state(self.project)
        sef.write_state(self.project, {**state, "risk_class": "unset"})
        with self.assertRaises(s.Invalid):
            self.grants(config())

    def test_incomplete_deliverables_cannot_receive_human_approval(self):
        with self.assertRaises(s.Invalid):
            reports.review(
                self.project,
                "Fixture Human",
                "AUTH-U",
                "fixture-only",
                "Revisão explícita dos produtos desta fixture",
                "approved",
            )
        reports.review(
            self.project,
            "Fixture Human",
            "AUTH-U",
            "fixture-only",
            "Rejeitar os produtos por lacunas analíticas",
            "rejected",
        )
        self.assertFalse(reports.quality(self.project)["client_ready"])

    def test_early_stop_is_not_success_at_full_horizon(self):
        c = {**config(), "stop_cash_below": 100000}
        r = engines.business(c)
        self.assertEqual(r["summary"][0]["conditional_success_fraction"], 0)
        self.assertEqual(r["summary"][0]["early_stopped_replicas"], 100)

    def test_mixed_currency_scenarios_are_rejected(self):
        c = config()
        other = {**c["scenarios"][0], "id": "USD-scenario", "currency": "USD"}
        with self.assertRaises(s.Invalid):
            engines.validate_config({**c, "scenarios": [*c["scenarios"], other]})

    def test_export_failure_does_not_erase_completed_simulation(self):
        from unittest.mock import patch

        c = config()
        grant = self.grants(c)
        with patch(
            "sef_runtime.reports.render",
            side_effect=RuntimeError("presentation failed"),
        ):
            r = simulation.run(self.project, c, grant)
        self.assertEqual(r["status"], "completed")
        self.assertEqual(r["export_status"], "failed")
        self.assertEqual(s.model(self.project)["runs"][0]["status"], "completed")

    def test_supervised_gradient_uses_holdout_and_proposes_only_within_training_bounds(
        self,
    ):
        import importlib.util

        if not importlib.util.find_spec("numpy"):
            self.skipTest("optional numpy unavailable")
        from sef_runtime import predictive
        from datetime import date, timedelta

        rows = [
            {
                "id": str(i),
                "date": str(date(2025, 1, 1) + timedelta(days=i)),
                "features": {"price": float(i % 10), "effort": float((i * 7) % 11)},
                "target": float(100 + 3 * (i % 10) - 2 * ((i * 7) % 11)),
            }
            for i in range(60)
        ]
        s.atomic(
            self.project / "dataset.json",
            {"classification": "synthetic", "source_ids": ["SRC-1"], "rows": rows},
        )
        c = {
            "engine": "ml",
            "dataset": "dataset.json",
            "features": ["price", "effort"],
            "seed": 1,
            "training_steps": 500,
            "optimize": {
                "direction": "maximize",
                "start": {"price": 5, "effort": 5},
                "bounds": {"price": [0, 9], "effort": [0, 10]},
            },
        }
        r = predictive.ml(self.project, c)
        self.assertLess(r["mae_holdout"], r["baseline_mean_mae"])
        self.assertEqual(r["classification"], "synthetic-software-smoke")
        for f, v in r["candidate"]["candidate"].items():
            self.assertTrue(
                c["optimize"]["bounds"][f][0] <= v <= c["optimize"]["bounds"][f][1]
            )
        rows[1]["id"] = rows[0]["id"]
        s.atomic(
            self.project / "dataset.json",
            {"classification": "synthetic", "source_ids": ["SRC-1"], "rows": rows},
        )
        with self.assertRaises(s.Invalid):
            predictive.dataset(self.project, c)

    def test_regional_stocks_reconcile_and_only_declared_regions_exist(self):
        c = config("dynamics")
        a = c["scenarios"][0]
        a = {
            **a,
            "regions": [
                {
                    "id": "A",
                    "market_size": 40,
                    "initial_customers": 0,
                    "conversion": 0.01,
                    "source_ids": ["SRC-1"],
                },
                {
                    "id": "B",
                    "market_size": 60,
                    "initial_customers": 0,
                    "conversion": 0.05,
                    "source_ids": ["SRC-1"],
                },
            ],
        }
        c = {**c, "scenarios": [a]}
        engines.validate_config(c)
        r = engines.business(c)
        for row in r["timeseries"]:
            self.assertAlmostEqual(
                sum(x["value"] for x in row["regional_customers"]), row["customers"]
            )
        self.assertEqual({x["region"] for x in r["regional_timeseries"]}, {"A", "B"})
        self.assertTrue(
            all(x["classification"] == "simulated" for x in r["regional_timeseries"])
        )
        a["regions"][0]["market_size"] = 41
        with self.assertRaises(s.Invalid):
            engines.validate_config(c)

    def test_applied_visual_validates_links_and_escapes_labels(self):
        from sef_runtime import visuals

        v = {
            "type": "flow",
            "title": "Fluxo proposto",
            "source_ids": ["SRC-1"],
            "classification": "Hipótese",
            "caption": "Não representa observação de clientes.",
            "nodes": [
                {"id": "A", "label": "<script>alert(1)</script>"},
                {"id": "B", "label": "Revisar"},
            ],
            "edges": [{"from": "A", "to": "B"}],
        }
        visuals.validate(v, {"SRC-1"})
        svg = visuals.render(v)
        self.assertNotIn("<script>", svg)
        self.assertIn("&lt;script&gt;", svg)
        v["edges"][0]["to"] = "missing"
        with self.assertRaises(s.Invalid):
            visuals.validate(v, {"SRC-1"})


if __name__ == "__main__":
    unittest.main()
