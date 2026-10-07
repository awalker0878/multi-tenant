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

## Integration and qualification still required

The application interface is executable and persistence-tested independently.
The production API/Temporal dispatcher, composite owner adapter, provider request
fence, guest/service effect adapters and independent native observer implementations
must be connected to the commissioned environment before dispatch can be enabled.
Use API-first Inventory/Console inputs under ADR-015/016; do not introduce a second
checked-in configuration authority. G07 still needs the original Q05/Q06 campaign,
actual owners and receiving decisions. No native operation is enabled by this
migration or by a test result.

The P07 component campaign now runs the complete Lifecycle suite with real
PostgreSQL, in addition to the existing worker/TLS/Terraform tests. Local
environments without PostgreSQL process/user support cannot qualify persistence;
the hosted campaign must run without skips.
