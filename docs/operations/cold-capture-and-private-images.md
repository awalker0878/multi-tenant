# VMware snapshot capture and private OpenStack images

The installed `vmware-openstack-cold-capture/1` purpose exports one approved,
already existing powered-off VMware snapshot and imports every selected disk as
a private Glance image. Its workflow ends `IMPORTED`. It does not create a VM,
prove boot, change guest drivers, promote a workload binding, or activate traffic.
The ordinary `COLD_VM_CONVERSION` migration remains held until those owners and
their separate native campaigns are accepted.

Before admission, retain a complete native VM/current snapshot configuration,
every disk and backing parent, hardware capacity, native snapshot membership,
powered-off/connected runtime and actual NFC device-key mapping. A label, slot
guess, absent field or unresolved VM question cannot supply a native fact.
Reject encryption, shared/passthrough devices, vTPM, incomplete chains and any
other unimplemented hardware contract. Both Linux Ubuntu 24.04 and Windows
Server 2022 descriptor profiles concern captured bytes only.

The canonical plan binds exactly one complete machine/disk mapping and
`spec.coldCapture={format:hosting-cold-capture-purpose/1,selectionDigest:<sha256>}`.
The independently protected `hosting-cold-capture-artifact/1` binds that selection,
the exact installed source revision, native product tuples, guest profile,
qualification and operations evidence, and counted resource bundle. Its common
scope/workload fields must equal the current approved B09 job. Native credentials
and file paths never enter the workflow input.

Commission these process-local owners before registering the worker:

| Owner | Required live authority and custody |
|---|---|
| `ColdExportAuthority` and `VsphereColdCapture` | Actual worker mTLS, current B10 `SNAPSHOT_EXPORT` grant, one existing B06 VM lease, original B11 intent, independently excluded previous writer, counted source/snapshot/staging receipts, pinned CA and immutable vCenter/NFC origins |
| `VsphereNativeCredentialOwner` | Fresh revocable Vault session per vCenter exchange; native currentSession user/key, actual VM datacenter ancestry and exact `System.Anonymous/System.View/System.Read/VApp.Export` privileges |
| `VsphereExportReadbackOwner` | Separate actual mTLS reader and native principal, current `DISCOVER_READ` authority, original credential/native exclusion owner and private immutable evidence/capture custody |
| `PlannedImageLeaseAuthority` | The same combined staged/image/native B10 owner used by the existing broker, one-time `enroll_cold_resources(coldStore,captureStore,{jobId:exportReader})`, sealed before worker registration |
| `ColdImageEnrollment` and `GlanceImageImporter` | Actual destination worker mTLS, exact counted Glance staging, original captured bytes; genuine planned CREATE and UPLOAD leases and new B10 `SNAPSHOT_IMPORT` grants issued only after original accepted capture |
| `GlanceImageReadbackOwner` | Separate current project reader, pinned Keystone/Glance endpoints and CA, actual native project/reader token, genuine original create UUID and secure image multihash/extent |

Use the existing B09 outbox and `SelectedColdCapture` workflow with
`PostgresColdCaptureSelector`. Register only `ColdCaptureActivities.activities`:
`cold_capture_export`, `cold_capture_import`, `cold_capture_verify`. The protected
descriptor fixes all step IDs, original operation IDs and lease keys. The
process enrollment map accepts concrete owners; queued module names, factories,
success booleans, pre-created image UUIDs and name searches are not authority.

During export, the writer issues the pinned vSphere 8.0.3.0 `ExportSnapshot`
request once. Its real HttpNfcLease handle is retained in the original journal,
including an authentic late response. Every HTTPS NFC download stays within the
approved origins and TLS trust; no vCenter session, Vault secret or bearer is
forwarded to the NFC host. Downloaded extents must match a complete native SHA-256
manifest. The independent reader retains ready-state manifest and lineage
before `HttpNfcLeaseComplete`, which invalidates the export lease. The completed
source/lease and that retained ready observation are independently inspected.

Each disk then passes the mandatory isolated image owner: checked standalone
VMDK custody, sandboxed `qemu-img info`, sandboxed conversion, and output
inspection under the pinned toolchain and commissioned Linux memory/CPU/I/O,
rate and additive storage limits. Virtual size must equal native snapshot disk
capacity. Originals and converted outputs remain sealed under private custody.

For each disk, the original CREATE intent retains the genuine Glance UUID and
request ID only after the actual POST. An independent GET must prove the exact
empty private protected image before a separate UPLOAD intent may be admitted.
The binary PUT is bound to that UUID and the exact sealed converted bytes. A
second independent GET must prove active state, project, original metadata,
byte/virtual sizes and SHA-256 or SHA-512 native multihash. The final activity
rechecks all original source and image intents, receipts and actual native
readback. Image UUIDs remain image observations, never invented VM bindings.

All effect activities have one attempt. On grant/key/certificate revocation,
scope/epoch change, partial transfer, lost native response, engine failure,
expired owner or missing independent observation, keep the original intent and
charged resources held. Do not repeat export/POST/PUT, replace a native UUID,
extend the original image lease, or clear uncertainty with an operator flag.
Use independently fenced original recovery; a new cleanup, deployment or boot
action needs its own concrete selected owner and current approval. Controlled
image cleanup and native guest boot/remediation remain prerequisites for a full
cold migration, including Windows virtio/storage/network/firmware work.

Local SQL/HTTPS/workflow fixtures verify contracts and confer no native site
qualification. Record separate native evidence for this lower purpose and each
later boot/guest/direction/method campaign.

Primary contracts: [ExportSnapshot](https://developer.broadcom.com/xapis/virtual-infrastructure-json-api/latest/sdk/vim25/release/VirtualMachineSnapshot/moId/ExportSnapshot/post/),
[HttpNfcLeaseDeviceUrl](https://developer.broadcom.com/xapis/virtual-infrastructure-json-api/latest/data-structures/HttpNfcLeaseDeviceUrl/),
[HttpNfcLeaseManifestEntry](https://developer.broadcom.com/xapis/virtual-infrastructure-json-api/latest/data-structures/HttpNfcLeaseManifestEntry/),
and [Glance image v2](https://docs.openstack.org/api-ref/image/v2/index.html).
