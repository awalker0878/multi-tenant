# 3. Networks, addresses and native gateways

[Documentation home](../../README.md) · [Source document](../../../reference/Portable_Hosting_Delivery_Kits_v1_1/02_Engineering/LLD_and_Engineering_Review_Template.docx) · [Chapter index](README.md)

> **Source:** ET — Delivery-kit v1.1 collection; original document version retained in the front matter. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: b25a109f59a09baebb4dfc8c7f5069e9e98421ae5b009dba0e4b08117280511d -->
<!-- SOURCE-BLOCK ET:33 BEGIN -->

<a id="ET_03"></a>

<!-- SOURCE-BLOCK ET:33 END -->

<!-- SOURCE-BLOCK ET:34 BEGIN -->

Actual site values are required. Complete the response fields and identify controlled schedule/diagram references. Unknown or unsupported items remain blocking for their affected scope.

<!-- SOURCE-BLOCK ET:34 END -->

<!-- SOURCE-BLOCK ET:35 BEGIN -->

Baseline and related records: [NET §1](../../engineering/fabric/1-transport-routing-and-overlay-ownership.md#NET_s_001)  •  [NET §4](../../engineering/fabric/4-address-naming-and-protocol-family-decisions.md#NET_s_004)

<!-- SOURCE-BLOCK ET:35 END -->

<!-- SOURCE-BLOCK ET:36 BEGIN -->


<a id="source-table-36"></a>

| Record / decision | What to enter | Working response |
| --- | --- | --- |
| Network register | Owner, zone/domain/instance, native object and offered families. | {{ET\_NETWORKS}} |
| Actual allocations | Authoritative IPAM/delegation, prefixes, addresses, gateways and reservation IDs. | {{ET\_IPAM}} |
| Underlay policy | ASNs, neighbours, import/export, authentication/control limits and convergence. | {{ET\_UNDERLAY}} |
| Overlay/attachments | Tunnel transport, optional EVPN RD/RT/VNI ownership and isolated handoff capacity. | {{ET\_OVERLAY}} |
| Name/host protocols | DNS/DHCP ownership, TTL/lease, IPv6 local controls and required PMTU treatment. | {{ET\_PROTOCOLS}} |
| Release/reuse | Withdrawal, neighbour/session/DNS cleanup and quarantine before reuse. | {{ET\_REUSE}} |

<!-- SOURCE-BLOCK ET:36 END -->

<!-- SOURCE-BLOCK ET:37 BEGIN -->

<!-- SOURCE-BLOCK ET:37 END -->

<!-- SOURCE-BLOCK ET:38 BEGIN -->

Review disposition: Draft until the actual engineering authority accepts the named scope. A checked form or calculator result does not establish live support, qualification or authorization.

<!-- SOURCE-BLOCK ET:38 END -->

<!-- SOURCE-BLOCK ET:39 BEGIN -->

<!-- SOURCE-BLOCK ET:39 END -->

[Previous chapter](2-physical-inventory-facility-and-port-schedule.md) · [Chapter index](README.md) · [Next chapter](4-routes-zips-and-permitted-flows.md)
