"""Synthetic preset transformations must not affect future scenario requests."""
from engine.scenario import DEFAULT, scenario


def test_production_surge_scales_loads_without_mutating_defaults():
    high = scenario("production-surge")
    assert high["base_kw"] == [
        round(value * 1.16, 2) for value in DEFAULT["base_kw"]
    ]
    assert [job["power_kw"] for job in high["jobs"]] == [
        round(job["power_kw"] * 1.16, 2) for job in DEFAULT["jobs"]
    ]
    assert scenario()["base_kw"] == DEFAULT["base_kw"]


def test_high_tariff_only_multiplies_the_late_slots():
    high = scenario("high-tariff", tariff_multiplier=1.2)
    expected = [
        round(rate * (1.5 if i >= 6 else 1) * 1.2, 2)
        for i, rate in enumerate(DEFAULT["tariff_inr_per_kwh"])
    ]
    assert high["tariff_inr_per_kwh"] == expected
    assert DEFAULT["tariff_inr_per_kwh"][0] == 7
