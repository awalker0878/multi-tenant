# CMP — assertion allocation

[Allocation index](../assertion-allocation.md) · [Unchanged requirement catalogue](../../assurance/requirements.md)

These are source-grounded proposed allocations, not native compliance results.

## CMP-001

Compute placement, maintenance evacuation, migration and HA restart SHALL enforce the approved tenant/domain/zone co-residency matrix; no scheduler action SHALL silently weaken it.


### CMP-001.A01

**Assertion:** Complete source obligation; all applicable clauses must be satisfied: Compute placement, maintenance evacuation, migration and HA restart SHALL enforce the approved tenant/domain/zone co-residency matrix; no scheduler action SHALL silently weaken it.

**Owner / location:** Platform engineering / Eligible host/storage pools, actual scheduler, volume/copy service, backup and protected recovery estate

**Disposition:** EXTERNAL_PLATFORM_STORAGE_PROTECTION_CONTROL_WITH_PARTIAL_WORKLOAD_CODE. **Evidence class:** NATIVE_NOT_RUN; related local fixtures/engine checks are narrower evidence, not satisfaction

**Artifact or required operating record:** Accepted placement/storage/protection profiles and native allocation, retention, copy/key and restore procedures — specifically: Complete source obligation; all applicable clauses must be satisfied: Compute placement, maintenance evacuation, migration and HA restart SHALL enforce the approved tenant/domain/zone co-residency matrix; no scheduler action SHALL silently weaken it.

**Available related source:** [terraform/modules/nutanix-workload](../../../terraform/modules/nutanix-workload) · [terraform/modules/vsphere-workload](../../../terraform/modules/vsphere-workload) · [terraform/modules/openstack-workload](../../../terraform/modules/openstack-workload) · [docs/current/TAD-infrastructure.md](../../current/TAD-infrastructure.md)

**Verification:** Check real initial/recovery placement and unauthorized attachment/copy access; measure usable isolated restore with required dependencies. Baseline procedures: CT-035, CT-056

**Remaining dependency:** VM/volume creation does not implement approved physical co-residency, backup authority, retained-copy catalogues or recoverable key custody.

**Review state:** PROPOSED_ALLOCATION; actual applicability, named authority and evidence assignment pending

### CMP-001.A02

**Assertion:** Compute placement, maintenance evacuation, migration and HA restart SHALL enforce the approved tenant/domain/zone co-residency matrix

**Owner / location:** Platform engineering / Eligible host/storage pools, actual scheduler, volume/copy service, backup and protected recovery estate

**Disposition:** EXTERNAL_PLATFORM_STORAGE_PROTECTION_CONTROL_WITH_PARTIAL_WORKLOAD_CODE. **Evidence class:** NATIVE_NOT_RUN; related local fixtures/engine checks are narrower evidence, not satisfaction

**Artifact or required operating record:** Accepted placement/storage/protection profiles and native allocation, retention, copy/key and restore procedures — specifically: Compute placement, maintenance evacuation, migration and HA restart SHALL enforce the approved tenant/domain/zone co-residency matrix

**Available related source:** [terraform/modules/nutanix-workload](../../../terraform/modules/nutanix-workload) · [terraform/modules/vsphere-workload](../../../terraform/modules/vsphere-workload) · [terraform/modules/openstack-workload](../../../terraform/modules/openstack-workload) · [docs/current/TAD-infrastructure.md](../../current/TAD-infrastructure.md)

**Verification:** Check real initial/recovery placement and unauthorized attachment/copy access; measure usable isolated restore with required dependencies. Baseline procedures: CT-035, CT-056

**Remaining dependency:** VM/volume creation does not implement approved physical co-residency, backup authority, retained-copy catalogues or recoverable key custody.

**Review state:** PROPOSED_ALLOCATION; actual applicability, named authority and evidence assignment pending

### CMP-001.A03

**Assertion:** no scheduler action SHALL silently weaken it.

**Owner / location:** Platform engineering / Eligible host/storage pools, actual scheduler, volume/copy service, backup and protected recovery estate

**Disposition:** EXTERNAL_PLATFORM_STORAGE_PROTECTION_CONTROL_WITH_PARTIAL_WORKLOAD_CODE. **Evidence class:** NATIVE_NOT_RUN; related local fixtures/engine checks are narrower evidence, not satisfaction

**Artifact or required operating record:** Accepted placement/storage/protection profiles and native allocation, retention, copy/key and restore procedures — specifically: no scheduler action SHALL silently weaken it.

**Available related source:** [terraform/modules/nutanix-workload](../../../terraform/modules/nutanix-workload) · [terraform/modules/vsphere-workload](../../../terraform/modules/vsphere-workload) · [terraform/modules/openstack-workload](../../../terraform/modules/openstack-workload) · [docs/current/TAD-infrastructure.md](../../current/TAD-infrastructure.md)

**Verification:** Check real initial/recovery placement and unauthorized attachment/copy access; measure usable isolated restore with required dependencies. Baseline procedures: CT-035, CT-056

**Remaining dependency:** VM/volume creation does not implement approved physical co-residency, backup authority, retained-copy catalogues or recoverable key custody.

**Review state:** PROPOSED_ALLOCATION; actual applicability, named authority and evidence assignment pending

## CMP-002

Each compute profile SHALL define supported hardware/software, boot/attestation controls, administrative isolation, resource guarantees, overcommit policy and handling of unsupported devices.


### CMP-002.A01

**Assertion:** Complete source obligation; all applicable clauses must be satisfied: Each compute profile SHALL define supported hardware/software, boot/attestation controls, administrative isolation, resource guarantees, overcommit policy and handling of unsupported devices.

**Owner / location:** Platform engineering / Eligible host/storage pools, actual scheduler, volume/copy service, backup and protected recovery estate

**Disposition:** EXTERNAL_PLATFORM_STORAGE_PROTECTION_CONTROL_WITH_PARTIAL_WORKLOAD_CODE. **Evidence class:** NATIVE_NOT_RUN; related local fixtures/engine checks are narrower evidence, not satisfaction

**Artifact or required operating record:** Accepted placement/storage/protection profiles and native allocation, retention, copy/key and restore procedures — specifically: Complete source obligation; all applicable clauses must be satisfied: Each compute profile SHALL define supported hardware/software, boot/attestation controls, administrative isolation, resource guarantees, overcommit policy and handling of unsupported devices.

**Available related source:** [terraform/modules/nutanix-workload](../../../terraform/modules/nutanix-workload) · [terraform/modules/vsphere-workload](../../../terraform/modules/vsphere-workload) · [terraform/modules/openstack-workload](../../../terraform/modules/openstack-workload) · [docs/current/TAD-infrastructure.md](../../current/TAD-infrastructure.md)

**Verification:** Check real initial/recovery placement and unauthorized attachment/copy access; measure usable isolated restore with required dependencies. Baseline procedures: CT-036, CT-039, CT-073

**Remaining dependency:** VM/volume creation does not implement approved physical co-residency, backup authority, retained-copy catalogues or recoverable key custody.

**Review state:** PROPOSED_ALLOCATION; actual applicability, named authority and evidence assignment pending

## CMP-003

The meaning of dedicated compute SHALL state its exact physical and administrative scope and disclose any shared storage, network, control, support or recovery dependency.


### CMP-003.A01

**Assertion:** Complete source obligation; all applicable clauses must be satisfied: The meaning of dedicated compute SHALL state its exact physical and administrative scope and disclose any shared storage, network, control, support or recovery dependency.

**Owner / location:** Architecture authority / Eligible host/storage pools, actual scheduler, volume/copy service, backup and protected recovery estate

**Disposition:** EXTERNAL_PLATFORM_STORAGE_PROTECTION_CONTROL_WITH_PARTIAL_WORKLOAD_CODE. **Evidence class:** NATIVE_NOT_RUN; related local fixtures/engine checks are narrower evidence, not satisfaction

**Artifact or required operating record:** Accepted placement/storage/protection profiles and native allocation, retention, copy/key and restore procedures — specifically: Complete source obligation; all applicable clauses must be satisfied: The meaning of dedicated compute SHALL state its exact physical and administrative scope and disclose any shared storage, network, control, support or recovery dependency.

**Available related source:** [terraform/modules/nutanix-workload](../../../terraform/modules/nutanix-workload) · [terraform/modules/vsphere-workload](../../../terraform/modules/vsphere-workload) · [terraform/modules/openstack-workload](../../../terraform/modules/openstack-workload) · [docs/current/TAD-infrastructure.md](../../current/TAD-infrastructure.md)

**Verification:** Check real initial/recovery placement and unauthorized attachment/copy access; measure usable isolated restore with required dependencies. Baseline procedures: CT-035, CT-062

**Remaining dependency:** VM/volume creation does not implement approved physical co-residency, backup authority, retained-copy catalogues or recoverable key custody.

**Review state:** PROPOSED_ALLOCATION; actual applicability, named authority and evidence assignment pending
