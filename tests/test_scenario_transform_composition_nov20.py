"""Scenario multipliers compose predictably and do not leak between controls."""
import unittest

from engine.scenario import DEFAULT, scenario


class ScenarioTransformCompositionTests(unittest.TestCase):
    def test_cloudy_solar_scale_does_not_rescale_demand(self):
        case = scenario("cloudy", solar_scale=1.25)
        expected_solar = [round(round(x * 0.5, 2) * 1.25, 2)
                          for x in DEFAULT["solar_kw"]]
        self.assertEqual(case["solar_kw"], expected_solar)
        self.assertEqual(case["base_kw"], DEFAULT["base_kw"])
        self.assertEqual(case["controls"]["solar_scale"], 1.25)

    def test_production_surge_discloses_requested_and_effective_demand(self):
        requested = 1.1
        effective = requested * 1.16
        case = scenario("production-surge", demand_scale=requested)
        self.assertEqual(case["controls"]["requested_demand_scale"], requested)
        self.assertEqual(case["controls"]["demand_scale"], round(effective, 4))
        self.assertEqual(
            case["base_kw"],
            [round(x * effective, 2) for x in DEFAULT["base_kw"]],
        )
        self.assertEqual(
            [job["power_kw"] for job in case["jobs"]],
            [round(job["power_kw"] * effective, 2) for job in DEFAULT["jobs"]],
        )
        self.assertEqual(case["solar_kw"], DEFAULT["solar_kw"])

    def test_normal_grid_cap_is_not_overridden_by_evening_control(self):
        normal = scenario("normal", evening_grid_cap=60)
        constrained = scenario("grid-stress", evening_grid_cap=60)
        self.assertEqual(normal["grid_limit_kw"], [165] * 12)
        self.assertEqual(constrained["grid_limit_kw"], [165] * 6 + [60] * 6)


if __name__ == "__main__":
    unittest.main()
