"""New operator alert and interactive UI regression checks."""
import unittest
from pathlib import Path
from engine.scenario import scenario
from engine.optimizer import optimize
from engine.diagnostics import analyze_dispatch
from app import route

ROOT=Path(__file__).resolve().parents[1]

class OperatorIntelligenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.normal=optimize(scenario())
        cls.emergency=optimize(scenario('emergency-outage'))

    def test_all_strategies_have_actionable_solver_backed_advisories(self):
        r=self.normal
        self.assertEqual(set(r['operator_alerts']),{'cost','balanced','carbon'})
        for strategy,alerts in r['operator_alerts'].items():
            self.assertGreaterEqual(len(alerts),1)
            self.assertLessEqual(len(alerts),5)
            self.assertEqual(len({a['kind'] for a in alerts}),len(alerts))
            for alert in alerts:
                self.assertIn(alert['severity'],{'critical','warning','info','ok'})
                self.assertTrue(alert['action'])
                if alert['hour'] is not None:
                    self.assertGreaterEqual(alert['hour'],0)
                    self.assertLess(alert['hour'],12)
                    self.assertIn(r['scenario']['hours'][alert['hour']],alert['detail'])

    def test_emergency_alert_hour_matches_actual_zero_grid_cap(self):
        r=self.emergency
        alerts=r['operator_alerts']['cost']
        outage=[a for a in alerts if a['kind']=='outage']
        self.assertEqual(len(outage),1)
        hour=outage[0]['hour']
        self.assertEqual(r['scenario']['grid_limit_kw'][hour],0)
        self.assertAlmostEqual(r['optimized']['slots'][hour]['grid_kw'],0,delta=.01)
        self.assertEqual(outage[0]['severity'],'critical')
        self.assertTrue(r['verification']['cost']['passed'])

    def test_carbon_tradeoff_flag_matches_signed_actual_difference(self):
        r=self.normal
        cost=r['operator_alerts']['cost']
        flagged=any(a['kind']=='carbon' for a in cost)
        self.assertEqual(flagged,r['strategy_comparisons']['cost']['emissions_change_kg'] < -.5)

    def test_no_false_outage_in_non_outage_scenario(self):
        self.assertFalse(any(a['kind']=='outage' for a in self.normal['operator_alerts']['cost']))

    def test_api_exposes_alerts_without_security_regression(self):
        code,result=route('POST','/api/optimize',{'preset':'emergency-outage'})
        self.assertEqual(code,200)
        self.assertIn('operator_alerts',result)
        self.assertTrue(result['verification']['cost']['passed'])
        code,bad=route('POST','/api/optimize',{'preset':'test','run_script':'unexpected'})
        self.assertEqual(code,400)

    def test_ui_controls_are_real_buttons_and_handlers_exist(self):
        html=(ROOT/'web/index.html').read_text(encoding='utf-8')
        js=(ROOT/'web/app.js').read_text(encoding='utf-8')
        for element in ('mission-console','operator-alerts','hour-analysis','experiment-results','machine-inspector','jump-peak','reset-controls','download-brief','save-experiment'):
            self.assertIn(f'id="{element}"',html)
        for method in ('launchMission','renderOperationalAlerts','renderExperiment','renderMachineInspector','renderHourAnalysis'):
            self.assertIn(f'function {method}',js)

if __name__=='__main__':unittest.main()
