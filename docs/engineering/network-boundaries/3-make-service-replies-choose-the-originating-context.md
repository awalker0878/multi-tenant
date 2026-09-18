# 3. Make service replies choose the originating context

[Documentation home](../../README.md) · [Source document](../../../reference/Portable_Hosting_Delivery_Kits_v1_1/02_Engineering/Network_and_Boundary_Detailed_Engineering.docx) · [Chapter index](README.md)

> **Source:** NBD — Delivery-kit v1.1 collection; original document version retained in the front matter. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: 7a86351d7f4be320e48d3112485bbab4b0f5b4a79cd0e420a823c793a708733a -->
<!-- SOURCE-BLOCK NBD:38 BEGIN -->

<a id="NBD_03"></a>

<!-- SOURCE-BLOCK NBD:38 END -->

<!-- SOURCE-BLOCK NBD:39 BEGIN -->

The shared-service endpoint needs an explicit return-path decision as well as a permitted incoming connection.

<!-- SOURCE-BLOCK NBD:39 END -->

<!-- SOURCE-BLOCK NBD:40 BEGIN -->

Design basis and related records: [WD §7](../../solutions/internal-protected-workload/7-service-permissions-and-non-ip-storage-paths.md#WD14_S07)  •  [SVC §2](../../architecture/shared-services/2-name-time-initialization-and-telemetry-profiles.md#SVC_s_002)  •  [NET §4](../fabric/4-address-naming-and-protocol-family-decisions.md#NET_s_004)

<!-- SOURCE-BLOCK NBD:40 END -->

<!-- SOURCE-BLOCK NBD:41 BEGIN -->

For a DNS query from D01O, the fixture routes the resolver host address 203.0.113.138/32 through EC-01 to SE-01. EC-01’s next hop is 198.51.100.18 over SH-01. SE-01 reaches the named service on its service-facing network. The reply must select the tenant-01 return path; a default through the other tenant context is not acceptable.

<!-- SOURCE-BLOCK NBD:41 END -->

<!-- SOURCE-BLOCK NBD:42 BEGIN -->


<a id="source-table-42"></a>

| Reply stage | Required WD decision | What remains denied |
| --- | --- | --- |
| Resolver to tenant-01 source | Return 192.0.2.0/27 or 192.0.2.32/27 through SE-01 at 203.0.113.129, using the qualified service-side method. | A broad default or host forwarding that bridges tenant contexts. |
| SE-01 to EC-01 | Own tenant prefixes via 198.51.100.17. | Routes to tenant-02 and general service-subnet access. |
| EC-01 to source domain | 192.0.2.0/27 via .2; 192.0.2.32/27 via .6 on the corresponding 198.51.100.x handoff. | Unsolicited service initiation except where separately approved. |

<!-- SOURCE-BLOCK NBD:42 END -->

<!-- SOURCE-BLOCK NBD:43 BEGIN -->

<!-- SOURCE-BLOCK NBD:43 END -->

<!-- SOURCE-BLOCK NBD:44 BEGIN -->

Implement the service-side decision with a supported routing or mediation design. Record route ownership, endpoint source validation, authentication, backend tenant entitlement and whether the service terminates and originates separate sessions. A proxy alternative changes client attribution and session semantics and therefore needs an explicit design, not silent substitution.

<!-- SOURCE-BLOCK NBD:44 END -->

<!-- SOURCE-BLOCK NBD:45 BEGIN -->

DNS qualification includes UDP and TCP to the approved resolver and a controlled response that exercises TCP fallback. RFC 7766 requires TCP support for general-purpose DNS implementations; one successful small UDP lookup is not full protocol evidence. Encrypted DNS variants remain separately selected profiles. \[D05\]

<!-- SOURCE-BLOCK NBD:45 END -->

<!-- SOURCE-BLOCK NBD:46 BEGIN -->

Verified mechanism source: [D05 — RFC 7766: DNS Transport over TCP](https://datatracker.ietf.org/doc/html/rfc7766)

<!-- SOURCE-BLOCK NBD:46 END -->

<!-- SOURCE-BLOCK NBD:47 BEGIN -->

Continue with: [QCP §4](../../assurance/qualification-campaign/4-observe-identity-storage-and-protocol-completeness.md#QCP_04)  •  [PBS §8](../platform-build/8-publish-shared-service-handoffs-without-sharing-authority.md#PBS_08)

<!-- SOURCE-BLOCK NBD:47 END -->

<!-- SOURCE-BLOCK NBD:48 BEGIN -->

<!-- SOURCE-BLOCK NBD:48 END -->

[Previous chapter](2-walk-f14-01-through-the-forward-and-reply-routes.md) · [Chapter index](README.md) · [Next chapter](4-budget-address-families-and-encapsulation-precisely.md)

<!-- BEGIN GENERATED DECISION LINKS -->

## Related decision records

- [ADR-0035 — Make shared-service replies select the originating security context](../../adr/0035-make-shared-service-replies-select-the-originating-security-context.md)

<!-- END GENERATED DECISION LINKS -->
