# Any-to-any migration commissioning and qualification

Use this runbook with the [P09-A direction matrix](../../implementation/p09-any-to-any.md)
and [native migration custody/recovery instructions](native-migration.md).
It describes the implemented software and the inputs needed for an actual campaign;
it is not permission to operate an unselected environment.

## Select and discover both roles

1. Enroll separate source and destination installations with their actual API,
   platform, network and storage versions. Same-platform migration requires distinct
   installation identities. Authorize scoped read-only discovery for both roles.
2. Collect the exact source VM inventory, every disk and NIC, firmware, guest facts,
   native configuration digests and observed destination resources. API guest/OS
   metadata is not verified guest state: AHV may have no guest ID and OpenStack
   declarations require offline inspection and independent boot checks. Source-only
   endpoint discovery does not require a destination capability profile.
3. Select the migration method and map all disks into application datasets.
   Configure observed destination placement, disk/controller order, quarantine and
   production networks, guest/hardware profile and security policy references.
   Unknown or unsupported native facts remain blockers and cannot be overridden.
4. Supply the owner-only consistency, service, traffic, data-validation and recovery
   requirements. Confirm the exact current review. A changed discovery, owner input
   or capability profile invalidates confirmation and the old plan.

## Commission accounts and stage mechanisms

Apply worker-owned native migrations through `005_any_to_any.sql` as the schema
owner before starting the new worker. This extends the append-only event ledger
for source images, guest preparation, import leases and durable continuation.
The runtime role must not own or alter its tables. Apply Lifecycle-owned migrations
separately; never share its database credentials with the worker.

Account commissioning schema v3 assigns platform independently to each source and
destination role. Enroll collector, writer and observer identities independently
on each platform; verify actual native principal and installation and preserve
origin/address/trust pins. For OpenStack schema v3, all connections including image
service share one token within a role; different roles use distinct principals and
tokens. Separate image writer and observer roles where the mechanism requires them.
Never put credentials or arbitrary native URLs into browser input.

Register each stage in the protected migration registry with its complete binding,
exact plan hash, adapter, configuration, independent observer and expiry. Registry
or credential drift stops subsequent effects. The dispatcher resolves the selected
mechanism; it cannot silently substitute a different migration method.

For cold copies, the source adapter captures only the selected stopped workload.
VMware uses snapshot/isolated clone plus OVF/NFC. OpenStack uses Nova root-image and
Cinder snapshot/isolated-volume/image operations. AHV uses Prism VM-disk images
with source VM/disk readback. Preserve task IDs before polling and retain unknown
outcomes for observation; never repeat a potentially accepted write.

Conversion uses the recorded all-disk archive and an approved, hashed QEMU sandbox.
Guest preparation additionally needs a sealed libguestfs appliance, exact guest
profile and staged licensed driver/package artifacts. Guest preparation is limited
to exact x86_64 Linux/Windows family, distribution and major-version selections.
Windows target tools may be staged offline and installed at first boot in quarantine.
The supplied VirtIO template prepares drivers; it is not a complete arbitrary
foreign-hypervisor Windows conversion. A route must select a guest-specific
transformation artifact and qualify its boot, storage, identity and recovery;
see [libguestfs preparation limits](https://libguestfs.org/virt-customize.1.html).
It operates on private
copies with no host guest shell or network downloads. Preserve approved firmware,
identity and device choices. Linux initramfs or Windows driver injection is not
proof of successful boot; independently observe the resulting guest.

VMware destination import binds folder, resource pool, host, datastore, guest and
hardware version, every disk and NIC. OpenStack binds its project/image/volume and
network mappings. AHV binds cluster/storage container, image, device and quarantine
subnet mappings. All require independent readback before subsequent stages.

Application rebuild/restore, application delta, file delta and external block
replication use the [typed method v2 contract](../../../contracts/openapi/worker-migration-method-v2.json).
The commissioned data-owner implementation and version, artifact identity and
independent E3 qualification remain explicit; this does not implement every
database, backup or storage product. Per-dataset readback and aggregate data-loss
limits must pass before accepting the method effect. They do not inherit cold-copy qualification. Retain exact dataset
and consistency bindings, operation receipts, fencing and recovery artifacts.

## Bind and observe acceptance

Start the separate `lifecycle-worker-observer --config <protected-file>` process
with its own enrolled caller registry, TLS identity and read-only service credentials.
It is a declared image entrypoint; the default diagnostic entrypoint does not
activate it.

Commission independent evidence manifests for each exact plan, stage, caller and
phase. Each check names a native subject, read-only service identity and expected
native predicates. Required outcomes include boot, drivers, storage, network,
identity, each dataset, security semantics and individual IPAM, DNS, identity, time,
trust, logging, monitoring and backup acceptance. Include both permitted and denied
security-path results. Verify principal separation against the provider, not merely
different secret filenames. Expired or altered manifests and partial results hold.

Prepare through Planning with the confirmed owner-input digest, exact route,
artifacts and outcome hashes. A route qualifies only its own source/destination,
installed versions, guest, method, topology and recovery. Ordinary admission
requires current native evidence and separate Governance approval. Lab campaigns
must follow the existing isolated qualification policy and limits.

## Observe, interrupt and recover

Use the native job page for persisted stage preparation/start/observation times,
verified stage counts, independently journaled completed-disk bytes and the exact
hold reason. Byte counters exclude unverified partial disks and carry their source
and observation time. No elapsed-time estimate implies data readiness. Refresh current state before issuing a control.

After interrupted image transfer, preserve the private partial files and custody
journal. Continuation requires the recorded immutable image, exact byte count and
prefix digest, unchanged source identity, renewed current authority and the same
operation lineage. A continuation candidate shown by the Console is not permission
to retry an unknown write. Failed prefix, identity, custody or authority checks hold.

A first possible destination business write moves recovery to the post-write side
even when its response is lost. Before that boundary, source return still requires
target fencing and evidence of no divergence. Afterwards, preserve target changes,
reconcile the dataset and use the selected forward or qualified reverse procedure.
Recovery approvals bind the predecessor, increased custody generation and all
original guest/security/service/data outcomes. Separately authorize cleanup.

## Reproduce and retain qualification

Run from a clean source checkout using the locked component dependencies:

```sh
P07_POSTGRES_BIN=/usr/lib/postgresql/16/bin python scripts/p08/qualify.py --output /tmp/p09-a-components
P05_POSTGRES_BIN=/usr/lib/postgresql/16/bin python scripts/p09/qualify.py --output /tmp/p09-a-conformance
python scripts/p08/qualify_browser.py --output /tmp/p09-a-browser
```

Use an unprivileged PostgreSQL process account and the pinned Console browser.
The component campaign refuses skipped database tests. The directional campaign
checks contract/domain agreement and common Planning-to-Lifecycle composition.
The browser campaign checks actual compiled Vue pages against isolated HTTP peers.
CI also validates independent packages, architecture boundaries and documentation.
These provide software evidence; synthetic peers do not qualify a native tuple.

For native exit, commission actual source/destination and owner services, qualify
the sealed converter/guest artifacts, execute a secured enterprise-integrated
workload in every selected direction, and retain original failures and source,
image and artifact identities. Exercise unsupported inputs, failed prerequisites,
partial service outcomes, lost responses, interruption, continuation, cutover and
both recovery boundaries. Submit exact results to the independent receiving owners
under P09/P10/P11; do not mark their acceptance on their behalf.
