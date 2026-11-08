"""Scenario presets transform independent synthetic copies."""
from engine.scenario import DEFAULT, scenario


def test_cloudy_preset_halves_solar_without_changing_defaults():
    cloudy = scenario("cloudy")
    assert cloudy["solar_kw"] == [round(value * 0.5, 2) for value in DEFAULT["solar_kw"]]
    assert scenario("grid-stress")["solar_kw"] == DEFAULT["solar_kw"]


def test_high_tariff_preset_only_adds_peak_multiplier():
    high = scenario("high-tariff")
    base = DEFAULT["tariff_inr_per_kwh"]
    assert high["tariff_inr_per_kwh"] == [
        round(rate * (1.5 if hour >= 6 else 1), 2)
        for hour, rate in enumerate(base)
    ]
    assert DEFAULT["tariff_inr_per_kwh"] == base
