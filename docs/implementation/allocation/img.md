# IMG — assertion allocation

[Allocation index](../assertion-allocation.md) · [Unchanged requirement catalogue](../../assurance/requirements.md)

These are source-grounded proposed allocations, not native compliance results.

## IMG-001

Only approved versioned images and baselines SHALL be deployed; each SHALL include provenance, digest, support status, hardening and vulnerability disposition with a retirement/rebuild policy.


### IMG-001.A01

**Assertion:** Complete source obligation; all applicable clauses must be satisfied: Only approved versioned images and baselines SHALL be deployed; each SHALL include provenance, digest, support status, hardening and vulnerability disposition with a retirement/rebuild policy.

**Owner / location:** Platform engineering / Eligible host/storage pools, actual scheduler, volume/copy service, backup and protected recovery estate

**Disposition:** EXTERNAL_PLATFORM_STORAGE_PROTECTION_CONTROL_WITH_PARTIAL_WORKLOAD_CODE. **Evidence class:** NATIVE_NOT_RUN; related local fixtures/engine checks are narrower evidence, not satisfaction

**Artifact or required operating record:** Accepted placement/storage/protection profiles and native allocation, retention, copy/key and restore procedures — specifically: Complete source obligation; all applicable clauses must be satisfied: Only approved versioned images and baselines SHALL be deployed; each SHALL include provenance, digest, support status, hardening and vulnerability disposition with a retirement/rebuild policy.

**Available related source:** [terraform/modules/nutanix-workload](../../../terraform/modules/nutanix-workload) · [terraform/modules/vsphere-workload](../../../terraform/modules/vsphere-workload) · [terraform/modules/openstack-workload](../../../terraform/modules/openstack-workload) · [docs/current/TAD-infrastructure.md](../../current/TAD-infrastructure.md)

**Verification:** Check real initial/recovery placement and unauthorized attachment/copy access; measure usable isolated restore with required dependencies. Baseline procedures: CT-036, CT-040, CT-041

**Remaining dependency:** VM/volume creation does not implement approved physical co-residency, backup authority, retained-copy catalogues or recoverable key custody.

**Review state:** PROPOSED_ALLOCATION; actual applicability, named authority and evidence assignment pending

### IMG-001.A02

**Assertion:** Only approved versioned images and baselines SHALL be deployed

**Owner / location:** Platform engineering / Eligible host/storage pools, actual scheduler, volume/copy service, backup and protected recovery estate

**Disposition:** EXTERNAL_PLATFORM_STORAGE_PROTECTION_CONTROL_WITH_PARTIAL_WORKLOAD_CODE. **Evidence class:** NATIVE_NOT_RUN; related local fixtures/engine checks are narrower evidence, not satisfaction

**Artifact or required operating record:** Accepted placement/storage/protection profiles and native allocation, retention, copy/key and restore procedures — specifically: Only approved versioned images and baselines SHALL be deployed

**Available related source:** [terraform/modules/nutanix-workload](../../../terraform/modules/nutanix-workload) · [terraform/modules/vsphere-workload](../../../terraform/modules/vsphere-workload) · [terraform/modules/openstack-workload](../../../terraform/modules/openstack-workload) · [docs/current/TAD-infrastructure.md](../../current/TAD-infrastructure.md)

**Verification:** Check real initial/recovery placement and unauthorized attachment/copy access; measure usable isolated restore with required dependencies. Baseline procedures: CT-036, CT-040, CT-041

**Remaining dependency:** VM/volume creation does not implement approved physical co-residency, backup authority, retained-copy catalogues or recoverable key custody.

**Review state:** PROPOSED_ALLOCATION; actual applicability, named authority and evidence assignment pending

### IMG-001.A03

**Assertion:** each SHALL include provenance, digest, support status, hardening and vulnerability disposition with a retirement/rebuild policy.

**Owner / location:** Platform engineering / Eligible host/storage pools, actual scheduler, volume/copy service, backup and protected recovery estate

**Disposition:** EXTERNAL_PLATFORM_STORAGE_PROTECTION_CONTROL_WITH_PARTIAL_WORKLOAD_CODE. **Evidence class:** NATIVE_NOT_RUN; related local fixtures/engine checks are narrower evidence, not satisfaction

**Artifact or required operating record:** Accepted placement/storage/protection profiles and native allocation, retention, copy/key and restore procedures — specifically: each SHALL include provenance, digest, support status, hardening and vulnerability disposition with a retirement/rebuild policy.

**Available related source:** [terraform/modules/nutanix-workload](../../../terraform/modules/nutanix-workload) · [terraform/modules/vsphere-workload](../../../terraform/modules/vsphere-workload) · [terraform/modules/openstack-workload](../../../terraform/modules/openstack-workload) · [docs/current/TAD-infrastructure.md](../../current/TAD-infrastructure.md)

**Verification:** Check real initial/recovery placement and unauthorized attachment/copy access; measure usable isolated restore with required dependencies. Baseline procedures: CT-036, CT-040, CT-041

**Remaining dependency:** VM/volume creation does not implement approved physical co-residency, backup authority, retained-copy catalogues or recoverable key custody.

**Review state:** PROPOSED_ALLOCATION; actual applicability, named authority and evidence assignment pending

## IMG-002

Runtime configuration SHALL be verified against the required baseline after provisioning and material change; unsupported protection agents or disabled mandatory controls SHALL not be silently accepted.


### IMG-002.A01

**Assertion:** Complete source obligation; all applicable clauses must be satisfied: Runtime configuration SHALL be verified against the required baseline after provisioning and material change; unsupported protection agents or disabled mandatory controls SHALL not be silently accepted.

**Owner / location:** Platform engineering / Eligible host/storage pools, actual scheduler, volume/copy service, backup and protected recovery estate

**Disposition:** EXTERNAL_PLATFORM_STORAGE_PROTECTION_CONTROL_WITH_PARTIAL_WORKLOAD_CODE. **Evidence class:** NATIVE_NOT_RUN; related local fixtures/engine checks are narrower evidence, not satisfaction

**Artifact or required operating record:** Accepted placement/storage/protection profiles and native allocation, retention, copy/key and restore procedures — specifically: Complete source obligation; all applicable clauses must be satisfied: Runtime configuration SHALL be verified against the required baseline after provisioning and material change; unsupported protection agents or disabled mandatory controls SHALL not be silently accepted.

**Available related source:** [terraform/modules/nutanix-workload](../../../terraform/modules/nutanix-workload) · [terraform/modules/vsphere-workload](../../../terraform/modules/vsphere-workload) · [terraform/modules/openstack-workload](../../../terraform/modules/openstack-workload) · [docs/current/TAD-infrastructure.md](../../current/TAD-infrastructure.md)

**Verification:** Check real initial/recovery placement and unauthorized attachment/copy access; measure usable isolated restore with required dependencies. Baseline procedures: CT-014, CT-036, CT-040

**Remaining dependency:** VM/volume creation does not implement approved physical co-residency, backup authority, retained-copy catalogues or recoverable key custody.

**Review state:** PROPOSED_ALLOCATION; actual applicability, named authority and evidence assignment pending

### IMG-002.A02

**Assertion:** Runtime configuration SHALL be verified against the required baseline after provisioning and material change

**Owner / location:** Platform engineering / Eligible host/storage pools, actual scheduler, volume/copy service, backup and protected recovery estate

**Disposition:** EXTERNAL_PLATFORM_STORAGE_PROTECTION_CONTROL_WITH_PARTIAL_WORKLOAD_CODE. **Evidence class:** NATIVE_NOT_RUN; related local fixtures/engine checks are narrower evidence, not satisfaction

**Artifact or required operating record:** Accepted placement/storage/protection profiles and native allocation, retention, copy/key and restore procedures — specifically: Runtime configuration SHALL be verified against the required baseline after provisioning and material change

**Available related source:** [terraform/modules/nutanix-workload](../../../terraform/modules/nutanix-workload) · [terraform/modules/vsphere-workload](../../../terraform/modules/vsphere-workload) · [terraform/modules/openstack-workload](../../../terraform/modules/openstack-workload) · [docs/current/TAD-infrastructure.md](../../current/TAD-infrastructure.md)

**Verification:** Check real initial/recovery placement and unauthorized attachment/copy access; measure usable isolated restore with required dependencies. Baseline procedures: CT-014, CT-036, CT-040

**Remaining dependency:** VM/volume creation does not implement approved physical co-residency, backup authority, retained-copy catalogues or recoverable key custody.

**Review state:** PROPOSED_ALLOCATION; actual applicability, named authority and evidence assignment pending

### IMG-002.A03

**Assertion:** unsupported protection agents or disabled mandatory controls SHALL not be silently accepted.

**Owner / location:** Platform engineering / Eligible host/storage pools, actual scheduler, volume/copy service, backup and protected recovery estate

**Disposition:** EXTERNAL_PLATFORM_STORAGE_PROTECTION_CONTROL_WITH_PARTIAL_WORKLOAD_CODE. **Evidence class:** NATIVE_NOT_RUN; related local fixtures/engine checks are narrower evidence, not satisfaction

**Artifact or required operating record:** Accepted placement/storage/protection profiles and native allocation, retention, copy/key and restore procedures — specifically: unsupported protection agents or disabled mandatory controls SHALL not be silently accepted.

**Available related source:** [terraform/modules/nutanix-workload](../../../terraform/modules/nutanix-workload) · [terraform/modules/vsphere-workload](../../../terraform/modules/vsphere-workload) · [terraform/modules/openstack-workload](../../../terraform/modules/openstack-workload) · [docs/current/TAD-infrastructure.md](../../current/TAD-infrastructure.md)

**Verification:** Check real initial/recovery placement and unauthorized attachment/copy access; measure usable isolated restore with required dependencies. Baseline procedures: CT-014, CT-036, CT-040

**Remaining dependency:** VM/volume creation does not implement approved physical co-residency, backup authority, retained-copy catalogues or recoverable key custody.

**Review state:** PROPOSED_ALLOCATION; actual applicability, named authority and evidence assignment pending
