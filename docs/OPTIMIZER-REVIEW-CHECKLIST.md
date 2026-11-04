# Optimization result acceptance checklist

A solver's successful status is necessary but not sufficient to certify the business interpretation of a simulated schedule.

For every reported scenario:

1. Capture the preset and complete control values.
2. Verify each production job is scheduled once, within its earliest start and deadline.
3. Check the hourly power balance: grid + used solar + discharge − charge = fixed + flexible demand, adjusted for permitted curtailment.
4. Check grid and PV supply caps, battery charging/discharging exclusivity, state-of-charge limits, and reserve constraints.
5. Compare objective components consistently across baseline and candidate plans.
6. Report signed emissions changes instead of assuming cost savings imply carbon reductions.
7. Document solver status, tolerance limits, infeasibility, and any time limitations.

All economic and environmental outputs are *model estimates for synthetic inputs*, not measured operational savings. No physical energy system is controlled.

See [scenario boundaries](SCENARIO_EVIDENCE_BOUNDARIES.md).
