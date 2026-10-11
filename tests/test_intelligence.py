"""Numerical sensitivity, preservation, audit and request-boundary regression tests."""
import json
import unittest
from copy import deepcopy
from unittest.mock import patch
from engine.scenario import scenario
from engine.optimizer import solve, OptimizationError
from engine.intelligence import analyze, evaluate_stress, stress_cases
from engine.verification import verify_plan
from app import route, lambda_handler, MAX_JSON_BYTES

class IntelligenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data=scenario(battery_wear_cost=8)
        cls.result=analyze(cls.data)
        cls.outage=scenario('emergency-outage')
        cls.outage_plan=solve(cls.outage)

    def test_stress_reproducible_and_preserves_input(self):
        before=deepcopy(self.outage_plan)
        a=evaluate_stress(self.outage,self.outage_plan)
        self.assertEqual(a,evaluate_stress(self.outage,self.outage_plan))
        self.assertEqual(self.outage_plan,before)

    def test_nominal_stress_passes(self):
        a=evaluate_stress(self.outage,self.outage_plan)
        self.assertTrue(a['cases'][0]['passed'])
        self.assertEqual(a['tested_count'],5)
        self.assertEqual(a['pass_pct'],round(100*a['passed_count']/5,1))

    def test_outage_shortfall_is_calculated_and_not_cost_saving(self):
        cases=[{'key':'no-sun','name':'No sun','solar_kw':[0]*12}]
        r=evaluate_stress(self.outage,self.outage_plan,cases)['cases'][0]
        self.assertFalse(r['passed']);self.assertGreater(r['shortfall_kwh'],0)
        self.assertIsNone(r['feasible_metrics'])
        for t in (8,9):
            s=self.outage_plan['slots'][t]
            expected=max(0,s['base_kw']+s['flexible_kw']+s['charge_kw']-s['discharge_kw']-s['noncritical_shed_kw'])
            self.assertAlmostEqual(r['shortfall_by_hour_kwh'][t],expected,places=3)

    def test_high_risk_counts_match_case_failures(self):
        r=evaluate_stress(self.outage,self.outage_plan)
        for t,h in enumerate(r['hours']):
            n=sum(c['shortfall_by_hour_kwh'][t]>.04 for c in r['cases'])
            self.assertEqual(h['failing_cases'],n);self.assertEqual(h['high_risk'],n>=2)

    def test_conservative_plan_verified_under_lower_pv(self):
        alt=self.result['conservative'];lower=deepcopy(self.data)
        lower['solar_kw']=[round(v*.6,4) for v in lower['solar_kw']]
        self.assertTrue(verify_plan(lower,alt['plan'])['passed'])
        self.assertEqual(alt['stress']['cases'][0]['solar_kw'],self.data['solar_kw'])

    def test_infeasible_conservative_is_explicit_without_losing_current(self):
        real=solve
        def mock(data,**kwargs):
            if data['solar_kw']!=self.data['solar_kw']:raise OptimizationError('No feasible schedule')
            return real(data,**kwargs)
        with patch('engine.intelligence.solve',side_effect=mock):r=analyze(self.data)
        self.assertIsNone(r['conservative']['plan']);self.assertIn('error',r['conservative'])
        self.assertTrue(r['current']['verification']['passed'])

    def test_efc_and_wear_formula(self):
        p=self.result['current']['plan'];m=p['metrics']
        throughput=sum(s['charge_kw']+s['discharge_kw'] for s in p['slots'])
        self.assertAlmostEqual(m['equivalent_full_cycles'],throughput/(2*self.data['battery']['capacity_kwh']),delta=.0001)
        self.assertAlmostEqual(m['battery_cycle_cost_inr'],throughput*8,delta=.05)
        self.assertTrue(verify_plan(self.data,p)['passed'])

    def test_wear_changes_dispatch_and_fair_economics(self):
        b=self.result['battery'];off,on=b['without_wear'],b['with_wear']
        self.assertLess(on['throughput_kwh'],off['throughput_kwh']-1)
        self.assertLessEqual(on['total_at_common_rate_inr'],off['total_at_common_rate_inr']+.5)
        for m in (off,on):self.assertAlmostEqual(m['wear_at_common_rate_inr'],8*m['throughput_kwh'],places=2)
        self.assertEqual(off['jobs_completed'],on['jobs_completed'])

    def test_zero_wear_is_optional(self):
        r=analyze(scenario(battery_wear_cost=0))
        self.assertEqual(r['battery']['without_wear'],r['battery']['with_wear'])
        self.assertEqual(r['battery']['with_wear']['wear_at_common_rate_inr'],0)

    def test_invalid_wear_values(self):
        for v in (-1,21,True,float('inf'),float('nan'),'5'):
            with self.subTest(v=v),self.assertRaises(ValueError):scenario(battery_wear_cost=v)

    def test_exact_selected_plan_retained(self):
        p=self.result['current']['plan']
        r=analyze(self.data,existing_plan=p)
        self.assertEqual(r['current']['plan'],p)

    def test_corrupt_metrics_and_job_power_rejected(self):
        for field in ['total_cost_inr','objective_value_inr','ending_soc_kwh']:
            p=deepcopy(self.result['current']['plan']);p['metrics'][field]+=30
            self.assertFalse(verify_plan(self.data,p)['passed'])
        p=deepcopy(self.result['current']['plan']);p['jobs'][0]['power_kw']+=1
        self.assertFalse(verify_plan(self.data,p)['passed'])

    def test_api_analysis_and_malformed_input(self):
        p=self.result['current']['plan']
        code,r=route('POST','/api/intelligence',{'battery_wear_cost':8,'strategy':'cost','plan':p})
        self.assertEqual(code,200);self.assertEqual(r['current']['plan'],p)
        for body in ({'strategy':'invalid'},{'plan':{}},{'plan':p,'strategy':'carbon'}):
            self.assertEqual(route('POST','/api/intelligence',body)[0],422)
        self.assertEqual(route('POST','/api/intelligence',{'unexpected':2})[0],400)

    def test_lambda_size_json_and_health(self):
        e={'rawPath':'/api/intelligence','requestContext':{'http':{'method':'POST'}},'body':'x'*(MAX_JSON_BYTES+1)}
        self.assertEqual(lambda_handler(e,None)['statusCode'],413)
        e['body']='not json';self.assertEqual(lambda_handler(e,None)['statusCode'],400)

    def test_true_infeasibility_reported(self):
        d=scenario('emergency-outage');d['solar_kw']=[0]*12;d['grid_limit_kw']=[0]*12
        with self.assertRaises(OptimizationError):solve(d)

if __name__=='__main__':unittest.main()
