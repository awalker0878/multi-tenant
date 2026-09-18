# 4. Logical tenancy, security and traffic views

[Documentation home](../../README.md) · [Source document](../../../reference/Portable_Hosting_Delivery_Kits_v1_1/01_Architecture/HLD_and_Architecture_Review_Template.docx) · [Chapter index](README.md)

> **Source:** AT — Delivery-kit v1.1 collection; original document version retained in the front matter. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: 911b87e6a36d903a12535d16d75f1875c0cefb6b72c462895f7c2559b556708c -->
<a id="AT_04"></a>

Working record for AK-03. Complete the responses and attach the referenced evidence or drawing; do not replace an unresolved item with an unsupported assumption.

Baseline and related records: [RA §7](../../architecture/reference/7-tenant-environments-and-security-domain-placement.md#RA_s_007)  •  [RA §8](../../architecture/reference/8-zone-interfaces-routing-and-security-edge-topology.md#RA_s_008)  •  [WD §6](../../solutions/internal-protected-workload/6-worked-forwarding-and-return-route-schedule.md#WD14_S06)


<a id="source-table-46"></a>

| Record / decision | What to enter | Working response |
| --- | --- | --- |
| V03 logical view | Tenants, WSDs, logical domains and site/platform instances with authorities. | {{AT\_V03}} |
| V04 path view | One approved flow and reply; one denied cross-tenant path; shared-service path. | {{AT\_V04}} |
| Boundary relationships | Two adjacent authorities, ZIP functions, default policy and approval ownership. | {{AT\_ZIPS}} |
| Bypass analysis | Native routing, shared segments, extra NICs, NAT, alternate families and failure paths. | {{AT\_BYPASS}} |
| Exposure model | Public, enterprise/partner and egress mediation; none unless explicitly selected. | {{AT\_EXPOSURE}} |
| Path schedule reference | Engineering flow/route records that will implement these views. | {{AT\_PATH\_REF}} |

Reviewer: every required trust transition has forwarding and enforcement explained; same zone class does not imply shared reachability.

Record status: Draft / In review / Accepted for stated scope / Returned for revision. Use the actual review record, not this prompt, as authority.

[Previous chapter](3-context-and-physical-deployment-views.md) · [Chapter index](README.md) · [Next chapter](5-management-data-and-service-dependencies.md)
