from __future__ import annotations
import contextlib
import copy
import io
import json
import random
import subprocess
import sys
import unittest
from pathlib import Path
import test_consulting as tc
from test_consulting import config, source
from sef_runtime import campaigns, engines, finance, simulation, store as s, research


def financial_config():
    c = config("dynamics")
    c.update(ticks=2, trials=2, sensitivity=[])
    a = c["scenarios"][0]
    a.update(
        price=10,
        variable_cost=2,
        fixed_cost=10,
        initial_cash=100,
        market_size=10,
        initial_customers=10,
        capacity=10,
        acquisition_spend=0,
        conversion=0,
        churn=0,
    )
    a["finance"] = {
        "initial_investment": 50,
        "discount_rate_per_period": 0,
        "revenue_tax_rate": 0.1,
        "collection_lag": 1,
        "operating_payment_lag": 0,
        "capex": [],
        "source_ids": ["SRC-1"],
        "limitations": "Hipótese sintética; não aplica legislação fiscal.",
    }
    return c


class FinanceTests(unittest.TestCase):
    def test_receipts_profit_cash_and_npv_are_distinct(self):
        c = financial_config()
        engines.validate_config(c)
        result = engines.business(c)
        rows = result["timeseries"]
        f = result["summary"][0]["financial"]
        self.assertEqual([r["cash"] for r in rows], [10, 70])
        self.assertEqual([r["profit"] for r in rows], [60, 60])
        self.assertEqual(rows[-1]["accounts_receivable"], 100)
        self.assertEqual(f["net_present_value"]["median"], -30)
        self.assertEqual(f["payback_reached_fraction"], 0)
        self.assertLess(result["reconciliation_max_error"], 1e-9)

    def test_capex_discount_and_funding_gap(self):
        c = financial_config()
        a = c["scenarios"][0]
        a["initial_cash"] = 40
        a["finance"].update(
            capex=[{"tick": 2, "amount": 20}], discount_rate_per_period=0.1
        )
        r = engines.business(c)["summary"][0]["financial"]
        self.assertAlmostEqual(
            r["net_present_value"]["median"], -50 - 40 / 1.1 + 40 / 1.1**2
        )
        self.assertEqual(r["additional_funding_required"]["median"], 50)

    def test_invalid_finance_rejected(self):
        for k, v in [
            ("collection_lag", True),
            ("revenue_tax_rate", 2),
            ("discount_rate_per_period", -1),
            ("source_ids", []),
        ]:
            c = financial_config()
            c["scenarios"][0]["finance"][k] = v
            with self.subTest(k=k), self.assertRaises(s.Invalid):
                engines.validate_config(c)

    def test_explicit_price_response(self):
        c = config("dynamics")
        c.update(ticks=1, sensitivity=[])
        a = c["scenarios"][0]
        a.update(price=20, conversion=0.1, initial_customers=0)
        a["price_response"] = {
            "reference_price": 10,
            "elasticity": -1,
            "source_ids": ["SRC-1"],
            "classification": "hypothesis",
        }
        engines.validate_config(c)
        self.assertAlmostEqual(engines.business(c)["timeseries"][0]["customers"], 5)


class CampaignTests(unittest.TestCase):
    setUp = tc.ConsultingTests.setUp
    tearDown = tc.ConsultingTests.tearDown

    def spec(self):
        c = config("agents")
        c.update(trials=2, ticks=2, agents=8, sensitivity=[])
        return {
            "base_config": c,
            "replicas_per_case": 2,
            "factors": [
                {
                    "parameter": "scenario.price",
                    "values": [15, 25],
                    "source_ids": ["SRC-1"],
                    "classification": "hypothesis",
                    "rationale": "Teste sintético",
                    "role": "decision",
                }
            ],
        }

    def test_pending_campaign_has_no_candidate_or_grant(self):
        r = campaigns.register(self.project, self.spec())
        cid = r["id"]
        self.assertFalse(r["execution_authorized"])
        self.assertEqual(campaigns.status(self.project, cid)["completed_cases"], 0)
        self.assertEqual(
            campaigns.next_case(self.project, cid)["status"],
            "awaiting-specific-authorization",
        )
        a = campaigns.analyze(self.project, cid)
        self.assertFalse(a["complete"])
        self.assertIsNone(a["candidate"])

    def test_mixed_financial_scenarios_export_without_erasing_results(self):
        c = financial_config()
        plain = copy.deepcopy(c["scenarios"][0])
        plain.pop("finance")
        plain["id"] = "PLAIN"
        c["scenarios"].insert(0, plain)
        grant = tc.ConsultingTests.grants(self, c)
        result = simulation.run(self.project, c, grant)
        self.assertEqual(result["status"], "completed")
        folder = s.root(self.project) / "runs" / result["id"]
        import csv

        rows = list(csv.DictReader((folder / "timeseries.csv").open()))
        self.assertEqual(rows[0]["accounts_receivable"], "")
        self.assertEqual(float(rows[-1]["accounts_receivable"]), 100)

    def test_unknown_source_creates_no_campaign(self):
        d = self.spec()
        d["factors"][0]["source_ids"] = ["SRC-MISSING"]
        with self.assertRaises(s.Invalid):
            campaigns.register(self.project, d)
        self.assertFalse(s.model(self.project).get("campaigns"))

    def test_real_local_fixture_flow_and_tamper_detection(self):
        cid = campaigns.register(self.project, self.spec())["id"]
        for _ in range(2):
            c = campaigns.next_case(self.project, cid)["case"]["config"]
            # Explicit fixture authorizations are bounded demonstration permissions only.
            s.authorize(
                self.project,
                c,
                "method",
                "Fixture Human",
                "AUTH-U",
                "fixture-method",
                "Teste explícito, sem aprovação real.",
                True,
            )
            g = s.authorize(
                self.project,
                c,
                "execution",
                "Fixture Human",
                "AUTH-U",
                "fixture-run",
                "Teste local explícito, sem aprovação real.",
                True,
            )
            simulation.run(self.project, c, g["grant_id"])
        a = campaigns.analyze(self.project, cid)
        self.assertTrue(a["complete"])
        self.assertEqual(len(a["ranking"]), 2)
        self.assertEqual(len(a["interpretations_pending"]), 2)
        run = s.model(self.project)["runs"][0]
        p = s.root(self.project) / "runs" / run["id"] / "result.json"
        d = s.read(p)
        d["summary"][0]["final_cash"]["median"] = 1e9
        s.atomic(p, d)
        with self.assertRaises(s.Invalid):
            campaigns.status(self.project, cid)
