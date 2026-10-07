# Native workflow control

Owner: Lifecycle. Packages: P07.02, P07.04 and P07.05. The implementation is
`services/lifecycle/src/lifecycle/application/native_workflow.py`; it is a durable
control component, not an enabled native dispatcher or an E3 qualification claim.

## Current boundary

Provisioning orders reserve, provision, guest configuration, service enrollment
and activation. Retirement uses a different immutable plan and approval, linked
to the active source job, and orders retirement before allocation release.
Each step refers to an immutable owner-specific intent digest. The coordinator
does not accept shell commands, platform credentials or caller-supplied evidence.

Apply `004_native_workflows.sql` using the Lifecycle migration owner. Its control
table starts empty. Runtime cannot install or change the independently held
custody epoch. Runtime may append job, operation, redemption, evidence and event
records, but cannot erase them. Resource and state-lineage holds survive expiry,
restart, response loss, activation and retirement. They are not time leases.

Before admission, preparation, redemption and every ongoing privileged boundary,
the current-authority port must authenticate Governance approval, exact confirmed
Inventory revision/digest, installed tuple, ownership, epoch and provider fencing.
The epoch is checked again after owner reads. Simulation receipts are rejected.
The service has no production implementation of that composite port yet; do not
substitute the synthetic test owner or a mounted JSON assertion for it.

Preparation and redemption re-read independent prerequisites. A grant can be
redeemed once by its bound worker, within 60 seconds of preparation. Ongoing
work may continue only until the approved plan expires and while current checks
pass. Response loss or process restart cannot redeem again or prepare a second
attempt. A stop is terminal for writes within that job.

## Observations and recovery

Every observation binds the exact operation/attempt, intent, phase, observer,
time and original evidence digest. Native actor, requester and executor cannot
serve as their own independent observer. Activation requires IPAM, DNS, identity,
time, trust, logging, monitoring, backup and restore, application health/data and
the exact allowed/denied policy cases. The approved matrix includes same-host/
subnet, inter-host and edge paths plus applicable IPv6 and return cases.

Reconciliation is read-only and remains available after write expiry or stop.
It advances only after all independent post-effect observations, including
provider-request quiescence, exist. A 404, Terraform exit, heartbeat timeout or
empty pending-request list does not supply that evidence. Failed or incomplete
observations hold the job. Earlier successful observations cannot clear a later
hold or regress a terminal state. No automatic retry or hold deletion is supplied.
An independent custody epoch change holds restored journals until the separate
recovery procedure is implemented and qualified.

Retirement additionally requires scoped ownership, quarantine, explicit retention
authority and readable retained data/keys. Independent native absence precedes
allocation release, and retained data/keys are checked again afterward. Successful
retirement does not grant authority to reprovision or destroy retained storage.

## Worker boundary contract

The [native boundary OpenAPI](../../../contracts/openapi/lifecycle-native-boundary-v1.json)
and [golden request](../../../contracts/fixtures/lifecycle/native-stage-grant-v1.json)
define a separate internal check route. The ASGI handler resolves tenant and worker
from its authenticated caller port; neither identity can be supplied in JSON.
Provisioning envelopes contain every existing worker `NativeBinding` field.
`GrantedNativeAuthority` checks the envelope before each saved-plan boundary;
`LifecycleNativeBoundary` provides fixed-origin pinned TLS, a protected distinct
workload credential, bounded strict JSON and no retries or redirects. Lost
redemption replies retain the existing worker journal hold without launching.

The handler is not installed into the simulation router. It must be composed with
the commissioned native owner and workload-trust implementations; an implemented
transport is not proof that those independent controls exist.

## Integration and qualification still required

The application interface is executable and persistence-tested independently.
The composite owner adapter, provider request fence, guest/service effect adapters
and independent native observer implementations must be connected to the
commissioned environment before dispatch can be enabled.
Use API-first Inventory/Console inputs under ADR-015/016; do not introduce a second
checked-in configuration authority. G07 still needs the original Q05/Q06 campaign,
actual owners and receiving decisions. No native operation is enabled by this
migration or by a test result.

The P07 component campaign now runs the complete Lifecycle suite with real
PostgreSQL, in addition to the existing worker/TLS/Terraform tests. Local
environments without PostgreSQL process/user support cannot qualify persistence;
the hosted campaign must run without skips.

## Native Temporal orchestration

Migration `005_native_dispatch.sql` adds the native admission outbox. New admission
commits its immutable job, resource hold and dispatch entry together. It does not
enqueue historical jobs. Runtime cannot replace workflow identities or delete
dispatch rows. `NativeDispatcher` uses a stable `p07-native-v1-<job>` identity and
the separate `p07-native-v1` queue. Lost start replies resolve the original workflow
only after matching type, queue, tenant, job, plan digest and version.

`NativeJourneyV1` delegates preparation and every current-authority check to
Lifecycle. Every activity has one attempt. The selected worker must redeem the
exact grant before effects; its return value supplies no readiness evidence.
Only independent reconciliation advances the next stage. A prepared operation
survives worker interruption without being dispatched again; missing observations
hold it. Wake notifications cannot clear a journal hold or authorize work.

Temporal cancellation records a hold; it does not establish that the provider has
stopped. A held job can advance only through the existing independent reconciliation
and fresh next-stage authority checks. Custody-epoch changes still prevent restored
journal resumption. The supplied `run_native` composition factory requires a
verified Temporal client plus actual native owner and effect implementations. The
simulation deployment does not register it or supply synthetic defaults.

The orchestration campaign uses real pinned Temporal, TLS/JWT and PostgreSQL to
exercise accepted start/effect response loss, restart, current-authority change,
missing provider-quiescence evidence, cancellation, retirement ordering and history
replay. Provision crosses the real worker effect TLS route, returns over the real
Lifecycle boundary TLS route and writes a separate worker-owned PostgreSQL journal.
Its current authority, saved-plan process, provider observations and other stage
effects are synthetic; this is E2 software evidence, not a native Q05/Q06 result.
Actual run results are retained separately.

## Saved-plan effect submission

`NativeWorkerEffects` implements the dispatch port through one registered executor
endpoint with a fixed IP, verified TLS hostname/CA and protected workload credential.
It makes one POST, follows no redirect and performs no retry. The bounded receipt
must bind the exact grant and explicitly deny readiness and retry authority.
Uncertain transport outcomes enter the same reconciliation hold.

The [worker effect contract](../../../contracts/openapi/worker-native-effect-v1.json)
is implemented by `NativeEffectApp` and `NativeSavedPlanEffect`. Caller trust supplies
tenant and worker independently from JSON. The use case checks current authority
before resolving tooling, then uses the existing saved-plan journal and one-time
grant redemption. Only the provision stage is supported; other stages require
their selected service adapters and remain held. `MountedNativeTooling` resolves
the existing protected tooling/observer packet, validates actual bound artifact
bytes and uses the independently scoped OpenStack observer. That packet conveys
no native authority and does not replace confirmed Inventory/Console configuration.

The effect handler is not registered by the simulation server or inspection CLI.
Production composition still requires the native current-owner implementation,
verified per-link caller trust, actual provider/state fencing, and each remaining
stage's commissioned effect/observer interfaces.
