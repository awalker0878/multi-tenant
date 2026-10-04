# Installed application worker composition

`provisioner.controlplane.workflow.application_runtime` composes the selected
VMware → OpenStack Ubuntu 24.04 rebuild/restore application workflow from the
existing PostgreSQL job/approval owners, capacity owner, qualification and
operating gates, delivery runner and migration activities. It does not commission
an estate or qualify a native migration. Native execution remains held wherever
current independent proof or an enrolled concrete owner is absent.

The worker registers the distinct `OpenStackApplicationMigration` workflow only
when `HOSTING_APPLICATION_EXECUTION` is exactly `1`. Unset or `0` retains the
existing gate workflow for plans without an execution selection. A canonical
plan that selects `spec.execution` cannot be silently dispatched to that older
gate when the selected runtime is disabled. The dispatcher locks and rechecks
the original job, start-payload digest, canonical plan/workload and current B07
approvals before returning `APPLICATION_SELECTED_DRIVER_RUNTIME_REQUIRED`.
That refusal precedes any Temporal start RPC.

## Protected commissioning settings

Settings contain absolute canonical paths to existing commissioned stores.
Input, packet, journal, result, capacity and accepted-source paths must be
separate, with no nested stores or symlinks. Private stores belong to the service
UID and have no group/other permissions. The source root belongs to the service
UID or root and is not group/other writable. Store identities are checked again
before composition, binding or graph display. The builder never initializes,
copies, discovers or substitutes a capacity database or secret.

| Environment variable | Existing protected owner content |
|---|---|
| `HOSTING_APPLICATION_EXECUTION_STORE` | Full selected execution artifacts, named by canonical digest. |
| `HOSTING_APPLICATION_DELIVERY_STORE` | Original reviewed delivery graphs, named by canonical digest. |
| `HOSTING_APPLICATION_RESOURCE_STORE` | Exact rederived resource selection documents, named by canonical digest. |
| `HOSTING_APPLICATION_INBOX_STORE` | Per-job reviewed delivery packets and their private inputs. |
| `HOSTING_APPLICATION_DATASET_STORE` | Original application data descriptors and captures. |
| `HOSTING_APPLICATION_CUTOVER_STORE` | Original selected source-fence descriptors. |
| `HOSTING_APPLICATION_MIGRATION_INPUT_STORE` | Per-job post-freeze transfer/restore and source-power authority packets. |
| `HOSTING_APPLICATION_JOURNAL_STORE` | Existing delivery and migration child journals. |
| `HOSTING_APPLICATION_RESULT_STORE` | Content-addressed retained migration results. |
| `HOSTING_APPLICATION_CAPACITY_DATABASE` | Existing authoritative SQLite capacity accounting and original event chain. |
| `HOSTING_APPLICATION_SOURCE_ROOT` | Independently accepted installed source/resource closure. |

Other `HOSTING_APPLICATION_` settings are rejected. No setting names a Python
factory, module, command, native credential or runtime worker identity.

The existing independent evidence settings and nonempty protected tenant scope
inventory are mandatory. Startup verifies the original commissioned capacity
envelope/event chain and restored audit/evidence custody for every listed tenant.
`build_action_gate` always constructs the fixed qualification and minimum
operating composition. Its distinct operating Vault trust and existing selected
qualification/provenance/campaign/capacity indexes remain their original owners.
No startup summary grants an action or replaces the fresh per-effect checks.

## One allocation, grant and native-intent composition

`build_application_worker_components(connect, evidence_gate, ...)` requires the
actual scoped PostgreSQL connection owner and `EvidenceMutationGate`. It creates
`PostgresResourceAuthority` and `ResourceTransactions` over the existing capacity
database. `FileResourceBundleStore` rederives the exact pool workload, staging,
snapshot and retained-source purposes rather than trusting advertised totals.

The same `PlannedLeaseAuthority` combines planned OpenStack creation leases with
existing native lease lookup. One `PostgresWorkerGrants` instance uses this mux
and the existing PostgreSQL grant ledger. The fixed operating continuation gate
uses that same grant owner. Supplying a prebuilt grant owner is allowed only if
its PostgreSQL connection, planned lease mux, protected stores and capacity owner
match this composition; the builder never silently repoints a live broker.

`ApplicationNativeProofBindings` accepts explicitly commissioned process-local
resource, creation and existing-native proof readers. They must authenticate
retained evidence and independently reread actual native occupancy, cleanup,
tasks and old-writer exclusion. A boolean, descriptor or returned native ID is
not a proof. The configuration has no way to construct these readers.

With no resource proof reader, reservation still runs through the actual
locked B07/B23 owners and original commissioned envelope. Confirmation and
release always refuse. With no creation or existing-native proof reader, their
native registries are absent and the component summary identifies the missing
dependencies. No affirmative proof default exists; expiry cannot refund an
uncertain resource charge.

## Actual worker enrollment and fixed activities

The default component set contains empty `ProvisioningRuntimeBindings` and
`MigrationRuntimeBindings`. Missing bindings hold before native dispatch.
These maps can contain only the concrete installed `PlannedTerraformRuntime`,
`ObservedProvisioningRuntime`, `DatasetWorkerRuntime` and `SourceWorkerRuntime`
classes, keyed to an exact job and stage/member. A copied certificate fingerprint
or credential in a packet cannot enroll one.

`PlannedTerraformRuntime` requires the actual current process-local mTLS socket
verified by the broker's `MutualTlsWorkerVerifier`, the same current grant owner
and a real enrolled `VaultDynamicCredentialIssuer`. Its independent creation
reader, native project/catalog verification and saved-plan/source/input checks
remain mandatory. Transfer and source-power runtimes likewise must be supplied
by the trusted installed enrollment/credential owner. The composition does not
create a listener, authenticate forwarded identity headers, hydrate a runtime
from JSON or guess native sessions from files.

After that real owner has enrolled runtimes against the composed owners,
`components.with_enrolled_bindings(...)` returns a new component set for
registration before worker startup. It checks the exact shared B10/B11 connection,
grant and independent proof owners. It does not mutate an active worker, grant a
credential or recover an owner epoch.

The registered activity list is fixed: resource reservation and provisioning;
dataset transfer, original reconciliation, join and inspection; source fence;
rehearsal, final sync, cutover and recovery inspection. Only bounded admitted
references and retained evidence digests enter Temporal history. Native effect
activities run once; interruption or a lost result requires original-operation
inspection. See the [application migration runtime](application-migration-runtime.md)
and [job-bound resource owner](job-bound-resource-transactions.md).

## Read-only graph and dependency display

The installed graph command reads only explicit protected stores:

```sh
hosting-application-runtime graph --selection-digest "$selected_artifact_digest"
```

`--job-id` optionally labels binding availability for that original job. This is
a local graph display, not job authentication or admission. It verifies the
selected artifact, delivery graph, rederived resource descriptor and exact data
and source-fence descriptor digests/scopes without a PostgreSQL or native call.
It displays stage IDs, kinds/dependencies, dataset consistency-group joins,
bounded parallel batches, source members and fixed missing-owner reasons.
Commands, packet filenames, source/target paths, tokens and secrets are omitted.

The display reports `READ_ONLY`, `nativeExecutionAuthorized: false` and
`productionActivationAuthorized: false`. A process-local owner binding is
displayed as requiring current authorization. Missing or changed stores return
a sanitized `HELD` result naming the setting/dependency, with exit status `2`.
The module entrypoint supports the same command when invoked through the
accepted installed Python environment.

## Explicit remaining holds and verification

The component summary reports missing **enrollment** for independent resource,
creation/native observation, planning, per-command guest, lifecycle, database,
cold-capture or recovery owners separately. Concrete implementations now exist;
missing process-local native owners still hold before dispatch. Register the fixed
owner set once, seal it before worker registration and commission its exact
source/wheel/interpreter, grant database, custody and native product tuples.
The application workflow cannot succeed with an absent required owner, unknown
native outcome, expired/revoked permission or unaccepted final proof.

Separate staging/cutover, PostgreSQL17 sync, cold image capture and post-write
forward repair are explicit purposes. None grants unimplemented Windows/cold
boot, warm-VM or additional directed migration support. The cold capture purpose
ends `IMPORTED`; final code, native campaign and receiving-owner acceptance remain
independent requirements.

`tests/provisioning/workflow/test_application_runtime.py` executes real SQLite
chain checks, the actual fixed gate construction with a synthetic Vault transport,
canonical descriptor parsing and a real graph CLI subprocess. It checks store
permissions/replacement, corrupted capacity history, independent custody/trust
refusals, exact disabled-dispatch plan checks, empty native holds and immutable
typed binding without crossing grant/proof owners. Its deliberately refusing
native proof fixtures cannot establish a positive native outcome. PostgreSQL
durability/RLS, deployed mTLS/Vault roles, estate commissioning and each actual
directed migration/method campaign remain separate acceptance gates.
