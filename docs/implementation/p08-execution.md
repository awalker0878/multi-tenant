# P08 — Native migration implementation

P08.01–P08.05 implement R17/R21–R24/R31/R33 through Inventory discovery,
Lifecycle's durable native coordinator and isolated Lifecycle workers. The accepted
[native migration design](p08-native-migration.md) remains authoritative.

## Source readiness and capture

The read-only `VmwareWorkloadDiscovery` consumes an enrolled VM allowlist and a
commissioned VI JSON endpoint. It observes immutable identity, versions, compute,
firmware, Tools, all disks/backing chains/controllers, NIC/network fingerprints,
snapshot tree and clone capabilities. A second configuration read detects drift.
Application datasets, dependencies, consistency and objectives remain explicit
owner inputs. Missing native facts produce holds; metadata does not establish
qualification. This component still needs Inventory/Console profile persistence
and the actual commissioned source tuple.

`VmwareCapture` submits one disk-only S0 snapshot and one exact-S0 clone through
native task APIs. It requires a stopped source, matching configuration, snapshot
support and host clone capability. All NICs and removable media are removed in
`CloneSpec` before creation, and the powered-off distinct clone's disk/controller
mapping is read back. No source NIC is changed and this adapter never powers on
production. RDM, independent/shared/encrypted disk and special-device profiles
are held for separately qualified handling. Task receipts survive uncertainty;
a task ID is observed rather than resubmitted after a lost outcome.

## Retained archive, conversion and native image import

`MigrationArchive` resolves the isolated clone from the same tenant/job/approved
capture intent in the worker's append-only journal. It transfers every disk into
private retained custody with byte/rate/deadline limits and verifies the native
manifest. It calls `OvfManager.CreateDescriptor` using the downloaded filenames and
sizes, rejects descriptor findings, external entities and incomplete/unsafe file
or disk references, and retains the descriptor before completing the NFC lease.
A failure keeps the partial archive and original lease identity; no new lease or
range resumption is attempted automatically.

`MigrationConversion` resolves only a completed archive. `CopyConverter` runs a
pinned QEMU artifact inside a pinned bubblewrap sandbox with a read-only rootfs
mount, isolated network/namespaces, no inherited credentials, read-only source and
one new output directory. Only explicitly selected RAW/QCOW2 conversion of
self-contained streamOptimized/monolithicSparse VMDK is admitted. The worker checks
virtual sizes, output metadata, QCOW2 consistency and guest-visible sector equality,
then hashes the original and converted files. It has no salvage, repair, in-place
conversion or method fallback. The current tests exercise a synthetic engine and
command contracts; they do **not** qualify the actual QEMU/bubblewrap runtime.

`MigrationImport` resolves the same job's completed conversion receipt, verifies
all disks before creating any image, and uses the explicitly selected Glance-direct
route. Image UUIDs, format, firmware and disk bus are fixed in the immutable intent.
The existing native OpenStack creation adapter can consume those image identities
for Cinder/Nova. Target guest readiness, quarantine readback, activation and native
acceptance remain independent requirements. The TLS campaign uses synthetic image
bytes; it does not boot a guest or qualify an installed image backend.

Artifact handoffs are references to prior immutable stage-intent digests. The
worker resolves native clone/operation identities from its journal under the same
job, tenant, source plan, epoch, scope and custody generation. Unknown, duplicate,
partial or cross-job receipts hold the next stage. Completion binds the aggregate
all-disk digest; additional disk events after completion are rejected. No payload crosses the control
API, Console or event bus. The current single activity is bounded to ten minutes;
large transfers need separately qualified chunk/range reconciliation rather than
an implicit longer timeout or blind restart.

## Migration control and recovery

Version 2 admission binds source/target profile identities, every disk/dataset,
exact method, conversion/guest/delta/recovery artifacts, independent approval,
owner objectives and rehearsal/recovery references. All five design methods have
explicit ordered contracts; admission still requires the commissioned owners'
current qualified-method and complete-dataset evidence. A method contract is not
an implemented or qualified application-specific adapter.

Rehearsal has no business-write stage. Cutover requires independent all-writer
fencing, final synchronization, source shutdown, target integrity, guest/services,
backup restore, security paths and current change authority. Guest-dependent
final delta precedes shutdown. Cold migration requires continued source shutdown
and fencing during movement. No failed method selects another method.

The append-only `native_migration_writes` row commits with activation grant
redemption, before the first possible target write. An uncertain activation
response therefore requires post-write recovery. A new recovery plan needs a
separate approval, newer custody generation and the same method/datasets/native
identities. Admission atomically stops the prior workflow. Provider-side stale
request exclusion and independent drain remain mandatory owner observations.
Pre-write source return requires target fencing and no divergence. Post-write
forward/reverse recovery requires retention of accepted target changes. Cleanup
has separate authority and cannot retire the source.

Worker custody generations are append-only and bind tenant/site/project/resource/
ownership scope. Multiple separately authorized stages share an admitted job;
a new job requires a newer independently authorized generation. Older generations
and cross-scope attempts are denied. Lifecycle remains the stage-order authority;
worker journal possession does not authorize an effect.

## Current qualification boundary

The [retained index](../../verification/p08/qualification-index.json) verifies
original source-bound archives, reports and command logs. At source
`a72d0e88b3626b6912cf189c46ce45cf2fc4878c`, the hosted campaign passes all 20
static/type/build/schema/test commands: 295 Lifecycle, 204 worker and 59
Inventory-worker tests, with no skips or failures. It verifies 262 source bindings.
The [check matrix](../../verification/p08/check-matrix.md) separates real
PostgreSQL/TLS/subprocess checks from synthetic native and current-owner peers.
The earlier strict-type failure remains FAILED in the original evidence, with
its correction and rerun recorded separately.

Real PostgreSQL checks run in the established hosted campaign because this local
container cannot create the required unprivileged database account. Missing-engine
local skips are not passing. The converter launcher sets limits in a fresh isolated
interpreter instead of a multithreaded-fork hook. Actual subprocess bounds and
cancellation are tested; a QEMU/bubblewrap rootfs and guest remain unqualified.

The [completion packet](p08-completion-review.md) and
[custody runbook](../operations/runbooks/native-migration.md) give the concrete
remaining obligations and recovery procedure. Remaining implementation includes profile persistence and Console admission,
commissioned capture/conversion/native-readback composition, concrete guest/service/
delta/traffic/recovery adapters and a composed native Q07 journey. Source and target
profile components distinguish observed facts from further capability evidence;
only genuinely API-unavailable values should become manual administrator inputs. Installed tuples, scoped identities, independent owner protocols,
application dataset/objective definitions and native fencing are not supplied.
P08 and G08 remain incomplete; software checks cannot supply those inputs or actual
Q07/G08 receiving decisions.

## Native references

Reviewed 2026-10-07 against Broadcom's VI JSON contracts:
[CloneVM_Task](https://developer.broadcom.com/xapis/virtual-infrastructure-json-api/latest/sdk/vim25/release/VirtualMachine/moId/CloneVM_Task/post/),
[CreateSnapshotEx_Task](https://developer.broadcom.com/xapis/virtual-infrastructure-json-api/latest/sdk/vim25/release/VirtualMachine/moId/CreateSnapshotEx_Task/post/), and
[CreateDescriptor](https://developer.broadcom.com/xapis/virtual-infrastructure-json-api/latest/sdk/vim25/release/OvfManager/moId/CreateDescriptor/post/).
These are documentation references, not installed-release qualification.

The converter options were checked against the [QEMU image utility documentation](https://www.qemu.org/docs/master/tools/qemu-img.html)
and [bubblewrap command reference](https://github.com/containers/bubblewrap/blob/main/bwrap.xml).
These references do not select or qualify an installed runtime.
