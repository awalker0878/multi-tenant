# P08 migration operations implementation

The remaining P08 work includes environment/account commissioning, complete native
journey composition, performance measurement, concurrency, staggered schedules and
operator control. This record supplements the existing P08 packages; it does not
change the native-only baseline or mark G08 accepted.

## Campaign control increment

Lifecycle owns migration campaigns, ordered plan references, UTC windows with an
IANA display zone, separate cutover windows, blackouts, staggered starts, phase
limits, failure limits and durable resource allocations. A schedule never supplies
execution authority. Native admission and every effect still require current
owners, exact reviewed plans, independent observations and existing custody.

The campaign domain checks cycles, missing dependencies and entire-window fit.
Performance estimates use the slowest current comparable measured sample for each
stage, add a 25% time margin and refuse unmeasured concurrency or stale routes.
Transfer throughput is not substituted for conversion/import throughput. A recent
production-impact breach holds the corresponding phase.

Migration campaign assignment and native job admission share one PostgreSQL
transaction. Capacity is counted across outstanding allocations, including unknown
outcomes. Stage slots are released only after the existing independent post-effect
observation. Completion does not release staging/rollback retention. Cancellation
removes queued starts and preserves active native jobs and their custody; native
stop/recovery remains an explicit separate operation.

Lifecycle now exposes scoped campaign create/read/list/command endpoints and
separate internal performance, capacity and cleanup-observation endpoints. Console
requests resolve requirements from authenticated immutable Planning records; sizes,
routes and resource demands cannot be supplied by the browser. Complete operational
migration plans remain required. Existing preparation-only records cannot be scheduled.

The native worker factory accepts an explicit campaign dispatcher and commissioned
plan source. Pending members are considered fairly across dispatch passes, so a
blocked high-priority member cannot starve ready members. Current native owners
are still rechecked by native admission. This does not commission a writer or
fill missing Planning/native-owner composition.

Each phase requires measurements at every occupancy up to its configured limit.
Stage limits apply across campaigns sharing the route and honor the stricter
active limit. Redundancy/outage groups exclude simultaneous admissions across a
tenant's campaigns. Pause, window, current measurement and pool-observation checks
also apply at worker effect boundaries. Independent reconciliation remains readable
after a pause. Uncertain effects retain their native operation and reservations.

Observation publishers use the separately mounted
`LIFECYCLE_CAMPAIGN_OBSERVERS_FILE` registry, re-read on every publication. Version 1
contains `schema_version: 1` and `grants`; each grant contains `tenant_id`,
`observer_id`, `token_file`, `expires_at`, `kind` (`performance`, `capacity` or
`release`) and `resources` (exact route digests or pool keys). Tokens must be
distinct per grant. Paths are trusted deployment inputs, not request fields.
Performance reports must be measurements from the commissioned route/phase at the
reported concurrency, with retained evidence and measured production impact. The
ingress does not perform a benchmark or manufacture native observations.

Pool capacity is a total migration budget net of unrelated usage; current
allocations are subtracted by Lifecycle. Publishers must refresh within five
minutes; paused or stale observations hold work. Shared pools use the minimum
current budget across their tenant observations. Physical pools must have stable
shared keys, while tenant quota pools must include the tenant in their identity.
Release requires a separately scoped independent publisher, a completed member,
fresh evidence of unused resources and drained provider requests. Cancel never
releases active allocations. Retained artifacts stay reserved until observed cleanup.

The Console campaign page creates drafts from owner-resolved complete plans and
provides schedule/resume, pause, queued cancellation and live member/estimate
views. It supports UTC windows with an explicit display zone, separate cutover
windows, blackouts, dependencies, outage groups, priorities, stagger, phase limits
and failure limits. Lost command replies retain the exact body/key; current access
is polled and revoked access clears the view. Read access does not grant controls.
The API contract and generated Console types are versioned independently of the
existing simulation job contract.

Environment/account commissioning, native measurement producers and complete
Planning/native runtime composition remain required integration work. Planning's
existing migration preparation does not yet emit the full operational native plan;
the new page holds those records. A future schedule does not extend a plan/profile
or approval's lifetime. Expired plans require a fresh approved campaign draft.

## Qualification corrections

Commit `9c1adaa3ade546b4f187420ee588204f128387e1` passed the hosted P08 PostgreSQL
test command and the existing migration browser journeys, but the overall P08
run `37650245430` failed its formatting check. The original failure remains in
GitHub Actions. Commit `f29325f6b97c4118a3db80ca077d2659d921a388` corrects only
the required test formatting. Subsequent results must be bound to their tested
source; none of these component checks establish native qualification.

## Remaining scope to close

1. Configure each source/target account through approved endpoint and secret custody;
   test actual permissions, rotation, revocation, worker placement and connectivity.
2. Complete source profile and native plan composition, real guest/converter/data/
   service/fencing/traffic/recovery adapters and the native runtime bootstrap.
3. Implement reconciled large-transfer continuation beyond the 600-second activity.
4. Publish authenticated performance and pool observations and integrate resource
   measurements from actual native producers. The authenticated ingress, durable
   allocation/stage admission, wave dispatch and Console controls are implemented;
   observed physical capacity, production impact and native composition are still required.
5. Qualify fleet partitioning and group scale without silently widening endpoint scope.
6. Run software, PostgreSQL, browser and workflow campaigns; retain original failures
   and corrections. Then execute Q05/Q06/Q07 on the actual commissioned VMware and
   OpenStack tuple, including both data recovery boundaries and accepted objectives.

Actual identities, installed platforms, owners' application protocols and native
Q07/G08 receiving results remain external inputs. Unknown or missing inputs remain
explicit holds. No software result can stand in for those observations.
