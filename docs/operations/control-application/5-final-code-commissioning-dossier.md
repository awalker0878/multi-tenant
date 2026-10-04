# Final-code commissioning dossier and acquisition sequence

The installed read-only dossier maps every directed method/profile row to actual
current native tuples, implementation owners, required assertions and operating
inputs. It never contacts an estate, dispatches a job, updates qualification,
issues a credential or accepts a release. The checked-in native qualification,
target-selection and campaign indexes currently contain no commissioned records.
There is consequently no actual native tuple ID to fill in on their behalf.

Use the exact accepted installation's Python, with protected
`HOSTING_APPLICATION_RUNTIME_CONFIG` and `HOSTING_APPLICATION_SOURCE_ROOT`.
The command rehashes the original configuration, wheel, installed source/files
and running interpreter before and after preparing its output:

```bash
python -m provisioner.qualification.commissioning --qualification-index /etc/hosting/qualification/native-index.json --provenance-index /etc/hosting/qualification/provenance-index.json --campaign-index /etc/hosting/qualification/campaign-index.json --selection-index /etc/hosting/qualification/target-selection-index.json --capacity-index /etc/hosting/qualification/capacity-index.json
```

Repeat `--specification /etc/hosting/campaigns/exact-directed-campaign.json` for
each independently selected campaign. With no specifications, the output retains
all missing direction/method/profile slots. With specifications, it adds each
original workload/job/plan binding, exact canonical tuple SHA-256, source and
destination selection, current metadata assessment and every required original
observation. A different code/artifact, duplicate route row or malformed custody
index holds the command. Missing tuple choices remain empty, rather than guessed
platform versions or invented campaign identities.

The JSON includes all 216 currently declared direction/method/profile rows,
including generic Linux/Windows and restricted devices. Even a complete metadata
assessment remains `COMMISSIONING_HELD` until the separate original-byte intake,
native qualification, operating acceptance and pilot owners finish their work.
`originalNativeProofVerified` remains false in this read-only dossier. Its current
qualification bundle digest is a binding for review, not action approval.

## Separate routes and methods

Each exact tuple pair, endpoint pair, method, profile and final installed artifact
needs its own original campaign. The dossier reads the installed implementation
map each time; this table describes the present declared boundaries.

| Directed family/method | Required acquisition boundary |
| --- | --- |
| VMware/NSX → OpenStack, application rebuild/restore, `linux-ubuntu-2404` | First declared driver `openstack-linux-rebuild/1`; use the actual admitted application workflow, scoped dataset/source/target owners and independent native observations. Missing commissioned owners still hold execution. |
| OpenStack → VMware/NSX | Select fresh reversed endpoint/tuple/action authority and separate reversed campaign. First-direction evidence cannot qualify it. |
| VMware/NSX → AHV and AHV → VMware/NSX | Select each direction's actual native tuple, resource/guest/transfer/fence and recovery owner. Neither inherits the VMware → OpenStack observations. |
| OpenStack → AHV and AHV → OpenStack | Select each direction independently, including target networking/storage/security realization, source exclusion and target committed-data recovery. |
| VMware → distinct VMware, AHV → distinct AHV, OpenStack → distinct OpenStack; same-family relocation | Retain distinct endpoint/topology/resource evidence, lineage and interrupted move recovery. Same-resource no-op is a required negative. |
| Cold whole-VM, each of the six cross-platform directions | Actual cold capture/export and complete disk chain; device/encryption/shared-disk negatives; isolated digest-bound conversion; actual target import, firmware/driver remediation and observed boot. A converted standalone disk is insufficient. |
| Application-native database sync, each of the six cross-platform directions | Exact database engine/version; consistent initial copy; actual commit positions, lag cutoff, divergent-writer exclusion and post-write reverse-sync/repair. File-transfer evidence cannot qualify database replication. |
| Warm whole-VM, each of the six cross-platform directions | Actual convergence/storage/bandwidth limits, stop threshold, RAM/device/key-state preservation and target service recovery. Missing native state preservation remains an implementation hold. |
| `windows-server-2022`, another exact Linux release, appliances, GPU/passthrough, encrypted/vTPM or shared disks | Each has its own installed implementation and method/profile evidence requirement. A broad `LINUX`/`WINDOWS` category or a Linux disk-conversion test cannot authorize these guests. |

`routeRows[].implementedDriver` and `implementedOwners` show the actual current
code declaration. A null driver is an implementation hold even if someone
supplies an otherwise valid dossier. `requiredAssertions` preserves the method's
actual procedure IDs. Native concurrent waves additionally require the four
separate `explicitWaveAssertions`; one application job cannot supply wave
dependency, fairness, shared-risk or resource-stop evidence.

## Roles, concrete inputs and installed commands

The dossier's `acquisitionStages` supplies the exact command/runbook mapping.
Obtain actual inputs in the following order under the site's existing authority:

1. Platform owners and source/destination security, contact/change/stop authority
   select two restricted disposable native scopes. Retain the exact product,
   version, API, API version, automation-provider, hardware and license tuple;
   site/cell/edge/network/storage/OOB realization; independent observer scope;
   current contact window; permitted/prohibited operations; credential custody;
   evidence workspace and cleanup authority. Run the existing target-selection
   and version-provenance validators. They check exported records and grant no
   contact permission. See [actual target selection](../../engineering/actual-target-selection-assurance.md).
2. Independent native observers acquire the real per-action/profile controls
   under that explicit restricted contact authority. The qualification owner
   separately reviews each tuple's dossier and the site's commissioned capacity
   envelope. Every selected action requires its own `ACTION_<kind>` observation
   and `action_variant` of the actual selected artifact. The dossier lists the
   exact endpoint and portable capabilities for each action. These preliminary
   action controls precede the first controlled full application migration; a
   generated full-migration result cannot bootstrap its own qualification.
3. Backup/restore and independent custody owners execute real observation-only
   archive recovery, reconcile independent evidence and original Temporal run
   prefixes, and retain all nine minimum B44–B46 prerequisite observations. A
   distinct operating owner accepts those exact facts. Execute the fixed approved
   HA switchover only with separate old-primary restart/delayed-request exclusion.
   Commission the actual instance under its OID/system identifier and current
   installed identity. See [HA and restore drills](3-controlled-ha-and-restore-drills.md).
4. `SOURCE_OWNER`, `DESTINATION_OWNER`, `SOURCE_SECURITY` and
   `DESTINATION_SECURITY` approve the exact current plan. A distinct authenticated
   `EXECUTION_OPERATOR` submits it through `POST /v1/plans/{exact-plan-id}/jobs`
   with its stable idempotency key. Pin the actual returned job ID, original start
   payload digest and acknowledged Temporal run. Inspect `GET /v1/jobs/{id}` and
   `/events`; bind the campaign specification to those original values. The
   installed runtime graph/run sheet can be inspected before any effect.
5. The trusted enrollment owner supplies the actual mTLS worker, current grant,
   lease and native credential custody to the concrete resource, provisioning,
   transfer, source fence, lifecycle and recovery owners. Start the installed
   application worker only after that composition is commissioned. Run the
   declared method through the original admitted Temporal application path.
   Empty bindings or missing independent proof readers remain held. See
   [worker composition](../../engineering/application-worker-composition.md).
6. For every procedure and endpoint, the independent observer retains the
   actual measurements/native responses and separate signed envelope. Preserve
   earlier healthy same-endpoint positive controls for all negatives. Use
   `qualification.intake` to stage a fresh review candidate, then the existing
   campaign/native/mobility validators for the separately administered indexes.
   The intake contract and exact commands are in
   [original final-code evidence](4-original-final-code-evidence-intake.md).
7. Rehearse B48 over authentic original retained state, independently verify
   counts/digests/native IDs/history/high-water and old-writer exclusion, and
   accept its separate scoped native epoch handover. It cannot activate the
   operating instance. Delete superseded paths only after their consumer/state
   conversion is proven; install the resulting exact final artifact and rerun
   every affected directed campaign. See
   [authenticated retained handover](../retained-state-authenticated-handover.md).
8. Actual sysadmins and the receiving team execute all six pilot scenarios on
   that final artifact/support matrix. An independent observer supplies original
   scenario proof, a separate receiving/change authority signs pilot acceptance,
   and a different release owner prepares the supported artifact. Publication
   and production authority remain their separate owner decisions.

The installed tenant dispatcher chooses the oldest due outbox job. Its `--once`
flag does not select the dossier's job ID. A restricted campaign must use an
independently isolated exact campaign outbox or a separately reviewed exact-job
dispatch owner. The commissioning command does not dispatch and exposes no
arbitrary callback, shell or endpoint override.

## Database method commissioning boundary

The dedicated `openstack-linux-application-database/1` selection pins the actual
PostgreSQL 17 source and target system identifiers, databases, TLS endpoints,
protected trust bundles, table/column/key shapes, original guest UUIDs/machine
IDs, workload dataset/member, target reference and consistency group. The
approved canonical workload must describe a database dataset; a file mapping
cannot substitute for this method. Each endpoint also selects a distinct
independent native `readRole` alongside its writer `ownerRole`.

The native commissioner installs SQL0033's private journal/fence helpers on the
two selected database engines. The restricted non-login helper owner needs
`CREATEROLE` and `ADMIN` only for the selected unprivileged application writer
roles, with their `INHERIT` and `SET` membership options disabled. It also needs
the reviewed statistics/backend-termination permissions. The installed native
source, target and fence operational roles remain separate non-administrator
roles; the operational session never falls back to the commissioning role.
PostgreSQL documents the requirements for
[altering roles](https://www.postgresql.org/docs/17/sql-alterrole.html) and
[terminating backends](https://www.postgresql.org/docs/17/functions-admin.html#FUNCTIONS-ADMIN-SIGNAL).
The disposable engine fixture's setup administrator is not production helper
commissioning or native migration qualification.

Before the first selected SQL command, the enrollment owner supplies all three
original grants: source `RESTORE_DATA`, target `RESTORE_DATA`, and source
`SOURCE_FENCE`. Source and fence intentionally use the same enrolled source
dataset owner/current lease epoch, with separate grants and Vault SQL roles.
Target owns its independently selected native dataset. The installed
`DatabaseOperationContext` and `OperationsActionGate.require_database_continuation`
verify every actual mTLS peer, current grant, native owner, request digest and
selected intent under the same control-database transaction. Missing/PREPARED
selected intents waive no hold; only the exact job's verified
`IN_FLIGHT`/`TASK_ACCEPTED` intents can continue. An uncertain selected intent,
unrelated work, containment, withdrawn grant or expired peer stops commands.

Acquire separate `ACTION_RESTORE_DATA` proof on both endpoints. Source additionally
qualifies capture/export and consistent snapshot capabilities. Every mutating
database action also requires all seven database method assertions on both exact
tuples, bound by
`provisioner.qualification.action_gate.database_method_variant(selected_artifact)`.
Load that artifact through the protected `FileExecutionSelectionStore` with its
approved compact canonical artifact digest. The variant binds the dedicated
driver, direction, tuples, profile, code, scopes and exact
`applicationDatabaseSelectionDigest`. Generic restoration or rebuild method
proof cannot satisfy it. `databaseMethodPrerequisites` in the read-only dossier
lists the actual assertions and variant owner. These preliminary restricted
method controls do not replace final `MobilityCampaign` evidence with the actual
original job/plan/final wheel, independent exclusion/commit observers or pilot
acceptance. Source retention remains held until the separately observed native
writer credentials are revoked and the original reader/replication state is
retired under current authority.

## Hold disposition

Commissioned estates, actual independently enrolled observers/signers, real
old-writer exclusion, current scoped credentials, retained Temporal state,
useful application probes, receiving-team pilot acceptance and release signing
custody are external gates. A missing installed method/profile owner is a code
gate. The dossier distinguishes both and supplies the next owner/procedure; it
does not close either with repository, loopback TLS, local engine or synthetic
PostgreSQL results.
