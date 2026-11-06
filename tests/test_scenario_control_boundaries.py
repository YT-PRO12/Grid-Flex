"""Control validation must not coerce booleans or nonfinite numbers."""
import math
import unittest

from engine.scenario import scenario


class ScenarioControlBoundariesTest(unittest.TestCase):
    def test_every_numeric_control_rejects_nonfinite_and_boolean_values(self):
        controls = (
            "solar_scale", "tariff_multiplier", "carbon_price", "demand_scale",
            "battery_capacity", "evening_grid_cap", "battery_wear_cost",
        )
        for control in controls:
            for bad in (math.nan, math.inf, -math.inf, True, False):
                with self.subTest(control=control, bad=bad):
                    with self.assertRaises(ValueError):
                        scenario(**{control: bad})

    def test_user_supplied_state_of_charge_obeys_capacity(self):
        with self.assertRaises(ValueError):
            scenario(battery_capacity=36, initial_soc=37)
        self.assertEqual(scenario(battery_capacity=36, initial_soc=8)["battery"]["initial_kwh"], 8)


if __name__ == "__main__":
    unittest.main()
