"""True mixed-integer linear program for hourly production + battery dispatch.

Works with scipy.optimize.milp/HiGHS. All energy units are kWh per 1-hour slot.
No infeasible baseline is ever counted as a saving.
"""
from math import isfinite
from time import perf_counter
import numpy as np
from scipy.optimize import Bounds, LinearConstraint, milp
from scipy.sparse import coo_matrix

class OptimizationError(Exception):
    pass


def _build_problem(data, *, baseline=False, objective="cost"):
    h = len(data["hours"])
    jobs = data["jobs"]
    battery = data["battery"]
    varnames, lower, upper, integral, coeff = [], [], [], [], []
    def variable(label,lo=0.0,hi=np.inf,integer=0,cost=0.0):
        i = len(varnames)
        varnames.append(label); lower.append(lo); upper.append(hi)
        integral.append(integer); coeff.append(cost)
        return i

    if objective not in ("cost", "balanced", "carbon"):
        raise OptimizationError("Unknown objective")
    # Carbon weighting is an explicit illustrative shadow price, not a
    # claim of carbon-credit valuation or calibrated emissions forecasting.
    carbon_weight = (data.get("carbon_price_inr_per_kg", 0) if objective=="cost"
        else max(10.0,data.get("carbon_price_inr_per_kg",0)) if objective=="balanced"
        else 150.0)
    starts = {}
    for j,job in enumerate(jobs):
        if job["duration_h"] <= 0 or job["earliest"] < 0 or job["deadline"] > h:
            raise OptimizationError("Invalid job schedule window")
        possible = range(job["earliest"], job["deadline"]-job["duration_h"]+1)
        if not possible:
            raise OptimizationError("Job has no feasible start window")
        for s in possible:
            # Baseline minimizes earliest start time first, then grid cost.
            starts[(j,s)] = variable(f"start_{j}_{s}", hi=1, integer=1, cost=100000*s if baseline else 0)
    grid = [variable(f"grid_{t}", hi=float(data["grid_limit_kw"][t]), cost=float(data["tariff_inr_per_kwh"][t]) + carbon_weight*float(data["carbon_kg_per_kwh"][t])) for t in range(h)]
    solar = [variable(f"solar_{t}", hi=float(data["solar_kw"][t])) for t in range(h)]
    charge = [variable(f"charge_{t}", hi=battery["max_charge_kw"],cost=data["battery_cycle_cost_inr_per_kwh"]) for t in range(h)]
    discharge = [variable(f"discharge_{t}", hi=battery["max_discharge_kw"],cost=data["battery_cycle_cost_inr_per_kwh"]) for t in range(h)]
    shed = [variable(f"noncritical_shed_{t}",hi=float(data["base_kw"][t])*float(data.get("max_sheddable_share",0)),
                     cost=float(data.get("unserved_energy_penalty_inr_per_kwh",2500))) for t in range(h)]
    # A mode bit ensures charging and discharging cannot occur simultaneously.
    mode = [variable(f"battery_mode_{t}",hi=1,integer=1) for t in range(h)]
    soc = [variable(f"soc_{t}",lo=battery["min_kwh"],hi=battery["capacity_kwh"]) for t in range(h+1)]
    peak = variable("peak_grid_import_kw",cost=data["grid_peak_rate_inr_per_kw"])
    rows,cols,vals,bl,bu = [],[],[],[],[]
    def constraint(items,lo=-np.inf,hi=np.inf):
        r = len(bl)
        for k,v in items.items():
            if v:
                rows.append(r); cols.append(k); vals.append(float(v))
        bl.append(float(lo));bu.append(float(hi))
    for j,_ in enumerate(jobs):
        constraint({idx:1 for (jj,_),idx in starts.items() if jj==j},lo=1,hi=1)
    for t in range(h):
        # power supply = inflexible and scheduled flexible load
        terms = {grid[t]:1,discharge[t]:1,solar[t]:1,charge[t]:-1,shed[t]:1}
        for (j,s),idx in starts.items():
            if s <= t < s+jobs[j]["duration_h"]:
                terms[idx] = -jobs[j]["power_kw"]
        constraint(terms,lo=data["base_kw"][t],hi=data["base_kw"][t])
        constraint({soc[t+1]:1,soc[t]:-1,charge[t]:-battery["charge_efficiency"],discharge[t]:1/battery["discharge_efficiency"]},lo=0,hi=0)
        constraint({charge[t]:1,mode[t]:-battery["max_charge_kw"]},hi=0)
        constraint({discharge[t]:1,mode[t]:battery["max_discharge_kw"]},hi=battery["max_discharge_kw"])
        constraint({grid[t]:1,peak:-1},hi=0)
    constraint({soc[0]:1},lo=battery["initial_kwh"],hi=battery["initial_kwh"])
    # End at least at initial SOC; prevents claiming savings by simply emptying the battery.
    constraint({soc[-1]:1},lo=battery["initial_kwh"])
    A = coo_matrix((vals,(rows,cols)),shape=(len(bl),len(varnames))).tocsr()
    return dict(names=varnames,c=np.asarray(coeff),integrality=np.asarray(integral),bounds=Bounds(lower,upper),constraints=LinearConstraint(A,bl,bu),starts=starts,grid=grid,solar=solar,charge=charge,discharge=discharge,soc=soc,peak=peak,shed=shed,objective=objective,carbon_weight=carbon_weight)


def solve(data, baseline=False, time_limit=5, objective="cost"):
    p = _build_problem(data,baseline=baseline,objective=objective)
    start_time=perf_counter()
    result = milp(c=p["c"], integrality=p["integrality"], bounds=p["bounds"],constraints=p["constraints"], options={"time_limit":time_limit,"mip_rel_gap":0.0001})
    duration=round((perf_counter()-start_time)*1000,1)
    if result.x is None:
        raise OptimizationError(f"No feasible schedule found (solver status {result.status}). Adjust grid constraints or workload.")
    if result.status not in (0,1):
        raise OptimizationError(f"Solver failed with status {result.status}")
    x=result.x
    def v(index):return round(max(0.0,float(x[index])),3)
    plan=[]
    for j,job in enumerate(data["jobs"]):
        chosen=[s for (jj,s),idx in p["starts"].items() if jj==j and x[idx]>0.5]
        if len(chosen)!=1:raise OptimizationError("Solver produced invalid job scheduling result")
        begin=chosen[0]
        plan.append({"id":job["id"],"name":job["name"],"start":begin,"end":begin+job["duration_h"],"power_kw":job["power_kw"],"deadline":job["deadline"],"color":job["color"]})
    slots=[]
    for t in range(len(data["hours"])):
        flexible=sum(job["power_kw"] for job in plan if job["start"]<=t<job["end"])
        slots.append({"time":data["hours"][t],"grid_kw":v(p["grid"][t]),"solar_used_kw":v(p["solar"][t]),"solar_available_kw":data["solar_kw"][t],"charge_kw":v(p["charge"][t]),"discharge_kw":v(p["discharge"][t]),"soc_kwh":v(p["soc"][t]),"base_kw":data["base_kw"][t],"noncritical_shed_kw":v(p["shed"][t]),"flexible_kw":flexible,"tariff":data["tariff_inr_per_kwh"][t],"grid_limit_kw":data["grid_limit_kw"][t]})
    energy_cost=sum(float(x[p["grid"][t]])*data["tariff_inr_per_kwh"][t] for t in range(len(slots)))
    demand_cost=max(float(x[k]) for k in p["grid"])*data["grid_peak_rate_inr_per_kw"]
    emissions=sum(float(x[p["grid"][t]])*data["carbon_kg_per_kwh"][t] for t in range(len(slots)))
    battery_throughput=sum(float(x[p["charge"][t]])+float(x[p["discharge"][t]]) for t in range(len(slots)))
    battery_cycle_cost=battery_throughput*data["battery_cycle_cost_inr_per_kwh"]
    unserved=sum(float(x[k]) for k in p["shed"])
    unserved_penalty=unserved*data.get("unserved_energy_penalty_inr_per_kwh",2500)
    return {"type":"first-feasible-earliest-baseline" if baseline else "optimized-milp","status":"optimal" if result.status==0 else "feasible-time-limited","solve_ms":duration,"objective":objective,"carbon_weight_inr_per_kg":p["carbon_weight"],"solver":"SciPy HiGHS mixed-integer linear programming","jobs":plan,"slots":slots,"metrics":{"energy_cost_inr":round(energy_cost,2),"demand_charge_inr":round(demand_cost,2),"battery_cycle_cost_inr":round(battery_cycle_cost,2),"battery_throughput_kwh":round(battery_throughput,2),"equivalent_full_cycles":round(battery_throughput/(2*data["battery"]["capacity_kwh"]),4),"operating_cost_excluding_wear_inr":round(energy_cost+demand_cost+unserved_penalty,2),"objective_value_inr":round(energy_cost+demand_cost+battery_cycle_cost+unserved_penalty+p["carbon_weight"]*emissions,2),"total_cost_inr":round(energy_cost+demand_cost+battery_cycle_cost+unserved_penalty,2),"unserved_noncritical_kwh":round(unserved,3),"unserved_penalty_inr":round(unserved_penalty,2),"critical_load_served_pct":100.0,"peak_import_kw":round(max(float(x[k]) for k in p["grid"]),2),"grid_energy_kwh":round(sum(float(x[k]) for k in p["grid"]),2),"solar_utilized_kwh":round(sum(float(x[k]) for k in p["solar"]),2),"estimated_grid_emissions_kg":round(emissions,2),"ending_soc_kwh":v(p["soc"][-1])}}


def explain(data, baseline, optimized):
    evidence=[]
    solar=data["solar_kw"]
    tariffs=data["tariff_inr_per_kwh"]
    for job in optimized["jobs"]:
        original=next(j for j in baseline["jobs"] if j["id"]==job["id"])
        start=job["start"]
        end=job["end"]
        if start!=original["start"]:
            sun=sum(solar[start:end])/max(1,end-start)
            rate=sum(tariffs[start:end])/max(1,end-start)
            direction="later" if start>original["start"] else "earlier"
            evidence.append({"kind":"schedule","title":f"{job['name']} shifted {direction}",
                "detail":f"Start {data['hours'][original['start']]} → {data['hours'][start]}; {job['power_kw']} kW, {job['end']-job['start']} h. New window: mean solar availability {sun:.1f} kW and tariff ₹{rate:.1f}/kWh. The global solver selected this under all constraints; the two values are context, not proof of one causal factor.",
                "job_id":job["id"]})
    charges=[s for s in optimized["slots"] if s["charge_kw"]>0.1]
    discharges=[s for s in optimized["slots"] if s["discharge_kw"]>0.1]
    if charges:
        evidence.append({"kind":"battery","title":"Battery charging scheduled",
            "detail":f"Charging occurs in {len(charges)} hourly slots, totaling {sum(s['charge_kw'] for s in charges):.1f} kWh of input. Charge/discharge exclusivity and state-of-charge bounds were enforced."})
    if discharges:
        evidence.append({"kind":"battery","title":"Battery discharging scheduled",
            "detail":f"Discharging occurs in {len(discharges)} slots, delivering {sum(s['discharge_kw'] for s in discharges):.1f} kWh within the battery and grid constraints."})
    tight=[s for s in optimized["slots"] if s["grid_limit_kw"]-s["grid_kw"]<0.1]
    if tight:
        evidence.append({"kind":"constraint","title":"Grid import limit active",
            "detail":"The model reaches its import cap at "+", ".join(s["time"] for s in tight)+". The cap is a binding modeled operational constraint."})
    if not evidence:
        evidence.append({"kind":"result","title":"All production requirements satisfied",
             "detail":"All jobs completed within release/deadline windows, with hourly grid and battery constraints enforced."})
    return evidence


def _comparison(baseline, optimized):
    a,b = baseline["metrics"],optimized["metrics"]
    savings = round(a["total_cost_inr"]-b["total_cost_inr"],2)
    return {"estimated_cost_saving_inr":savings,
            "estimated_cost_saving_pct":round(100*savings/a["total_cost_inr"],1) if a["total_cost_inr"] else 0,
            "peak_reduction_kw":round(a["peak_import_kw"]-b["peak_import_kw"],2),
            "emissions_change_kg":round(a["estimated_grid_emissions_kg"]-b["estimated_grid_emissions_kg"],2),
            "shed_change_kwh":round(a["unserved_noncritical_kwh"]-b["unserved_noncritical_kwh"],3)}


def optimize(data):
    from .verification import verify_plan
    from .diagnostics import analyze_dispatch
    baseline=solve(data,baseline=True)
    # Three genuinely different MILP objective weights, sharing the same
    # production windows, physical assets, and outage constraints.
    plans={objective:solve(data,objective=objective) for objective in ("cost","balanced","carbon")}
    verified={"baseline":verify_plan(data,baseline)}
    for objective,plan in plans.items():
        verified[objective]=verify_plan(data,plan)
    if not all(v["passed"] for v in verified.values()):
        raise OptimizationError("Independent physical-constraint verification failed")
    optimized=plans["cost"]
    strategies=[{"key":name,"name":{"cost":"Cost priority","balanced":"Balanced","carbon":"Carbon priority"}[name],
                 "carbon_weight_inr_per_kg":plans[name]["carbon_weight_inr_per_kg"],
                 "metrics":plans[name]["metrics"],"verification":verified[name]["summary"]}
                for name in ("cost","balanced","carbon")]
    return {"scenario":data,"baseline":baseline,"optimized":optimized,
            "strategy_plans":plans,"strategy_comparisons":{name:_comparison(baseline,plan) for name,plan in plans.items()},
            "strategy_explanations":{name:explain(data,baseline,plan) for name,plan in plans.items()},
            "frontier":strategies,"comparison":_comparison(baseline,optimized),
            "explanations":explain(data,baseline,optimized),
            "verification":verified,
            "operator_alerts":{name:analyze_dispatch(data,plan,_comparison(baseline,plan)) for name,plan in plans.items()},
            "disclosure":"Synthetic planning exercise; cost, tariffs and emissions factors are illustrative. Carbon weights are modeled shadow prices, not measured environmental impact. Emergency shedding affects only declared noncritical fixed demand; physical equipment is never controlled. Baseline and all strategies obey the same operational constraints."}
