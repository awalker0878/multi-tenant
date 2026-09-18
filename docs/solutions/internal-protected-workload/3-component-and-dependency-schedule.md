# 3. Component and dependency schedule

[Documentation home](../../README.md) · [Source document](../../../reference/Portable_Hosting_Delivery_Kits_v1_1/05_Reference_v1_4/07_Worked_Infrastructure_Design_and_Acceptance_v1_4.docx) · [Chapter index](README.md)

> **Source:** WD — Draft v1.4. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: e4a2e42888349b5967f7b3174c78e53171728b13e99e4c78bc3cfb53310f68db -->
<a id="WD14_S03"></a>

The component IDs below are architecture identities, not mandated product object names. Where a security platform combines EC and SE functions, it must preserve their routing, policy and management scopes. Where it separates them, both members of the composed boundary belong in the path and failure record.

Choose one hosting stack per qualification campaign. Repeating the same fixture on the next stack is portable alternative placement. Simultaneously splitting a production WSD between stacks is composite delivery and requires additional latency, dependency and recovery design.

The provider service network and security contexts may be shared physical infrastructure. Its endpoints, managers, storage, keys and power dependencies remain in the failure and co-residency analysis. No row implies that one VM, two hosts or a named cluster satisfies a product minimum or a promised failure model.


<a id="source-table-49"></a>

| Component ID | Infrastructure role | Accountability and dependency |
| --- | --- | --- |
| SITE-REF-A / CELL-REF-A | Primary illustrative site and one selected native hosting cell. | Site owner records actual racks, power, links, platform and storage fault groups. |
| FAB-REF / OOB-REF | Routed platform transport and separately designed hardware recovery access. | Network owner; OOB independence evaluated against the stated production-path failure. |
| MGMT-REF | Protected administrative domains, privileged access and approved execution interfaces. | Management and identity owners; not a universally routed management subnet. |
| HP-O / HP-R | Eligible compute pools for the approved OZ and RZ sharing decisions. | Platform owner enforces placement, evacuation, restart and recovery eligibility. |
| EC-01 / EC-02 | Tenant boundary contexts joining only that tenant's allowed domain and service paths. | Security-edge owner; separate policy, routing, identity and change scope. |
| SE-01 / SE-02 | Service-edge contexts receiving their corresponding dedicated tenant service handoff. | Provider-service security owner; only approved endpoint traffic crosses the boundary. |
| SVC-REF | Provider-controlled service domain with resolver, time, log ingestion and repository endpoints. | Service owners control entitlement, management, backend and return routes. |
| BKP-REF / KEY-REF | Qualified protection catalogue/repository and key/trust service dependencies. | Protection and key custodians; routine tenant identities cannot destroy retained recovery. |
| SITE-REF-B | Optional prequalified recovery target when the offered class includes site recovery. | Not automatically available; actual target capacity, keys, data and fencing must be accepted. |

Related documents: [QUAL — Actual site and failure records](../../assurance/site-qualification/README.md#V14_QUAL_START)  \|  [SVC — Service and recovery dependencies](../../architecture/shared-services/README.md#V14_SVC_START)

[Previous chapter](2-reference-decisions-and-infrastructure-boundaries.md) · [Chapter index](README.md) · [Next chapter](4-tenant-attachment-and-address-schedule.md)
