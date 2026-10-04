# Operating targets and measurement

Owner: product and SRE leads with application, security and service owners. Related work: P00.05, P04, P06, P10–P11; R29–R35; ADR-017.

## Target record

Each accepted objective identifies the service journey, environment, scope, unit, measurement interval, workload model, exclusions, dependency assumptions, owner and evidence required. Record both an initial operating tier and a growth tier. Ratification occurs through ADR-017; measurements are registered against Q09/Q10 and the applicable gate.

| Objective | Initial design input | Measurement rule |
| --- | --- | --- |
| Core control-plane availability | 99.9% monthly | Authenticated catalogue/read, assessment admission, plan review and job-status journeys; define denominator, maintenance treatment and dependency failures explicitly |
| Interactive reads | p95 at or below 2 seconds | End-to-end browser/server timing under the selected session/data distribution; report errors and timeout rate alongside latency |
| Durable command acceptance | p95 at or below 3 seconds | Receipt of a valid eligible request to durable accepted receipt; excludes subsequent assessment/native operation duration |
| Control-plane data recovery | RPO at or below 15 minutes | Actual recoverable state across required databases, workflow history, evidence, keys and infrastructure state; do not infer from backup frequency |
| Control-plane restoration | RTO at or below 4 hours | Measured restoration to safe reviewed service; report separately when native writes remain held for reconciliation |
| Application recovery and migration outage | Application-owner values for selected workload | Define data-loss bound, consistency boundary, outage start/end, validation queries and retained-source/target-write behavior |
| Discovery freshness | Per endpoint/resource class | Age from last complete authorized generation and changes since it; partial discovery cannot reset completeness-based freshness |
| Tenant isolation | No successful unauthorized action in defined campaigns | Test direct APIs, object access, projections/events, searches, job status, evidence/export and restored state |

These values are design inputs already present in the phase plan. They become accepted service objectives only after the accountable owners choose the workload model and measurement conditions. A control-plane target is not automatically an application service commitment.

## Capacity model

Capture distributions as well as totals: active tenants/users; applications/workloads; dependency and policy edges; revision retention; endpoints/resources/API pages; discovery interval and endpoint budgets; concurrent sessions and request mix; workflow/activity duration and bursts; retries/failure rates; evidence/telemetry sizes and retention; dataset size/change rate; and effective transfer/storage throughput.

Plan for one failed component or failure domain using the selected recovery model. Measure surviving eligible capacity and queue growth. Add tenant fairness, worker concurrency, native API and transfer-bandwidth budgets so one large job cannot consume every endpoint or saturate a shared dependency.

## Measurement campaigns

1. Record exact product/dependency versions, configuration, topology, data shape, generators and allowed endpoint budgets.
2. Establish idle and nominal-load baselines; verify telemetry and independent time measurement before collecting results.
3. Exercise the representative journey mix and peak bursts. Include incomplete discovery, dependency latency, retries and one noisy tenant.
4. Inject the selected failure conditions and measure detection, safe containment, queue recovery, restore and reconciliation separately.
5. Report latency percentiles, throughput, error/timeout rate, backlog, resource saturation and the number of operations held for safety.
6. Compare results with each accepted objective, preserving failures and limitations. Record artifacts and reviewer decisions in the delivery register.

Do not report a latency percentile from successful requests alone while omitting timed-out or rejected requests. Do not advertise a throughput reached by disabling authorization, evidence writes, encryption, policy checks or rate limits required in the supported deployment.

## Service indicators and action thresholds

| Indicator | Meaning | Operating response |
| --- | --- | --- |
| Admission failure / latency | Authority or dependency path cannot accept eligible work | Classify denied requests separately from service failures; preserve request identity and stop unsafe fallback |
| Discovery age / coverage | Plans may rely on stale or incomplete observations | Hold eligibility requiring those facts; inspect scope, paging, credentials and endpoint throttling |
| Queue age / tenant share | Work is delayed or unfairly scheduled | Bound ingress, adjust admitted concurrency and verify endpoint budgets before scaling workers |
| Unknown outcomes / held scope | External effect cannot yet be established safely | Keep affected resource holds; use reconciliation with independent observations |
| Evidence backlog / finalization failures | Execution claims lack durable custody | Prevent affected success/qualification publication and restore evidence ingestion |
| Recovery lag / dependency health | The system cannot meet its restoration assumptions | Review available backups, keys, version compatibility and dependency restoration order |

Exact thresholds derive from the accepted objective and measured normal variation. Critical safety events such as unauthorized access, conflicting writers or lost fencing trigger containment independent of monthly availability figures.

## Review and change

Reassess targets at scope/feasibility acceptance, after P06 simulation, after first native qualification, after material topology/dependency changes and before pilot acceptance. Preserve the previous target and reason for change. A failed objective leads to corrective work or explicit scope renegotiation, not an edited historical result.
