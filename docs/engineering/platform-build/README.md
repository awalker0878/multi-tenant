# Platform engineering and build specifications

[Documentation home](../../README.md) · [Source document](../../../reference/Portable_Hosting_Delivery_Kits_v1_1/02_Engineering/Platform_Engineering_and_Build_Specifications.docx)

> **Source:** PBS — Delivery-kit v1.1 collection; original document version retained in the front matter. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: 8c2dd9e86b4ea021922777a963534c6b52d85dff8ee398c3a12cc81287356643 -->

## Chapters

- [1. Choose the platform boundary and configuration owner](1-choose-the-platform-boundary-and-configuration-owner.md)
- [2. Nutanix: commission the hosting cell](2-nutanix-commission-the-hosting-cell.md)
- [3. Nutanix: realize a tenant and its workload domains](3-nutanix-realize-a-tenant-and-its-workload-domains.md)
- [4. VMware/NSX: commission transport, compute and edge roles](4-vmware-nsx-commission-transport-compute-and-edge-roles.md)
- [5. VMware/NSX: bind domain, workload and policy lifecycles](5-vmware-nsx-bind-domain-workload-and-policy-lifecycles.md)
- [6. OpenStack: commission a distribution, not a generic label](6-openstack-commission-a-distribution-not-a-generic-label.md)
- [7. OpenStack: protect mandatory network mutation](7-openstack-protect-mandatory-network-mutation.md)
- [8. Publish shared-service handoffs without sharing authority](8-publish-shared-service-handoffs-without-sharing-authority.md)
- [9. Release a native build package that can be independently reviewed](9-release-a-native-build-package-that-can-be-independently-reviewed.md)

## Source front matter
DESIGN DEVELOPMENT  /  PBS

## Platform Engineering and Build Specifications

*Assign native resource ownership, dependencies, build outputs and acceptance for each vendor stack.*

Kit release v1.1 • 17 September 2026 • Parent architecture v1.4 retained

Proposed engineering development. Reference examples, site decisions, actual observations and approval remain separate.

This supplement develops the earlier vendor cards into build specifications. Select one platform track plus the required shared infrastructure. Every native object still needs the actual supported release and environment values from the LLD. No commands, provider versions, platform installation or live test result are invented.

## Section navigation

[1. Choose the platform boundary and configuration owner](1-choose-the-platform-boundary-and-configuration-owner.md#PBS_01)

[2. Nutanix: commission the hosting cell](2-nutanix-commission-the-hosting-cell.md#PBS_02)

[3. Nutanix: realize a tenant and its workload domains](3-nutanix-realize-a-tenant-and-its-workload-domains.md#PBS_03)

[4. VMware/NSX: commission transport, compute and edge roles](4-vmware-nsx-commission-transport-compute-and-edge-roles.md#PBS_04)

[5. VMware/NSX: bind domain, workload and policy lifecycles](5-vmware-nsx-bind-domain-workload-and-policy-lifecycles.md#PBS_05)

[6. OpenStack: commission a distribution, not a generic label](6-openstack-commission-a-distribution-not-a-generic-label.md#PBS_06)

[7. OpenStack: protect mandatory network mutation](7-openstack-protect-mandatory-network-mutation.md#PBS_07)

[8. Publish shared-service handoffs without sharing authority](8-publish-shared-service-handoffs-without-sharing-authority.md#PBS_08)

[9. Release a native build package that can be independently reviewed](9-release-a-native-build-package-that-can-be-independently-reviewed.md#PBS_09)

Basis: linked RA/WD and role-kit sections retain their original authority. The elaborations, record formats and calculations in this supplement are local proposals, not new government requirements. D-source references identify freshly checked public mechanisms, not installed compatibility. Exact source locators are in 04\_Shared/development/source\_reviews.csv.
