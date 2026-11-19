"""The simulated emergency outage must stay at its disclosed two-hour window."""
import unittest

from engine.scenario import scenario


class OutageTimelineTests(unittest.TestCase):
    def test_outage_timeline_matches_zero_grid_capacity(self):
        case = scenario("emergency-outage")
        zero_hours = [
            hour for hour, cap in zip(case["hours"], case["grid_limit_kw"])
            if cap == 0
        ]
        self.assertTrue(case["emergency"])
        self.assertEqual(zero_hours, ["16:00", "17:00"])
        self.assertEqual(case["outage_hours"], zero_hours)
        self.assertEqual(case["max_sheddable_share"], 0.30)

    def test_other_presets_do_not_inherit_emergency_capabilities(self):
        for preset in ("normal", "grid-stress", "cloudy",
                       "high-tariff", "production-surge", "battery-limited"):
            with self.subTest(preset=preset):
                case = scenario(preset)
                self.assertFalse(case["emergency"])
                self.assertEqual(case["max_sheddable_share"], 0)
                self.assertNotIn("outage_hours", case)
                self.assertTrue(all(cap > 0 for cap in case["grid_limit_kw"]))


if __name__ == "__main__":
    unittest.main()
