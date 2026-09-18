# 6. Portable, composite and migrated service choices

[Documentation home](../../README.md) · [Source document](../../../reference/Portable_Hosting_Delivery_Kits_v1_1/05_Reference_v1_4/03_Vendor_Stack_Realizations_v1_4.docx) · [Chapter index](README.md)

> **Source:** VND — Draft v1.4. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: 73be32b98783bd7857be8a00928c6894bf16f6bc98c8eb016058d3cf75b9d86b -->
<!-- SOURCE-BLOCK VND:83 BEGIN -->

<a id="__RefHeading___Toc4818_865363315"></a>
<a id="VND_s_006"></a>

<!-- SOURCE-BLOCK VND:83 END -->

<!-- SOURCE-BLOCK VND:84 BEGIN -->

Parent architecture: [RA §15](../../architecture/reference/15-cross-vendor-realization-model.md#RA_s_015)  •  [RA §27](../../architecture/reference/27-recovery-migration-and-retirement.md#RA_s_027)

<!-- SOURCE-BLOCK VND:84 END -->

<!-- SOURCE-BLOCK VND:85 BEGIN -->


<a id="source-table-85"></a>

| Delivery choice | Use when | Required additional design |
| --- | --- | --- |
| Portable alternative placement | One bounded environment can be rebuilt on another eligible stack. | Equivalent resource/service requirements, target image/data compatibility and outcome comparison. |
| Composite delivery | A deliberate service uses resources across several stacks concurrently. | Explicit domain/service boundaries, latency/capacity budget, common dependency and coordinated recovery ownership. |
| Cross-platform migration | Actual workload/data state moves from one stack to another. | Supported transfer/conversion, consistency point, fencing, cutover, reverse-data handling and source retirement. |
| Intra-platform live mobility | The qualified vendor platform moves a running workload inside an eligible arrangement. | Supported compute/storage/transport compatibility, retained policy and placement constraints. |

<!-- SOURCE-BLOCK VND:85 END -->

<!-- SOURCE-BLOCK VND:86 BEGIN -->

<!-- SOURCE-BLOCK VND:86 END -->

<!-- SOURCE-BLOCK VND:87 BEGIN -->

The default remains one bounded WSD realization in an eligible cell with explicitly consumed shared services. A composite placement needs a reason beyond spare capacity: network delay, data consistency, coupled maintenance and cross-stack restore can become dominant dependencies. It does not require a common cross-vendor overlay. Independent domains communicate through the approved service/security boundary. \[[B2](08-references-parent-basis-and-external-context.md#VND_src_B2) §§15, 27\]

<!-- SOURCE-BLOCK VND:87 END -->

<!-- SOURCE-BLOCK VND:88 BEGIN -->

Terraform can prepare target resources and controlled transfer connectivity; it does not itself make application state consistent or guarantee live migration across unrelated hypervisors. Data and image transfer uses a supported tool and an approved owner. After writes begin at the target, returning to the source may require reverse synchronization or restore; restarting a stale source is not a safe generic rollback.

<!-- SOURCE-BLOCK VND:88 END -->

<!-- SOURCE-BLOCK VND:89 BEGIN -->

Acceptance compares the same architectural outcomes, not identical topology. Record any lost optional function, changed operating task, required guest driver/boot change, data export limitation or special device dependency. A mandatory capability cannot be silently downgraded to keep a portability claim. Extensions remain visible in the service description and exit plan.

<!-- SOURCE-BLOCK VND:89 END -->

<!-- SOURCE-BLOCK VND:90 BEGIN -->

Related engineering: [Recovery and failback](../../architecture/shared-services/6-failure-recovery-migration-and-failback-topology.md#SVC_s_006)  •  [First-stack and portability qualification](../../assurance/site-qualification/5-qualification-stages-applicability-and-evidence.md#QUAL_s_005)

<!-- SOURCE-BLOCK VND:90 END -->

[Previous chapter](5-openstack-selected-services-backend-and-mandatory-policy.md) · [Chapter index](README.md) · [Next chapter](7-implementation-tuple-and-decision-package.md)

<!-- BEGIN GENERATED DECISION LINKS -->

## Related decision records

- [ADR-0005 — Keep vendor overlays local and connect through controlled handoffs](../../adr/0005-keep-vendor-overlays-local-and-connect-through-controlled-handoffs.md)

<!-- END GENERATED DECISION LINKS -->
