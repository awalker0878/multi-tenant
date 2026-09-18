# STO — assertion allocation

[Allocation index](../assertion-allocation.md) · [Unchanged requirement catalogue](../../assurance/requirements.md)

These are source-grounded proposed allocations, not native compliance results.

## STO-001

Every storage resource and derivative copy SHALL carry owner, categorization, access scope, key policy, placement/retention constraints and lineage; cross-scope attachment or export SHALL require explicit authorization.


### STO-001.A01

**Assertion:** Complete source obligation; all applicable clauses must be satisfied: Every storage resource and derivative copy SHALL carry owner, categorization, access scope, key policy, placement/retention constraints and lineage; cross-scope attachment or export SHALL require explicit authorization.

**Owner / location:** Storage operations / Eligible host/storage pools, actual scheduler, volume/copy service, backup and protected recovery estate

**Disposition:** EXTERNAL_PLATFORM_STORAGE_PROTECTION_CONTROL_WITH_PARTIAL_WORKLOAD_CODE. **Evidence class:** NATIVE_NOT_RUN; related local fixtures/engine checks are narrower evidence, not satisfaction

**Artifact or required operating record:** Accepted placement/storage/protection profiles and native allocation, retention, copy/key and restore procedures — specifically: Complete source obligation; all applicable clauses must be satisfied: Every storage resource and derivative copy SHALL carry owner, categorization, access scope, key policy, placement/retention constraints and lineage; cross-scope attachment or export SHALL require explicit authorization.

**Available related source:** [terraform/modules/nutanix-workload](../../../terraform/modules/nutanix-workload) · [terraform/modules/vsphere-workload](../../../terraform/modules/vsphere-workload) · [terraform/modules/openstack-workload](../../../terraform/modules/openstack-workload) · [docs/current/TAD-infrastructure.md](../../current/TAD-infrastructure.md)

**Verification:** Check real initial/recovery placement and unauthorized attachment/copy access; measure usable isolated restore with required dependencies. Baseline procedures: CT-037, CT-053, CT-078

**Remaining dependency:** VM/volume creation does not implement approved physical co-residency, backup authority, retained-copy catalogues or recoverable key custody.

**Review state:** PROPOSED_ALLOCATION; actual applicability, named authority and evidence assignment pending

### STO-001.A02

**Assertion:** Every storage resource and derivative copy SHALL carry owner, categorization, access scope, key policy, placement/retention constraints and lineage

**Owner / location:** Storage operations / Eligible host/storage pools, actual scheduler, volume/copy service, backup and protected recovery estate

**Disposition:** EXTERNAL_PLATFORM_STORAGE_PROTECTION_CONTROL_WITH_PARTIAL_WORKLOAD_CODE. **Evidence class:** NATIVE_NOT_RUN; related local fixtures/engine checks are narrower evidence, not satisfaction

**Artifact or required operating record:** Accepted placement/storage/protection profiles and native allocation, retention, copy/key and restore procedures — specifically: Every storage resource and derivative copy SHALL carry owner, categorization, access scope, key policy, placement/retention constraints and lineage

**Available related source:** [terraform/modules/nutanix-workload](../../../terraform/modules/nutanix-workload) · [terraform/modules/vsphere-workload](../../../terraform/modules/vsphere-workload) · [terraform/modules/openstack-workload](../../../terraform/modules/openstack-workload) · [docs/current/TAD-infrastructure.md](../../current/TAD-infrastructure.md)

**Verification:** Check real initial/recovery placement and unauthorized attachment/copy access; measure usable isolated restore with required dependencies. Baseline procedures: CT-037, CT-053, CT-078

**Remaining dependency:** VM/volume creation does not implement approved physical co-residency, backup authority, retained-copy catalogues or recoverable key custody.

**Review state:** PROPOSED_ALLOCATION; actual applicability, named authority and evidence assignment pending

### STO-001.A03

**Assertion:** cross-scope attachment or export SHALL require explicit authorization.

**Owner / location:** Storage operations / Eligible host/storage pools, actual scheduler, volume/copy service, backup and protected recovery estate

**Disposition:** EXTERNAL_PLATFORM_STORAGE_PROTECTION_CONTROL_WITH_PARTIAL_WORKLOAD_CODE. **Evidence class:** NATIVE_NOT_RUN; related local fixtures/engine checks are narrower evidence, not satisfaction

**Artifact or required operating record:** Accepted placement/storage/protection profiles and native allocation, retention, copy/key and restore procedures — specifically: cross-scope attachment or export SHALL require explicit authorization.

**Available related source:** [terraform/modules/nutanix-workload](../../../terraform/modules/nutanix-workload) · [terraform/modules/vsphere-workload](../../../terraform/modules/vsphere-workload) · [terraform/modules/openstack-workload](../../../terraform/modules/openstack-workload) · [docs/current/TAD-infrastructure.md](../../current/TAD-infrastructure.md)

**Verification:** Check real initial/recovery placement and unauthorized attachment/copy access; measure usable isolated restore with required dependencies. Baseline procedures: CT-037, CT-053, CT-078

**Remaining dependency:** VM/volume creation does not implement approved physical co-residency, backup authority, retained-copy catalogues or recoverable key custody.

**Review state:** PROPOSED_ALLOCATION; actual applicability, named authority and evidence assignment pending

## STO-002

Storage service profiles SHALL define measurable capacity/performance, consistency, replication, snapshot/clone and portability semantics and SHALL be tested under contention and the accepted failure condition.


### STO-002.A01

**Assertion:** Complete source obligation; all applicable clauses must be satisfied: Storage service profiles SHALL define measurable capacity/performance, consistency, replication, snapshot/clone and portability semantics and SHALL be tested under contention and the accepted failure condition.

**Owner / location:** Storage operations / Eligible host/storage pools, actual scheduler, volume/copy service, backup and protected recovery estate

**Disposition:** EXTERNAL_PLATFORM_STORAGE_PROTECTION_CONTROL_WITH_PARTIAL_WORKLOAD_CODE. **Evidence class:** NATIVE_NOT_RUN; related local fixtures/engine checks are narrower evidence, not satisfaction

**Artifact or required operating record:** Accepted placement/storage/protection profiles and native allocation, retention, copy/key and restore procedures — specifically: Complete source obligation; all applicable clauses must be satisfied: Storage service profiles SHALL define measurable capacity/performance, consistency, replication, snapshot/clone and portability semantics and SHALL be tested under contention and the accepted failure condition.

**Available related source:** [terraform/modules/nutanix-workload](../../../terraform/modules/nutanix-workload) · [terraform/modules/vsphere-workload](../../../terraform/modules/vsphere-workload) · [terraform/modules/openstack-workload](../../../terraform/modules/openstack-workload) · [docs/current/TAD-infrastructure.md](../../current/TAD-infrastructure.md)

**Verification:** Check real initial/recovery placement and unauthorized attachment/copy access; measure usable isolated restore with required dependencies. Baseline procedures: CT-039, CT-052, CT-060

**Remaining dependency:** VM/volume creation does not implement approved physical co-residency, backup authority, retained-copy catalogues or recoverable key custody.

**Review state:** PROPOSED_ALLOCATION; actual applicability, named authority and evidence assignment pending

## STO-003

Storage release and reuse SHALL reconcile all known copies and legal/administrative holds, apply an approved sanitization method and retain a receipt describing scope, method, verification and exceptions.


### STO-003.A01

**Assertion:** Complete source obligation; all applicable clauses must be satisfied: Storage release and reuse SHALL reconcile all known copies and legal/administrative holds, apply an approved sanitization method and retain a receipt describing scope, method, verification and exceptions.

**Owner / location:** Storage operations / Eligible host/storage pools, actual scheduler, volume/copy service, backup and protected recovery estate

**Disposition:** EXTERNAL_PLATFORM_STORAGE_PROTECTION_CONTROL_WITH_PARTIAL_WORKLOAD_CODE. **Evidence class:** NATIVE_NOT_RUN; related local fixtures/engine checks are narrower evidence, not satisfaction

**Artifact or required operating record:** Accepted placement/storage/protection profiles and native allocation, retention, copy/key and restore procedures — specifically: Complete source obligation; all applicable clauses must be satisfied: Storage release and reuse SHALL reconcile all known copies and legal/administrative holds, apply an approved sanitization method and retain a receipt describing scope, method, verification and exceptions.

**Available related source:** [terraform/modules/nutanix-workload](../../../terraform/modules/nutanix-workload) · [terraform/modules/vsphere-workload](../../../terraform/modules/vsphere-workload) · [terraform/modules/openstack-workload](../../../terraform/modules/openstack-workload) · [docs/current/TAD-infrastructure.md](../../current/TAD-infrastructure.md)

**Verification:** Check real initial/recovery placement and unauthorized attachment/copy access; measure usable isolated restore with required dependencies. Baseline procedures: CT-053, CT-059, CT-078

**Remaining dependency:** VM/volume creation does not implement approved physical co-residency, backup authority, retained-copy catalogues or recoverable key custody.

**Review state:** PROPOSED_ALLOCATION; actual applicability, named authority and evidence assignment pending
