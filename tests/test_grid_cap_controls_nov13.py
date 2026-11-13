"""Grid control inputs apply only to the applicable synthetic preset slots."""
from engine.scenario import DEFAULT, scenario


def test_grid_stress_uses_configured_evening_cap():
    result = scenario("grid-stress", evening_grid_cap=100)
    assert result["grid_limit_kw"] == [165] * 6 + [100] * 6
    assert result["controls"]["evening_grid_cap"] == 100


def test_normal_preset_keeps_full_grid_access():
    normal = scenario("normal", evening_grid_cap=100)
    assert normal["grid_limit_kw"] == [165] * 12


def test_emergency_outage_overrides_cap_only_in_outage_slots():
    emergency = scenario("emergency-outage", evening_grid_cap=100)
    assert emergency["grid_limit_kw"] == [165] * 6 + [100, 100, 0, 0, 100, 100]
    assert emergency["max_sheddable_share"] == 0.30
    assert DEFAULT["grid_limit_kw"][8] == 86
