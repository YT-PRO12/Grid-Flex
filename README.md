# Grid Flex

### Industrial renewable energy, carbon-aware optimization and resilience decision intelligence

Grid Flex is a **working industrial energy planning prototype** for a synthetic factory with solar PV, battery storage, limited grid imports and production deadlines. The Python/SciPy HiGHS **mixed-integer linear program (MILP)** coordinates machine start times, grid energy, solar use, battery charge/discharge and hourly load. It is **not a live SCADA platform**, does not control physical equipment, and its results are **scenario-specific modeled estimates**, not proven factory savings or real-world emissions measurements.

## Ready-to-demo capabilities

- **Premium industrial operations control room:** desktop-first power bus/digital twin, replay controls, tariff and physical dispatch visualizations, timeline, actual job schedules, comparison panel and CSV export.
- **Cost–carbon decision laboratory (new P0):** three separately solved MILP plans: cost priority, balanced (at least ₹10/kg synthetic carbon shadow cost) and carbon priority (₹150/kg). Switch plans instantly; all telemetry, machine schedules, KPIs, constraints and explanations update from the actual selected solution. SVG frontier shows *modeled* cost/emissions candidates, not real measurements.
- **Emergency response planning (new P0):** simulated total grid outage from 16:00 to 18:00; changes grid availability to zero for two slots. The optimizer can curtail at most 30% of synthetic fixed demand (predeclared noncritical fraction) with a large penalty, while preserving the 70% critical fixed-load floor and scheduling the five production jobs by their deadlines. No physical switching is performed.
- **Independent mathematical audit (new P0):** post-solve verifier checks serialized schedule job windows, durations and counts, hourly power balance, grid and solar limits, battery exclusivity, state-of-charge bounds/reserve, load shedding allowance, and reported totals. Results appear on-screen per selected strategy and fail closed on constraint violations.
- **AWS Lambda + API Gateway + DynamoDB integration contract (new P0):** serverless deployment template, persistence contract tests, TTL for stored runs, health/status disclosure and a **live cloud verification script** that requires real deployed resources and AWS credentials. **Cloud deployment and live AWS verification have NOT been performed in this workspace.**
- Seven scenarios: grid stress, normal grid, cloudy day, high tariff, production surge, battery derating and emergency grid outage. Interactive controls for solar, tariff, demand, battery capacity, evening grid cap and optional carbon shadow cost.

## Interactive operator workspace — latest upgrade

The app is intentionally **functional, not just animated**. Its new buttons drive the same computed optimization results displayed in the dashboards:

1. **Four instant operating missions:** launch normal production, solar shortfall, evening tariff shock or a two-hour blackout. Each mission resets the scenario controls to a defined, reproducible configuration, runs the solver and opens the energy command room. **Reset all inputs** runs the default baseline scenario again.
2. **Solver-derived operator advisories:** see hour-specific grid-cap pressure, simulated outages, noncritical demand curtailment, battery reserve, unused modeled PV availability and negative cost–carbon trade-offs, where applicable. Click an advisory to jump to its actual computed hour or to select Carbon priority. No alerts claim live monitoring.
3. **Hour inspector and peak jump:** the microgrid replay and **Jump to peak hour** button update an hourly physical breakdown of grid headroom, unused PV, battery activity and noncritical curtailment.
4. **Clickable production explorer:** click machine rows, schedule cells or active-machine buttons to inspect scheduled hours, total energy, movement from baseline and deadline slack; the **View start hour** action navigates to the grid dispatch at that time.
5. **Pinned A/B experiment lab:** **Pin current run**, change inputs or strategy and rerun to compare both solved results side-by-side. **Restore pinned inputs & run** reproduces the selected reference controls, while **Download decision brief** exports a markdown report of actual solver metrics, advisory evidence, audit summary and synthetic-data disclaimers. Pinned runs live **only in the current browser session**, not the AWS table or persistent storage.
6. **Clear cursor affordances:** noninteractive labels use an arrow; interactive controls use a pointer. Keyboard focus is visible.

**Quick demo:** Load the page → Pin current run → click **Solar shortfall** → review the A/B comparisons → click a machine to inspect its schedule → click **Grid blackout** → inspect outage alerts and the mathematical audit → download a decision brief.

## Final engineering additions

- **Forecast Risk:** five deterministic solar profiles (expected, −10%, −25%, −40%, and an afternoon cloud bank). Analyze the exact selected schedule; production jobs, battery actions and planned curtailment stay fixed. Grid imports can replace missing PV up to the hourly cap. Report constraint pass counts, percentages, hourly deficits and a separately solved 60%-solar alternative. Pass fractions are **not probabilities** and the alternative is **not robust optimization**. Compare both policies at the same expected solar assumptions; failed stress cases do not receive misleading comparable costs.
- **Battery economics:** configurable ₹0–20/kWh AC-throughput allowance, including zero to disable it. Approximate equivalent full cycles = (AC charging + AC discharging kWh)/(2 × nominal battery kWh). Compare a solve with wear against one without wear and value both at the same chosen rate. The panel includes operating cost, estimated wear, total cost, peak, production completion and hourly dispatch differences. It is an illustrative aging proxy, not a manufacturer lifetime prediction.
- **Judge workflow:** open the app → pin a reference → run a mission or adjust inputs → inspect cost/carbon strategies → click **Analyze forecast & battery** → inspect solar profiles and battery economics → inspect constraint audit → download the decision brief or CSV. Set wear to ₹8/kWh, rerun and analyze to see a stronger sensitivity example. Default ₹0.15 preserves the original assumptions.
- Analyses are on demand to avoid unnecessary solves. Changing inputs/strategy invalidates analysis; controls are locked during a solve and reports remain tied to submitted inputs. Decision briefs include current analysis when available. Charts/schedule can still toggle baseline; summary KPIs and analysis concern the selected optimized strategy.

See `docs/FINAL_VERIFICATION.md` for the final test result and boundaries.

## Fast local start

Use Python 3.12 (verified locally with 3.12.14). In Windows PowerShell:

```powershell
python -m pip install -r requirements.txt
powershell -ExecutionPolicy Bypass -File .\start-local.ps1
```

Go to **http://localhost:8000**. Or use `python server.py` and manually open the URL. The API and UI are served on the same port; no JavaScript build step is necessary.

```powershell
python -m unittest discover -s tests -v
```

## API

| Method | Route | Function |
| --- | --- | --- |
| GET | `/api/health` | Accurate runtime and storage **configuration** status; never pretends AWS integration is verified |
| GET | `/api/scenario` | Synthetic baseline fixture |
| POST | `/api/optimize` | Validated scenario parameters; returns three MILP plans, comparison, solver-derived operator alerts, explanations, constraint audit and run ID |
| POST | `/api/intelligence` | Same scenario controls, strategy (`cost`, `balanced`, `carbon`), and optional verified `plan`; returns solar stress/conservative and wear comparisons |
| GET | `/api/history` | Recent runs in ephemeral local memory or configured DynamoDB |

Example:

```json
{"preset":"emergency-outage","solar_scale":1,"tariff_multiplier":1,"carbon_price":0,"demand_scale":1,"battery_capacity":72,"evening_grid_cap":86,"battery_wear_cost":0.15}
```

### Reproducible synthetic demonstrations

All five production jobs complete within deadlines in the illustrated cases below.

| Grid-stress optimization strategy | Modeled operating cost | Modeled grid emissions |
| --- | ---: | ---: |
| Cost priority | ₹6,942.91 | 314.95 kg |
| Balanced | ₹6,950.69 | 313.76 kg |
| Carbon priority | ₹7,773.07 | 299.96 kg |

Actual values may vary slightly with solver versions/tolerances. **Carbon priority reduces modeled emissions at increased modeled financial cost.** This is not a verified emissions saving at any real factory.

In the illustrative **emergency** scenario, modeled grid import is **0 kWh during the two-hour utility outage**, **2.00 kWh of noncritical fixed demand** is curtailed, the **70% critical fixed-load floor remains supplied**, and **5/5 production jobs** are scheduled by deadline. These are synthetic optimization results with no claim of deployment or safety approval.

## AWS deployment and real verification

AWS integration is prepared, **not live-verified**. Read [docs/AWS_DEPLOY_VERIFY.md](docs/AWS_DEPLOY_VERIFY.md) for the smallest reliable deployment/read-back workflow. `scripts/verify_live_aws.py` calls your deployed API Gateway endpoint, triggers a real optimization, and uses **AWS DynamoDB `GetItem`** to confirm its result was written by Lambda. It exits nonzero if verification fails. It does not access credentials from this archive or modify AWS infrastructure itself.

The backend is a Python Lambda app with SciPy and DynamoDB. The frontend remains a static site to host separately. For static hosting, append `?api=https://YOUR_REAL_API_BASE` to the frontend URL. Configure the exact frontend origin using the SAM `AllowedOrigin` parameter; the included infrastructure is a public, rate-limited *demonstration template*. CORS is not authentication.

## Main files

| Path | Responsibility |
| --- | --- |
| `engine/optimizer.py` | MILP model and three-strategy comparison |
| `engine/intelligence.py` | Deterministic solar stress and battery-wear sensitivity |
| `engine/verification.py` | Independent post-solve constraint and financial-total audit |
| `engine/diagnostics.py` | Explainable synthetic operational advisories derived from solved hourly dispatch |
| `engine/scenario.py` | Synthetic fixtures, seven presets and validation |
| `app.py`, `server.py` | Unified local/Lambda HTTP API |
| `web/index.html`, `web/styles.css`, `web/app.js` | Premium interactive operations control room |
| `aws/template.yaml` | AWS SAM deployment template (not deployed) |
| `scripts/verify_live_aws.py` | Actual AWS API + DynamoDB read-back check |
| `tests/` | Mathematical, UI API contract, AWS persistence mock and regression tests |
| `docs/FINAL_VERIFICATION.md` | Final verification evidence and deployment limits |

## Safety and transparency

- Grid Flex uses synthetic tariffs, solar predictions, demand, equipment and emission factors. No live sensors or utility contracts are connected.
- The simulated outage is **not a protection-system recommendation** and may not be used for operational switching, isolation or actual safety-critical load shedding.
- A MILP audit proves **internal mathematical consistency**, not physical site feasibility or grid code compliance.
- Emissions comparisons use synthetic time-varying grid intensity, not a validated marginal-emissions forecast.
- Users must not infer that the public AWS API exists or that AWS credits are consumed simply because the template is present.
