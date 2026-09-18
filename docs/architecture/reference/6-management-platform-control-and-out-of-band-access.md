# 6. Management, platform control and out-of-band access

[Documentation home](../../README.md) · [Source document](../../../reference/Portable_Hosting_Delivery_Kits_v1_1/05_Reference_v1_4/00_Reference_Architecture_v1_4.docx) · [Chapter index](README.md)

> **Source:** RA — Draft v1.4. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: e50894d7f7b87cef50a283399b85925c8a96c5b9cd0428ce71ca0143d9be8d19 -->
<!-- SOURCE-BLOCK RA:117 BEGIN -->

<a id="__RefHeading___Toc3650_865363315"></a>
<a id="RA_s_006"></a>

<!-- SOURCE-BLOCK RA:117 END -->

<!-- SOURCE-BLOCK RA:118 BEGIN -->

Management is a separate infrastructure environment. It contains privileged access services, platform managers, fabric and security administration, storage administration and the management interfaces of shared services. Tenant guest administration is a different authority and follows its own approved access path. A tenant role that can restart a VM must not thereby acquire control over the host, virtual fabric, storage backend or security edge.

<!-- SOURCE-BLOCK RA:118 END -->

<!-- SOURCE-BLOCK RA:119 BEGIN -->

The Management Zone describes the trust and access policy. OOB describes a transport and recovery property. The reference uses dedicated OOB interfaces and switching where supported; platform control APIs that use ordinary Ethernet remain in separately protected management networks. Their independence must be described honestly when they share production links, power or hosting resources. The cloud-zoning guidance supports an isolated management approach. \[[S02](34-appendix-d-sources-and-review-status.md#RA_src_S02)\]

<!-- SOURCE-BLOCK RA:119 END -->

<!-- SOURCE-BLOCK RA:120 BEGIN -->


<a id="source-table-120"></a>

| Administrative path | Termination and authority | Separation rule |
| --- | --- | --- |
| Infrastructure operator | Hardened admin endpoint → privileged-access boundary → authorized management service | Scoped identity; no direct route from ordinary workload networks |
| Automation execution | Authority-specific runner → allowlisted platform or infrastructure API | No shared privileged identity spanning fabric, edge and tenant resources |
| Hardware recovery | Controlled emergency access → OOB network → BMC/switch console | Survives the specified production failure; separately authenticated and logged |
| Tenant guest operator | Approved guest-access service → assigned guest endpoints | No reuse of host-management credentials or implicit access to infrastructure APIs |
| Supplier support | Time-limited approved session → named target | Recorded scope; no standing unrestricted access or uncontrolled diagnostic export |

<!-- SOURCE-BLOCK RA:120 END -->

<!-- SOURCE-BLOCK RA:121 BEGIN -->

<!-- SOURCE-BLOCK RA:121 END -->

<!-- SOURCE-BLOCK RA:122 BEGIN -->

The management environment is an umbrella for isolated management domains, not one universally routed MZ. Management authority follows the zones and resources being administered; shared tooling does not create direct MZ-to-MZ connectivity. The on-premises virtualization guidance also recommends separate zone-management and virtualization-storage environments and physical separation of privileged transports. Any consolidated HCI/control/transport realization therefore needs an explicit applicability and tailoring decision; this architecture does not assert that logical isolation automatically satisfies those physical recommendations. \[[S03](34-appendix-d-sources-and-review-status.md#RA_src_S03)\]

<!-- SOURCE-BLOCK RA:122 END -->

<!-- SOURCE-BLOCK RA:123 BEGIN -->

Platform managers are not in the normal workload packet path, but their unavailability can still affect scheduling, policy updates, restart and recovery. Host and controller failure behaviour is therefore qualified for the selected release rather than inferred from the diagram. Management compute and the minimum bootstrap services must remain recoverable without first restoring every tenant workload.

<!-- SOURCE-BLOCK RA:123 END -->

<!-- SOURCE-BLOCK RA:124 BEGIN -->

The provider service area is not one large management network. DNS queries, log ingestion, backup data transfer and key-use requests terminate on consumption interfaces. Directory administration, collector configuration, backup deletion and key destruction terminate on management interfaces. Where a product combines them on one appliance, separate access paths and authorization remain required. Shared hardware must not erase the trust boundary.

<!-- SOURCE-BLOCK RA:124 END -->

<!-- SOURCE-BLOCK RA:125 BEGIN -->

Break-glass access is a controlled exception to the normal identity path, not an exception to accountability. Recovery procedures identify who may activate it, what endpoints it can reach, how activity is retained when central services are unavailable, and how credentials and sessions are revoked afterwards. Test that access against the failure it is intended to repair.

<!-- SOURCE-BLOCK RA:125 END -->

<!-- SOURCE-BLOCK RA:126 BEGIN -->

Related engineering: [NET §6 — Management paths and interface handover](../../engineering/fabric/6-management-paths-and-interface-handover.md#NET_s_006)  •  [SVC §3 — Identity, certificates, keys and independent recovery](../shared-services/3-identity-certificates-keys-and-independent-recovery.md#SVC_s_003)

<!-- SOURCE-BLOCK RA:126 END -->

<!-- SOURCE-BLOCK RA:127 BEGIN -->

PART 2  /  Logical hosting and security

<!-- SOURCE-BLOCK RA:127 END -->

[Previous chapter](5-physical-fabric-and-platform-attachment.md) · [Chapter index](README.md) · [Next chapter](7-tenant-environments-and-security-domain-placement.md)

<!-- BEGIN GENERATED DECISION LINKS -->

## Related decision records

- [ADR-0009 — Separate management security, platform control and OOB recovery](../../adr/0009-separate-management-security-platform-control-and-oob-recovery.md)

<!-- END GENERATED DECISION LINKS -->
