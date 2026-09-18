# 3. Context and physical deployment views

[Documentation home](../../README.md) · [Source document](../../../reference/Portable_Hosting_Delivery_Kits_v1_1/01_Architecture/HLD_and_Architecture_Review_Template.docx) · [Chapter index](README.md)

> **Source:** AT — Delivery-kit v1.1 collection; original document version retained in the front matter. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: 911b87e6a36d903a12535d16d75f1875c0cefb6b72c462895f7c2559b556708c -->
<a id="AT_03"></a>

Working record for AK-03. Complete the responses and attach the referenced evidence or drawing; do not replace an unresolved item with an unsupported assumption.

Baseline and related records: [RA §3](../../architecture/reference/3-system-context-and-physical-hosting-topology.md#RA_s_003)  •  [RA §4](../../architecture/reference/4-hosting-cells-resource-pools-and-failure-boundaries.md#RA_s_004)


<a id="source-table-38"></a>

| Record / decision | What to enter | Working response |
| --- | --- | --- |
| V01 context | Attach a view of consumers, providers, external authorities and offered service boundary. | {{AT\_V01}} |
| V02 physical view | Attach sites, cells, host/storage/edge/control roles and main links. | {{AT\_V02}} |
| Failure dependencies | Identify shared racks, power, links, managers, storage and trust services. | {{AT\_FAILURES}} |
| Physical sharing | State physical dedication versus logical separation per component role. | {{AT\_PHYSICAL}} |
| External dependencies | Owner, service interface and availability/approval boundary. | {{AT\_EXTERNAL}} |
| Assumptions | Unconfirmed inventory/topology assumptions and who must resolve them. | {{AT\_ASSUMPTIONS}} |

Reviewer: redundant symbols have explicit failure assumptions; a hosting cell is not automatically an independent failure domain.

Record status: Draft / In review / Accepted for stated scope / Returned for revision. Use the actual review record, not this prompt, as authority.

[Previous chapter](2-requirements-and-applicability.md) · [Chapter index](README.md) · [Next chapter](4-logical-tenancy-security-and-traffic-views.md)
