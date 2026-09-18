# 7. Implementation tuple and decision package

[Documentation home](../../README.md) · [Source document](../../../reference/Portable_Hosting_Delivery_Kits_v1_1/05_Reference_v1_4/03_Vendor_Stack_Realizations_v1_4.docx) · [Chapter index](README.md)

> **Source:** VND — Draft v1.4. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: 73be32b98783bd7857be8a00928c6894bf16f6bc98c8eb016058d3cf75b9d86b -->
<!-- SOURCE-BLOCK VND:91 BEGIN -->

<a id="__RefHeading___Toc4820_865363315"></a>
<a id="VND_s_007"></a>

<!-- SOURCE-BLOCK VND:91 END -->

<!-- SOURCE-BLOCK VND:92 BEGIN -->

Parent architecture: [RA §15](../../architecture/reference/15-cross-vendor-realization-model.md#RA_s_015)  •  [RA §16](../../architecture/reference/16-nutanix-hosting-stack-reference-realization.md#RA_s_016)  •  [RA §17](../../architecture/reference/17-vmware-and-nsx-hosting-stack-reference-realization.md#RA_s_017)  •  [RA §18](../../architecture/reference/18-openstack-hosting-stack-reference-realization.md#RA_s_018)  •  [RA §22](../../architecture/reference/22-vendor-platform-and-shared-service-commissioning.md#RA_s_022)  •  [RA §30](../../architecture/reference/30-implementation-handoff-and-delivery-sequence.md#RA_s_030)

<!-- SOURCE-BLOCK VND:92 END -->

<!-- SOURCE-BLOCK VND:93 BEGIN -->

Each native realization needs a controlled implementation record before it is offered. This is an engineering record, not a new custom API schema. Preserve the exact hardware/firmware, product/service releases, enabled features, licences/entitlements, network/storage backends, management topology, API/provider versions and installer/tool ownership. A source review date or a provider repository version is not evidence that the installed combination is supported.

<!-- SOURCE-BLOCK VND:93 END -->

<!-- SOURCE-BLOCK VND:94 BEGIN -->


<a id="source-table-94"></a>

| Record | Must answer | Blocking condition |
| --- | --- | --- |
| Component and interface schedule | What exists, where it runs, how it connects and who owns it. | A diagrammed boundary has no actual routing/enforcement component. |
| Sharing and failure map | Which hosts, storage, managers, edge and trust dependencies are common. | Claimed dedication or independence is unsupported. |
| Operation support | Which tool creates, observes, changes, adopts, replaces, deletes and reconciles each native resource. | Required operation has only a placeholder or unmanaged side effect. |
| Service capability and limits | Which families, exposure, recovery and isolation classes were measured under which conditions. | An optional/unsupported feature is advertised as mandatory capability. |
| Evidence and decisions | Which tests ran on this tuple, which limits or exceptions apply and who approved use. | Candidate documentation or expired evidence substitutes for qualification. |
| Source currency | Which documentation edition was reviewed, what was inaccessible and what requires vendor confirmation. | A historic or restricted page is represented as full current verification. |

<!-- SOURCE-BLOCK VND:94 END -->

<!-- SOURCE-BLOCK VND:95 BEGIN -->

<!-- SOURCE-BLOCK VND:95 END -->

<!-- SOURCE-BLOCK VND:96 BEGIN -->

The supplied operation-coverage CSV is intentionally unqualified. Populate a row with actual resource types and supported operations, attach current vendor evidence and execute the lifecycle scenarios. Where another owner or installer manages the resource, name that owner and the accepted handoff rather than forcing the object into Terraform state. A provider change may require requalification even if the running platform release is unchanged.

<!-- SOURCE-BLOCK VND:96 END -->

<!-- SOURCE-BLOCK VND:97 BEGIN -->

Related engineering: [Vendor decision gaps](../../assurance/gap-map/3-detailed-gap-register-and-treatment.md#GM_s_003)  •  [Operation-level matrix](../../implementation/provisioning-strategy/3-terraform-native-tools-and-operation-level-support.md#PROV_s_003)  •  [Evidence applicability](../../assurance/site-qualification/5-qualification-stages-applicability-and-evidence.md#QUAL_s_005)

<!-- SOURCE-BLOCK VND:97 END -->

[Previous chapter](6-portable-composite-and-migrated-service-choices.md) · [Chapter index](README.md) · [Next chapter](08-references-parent-basis-and-external-context.md)
