# 6. Control inheritance, assurance and organizational interfaces

[Documentation home](../../README.md) · [Source document](../../../reference/Portable_Hosting_Delivery_Kits_v1_1/05_Reference_v1_4/06_Site_Design_Qualification_and_Operations_v1_4.docx) · [Chapter index](README.md)

> **Source:** QUAL — Draft v1.4. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: 783edbba45483d0d3c3b966765589762698836320237906a0f9a60080574af37 -->
<!-- SOURCE-BLOCK QUAL:75 BEGIN -->

<a id="__RefHeading___Toc10043_1525915568"></a>
<a id="QUAL_s_006"></a>

<!-- SOURCE-BLOCK QUAL:75 END -->

<!-- SOURCE-BLOCK QUAL:76 BEGIN -->

Parent architecture: [RA §1](../../architecture/reference/1-purpose-scope-and-architectural-authority.md#RA_s_001)  •  [RA §6](../../architecture/reference/6-management-platform-control-and-out-of-band-access.md#RA_s_006)  •  [RA §7](../../architecture/reference/7-tenant-environments-and-security-domain-placement.md#RA_s_007)  •  [RA §13](../../architecture/reference/13-identity-cryptography-and-service-trust.md#RA_s_013)  •  [RA §26](../../architecture/reference/26-operating-model-capacity-and-observability.md#RA_s_026)  •  [RA §28](../../architecture/reference/28-architecture-acceptance-and-verification.md#RA_s_028)

<!-- SOURCE-BLOCK QUAL:76 END -->

<!-- SOURCE-BLOCK QUAL:77 BEGIN -->

The architecture supplies infrastructure controls and defined interfaces to organization-wide controls. It does not replace the personnel, facility, procurement, maintenance, training, privacy or risk-management authorities. For each selected control and parameter, identify provider implementation, tenant implementation, shared responsibility or accepted inheritance, and retain evidence of the boundary. \[[B2](09-references-parent-basis-and-external-context.md#QUAL_src_B2) §§1, 26, 28\]

<!-- SOURCE-BLOCK QUAL:77 END -->

<!-- SOURCE-BLOCK QUAL:78 BEGIN -->


<a id="source-table-78"></a>

| Control interface | Hosting design obligation | External owner/evidence to resolve |
| --- | --- | --- |
| Physical/environmental | Record site/rack access, power, media custody and failure groups that hosting depends on. | Facility authority; accepted site protections and current evidence. |
| Personnel and privileged roles | Scope access and support/recovery duties; remove stale grants. | Relevant personnel/security and identity authorities; eligibility and access-review evidence. |
| Maintenance and support | Controlled vendor sessions, supported update/repair path, diagnostics handling and part/media disposition. | Platform, maintenance and security owners; procedures and supplier access records. |
| Training and operations | Operators can execute recovery, containment and safe change for the actual stack. | Operational owner; exercised runbooks, role competence and escalation coverage. |
| Data/privacy/location | Apply approved data, copy, telemetry, key and support-location constraints. | Data/privacy/legal/security authorities; decisions and retention obligations. |
| Assessment and authorization | Supply configuration/test/inheritance evidence tied to actual scope and current conditions. | Assessor and designated authorizing authority; separate attributable decision. |

<!-- SOURCE-BLOCK QUAL:78 END -->

<!-- SOURCE-BLOCK QUAL:79 BEGIN -->

<!-- SOURCE-BLOCK QUAL:79 END -->

<!-- SOURCE-BLOCK QUAL:80 BEGIN -->

The current ITSP.10.033 catalogue supersedes ITSG-33 Annex 3A; source edition and identifier remain necessary when reconciling inherited assessments. The family mappings in the baseline requirements are selection aids, not a complete assessment. The regenerated family index in this release includes every family present in the retained catalogue, while additional organizational interfaces above remain explicit applicability decisions. \[[S05](09-references-parent-basis-and-external-context.md#QUAL_src_S05)\]

<!-- SOURCE-BLOCK QUAL:80 END -->

<!-- SOURCE-BLOCK QUAL:81 BEGIN -->

A supplier or shared service may provide inherited evidence for an infrastructure control, but that evidence must apply to the actual service, site, version, tenant scope and time interval. Inheritance cannot silently cover a different data location or administrative path. The adopting authority records residual gaps and conditions rather than treating a cloud/private-platform brand as a compliance certificate.

<!-- SOURCE-BLOCK QUAL:81 END -->

<!-- SOURCE-BLOCK QUAL:82 BEGIN -->

Related engineering: [Isolation dimensions](../../engineering/platform-realizations/2-physical-placement-and-the-sharing-decision.md#VND_s_002)  •  [Adoption and inheritance gaps](../gap-map/3-detailed-gap-register-and-treatment.md#GM_s_003)

<!-- SOURCE-BLOCK QUAL:82 END -->

[Previous chapter](5-qualification-stages-applicability-and-evidence.md) · [Chapter index](README.md) · [Next chapter](7-operating-accountability-handover-and-change.md)

<!-- BEGIN GENERATED DECISION LINKS -->

## Related decision records

- [ADR-0017 — Separate reference adoption, technical qualification and authorization](../../adr/0017-separate-reference-adoption-technical-qualification-and-authorization.md)

<!-- END GENERATED DECISION LINKS -->
