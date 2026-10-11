"""Control-room v1.2 regression coverage — deterministic synthetic MILP results."""
import unittest
from math import isfinite
from engine.scenario import scenario
from engine.optimizer import optimize
from app import route


class ControlRoomTests(unittest.TestCase):
    def test_six_presets_are_feasible_and_consistent(self):
        for preset in ('grid-stress','normal','cloudy','high-tariff','production-surge','battery-limited'):
            with self.subTest(preset=preset):
                data = scenario(preset=preset)
                result = optimize(data)
                self.assertIn(result['optimized']['status'], ('optimal','feasible-time-limited'))
                self.assertEqual(len(result['optimized']['jobs']), len(data['jobs']))
                self.assertEqual(len(result['optimized']['slots']), 12)

    def test_what_if_controls_change_actual_physical_inputs(self):
        default=scenario()
        changed=scenario(demand_scale=1.2,solar_scale=.55,battery_capacity=60,
                         evening_grid_cap=70,tariff_multiplier=1.4,carbon_price=7)
        self.assertGreater(changed['jobs'][0]['power_kw'], default['jobs'][0]['power_kw'])
        self.assertGreater(changed['base_kw'][2], default['base_kw'][2])
        self.assertLess(changed['solar_kw'][3],default['solar_kw'][3])
        self.assertEqual(changed['battery']['capacity_kwh'],60)
        self.assertEqual(changed['grid_limit_kw'][6],70)
        self.assertGreater(changed['tariff_inr_per_kwh'][0],default['tariff_inr_per_kwh'][0])
        self.assertEqual(changed['carbon_price_inr_per_kg'],7)

    def test_invalid_inputs_rejected_early(self):
        invalid=[{'battery_capacity':35},{'battery_capacity':121},{'demand_scale':1.4},
                 {'evening_grid_cap':59},{'evening_grid_cap':float('inf')},
                 {'demand_scale':float('nan')},{'initial_soc':70,'battery_capacity':60},
                 {'carbon_price':-1},{'solar_scale':True},{'preset':'unknown'}]
        for case in invalid:
            with self.subTest(case=case), self.assertRaises(ValueError):
                scenario(**case)

    def test_extended_api_and_explanations(self):
        code,payload=route('POST','/api/optimize',{'preset':'cloudy','demand_scale':1.10,
                   'battery_capacity':80,'evening_grid_cap':90})
        self.assertEqual(code,200)
        self.assertEqual(payload['scenario']['battery']['capacity_kwh'],80)
        self.assertGreaterEqual(len(payload['explanations']),1)
        for item in payload['explanations']:
            self.assertIn(item['kind'],('schedule','battery','constraint','result'))
            self.assertGreater(len(item['detail']),25)

    def test_battery_throughput_accounted_in_modeled_cost(self):
        result=optimize(scenario())
        for name in ('optimized','baseline'):
            metric=result[name]['metrics']
            self.assertAlmostEqual(metric['total_cost_inr'],metric['energy_cost_inr']+
                  metric['demand_charge_inr']+metric['battery_cycle_cost_inr'],delta=.02)
            self.assertGreaterEqual(metric['battery_throughput_kwh'],0)

    def test_optimized_controls_obey_all_operational_constraints(self):
        for data in (scenario(demand_scale=1.35),scenario(battery_capacity=36),
                     scenario(evening_grid_cap=60),scenario(preset='cloudy',solar_scale=.5)):
            result=optimize(data)
            jobs={j['id']:j for j in data['jobs']}
            for plan in (result['baseline'],result['optimized']):
                self.assertTrue(all(j['start']>=jobs[j['id']]['earliest'] and
                         j['end']<=jobs[j['id']]['deadline'] for j in plan['jobs']))
                state=data['battery']['initial_kwh']
                for idx,slot in enumerate(plan['slots']):
                    self.assertLessEqual(slot['grid_kw'],data['grid_limit_kw'][idx]+0.001)
                    self.assertLessEqual(slot['solar_used_kw'],data['solar_kw'][idx]+0.001)
                    self.assertAlmostEqual(slot['grid_kw']+slot['solar_used_kw']+
                        slot['discharge_kw']-slot['charge_kw'],slot['base_kw']+slot['flexible_kw'],delta=.025)
                    self.assertFalse(slot['charge_kw']>.01 and slot['discharge_kw']>.01)
                    state+=slot['charge_kw']*data['battery']['charge_efficiency']-slot['discharge_kw']/data['battery']['discharge_efficiency']
                    self.assertGreaterEqual(state,data['battery']['min_kwh']-.03)
                    self.assertLessEqual(state,data['battery']['capacity_kwh']+.03)
                self.assertGreaterEqual(state,data['battery']['initial_kwh']-.03)

    def test_tradeoff_is_signed_not_always_green(self):
        r=optimize(scenario())
        self.assertLess(r['comparison']['emissions_change_kg'],0)
        self.assertTrue(isfinite(r['comparison']['estimated_cost_saving_pct']))

    def test_api_rejects_out_of_range_control(self):
        code,payload=route('POST','/api/optimize',{'battery_capacity':-1})
        self.assertEqual(code,422)
        self.assertIn('battery_capacity',payload['error'])


if __name__=='__main__':
    unittest.main()
