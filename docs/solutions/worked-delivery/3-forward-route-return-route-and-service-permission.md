# 3. Forward route, return route and service permission

[Documentation home](../../README.md) · [Source document](../../../reference/Portable_Hosting_Delivery_Kits_v1_1/04_Shared/Worked_Delivery_Example.docx) · [Chapter index](README.md)

> **Source:** WDE — Delivery-kit v1.1 collection; original document version retained in the front matter. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: ae4ea65ea564fe848f214f5154ca4b67726eb6628d07a4b4f7714210e49ccd0d -->
<a id="EX_03"></a>

The following path shows one tenant application service and a shared resolver. Forwarding and policy are distinct.

Baseline and related records: [WD §6](../internal-protected-workload/6-worked-forwarding-and-return-route-schedule.md#WD14_S06)  •  [WD §7](../internal-protected-workload/7-service-permissions-and-non-ip-storage-paths.md#WD14_S07)  •  [NET §3](../../engineering/fabric/3-worked-inter-zone-routing-and-enforcement-schedule.md#NET_s_003)


<a id="source-table-36"></a>

| Path segment | Illustrative next-hop decision | Separate policy obligation |
| --- | --- | --- |
| processor-01 → data-01 | NG-D01O sends 192.0.2.32/27 toward EC-01 at 198.51.100.1; EC-01 sends toward NG-D01R at .6. | F14-01 permits the selected TCP/443 service with endpoint TLS validation; other services deny. |
| data-01 → processor-01 reply | NG-D01R sends 192.0.2.0/27 toward EC-01 at .5; EC-01 sends toward NG-D01O at .2. | Stateful replies use the correct context. A new unsolicited reverse connection remains denied. |
| processor-01 → resolver | Approved resolver 203.0.113.138/32 goes from NG-D01O to EC-01, then SH-01 to SE-01. | Entitled sources may use UDP/53 and TCP/53. No broad provider-subnet permission. |
| Resolver → tenant-01 reply | The service endpoint sends tenant-01 prefixes through SE-01 .129; SE-01 returns through EC-01 .17. | Correct origin context and source identity; no tenant-02 transit through EC-01. |
| Management and other services | Not supplied by the application route; published service/admin interfaces remain separate. | No router administration, arbitrary KMS access, repository publication or provider-wide reachability. |

For actual implementation, observe connected routes and the effective forwarding table as well as declared static routes. Required route advertisements, HA next-hop ownership and service endpoint return routing belong in the LLD. A firewall downstream cannot inspect a path that has already bypassed it.

No packet has been sent by this worked example. These are intended paths and expected restrictions, not observed results.

[Previous chapter](2-resource-and-boundary-schedule.md) · [Chapter index](README.md) · [Next chapter](4-native-realization-and-provisioning-ownership.md)
