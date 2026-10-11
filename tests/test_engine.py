"""Deterministic integration, MILP physical-feasibility and input tests."""
import unittest
import json
from engine.scenario import scenario
from engine.optimizer import optimize,solve
from app import route,lambda_handler

class GridFlexTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data=scenario()
        cls.result=optimize(cls.data)

    def test_optimized_schedules_jobs_exactly_once_within_windows(self):
        tasks={j['id']:j for j in self.data['jobs']}
        for plan in self.result['optimized']['jobs']:
            job=tasks[plan['id']]
            self.assertGreaterEqual(plan['start'],job['earliest'])
            self.assertLessEqual(plan['end'],job['deadline'])
            self.assertEqual(plan['end']-plan['start'],job['duration_h'])
        self.assertEqual(len(tasks),len(self.result['optimized']['jobs']))

    def test_both_plans_physically_valid(self):
        for key in ('baseline','optimized'):
            result=self.result[key]
            b=self.data['battery']
            soc=b['initial_kwh']
            for t,slot in enumerate(result['slots']):
                lhs=slot['grid_kw']+slot['solar_used_kw']+slot['discharge_kw']-slot['charge_kw']
                demand=slot['base_kw']+slot['flexible_kw']
                self.assertAlmostEqual(lhs,demand,delta=0.012)
                self.assertLessEqual(slot['grid_kw'],self.data['grid_limit_kw'][t]+0.001)
                self.assertLessEqual(slot['solar_used_kw'],self.data['solar_kw'][t]+0.001)
                self.assertFalse(slot['charge_kw']>0.01 and slot['discharge_kw']>0.01)
                soc += b['charge_efficiency']*slot['charge_kw'] - slot['discharge_kw']/b['discharge_efficiency']
                self.assertGreaterEqual(soc,b['min_kwh']-0.02)
                self.assertLessEqual(soc,b['capacity_kwh']+0.02)
            self.assertGreaterEqual(soc,b['initial_kwh']-0.02)

    def test_baseline_optimized_are_different(self):
        self.assertGreaterEqual(self.result['comparison']['estimated_cost_saving_inr'],-0.05)
        self.assertGreater(self.result['comparison']['peak_reduction_kw'],0)

    def test_emissions_are_not_improperly_labelled_savings(self):
        # Cost and peak optimality does not imply emissions decrease; report signed difference.
        comp=self.result['comparison']
        self.assertAlmostEqual(comp['emissions_change_kg'],round(self.result['baseline']['metrics']['estimated_grid_emissions_kg']-self.result['optimized']['metrics']['estimated_grid_emissions_kg'],2))

    def test_scenario_presets(self):
        self.assertTrue(all(v==165 for v in scenario('normal')['grid_limit_kw']))
        self.assertEqual(scenario('cloudy')['solar_kw'][0],4)
        self.assertEqual(scenario(solar_scale=0.5)['solar_kw'][0],4)

    def test_input_validation(self):
        for opts in ({'preset':'unknown'},{'solar_scale':5},{'initial_soc':0},{'carbon_price':float('nan')},{'tariff_multiplier':False}):
            with self.assertRaises(ValueError):scenario(**opts)

    def test_cloudy_scenario_feasible(self):
        res=optimize(scenario('cloudy'))
        self.assertIn(res['optimized']['status'],('optimal','feasible-time-limited'))

    def test_normal_scenario_feasible(self):
        res=optimize(scenario('normal'))
        self.assertIn(res['optimized']['status'],('optimal','feasible-time-limited'))

    def test_api_health_and_scenario(self):
        c,p=route('GET','/api/health');self.assertEqual(c,200);self.assertEqual(p['storage'],'local-ephemeral')
        c,p=route('GET','/api/scenario');self.assertEqual(c,200);self.assertEqual(len(p['hours']),12)

    def test_api_rejects_unknown_fields(self):
        c,p=route('POST','/api/optimize',{'energy_cost_overrides':[0]*12});self.assertEqual(c,400)

    def test_api_optimizes_and_records_history(self):
        c,p=route('POST','/api/optimize',{'preset':'grid-stress'});self.assertEqual(c,200)
        c,h=route('GET','/api/history');self.assertEqual(c,200)
        self.assertEqual(h['runs'][0]['id'],p['run_id'])

    def test_lambda_handler_contract(self):
        event={'requestContext':{'http':{'method':'GET'}},'rawPath':'/api/health'}
        response=lambda_handler(event,None)
        self.assertEqual(response['statusCode'],200)
        self.assertIn('synthetic',response['body'])

if __name__=='__main__':unittest.main()
