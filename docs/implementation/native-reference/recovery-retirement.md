# Recovery, uncertain outcomes and data-safe retirement

**NRC-M01 supporting procedure — Proposed.** References: [operational recovery and transition](../../operations/README.md),
[shared recovery topology](../../architecture/shared-services/6-failure-recovery-migration-and-failback-topology.md)
and [single-writer execution](../provisioning-strategy/5-concurrency-ownership-and-failed-execution.md).
No step below is automatically executed by the worksheet exporter.

## Before the first native change

Name the person/role able to stop the campaign, the native resource owners, the incident
contact, independent management path, fault budget and protected evidence location.
Identify the consistency point, retained-data obligations and separately authorized
repair/cleanup tools. Confirm that the operators can recover required catalogue, key,
identity and state-backend dependencies under the failure being exercised.

Create a resource receipt per writer scope, including stable native IDs and any recorded
task. Do not grant the campaign coordinator shared blanket credentials. Confirm how
ownership, leases and native asynchronous work are positively reconciled after runner
loss. A test plan that can create but cannot safely discover partial effects is incomplete.

## On a failed check or lost reply

Hold new dependent changes and preserve current containment, the last observed generation,
original request/task/resource references and any data already written. Determine whether
the original process or native asynchronous operation can still complete. Observe the
known scope without following untrusted discovery links or automatically retrying writes.

An expired lease, killed runner or released Terraform lock alone does not prove a native
writer is fenced. A failed task may leave useful or dangerous partial resources. A missing
GET can reflect the wrong ID, permission loss or API availability. Do not create a duplicate,
release its address, restore an old state file as resource rollback, or delete an unknown
object to make the inventory look clean.

The responsible owners decide the separately authorized recovery or repair after current
state and authority are known. Keep an independent incident restriction ahead of ordinary
desired-state reconciliation. Stop the experiment rather than bypass mandatory controls
when remaining scope, management, observation or fault-budget assumptions are invalid.

## Prove an isolated restore, not just a boot

Record the data-owner-approved consistency point and the actual capture, transfer,
catalogue, key and retained-copy chain. Select an eligible recovery target whose routing,
identity, mandatory policy and data entitlements remain isolated. Prove authorized access
to useful recovered data and its application/service integrity checks, not only guest
power state, a mounted volume or a successful restore-task result.

Measure the promised service RTO/RPO against the actual observation definitions and
all dependencies. Record independent protection/delete authority and deny unauthorized
copy/key destruction. Unpurchased site recovery does not remove applicable backup,
management recovery, ownership and continuity obligations. Do not withdraw the only
usable bootstrap/key/catalogue recovery material before its replacement is demonstrated.

## Cutover and rollback after writes

Before target exposure, establish final synchronization/consistency, explicit source
writer exclusion, target policy and identity, and current operating acceptance. Once the
target has accepted writes, restarting the old source is not a safe universal rollback.
The data owner must determine reverse synchronization and conflict handling, then verify
the resulting service and paths. Retained network identity is not a substitute for data
consistency or fencing.

## Clean up the restricted fixture even when qualification fails

The NC00–NC90 dependency table is **not permission to postpone cleanup until production
acceptance**. Under the previously accepted cleanup authority, inventory actual partial
resources first. Withdraw discretionary exposure and test flows; remove scoped temporary
probes, grants, mounts and attachments in dependency-safe order. Preserve shared services,
other tenants, retained copies, required keys and investigation evidence.

Confirm absence of obsolete routing/policy/identity and authoritative name registration
before releasing reservations or reusing addresses/attachments. Apply the actual name and
address quarantine policy; the [DNS client](../../../tools/dns_change.py) does not replace
IPAM or prove all downstream caches/log/copy obligations are clear. A missing resource in
one API is not sufficient release evidence.

Transfer remaining copy/catalogue/key and legal retention obligations to accountable
custodians. Record live-service retirement separately from eventual eligible sanitization.
Keep attempted and completed teardown evidence, unresolved resources, owners and next
actions. No unsupported `terraform destroy` or blanket deletion is a substitute for this
resource-by-resource handover.

[Kit index](README.md) · [Campaign evidence](campaign.md)

The NC55 cleanup planning prerequisite is NC00 (scope and ownership), not a successful
NC40 or NC50. Use the actually discovered resource identities and separately controlled
cleanup authority after an early failure; do not invent a resource or delete a shared
dependency merely because its intended build step is incomplete.
