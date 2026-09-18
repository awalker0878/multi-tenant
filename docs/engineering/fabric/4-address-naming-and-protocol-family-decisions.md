# 4. Address, naming and protocol-family decisions

[Documentation home](../../README.md) · [Source document](../../../reference/Portable_Hosting_Delivery_Kits_v1_1/05_Reference_v1_4/02_Fabric_Security_and_Interfaces_v1_4.docx) · [Chapter index](README.md)

> **Source:** NET — Draft v1.4. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: 9c557d7d94dbdf24630994d2676aca3ddfa80e67c2910fb1a29ea4561c591dcf -->
<!-- SOURCE-BLOCK NET:55 BEGIN -->

<a id="__RefHeading___Toc5751_1525915568"></a>
<a id="NET_s_004"></a>

<!-- SOURCE-BLOCK NET:55 END -->

<!-- SOURCE-BLOCK NET:56 BEGIN -->

Parent architecture: [RA §9](../../architecture/reference/9-shared-services-ingress-and-controlled-egress.md#RA_s_009)  •  [RA §10](../../architecture/reference/10-addressing-name-services-and-end-to-end-traffic.md#RA_s_010)

<!-- SOURCE-BLOCK NET:56 END -->

<!-- SOURCE-BLOCK NET:57 BEGIN -->

The site design delegates non-overlapping address authorities for transport, management, provider services, attachments and workloads. A native platform allocator may own an explicitly delegated scope; it must not compete with enterprise IPAM over the same addresses. Prefix length follows workload growth, routing and operational constraints, not a universal allocation per tenant. Address ownership remains attributable after retirement.

<!-- SOURCE-BLOCK NET:57 END -->

<!-- SOURCE-BLOCK NET:58 BEGIN -->


<a id="source-table-58"></a>

| Offered mode | Required path evidence | Do not infer |
| --- | --- | --- |
| IPv4-only | Approved IPv4 transport/service paths plus defined IPv6 link-local and transition posture. | That no IPv6-capable endpoint exists merely because no global IPv6 prefix was allocated. |
| IPv6-only | IPv6 allocation, local control, routing, ZIP, DNS, monitoring and recovery work end to end. | A fictitious IPv4 prefix to satisfy an implementation form; silent dependence on an unavailable IPv4 service. |
| Dual-stack | Both families pass the same security outcomes; family-specific local controls are tested. | That an IPv4 firewall or backup success covers IPv6. |

<!-- SOURCE-BLOCK NET:58 END -->

<!-- SOURCE-BLOCK NET:59 BEGIN -->

<!-- SOURCE-BLOCK NET:59 END -->

<!-- SOURCE-BLOCK NET:60 BEGIN -->

Each service class declares which of these modes it actually offers. Unsupported combinations are excluded or require a separately qualified mediation service. A platform capability flag does not prove a complete service path. Necessary IPv6 neighbour, router-advertisement and ICMPv6 behaviour is addressed in the selected network profile; record source validation and allowed local control rather than disabling the protocol indiscriminately. \[[B2](07-references-parent-basis-and-external-context.md#NET_src_B2) §10\]

<!-- SOURCE-BLOCK NET:60 END -->

<!-- SOURCE-BLOCK NET:61 BEGIN -->

Name ownership is separate from address ownership. Specify authoritative zones, permitted updates, resolver endpoints, reverse registration, split-horizon behaviour and the cutover TTL. A rename or platform move should preserve logical service identity where required while retiring stale addresses safely. Allocate, register, observe, withdraw and quarantine are coordinated across IPAM, DNS, DHCP and edge policy.

<!-- SOURCE-BLOCK NET:61 END -->

<!-- SOURCE-BLOCK NET:62 BEGIN -->

Related engineering: [DNS including TCP fallback](../../architecture/shared-services/2-name-time-initialization-and-telemetry-profiles.md#SVC_s_002)  •  [Activation and name cutover](../../implementation/provisioning-strategy/4-end-to-end-fixture-provisioning-and-safe-activation.md#PROV_s_004)

<!-- SOURCE-BLOCK NET:62 END -->

[Previous chapter](3-worked-inter-zone-routing-and-enforcement-schedule.md) · [Chapter index](README.md) · [Next chapter](5-mtu-performance-and-failure-engineering.md)

<!-- BEGIN GENERATED DECISION LINKS -->

## Related decision records

- [ADR-0020 — Use authoritative unique-by-default address allocation and controlled reuse](../../adr/0020-use-authoritative-unique-by-default-address-allocation-and-controlled-reuse.md)
- [ADR-0021 — Offer address families explicitly across the whole service path](../../adr/0021-offer-address-families-explicitly-across-the-whole-service-path.md)

<!-- END GENERATED DECISION LINKS -->
