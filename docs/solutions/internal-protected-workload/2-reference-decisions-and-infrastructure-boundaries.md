# 2. Reference decisions and infrastructure boundaries

[Documentation home](../../README.md) · [Source document](../../../reference/Portable_Hosting_Delivery_Kits_v1_1/05_Reference_v1_4/07_Worked_Infrastructure_Design_and_Acceptance_v1_4.docx) · [Chapter index](README.md)

> **Source:** WD — Draft v1.4. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: e4a2e42888349b5967f7b3174c78e53171728b13e99e4c78bc3cfb53310f68db -->
<a id="WD14_S02"></a>

The selected example uses unique tenant addresses, native isolated domain routing, a separately controlled stateful edge context for each tenant, and dedicated routed service handoffs. A tenant context can implement several pairwise ZIP relationships; neither a logical ZIP relationship nor an attachment is a physical appliance count.

The provider service domain contains service endpoints, not tenant gateways. Each tenant reaches that domain through its own service-edge context. This makes the point at which paths may share a service network explicit: after the provider security controls, never as an uninspected shared external subnet between native tenant gateways.

A centralized shared service is not automatically safe merely because the incoming routes are filtered. The design also controls service-side identity, return routing, source validation and the ability of a compromised endpoint to originate new traffic. Service hosts are not general-purpose transit routers. The shared service remains a disclosed compromise and availability dependency.

For the base OpenStack service, provider-owned roles retain network-policy and attachment mutation authority. Tenant self-service requests can use existing approved service and change tooling; a custom controller is not required. Direct delegated security-group, port-security, router or external-network editing is a separate optional service with its own effective-policy proof. Additive allow groups must not be described as a mandatory deny hierarchy. \[R14-05\]


<a id="source-table-41"></a>

| Decision | Selected reference treatment | Qualification or variation condition |
| --- | --- | --- |
| RD14-01 / boundary ownership | EC-01 and EC-02 have separate routing and policy authority; no unrestricted inter-context route import. | Actual virtual-system/VRF/context and stateful enforcement combination must be supported. |
| RD14-02 / shared services | Dedicated tenant-to-service handoffs; service-side return routes select the originating tenant context. | A shared attachment or proxy alternative needs its own path and identity analysis. |
| RD14-03 / mandatory policy | Provider retains mutation authority for baseline networks, policies and attachments. | Delegation requires tested limits that cannot expand the mandatory envelope. |
| RD14-04 / activation | Production G3 requires the applicable G4 readiness evidence and valid authority to operate. | Restricted, non-production qualification is a distinct authorized activity. |
| RD14-05 / resource ownership | Each native object and sensitive subresource has one authoritative writer and a defined handoff. | Shared objects are not recreated independently by each tenant workflow. |

Related documents: [RA — Selected design and variations](../../architecture/reference/README.md#V14_RA_START)  \|  [NET — Routing and attachment mechanics](../../engineering/fabric/README.md#V14_NET_START)  \|  [VND — Native implementation choices](../../engineering/platform-realizations/README.md#V14_VND_START)

[Previous chapter](1-purpose-status-and-reading-order.md) · [Chapter index](README.md) · [Next chapter](3-component-and-dependency-schedule.md)

<!-- BEGIN GENERATED DECISION LINKS -->

## Related decision records

- [ADR-0006 — Use an explicit governed ZIP for inter-domain trust transitions](../../adr/0006-use-an-explicit-governed-zip-for-inter-domain-trust-transitions.md)
- [ADR-0023 — Protect mandatory policy and identity selectors from tenant mutation](../../adr/0023-protect-mandatory-policy-and-identity-selectors-from-tenant-mutation.md)
- [ADR-0035 — Make shared-service replies select the originating security context](../../adr/0035-make-shared-service-replies-select-the-originating-security-context.md)

<!-- END GENERATED DECISION LINKS -->
