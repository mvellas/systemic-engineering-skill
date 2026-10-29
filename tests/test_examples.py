"""Executable acceptance examples: real CLI/state transitions, explicitly synthetic approvals."""

import json, subprocess, sys, tempfile, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class ExampleAcceptanceTests(unittest.TestCase):
    def exercise(self, kind):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / kind
            p = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "examples/run_example.py"),
                    "--kind",
                    kind,
                    "--output",
                    str(target),
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                timeout=90,
            )
            self.assertEqual(p.returncode, 0, p.stderr[-4000:])
            data = json.loads(p.stdout)
            self.assertFalse(data["real_approval"])
            self.assertFalse(data["outputs"]["quality"]["client_ready"])
            control = target / ".systemic-engineering"
            state = json.loads((control / "state.json").read_text())
            self.assertEqual(state["mode"], "fixture")
            self.assertTrue(all(x.get("fixture") for x in state["approvals"]))
            report = Path(data["outputs"]["report"])
            dashboard = Path(data["outputs"]["dashboard"])
            self.assertTrue(report.is_file())
            self.assertTrue(dashboard.is_file())
            self.assertEqual(len(list((report.parent / "documentos").glob("*.md"))), 22)
            self.assertIn("Exemplo sintético", report.read_text())
            self.assertEqual(
                len(
                    json.loads((report.parent / "study.json").read_text())["model"][
                        "sources"
                    ]
                ),
                4 if kind == "business" else 3,
            )
            if kind == "critical":
                self.assertEqual(state["phase"], "stpa")
                self.assertTrue(data["phase_result"]["blocked_as_designed"])
                self.assertFalse(list((control / "08-consulting/runs").glob("RUN-*")))
                self.assertTrue(
                    any(
                        "missing-role:domain-expert" in x
                        for x in data["phase_result"]["gate"]["hard_blockers"]
                    )
                )
            else:
                self.assertEqual(state["phase"], "closure")
                self.assertFalse(data["phase_result"]["blocked_as_designed"])
                runs = list(
                    (control / "08-consulting/runs").glob("RUN-*/manifest.json")
                )
                self.assertEqual(len(runs), 2)
                self.assertTrue(
                    all(
                        json.loads(p.read_text())["status"] == "completed" for p in runs
                    )
                )
                self.assertTrue(any("advance" in x["kind"] for x in state["history"]))
                if kind == "business":
                    results = [
                        json.loads((p.parent / "result.json").read_text()) for p in runs
                    ]
                    regional = next(r for r in results if r["engine"] == "monte-carlo")
                    self.assertTrue(regional["regional_timeseries"])
                    self.assertEqual(
                        {x["region"] for x in regional["regional_timeseries"]},
                        {"35", "53"},
                    )

    def test_business_through_closure_with_regional_hypotheses(self):
        self.exercise("business")

    def test_software_through_closure_with_synthetic_approvals(self):
        self.exercise("software")

    def test_critical_stops_before_unqualified_safety_approval(self):
        self.exercise("critical")


if __name__ == "__main__":
    unittest.main()
