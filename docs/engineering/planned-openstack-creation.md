# Planned OpenStack native creation

`PlannedLeaseAuthority` extends the existing B10/B11 owner to a resource that has
not been created yet. `planned_resource_ownership` records an explicitly logical
VM or aggregate deployment identity. `planned_creation_children` is its immutable
constraint projection: an aggregate and an individual VM cannot claim the same
reviewed target machine, including from a changed plan or different job. These
tables do not manufacture native IDs or form another operation journal. Actual
`native_operation_leases`, `native_operation_intents`, observations and reviews
remain authoritative for the attempt.

Registration rechecks the canonical running job, approvals and protected execution
selection. Every target machine in the MigrationPlan must match the resource
bundle's workload members. The owner records exact creation request and counted
capacity receipt digests, scoped worker, epoch and bounded deadline. B10 grants
use the same planned/observed lease lookup. A copied grant or capacity receipt is
insufficient. Capacity renewal changes its receipt and must precede planned-owner
registration; it cannot silently renew an immutable planned writer afterward.

`PlannedNativeCreationRegistry.prepare` and `claim_once` use the existing intent
journal. Only PREPARED can become IN_FLIGHT. A timeout, loss of readback or uncertain
reply retains that attempt. Expiry never permits another apply. Native TASK_ACCEPTED
requires an actual task receipt; the Terraform exit code cannot supply one.
`NativeCreationObservation` contains actual typed native bindings and a fresh
independent observation whose custody and exact selected children the evidence
owner must authenticate. Construction of that object proves nothing by itself.

Current, quiesced, independently observed creation may be acknowledged as
EFFECT_PRESENT. Read-only reconciliation compares the original actual bindings;
it never replays creation. Recovery of an expired uncertain writer requires fresh
native readback, independently verified old-worker exclusion and two distinct
current execution operators reviewing the same evidence and incident. NO_EFFECT
still does not release capacity or permit reuse. Actual native ownership is
materialized only after observed occupancy is confirmed and the accepted workload
WSD trigger allows it. Cross-WSD membership retains its separate transition gate.

## Enrolled saved-plan runtime

`PlannedTerraformRuntime` is a process-local binding for the exact admitted job,
aggregate deployment, step, live WorkerGrant, verified mTLS peer and actual
PostgresWorkerGrants/PlannedLeaseAuthority owner. It dispatches the existing saved
Terraform plan owner. A plan, queue or environment cannot select a module or
substitute an arbitrary native executor. Saved inputs must equal the complete
selected ResourceBundle inputs before the intent can be claimed.

`EphemeralOpenStackApplyContext` refreshes secrets through the enrolled
CredentialBroker and VaultDynamicCredentialIssuer. It consumes the single-use
wrapped credential at that issuer's pinned HTTPS endpoint. The dynamic role must
return exactly `environment` and `cloud` in a bounded revocable lease. Its policy
must constrain actual OpenStack and state-backend permissions, TTL and revocation
to the selected operation; wrapping TTL alone cannot supply those permissions.

The fresh cloud must preserve its alias, Keystone URL, region, interface and TLS
settings. Actual Keystone application-credential authentication must report the
exact selected project and commissioned compute origin. The current grant,
worker mTLS identity, selected creation intent and native authentication are
rechecked before and after each apply/output subprocess. Timeouts are bounded by
the current grant and credential deadlines. Failed or expired checks retain an
uncertain intent even if Terraform has already reported success.

The original saved plan, input bytes, reviewed source, original cloud file,
non-secret configuration, CA and executable hashes remain unchanged. Fresh
secrets go in a private per-attempt runtime overlay; a versioned binding record
contains only their non-secret scope, lease digest and deadlines. The historical
CLI apply path still verifies its exact original bundle and credentials. There is
no CLI flag or caller success boolean for the process-local refresh context.

After apply, the independent creation reader must observe every selected target
VM and the registry must accept its actual bindings before delivery can publish a
completion marker. The reader, resource occupancy verifier and worker-exclusion
verifier are independently commissioned owner ports. Missing bindings hold; no
production implementation is inferred from a test fixture.

## Verification scope

`test_planned_terraform.py` executes the actual saved-plan closure and loopback TLS
Vault/Keystone credential consumption. Terraform processes, enrollment and grant
ports are synthetic. It verifies preservation of reviewed artifacts, fresh secret
overlay, native project/endpoint refusal, deadline bounds, revocation refusal and
tamper detection. `test_planned_creation.py` separately defines real PostgreSQL
tests for existing intents, actual B10 revalidation, RLS, append-only identities,
aggregate/child overlap, expiry/fencing/two-reviewer recovery, selected operation
domains and resource-authority revocation. Those PostgreSQL cases require the
isolated runtime/enrollment/migration roles and are skipped when unavailable.

Local fixture success does not qualify a deployed dynamic role, native observer,
capacity owner, application or migration direction. The selected-site campaigns,
old-worker fencing, resource confirmation/cleanup and first directed application
migration must supply that evidence independently.
