"""The verification boundary must reject JSON-compatible booleans and nonfinite values."""
from copy import deepcopy
from math import inf, nan
import unittest

from engine.scenario import scenario
from engine.verification import verify_plan


FIELDS = (
    "grid_kw", "solar_used_kw", "charge_kw", "discharge_kw", "base_kw",
    "flexible_kw", "noncritical_shed_kw", "soc_kwh", "grid_limit_kw",
    "solar_available_kw",
)


def skeleton():
    slots = [{field: 0.0 for field in FIELDS} for _ in range(12)]
    return {"slots": slots, "jobs": [], "metrics": {}}


class DispatchTypeBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.data = scenario()

    def assert_rejected_early(self, plan):
        outcome = verify_plan(self.data, plan)
        self.assertFalse(outcome["passed"])
        self.assertEqual(outcome["checks_performed"], 0)
        self.assertEqual(outcome["violations"], ["Malformed dispatch plan (ValueError)"])
        self.assertIsNone(outcome["summary"]["critical_load_preserved"])

    def test_each_hourly_numeric_field_rejects_coercible_boolean(self):
        for field in FIELDS:
            with self.subTest(field=field):
                plan = skeleton()
                plan["slots"][0][field] = True
                self.assert_rejected_early(plan)

    def test_nonfinite_and_missing_hourly_numbers_are_rejected(self):
        for field in FIELDS:
            for value in (nan, inf, -inf, "0"):
                with self.subTest(field=field, value=str(value)):
                    plan = skeleton()
                    plan["slots"][3][field] = value
                    self.assert_rejected_early(plan)
            with self.subTest(field=field, value="missing"):
                plan = skeleton()
                del plan["slots"][3][field]
                self.assert_rejected_early(plan)

    def test_payload_is_not_modified_by_rejection(self):
        plan = skeleton()
        plan["slots"][4]["grid_kw"] = True
        original = deepcopy(plan)
        self.assert_rejected_early(plan)
        self.assertEqual(plan, original)


if __name__ == "__main__":
    unittest.main()
