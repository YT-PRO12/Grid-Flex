# Scenario evidence boundaries

Grid Flex is an optimization decision-support prototype for a **synthetic** factory. Its scenarios are deterministic illustrative inputs, not site-metered operating data.

## Inputs and outputs

The [scenario fixture](../engine/scenario.py) defines 12 hourly slots, illustrative tariffs, energy sources, five production jobs, battery constraints, and emissions factors. The solver returns candidate schedules. Verification should check power balance, battery state of charge, grid caps, job deadlines, and the applicable load-shedding allowance.

Cost and carbon figures are **modeled comparisons under those assumptions**, not measured savings. The outage preset simulates two hours of unavailable grid power; it is not an emergency switching command.

## Review before making claims

1. Record the scenario preset and every changed control.
2. Confirm independent mathematical audit results for the same selected solution.
3. Report solver status and limitations, not only the winning KPI.
4. Clearly distinguish infeasibility from API and runtime errors.
5. Never imply live equipment control, operational safety validation, or deployed cloud integration on the basis of a local calculation.

See [README](../README.md) for current scope and deployment boundaries.
