"""Battery-limited presets never mutate the default scenario."""
from engine.scenario import DEFAULT, scenario


def test_battery_limited_preset_restricts_capacity_and_charge_rate():
    limited = scenario("battery-limited")
    assert limited["battery"]["capacity_kwh"] == 40
    assert limited["battery"]["max_charge_kw"] == 15
    assert limited["battery"]["max_discharge_kw"] == 15
    assert limited["battery"]["initial_kwh"] == 26


def test_battery_limited_preset_honors_smaller_explicit_capacity():
    limited = scenario("battery-limited", battery_capacity=36, initial_soc=8)
    assert limited["battery"]["capacity_kwh"] == 36
    assert limited["battery"]["max_charge_kw"] == 13.5
    assert limited["battery"]["initial_kwh"] == 8
    assert DEFAULT["battery"]["capacity_kwh"] == 72
    assert scenario()["battery"]["capacity_kwh"] == 72
