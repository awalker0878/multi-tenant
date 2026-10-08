# Platform expansion and adapter operation

Use the [P09 implementation](../../implementation/p09-expansion.md),
[completion packet](../../implementation/p09-completion-review.md) and
[Q08 campaign](../../qualification/campaigns/q08-route-expansion.md).
No native tuple or deployment is enabled by the software tests.

## Freeze the intended tranche

Validate the versioned baseline using `contracts/schemas/expansion/tranche-v1.json`
and `planning.domain.expansion.tranche`. A protected baseline binds exact source and
target Inventory observations, all eleven profile dimensions, guest/method/topology,
datasets, policy, services, recovery, artifact digests and owner objectives. Record
all nine directions as selected or explicitly deferred. Generate each route's
qualification plan with `planning.domain.expansion.qualification_plan`.

The matrix consumes current Assurance-owner records. Do not promote caller-submitted
JSON to Assurance authority. An exact accepted E3 row can establish native qualification;
it cannot supply operational acceptance, tenant permission or consent for a plan.

## Commission adoption and enterprise control

Apply `services/lifecycle/migrations/009_expansion.sql` through the existing owner
migration process. Configure the existing verified PostgreSQL connection and the
Lifecycle Console caller/Governance delegated-actor credentials. Runtime must remain
unable to migrate the database or delete audit events.

Start the explicit control process using:

```sh
lifecycle-expansion --owners /run/protected/p09-owners.json \
  --tls-cert /run/protected/service.crt --tls-key /run/protected/service.key
```

The protected owner configuration has schema version 1, a current `expires_at`,
distinct `observer_id`/`writer_id`, and five owner endpoints: `plans`, `authority`,
`budgets`, `observations`, and `adoption`. Each endpoint names `origin`, pinned
`address`, absolute `ca_file`, and its own protected `credential_file`. The process
uses only the fixed `/v1/expansion/*` protocol routes declared in
`lifecycle.infrastructure.expansion_owners`. Changing the configuration during a
request holds the result. Observe native account-to-principal bindings independently
at commissioning; different secret bytes alone do not prove separate people or roles.

The Console/workload caller needs a current delegated actor for every affected
site/environment/resource scope. These APIs do not accept arbitrary worker dispatch:

| API | Behavior |
| --- | --- |
| `POST /v1/tenants/{tenant}/expansion/adoptions` | Supply exact native scope and selected field names; collect current independent baseline |
| `GET /v1/tenants/{tenant}/expansion/adoptions/{id}` | Read retained baseline, state and revision under current scoped access |
| `POST /v1/tenants/{tenant}/expansion/adoptions/{id}/commands` | `import`, `transfer`, `reconcile`, or `detach`; exact expected revision, idempotency key and `proposed_fields` (`null` except import) |
| `POST /v1/tenants/{tenant}/expansion/waves` | Submit immutable plan ID/revision/digest references; the configured plan owner supplies specifications |
| `GET /v1/tenants/{tenant}/expansion/waves/{id}` | Read a wave after authorization of every member scope |
| `POST /v1/tenants/{tenant}/expansion/waves/{id}/commands` | `pause`, `resume`, or irreversible `stop`; expected revision and idempotency key |

Import checks equality with observed field-value digests. Import does not edit native
objects. Transfer requires all previous writers enumerated and excluded, no active
effects, and the exact receiving writer. Reconciliation is not a force-unlock: it
retains claims and requires a separate transfer. Detach requires the product writer
excluded and a different confirmed receiver; it never calls native deletion.

## Schedule and reconcile effects

Enterprise plans declare DAG dependencies, UTC windows/blackouts, complete maximum
duration, priority, and native scope. Mandatory prerequisites pin safety, policy,
services, recovery, ownership and capacity. Budget demands must include the tenant,
endpoint and correlated-impact pool; all limits and external usage come from the
commissioned budget owner, never the control request.

Compose `EnterpriseDispatcher` with the selected `EnterpriseEffects` implementation.
The implementation must call the supplied boundary immediately before each native
request and enforce provider-side exclusion of stale workers. An application callback
alone is not proof of distributed native fencing. Compose remote worker boundary
verification and selected service effects before advertising a runnable operation.

An active or unknown operation keeps budgets and its object claim. Restarting the
dispatcher cannot resubmit it. Pause/stop denies subsequent boundaries; accepted
requests may still finish and must be observed. The independent final receipt must
match operation, lease and full specification, exclude the old writer and prove
required policy/service/recovery outcomes. Only then release allocations. Failed
dependencies hold downstream work. Recovery uses renewed, separately bound authority.

## Install or change a signed adapter

The native worker registry supports `platform_lifecycle`. Its configuration supplies
separate native `writer`/`reader` endpoints, `trust_file`, `envelope_file`, and
`artifact_file`, plus distinct commissioned `observer_id`/`writer_id` principal IDs;
the entry's observer is `null` because its independent native reader
is constructed explicitly. The protected plan fixes platform, API contract, native
object, one operation, desired owned fields, baseline and exact tuple/route/adapter
digests, project and custody scope. Runtime binding changes invalidate the entry.
Credential separation is checked before and after readback. Actual account-to-principal
mapping must be independently established; different token values cannot establish it.

1. Build the pinned worker wheel. Calculate its SHA-256 and the installed Python
   implementation digest using `extension_trust.implementation_digest`. The signed
   manifest binds both, the release, constraint version, interface versions, exact
   operation/tuple/route capabilities, owner, validity period and all retest triggers.
2. Have the independently administered signing owner sign
   `extension_trust.signing_bytes(manifest)` with Ed25519. Store the manifest/key ID
   and base64 signature in the envelope. Never package the private signing key.
3. Install the public trust configuration in protected custody. It records epoch,
   expiry, key validity/revocation, per-key adapter scope and revoked artifact digests.
   Only `vmware-lifecycle-v1` and `ahv-lifecycle-v1` are currently registered built-ins.
4. Verify the envelope, exact artifact bytes and installed code identity before
   admission. Supply independently commissioned write/read identities and scope.
   VMware supports the pinned REST contract; AHV uses VMM v4.0. Do not substitute a
   version, raw command, arbitrary URL or another migration method.
5. Drain/reconcile active and unknown attempts before an upgrade or recovery. Obtain
   exact old/new-manifest, common-path and recovery evidence through the trusted
   qualification owner; validate it with `extension_trust.upgrade`. Publish the new
   protected runtime selection only after its operating approval. Retest all affected
   support rows; signature validity alone is not native qualification.

Revocation or expiry blocks subsequent effect boundaries. A revoked package must not
be re-enabled by restoring an older trust file: independently managed epoch/backup
custody and the current authority service must prevent stale-state resumption. The
software trust-file reader alone does not implement an external trust custodian.
