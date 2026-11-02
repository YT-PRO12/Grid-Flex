"""Scenario construction must not alter baseline synthetic inputs."""
import unittest
from copy import deepcopy

from engine.scenario import DEFAULT, scenario


class ScenarioIsolationTests(unittest.TestCase):
    def test_modified_scenarios_do_not_mutate_default(self):
        before = deepcopy(DEFAULT)
        custom = scenario("cloudy", solar_scale=0.75, demand_scale=1.1)
        self.assertEqual(DEFAULT, before)
        self.assertNotEqual(custom["solar_kw"], DEFAULT["solar_kw"])

    def test_separate_scenarios_do_not_share_mutable_jobs(self):
        first = scenario()
        second = scenario()
        first["jobs"][0]["power_kw"] = 999
        first["battery"]["initial_kwh"] = 8
        self.assertNotEqual(first["jobs"][0]["power_kw"], second["jobs"][0]["power_kw"])
        self.assertNotEqual(first["battery"]["initial_kwh"], second["battery"]["initial_kwh"])

if __name__ == "__main__":
    unittest.main()
