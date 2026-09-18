# ADR-0027 — Separate virtual-disk, guest-data, replication and administration paths

**Status:** Proposed<br>
**Accountable role:** Storage operations<br>
**Scope:** Reusable reference decision; actual site adoption remains unissued<br>
**Record date:** 2026-09-17 (not an approval date)<br>
**Original decision identifiers:** Chapter-derived; no invented source decision identifier.<br>
**Source chapters:** [RA §12](../architecture/reference/12-storage-backup-and-data-isolation-architecture.md) · [SVC §4](../architecture/shared-services/4-storage-copies-and-retained-data-ownership.md) · [WD §7](../solutions/internal-protected-workload/7-service-permissions-and-non-ip-storage-paths.md)

Source-derived synthesis; not a new source standard or a reconstructed approval meeting.

## Context

Virtual disk I/O can reach storage through the hypervisor without traversing the guest NIC or guest-network ZIP. Copies and exports can bypass intended data-placement restrictions if treated only as storage capacity.

## Decision

Define controls at each actual data path: authorized hypervisor disk attachment, guest block/file/object access, backend replication/rebuild, management and copy/export. Preserve tenant ownership, classification, location, retention and key scope across copies.

## Alternatives and source limitations

Block, file and object services are separately qualified behaviours, not interchangeable because they store bytes. A shared backend is acceptable only under its declared access and dependency controls.

## Consequences

Separating guest placement does not isolate shared HCI controllers, storage media or management. Snapshot creation is not proof of an independently recoverable backup.

## Engineering and implementation obligations

Record the storage service class, performance/failure envelope, actual client identity, copy lineage, destination checks and sanitization/reuse evidence.

## Requirement and code traceability

[STO-001](../assurance/requirements.md#STO-001) · [STO-002](../assurance/requirements.md#STO-002) · [STO-003](../assurance/requirements.md#STO-003)

These are related implementation areas, not assertion-level evidence of native qualification:

- [terraform/modules/nutanix-workload](../../terraform/modules/nutanix-workload)
- [terraform/modules/vsphere-workload](../../terraform/modules/vsphere-workload)
- [terraform/modules/openstack-workload](../../terraform/modules/openstack-workload)

[Requirement/assertion allocation](../assurance/implementation-allocation.md) records partial, external and unimplemented controls separately.

## Open work

Actual backend isolation, object/file semantics, copy policy and media sanitization remain independent engineering and qualification responsibilities.

## Decision lifecycle and authority

- Deciding authority: Not recorded.
- Decision date: Not recorded.
- Decision evidence: Not supplied; no acceptance claim.
- Disposition rationale: No rejection or supersession recorded.
- Supersedes: None.
- Superseded by: None.

Record authenticity and the deciding authority's jurisdiction require independent review. Passing a record-schema check does not issue or authenticate an approval. The current record status is declared above; publication never grants decision authority.

[Decision register](README.md) · [Maintenance rules](../DOCUMENTATION_MIGRATION.md)
