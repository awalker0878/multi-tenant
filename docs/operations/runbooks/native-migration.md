# Native migration component custody and recovery

Owner: Lifecycle/Infrastructure. Packages: P08.01–P08.05. This procedure describes
implemented component boundaries and the prerequisites for commissioning them.
It does not enable a native deployment. Use the
[P08 completion packet](../../implementation/p08-completion-review.md) for the
remaining integration and native acceptance work.

For all source/destination combinations, use the [any-to-any extension](any-to-any-migration.md)
and [current directional matrix](../../implementation/p09-any-to-any.md). The VMware/OpenStack
sections below describe the original custody path; P09-A adds AHV sources, VMware
destinations, copy-only guest preparation and typed independent outcomes.

## Collect and confirm migration profiles

Apply Inventory migrations through `005_workload_profiles.sql` with its schema
owner. Enable the enrolled `source_profile` stream after scoped server discovery,
with the exact four-part VI JSON release and approved VM allowlist. The detailed
source stream and listing must use the same host, addresses and trust. Enable the
OpenStack `target_profile` with the explicitly approved Glance v2 root alongside
the enrolled Nova/Cinder/Neutron version/configuration streams. Every native GET
requires a fresh worker read permit under the collection lease and endpoint budget.
Only a complete generation publishes immutable profiles; partial/changed/revoked
collection remains held. This setup supplies no native write credential.

Open **Configure porting → Migration readiness review**. Select current source and
target observations and one explicit method, map every disk into owner-defined
datasets, and supply the application references and objectives the APIs cannot
discover. Save and confirm the exact revision. API facts cannot be overridden.
A lost response offers the same command key/payload; a changed or expired profile
requires a fresh collection and review. A confirmation is not migration approval.

The [Planning preparation contract](../../../contracts/openapi/planning-migration-v1.json)
requires current scoped `plan.create` delegation. It re-reads the confirmed Inventory
revision and validates each target disk key/format against observed source disks and
target formats. Preserve the returned review and owner-input digests in the complete
native plan. Lifecycle rechecks the full Inventory receipt at admission. Commissioned
stage intents, qualification, separate approval and native custody are still required.

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

Image import requires separate writer/observer project credentials on identical
enrolled OpenStack service URLs and address pins. The worker checks credential
separation before effects. Rotation or expiry during a Glance upload stops before
the next chunk and holds the attempt, including when the provider's final response
arrives after rotation. Preserve the staged object and receipts for independent
reconciliation. A truncated or ambiguously framed native response is unconfirmed;
it cannot justify continuing, completing an import or replaying a request.

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

Version 1 movement intents retain a 600-second limit. Explicit version 2
archive/conversion/import intents accept up to 86,400 seconds; shorter plan, profile,
credential or campaign expiry still wins. Budget hashing and conversion as well as
payload movement. Interrupted workloads require implemented, qualified reconciliation;
a longer budget or restarting an unknown lease is not resumption. Staging failures retain partial files
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
The command runs static/type/build/schema checks and all five Python test suites.
It records exact source and command-log digests, original JUnit results and failures.

After installing the exact Console lock and Chromium, run
`python scripts/p08/qualify_browser.py --output /absolute/private/browser-report`.
This exercises the actual Vue/Inertia page with an isolated HTTP fixture. It checks
disk mapping, confirmation, unchanged uncertain retry, stale/revoked access and
narrow viewport behavior; service persistence and authority have separate tests.

The [retained index](../../../verification/p08/qualification-index.json) is E2 only.
Its native responses and application/owner peers are synthetic; converter command
fixtures do not boot a guest or qualify a QEMU rootfs. Real subprocess limit tests
exercise only launcher containment. Follow Q07 and G08 for actual native acceptance.

## Discover and group source machines in the Console

1. Open Site inventory → Migrate to OpenStack. Choose an enrolled VMware connection
   and Refresh from API. After collection completes, Refresh findings. A failed or
   partial discovery does not publish a new current generation.
2. Filter and group the discovered list; Load more source VMs as needed. Select VMs
   individually or by visible group/filter. Filters do not discard existing selections.
3. Save a named group with its catalogue application/environment, observed OpenStack
   target and supported disk format. Group selection can include held machines for
   review; a source with no detailed profile cannot prepare. Enable its detailed
   profile stream within the commissioned enrollment scope and recollect.
4. Use Review VM for each member, account for every disk/dataset and supply the
   application inputs the native APIs cannot determine. Save and confirm each review.
   A newly collected profile requires fresh confirmation and, if identity changed,
   explicit group resaving after review.
5. Reopen the group and Prepare group for OpenStack. Inspect each prepared binding or
   hold. An unavailable owner or changed group pauses the batch; refresh before retry.
   Preparation performs no native writes and can be rerun with current inputs. The
   complete-plan, approval, rehearsal, cutover and recovery procedures still apply.
