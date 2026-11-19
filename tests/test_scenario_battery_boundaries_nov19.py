"""Synthetic battery controls remain physically bounded when capacity changes."""
import unittest

from engine.scenario import scenario


class BatteryBoundaryTests(unittest.TestCase):
    def test_power_limited_by_capacity_and_hard_ceiling(self):
        for capacity in (36.0, 40.0, 72.0, 120.0):
            with self.subTest(capacity=capacity):
                case = scenario(battery_capacity=capacity)
                battery = case["battery"]
                expected = min(27, capacity * 0.375)
                self.assertEqual(battery["capacity_kwh"], capacity)
                self.assertEqual(battery["max_charge_kw"], expected)
                self.assertEqual(battery["max_discharge_kw"], expected)

    def test_initial_energy_is_in_bounds(self):
        for capacity in (36.0, 72.0, 120.0):
            with self.subTest(capacity=capacity):
                battery = scenario(battery_capacity=capacity)["battery"]
                self.assertGreaterEqual(battery["initial_kwh"], battery["min_kwh"])
                self.assertLessEqual(battery["initial_kwh"], battery["capacity_kwh"])
                selected = scenario(
                    battery_capacity=capacity, initial_soc=capacity
                )["battery"]
                self.assertEqual(selected["initial_kwh"], capacity)

    def test_initial_energy_above_capacity_fails(self):
        with self.assertRaisesRegex(ValueError, "initial_soc"):
            scenario(battery_capacity=40, initial_soc=40.001)


if __name__ == "__main__":
    unittest.main()
