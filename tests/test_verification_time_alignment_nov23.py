"""Hourly dispatch output must align exactly with the trusted synthetic scenario."""
from copy import deepcopy
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
            {"time": hour, "tariff": data["tariff_inr_per_kwh"][i],
             **{field: 0.0 for field in NUMERIC_FIELDS}}
            for i, hour in enumerate(data["hours"])
        ],
    }


class TimeAlignmentTests(unittest.TestCase):
    def setUp(self):
        self.data = scenario()

    def assert_has_timestamp_violation(self, plan):
        result = verify_plan(self.data, plan)
        self.assertFalse(result["passed"])
        self.assertTrue(any("Slot timestamp mismatch" in value
                            for value in result["violations"]), result["violations"])
        self.assertIsNone(result["summary"]["critical_load_preserved"])

    def test_reordered_time_labels_are_rejected(self):
        candidate = sample_plan(self.data)
        candidate["slots"][0]["time"], candidate["slots"][1]["time"] = (
            candidate["slots"][1]["time"], candidate["slots"][0]["time"]
        )
        self.assert_has_timestamp_violation(candidate)

    def test_missing_and_duplicate_timestamp_are_rejected(self):
        for replacement in (None, "", self.data["hours"][0], "20:00", 8):
            with self.subTest(replacement=replacement):
                candidate = sample_plan(self.data)
                candidate["slots"][4]["time"] = replacement
                self.assert_has_timestamp_violation(candidate)
        candidate = sample_plan(self.data)
        del candidate["slots"][4]["time"]
        self.assert_has_timestamp_violation(candidate)

    def test_failed_audit_does_not_mutate_original_plan(self):
        candidate = sample_plan(self.data)
        candidate["slots"][3]["time"] = "wrong"
        original = deepcopy(candidate)
        self.assert_has_timestamp_violation(candidate)
        self.assertEqual(candidate, original)


if __name__ == "__main__":
    unittest.main()
