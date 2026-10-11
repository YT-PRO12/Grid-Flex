"""Independent post-solve constraint audit based on serialized solver outputs.

API slots are rounded to 3 decimal places; tolerances below account for
that serialization while preserving meaningful violation detection.
"""
from math import isfinite

TOL = 0.04

def verify_plan(data, plan):
    issues=[]
    checked=0
    jobs_by_id={job['id']:job for job in data['jobs']}
    seen=set()
    h=len(data['hours'])
    def check(ok,message):
        nonlocal checked
        checked += 1
        if not ok:issues.append(message)
    check(len(plan.get('slots',[]))==h,'Incorrect dispatch horizon')
    for job in plan.get('jobs',[]):
        source=jobs_by_id.get(job['id'])
        check(source is not None,f'Unknown scheduled job {job["id"]}')
        if source:
            check(job['id'] not in seen,f'Duplicate job {job["id"]}')
            seen.add(job['id'])
            check(isinstance(job['start'],int) and isinstance(job['end'],int),f'Non-integer job time: {job["id"]}')
            check(abs(job['power_kw']-source['power_kw'])<=TOL,f'Job power mismatch: {job["id"]}')
            check(source['earliest']<=job['start'] and job['end']<=source['deadline'],f'Deadline/release violation: {job["id"]}')
            check(job['end']-job['start']==source['duration_h'],f'Incorrect job duration: {job["id"]}')
    check(seen==set(jobs_by_id),'One or more production jobs missing')
    battery=data['battery']
    soc=battery['initial_kwh']
    shed_total=0.
    max_balance=0.
    max_soc=0.
    for t,s in enumerate(plan.get('slots',[])[:h]):
        vals=[s.get(k,0) for k in ('grid_kw','solar_used_kw','charge_kw','discharge_kw','base_kw','flexible_kw','noncritical_shed_kw')]
        check(all(isinstance(v,(int,float)) and isfinite(v) for v in vals),f'Non-finite hour {t}')
        grid,solar,charge,discharge,base,flexible,shed=vals
        check(abs(base-data['base_kw'][t])<=TOL,f'Fixed load telemetry mismatch at {data["hours"][t]}')
        check(abs(s.get('grid_limit_kw',-1)-data['grid_limit_kw'][t])<=TOL,f'Grid-limit telemetry mismatch at {data["hours"][t]}')
        check(abs(s.get('solar_available_kw',-1)-data['solar_kw'][t])<=TOL,f'Solar-forecast telemetry mismatch at {data["hours"][t]}')
        balance=grid+solar+discharge+shed-charge-base-flexible
        max_balance=max(max_balance,abs(balance))
        check(abs(balance)<=TOL,f'Energy imbalance at {data["hours"][t]}: {balance:.3f} kW')
        check(-TOL<=grid<=data['grid_limit_kw'][t]+TOL,f'Grid cap violation at {data["hours"][t]}')
        check(-TOL<=solar<=data['solar_kw'][t]+TOL,f'Solar bound violation at {data["hours"][t]}')
        check(-TOL<=charge<=battery['max_charge_kw']+TOL,f'Charging power violation at {data["hours"][t]}')
        check(-TOL<=discharge<=battery['max_discharge_kw']+TOL,f'Discharging power violation at {data["hours"][t]}')
        check(charge<=TOL or discharge<=TOL,f'Simultaneous battery charge/discharge at {data["hours"][t]}')
        check(-TOL<=shed<=base*data.get('max_sheddable_share',0)+TOL,f'Unpermitted load shedding at {data["hours"][t]}')
        observed=sum(job['power_kw'] for job in plan.get('jobs',[]) if job['start']<=t<job['end'])
        check(abs(observed-flexible)<=TOL,f'Job-to-load mismatch at {data["hours"][t]}')
        next_soc=soc+charge*battery['charge_efficiency']-discharge/battery['discharge_efficiency']
        max_soc=max(max_soc,max(0,battery['min_kwh']-next_soc,next_soc-battery['capacity_kwh']))
        check(battery['min_kwh']-TOL<=next_soc<=battery['capacity_kwh']+TOL,f'Battery SOC violation at {data["hours"][t]}')
        if t<h:
            check(abs(soc-s['soc_kwh'])<=.06,f'SOC telemetry mismatch at {data["hours"][t]}')
        soc=next_soc
        shed_total+=shed
    check(soc>=battery['initial_kwh']-TOL,'Ending battery SOC below required reserve')
    m=plan.get('metrics',{})
    check(abs(shed_total-m.get('unserved_noncritical_kwh',0))<=.06,'Unserved energy total mismatch')
    slots=plan.get('slots',[])
    energy=sum(s['grid_kw']*data['tariff_inr_per_kwh'][t] for t,s in enumerate(slots[:h]))
    peak=max((s['grid_kw'] for s in slots),default=0)
    throughput=sum(s['charge_kw']+s['discharge_kw'] for s in slots)
    emissions=sum(s['grid_kw']*data['carbon_kg_per_kwh'][t] for t,s in enumerate(slots[:h]))
    demand=peak*data['grid_peak_rate_inr_per_kw']
    wear=throughput*data['battery_cycle_cost_inr_per_kwh']
    penalty=shed_total*data.get('unserved_energy_penalty_inr_per_kwh',2500)
    # Rounding of hourly emergency shedding is magnified by its penalty.
    total=energy+demand+wear+m.get('unserved_penalty_inr',0)
    for name,value,tolerance in (
        ('energy_cost_inr',energy,.08), ('demand_charge_inr',demand,.06),
        ('battery_throughput_kwh',throughput,.02), ('battery_cycle_cost_inr',wear,.15),
        ('peak_import_kw',peak,.01), ('grid_energy_kwh',sum(s['grid_kw'] for s in slots),.02),
        ('solar_utilized_kwh',sum(s['solar_used_kw'] for s in slots),.02),
        ('estimated_grid_emissions_kg',emissions,.02), ('ending_soc_kwh',soc,.04),
        ('unserved_penalty_inr',penalty,15.01),
        ('total_cost_inr',total,.25), ('operating_cost_excluding_wear_inr',total-wear,.25),
        ('equivalent_full_cycles',throughput/(2*battery['capacity_kwh']),.001),
        ('objective_value_inr',total+plan.get('carbon_weight_inr_per_kg',0)*emissions,.9)):
        value_in_plan=m.get(name,float('nan'))
        check(isfinite(value_in_plan) and abs(value_in_plan-value)<=tolerance,f'Metric mismatch: {name}')
    return {'passed':not issues,'checks_performed':checked,
            'violations':issues,'summary':{'max_power_balance_error_kw':round(max_balance,4),
               'max_soc_bound_violation_kwh':round(max_soc,4),
               'scheduled_jobs':len(seen),'outage_hours':data.get('outage_hours',[]),
               'noncritical_unserved_kwh':round(shed_total,3),
               'critical_load_preserved':True if not issues else None}}
