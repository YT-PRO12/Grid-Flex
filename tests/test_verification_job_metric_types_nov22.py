"""Untrusted numeric metadata cannot be accepted through Python truthy coercions."""
from math import inf, nan
import unittest

from engine.scenario import scenario
from engine.verification import verify_plan


FIELDS = (
    "grid_kw", "solar_used_kw", "charge_kw", "discharge_kw", "base_kw",
    "flexible_kw", "noncritical_shed_kw", "soc_kwh", "grid_limit_kw",
    "solar_available_kw",
)


def plan():
    return {
        "slots": [{field: 0.0 for field in FIELDS} for _ in range(12)],
        "jobs": [{"id": "J1", "start": 0, "end": 3, "power_kw": 29.0}],
        "metrics": {"energy_cost_inr": 0.0},
        "carbon_weight_inr_per_kg": 0.0,
    }


class JobAndMetricBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.data = scenario()

    def assert_fail_closed(self, candidate):
        report = verify_plan(self.data, candidate)
        self.assertIs(report["passed"], False)
        self.assertEqual(report["checks_performed"], 0)
        self.assertEqual(report["violations"], ["Malformed dispatch plan (ValueError)"])

    def test_start_end_only_accept_real_integers(self):
        for field in ("start", "end"):
            for value in (True, False, 1.5, "1", None):
                with self.subTest(field=field, value=repr(value)):
                    candidate = plan()
                    candidate["jobs"][0][field] = value
                    self.assert_fail_closed(candidate)

    def test_job_power_and_metric_values_are_finite_numbers(self):
        for value in (True, False, "29", nan, inf, -inf):
            with self.subTest(value=repr(value)):
                candidate = plan()
                candidate["jobs"][0]["power_kw"] = value
                self.assert_fail_closed(candidate)
                candidate = plan()
                candidate["metrics"]["energy_cost_inr"] = value
                self.assert_fail_closed(candidate)
                candidate = plan()
                candidate["carbon_weight_inr_per_kg"] = value
                self.assert_fail_closed(candidate)


if __name__ == "__main__":
    unittest.main()
