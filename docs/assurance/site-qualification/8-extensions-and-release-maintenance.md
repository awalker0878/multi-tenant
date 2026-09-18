# 8. Extensions and release maintenance

[Documentation home](../../README.md) · [Source document](../../../reference/Portable_Hosting_Delivery_Kits_v1_1/05_Reference_v1_4/06_Site_Design_Qualification_and_Operations_v1_4.docx) · [Chapter index](README.md)

> **Source:** QUAL — Draft v1.4. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: 783edbba45483d0d3c3b966765589762698836320237906a0f9a60080574af37 -->
<a id="__RefHeading___Toc10047_1525915568"></a>
<a id="QUAL_s_008"></a>

Parent architecture: [RA §19](../../architecture/reference/19-physical-workloads-and-future-platform-extensions.md#RA_s_019)  •  [RA §29](../../architecture/reference/29-architecture-decisions-and-alternatives.md#RA_s_029)  •  [RA §30](../../architecture/reference/30-implementation-handoff-and-delivery-sequence.md#RA_s_030)

Bare metal, containers, accelerators, cross-vendor overlay federation, L2 stretch and higher-assurance extensions are not silently promoted into the base offered service. An extension supplies its own component topology, trust/failure boundaries, actual supported stack, provisioning ownership, service parameters and applicable qualification. Reusing the WSD terminology does not make a container namespace or physical port a complete security boundary. \[[B2](09-references-parent-basis-and-external-context.md#QUAL_src_B2) §19\]


<a id="source-table-95"></a>

| Extension | Specific additional design | Gate before offering |
| --- | --- | --- |
| Bare metal | BMC/boot/firmware, port/gateway authority, data attachment and sanitization before reuse. | G0 extension scope and G1–G4 applicable qualification. |
| Containers | Control-plane/node sharing, network-policy enforcement, privileged workloads, storage and cluster recovery. | Separate service design and proof of the required tenancy boundary. |
| Special devices/accelerators | Physical/device tenancy, host compatibility, reset/data handling and mobility limits. | Supported assignment and recovery/exit evidence. |
| L2 stretch or composite cross-stack | Actual gateway/partition/fencing, latency, failure coupling and ownership. | Accepted variation with no bypass or unsupported availability promise. |
| HRZ/higher assurance | Source applicability, infrastructure dedication/control scope and explicit approval. | Not a base portable cloud offering; separate authorized design. |

Maintain the document family as one versioned architecture release. Change the parent when a durable design decision changes; update the relevant supplement when an engineering pattern or evidence interface changes; update the site/as-built record when actual values or resources change. A supplement must not silently weaken the parent. A detected conflict remains open until resolved by the appropriate architecture/security authority.

The release package includes the gap map, primary-home crosswalk, source review status, baseline requirements/tests and reproducible document-generation source. Automated package checks verify identifiers and links, not deployed safety. Future maintainers should update fields after editing and rerun rendering/link checks before release, then re-evaluate which installed environments are affected.

Related engineering: [Document precedence](../gap-map/1-document-family-scope-and-precedence.md#GM_s_001)  •  [Knowledge ownership and maintenance](../gap-map/2-primary-knowledge-homes-and-cross-cutting-changes.md#GM_s_002)

[Previous chapter](7-operating-accountability-handover-and-change.md) · [Chapter index](README.md) · [Next chapter](09-references-parent-basis-and-external-context.md)
