"""A synthetic production surge is distinct from the caller's manual scale."""
from engine.scenario import DEFAULT, scenario


def test_surge_reports_manual_and_effective_demand_separately():
    result = scenario("production-surge", demand_scale=1.1)
    expected = 1.1 * 1.16
    assert result["controls"]["requested_demand_scale"] == 1.1
    assert result["controls"]["demand_scale"] == round(expected, 4)
    assert result["base_kw"] == [
        round(base * expected, 2) for base in DEFAULT["base_kw"]
    ]


def test_normal_preset_does_not_apply_surge_multiplier():
    result = scenario("normal", demand_scale=1.1)
    assert result["controls"]["requested_demand_scale"] == 1.1
    assert result["controls"]["demand_scale"] == 1.1
    assert DEFAULT["base_kw"][0] == 32
