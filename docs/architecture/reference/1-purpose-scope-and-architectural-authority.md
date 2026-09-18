# 1. Purpose, scope and architectural authority

[Documentation home](../../README.md) · [Source document](../../../reference/Portable_Hosting_Delivery_Kits_v1_1/05_Reference_v1_4/00_Reference_Architecture_v1_4.docx) · [Chapter index](README.md)

> **Source:** RA — Draft v1.4. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: e50894d7f7b87cef50a283399b85925c8a96c5b9cd0428ce71ca0143d9be8d19 -->
<a id="__RefHeading___Toc3640_865363315"></a>
<a id="RA_s_001"></a>

This document defines the infrastructure that provides portable, secure multi-tenant hosting. It describes the arrangement of sites, physical networks, hosting platforms, security boundaries, management services, compute and storage resources, and the sequence used to provision and operate them. Nutanix, VMware/NSX and OpenStack are alternative realizations of that architecture. Terraform is one provisioning mechanism within the delivery strategy; the architecture does not depend on a bespoke service-controller application.

The reference envelope comprises virtual machines and their networks, data services, controlled external access and operational dependencies. Bare-metal and container hosting are explicit extensions. The security context is Unclassified, Protected A and Protected B with independently determined integrity and availability impacts. Classified and Protected C services need an additional architecture and authorization; an HRZ or dedicated-host label does not extend this scope. This scope is consistent with the boundaries stated by the Cyber Centre zoning guidance. \[[S01](34-appendix-d-sources-and-review-status.md#RA_src_S01); [S02](34-appendix-d-sources-and-review-status.md#RA_src_S02)\]


<a id="source-table-64"></a>

| This reference architecture decides | The implementation design supplies |
| --- | --- |
| Infrastructure layers, trust boundaries, selected topology patterns and ownership | Named sites, physical inventories, port/cable schedules and actual failure-domain assignments |
| How the same hosting requirement is realized on each vendor stack | Exact hardware, product/API/provider releases, entitlements and supported feature combinations |
| Provisioning packages, dependency gates, change boundaries and operational handover | Executable modules, platform installer configuration, pipeline tooling, credentials and environment values |
| Required isolation, recovery, verification and lifecycle outcomes | Measured capacity, approved service targets, executed evidence and formal authorization |

Draft v1.4 retains the v1.2 architecture-led structure and develops its engineering handoffs through linked supplements. The v1.2 narrative superseded the explanatory structure of v1.1. Its retained security and operational requirements are preserved in the accompanying traceability package, with explicit dispositions rather than silent deletion. API implementation detail, schema envelopes and controller algorithms are supporting implementation material, not the organizing model of this document. Appendix A explains the two historical v1.2 requirement clarifications preserved in this release.

## Authority and interpretation

Statements describing the reference design are proposed architectural decisions. They are not represented as verbatim government requirements. Applicable policy, the adopted control profile and authorization conditions take precedence. Standards citations identify their source context; implementation references describe products, not their approval. The approving authority must resolve conflicts before commissioning, and record variations with their effect on isolation, recovery and portability.

Use ITSP.80.022 together with ITSP.80.023 for zoning, ITSP.70.010 for virtualization risk, and the applicable security-risk lifecycle and control selection. The current ITSP.10.033 catalogue explicitly supersedes ITSG-33 Annex 3A; this is not a statement that every ITSG-33 lifecycle document was withdrawn. Preserve source editions when reconciling existing control records. \[[S01](34-appendix-d-sources-and-review-status.md#RA_src_S01); [S02](34-appendix-d-sources-and-review-status.md#RA_src_S02); [S03](34-appendix-d-sources-and-review-status.md#RA_src_S03); [S05](34-appendix-d-sources-and-review-status.md#RA_src_S05)\]

## Linked engineering document family

Draft v1.4 adds a controlled set of engineering supplements and a gap/decision register around this parent architecture. The parent remains the home of durable topology, security and provisioning choices. NET develops fabric, attachments and paths; VND develops the native realizations; PROV develops work-package execution; SVC develops services/data/recovery; QUAL develops site design and evidence; GM tracks unresolved decisions. A supplement cannot silently amend an adopted parent requirement.

Documentation coverage, approved site/vendor decisions, implemented automation, observed qualification and formal authorization remain separate states. The gap register identifies the owner role, blocking gate and proof still required for each unresolved implementation question. Relative document links work when the delivered files remain together; readable document and section IDs provide a fallback.

Related engineering: [GM §1 — Document family, scope and precedence](../../assurance/gap-map/1-document-family-scope-and-precedence.md#GM_s_001)

[Chapter index](README.md) · [Next chapter](2-design-drivers-and-selected-reference-pattern.md)

<!-- BEGIN GENERATED DECISION LINKS -->

## Related decision records

- [ADR-0003 — Let the infrastructure architecture lead the tooling](../../adr/0003-let-the-infrastructure-architecture-lead-the-tooling.md)

<!-- END GENERATED DECISION LINKS -->
