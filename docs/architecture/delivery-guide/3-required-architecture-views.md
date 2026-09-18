# 3. Required architecture views

[Documentation home](../../README.md) · [Source document](../../../reference/Portable_Hosting_Delivery_Kits_v1_1/01_Architecture/Architecture_Kit.docx) · [Chapter index](README.md)

> **Source:** AK — Delivery-kit v1.1 collection; original document version retained in the front matter. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: f0cd99f187d5f883e0f752e07de20f8878bef02fa1d0b36817674ef59bfd9802 -->
<!-- SOURCE-BLOCK AK:36 BEGIN -->

<a id="AK_03"></a>

<!-- SOURCE-BLOCK AK:36 END -->

<!-- SOURCE-BLOCK AK:37 BEGIN -->

Create views that answer distinct questions but share component and interface IDs. Combine diagrams where useful; completeness is coverage, not a required count of separate drawings.

<!-- SOURCE-BLOCK AK:37 END -->

<!-- SOURCE-BLOCK AK:38 BEGIN -->

Baseline and related records: [RA §3](../reference/3-system-context-and-physical-hosting-topology.md#RA_s_003)  •  [RA §10](../reference/10-addressing-name-services-and-end-to-end-traffic.md#RA_s_010)  •  [AT §3](../../templates/hld/3-context-and-physical-deployment-views.md#AT_03)

<!-- SOURCE-BLOCK AK:38 END -->

<!-- SOURCE-BLOCK AK:39 BEGIN -->


<a id="source-table-39"></a>

| View | Question / minimum contents |
| --- | --- |
| V01 Context and service boundary | What service is offered and who owns each external dependency? Sites, tenants, provider services, consumers, external authorities. |
| V02 Physical deployment | Where are the equipment, links, power and shared failure dependencies? Sites/racks, cells, OOB, host pools, storage, edges, control components. |
| V03 Logical tenancy and security | Which independent authorities and zones exist? Tenant/WSD/domain/instance/network, owner, sharing and trust transitions. |
| V04 End-to-end forwarding and enforcement | Where do request and reply travel and where are they enforced? Gateways, ZIPs, allowed prefixes, routes, NAT, policy and native bypass candidates. |
| V05 Management and administrative authority | Who can change each component and by which protected path? Privileged endpoint, management domain, roles, API/BMC, break-glass and logging. |
| V06 Compute and storage | Which resources and copies share hardware/control and how is placement enforced? Pools, schedulers, virtual disks, file/object clients, copies, keys and protection. |
| V07 Shared-service consumption | What is the consumer allowed to do and how does the service reply? Service endpoint, client identity, return routes, backend authorization and admin plane. |
| V08 Failure and recovery | Which failures are covered and which dependencies must survive? Failure sets, quorum/fencing, independent trust, restored service scope and failback. |
| V09 Vendor realization | Which native components realize the same requirements on each selected stack? Actual tuple, mechanisms, enforcement locations, support limits and alternatives. |
| V10 Provisioning and lifecycle | What is installed, allocated, changed and retired by each owner? P0–P6 resources, prerequisites, single-writer ownership, handoffs and safe stops. |
| V11 Transition and operational model | How does the current environment become and remain the target? Adoption waves, dependencies, capacity, operating responsibilities, exit and disposal. |

<!-- SOURCE-BLOCK AK:39 END -->

<!-- SOURCE-BLOCK AK:40 BEGIN -->

<!-- SOURCE-BLOCK AK:40 END -->

<!-- SOURCE-BLOCK AK:41 BEGIN -->

Use a legend for data, management and dependency relationships. Show administrative and failure boundaries separately from routing boundaries. Identify shared equipment explicitly. A redundant icon does not establish independent power, storage, controller, uplink or key dependencies.

<!-- SOURCE-BLOCK AK:41 END -->

<!-- SOURCE-BLOCK AK:42 BEGIN -->

<!-- SOURCE-BLOCK AK:42 END -->

[Previous chapter](2-service-requirements-and-applicability.md) · [Chapter index](README.md) · [Next chapter](4-security-management-and-co-residency-decisions.md)
