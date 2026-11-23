"""Reported tariffs are scenario-derived evidence, never an unchecked client input."""
from math import inf, nan
import unittest

from engine.scenario import scenario
from engine.verification import verify_plan


NUMERIC_FIELDS = (
    "grid_kw", "solar_used_kw", "charge_kw", "discharge_kw", "base_kw",
    "flexible_kw", "noncritical_shed_kw", "soc_kwh", "grid_limit_kw",
    "solar_available_kw",
)


def sample_plan(data):
    return {
        "jobs": [],
        "metrics": {},
        "slots": [
            {"time": time, "tariff": data["tariff_inr_per_kwh"][i],
             **{field: 0.0 for field in NUMERIC_FIELDS}}
            for i, time in enumerate(data["hours"])
        ],
    }


class TariffIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.data = scenario()

    def test_forged_numeric_tariff_is_detected(self):
        for difference in (-1.0, 0.05, 1.0):
            with self.subTest(difference=difference):
                candidate = sample_plan(self.data)
                candidate["slots"][2]["tariff"] += difference
                outcome = verify_plan(self.data, candidate)
                self.assertFalse(outcome["passed"])
                self.assertTrue(any("Tariff telemetry mismatch" in v
                                    for v in outcome["violations"]), outcome["violations"])

    def test_missing_and_invalid_tariffs_are_rejected_before_arithmetic(self):
        for value in (True, False, "7", None, nan, inf, -inf, [], {}):
            with self.subTest(tariff=repr(value)):
                candidate = sample_plan(self.data)
                candidate["slots"][3]["tariff"] = value
                outcome = verify_plan(self.data, candidate)
                self.assertFalse(outcome["passed"])
                self.assertEqual(outcome["checks_performed"], 0)
                self.assertEqual(outcome["violations"],
                                 ["Malformed dispatch plan (ValueError)"])
        candidate = sample_plan(self.data)
        del candidate["slots"][3]["tariff"]
        self.assertEqual(verify_plan(self.data, candidate)["checks_performed"], 0)


if __name__ == "__main__":
    unittest.main()
