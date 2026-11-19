"""Boundary regression tests for numeric scenario controls."""
import unittest

from engine.scenario import scenario


class FractionalControlBoundaryTests(unittest.TestCase):
    def test_documented_endpoints_are_inclusive(self):
        bounds = {
            "solar_scale": (0.25, 1.5),
            "tariff_multiplier": (0.5, 2.0),
            "carbon_price": (0, 15),
            "demand_scale": (0.75, 1.35),
            "battery_capacity": (36, 120),
            "evening_grid_cap": (60, 165),
            "battery_wear_cost": (0, 20),
        }
        for key, limits in bounds.items():
            for value in limits:
                with self.subTest(control=key, endpoint=value):
                    output = scenario(**{key: value})
                    self.assertEqual(output["controls"][key], value)

    def test_out_of_bounds_controls_are_rejected_without_clamping(self):
        outside = {
            "solar_scale": (0.2499, 1.5001),
            "tariff_multiplier": (0.4999, 2.0001),
            "carbon_price": (-0.0001, 15.0001),
            "demand_scale": (0.7499, 1.3501),
            "battery_capacity": (35.9999, 120.0001),
            "evening_grid_cap": (59.9999, 165.0001),
            "battery_wear_cost": (-0.0001, 20.0001),
        }
        for key, values in outside.items():
            for value in values:
                with self.subTest(control=key, value=value):
                    with self.assertRaisesRegex(ValueError, key):
                        scenario(**{key: value})


if __name__ == "__main__":
    unittest.main()
