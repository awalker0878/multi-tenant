# 1. Choose the platform boundary and configuration owner

[Documentation home](../../README.md) · [Source document](../../../reference/Portable_Hosting_Delivery_Kits_v1_1/02_Engineering/Platform_Engineering_and_Build_Specifications.docx) · [Chapter index](README.md)

> **Source:** PBS — Delivery-kit v1.1 collection; original document version retained in the front matter. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: 8c2dd9e86b4ea021922777a963534c6b52d85dff8ee398c3a12cc81287356643 -->
<a id="PBS_01"></a>

One WSD delivery spans several infrastructure owners. The selected hypervisor provider does not automatically establish the fabric, security edge, identity, addressing, backup and recovery services.

Design basis and related records: [RA §15](../../architecture/reference/15-cross-vendor-realization-model.md#RA_s_015)  •  [RA §20](../../architecture/reference/20-provisioning-model-and-infrastructure-work-packages.md#RA_s_020)  •  [VC §1](../vendor-cards/1-common-scope-and-native-implementation-contract.md#VC_01)  •  [PROV §3](../../implementation/provisioning-strategy/3-terraform-native-tools-and-operation-level-support.md#PROV_s_003)


<a id="source-table-21"></a>

| Resource family | Commissioning / mutation owner | Accepted consumer output |
| --- | --- | --- |
| Physical transport and OOB | P0/P1 foundation owner and selected network/hardware mechanism. | Actual paths, permitted transport, interface capacity and recovery access. |
| Native platform | P2 owner using the supported installer/lifecycle method and qualified APIs. | Healthy supported cluster/control scope, eligible pools, storage and network capability. |
| ZIP and common services | P3 security, network-service, identity, storage and protection owners. | Scoped attachments, endpoints, permissions, capacity, support and loss behaviour. |
| Tenant and workload | P4/P5 resource owners using approved modules/API operations. | Owned networks, compute/data attachments, protection and current activation evidence. |
| Lifecycle | P6 owner of each affected native resource, with coordinated dependencies. | Changed as-built, retained obligations, requalification and cleanup evidence. |

A native installer may own controller databases, platform certificates, host configuration and transport setup. A Terraform module may own tenant VMs, networks or a supported policy resource. Record ownership at the smallest supported independent resource boundary; do not place overlapping controllers over the same field or object.

The operation specification contains create, read/observe, update, adoption, replacement, deletion and uncertain-outcome recovery separately. For each operation identify its input artifact, privilege scope, completion signal and possible data effect. Read access to a product API cannot establish full lifecycle coverage.

Build sequence is dependency-driven, not tool-driven. P2 can use accepted temporary P0 services; P2/P3 offered-service acceptance is resolved before ordinary tenant allocation.

Continue with: [PBS §8](8-publish-shared-service-handoffs-without-sharing-authority.md#PBS_08)  •  [PBS §9](9-release-a-native-build-package-that-can-be-independently-reviewed.md#PBS_09)

[Chapter index](README.md) · [Next chapter](2-nutanix-commission-the-hosting-cell.md)

<!-- BEGIN GENERATED DECISION LINKS -->

## Related decision records

- [ADR-0014 — Bootstrap management and trust before consuming native APIs](../../adr/0014-bootstrap-management-and-trust-before-consuming-native-apis.md)

<!-- END GENERATED DECISION LINKS -->
