# P08 — VMware to portable-target migration design

P08 implements migration after P07's independently qualified native provisioning
path. Native platform APIs are authoritative for both source and target. Terraform
is not a product execution dependency. VDDK is optional only for a separately
approved, entitled external adapter; baseline discovery, capture and export do not
require it. The initial qualification route is VMware → OpenStack; Nutanix and
another VMware environment require their own destination adapters and campaigns.

## Profiles and immutable plan

Inventory produces a normalized `SourceWorkloadProfile` from vSphere: immutable
VM/vCenter identity, installed versions, guest OS and Tools status, CPU/RAM,
disks/controllers/backing chains, snapshots, BIOS/UEFI, NICs/MACs, encryption and
key custody, datastores, distributed switches/networks and observed dependencies.
Unobservable application details remain explicit owner inputs.

Destination APIs produce `TargetCapabilityProfile`: compute/storage limits,
accepted disk formats, firmware and device models, guest drivers/agent support,
metadata/config-drive/cloud-init, network/security capabilities and service
attachments. Console presents discovered values for administrator validation,
reasoned overrides and completion of undiscoverable fields.

The immutable `MigrationPlan` binds both identities/profiles and exact versions,
one selected method, every disk and target resource, conversion artifacts and
options, transformation requirements, consistency/delta boundary, data custody,
capacity/bandwidth/outage estimates, validation and recovery requirements, source
fencing, actor/executor scope, approval and authorization epoch. Unknown mandatory
capabilities hold the plan. A new method requires a new reviewed plan.

## Explicit method selection

These are distinct qualification scopes, not a retry/fallback chain. Planning may
recommend one method from the discovered requirements; execution uses only the
approved method and never substitutes another after failure.

| Method | Required condition | Authoritative data boundary |
| --- | --- | --- |
| `APPLICATION_REBUILD_RESTORE` | Complete reproducible application/configuration and consistent data restore | Owner-approved application capture and restore; no whole-VM preservation claim |
| `VM_SNAPSHOT_BASELINE_APP_DELTA` | Supported application-native replication/export or transaction-log delta | Snapshot S0 baseline plus verified final application delta |
| `VM_SNAPSHOT_BASELINE_FILE_DELTA` | Filesystem synchronization is valid for all declared data and metadata | Snapshot S0 plus bounded initial/incremental synchronization and verified final delta |
| `VM_COLD_EXPORT` | No qualified delta mechanism; accepted full-export outage | Source remains stopped/fenced for the complete authoritative export/import |
| `EXTERNAL_BLOCK_REPLICATION` | Separately approved, entitled and qualified block-copy integration | Exact adapter's documented block consistency, change tracking and recovery boundaries |

Restarting production after baseline capture is admissible only with an explicit,
qualified delta strategy. A generic opaque VM without one uses cold migration and
its longer measured outage. File copying alone does not establish database consistency.

## Capture, export and conversion

1. Check source/destination authority, capacity, network budget, encryption,
   compatibility, application consistency and recoverability before capture.
   Exact-snapshot cloning requires the source host's `cloneFromSnapshotSupported`
   and the VM's `snapshotConfigSupported` capabilities. Bind encryption keys and
   any virtual TPM handling explicitly; unknown clone capabilities hold capture.
2. Stop the application cleanly, gracefully shut down and independently confirm
   `poweredOff`. Create a disk-only snapshot S0 with memory capture disabled and
   journal its native task/result and snapshot identity.
3. For an admitted delta method, restart production and verify application health.
   For cold export, retain the source outage and fence through the authoritative
   capture and cutover. Never restart solely because baseline capture succeeded.
4. Invoke `CloneVM_Task` from the exact S0 with `powerOn=false`. Bind the returned
   clone to S0 and verify every production NIC is disconnected and cannot connect
   at boot. No duplicate production identity may become reachable. Unsupported
   clone-time isolation holds capture; it does not allow a briefly exposed clone.
5. Confirm the isolated migration clone is powered off, invoke `ExportVm` once and
   journal its `HttpNfcLease`. Wait for ready and obtain every disk URL. An optional
   native OVF descriptor dry run may check export compatibility before transfer.
6. Maintain lease progress while the data mover transfers bounded, throttled chunks
   over verified TLS between approved endpoints. Retain lengths, secure digests,
   disk mappings and progress. Verify the native manifest after disk transfer and
   generate the final descriptor through `OvfManager.CreateDescriptor`, using the
   actual downloaded file names and sizes. Resolve descriptor errors and required
   warnings before completing the lease; retain the complete descriptor and disks.
7. Inspect the VMDK subtype and run only the plan's pinned conversion on the
   migration copy when required: VMDK → RAW or QCOW2. Validate the resulting disks,
   virtual sizes and new digests. Conversion is an explicit method step, never an
   automatic response to native import failure. No conversion modifies production.

A source snapshot is not a delta engine. Native lease completion releases its
VM-operation exclusion; independent source-writer fencing must survive it.
Interrupted work retains the original task/lease/object identities and custody.
Resume requires reconciled byte ranges, immutable source and renewed authority;
an unknown export, clone, image import or conversion is never blindly repeated.

## Target import and guest transformation

For OpenStack, the approved route selects Glance image import or Cinder volume
import from actual native capabilities; it does not try one after another fails.
Nova creates the target with exact CPU/RAM, firmware, boot/data volume order,
NICs, security attachments and required metadata/config-drive. The target boots
in quarantine with production ingress and business effects suppressed.

All migration-specific guest changes occur on the destination copy: storage and
network drivers, initramfs and boot configuration, BIOS/UEFI support, qemu guest
agent, applicable cloud-init and VMware-specific integration removal. If the guest
cannot boot before driver preparation, the approved isolated conversion/guest
worker must prepare the copied disk before the first boot. Preserve tools needed
for remaining guest operations until those operations are complete. Generic Linux
and Windows transformation require separate profiles and evidence.

## Delta, cutover and recovery

For application/file delta methods, keep production authoritative while the
baseline is copied and transformed. At final cutover, block new workload changes,
fence all writers, stop the application, and establish the approved last-write
boundary. Apply the final delta before shutdown if the selected synchronization
method needs a running guest; otherwise use its approved offline access path.
Gracefully shut down and verify the source state before target write admission.
A shut-down guest cannot supply a guest-agent-dependent final delta.

Independently verify OS/filesystems, agent, all data and metadata, guest/application
health, service attachments and allowed/denied security paths. Only current
approval plus passing acceptance checks can enable target writes, production
networking, monitoring/backup, load-balancer and DNS changes. Journal the first
possible target write. Source remains fenced/off for the defined retention period.

Before target writes, source service can return only after target fencing and
verification that no divergent writes were accepted. After actual or possible
target writes, preserve those changes and require explicit forward recovery or
qualified reverse synchronization; never blindly power on the old source.

## Cleanup and evidence

Under separate scoped authority, remove the migration clone and S0, independently
confirm snapshot consolidation, revoke migration credentials and remove temporary
buffers/conversion artifacts. Retain source/destination identities, artifact and
payload digests, task/lease receipts, failures and original observation evidence.
Successful migration never implicitly retires the source.

## Implementation order

| Increment | Delivered capability and acceptance scope |
| --- | --- |
| M1 | VMware discovery adapter and normalized source/target profiles |
| M2 | Power, snapshot and exact-S0 isolated clone adapters with task reconciliation |
| M3 | ExportVm, NFC lease lifecycle and native OVF descriptor generation |
| M4 | Data mover, throttling, byte/digest/progress journal and reconciled resumption |
| M5 | VMDK inspection and isolated pinned conversion worker |
| M6 | Exact Glance/Cinder/Nova import and native object readback |
| M7 | Quarantined target boot and native mappings |
| M8 | Copy-only guest transformation and agent/driver profiles |
| M9 | Independent target validation and activation boundaries |
| M10 | Application-native/file-delta framework and final consistency receipts |
| M11 | Both recovery boundaries, retained data and explicit cleanup workflows |
| M12 | VMware → OpenStack Q07 qualification campaign |
| M13 | Separately qualified VMware → Nutanix / VMware destinations |
| M14 | Optional approved external block-replication adapters; VDDK only if entitled |

The [implementation record](p08-execution.md) now covers read-only profile
components, disk-only S0/isolated exact-S0 capture, retained NFC/OVF archives,
copy-only conversion, explicit Glance import and durable migration/recovery
control. Component qualification uses synthetic native peers; the conversion
engine/guest, owner protocols and composed Q07 journey remain unqualified.
The [completion packet](p08-completion-review.md) separates unfinished software
from actual commissioning/receiving inputs. P08 and G08 remain incomplete; these
components supply no P07 installed-platform acceptance evidence.

## Native contract references

- [Clone specification and exact-snapshot capabilities](https://developer.broadcom.com/xapis/vsphere-web-services-api/latest/vim.vm.CloneSpec.html)
- [VirtualMachine export contract](https://developer.broadcom.com/xapis/vsphere-web-services-api/latest/vim.VirtualMachine.html#exportVm)
- [NFC lease lifecycle](https://developer.broadcom.com/xapis/vsphere-web-services-api/latest/vim.HttpNfcLease.html)
- [OVF descriptor generation after downloaded file mapping](https://developer.broadcom.com/xapis/vsphere-web-services-api/latest/vim.OvfManager.html)

Commission the installed release against these contracts; documentation for the latest
release does not establish that an older source or target exposes the same capabilities.
