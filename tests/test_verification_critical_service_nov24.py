"""A complete positive control isolates the critical-service metric check."""
from copy import deepcopy
import unittest

from engine.verification import verify_plan


def fixture():
    data = {
        "hours": ["08:00"], "jobs": [],
        "base_kw": [5.0], "grid_limit_kw": [10.0], "solar_kw": [0.0],
        "tariff_inr_per_kwh": [2.0], "carbon_kg_per_kwh": [0.5],
        "grid_peak_rate_inr_per_kw": 1.0, "battery_cycle_cost_inr_per_kwh": 1.0,
        "battery": {
            "initial_kwh": 5.0, "min_kwh": 0.0, "capacity_kwh": 10.0,
            "max_charge_kw": 2.0, "max_discharge_kw": 2.0,
            "charge_efficiency": 1.0, "discharge_efficiency": 1.0,
        },
    }
    plan = {
        "jobs": [],
        "slots": [{
            "time": "08:00", "tariff": 2.0, "grid_kw": 5.0,
            "solar_used_kw": 0.0, "charge_kw": 0.0, "discharge_kw": 0.0,
            "base_kw": 5.0, "flexible_kw": 0.0, "noncritical_shed_kw": 0.0,
            "soc_kwh": 5.0, "grid_limit_kw": 10.0, "solar_available_kw": 0.0,
        }],
        "metrics": {
            "energy_cost_inr": 10.0, "demand_charge_inr": 5.0,
            "battery_throughput_kwh": 0.0, "battery_cycle_cost_inr": 0.0,
            "peak_import_kw": 5.0, "grid_energy_kwh": 5.0,
            "solar_utilized_kwh": 0.0, "estimated_grid_emissions_kg": 2.5,
            "ending_soc_kwh": 5.0, "unserved_penalty_inr": 0.0,
            "total_cost_inr": 15.0, "operating_cost_excluding_wear_inr": 15.0,
            "equivalent_full_cycles": 0.0, "objective_value_inr": 15.0,
            "unserved_noncritical_kwh": 0.0, "critical_load_served_pct": 100.0,
        },
    }
    return data, plan


class CriticalServiceTests(unittest.TestCase):
    def test_valid_plan_passes(self):
        data, plan = fixture()
        original = deepcopy(plan)
        result = verify_plan(data, plan)
        self.assertTrue(result["passed"], result["violations"])
        self.assertIs(result["summary"]["critical_load_preserved"], True)
        self.assertEqual(plan, original)

    def test_incorrect_or_missing_percentage_is_rejected(self):
        for percentage in (0, 99.9, 101, None):
            with self.subTest(percentage=percentage):
                data, plan = fixture()
                if percentage is None:
                    del plan["metrics"]["critical_load_served_pct"]
                else:
                    plan["metrics"]["critical_load_served_pct"] = percentage
                result = verify_plan(data, plan)
                self.assertFalse(result["passed"])
                self.assertEqual(result["violations"],
                                 ["Critical-load service percentage mismatch"])


if __name__ == "__main__":
    unittest.main()
