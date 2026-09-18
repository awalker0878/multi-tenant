# 10. Addressing, name services and end-to-end traffic

[Documentation home](../../README.md) · [Source document](../../../reference/Portable_Hosting_Delivery_Kits_v1_1/05_Reference_v1_4/00_Reference_Architecture_v1_4.docx) · [Chapter index](README.md)

> **Source:** RA — Draft v1.4. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: e50894d7f7b87cef50a283399b85925c8a96c5b9cd0428ce71ca0143d9be8d19 -->
<!-- SOURCE-BLOCK RA:166 BEGIN -->

<a id="__RefHeading___Toc3658_865363315"></a>
<a id="RA_s_010"></a>

<!-- SOURCE-BLOCK RA:166 END -->

<!-- SOURCE-BLOCK RA:167 BEGIN -->

The address plan has separate scopes for underlay links/loopbacks, management/OOB, platform transport, provider data services, edge attachments and tenant networks. Allocation follows routing authority, site and service requirements rather than an inherited /16-per-function pattern. Tenant prefixes are unique by default. Overlap is an explicit migration or service exception with translation and unambiguous ownership. VLANs, VNIs, RDs and RTs are provider implementation identifiers, not consumer inputs.

<!-- SOURCE-BLOCK RA:167 END -->

<!-- SOURCE-BLOCK RA:168 BEGIN -->

Authoritative IPAM reserves addresses before dependent network creation, confirms them after realization and releases them only after routes, leases, DNS and policy are reconciled. DNS forward/reverse records, delegation, resolver bindings and relevant TTLs are part of the same lifecycle. A platform’s native IPAM must either be authoritative for its delegated scope or reconcile to the enterprise authority; two independent writers must not allocate the same pool.

<!-- SOURCE-BLOCK RA:168 END -->

<!-- SOURCE-BLOCK RA:169 BEGIN -->

Each service class declares which of IPv4-only, IPv6-only and dual-stack it offers and qualifies; support for every mode is not assumed. The entire path must support its offered families: host, overlay, gateway, ZIP, service, monitoring and recovery. Even IPv4-only service needs a deliberate treatment of IPv6 link-local traffic and transition mechanisms. Required ICMPv6 and path-MTU behaviour must not be broken by a blanket deny copied from an IPv4 ruleset. \[[S23](34-appendix-d-sources-and-review-status.md#RA_src_S23); [S24](34-appendix-d-sources-and-review-status.md#RA_src_S24)\]

<!-- SOURCE-BLOCK RA:169 END -->

<!-- SOURCE-BLOCK RA:170 BEGIN -->

## Reference path catalogue

<!-- SOURCE-BLOCK RA:170 END -->

<!-- SOURCE-BLOCK RA:171 BEGIN -->


<a id="source-table-171"></a>

| Path | Forwarding and enforcement | Required observation |
| --- | --- | --- |
| Same domain, same host | Endpoint → host virtual switch and mandatory workload policy → endpoint | The control is enforced without a physical gateway hop |
| Same domain, different hosts | Endpoint policy → vendor overlay/underlay transport → destination policy | Tunnel path, MTU and destination identity remain correct |
| Different domains or zones | Source gateway → isolated attachment → ZIP → destination attachment/gateway | Permitted flow appears at the boundary; an alternate native route does not exist |
| Shared service consumption | Domain → approved service path/ZIP where needed → service endpoint | Only the entitled endpoint and resource scope are accessible |
| Public ingress | External boundary → PAZ ingress → separate approved internal flow | Internal VM is not directly public; return path and client attribution are defined |
| Privileged administration | Hardened admin path → management boundary → authorized interface | No dependence on a tenant transit route |
| Virtual disk I/O | Guest virtual device → hypervisor/storage stack → authorized backend | Storage attachment and backend isolation; not an assumed guest IP firewall hop |
| Guest file/object access | Guest NIC → approved network/service path → tenant data endpoint | Both network policy and data-service authorization |
| Backup | Snapshot/API/proxy or guest-agent path selected for the service | Data mover has only required scope; management credentials remain isolated |
| Live mobility / replication | Provider endpoints on controlled infrastructure transport | No guest bridging or cross-domain escape; eligibility survives relocation |

<!-- SOURCE-BLOCK RA:171 END -->

<!-- SOURCE-BLOCK RA:172 BEGIN -->

<!-- SOURCE-BLOCK RA:172 END -->

<!-- SOURCE-BLOCK RA:173 BEGIN -->

For each deployed path, the low-level design records source/destination identity, address family, routing owner, enforcement point, NAT if any, return path, service dependencies and fault behaviour. Positive tests establish endpoint health and allowed operation; negative tests show the intended control denies unauthorized traffic. A timeout from an unhealthy destination is not evidence of isolation.

<!-- SOURCE-BLOCK RA:173 END -->

<!-- SOURCE-BLOCK RA:174 BEGIN -->

Persistent infrastructure versus temporary migration — Hypervisor live-mobility and storage-replication networks may be persistent provider infrastructure. The time-bound migration rule applies to temporary cross-domain or cross-platform transfer access. It must not be interpreted as requiring vMotion, HCI replication or equivalent platform transport to be rebuilt for every operation.

<!-- SOURCE-BLOCK RA:174 END -->

<!-- SOURCE-BLOCK RA:175 BEGIN -->

Related engineering: [NET §3 — Worked inter-zone routing and enforcement schedule](../../engineering/fabric/3-worked-inter-zone-routing-and-enforcement-schedule.md#NET_s_003)  •  [NET §4 — Address, naming and protocol-family decisions](../../engineering/fabric/4-address-naming-and-protocol-family-decisions.md#NET_s_004)  •  [SVC §2 — Name, time, initialization and telemetry profiles](../shared-services/2-name-time-initialization-and-telemetry-profiles.md#SVC_s_002)

<!-- SOURCE-BLOCK RA:175 END -->

[Previous chapter](9-shared-services-ingress-and-controlled-egress.md) · [Chapter index](README.md) · [Next chapter](11-compute-pools-hypervisors-and-workload-placement.md)

<!-- BEGIN GENERATED DECISION LINKS -->

## Related decision records

- [ADR-0012 — Distinguish persistent platform transports from temporary migration access](../../adr/0012-distinguish-persistent-platform-transports-from-temporary-migration-access.md)
- [ADR-0020 — Use authoritative unique-by-default address allocation and controlled reuse](../../adr/0020-use-authoritative-unique-by-default-address-allocation-and-controlled-reuse.md)
- [ADR-0021 — Offer address families explicitly across the whole service path](../../adr/0021-offer-address-families-explicitly-across-the-whole-service-path.md)

<!-- END GENERATED DECISION LINKS -->
