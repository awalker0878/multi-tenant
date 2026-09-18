# 6. Worked forwarding and return-route schedule

[Documentation home](../../README.md) · [Source document](../../../reference/Portable_Hosting_Delivery_Kits_v1_1/05_Reference_v1_4/07_Worked_Infrastructure_Design_and_Acceptance_v1_4.docx) · [Chapter index](README.md)

> **Source:** WD — Draft v1.4. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: e4a2e42888349b5967f7b3174c78e53171728b13e99e4c78bc3cfb53310f68db -->
<!-- SOURCE-BLOCK WD:70 BEGIN -->

<a id="WD14_S06"></a>

<!-- SOURCE-BLOCK WD:70 END -->

<!-- SOURCE-BLOCK WD:71 BEGIN -->

Each destination service /32 means a specifically approved endpoint, not the whole provider subnet. The table states intended routing; stateful policy separately constrains sources, destinations, protocols and initiation. Neither a route nor a successful ping constitutes permission.

<!-- SOURCE-BLOCK WD:71 END -->

<!-- SOURCE-BLOCK WD:72 BEGIN -->

For processor-01 to data-01, the forward route is NG-D01O to EC-01 via .1, then EC-01 to NG-D01R via .6. The reply travels NG-D01R to EC-01 via .5, then EC-01 to NG-D01O via .2. The stateful enforcement point is EC-01 for Z01. A new unsolicited reverse connection remains denied.

<!-- SOURCE-BLOCK WD:72 END -->

<!-- SOURCE-BLOCK WD:73 BEGIN -->

For processor-01 to the resolver, the path is NG-D01O, EC-01, SH-01, SE-01 and the named resolver. The resolver must return tenant-01 prefixes through SE-01, not whichever service-edge default is convenient. The service hosts require the supported return-routing or equivalent service-mediation design. Missing return control disqualifies this realization.

<!-- SOURCE-BLOCK WD:73 END -->

<!-- SOURCE-BLOCK WD:74 BEGIN -->

The shared service segment is behind the security boundaries. EC and SE policies deny tenant access to service-router administrative addresses, all unlisted provider destinations and other tenant prefixes. Service endpoints do not forward arbitrary traffic and cannot initiate general connections back to tenants. This limits network transit, but does not remove the risk of a compromised shared service misusing the legitimate sessions or data entitlements it has; those residual risks belong in the service threat analysis.

<!-- SOURCE-BLOCK WD:74 END -->

<!-- SOURCE-BLOCK WD:75 BEGIN -->


<a id="source-table-75"></a>

| Routing owner | Permitted nonlocal destination | Next hop / required exclusion |
| --- | --- | --- |
| NG-D01O | 192.0.2.32/27; approved service /32s | 198.51.100.1; no P02O/P02R route. |
| NG-D01R | 192.0.2.0/27; approved service /32s | 198.51.100.5; no P02O/P02R route. |
| NG-D02O | 192.0.2.96/27; approved service /32s | 198.51.100.9; no P01O/P01R route. |
| NG-D02R | 192.0.2.64/27; approved service /32s | 198.51.100.13; no P01O/P01R route. |
| EC-01 | 192.0.2.0/27; 192.0.2.32/27 | Respectively .2 and .6 on its handoffs; no tenant-02 route import. |
| EC-01 | Approved 203.0.113.138–141 /32s only | 198.51.100.18; policy permits only selected services and entitled sources. |
| EC-02 | 192.0.2.64/27; 192.0.2.96/27 | Respectively .10 and .14; no tenant-01 route import. |
| EC-02 | Approved service /32s only | 198.51.100.22; independently approved service policy. |
| SE-01 | Tenant-01 exact /27 prefixes | 198.51.100.17; no routes to tenant-02 through this context. |
| SE-02 | Tenant-02 exact /27 prefixes | 198.51.100.21; no routes to tenant-01 through this context. |
| Service endpoint return routes | Tenant-01 /27s; tenant-02 /27s | 203.0.113.129 and .130 respectively; validate supported host/service routing. |

<!-- SOURCE-BLOCK WD:75 END -->

<!-- SOURCE-BLOCK WD:76 BEGIN -->

<!-- SOURCE-BLOCK WD:76 END -->

<!-- SOURCE-BLOCK WD:77 BEGIN -->

Related documents: [NET — Forward/reply and session semantics](../../engineering/fabric/README.md#V14_NET_START)  \|  [SVC — Shared-service authorizations](../../architecture/shared-services/README.md#V14_SVC_START)

<!-- SOURCE-BLOCK WD:77 END -->

<!-- SOURCE-BLOCK WD:78 BEGIN -->

<!-- SOURCE-BLOCK WD:78 END -->

[Previous chapter](5-dedicated-handoff-inventory-and-route-ownership.md) · [Chapter index](README.md) · [Next chapter](7-service-permissions-and-non-ip-storage-paths.md)

<!-- BEGIN GENERATED DECISION LINKS -->

## Related decision records

- [ADR-0035 — Make shared-service replies select the originating security context](../../adr/0035-make-shared-service-replies-select-the-originating-security-context.md)

<!-- END GENERATED DECISION LINKS -->
