"""Experimental planning and actual network rule contracts; no market runs."""

import copy
import random
import unittest
from test_consulting import config
from sef_runtime import engines, experiments, store as s


def design():
    return {
        "base_config": config("agents"),
        "replicas_per_case": 50,
        "factors": [
            {
                "parameter": "scenario.price",
                "values": [15, 25],
                "source_ids": ["SRC-PRICE"],
                "classification": "hypothesis",
                "rationale": "Faixa ilustrativa; não observada no mercado.",
            },
            {
                "parameter": "config.network_topology",
                "values": ["ring", "random"],
                "source_ids": ["SRC-NET"],
                "classification": "hypothesis",
                "rationale": "Estruturas alternativas, não redes observadas.",
            },
        ],
    }


class ExperimentTests(unittest.TestCase):
    def test_factorial_reproducible_without_authorization_or_mutation(self):
        d = design()
        old = copy.deepcopy(d)
        p = experiments.plan(d)
        self.assertEqual(d, old)
        self.assertEqual(p, experiments.plan(d))
        self.assertEqual(p["case_count"], 4)
        self.assertEqual(p["trajectory_count"], 200)
        self.assertFalse(p["execution_authorized"])
        self.assertEqual(len({x["config_hash"] for x in p["cases"]}), 4)
        self.assertIn(
            "SRC-PRICE", p["cases"][0]["config"]["scenarios"][0]["source_ids"]
        )

    def test_invalid_designs_rejected(self):
        for change in (
            "duplicate",
            "source",
            "bounds",
            "replicas",
            "budget",
            "topology",
        ):
            d = design()
            if change == "duplicate":
                d["factors"].append(copy.deepcopy(d["factors"][0]))
            if change == "source":
                d["factors"][0]["source_ids"] = "invented"
            if change == "bounds":
                d["factors"][0]["parameter"] = "scenario.conversion"
                d["factors"][0]["values"] = [2]
            if change == "replicas":
                d["replicas_per_case"] = True
            if change == "budget":
                d["replicas_per_case"] = 100000
            if change == "topology":
                d["factors"][1]["values"] = ["invented"]
            with self.subTest(change=change), self.assertRaises(s.Invalid):
                experiments.plan(d)

    def test_ring_edges_are_the_contacts_used(self):
        c = config("agents")
        c.update(network_topology="ring", agents=8, ticks=1)
        row = engines.trajectory(c["scenarios"][0], c, random.Random(17), "agents")[0]
        edges = {(e["from"], e["to"]) for e in row["agent_edges"]}
        self.assertEqual(edges, {((i + d) % 8, i) for i in range(8) for d in (-1, 1)})
        self.assertAlmostEqual(
            row["opening_cash"] + row["inflows"] - row["outflows"], row["cash"]
        )

    def test_more_replicas_only_change_numerical_precision(self):
        d = design()
        a = experiments.plan(d)
        d["replicas_per_case"] = 200
        b = experiments.plan(d)
        self.assertAlmostEqual(
            a["precision_note"]["worst_case_success_fraction_standard_error"],
            2 * b["precision_note"]["worst_case_success_fraction_standard_error"],
        )
