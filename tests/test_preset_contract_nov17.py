"""Scenario fixtures are deterministic inputs, not measured grid forecasts."""
from copy import deepcopy

from engine.scenario import DEFAULT, scenario


def test_all_preset_series_cover_the_same_twelve_slots():
    original = deepcopy(DEFAULT)
    for name in ("grid-stress", "normal", "cloudy", "high-tariff",
                 "production-surge", "battery-limited", "emergency-outage"):
        result = scenario(name)
        for key in ("hours", "base_kw", "solar_kw", "tariff_inr_per_kwh",
                    "grid_limit_kw", "carbon_kg_per_kwh"):
            assert len(result[key]) == 12, (name, key)
        assert result["preset"] == name
        assert result["battery"]["capacity_kwh"] >= result["battery"]["initial_kwh"]
        assert all(value >= 0 for value in result["solar_kw"])
    assert DEFAULT == original


def test_synthetic_notice_is_preserved_for_all_presets():
    assert "synthetic" in scenario("normal")["data_notice"].lower()
    assert scenario("normal") == scenario("normal")
