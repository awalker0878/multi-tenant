# 9. Shared services, ingress and controlled egress

[Documentation home](../../README.md) · [Source document](../../../reference/Portable_Hosting_Delivery_Kits_v1_1/05_Reference_v1_4/00_Reference_Architecture_v1_4.docx) · [Chapter index](README.md)

> **Source:** RA — Draft v1.4. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: e50894d7f7b87cef50a283399b85925c8a96c5b9cd0428ce71ca0143d9be8d19 -->
<!-- SOURCE-BLOCK RA:154 BEGIN -->

<a id="__RefHeading___Toc3656_865363315"></a>
<a id="RA_s_009"></a>

<!-- SOURCE-BLOCK RA:154 END -->

<!-- SOURCE-BLOCK RA:155 BEGIN -->

Shared services are provided through explicit consumption interfaces. The architecture distinguishes the service endpoint exposed to a tenant from the backing service infrastructure and its management. A service binding identifies which domain or workload may use which service, with the required direction, protocol, authentication and recovery expectation. It is a connectivity and entitlement decision, not necessarily a new software resource type.

<!-- SOURCE-BLOCK RA:155 END -->

<!-- SOURCE-BLOCK RA:156 BEGIN -->


<a id="source-table-156"></a>

| Service | Workload-facing path | Provider-only administration |
| --- | --- | --- |
| DNS and time | Approved resolver/time endpoints; necessary protocol behaviour only | Zones, delegation, clock sources and server configuration |
| Identity, certificates and keys | Entitled authentication, certificate enrolment or key-use endpoint | Directory administration, trust roots, key lifecycle and recovery custody |
| Logging and monitoring | Authenticated ingestion or tightly scoped collection | Collector configuration, search authorization, retention and evidence control |
| Backup and recovery | Approved agent, proxy or data-mover path appropriate to the platform | Policy, catalogue, repositories, immutability and disposal authority |
| Images and updates | Approved artifact repository or software distribution endpoint | Publishing, signing, provenance and retirement |
| File and object services | Tenant-authorized data endpoint with namespace and access controls | Storage controllers, replication policy, snapshots and cross-tenant sharing |

<!-- SOURCE-BLOCK RA:156 END -->

<!-- SOURCE-BLOCK RA:157 BEGIN -->

<!-- SOURCE-BLOCK RA:157 END -->

<!-- SOURCE-BLOCK RA:158 BEGIN -->

A service may expose endpoints aligned to several zones while sharing backend capacity. Those endpoints are not automatically independent failure domains. Record common storage, controllers, credentials and certificates. Network authorization is also not data authorization: two tenants able to contact a storage or key service must still be unable to enumerate or access each other’s resources.

<!-- SOURCE-BLOCK RA:158 END -->

<!-- SOURCE-BLOCK RA:159 BEGIN -->

## Public access

<!-- SOURCE-BLOCK RA:159 END -->

<!-- SOURCE-BLOCK RA:160 BEGIN -->

Public traffic terminates through an approved perimeter and PAZ ingress service such as a reverse proxy, load balancer or application firewall where required. A separately approved backend flow crosses the internal ZIP. Certificate identity, TLS termination or passthrough, backend re-encryption, health checks, denial-of-service handling and source attribution are explicit design choices. A public address on an internal VM is not the default realization.

<!-- SOURCE-BLOCK RA:160 END -->

<!-- SOURCE-BLOCK RA:161 BEGIN -->

## Egress and other external networks

<!-- SOURCE-BLOCK RA:161 END -->

<!-- SOURCE-BLOCK RA:162 BEGIN -->

Internet egress is absent until an approved egress service is attached. The design states whether it uses a proxy, routed security edge, translation or a qualified combination. NAT is an address transformation, not an access-control policy. Record both original and translated identities where needed for attribution. FQDN restrictions require a defined DNS resolution and refresh method; they cannot be inferred from a generic TCP allow rule.

<!-- SOURCE-BLOCK RA:162 END -->

<!-- SOURCE-BLOCK RA:163 BEGIN -->

Private circuits, enterprise networks and cloud interconnects terminate at named external-domain boundaries. Their presence does not grant broad access to all tenants or shared-service subnets. Partner sharing, inter-tenant sharing and migration are separately approved relationships. New exposure is activated only after baseline policy, route symmetry, certificates, monitoring and ownership have been verified; withdrawal includes established-session behaviour.

<!-- SOURCE-BLOCK RA:163 END -->

<!-- SOURCE-BLOCK RA:164 BEGIN -->

Publish the service protocol set, not just a service name. Ordinary resolver consumption requires the applicable UDP and TCP DNS behaviour, including fallback testing; authoritative updates, administrative operations and any encrypted-DNS variant remain separately scoped. RFC 7766 provides the TCP DNS basis. SVC §2 describes the corresponding endpoint and lifecycle decisions. \[[S38](34-appendix-d-sources-and-review-status.md#RA_src_S38)\]

<!-- SOURCE-BLOCK RA:164 END -->

<!-- SOURCE-BLOCK RA:165 BEGIN -->

Related engineering: [SVC §1 — Shared service placement and consumption boundaries](../shared-services/1-shared-service-placement-and-consumption-boundaries.md#SVC_s_001)  •  [SVC §2 — Name, time, initialization and telemetry profiles](../shared-services/2-name-time-initialization-and-telemetry-profiles.md#SVC_s_002)

<!-- SOURCE-BLOCK RA:165 END -->

[Previous chapter](8-zone-interfaces-routing-and-security-edge-topology.md) · [Chapter index](README.md) · [Next chapter](10-addressing-name-services-and-end-to-end-traffic.md)

<!-- BEGIN GENERATED DECISION LINKS -->

## Related decision records

- [ADR-0010 — Expose shared services through scoped consumption endpoints](../../adr/0010-expose-shared-services-through-scoped-consumption-endpoints.md)
- [ADR-0022 — Treat public access and egress as explicit service extensions](../../adr/0022-treat-public-access-and-egress-as-explicit-service-extensions.md)

<!-- END GENERATED DECISION LINKS -->
