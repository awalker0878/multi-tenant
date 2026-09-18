# PLACE — assertion allocation

[Allocation index](../assertion-allocation.md) · [Unchanged requirement catalogue](../../assurance/requirements.md)

These are source-grounded proposed allocations, not native compliance results.

## PLACE-001

Placement SHALL satisfy all mandatory security, assurance, location, lifecycle, capacity and recovery constraints using a current qualified platform profile; unresolved or conflicting constraints SHALL reject the request.


### PLACE-001.A01

**Assertion:** Complete source obligation; all applicable clauses must be satisfied: Placement SHALL satisfy all mandatory security, assurance, location, lifecycle, capacity and recovery constraints using a current qualified platform profile; unresolved or conflicting constraints SHALL reject the request.

**Owner / location:** Automation platform / Eligible host/storage pools, actual scheduler, volume/copy service, backup and protected recovery estate

**Disposition:** EXTERNAL_PLATFORM_STORAGE_PROTECTION_CONTROL_WITH_PARTIAL_WORKLOAD_CODE. **Evidence class:** NATIVE_NOT_RUN; related local fixtures/engine checks are narrower evidence, not satisfaction

**Artifact or required operating record:** Accepted placement/storage/protection profiles and native allocation, retention, copy/key and restore procedures — specifically: Complete source obligation; all applicable clauses must be satisfied: Placement SHALL satisfy all mandatory security, assurance, location, lifecycle, capacity and recovery constraints using a current qualified platform profile; unresolved or conflicting constraints SHALL reject the request.

**Available related source:** [terraform/modules/nutanix-workload](../../../terraform/modules/nutanix-workload) · [terraform/modules/vsphere-workload](../../../terraform/modules/vsphere-workload) · [terraform/modules/openstack-workload](../../../terraform/modules/openstack-workload) · [docs/current/TAD-infrastructure.md](../../current/TAD-infrastructure.md)

**Verification:** Check real initial/recovery placement and unauthorized attachment/copy access; measure usable isolated restore with required dependencies. Baseline procedures: CT-018, CT-035, CT-056, CT-061

**Remaining dependency:** VM/volume creation does not implement approved physical co-residency, backup authority, retained-copy catalogues or recoverable key custody.

**Review state:** PROPOSED_ALLOCATION; actual applicability, named authority and evidence assignment pending

### PLACE-001.A02

**Assertion:** Placement SHALL satisfy all mandatory security, assurance, location, lifecycle, capacity and recovery constraints using a current qualified platform profile

**Owner / location:** Automation platform / Eligible host/storage pools, actual scheduler, volume/copy service, backup and protected recovery estate

**Disposition:** EXTERNAL_PLATFORM_STORAGE_PROTECTION_CONTROL_WITH_PARTIAL_WORKLOAD_CODE. **Evidence class:** NATIVE_NOT_RUN; related local fixtures/engine checks are narrower evidence, not satisfaction

**Artifact or required operating record:** Accepted placement/storage/protection profiles and native allocation, retention, copy/key and restore procedures — specifically: Placement SHALL satisfy all mandatory security, assurance, location, lifecycle, capacity and recovery constraints using a current qualified platform profile

**Available related source:** [terraform/modules/nutanix-workload](../../../terraform/modules/nutanix-workload) · [terraform/modules/vsphere-workload](../../../terraform/modules/vsphere-workload) · [terraform/modules/openstack-workload](../../../terraform/modules/openstack-workload) · [docs/current/TAD-infrastructure.md](../../current/TAD-infrastructure.md)

**Verification:** Check real initial/recovery placement and unauthorized attachment/copy access; measure usable isolated restore with required dependencies. Baseline procedures: CT-018, CT-035, CT-056, CT-061

**Remaining dependency:** VM/volume creation does not implement approved physical co-residency, backup authority, retained-copy catalogues or recoverable key custody.

**Review state:** PROPOSED_ALLOCATION; actual applicability, named authority and evidence assignment pending

### PLACE-001.A03

**Assertion:** unresolved or conflicting constraints SHALL reject the request.

**Owner / location:** Automation platform / Eligible host/storage pools, actual scheduler, volume/copy service, backup and protected recovery estate

**Disposition:** EXTERNAL_PLATFORM_STORAGE_PROTECTION_CONTROL_WITH_PARTIAL_WORKLOAD_CODE. **Evidence class:** NATIVE_NOT_RUN; related local fixtures/engine checks are narrower evidence, not satisfaction

**Artifact or required operating record:** Accepted placement/storage/protection profiles and native allocation, retention, copy/key and restore procedures — specifically: unresolved or conflicting constraints SHALL reject the request.

**Available related source:** [terraform/modules/nutanix-workload](../../../terraform/modules/nutanix-workload) · [terraform/modules/vsphere-workload](../../../terraform/modules/vsphere-workload) · [terraform/modules/openstack-workload](../../../terraform/modules/openstack-workload) · [docs/current/TAD-infrastructure.md](../../current/TAD-infrastructure.md)

**Verification:** Check real initial/recovery placement and unauthorized attachment/copy access; measure usable isolated restore with required dependencies. Baseline procedures: CT-018, CT-035, CT-056, CT-061

**Remaining dependency:** VM/volume creation does not implement approved physical co-residency, backup authority, retained-copy catalogues or recoverable key custody.

**Review state:** PROPOSED_ALLOCATION; actual applicability, named authority and evidence assignment pending

## PLACE-002

Data, backup, telemetry, diagnostic, control-plane, administrative-access and key locations/control constraints SHALL be represented separately and enforced through approved profiles and agreements.


### PLACE-002.A01

**Assertion:** Complete source obligation; all applicable clauses must be satisfied: Data, backup, telemetry, diagnostic, control-plane, administrative-access and key locations/control constraints SHALL be represented separately and enforced through approved profiles and agreements.

**Owner / location:** Service owner / Eligible host/storage pools, actual scheduler, volume/copy service, backup and protected recovery estate

**Disposition:** EXTERNAL_PLATFORM_STORAGE_PROTECTION_CONTROL_WITH_PARTIAL_WORKLOAD_CODE. **Evidence class:** NATIVE_NOT_RUN; related local fixtures/engine checks are narrower evidence, not satisfaction

**Artifact or required operating record:** Accepted placement/storage/protection profiles and native allocation, retention, copy/key and restore procedures — specifically: Complete source obligation; all applicable clauses must be satisfied: Data, backup, telemetry, diagnostic, control-plane, administrative-access and key locations/control constraints SHALL be represented separately and enforced through approved profiles and agreements.

**Available related source:** [terraform/modules/nutanix-workload](../../../terraform/modules/nutanix-workload) · [terraform/modules/vsphere-workload](../../../terraform/modules/vsphere-workload) · [terraform/modules/openstack-workload](../../../terraform/modules/openstack-workload) · [docs/current/TAD-infrastructure.md](../../current/TAD-infrastructure.md)

**Verification:** Check real initial/recovery placement and unauthorized attachment/copy access; measure usable isolated restore with required dependencies. Baseline procedures: CT-061, CT-079

**Remaining dependency:** VM/volume creation does not implement approved physical co-residency, backup authority, retained-copy catalogues or recoverable key custody.

**Review state:** PROPOSED_ALLOCATION; actual applicability, named authority and evidence assignment pending

## PLACE-003

Each portable service class SHALL have a documented exit path, declared proprietary dependencies and representative export/recovery evidence; residency or format support alone SHALL NOT be presented as portability or sovereignty proof.


### PLACE-003.A01

**Assertion:** Complete source obligation; all applicable clauses must be satisfied: Each portable service class SHALL have a documented exit path, declared proprietary dependencies and representative export/recovery evidence; residency or format support alone SHALL NOT be presented as portability or sovereignty proof.

**Owner / location:** Architecture authority / Eligible host/storage pools, actual scheduler, volume/copy service, backup and protected recovery estate

**Disposition:** EXTERNAL_PLATFORM_STORAGE_PROTECTION_CONTROL_WITH_PARTIAL_WORKLOAD_CODE. **Evidence class:** NATIVE_NOT_RUN; related local fixtures/engine checks are narrower evidence, not satisfaction

**Artifact or required operating record:** Accepted placement/storage/protection profiles and native allocation, retention, copy/key and restore procedures — specifically: Complete source obligation; all applicable clauses must be satisfied: Each portable service class SHALL have a documented exit path, declared proprietary dependencies and representative export/recovery evidence; residency or format support alone SHALL NOT be presented as portability or sovereignty proof.

**Available related source:** [terraform/modules/nutanix-workload](../../../terraform/modules/nutanix-workload) · [terraform/modules/vsphere-workload](../../../terraform/modules/vsphere-workload) · [terraform/modules/openstack-workload](../../../terraform/modules/openstack-workload) · [docs/current/TAD-infrastructure.md](../../current/TAD-infrastructure.md)

**Verification:** Check real initial/recovery placement and unauthorized attachment/copy access; measure usable isolated restore with required dependencies. Baseline procedures: CT-060, CT-073

**Remaining dependency:** VM/volume creation does not implement approved physical co-residency, backup authority, retained-copy catalogues or recoverable key custody.

**Review state:** PROPOSED_ALLOCATION; actual applicability, named authority and evidence assignment pending

### PLACE-003.A02

**Assertion:** Each portable service class SHALL have a documented exit path, declared proprietary dependencies and representative export/recovery evidence

**Owner / location:** Architecture authority / Eligible host/storage pools, actual scheduler, volume/copy service, backup and protected recovery estate

**Disposition:** EXTERNAL_PLATFORM_STORAGE_PROTECTION_CONTROL_WITH_PARTIAL_WORKLOAD_CODE. **Evidence class:** NATIVE_NOT_RUN; related local fixtures/engine checks are narrower evidence, not satisfaction

**Artifact or required operating record:** Accepted placement/storage/protection profiles and native allocation, retention, copy/key and restore procedures — specifically: Each portable service class SHALL have a documented exit path, declared proprietary dependencies and representative export/recovery evidence

**Available related source:** [terraform/modules/nutanix-workload](../../../terraform/modules/nutanix-workload) · [terraform/modules/vsphere-workload](../../../terraform/modules/vsphere-workload) · [terraform/modules/openstack-workload](../../../terraform/modules/openstack-workload) · [docs/current/TAD-infrastructure.md](../../current/TAD-infrastructure.md)

**Verification:** Check real initial/recovery placement and unauthorized attachment/copy access; measure usable isolated restore with required dependencies. Baseline procedures: CT-060, CT-073

**Remaining dependency:** VM/volume creation does not implement approved physical co-residency, backup authority, retained-copy catalogues or recoverable key custody.

**Review state:** PROPOSED_ALLOCATION; actual applicability, named authority and evidence assignment pending

### PLACE-003.A03

**Assertion:** residency or format support alone SHALL NOT be presented as portability or sovereignty proof.

**Owner / location:** Architecture authority / Eligible host/storage pools, actual scheduler, volume/copy service, backup and protected recovery estate

**Disposition:** EXTERNAL_PLATFORM_STORAGE_PROTECTION_CONTROL_WITH_PARTIAL_WORKLOAD_CODE. **Evidence class:** NATIVE_NOT_RUN; related local fixtures/engine checks are narrower evidence, not satisfaction

**Artifact or required operating record:** Accepted placement/storage/protection profiles and native allocation, retention, copy/key and restore procedures — specifically: residency or format support alone SHALL NOT be presented as portability or sovereignty proof.

**Available related source:** [terraform/modules/nutanix-workload](../../../terraform/modules/nutanix-workload) · [terraform/modules/vsphere-workload](../../../terraform/modules/vsphere-workload) · [terraform/modules/openstack-workload](../../../terraform/modules/openstack-workload) · [docs/current/TAD-infrastructure.md](../../current/TAD-infrastructure.md)

**Verification:** Check real initial/recovery placement and unauthorized attachment/copy access; measure usable isolated restore with required dependencies. Baseline procedures: CT-060, CT-073

**Remaining dependency:** VM/volume creation does not implement approved physical co-residency, backup authority, retained-copy catalogues or recoverable key custody.

**Review state:** PROPOSED_ALLOCATION; actual applicability, named authority and evidence assignment pending
