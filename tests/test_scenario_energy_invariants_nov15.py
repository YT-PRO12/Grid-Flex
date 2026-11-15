"""Scenario transformation must not mutate default energy and job inputs."""
from copy import deepcopy

from engine.scenario import DEFAULT, scenario


def test_surge_and_cloudy_presets_keep_physically_valid_input_ranges():
    original = deepcopy(DEFAULT)
    for preset in ("normal", "cloudy", "production-surge", "high-tariff"):
        result = scenario(preset, solar_scale=1.25, demand_scale=1.1)
        assert len(result["hours"]) == 12
        assert len(result["base_kw"]) == 12
        assert len(result["solar_kw"]) == 12
        assert all(load >= 0 for load in result["base_kw"])
        assert all(power >= 0 for power in result["solar_kw"])
        assert all(job["power_kw"] > 0 for job in result["jobs"])
        assert result["controls"]["requested_demand_scale"] == 1.1

    assert DEFAULT == original


def test_derived_scenario_cannot_mutate_future_scenario_controls():
    first = scenario("cloudy")
    first["jobs"][0]["power_kw"] = 9999
    first["battery"]["capacity_kwh"] = -1
    second = scenario("cloudy")
    assert second["jobs"][0]["power_kw"] != 9999
    assert second["battery"]["capacity_kwh"] > 0
