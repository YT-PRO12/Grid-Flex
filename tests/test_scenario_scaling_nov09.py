"""Scenario controls must scale both job demand and base load consistently."""
from engine.scenario import DEFAULT, scenario


def test_solar_and_demand_scaling_preserves_baseline():
    result = scenario("normal", solar_scale=1.25, demand_scale=1.1)
    assert result["solar_kw"] == [
        round(value * 1.25, 2) for value in DEFAULT["solar_kw"]
    ]
    assert result["base_kw"] == [
        round(value * 1.1, 2) for value in DEFAULT["base_kw"]
    ]
    assert [job["power_kw"] for job in result["jobs"]] == [
        round(job["power_kw"] * 1.1, 2) for job in DEFAULT["jobs"]
    ]
    assert result["grid_limit_kw"] == [165] * 12
    assert scenario("grid-stress")["solar_kw"] == DEFAULT["solar_kw"]


def test_battery_capacity_recomputes_charge_limits():
    result = scenario(battery_capacity=36, initial_soc=8)
    assert result["battery"]["capacity_kwh"] == 36
    assert result["battery"]["initial_kwh"] == 8
    assert result["battery"]["max_charge_kw"] == 13.5
    assert result["battery"]["max_discharge_kw"] == 13.5
