# Grid Flex — final verification

## Local result

- Original baseline: **37/37 passed** before edits.
- Final consolidated Python regression suite: **52/52 passed** in 36.393 seconds (37 existing + 15 new).
- Runtime: Python 3.12.14, NumPy 2.3.5, SciPy 1.17.0. JavaScript syntax checks passed.
- Real local HTTP smoke test passed: health, optimization, three strategy audits, exact-plan intelligence and battery sensitivity.
- Chromium automation passed at 1440px desktop and 390px mobile: optimization, selected-plan identity, stress selection, battery sensitivity, strategy switching, emergency scenario, pin/restore, machine/alert/hour/peak/playback navigation, CSV and decision-brief downloads, keyboard focus and cursor behavior.
- No JavaScript page errors or page-level horizontal overflow. Analysis tables scroll locally on narrow screens. Desktop analysis and mobile layouts visually inspected.
- Focused failure-path browser check passed: a failed solve retains the previous result with a clear failure label while disabling stale exports/analysis. Inputs and analysis are invalidated consistently.
- SAM YAML parsed locally; five routes, explicit HTTPS CORS origin parameter, x86_64/Python 3.12 runtime and DynamoDB environment/table contract inspected. Mock persistence regression tests pass.
- Final archive CRC/integrity and excluded-file checks passed during packaging.

## Numerical evidence

For the default emergency outage and cost strategy, the fixed current policy passes **1/5** solar stress cases; the separately solved 60%-solar policy passes **4/5**. This is a deterministic test count, not a forecast probability or robustness guarantee.

For default grid stress with an illustrative ₹8/kWh AC-throughput wear allowance:

| Metric | Wear ignored in solve | Wear included |
|---|---:|---:|
| Battery throughput | 74.00 kWh | 36.74 kWh |
| Approx. equivalent full cycles | 0.5139 | 0.2551 |
| Operating cost excluding wear | ₹6,931.81 | ₹7,120.40 |
| Total valued at common wear rate | ₹7,523.81 | ₹7,414.32 |
| Peak import | 35.55 kW | 39.75 kW |
| Production jobs completed | 5/5 | 5/5 |

Rounding/tied schedules can vary by solver version. End-of-horizon battery reserve remains 26 kWh. This model estimates throughput use, not validated lifetime.

## Reproduce

```powershell
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python server.py
# In a second terminal:
python scripts/smoke_test.py
```

Optional browser regression (Node required; development-only dependencies):

```powershell
npm install --no-save playwright
npx playwright install chromium
node scripts/browser_smoke.cjs
```

## Remaining owner verification

No known blocker to the tested local demonstration. AWS SAM CLI/Docker container build, native-library cold starts, API Gateway CORS from the real frontend, cloud latency and real DynamoDB write/read are **not verified** here. Run the owner checklist in AWS_DEPLOY_VERIFY.md before claiming a live deployment. No credentials, accounts, resources, GitHub publication or hackathon submission were accessed.

Synthetic factory scenarios only. Not a live industrial controller. Infeasible conservative plans are reported explicitly; the current valid plan is retained. Five-second per-solve limits return labeled feasible time-limited results when available, otherwise an explicit failure.
