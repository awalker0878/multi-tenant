# 22. Vendor-platform and shared-service commissioning

[Documentation home](../../README.md) · [Source document](../../../reference/Portable_Hosting_Delivery_Kits_v1_1/05_Reference_v1_4/00_Reference_Architecture_v1_4.docx) · [Chapter index](README.md)

> **Source:** RA — Draft v1.4. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: e50894d7f7b87cef50a283399b85925c8a96c5b9cd0428ce71ca0143d9be8d19 -->
<a id="__RefHeading___Toc3682_865363315"></a>
<a id="RA_s_022"></a>

Platform commissioning turns installed capacity into an offered hosting service. The target platform must already have a functioning management path and supported installation. Commissioning establishes eligible compute pools, storage classes, overlay transport, baseline policy, security-edge integration and operational dependencies before any ordinary tenant request is admitted.


<a id="source-table-314"></a>

| Commissioning layer | Nutanix | VMware/NSX | OpenStack |
| --- | --- | --- | --- |
| Install/control | Supported cluster and Prism deployment; required Flow components | vCenter/ESXi and selected NSX control deployment | Supported distribution and service control/database/messaging deployment |
| Resource pools | Eligible AHV hosts, storage/controller scope and placement restrictions | ESXi clusters/host groups, datastore policies and placement restrictions | Nova/Placement hosts, enforced aggregates/traits/flavours and Cinder classes |
| Network foundation | Platform transport, VPC capability and isolated external-attachment capacity | Transport nodes/zones, Edge capacity and isolated upstream gateway pattern | Chosen Neutron backend, overlay transport, gateway roles and provider mappings |
| Mandatory security | Protected selectors, default policy and explicit ZIP integration | Provider rule hierarchy, protected groups and explicit ZIP integration | Controlled API/port/group defaults and explicit ZIP integration |
| Operational service | Identity, logging, images, keys, backup, monitoring and recovery integration | Same architectural dependencies with native integration | Same architectural dependencies with selected distribution services |

The platform owner publishes an implementation profile showing the chosen topology, actual versions, supported operations and dependencies. The profile explicitly identifies what Terraform can create, read, update, import and delete, what installer/lifecycle tooling owns, and what requires another service’s execution. API read access alone is not full lifecycle automation. Destructive replacement semantics, asynchronous tasks and eventual consistency are included in the support record.

## Common-service commissioning

The edge owner commissions resilient capacity, isolated routing/policy contexts, management controls and observability. Identity and key owners publish authorized consumption endpoints and role/key policies. Network services publish delegated address pools and DNS/DHCP ownership. Backup owners publish supported capture/restore methods, protected repositories and retention classes. Monitoring owners establish independent collection and tenant attribution. These services are not recreated independently by each vendor adapter.

Before the cell is advertised, execute a representative two-tenant environment with separate domain instances, approved shared-service access and protected management. Verify ordinary allocation, changes, fault behaviour, isolated restore and retirement. Prove the selected attachment design, including any shared connected network, under both normal and failed conditions. The measured capacity includes enabled inspection and failure reserve rather than unprotected throughput figures.

Platform readiness requires an accepted topology, supported product/API/provider combination, measured service limits, operational owners and current evidence for the service classes being offered. It is distinct from formal system authorization and from the health of any particular workload. A candidate feature that has only been documented is not advertised as a production capability. Existing service restrictions must remain visible after qualification expires or a dependency changes.

Build order versus ownership — Some installation tasks can run in parallel, but a tenant allocation cannot depend on a security, storage or management foundation that has not been accepted. A shared-service handoff is an explicit gate, not a promise that another team will configure it later.

Related engineering: [PROV §2 — Day-0 and steady-state commissioning without circular dependencies](../../implementation/provisioning-strategy/2-day-0-and-steady-state-commissioning-without-circular-dependencies.md#PROV_s_002)  •  [PROV §3 — Terraform, native tools and operation-level support](../../implementation/provisioning-strategy/3-terraform-native-tools-and-operation-level-support.md#PROV_s_003)  •  [SVC §1 — Shared service placement and consumption boundaries](../shared-services/1-shared-service-placement-and-consumption-boundaries.md#SVC_s_001)

[Previous chapter](21-day-0-bootstrap-and-physical-commissioning.md) · [Chapter index](README.md) · [Next chapter](23-tenant-domain-and-workload-provisioning-sequence.md)

<!-- BEGIN GENERATED DECISION LINKS -->

## Related decision records

- [ADR-0014 — Bootstrap management and trust before consuming native APIs](../../adr/0014-bootstrap-management-and-trust-before-consuming-native-apis.md)
- [ADR-0038 — Govern images and privileged dependency provenance across their lifecycle](../../adr/0038-govern-images-and-privileged-dependency-provenance-across-their-lifecycle.md)

<!-- END GENERATED DECISION LINKS -->
