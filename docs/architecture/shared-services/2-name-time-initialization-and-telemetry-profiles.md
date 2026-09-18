# 2. Name, time, initialization and telemetry profiles

[Documentation home](../../README.md) · [Source document](../../../reference/Portable_Hosting_Delivery_Kits_v1_1/05_Reference_v1_4/05_Shared_Services_Data_and_Recovery_v1_4.docx) · [Chapter index](README.md)

> **Source:** SVC — Draft v1.4. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: 2257e6f3badac48b07989244fbfae96643d68cc6633b28e9799a14733bccea3a -->
<a id="__RefHeading___Toc8877_1525915568"></a>
<a id="SVC_s_002"></a>

Parent architecture: [RA §9](../reference/9-shared-services-ingress-and-controlled-egress.md#RA_s_009)  •  [RA §10](../reference/10-addressing-name-services-and-end-to-end-traffic.md#RA_s_010)  •  [RA §23](../reference/23-tenant-domain-and-workload-provisioning-sequence.md#RA_s_023)  •  [RA §26](../reference/26-operating-model-capacity-and-observability.md#RA_s_026)

A service-connectivity schedule records endpoint identity, initiating party, protocol behaviour, address families, authentication, route/ZIP, replies, logs and revocation. The rows below are proposed reference profiles, not a blanket port list to apply to every workload. Names and time required for secure initialization should work before activation; that does not justify unrestricted access to provider infrastructure.


<a id="source-table-37"></a>

| Reference profile | Required functional path | Control and qualification |
| --- | --- | --- |
| Resolver consumption | Workload or infrastructure client → approved recursive resolver; DNS over UDP/53 and TCP/53 as applicable. | Permit intended resolver only; verify ordinary resolution, TCP and truncated-response fallback. |
| Authoritative DNS update | Authorized address/name owner → selected authoritative update interface. | Separate from recursion; restrict zones/records and authenticate the selected method. |
| Time synchronization | Approved client → selected trusted time service using its declared protocol; ordinary NTP commonly uses UDP/123. | Confirm required client/server behaviour, trust and offset alarms; not arbitrary time-server access. |
| Image/software retrieval | Eligible bootstrap or workload → approved repository endpoint. | Required protocol/TLS identity and artefact verification; deny arbitrary external download paths. |
| Log ingestion | Named infrastructure/workload sender → authenticated collector interface on the selected service port. | Bound tenant/source identity, protect transport, minimize payload and separate search/admin permissions. |
| Monitoring collection | Explicit push endpoint or authorized collector → named monitored target. | Required metrics only; no broad management reachability granted to tenant workloads. |

DNS needs more than a successful small UDP answer. RFC 7766 requires TCP support for general-purpose DNS implementations and describes failures caused by blocking it. Qualify TCP directly and the transition from a truncated UDP response; test the selected resolver path for each offered address family. Encrypted DNS alternatives are separate approved profiles rather than an ungoverned bypass. \[[S38](07-references-parent-basis-and-external-context.md#SVC_src_S38)\]

Separate recursive resolution, authoritative hosting, dynamic updates and transfer/replication duties. The address/name owner controls registration and deletion; workloads do not automatically gain zone-administration authority. The lifecycle records forward/reverse entries, delegation, TTLs, leases, source address history and reuse conditions. During migration, lower or change TTLs only through an accepted cutover plan and retain rollback/recovery identity information.

A loss of trusted time can affect event correlation and certificate operation even where network forwarding continues. Record both event time and collector receipt time, clock-source health and an approved tolerance. The numeric tolerance is a site/service decision, not invented here. Define buffer capacity, export delay, sequence/loss indication, retention and alarms for telemetry; central collection failure must be visible without creating a network permit path.


<a id="source-table-42"></a>

| Service failure | Existing operation | New changes / recovery |
| --- | --- | --- |
| Resolver unavailable | Existing sessions may continue according to their real dependencies; cached data is not a guaranteed service. | Pause changes requiring trustworthy name updates; use only the preapproved recovery resolver path. |
| Time source lost | Continue only within accepted measured offset and native behaviour. | Alert and evaluate certificate/evidence limits; restore approved time, not arbitrary external synchronization. |
| Collector unavailable | Preserve enforcement, buffer as supported and report loss/overflow. | Apply the accepted operating restriction; do not disable logging obligations silently. |
| Repository unavailable | Existing approved images remain governed by lifecycle policy. | Do not substitute unverified images or open unrestricted egress to finish a build. |

Related engineering: [Address-family and ownership decisions](../../engineering/fabric/4-address-naming-and-protocol-family-decisions.md#NET_s_004)  •  [Service parameter approval](../../assurance/site-qualification/4-service-parameter-and-requirement-decisions.md#QUAL_s_004)  •  [Activation services](../../implementation/provisioning-strategy/4-end-to-end-fixture-provisioning-and-safe-activation.md#PROV_s_004)

[Previous chapter](1-shared-service-placement-and-consumption-boundaries.md) · [Chapter index](README.md) · [Next chapter](3-identity-certificates-keys-and-independent-recovery.md)

<!-- BEGIN GENERATED DECISION LINKS -->

## Related decision records

- [ADR-0037 — Define independent telemetry and collection-loss behaviour](../../adr/0037-define-independent-telemetry-and-collection-loss-behaviour.md)

<!-- END GENERATED DECISION LINKS -->
