"""P0 enhancement tests: objective portfolio, real outage, audit and cloud contract."""
import json
import os
import sys
import types
import unittest
from unittest.mock import patch
from copy import deepcopy
from engine.scenario import scenario
from engine.optimizer import optimize
from engine.verification import verify_plan
from app import lambda_handler, route

class AdvanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.default=optimize(scenario())
        cls.emergency=optimize(scenario('emergency-outage'))

    def test_pareto_candidates_genuine_distinct_solutions(self):
        r=self.default
        self.assertEqual([x['key'] for x in r['frontier']],['cost','balanced','carbon'])
        cost=r['strategy_plans']['cost']['metrics']
        carbon=r['strategy_plans']['carbon']['metrics']
        self.assertLessEqual(cost['total_cost_inr'],carbon['total_cost_inr']+.1)
        self.assertLess(carbon['estimated_grid_emissions_kg'],cost['estimated_grid_emissions_kg'])
        for name in ('cost','balanced','carbon'):
            self.assertTrue(r['verification'][name]['passed'])
            self.assertEqual(len(r['strategy_plans'][name]['jobs']),5)

    def test_emergency_zero_import_and_noncritical_shedding(self):
        d=self.emergency['scenario'];r=self.emergency
        self.assertTrue(d['emergency'])
        self.assertEqual(d['grid_limit_kw'][8:10],[0,0])
        self.assertTrue(r['verification']['cost']['passed'])
        self.assertTrue(r['verification']['baseline']['passed'])
        for plan in (r['baseline'],*r['strategy_plans'].values()):
            self.assertEqual(len(plan['jobs']),5)
            self.assertTrue(all(s['grid_kw']<=.001 for s in plan['slots'][8:10]))
            self.assertGreaterEqual(plan['metrics']['unserved_noncritical_kwh'],0)
            for s in plan['slots']:
                self.assertLessEqual(s['noncritical_shed_kw'],s['base_kw']*.30+.01)
                self.assertGreaterEqual(s['base_kw']-s['noncritical_shed_kw'],s['base_kw']*.70-.01)

    def test_no_shedding_in_normal_mode(self):
        for plan in (self.default['baseline'],*self.default['strategy_plans'].values()):
            self.assertEqual(plan['metrics']['unserved_noncritical_kwh'],0)

    def test_verifier_detects_real_violation(self):
        data=self.default['scenario'];plan=deepcopy(self.default['optimized'])
        plan['slots'][4]['grid_kw']+=10
        result=verify_plan(data,plan)
        self.assertFalse(result['passed'])
        self.assertTrue(any('imbalance' in s for s in result['violations']))

    def test_verifier_detects_deadline_violation(self):
        data=self.default['scenario'];plan=deepcopy(self.default['optimized'])
        plan['jobs'][0]['end']=data['jobs'][0]['deadline']+1
        result=verify_plan(data,plan)
        self.assertFalse(result['passed'])

    def test_lambda_health_does_not_fake_cloud_verification(self):
        with patch.dict(os.environ, {'RUNS_TABLE':'demo-table','AWS_LAMBDA_FUNCTION_NAME':'demo-func'}):
            response=lambda_handler({'rawPath':'/api/health','requestContext':{'http':{'method':'GET'}}},None)
            data=json.loads(response['body'])
            self.assertEqual(data['environment'],'aws-lambda')
            self.assertFalse(data['cloud_integration_verified'])
            self.assertEqual(data['storage'],'aws-dynamodb-configured-unverified')

    def test_dynamodb_write_read_contract_with_fake_table(self):
        class FakeTable:
            def __init__(self):self.values={}
            def put_item(self,Item):self.values[Item['pk']]=Item
            def scan(self,Limit):return {'Items':list(self.values.values())[:Limit]}
        table=FakeTable()
        with patch.dict(os.environ, {'RUNS_TABLE':'demo-table'}),patch('app.dynamodb_table',return_value=table):
            code,p=route('POST','/api/optimize',{'preset':'normal'})
            self.assertEqual(code,200)
            self.assertEqual(table.values[p['run_id']]['pk'],p['run_id'])
            self.assertGreater(table.values[p['run_id']]['expires_at'],0)
            record=json.loads(table.values[p['run_id']]['payload'])
            self.assertEqual(len(record['strategies']),3)
            self.assertTrue(record['verified'])
            code,history=route('GET','/api/history')
            self.assertEqual(code,200)
            self.assertEqual(history['runs'][0]['id'],p['run_id'])

if __name__=='__main__':unittest.main()
