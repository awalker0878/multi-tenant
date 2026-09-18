# 9. Security Domain Instance

[Documentation home](../../README.md) · [Source document](../../../reference/migration-source-documents/Handbook_v1_0.docx) · [Chapter index](README.md)

> **Source:** HB10 — Draft v1.0. Historical source; not the active design.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: 100c760003b9ff956ae369ece65c5ffe7736f6d481496d8df4c99dd6105d4190 -->

> **Historical only.** Use the [v1.4 reference architecture](../../architecture/reference/README.md) for the active design baseline. Conflicting historical text has not been silently reconciled.
A Security Domain Instance is an isolated routing and policy namespace associated with a zone class, authority, platform/site realization, and assurance profile. Multiple WSDs may share an instance if the assurance profile permits and workload microsegmentation provides the required internal separation.


<a id="source-table-106"></a>

| SecurityDomainInstance = {<br>  zone\_class        = OZ \| RZ \| PAZ \| HRZ \| REZ \| MZ<br>  tenant\_scope      = &lt;namespace or provider service scope&gt;<br>  platform          = &lt;placement result&gt;<br>  site              = &lt;failure domain&gt;<br>  assurance\_profile = standard \| enhanced \| dedicated<br>  address\_scope     = &lt;IPAM authority&gt;<br>  routing\_policy    = derived<br>}<br> |
| --- |


<a id="source-table-107"></a>

| SDI-001 | A Security Domain Instance SHALL contain only networks authorized to share its routing/security authority. |
| --- | --- |


<a id="source-table-108"></a>

| SDI-002 | Sharing a zone class SHALL NOT imply reachability between independent Security Domain Instances. |
| --- | --- |


<a id="source-table-109"></a>

| SDI-003 | Dedicated Security Domain Instances SHOULD be available for workloads whose assurance profile or threat model requires stronger isolation than shared logical segmentation. |
| --- | --- |

[Previous chapter](8-workload-security-domain.md) · [Chapter index](README.md) · [Next chapter](10-security-zone-semantics.md)
