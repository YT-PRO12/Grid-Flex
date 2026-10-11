"""Deterministic, explainable advisory signals from a computed *synthetic* dispatch.

These are observations and scenario-inspection aids, NOT control instructions.
"""


def analyze_dispatch(data, plan, comparison):
    alerts = []
    slots = plan["slots"]
    batt = data["battery"]
    for hour, slot in enumerate(slots):
        limit = slot["grid_limit_kw"]
        if limit == 0:
            alerts.append({"kind": "outage", "severity": "critical", "hour": hour,
                "title": "Utility supply unavailable", "detail": f"At {slot['time']}, the modeled grid cap is zero. The dispatch has {slot['grid_kw']:.1f} kW grid import and {slot['noncritical_shed_kw']:.1f} kW noncritical curtailment.",
                "action": "Inspect outage hour"})
        elif limit < 150 and slot["grid_kw"] / limit >= .90:
            alerts.append({"kind": "capacity", "severity": "warning", "hour": hour,
                "title": "Approaching grid import ceiling", "detail": f"At {slot['time']}, grid import is {slot['grid_kw']:.1f} of {limit:.1f} kW available ({100*slot['grid_kw']/limit:.0f}% utilized).",
                "action": "Inspect constrained hour"})
        if slot["noncritical_shed_kw"] > .05:
            alerts.append({"kind": "curtailment", "severity": "warning", "hour": hour,
                "title": "Noncritical demand curtailed", "detail": f"At {slot['time']}, {slot['noncritical_shed_kw']:.1f} kW of modeled noncritical fixed load cannot be served within the scenario constraints.",
                "action": "Inspect curtailment"})
        if slot["solar_available_kw"] - slot["solar_used_kw"] >= 8:
            alerts.append({"kind": "solar", "severity": "info", "hour": hour,
                "title": "Available solar not fully utilized", "detail": f"At {slot['time']}, {slot['solar_available_kw']-slot['solar_used_kw']:.1f} kW of modeled PV availability is not used. This is not a claim of measured curtailment.",
                "action": "Inspect solar dispatch"})
        soc_end = slot["soc_kwh"] + slot["charge_kw"]*batt["charge_efficiency"]-slot["discharge_kw"]/batt["discharge_efficiency"]
        if soc_end <= batt["min_kwh"] + batt["capacity_kwh"]*.05:
            alerts.append({"kind": "battery", "severity": "warning", "hour": hour,
                "title": "Battery near modeled reserve", "detail": f"At {slot['time']}, end-of-hour modeled state of charge is {soc_end:.1f} kWh, close to its {batt['min_kwh']:.1f} kWh minimum.",
                "action": "Inspect battery reserve"})
    if comparison["emissions_change_kg"] < -.5:
        alerts.append({"kind": "carbon", "severity": "info", "hour": None,
            "title": "Cost–carbon trade-off detected", "detail": f"This plan has {abs(comparison['emissions_change_kg']):.1f} kg more modeled grid emissions than the feasible baseline. Compare against Carbon priority.",
            "action": "Explore carbon strategy"})
    # Compact actionable feed: most severe, then distinct categories; stable
    # tie-breaking makes demonstrations and tests reproducible.
    priority = {"critical": 0, "warning": 1, "info": 2}
    alerts.sort(key=lambda a: (priority[a["severity"]], a["hour"] if a["hour"] is not None else 99, a["kind"]))
    seen = set()
    picked = []
    for entry in alerts:
        if entry["kind"] not in seen:
            picked.append(entry)
            seen.add(entry["kind"])
        if len(picked) == 5:
            break
    if not picked:
        picked = [{"kind": "stable", "severity": "ok", "hour": None,
                   "title": "No modeled threshold alerts", "detail": "No preset advisory threshold was crossed in this computed 12-hour dispatch; this is not a live safety assessment.",
                   "action": "View audit"}]
    return picked
