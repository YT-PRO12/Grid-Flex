"""Cheap fixture checks without launching the MILP solver."""
import unittest

from engine.scenario import DEFAULT, scenario


class EmergencyScenarioContractTest(unittest.TestCase):
    def test_outage_disables_grid_in_the_declared_slots_only(self):
        data = scenario("emergency-outage")
        self.assertTrue(data["emergency"])
        self.assertEqual(data["hours"][8:10], ["16:00", "17:00"])
        self.assertEqual(data["outage_hours"], data["hours"][8:10])
        self.assertEqual(data["grid_limit_kw"][8:10], [0, 0])
        self.assertTrue(all(value > 0 for index, value in enumerate(
            data["grid_limit_kw"]
        ) if index not in (8, 9)))
        self.assertEqual(data["max_sheddable_share"], 0.30)

    def test_normal_preset_does_not_inherit_outage_mutations(self):
        scenario("emergency-outage")
        normal = scenario("normal")
        self.assertFalse(normal["emergency"])
        self.assertEqual(normal["max_sheddable_share"], 0.0)
        self.assertTrue(all(value == 165 for value in normal["grid_limit_kw"]))
        self.assertEqual(DEFAULT["grid_limit_kw"][8], 86)


if __name__ == "__main__":
    unittest.main()
