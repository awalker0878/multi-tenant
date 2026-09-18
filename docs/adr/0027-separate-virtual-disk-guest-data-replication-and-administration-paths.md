# ADR-0027 — Separate virtual-disk, guest-data, replication and administration paths

**Status:** Proposed<br>
**Accountable role:** Architecture authority and responsible infrastructure service owner<br>
**Scope:** Portable hosting reference pattern; site/service adoption remains unrecorded<br>
**Original decision identifiers:** Chapter-derived; no standalone source ID asserted.<br>
**Source chapters:** [RA §12](../architecture/reference/12-storage-backup-and-data-isolation-architecture.md) · [SVC §4](../architecture/shared-services/4-storage-copies-and-retained-data-ownership.md) · [WD §7](../solutions/internal-protected-workload/7-service-permissions-and-non-ip-storage-paths.md)

Source-derived synthesis; not a new source standard or a reconstructed approval meeting. The linked record is not made authoritative by rendering it. Real adoption needs the stated scope, actual authority and independently protected decision evidence.

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

Related implementation areas are traceability targets, not proof of complete implementation:

- [terraform/modules/nutanix-workload](../../terraform/modules/nutanix-workload)
- [terraform/modules/vsphere-workload](../../terraform/modules/vsphere-workload)
- [terraform/modules/openstack-workload](../../terraform/modules/openstack-workload)

Review [the assertion allocation](../implementation/assertion-allocation.md) for enforcement owner, location, evidence class and unimplemented dependencies.

## Open decisions and acceptance

Actual backend isolation, object/file semantics, copy policy and media sanitization remain independent engineering and qualification responsibilities.

**Deciding authority:** Not recorded<br>
**Decision date:** Not recorded<br>
**Decision record:** Not supplied<br>
**Evidence references:** Not supplied<br>
**Decision rationale:** No lifecycle decision recorded<br>
**Superseded by:** None

Evidence references require owner verification; this repository does not authenticate a signatory or issue native operating authorization. Source-derived Proposed records remain proposed until their genuine decision is recorded. Accepted and rejected records are retained, not overwritten out of history.

---

[Decision register](README.md) · [Maintained design workspace](../current/README.md)
