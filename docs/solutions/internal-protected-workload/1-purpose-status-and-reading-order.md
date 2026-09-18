# 1. Purpose, status and reading order

[Documentation home](../../README.md) · [Source document](../../../reference/Portable_Hosting_Delivery_Kits_v1_1/05_Reference_v1_4/07_Worked_Infrastructure_Design_and_Acceptance_v1_4.docx) · [Chapter index](README.md)

> **Source:** WD — Draft v1.4. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: e4a2e42888349b5967f7b3174c78e53171728b13e99e4c78bc3cfb53310f68db -->
<a id="WD14_S01"></a>

This is a worked infrastructure design for the reference architecture, not a site configuration, an approved bill of materials, or a claim that a vendor combination has passed qualification. It connects the same resource identities across topology, routing, policy, shared services, provisioning, failure handling and acceptance. The host-platform choice changes the native realization, not the required outcomes.

The starting fixture remains two tenants, two WSDs, four tenant domain instances, four permanent disposable workload endpoints and two tenant OZ-to-RZ relationships. This book explicitly adds the infrastructure that the small fixture previously left outside its count: service-facing handoffs, provider service endpoints, management paths, protection dependencies and temporary test capacity.

Treat every IP address, capacity value and next hop in this book as an illustrative design value. They use documentation address space and must be replaced through an approved site address plan. The IPv6 column is a separate qualification candidate; it does not assert that every selected platform offers dual-stack or IPv6-only service. \[R14-01, R14-02\]

Read RA for the architecture; NET and VND for mechanism choices; this book for the connected example; PROV for execution ownership; SVC for data and trust dependencies; and QUAL for actual acceptance. The working schedules do not authorize production changes.


<a id="source-table-32"></a>

| Record type | Meaning in this release | What it does not establish |
| --- | --- | --- |
| Reference selection | A concrete proposed way to instantiate the parent design. | Organizational adoption or vendor support. |
| Documentation-supported mechanism | A described product or protocol mechanism with a named source. | Support for the installed hardware, release, entitlement and configuration. |
| Site decision | An actual selection requiring an accountable owner and approval. | A value supplied by copying an illustrative table. |
| Observed qualification | Measurements against actual components, versions and an approved test scope. | Any result in this documentation-only release. |

Related documents: [RA — Architecture and authority](../../architecture/reference/README.md#V14_RA_START)  \|  [GM — Gap and decision ownership](../../assurance/gap-map/README.md#V14_GM_START)

[Chapter index](README.md) · [Next chapter](2-reference-decisions-and-infrastructure-boundaries.md)
