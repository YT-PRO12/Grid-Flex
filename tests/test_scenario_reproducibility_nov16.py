"""Repeatable simulation inputs are required for a defensible optimizer comparison."""
from copy import deepcopy
import json

from engine.scenario import DEFAULT, scenario


PRESETS = (
    "grid-stress", "normal", "cloudy", "high-tariff",
    "production-surge", "battery-limited", "emergency-outage",
)


def test_each_preset_is_stable_and_json_serializable():
    original = deepcopy(DEFAULT)
    for preset in PRESETS:
        first = scenario(preset)
        second = scenario(preset)
        assert first == second
        assert first["preset"] == preset
        assert len(first["hours"]) == len(first["base_kw"]) == 12
        assert len(first["tariff_inr_per_kwh"]) == 12
        json.dumps(first, allow_nan=False)
    assert DEFAULT == original


def test_mutating_one_preset_does_not_change_subsequent_results():
    first = scenario("battery-limited")
    first["jobs"][0]["power_kw"] = 9000
    first["battery"]["initial_kwh"] = -100
    later = scenario("battery-limited")
    assert later["jobs"][0]["power_kw"] < 100
    assert later["battery"]["initial_kwh"] >= 8
