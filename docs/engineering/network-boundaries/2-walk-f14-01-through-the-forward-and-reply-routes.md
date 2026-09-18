# 2. Walk F14-01 through the forward and reply routes

[Documentation home](../../README.md) · [Source document](../../../reference/Portable_Hosting_Delivery_Kits_v1_1/02_Engineering/Network_and_Boundary_Detailed_Engineering.docx) · [Chapter index](README.md)

> **Source:** NBD — Delivery-kit v1.1 collection; original document version retained in the front matter. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: 7a86351d7f4be320e48d3112485bbab4b0f5b4a79cd0e420a823c793a708733a -->
<!-- SOURCE-BLOCK NBD:26 BEGIN -->

<a id="NBD_02"></a>

<!-- SOURCE-BLOCK NBD:26 END -->

<!-- SOURCE-BLOCK NBD:27 BEGIN -->

The example preserves the WD IPv4 route schedule. It is a reasoning fixture; no route in this table has been installed or tested.

<!-- SOURCE-BLOCK NBD:27 END -->

<!-- SOURCE-BLOCK NBD:28 BEGIN -->

Design basis and related records: [WD §5](../../solutions/internal-protected-workload/5-dedicated-handoff-inventory-and-route-ownership.md#WD14_S05)  •  [WD §6](../../solutions/internal-protected-workload/6-worked-forwarding-and-return-route-schedule.md#WD14_S06)  •  [RA §10](../../architecture/reference/10-addressing-name-services-and-end-to-end-traffic.md#RA_s_010)

<!-- SOURCE-BLOCK NBD:28 END -->

<!-- SOURCE-BLOCK NBD:29 BEGIN -->

F14-01 permits processor-01 in D01O to initiate the declared TCP/443 service at data-01 in D01R. D01O uses 192.0.2.0/27 and D01R uses 192.0.2.32/27. The route establishes reachability to a prefix; the identity/service policy narrows which endpoint and operation may use it.

<!-- SOURCE-BLOCK NBD:29 END -->

<!-- SOURCE-BLOCK NBD:30 BEGIN -->


<a id="source-table-30"></a>

| Route owner | Destination | Next hop / receiving role |
| --- | --- | --- |
| D01O | 192.0.2.32/27 | 198.51.100.1 — EC-01, via A01O |
| EC-01 | 192.0.2.32/27 | 198.51.100.6 — D01R gateway, via A01R |
| D01R, reply | 192.0.2.0/27 | 198.51.100.5 — EC-01, via A01R |
| EC-01, reply | 192.0.2.0/27 | 198.51.100.2 — D01O gateway, via A01O |

<!-- SOURCE-BLOCK NBD:30 END -->

<!-- SOURCE-BLOCK NBD:31 BEGIN -->

<!-- SOURCE-BLOCK NBD:31 END -->

<!-- SOURCE-BLOCK NBD:32 BEGIN -->

## What the LLD must prove

<!-- SOURCE-BLOCK NBD:32 END -->

<!-- SOURCE-BLOCK NBD:33 BEGIN -->

Map the native gateway’s connected and learned routes, its selected outgoing interface and the effective enforcement point. The edge observes the permitted new session and its stateful reply. A new session initiated from data-01 toward processor-01 remains denied unless independently approved. Returning through EC-02 or a shared upstream route is not an equivalent implementation.

<!-- SOURCE-BLOCK NBD:33 END -->

<!-- SOURCE-BLOCK NBD:34 BEGIN -->

Inspect alternatives at each forwarding component: an additional NIC, a common external subnet, native inter-domain route propagation, an imported summary, PBR or a failure next hop. Record why each is absent or constrained. A permitted connection appearing in edge logs is necessary evidence but does not by itself prove that no second path exists.

<!-- SOURCE-BLOCK NBD:34 END -->

<!-- SOURCE-BLOCK NBD:35 BEGIN -->

Repeat the same logical analysis against the inherited IPv6 schedule when dual-stack is offered. Preserve the address-family-specific neighbour and MTU behaviour instead of mechanically copying IPv4 syntax.

<!-- SOURCE-BLOCK NBD:35 END -->

<!-- SOURCE-BLOCK NBD:36 BEGIN -->

Continue with: [QCP §3](../../assurance/qualification-campaign/3-observe-network-paths-and-boundary-enforcement.md#QCP_03)  •  [PBS §5](../platform-build/5-vmware-nsx-bind-domain-workload-and-policy-lifecycles.md#PBS_05)

<!-- SOURCE-BLOCK NBD:36 END -->

<!-- SOURCE-BLOCK NBD:37 BEGIN -->

<!-- SOURCE-BLOCK NBD:37 END -->

[Previous chapter](1-count-and-assign-the-actual-isolation-units.md) · [Chapter index](README.md) · [Next chapter](3-make-service-replies-choose-the-originating-context.md)
