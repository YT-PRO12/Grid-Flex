"""Synthetic preset calls should never leak state into later requests."""
import unittest

from engine.scenario import DEFAULT, scenario


class IndependentControlsTest(unittest.TestCase):
    def test_outage_does_not_affect_normal_preset(self):
        outage = scenario("emergency-outage")
        self.assertEqual(outage["grid_limit_kw"][8:10], [0, 0])
        normal = scenario("normal")
        self.assertEqual(normal["grid_limit_kw"], [165] * 12)
        self.assertFalse(normal["emergency"])
        self.assertEqual(normal["max_sheddable_share"], 0.0)

    def test_nested_lists_are_separate_between_calls(self):
        first = scenario()
        second = scenario()
        first["solar_kw"][0] = 999
        first["jobs"][0]["duration_h"] = 99
        self.assertEqual(second["solar_kw"][0], DEFAULT["solar_kw"][0])
        self.assertEqual(second["jobs"][0]["duration_h"], DEFAULT["jobs"][0]["duration_h"])


if __name__ == "__main__":
    unittest.main()
