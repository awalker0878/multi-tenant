# 4. Tenant, attachment and address schedule

[Documentation home](../../README.md) · [Source document](../../../reference/Portable_Hosting_Delivery_Kits_v1_1/05_Reference_v1_4/07_Worked_Infrastructure_Design_and_Acceptance_v1_4.docx) · [Chapter index](README.md)

> **Source:** WD — Draft v1.4. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: e4a2e42888349b5967f7b3174c78e53171728b13e99e4c78bc3cfb53310f68db -->
<a id="WD14_S04"></a>

IPv4 uses the TEST-NET ranges defined for documentation; IPv6 uses 2001:db8::/32. These are not allocations for a connected production or laboratory deployment. The .example naming convention likewise illustrates service identity rather than a registered operational domain. \[R14-01, R14-02, R14-03\]

Four independent tenant prefixes remain distinct from link prefixes, provider service addresses and management scope. No repeated zone label grants reachability. Gateway addresses below denote the logical native gateway role; exact realization may be distributed, virtual or appliance-based.

For IPv6, the same logical route and policy schedule applies using the selected family-specific prefixes and next hops. The illustrative /64 handoffs are not a prescription of platform link-prefix support. Native next-hop, RA, neighbour, MTU and service support must be confirmed before that family is offered.


<a id="source-table-57"></a>

| Domain / endpoint | Illustrative IPv4 | Illustrative IPv6 / ownership |
| --- | --- | --- |
| D01O / processor-01 | 192.0.2.0/27; gateway .1; endpoint .10 | 2001:db8:100:1::/64; gateway ::1; endpoint ::10; tenant-01 |
| D01R / data-01 | 192.0.2.32/27; gateway .33; endpoint .42 | 2001:db8:100:2::/64; gateway ::1; endpoint ::10; tenant-01 |
| D02O / processor-02 | 192.0.2.64/27; gateway .65; endpoint .74 | 2001:db8:100:3::/64; gateway ::1; endpoint ::10; tenant-02 |
| D02R / data-02 | 192.0.2.96/27; gateway .97; endpoint .106 | 2001:db8:100:4::/64; gateway ::1; endpoint ::10; tenant-02 |
| Provider service domain | 203.0.113.128/27; SE-01 .129; SE-02 .130 | 2001:db8:300:1::/64; SE-01 ::129; SE-02 ::130; provider-owned scope |
| Resolver / time / logs / repository | 203.0.113.138 / .139 / .140 / .141 | 2001:db8:300:1::138 / ::139 / ::140 / ::141 respectively; offered families remain separately qualified. |

Related documents: [NET — Address-family and allocation decisions](../../engineering/fabric/README.md#V14_NET_START)  \|  [PROV — Reservations and registration](../../implementation/provisioning-strategy/README.md#V14_PROV_START)

[Previous chapter](3-component-and-dependency-schedule.md) · [Chapter index](README.md) · [Next chapter](5-dedicated-handoff-inventory-and-route-ownership.md)
