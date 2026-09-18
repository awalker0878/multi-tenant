# 4. Routes, ZIPs and permitted flows

[Documentation home](../../README.md) · [Source document](../../../reference/Portable_Hosting_Delivery_Kits_v1_1/02_Engineering/LLD_and_Engineering_Review_Template.docx) · [Chapter index](README.md)

> **Source:** ET — Delivery-kit v1.1 collection; original document version retained in the front matter. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: b25a109f59a09baebb4dfc8c7f5069e9e98421ae5b009dba0e4b08117280511d -->
<!-- SOURCE-BLOCK ET:40 BEGIN -->

<a id="ET_04"></a>

<!-- SOURCE-BLOCK ET:40 END -->

<!-- SOURCE-BLOCK ET:41 BEGIN -->

Actual site values are required. Complete the response fields and identify controlled schedule/diagram references. Unknown or unsupported items remain blocking for their affected scope.

<!-- SOURCE-BLOCK ET:41 END -->

<!-- SOURCE-BLOCK ET:42 BEGIN -->

Baseline and related records: [NET §3](../../engineering/fabric/3-worked-inter-zone-routing-and-enforcement-schedule.md#NET_s_003)  •  [WD §6](../../solutions/internal-protected-workload/6-worked-forwarding-and-return-route-schedule.md#WD14_S06)

<!-- SOURCE-BLOCK ET:42 END -->

<!-- SOURCE-BLOCK ET:43 BEGIN -->


<a id="source-table-43"></a>

| Record / decision | What to enter | Working response |
| --- | --- | --- |
| Boundary mapping | Logical ZIP endpoints/authorities to actual routing/enforcement components. | {{ET\_ZIP}} |
| Forward/reply routes | Per-owner route/interface/next hop and return owner for each approved destination. | {{ET\_ROUTES}} |
| Flow schedule | Source initiator, target, service/protocol, auth/TLS, stateful reply and logs. | {{ET\_FLOWS}} |
| Bypass and precedence | Connected/native/distributed paths, imported routes, NAT/PBR, additive policies and extra NICs. | {{ET\_BYPASS}} |
| Revocation/failure | Session termination/drain rule, enforcement failover and denied alternatives. | {{ET\_REVOKE}} |
| Path evidence plan | Observation method and CT/W14 assertion for each required path. | {{ET\_PATH\_TEST}} |

<!-- SOURCE-BLOCK ET:43 END -->

<!-- SOURCE-BLOCK ET:44 BEGIN -->

<!-- SOURCE-BLOCK ET:44 END -->

<!-- SOURCE-BLOCK ET:45 BEGIN -->

Review disposition: Draft until the actual engineering authority accepts the named scope. A checked form or calculator result does not establish live support, qualification or authorization.

<!-- SOURCE-BLOCK ET:45 END -->

<!-- SOURCE-BLOCK ET:46 BEGIN -->

<!-- SOURCE-BLOCK ET:46 END -->

[Previous chapter](3-networks-addresses-and-native-gateways.md) · [Chapter index](README.md) · [Next chapter](5-compute-storage-and-placement.md)
