# 3. Worked inter-zone routing and enforcement schedule

[Documentation home](../../README.md) · [Source document](../../../reference/Portable_Hosting_Delivery_Kits_v1_1/05_Reference_v1_4/02_Fabric_Security_and_Interfaces_v1_4.docx) · [Chapter index](README.md)

> **Source:** NET — Draft v1.4. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: 9c557d7d94dbdf24630994d2676aca3ddfa80e67c2910fb1a29ea4561c591dcf -->
<!-- SOURCE-BLOCK NET:43 BEGIN -->

<a id="__RefHeading___Toc5749_1525915568"></a>
<a id="NET_s_003"></a>

<!-- SOURCE-BLOCK NET:43 END -->

<!-- SOURCE-BLOCK NET:44 BEGIN -->

WD §§5–7 supplies an illustrative exact-prefix and next-hop schedule. Its service return path is explicit: each service endpoint returns the originating tenant prefixes through that tenant's service-edge context. A shared service segment is behind the controls, not an uninspected connection between native tenant gateways. Actual connected, source-validation and reverse-session behavior must still be qualified.

<!-- SOURCE-BLOCK NET:44 END -->

<!-- SOURCE-BLOCK NET:45 BEGIN -->

Parent architecture: [RA §8](../../architecture/reference/8-zone-interfaces-routing-and-security-edge-topology.md#RA_s_008)  •  [RA §10](../../architecture/reference/10-addressing-name-services-and-end-to-end-traffic.md#RA_s_010)  •  [RA §23](../../architecture/reference/23-tenant-domain-and-workload-provisioning-sequence.md#RA_s_023)

<!-- SOURCE-BLOCK NET:45 END -->

<!-- SOURCE-BLOCK NET:46 BEGIN -->

Use the VND §1 fixture: P01O and P01R are symbolic allocated prefixes for tenant-01; P02O and P02R belong to tenant-02. They are not real address allocations. REF-DATA-HTTPS is a deliberately simple test service using TCP/443 with endpoint TLS validation, not an application architecture. Only the declared processor endpoint may initiate to its own data endpoint. Other intra-tenant and cross-tenant communication remains denied unless explicitly added.

<!-- SOURCE-BLOCK NET:46 END -->

<!-- SOURCE-BLOCK NET:47 BEGIN -->


<a id="source-table-47"></a>

| Path ID / purpose | Forward path and initiating authority | Reply and mandatory denial |
| --- | --- | --- |
| PATH-01 · tenant-01 data service | processor-01 → D01O gateway → A01O → Z01 → A01R → D01R gateway → data-01. | Stateful return along the qualified reverse path; no unsolicited data-01→processor-01 initiation. |
| PATH-02 · tenant-02 data service | Equivalent D02O/A02O/Z02/A02R/D02R path with independently owned policy. | Same expected outcome; no permission inherited from Z01. |
| PATH-03 · cross-tenant | D01O/R towards D02O/R is not an approved relation. | Deny both initiations; no shared external segment, native route or generic transit bypass. |
| PATH-04 · shared resolver | Each entitled endpoint → its approved service boundary → resolver endpoint. | UDP/TCP replies tied to intended service; no access to resolver administration or other provider endpoints. |
| PATH-05 · management | Authorized privileged source → management-specific boundary → named platform or edge interface. | Return only to authorized management scope; no guest path into the same administrative endpoint. |
| PATH-06 · same-domain probe | Two disposable endpoints in one approved domain, same host and different hosts. | Only explicit test permit succeeds; endpoint controls enforce denial even without a gateway hop. |

<!-- SOURCE-BLOCK NET:47 END -->

<!-- SOURCE-BLOCK NET:48 BEGIN -->

<!-- SOURCE-BLOCK NET:48 END -->

<!-- SOURCE-BLOCK NET:49 BEGIN -->

For PATH-01, the source gateway owns P01O as its local domain network and reaches P01R through the isolated boundary handoff. The ZIP has the intended path back to both domains. The destination gateway has a path to P01O through the same authorized relationship. Record these as actual prefix/next-hop entries after implementation. A shared next hop is acceptable only within a demonstrated isolated routing context; the diagram alone does not establish it.

<!-- SOURCE-BLOCK NET:49 END -->

<!-- SOURCE-BLOCK NET:50 BEGIN -->

Review translation explicitly. The preferred unique-address internal pattern preserves source identity without NAT where supported. A translation alternative records original and translated address/port tuples and the authoritative owner of each mapping. It must not turn two different domain identities into an indistinguishable permission or create a hairpin shortcut. Policy-based routing also requires a defined unavailable-next-hop behaviour; falling back to an uninspected ordinary route is not acceptable.

<!-- SOURCE-BLOCK NET:50 END -->

<!-- SOURCE-BLOCK NET:51 BEGIN -->


<a id="source-table-51"></a>

| Condition | Required reference behaviour | Observation to collect |
| --- | --- | --- |
| Permit removed | New sessions denied; existing sessions terminated or drained within the approved service limit. | Policy commit, session state, subsequent probes and attributed logs. |
| Edge member lost | Remaining qualified path preserves inspection and declared session behaviour. | Forward and reverse hop/enforcement ownership, drops and convergence. |
| Management unavailable | No new uncontrolled policy; running enforcement follows proven native behaviour. | Current policy and service effect, not just manager reachability. |
| Route withdrawn | No alternate path outside the declared boundary appears. | Native and physical forwarding state and healthy negative-test controls. |

<!-- SOURCE-BLOCK NET:51 END -->

<!-- SOURCE-BLOCK NET:52 BEGIN -->

<!-- SOURCE-BLOCK NET:52 END -->

<!-- SOURCE-BLOCK NET:53 BEGIN -->

The path schedule is accepted only when native connected/distributed routes and observed traffic agree with the intended boundary. Use authorized test endpoints and a controlled outage scope. Denial tests must establish that the destination and the allowed control flow are healthy; a timeout alone does not prove isolation.

<!-- SOURCE-BLOCK NET:53 END -->

<!-- SOURCE-BLOCK NET:54 BEGIN -->

Related engineering: [Nutanix path realization](../platform-realizations/3-nutanix-component-path-and-lifecycle-realization.md#VND_s_003)  •  [VMware/NSX path realization](../platform-realizations/4-vmware-nsx-isolated-upstream-routing-and-enforcement.md#VND_s_004)  •  [OpenStack path realization](../platform-realizations/5-openstack-selected-services-backend-and-mandatory-policy.md#VND_s_005)

<!-- SOURCE-BLOCK NET:54 END -->

[Previous chapter](2-isolated-attachment-units-and-bounded-capacity.md) · [Chapter index](README.md) · [Next chapter](4-address-naming-and-protocol-family-decisions.md)

<!-- BEGIN GENERATED DECISION LINKS -->

## Related decision records

- [ADR-0007 — Allocate isolated domain attachments and qualify sharing](../../adr/0007-allocate-isolated-domain-attachments-and-qualify-sharing.md)

<!-- END GENERATED DECISION LINKS -->
