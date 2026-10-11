"""Deterministic sensitivity studies; neither probabilistic forecasts nor robust MILP.

The stress policy freezes jobs, battery actions and planned curtailment. Reduced
PV use is replaced by grid imports only up to the original hourly cap. No extra
shedding or battery redispatch is assumed. One-hour slots make kW numerically kWh.
"""
from copy import deepcopy
from .optimizer import solve, OptimizationError
from .verification import verify_plan, TOL


def stress_cases(data):
    h = len(data['hours'])
    profiles = [('nominal', 'Expected solar', [1.] * h),
                ('mild', '10% less solar', [.9] * h),
                ('cloudy', '25% less solar', [.75] * h),
                ('severe', '40% less solar', [.6] * h),
                ('cloud-bank', 'Afternoon cloud bank', [.4 if 6 <= t <= 9 else 1. for t in range(h)])]
    return [{'key': key, 'name': name, 'solar_kw': [round(v*f, 4) for v, f in zip(data['solar_kw'], factors)]}
            for key, name, factors in profiles]


def evaluate_stress(data, plan, cases=None):
    cases = stress_cases(data) if cases is None else cases
    results = []
    risk_counts = [0] * len(data['hours'])
    for case in cases:
        actual = deepcopy(data)
        actual['solar_kw'] = case['solar_kw']
        dispatch = deepcopy(plan)
        shortfall = []
        for t, slot in enumerate(dispatch['slots']):
            used = min(slot['solar_used_kw'], case['solar_kw'][t])
            needed = slot['base_kw'] + slot['flexible_kw'] + slot['charge_kw'] - slot['discharge_kw'] - slot['noncritical_shed_kw'] - used
            grid = min(data['grid_limit_kw'][t], max(0., needed))
            deficit = max(0., needed-grid)
            slot.update(solar_used_kw=used, solar_available_kw=case['solar_kw'][t], grid_kw=grid)
            shortfall.append(round(deficit, 4))
            if deficit > TOL:
                risk_counts[t] += 1
        # Recompute financial/environmental totals for the actual grid recourse.
        m = dispatch['metrics']
        energy = sum(s['grid_kw'] * data['tariff_inr_per_kwh'][t] for t, s in enumerate(dispatch['slots']))
        peak = max(s['grid_kw'] for s in dispatch['slots'])
        emissions = sum(s['grid_kw'] * data['carbon_kg_per_kwh'][t] for t, s in enumerate(dispatch['slots']))
        m.update(energy_cost_inr=round(energy, 2), demand_charge_inr=round(peak*data['grid_peak_rate_inr_per_kw'], 2),
                 peak_import_kw=round(peak, 2), grid_energy_kwh=round(sum(s['grid_kw'] for s in dispatch['slots']), 2),
                 solar_utilized_kwh=round(sum(s['solar_used_kw'] for s in dispatch['slots']), 2), estimated_grid_emissions_kg=round(emissions, 2))
        operating = energy + peak*data['grid_peak_rate_inr_per_kw'] + m['unserved_penalty_inr']
        total = operating + m['battery_cycle_cost_inr']
        m.update(operating_cost_excluding_wear_inr=round(operating, 2), total_cost_inr=round(total, 2),
                 objective_value_inr=round(total+plan['carbon_weight_inr_per_kg']*emissions, 2))
        audit = verify_plan(actual, dispatch)
        passed = audit['passed']
        results.append({**case, 'passed': passed, 'shortfall_by_hour_kwh': shortfall,
                        'shortfall_kwh': round(sum(shortfall), 3), 'violations': audit['violations'],
                        # A deficient plan's partial bill is not a valid feasible cost comparison.
                        'feasible_metrics': m if passed else None})
    count = sum(r['passed'] for r in results)
    return {'passed_count': count, 'tested_count': len(results), 'pass_pct': round(100*count/len(results), 1),
            'cases': results, 'hours': [{'time': time, 'failing_cases': risk_counts[t],
                'tested_cases': len(results), 'high_risk': risk_counts[t] >= 2,
                'worst_shortfall_kwh': max(r['shortfall_by_hour_kwh'][t] for r in results)}
                for t, time in enumerate(data['hours'])]}


def _verified_solve(data, strategy):
    plan = solve(data, objective=strategy)
    audit = verify_plan(data, plan)
    if not audit['passed']:
        raise OptimizationError('Intelligence plan failed independent verification')
    return plan, audit


def analyze(data, strategy='cost', existing_plan=None):
    if strategy not in ('cost', 'balanced', 'carbon'):
        raise ValueError('Unknown strategy')
    if existing_plan is None:
        current, audit = _verified_solve(data, strategy)
    else:
        try:
            expected_weight = (data.get('carbon_price_inr_per_kg',0) if strategy=='cost' else
                               max(10.,data.get('carbon_price_inr_per_kg',0)) if strategy=='balanced' else 150.)
            audit = verify_plan(data, existing_plan)
            if not audit['passed'] or existing_plan['objective'] != strategy or existing_plan['carbon_weight_inr_per_kg'] != expected_weight:
                raise ValueError('Supplied plan does not match scenario, strategy or verified constraints')
            current = deepcopy(existing_plan)
        except (KeyError, TypeError, IndexError, AttributeError) as exc:
            raise ValueError('Invalid supplied plan structure') from exc
    cases = stress_cases(data)
    # A single lower-solar deterministic solve, NOT a multi-scenario robust solve.
    lower = deepcopy(data)
    lower['solar_kw'] = [round(v*.6, 4) for v in data['solar_kw']]
    alternative = None
    try:
        plan, checked = _verified_solve(lower, strategy)
        alternative = {'plan': plan, 'verification': checked,
                       'stress': evaluate_stress(data, plan, cases)}
    except OptimizationError as exc:
        alternative = {'plan': None, 'error': str(exc)}
    free = deepcopy(data)
    free['battery_cycle_cost_inr_per_kwh'] = 0.
    no_wear, free_audit = (current, audit) if data['battery_cycle_cost_inr_per_kwh'] == 0 else _verified_solve(free, strategy)
    rate = data['battery_cycle_cost_inr_per_kwh']
    def economics(plan):
        m = plan['metrics']
        return {'operating_cost_inr': m['operating_cost_excluding_wear_inr'],
                'wear_at_common_rate_inr': round(m['battery_throughput_kwh']*rate, 2),
                'total_at_common_rate_inr': round(m['operating_cost_excluding_wear_inr']+m['battery_throughput_kwh']*rate, 2),
                'throughput_kwh': m['battery_throughput_kwh'], 'equivalent_full_cycles': m['equivalent_full_cycles'],
                'peak_import_kw': m['peak_import_kw'], 'ending_soc_kwh': m['ending_soc_kwh'],
                'jobs_completed': len(plan['jobs'])}
    return {'strategy': strategy, 'controls': data['controls'], 'expected_solar_kw': data['solar_kw'],
            'current': {'plan': current, 'verification': audit, 'stress': evaluate_stress(data, current, cases)},
            'conservative': alternative, 'conservative_solar_factor': .6,
            'battery': {'wear_rate_inr_per_kwh': rate, 'without_wear': economics(no_wear),
                        'with_wear': economics(current), 'without_wear_plan': no_wear, 'verification': free_audit,
                        'efc_formula': '(AC charge kWh + AC discharge kWh) / (2 × nominal capacity kWh)'},
            'method': 'Five deterministic stress tests; pass fraction is not a probability. Jobs, battery actions and planned curtailment stay fixed; only grid imports may increase up to their cap. High-risk hours fail at least two tests. Conservative planning assumes 60% of expected PV; it is not robust optimization.',
            'battery_disclosure': 'Illustrative linear AC-throughput wear allowance, not a cash tariff or manufacturer-validated lifetime model. EFC is an approximate AC-throughput proxy; temperature, calendar aging and depth-of-discharge effects are not modeled.'}
