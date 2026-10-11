"""Deterministic *synthetic* industrial microgrid fixtures and strict controls."""
from copy import deepcopy

HOURS = [f"{hour:02d}:00" for hour in range(8, 20)]
DEFAULT = {
    "name": "Industrial Flexibility — Solar + Battery + Grid",
    "site": "Synthetic medium-size manufacturing facility (India)",
    "hours": HOURS,
    "base_kw": [32, 34, 37, 39, 40, 42, 46, 49, 50, 47, 43, 39],
    "solar_kw": [8, 18, 33, 53, 68, 77, 72, 55, 35, 18, 4, 0],
    "tariff_inr_per_kwh": [7, 7, 7, 6, 6, 7, 9, 11, 13, 14, 13, 10],
    "grid_limit_kw": [165, 165, 165, 165, 165, 165, 86, 86, 86, 86, 86, 86],
    "emergency": False,
    "max_sheddable_share": 0.0,
    "unserved_energy_penalty_inr_per_kwh": 2500.0,
    "carbon_kg_per_kwh": [0.69, 0.69, 0.68, 0.65, 0.64, 0.65, 0.74, 0.81, 0.84, 0.86, 0.83, 0.78],
    "battery": {"capacity_kwh": 72, "initial_kwh": 26, "min_kwh": 8, "max_charge_kw": 27, "max_discharge_kw": 27, "charge_efficiency": 0.94, "discharge_efficiency": 0.94},
    "jobs": [
        {"id":"J1", "name":"CNC milling", "power_kw":29, "duration_h":3, "earliest":0, "deadline":9, "color":"#54d5cc"},
        {"id":"J2", "name":"Industrial dryer", "power_kw":37, "duration_h":3, "earliest":1, "deadline":11, "color":"#a8a4ff"},
        {"id":"J3", "name":"Chiller pre-cooling", "power_kw":24, "duration_h":2, "earliest":0, "deadline":6, "color":"#69afff"},
        {"id":"J4", "name":"Process water pump", "power_kw":28, "duration_h":2, "earliest":3, "deadline":12, "color":"#ffc36d"},
        {"id":"J5", "name":"Packaging conveyor", "power_kw":21, "duration_h":3, "earliest":5, "deadline":12, "color":"#ff8ba7"},
    ],
    "grid_peak_rate_inr_per_kw": 85,
    "battery_cycle_cost_inr_per_kwh": 0.15,
    "data_notice": "All loads, forecasts, tariffs and emissions factors are illustrative synthetic values; not measured or utility-provided data."
}


def _check_range(name, value, low, high):
    from math import isfinite
    if (not isinstance(value, (int,float)) or isinstance(value,bool)
            or not isfinite(value) or not low <= value <= high):
        raise ValueError(f"{name} must be a finite number between {low} and {high}")


def scenario(preset="grid-stress", solar_scale=1.0, tariff_multiplier=1.0,
             initial_soc=None, carbon_price=0.0, demand_scale=1.0,
             battery_capacity=72.0, evening_grid_cap=86.0, battery_wear_cost=0.15):
    presets=("grid-stress", "normal", "cloudy", "high-tariff", "production-surge", "battery-limited", "emergency-outage")
    if preset not in presets:
        raise ValueError("Unknown scenario. Choose: " + ", ".join(presets))
    for name,value,low,high in (
        ("battery_wear_cost",battery_wear_cost,0,20),
        ("solar_scale",solar_scale,.25,1.5),
        ("tariff_multiplier",tariff_multiplier,.5,2.0),
        ("carbon_price",carbon_price,0,15),
        ("demand_scale",demand_scale,.75,1.35),
        ("battery_capacity",battery_capacity,36,120),
        ("evening_grid_cap",evening_grid_cap,60,165)):
        _check_range(name,value,low,high)
    data=deepcopy(DEFAULT)
    data["battery_cycle_cost_inr_per_kwh"] = battery_wear_cost
    if preset == "normal":
        data["grid_limit_kw"] = [165]*12
    else:
        data["grid_limit_kw"] = [165]*6 + [evening_grid_cap]*6
    if preset == "emergency-outage":
        # Simulated two-hour total grid outage, 16:00–18:00. Emergency
        # shedding may ONLY apply to a limited noncritical fixed-load share.
        data["grid_limit_kw"][8:10] = [0, 0]
        data["emergency"] = True
        data["max_sheddable_share"] = .30
        data["outage_hours"] = [data["hours"][8], data["hours"][9]]
    if preset == "cloudy":
        data["solar_kw"] = [round(x*.5,2) for x in data["solar_kw"]]
    if preset == "high-tariff":
        data["tariff_inr_per_kwh"] = [v*(1.5 if t>=6 else 1) for t,v in enumerate(data["tariff_inr_per_kwh"])]
    if preset == "production-surge":
        demand_scale *= 1.16
    if preset == "battery-limited":
        battery_capacity = min(battery_capacity,40)
    data["solar_kw"] = [round(x*solar_scale,2) for x in data["solar_kw"]]
    data["base_kw"] = [round(x*demand_scale,2) for x in data["base_kw"]]
    for job in data["jobs"]:
        job["power_kw"] = round(job["power_kw"]*demand_scale,2)
    data["tariff_inr_per_kwh"] = [round(x*tariff_multiplier,2) for x in data["tariff_inr_per_kwh"]]
    data["battery"]["capacity_kwh"] = battery_capacity
    data["battery"]["max_charge_kw"] = min(27,battery_capacity*.375)
    data["battery"]["max_discharge_kw"] = min(27,battery_capacity*.375)
    if initial_soc is not None:
        _check_range("initial_soc",initial_soc,8,battery_capacity)
        data["battery"]["initial_kwh"] = initial_soc
    else:
        data["battery"]["initial_kwh"] = min(26,battery_capacity)
    data["carbon_price_inr_per_kg"] = carbon_price
    data["preset"] = preset
    data["controls"] = {"solar_scale":solar_scale,"tariff_multiplier":tariff_multiplier,
                         "demand_scale":round(demand_scale,4),"battery_capacity":battery_capacity,
                         "evening_grid_cap":evening_grid_cap,"carbon_price":carbon_price,"battery_wear_cost":battery_wear_cost}
    return data
