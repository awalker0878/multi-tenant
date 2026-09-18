# 1. Shared service placement and consumption boundaries

[Documentation home](../../README.md) · [Source document](../../../reference/Portable_Hosting_Delivery_Kits_v1_1/05_Reference_v1_4/05_Shared_Services_Data_and_Recovery_v1_4.docx) · [Chapter index](README.md)

> **Source:** SVC — Draft v1.4. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: 2257e6f3badac48b07989244fbfae96643d68cc6633b28e9799a14733bccea3a -->
<!-- SOURCE-BLOCK SVC:23 BEGIN -->

<a id="__RefHeading___Toc8875_1525915568"></a>
<a id="SVC_s_001"></a>

<!-- SOURCE-BLOCK SVC:23 END -->

<!-- SOURCE-BLOCK SVC:24 BEGIN -->

WD §§3–7 selects a worked service-facing design: dedicated tenant-to-service handoffs, separately controlled service-edge contexts, named endpoints and origin-specific return routes. This is a proposed realization requiring actual supported service routing and authority. A shared endpoint remains a shared compromise dependency; network restrictions do not replace tenant resource entitlement or content/provenance controls.

<!-- SOURCE-BLOCK SVC:24 END -->

<!-- SOURCE-BLOCK SVC:25 BEGIN -->

Parent architecture: [RA §6](../reference/6-management-platform-control-and-out-of-band-access.md#RA_s_006)  •  [RA §9](../reference/9-shared-services-ingress-and-controlled-egress.md#RA_s_009)  •  [RA §12](../reference/12-storage-backup-and-data-isolation-architecture.md#RA_s_012)  •  [RA §13](../reference/13-identity-cryptography-and-service-trust.md#RA_s_013)  •  [RA §22](../reference/22-vendor-platform-and-shared-service-commissioning.md#RA_s_022)

<!-- SOURCE-BLOCK SVC:25 END -->

<!-- SOURCE-BLOCK SVC:26 BEGIN -->

A shared service has at least three architectural surfaces: the tenant-facing consumption endpoint, the backing service/data infrastructure, and the privileged administration path. They may reside on one supported appliance or several components, but their authority remains distinct. A permitted route to a service does not grant access to all data behind it or to its administrative functions. \[[B2](07-references-parent-basis-and-external-context.md#SVC_src_B2) §§6, 9, 12–13\]

<!-- SOURCE-BLOCK SVC:26 END -->

<!-- SOURCE-BLOCK SVC:27 BEGIN -->


<a id="source-table-27"></a>

| Service | Consumption and entitlement | Administration / common dependencies |
| --- | --- | --- |
| Names and time | Approved resolver/time endpoints; requester and zone eligibility identified. | Zone/delegation or time-source configuration; hosting, network and upstream service dependencies. |
| Identity and certificates | Scoped authentication/enrolment with approved issuer and relying-party trust. | Directory/CA roots, role policy and revocation; recovery identity and trusted time. |
| Keys | Authorized key use for selected resource/tenant scope. | Key creation, rotation, recovery and destruction; module, custody and availability dependencies. |
| Logging and monitoring | Authenticated event ingestion or explicit read/collection scope. | Collector/search/retention configuration; storage, identity, time and ingestion capacity. |
| Backup/protection | Qualified capture/data-transfer/restore interface. | Catalogue, policy, repositories and disposal; key and consistency dependencies. |
| Images and updates | Approved signed/digested artefacts available to entitled systems. | Build, publication, signing and retirement; staging and offline supply where required. |
| File/object data | Tenant-scoped namespace, protocol authorization and correct network boundary. | Backend/controller, copy, replication and sharing policy; keys and storage fault domains. |

<!-- SOURCE-BLOCK SVC:27 END -->

<!-- SOURCE-BLOCK SVC:28 BEGIN -->

<!-- SOURCE-BLOCK SVC:28 END -->

<!-- SOURCE-BLOCK SVC:29 BEGIN -->

Zone-aligned service endpoints can reduce unnecessary trust transitions, but an additional endpoint is not an independent service replica. Record its shared backend, identity issuer, keys, certificate chain, control plane, power and storage. When a dependency fails, evaluate all endpoints and tenants relying on it rather than only the failed virtual IP.

<!-- SOURCE-BLOCK SVC:29 END -->

<!-- SOURCE-BLOCK SVC:30 BEGIN -->

The reference default places administration in protected management domains and exposes only the explicitly entitled data/service endpoints. Cross-zone consumption follows the applicable ZIP relationship. If a service initiates a connection toward a workload, such as a collector or backup process, that initiation is separately authorized and scoped; do not disguise it as unrestricted reverse reachability.

<!-- SOURCE-BLOCK SVC:30 END -->

<!-- SOURCE-BLOCK SVC:31 BEGIN -->


<a id="source-table-31"></a>

| Placement decision | Selected reference rule | Site-specific record |
| --- | --- | --- |
| Local versus remote | Use a service endpoint whose latency, resilience and location meet the offered class. | Actual endpoint/backend sites and outage dependencies. |
| Shared versus dedicated | Share only where tenant authorization and accepted fault/privilege boundaries are preserved. | Dedicated dimensions and residual shared administrators/controllers. |
| Consumption versus management | Never publish administrative entitlement as a side effect of consuming data. | Interface, certificate, API permission and route schedule. |
| Version/lifecycle | Consumers use an accepted service version and supported transition path. | Dependent WSD list, replacement/cutover plan and withdrawal condition. |

<!-- SOURCE-BLOCK SVC:31 END -->

<!-- SOURCE-BLOCK SVC:32 BEGIN -->

<!-- SOURCE-BLOCK SVC:32 END -->

<!-- SOURCE-BLOCK SVC:33 BEGIN -->

Related engineering: [Administrative interface schedule](../../engineering/fabric/6-management-paths-and-interface-handover.md#NET_s_006)  •  [P3 service handoffs](../../implementation/provisioning-strategy/1-provisioning-scopes-ownership-and-accepted-handoffs.md#PROV_s_001)

<!-- SOURCE-BLOCK SVC:33 END -->

[Chapter index](README.md) · [Next chapter](2-name-time-initialization-and-telemetry-profiles.md)

<!-- BEGIN GENERATED DECISION LINKS -->

## Related decision records

- [ADR-0010 — Expose shared services through scoped consumption endpoints](../../adr/0010-expose-shared-services-through-scoped-consumption-endpoints.md)

<!-- END GENERATED DECISION LINKS -->
