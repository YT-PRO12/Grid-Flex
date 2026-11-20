"""Inputs must not be implicitly coerced into operational control values."""
import math
import unittest

from engine.scenario import scenario


class ScenarioInputContractTests(unittest.TestCase):
    def test_numeric_controls_reject_strings_and_containers(self):
        fields = (
            "solar_scale", "tariff_multiplier", "carbon_price",
            "demand_scale", "battery_capacity", "evening_grid_cap",
            "battery_wear_cost",
        )
        for field in fields:
            for value in ("1", "", None, [], {}):
                with self.subTest(field=field, value=repr(value)):
                    with self.assertRaisesRegex(ValueError, field):
                        scenario(**{field: value})

    def test_initial_state_of_charge_rejects_boolean_and_nonfinite(self):
        for invalid in (True, False, math.nan, math.inf, -math.inf, "26", None):
            if invalid is None:
                # None intentionally asks for the documented default.
                self.assertEqual(scenario(initial_soc=None)["battery"]["initial_kwh"], 26)
                continue
            with self.subTest(initial_soc=repr(invalid)):
                with self.assertRaisesRegex(ValueError, "initial_soc"):
                    scenario(initial_soc=invalid)

    def test_invalid_preset_is_rejected_before_scenario_generation(self):
        for preset in ("", "emergency", "unknown", None):
            with self.subTest(preset=preset):
                with self.assertRaisesRegex(ValueError, "Unknown scenario"):
                    scenario(preset)


if __name__ == "__main__":
    unittest.main()
