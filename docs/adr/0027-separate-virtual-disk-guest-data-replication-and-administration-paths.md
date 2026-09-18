# ADR-0027 — Separate virtual-disk, guest-data, replication and administration paths

**Status:** Proposed — source-derived; organizational acceptance not recorded<br>
**Original decision identifiers:** No standalone source ID; extracted from the explicitly linked chapter decisions.<br>
**Source chapters:** [RA §12](../architecture/reference/12-storage-backup-and-data-isolation-architecture.md) · [SVC §4](../architecture/shared-services/4-storage-copies-and-retained-data-ownership.md) · [WD §7](../solutions/internal-protected-workload/7-service-permissions-and-non-ip-storage-paths.md)

Source-derived synthesis; not a new source standard or a reconstructed approval meeting. The original source remains linked below; this ADR does not record an approval meeting or invent an acceptance date.

## Context

Virtual disk I/O can reach storage through the hypervisor without traversing the guest NIC or guest-network ZIP. Copies and exports can bypass intended data-placement restrictions if treated only as storage capacity.

## Decision recorded in the source

Define controls at each actual data path: authorized hypervisor disk attachment, guest block/file/object access, backend replication/rebuild, management and copy/export. Preserve tenant ownership, classification, location, retention and key scope across copies.

## Alternatives and limits recorded in the source

Block, file and object services are separately qualified behaviours, not interchangeable because they store bytes. A shared backend is acceptable only under its declared access and dependency controls.

## Consequences

Separating guest placement does not isolate shared HCI controllers, storage media or management. Snapshot creation is not proof of an independently recoverable backup.

## Engineering and implementation obligations

Record the storage service class, performance/failure envelope, actual client identity, copy lineage, destination checks and sanitization/reuse evidence.

## Requirement and code traceability

[STO-001](../assurance/requirements.md#STO-001) · [STO-002](../assurance/requirements.md#STO-002) · [STO-003](../assurance/requirements.md#STO-003)

The following implementation areas are traceability targets, not proof that this decision has been qualified:

- [terraform/modules/nutanix-workload](../../terraform/modules/nutanix-workload)
- [terraform/modules/vsphere-workload](../../terraform/modules/vsphere-workload)
- [terraform/modules/openstack-workload](../../terraform/modules/openstack-workload)

Review [the implementation coverage map](../implementation/code-map.md) and the target-specific evidence before asserting completion. A local fixture or static source check does not establish deployed behaviour.

## Open decisions and acceptance

Actual backend isolation, object/file semantics, copy policy and media sanitization remain independent engineering and qualification responsibilities.

Accepting authority: **not recorded**.<br>
Acceptance evidence: **not supplied by this conversion**.<br>
Supersession: no new source supersession is asserted. Record a future change explicitly rather than silently editing an accepted decision.

---

[Decision register](README.md) · [Source and maintenance rules](../DOCUMENTATION_MIGRATION.md)
