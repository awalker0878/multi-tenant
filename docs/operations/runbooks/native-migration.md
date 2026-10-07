# Native migration component custody and recovery

Owner: Lifecycle/Infrastructure. Packages: P08.01–P08.05. This procedure describes
implemented component boundaries and the prerequisites for commissioning them.
It does not enable a native deployment. Use the
[P08 completion packet](../../implementation/p08-completion-review.md) for the
remaining integration and native acceptance work.

## Control and worker setup

Apply Lifecycle migrations through `006_migration_boundaries.sql` with the schema
owner and worker native migrations through `003_conversion.sql` with the separate
worker schema owner. Runtime has append-only write-marker/custody permissions;
it cannot erase attempts, advance its own authority or delete evidence to retry.
Do not combine Lifecycle and worker database credentials.

Migration admission uses the version 2 plan/grant and
[boundary contract](../../../contracts/openapi/lifecycle-migration-boundary-v2.json).
The [worker contract](../../../contracts/openapi/worker-migration-effect-v2.json)
binds every effect to its exact operation intent, job, tenant, native scope,
authorization epoch and custody generation. Version 1 provision contracts remain
separate. The fixed TLS routes transmit bounded metadata only.

`CommissionedMigrationRuntime` resolves only an explicitly registered intent
hash to its adapter and independent observer. Install actual current-owner and
caller-trust implementations and provider fencing before dispatch. An absent
registry entry holds the effect; never substitute a generic command runner or
synthetic observer. The simulation deployment does not activate this runtime.

## Data custody

1. `VmwareCapture` requires a stopped source and exact current native profile.
   It journals the disk-only snapshot/task and exact-S0 clone/task. Clone creation
   removes NICs/removable media and keeps power off. Observe a recorded task rather
   than resubmit it if the response is uncertain.
2. `MigrationArchive` resolves the same job's approved capture receipt. Use an
   absolute private spool directory with no symlink components. It creates an
   exclusive operation directory, moves only the declared disks over verified TLS,
   checks the native manifest, and retains the OVF descriptor before lease completion.
3. `MigrationConversion` resolves the exact completed archive and `MigrationImport`
   resolves the exact completed conversion. The journal checks tenant/job/plan/
   scope/epoch/generation and the completed all-disk digest. Unknown, duplicate,
   late or incomplete disk receipts hold the handoff. Rehash retained source and
   output bytes; their paths and metadata are not caller-supplied authority.
4. Provision the converter's protected runtime descriptor with exact sandbox and
   rootfs digests. The rootfs must be mounted read-only. The converter has isolated
   network/namespaces, read-only source, private output and process/file/time bounds.
   Qualify the actual QEMU/bubblewrap artifacts before using them on a guest image.
5. Import uses the plan's Glance-direct route, exact image UUIDs and selected RAW
   or QCOW2 format, firmware and disk bus. All disks are checked before image creation.
   A failed image import never selects another import method automatically.

The activity deadline is at most 600 seconds. Budget whole-transfer hashing and
conversion as well as payload movement. Larger workloads require implemented,
qualified reconciled range/chunk continuation; increasing a timeout or restarting
an unknown lease is not that capability. Staging failures retain partial files
and task/lease/object identities. Secure the spool and retain readable keys under
owner policy until separately authorized cleanup.

## Held outcomes and recovery

Read-only reconciliation remains available when write authority expires. Retain
the original plan, grant, operation/attempt, task/lease/object IDs, profile/artifact
hashes, byte observations and failed response. Do not remove the journal claim or
operation directory, renew a lease blindly, or mark a copy complete to bypass a hold.
Obtain independent native readback and request-drain evidence before a new effect.

A migration's first possible target business write is recorded atomically when
Lifecycle redeems `admit_writes`, before the provider call. Unknown activation
therefore takes the post-write recovery path. A recovery job requires its own
approval, higher custody generation and exact predecessor/method/data/native
identity bindings. Admission stops the predecessor; real provider exclusion and
drain must still be independently established.

Pre-write source return requires target fencing and no divergence. After possible
writes, retain accepted target changes and perform the selected forward or qualified
reverse recovery. The write boundary follows ancestry across subsequent recoveries;
a new recovery ID does not make old-source restart safe. Cleanup may remove the
owned copy/snapshot only under separate authority and verified consolidation,
with source and required data/keys retained. Actual guest, delta, traffic, recovery
and cleanup adapters still need commissioned implementation and Q07 qualification.

## Reproduce software qualification

Run `python scripts/p08/qualify.py --output /absolute/private/report-directory`
from a clean source checkout with locked uv/Python dependencies and
`P07_POSTGRES_BIN` pointing to PostgreSQL 16 executables. A suitable unprivileged
process account is required; missing/skipped PostgreSQL checks are not passing.
The command runs static/type/build/schema checks and all three Python test suites.
It records exact source and command-log digests, original JUnit results and failures.

The [retained index](../../../verification/p08/qualification-index.json) is E2 only.
Its native responses and application/owner peers are synthetic; converter command
fixtures do not boot a guest or qualify a QEMU rootfs. Real subprocess limit tests
exercise only launcher containment. Follow Q07 and G08 for actual native acceptance.
