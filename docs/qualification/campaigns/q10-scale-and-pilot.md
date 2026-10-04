# Q10 — Scale and pilot

Q10 verifies R28, R30 and R33–R35. It supports P09 scheduling controls, P10.01/P10.04/P10.06 and P11.01–P11.04. G09.04/G10.01/G10.04 evaluate operating behavior; G11.01–G11.04 evaluate the bounded production pilot and handover.

## Scope and ownership

Product/application owners define useful operator tasks and acceptance; performance/SRE own workload generation, endpoint budgets and service measurements; receiving operations independently exercises the service. E2 supports integration load work, E3 covers qualified native effects and E4 records operational acceptance. The user's estate figures are planning inputs, not passed scale claims.

Use the [phased plan](../../implementation/phased-plan.md), [estimation and dependencies](../../implementation/estimation-and-dependencies.md), [support matrix](../../implementation/support-matrix.md) and [Q09 recovery procedure](q09-deployment-and-recovery.md). Freeze the qualified release and selected pilot scope before operational work.

## Preparation

1. Approve initial/growth workload tiers: tenant/site/resource counts, discovery churn/rate, concurrent jobs, transfer bandwidth and API/UI task mix.
2. Assign numerical SLO/latency/outage/data and endpoint/concurrent-impact limits, their measurement windows and responsible owners; do not derive promised values from this procedure.
3. Prepare reproducible workload seeds, synthetic data, representative distributions, cold/warm cache cases and monitoring independent from the load generator.
4. For pilot, verify G10 acceptance and approved production environment/tenant/site, credentials, backup/monitoring, change window, stop/recovery and support scope.
5. Train independent operators on actual runbooks and define the observation period, feedback method, incident escalation and acceptance reviewers.

## Case matrix

| Case | Action or injected fault | Required observation | Evidence |
| --- | --- | --- | --- |
| Q10.01 | Run approved initial/growth discovery and API workload mixes | Measured throughput, latency, freshness and resource use meet declared tier targets | Workload manifest, time series and percentile definitions |
| Q10.02 | Increase job/wave concurrency across tenants and shared endpoints | Fairness, dependency order, quotas and endpoint/impact limits remain within approved budgets | Queue/native request timelines and budget measurements |
| Q10.03 | Reach documented capacity saturation and inject slow dependencies | Backpressure and explicit holds prevent overload amplification; recovery drains safely | Saturation curve, error/hold behavior and recovery trace |
| Q10.04 | Pause/stop competing waves with queued, active and unknown operations | Stop boundary is respected; active outcomes reconcile without unbounded concurrent effects | Q08.09 evidence and operator-visible wave state |
| Q10.05 | Remove a selected failure domain/dependency during representative load | Service behavior and measured recovery satisfy approved objectives without widening security scope | Fault timeline, Q09 references and before/after metrics |
| Q10.06 | Trigger freshness, stuck-job, drift, custody and availability alerts | Real recipients receive/acknowledge the alert; escalation and runbook action work | Alert IDs, delivery/acknowledgement and incident record |
| Q10.07 | Assign delegated operators complete catalogue, plan, approve, observe and recovery tasks | Authorized journeys succeed with keyboard/accessibility requirements; errors/holds are understood | Observed task completion, browser records and user findings |
| Q10.08 | Run the approved production pilot for its agreed observation period | Application integrity, usable service, performance and incident behavior meet selected scope | Pilot task/outcome log, measurements and owner acceptance |
| Q10.09 | Ask an operator other than the developer to install/recover and export audit evidence | Runbooks and support/escalation ownership suffice without unauthorized writes or hidden developer steps | Independent handover exercise and remediation findings |
| Q10.10 | Reconcile the release dossier against installed digests and support claims | Every advertised tuple has current evidence; limits, contacts and risks are accepted by receiving owners | Release/support reconciliation and actual review decision |

## Execution and observations

Record latency start/end boundaries, sample counts, error inclusion, warm-up and measurement windows. Publish workload shape with the result so a low-load run cannot be mistaken for estate capacity proof.

Separate simulated load from real endpoint load. Native traffic must stay within owner-approved budgets; scaling a simulator validates control-plane behavior but does not establish native platform throughput.

Production pilot tasks use explicit operational authorization and the already qualified scope. Fault/recovery demonstrations belong in the separately approved environment and change window; do not assume a pilot permits arbitrary production disruption.

## Pass criteria and evidence

Every accepted tier and selected pilot task must meet its approved measures. Required alerts must reach real assigned recipients; receiving operators must complete the handover exercises. Open material integrity, isolation, recoverability or usability failures block acceptance or require an explicitly narrower reviewed release scope.

Retain workload/configuration manifests, raw measurement references, calculations, fault/alert timelines, operator task observations, pilot outcomes, support assignments and actual receiving-owner decisions. Record E4 only when operational review occurs, following [canonical state rules](../../implementation/status-model.md).

## Cleanup and reruns

Stop workload generators, reconcile jobs/allocations and remove only authorized test scope. Preserve production pilot records under accepted retention. Rerun affected tiers/tasks after material resource sizing, scheduler, dependency, UI, support or release changes; previous pilot acceptance never automatically covers a new release.
