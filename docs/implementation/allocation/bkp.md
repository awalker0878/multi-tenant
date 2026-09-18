# BKP — assertion allocation

[Allocation index](../assertion-allocation.md) · [Unchanged requirement catalogue](../../assurance/requirements.md)

These are source-grounded proposed allocations, not native compliance results.

## BKP-001

Backup consumers SHALL NOT receive connectivity to backup management interfaces merely because they consume backup service.


### BKP-001.A01

**Assertion:** Complete source obligation; all applicable clauses must be satisfied: Backup consumers SHALL NOT receive connectivity to backup management interfaces merely because they consume backup service.

**Owner / location:** Backup operations / Eligible host/storage pools, actual scheduler, volume/copy service, backup and protected recovery estate

**Disposition:** EXTERNAL_PLATFORM_STORAGE_PROTECTION_CONTROL_WITH_PARTIAL_WORKLOAD_CODE. **Evidence class:** NATIVE_NOT_RUN; related local fixtures/engine checks are narrower evidence, not satisfaction

**Artifact or required operating record:** Accepted placement/storage/protection profiles and native allocation, retention, copy/key and restore procedures — specifically: Complete source obligation; all applicable clauses must be satisfied: Backup consumers SHALL NOT receive connectivity to backup management interfaces merely because they consume backup service.

**Available related source:** [terraform/modules/nutanix-workload](../../../terraform/modules/nutanix-workload) · [terraform/modules/vsphere-workload](../../../terraform/modules/vsphere-workload) · [terraform/modules/openstack-workload](../../../terraform/modules/openstack-workload) · [docs/current/TAD-infrastructure.md](../../current/TAD-infrastructure.md)

**Verification:** Check real initial/recovery placement and unauthorized attachment/copy access; measure usable isolated restore with required dependencies. Baseline procedures: CT-004, CT-051

**Remaining dependency:** VM/volume creation does not implement approved physical co-residency, backup authority, retained-copy catalogues or recoverable key custody.

**Review state:** PROPOSED_ALLOCATION; actual applicability, named authority and evidence assignment pending

## BKP-002

Restore workflows SHALL enforce the same tenant, security-zone, identity, and evidence controls as backup ingestion.


### BKP-002.A01

**Assertion:** Complete source obligation; all applicable clauses must be satisfied: Restore workflows SHALL enforce the same tenant, security-zone, identity, and evidence controls as backup ingestion.

**Owner / location:** Backup operations / Eligible host/storage pools, actual scheduler, volume/copy service, backup and protected recovery estate

**Disposition:** EXTERNAL_PLATFORM_STORAGE_PROTECTION_CONTROL_WITH_PARTIAL_WORKLOAD_CODE. **Evidence class:** NATIVE_NOT_RUN; related local fixtures/engine checks are narrower evidence, not satisfaction

**Artifact or required operating record:** Accepted placement/storage/protection profiles and native allocation, retention, copy/key and restore procedures — specifically: Complete source obligation; all applicable clauses must be satisfied: Restore workflows SHALL enforce the same tenant, security-zone, identity, and evidence controls as backup ingestion.

**Available related source:** [terraform/modules/nutanix-workload](../../../terraform/modules/nutanix-workload) · [terraform/modules/vsphere-workload](../../../terraform/modules/vsphere-workload) · [terraform/modules/openstack-workload](../../../terraform/modules/openstack-workload) · [docs/current/TAD-infrastructure.md](../../current/TAD-infrastructure.md)

**Verification:** Check real initial/recovery placement and unauthorized attachment/copy access; measure usable isolated restore with required dependencies. Baseline procedures: CT-052, CT-054

**Remaining dependency:** VM/volume creation does not implement approved physical co-residency, backup authority, retained-copy catalogues or recoverable key custody.

**Review state:** PROPOSED_ALLOCATION; actual applicability, named authority and evidence assignment pending

## BKP-003

Every protected production WSD SHALL have a BackupPolicy with consistency, retention, location, key and protected-copy requirements; successful isolated restore SHALL be demonstrated at the policy cadence.


### BKP-003.A01

**Assertion:** Complete source obligation; all applicable clauses must be satisfied: Every protected production WSD SHALL have a BackupPolicy with consistency, retention, location, key and protected-copy requirements; successful isolated restore SHALL be demonstrated at the policy cadence.

**Owner / location:** Backup operations / Eligible host/storage pools, actual scheduler, volume/copy service, backup and protected recovery estate

**Disposition:** EXTERNAL_PLATFORM_STORAGE_PROTECTION_CONTROL_WITH_PARTIAL_WORKLOAD_CODE. **Evidence class:** NATIVE_NOT_RUN; related local fixtures/engine checks are narrower evidence, not satisfaction

**Artifact or required operating record:** Accepted placement/storage/protection profiles and native allocation, retention, copy/key and restore procedures — specifically: Complete source obligation; all applicable clauses must be satisfied: Every protected production WSD SHALL have a BackupPolicy with consistency, retention, location, key and protected-copy requirements; successful isolated restore SHALL be demonstrated at the policy cadence.

**Available related source:** [terraform/modules/nutanix-workload](../../../terraform/modules/nutanix-workload) · [terraform/modules/vsphere-workload](../../../terraform/modules/vsphere-workload) · [terraform/modules/openstack-workload](../../../terraform/modules/openstack-workload) · [docs/current/TAD-infrastructure.md](../../current/TAD-infrastructure.md)

**Verification:** Check real initial/recovery placement and unauthorized attachment/copy access; measure usable isolated restore with required dependencies. Baseline procedures: CT-051, CT-052, CT-053

**Remaining dependency:** VM/volume creation does not implement approved physical co-residency, backup authority, retained-copy catalogues or recoverable key custody.

**Review state:** PROPOSED_ALLOCATION; actual applicability, named authority and evidence assignment pending

### BKP-003.A02

**Assertion:** Every protected production WSD SHALL have a BackupPolicy with consistency, retention, location, key and protected-copy requirements

**Owner / location:** Backup operations / Eligible host/storage pools, actual scheduler, volume/copy service, backup and protected recovery estate

**Disposition:** EXTERNAL_PLATFORM_STORAGE_PROTECTION_CONTROL_WITH_PARTIAL_WORKLOAD_CODE. **Evidence class:** NATIVE_NOT_RUN; related local fixtures/engine checks are narrower evidence, not satisfaction

**Artifact or required operating record:** Accepted placement/storage/protection profiles and native allocation, retention, copy/key and restore procedures — specifically: Every protected production WSD SHALL have a BackupPolicy with consistency, retention, location, key and protected-copy requirements

**Available related source:** [terraform/modules/nutanix-workload](../../../terraform/modules/nutanix-workload) · [terraform/modules/vsphere-workload](../../../terraform/modules/vsphere-workload) · [terraform/modules/openstack-workload](../../../terraform/modules/openstack-workload) · [docs/current/TAD-infrastructure.md](../../current/TAD-infrastructure.md)

**Verification:** Check real initial/recovery placement and unauthorized attachment/copy access; measure usable isolated restore with required dependencies. Baseline procedures: CT-051, CT-052, CT-053

**Remaining dependency:** VM/volume creation does not implement approved physical co-residency, backup authority, retained-copy catalogues or recoverable key custody.

**Review state:** PROPOSED_ALLOCATION; actual applicability, named authority and evidence assignment pending

### BKP-003.A03

**Assertion:** successful isolated restore SHALL be demonstrated at the policy cadence.

**Owner / location:** Backup operations / Eligible host/storage pools, actual scheduler, volume/copy service, backup and protected recovery estate

**Disposition:** EXTERNAL_PLATFORM_STORAGE_PROTECTION_CONTROL_WITH_PARTIAL_WORKLOAD_CODE. **Evidence class:** NATIVE_NOT_RUN; related local fixtures/engine checks are narrower evidence, not satisfaction

**Artifact or required operating record:** Accepted placement/storage/protection profiles and native allocation, retention, copy/key and restore procedures — specifically: successful isolated restore SHALL be demonstrated at the policy cadence.

**Available related source:** [terraform/modules/nutanix-workload](../../../terraform/modules/nutanix-workload) · [terraform/modules/vsphere-workload](../../../terraform/modules/vsphere-workload) · [terraform/modules/openstack-workload](../../../terraform/modules/openstack-workload) · [docs/current/TAD-infrastructure.md](../../current/TAD-infrastructure.md)

**Verification:** Check real initial/recovery placement and unauthorized attachment/copy access; measure usable isolated restore with required dependencies. Baseline procedures: CT-051, CT-052, CT-053

**Remaining dependency:** VM/volume creation does not implement approved physical co-residency, backup authority, retained-copy catalogues or recoverable key custody.

**Review state:** PROPOSED_ALLOCATION; actual applicability, named authority and evidence assignment pending

## BKP-004

Production credentials SHALL NOT be able to destroy or reduce the protection of recovery copies designated independent/immutable; retained copies SHALL keep the keys and catalogue required for authorized recovery.


### BKP-004.A01

**Assertion:** Complete source obligation; all applicable clauses must be satisfied: Production credentials SHALL NOT be able to destroy or reduce the protection of recovery copies designated independent/immutable; retained copies SHALL keep the keys and catalogue required for authorized recovery.

**Owner / location:** Backup operations / Eligible host/storage pools, actual scheduler, volume/copy service, backup and protected recovery estate

**Disposition:** EXTERNAL_PLATFORM_STORAGE_PROTECTION_CONTROL_WITH_PARTIAL_WORKLOAD_CODE. **Evidence class:** NATIVE_NOT_RUN; related local fixtures/engine checks are narrower evidence, not satisfaction

**Artifact or required operating record:** Accepted placement/storage/protection profiles and native allocation, retention, copy/key and restore procedures — specifically: Complete source obligation; all applicable clauses must be satisfied: Production credentials SHALL NOT be able to destroy or reduce the protection of recovery copies designated independent/immutable; retained copies SHALL keep the keys and catalogue required for authorized recovery.

**Available related source:** [terraform/modules/nutanix-workload](../../../terraform/modules/nutanix-workload) · [terraform/modules/vsphere-workload](../../../terraform/modules/vsphere-workload) · [terraform/modules/openstack-workload](../../../terraform/modules/openstack-workload) · [docs/current/TAD-infrastructure.md](../../current/TAD-infrastructure.md)

**Verification:** Check real initial/recovery placement and unauthorized attachment/copy access; measure usable isolated restore with required dependencies. Baseline procedures: CT-038, CT-051, CT-053

**Remaining dependency:** VM/volume creation does not implement approved physical co-residency, backup authority, retained-copy catalogues or recoverable key custody.

**Review state:** PROPOSED_ALLOCATION; actual applicability, named authority and evidence assignment pending

### BKP-004.A02

**Assertion:** Production credentials SHALL NOT be able to destroy or reduce the protection of recovery copies designated independent/immutable

**Owner / location:** Backup operations / Eligible host/storage pools, actual scheduler, volume/copy service, backup and protected recovery estate

**Disposition:** EXTERNAL_PLATFORM_STORAGE_PROTECTION_CONTROL_WITH_PARTIAL_WORKLOAD_CODE. **Evidence class:** NATIVE_NOT_RUN; related local fixtures/engine checks are narrower evidence, not satisfaction

**Artifact or required operating record:** Accepted placement/storage/protection profiles and native allocation, retention, copy/key and restore procedures — specifically: Production credentials SHALL NOT be able to destroy or reduce the protection of recovery copies designated independent/immutable

**Available related source:** [terraform/modules/nutanix-workload](../../../terraform/modules/nutanix-workload) · [terraform/modules/vsphere-workload](../../../terraform/modules/vsphere-workload) · [terraform/modules/openstack-workload](../../../terraform/modules/openstack-workload) · [docs/current/TAD-infrastructure.md](../../current/TAD-infrastructure.md)

**Verification:** Check real initial/recovery placement and unauthorized attachment/copy access; measure usable isolated restore with required dependencies. Baseline procedures: CT-038, CT-051, CT-053

**Remaining dependency:** VM/volume creation does not implement approved physical co-residency, backup authority, retained-copy catalogues or recoverable key custody.

**Review state:** PROPOSED_ALLOCATION; actual applicability, named authority and evidence assignment pending

### BKP-004.A03

**Assertion:** retained copies SHALL keep the keys and catalogue required for authorized recovery.

**Owner / location:** Backup operations / Eligible host/storage pools, actual scheduler, volume/copy service, backup and protected recovery estate

**Disposition:** EXTERNAL_PLATFORM_STORAGE_PROTECTION_CONTROL_WITH_PARTIAL_WORKLOAD_CODE. **Evidence class:** NATIVE_NOT_RUN; related local fixtures/engine checks are narrower evidence, not satisfaction

**Artifact or required operating record:** Accepted placement/storage/protection profiles and native allocation, retention, copy/key and restore procedures — specifically: retained copies SHALL keep the keys and catalogue required for authorized recovery.

**Available related source:** [terraform/modules/nutanix-workload](../../../terraform/modules/nutanix-workload) · [terraform/modules/vsphere-workload](../../../terraform/modules/vsphere-workload) · [terraform/modules/openstack-workload](../../../terraform/modules/openstack-workload) · [docs/current/TAD-infrastructure.md](../../current/TAD-infrastructure.md)

**Verification:** Check real initial/recovery placement and unauthorized attachment/copy access; measure usable isolated restore with required dependencies. Baseline procedures: CT-038, CT-051, CT-053

**Remaining dependency:** VM/volume creation does not implement approved physical co-residency, backup authority, retained-copy catalogues or recoverable key custody.

**Review state:** PROPOSED_ALLOCATION; actual applicability, named authority and evidence assignment pending
