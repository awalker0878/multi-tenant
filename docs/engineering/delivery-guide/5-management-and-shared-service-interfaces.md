# 5. Management and shared-service interfaces

[Documentation home](../../README.md) · [Source document](../../../reference/Portable_Hosting_Delivery_Kits_v1_1/02_Engineering/Engineering_Kit.docx) · [Chapter index](README.md)

> **Source:** EK — Delivery-kit v1.1 collection; original document version retained in the front matter. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: 0aeb8ee0a114d3ed23e97c684cc9812a0fa6ea5252e49f0c902132bf4e053a7d -->
<!-- SOURCE-BLOCK EK:49 BEGIN -->

<a id="EK_05"></a>

<!-- SOURCE-BLOCK EK:49 END -->

<!-- SOURCE-BLOCK EK:50 BEGIN -->

Every shared service needs a consumption interface, an administrative interface, an authorization model and a recovery dependency. Record the actual client; it may be a host, service appliance, data mover or workload.

<!-- SOURCE-BLOCK EK:50 END -->

<!-- SOURCE-BLOCK EK:51 BEGIN -->

Baseline and related records: [SVC §1](../../architecture/shared-services/1-shared-service-placement-and-consumption-boundaries.md#SVC_s_001)  •  [SVC §2](../../architecture/shared-services/2-name-time-initialization-and-telemetry-profiles.md#SVC_s_002)  •  [SVC §3](../../architecture/shared-services/3-identity-certificates-keys-and-independent-recovery.md#SVC_s_003)  •  [ET §6](../../templates/lld/6-management-services-and-trust.md#ET_06)

<!-- SOURCE-BLOCK EK:51 END -->

<!-- SOURCE-BLOCK EK:52 BEGIN -->


<a id="source-table-52"></a>

| Service / plane | Design and ownership inputs |
| --- | --- |
| Management and OOB | Hardened privileged origin, boundary path, roles, targets, MFA/PAM requirements, logs, emergency recovery and supplier sessions. |
| IPAM/DNS/DHCP | Authoritative or delegated scope, reservation/release ownership, forward/reverse zones, resolver endpoints, leases/TTLs and reuse quarantine. |
| Time and logging | Approved time source, skew treatment; authenticated ingestion/collection, event identity, buffering, loss detection and retention/access. |
| Identity/PKI/KMS | Issuers/trust roots, service/client identities, role mapping, certificate renewal/revocation, key use/admin/recovery separation and cached/outage behaviour. |
| Backup and software supply | Capture API and transfer path; protected repository/catalogue; trusted images/packages and update source; publication versus retrieval authority. |
| Bootstrap transition | Temporary service location, permitted scope, owner/expiry, steady-state migration and independent recovery retained after cleanup. |

<!-- SOURCE-BLOCK EK:52 END -->

<!-- SOURCE-BLOCK EK:53 BEGIN -->

<!-- SOURCE-BLOCK EK:53 END -->

<!-- SOURCE-BLOCK EK:54 BEGIN -->

Define exact protocol configurations against the adopted security profile and applicable source editions. ITSP.40.062 is protocol-configuration guidance; use it with the selected algorithms and actual product modes rather than assuming an encryption checkbox proves a safe channel. \[K10\]

<!-- SOURCE-BLOCK EK:54 END -->

<!-- SOURCE-BLOCK EK:55 BEGIN -->

External mechanism context: [K10 — Guidance on securely configuring network protocols (ITSP.40.062)](https://www.cyber.gc.ca/en/guidance/guidance-securely-configuring-network-protocols-itsp40062)

<!-- SOURCE-BLOCK EK:55 END -->

<!-- SOURCE-BLOCK EK:56 BEGIN -->

A service handoff must include failure behaviour and operational ownership. “Another team will configure it later” is not an accepted dependency.

<!-- SOURCE-BLOCK EK:56 END -->

<!-- SOURCE-BLOCK EK:57 BEGIN -->

<!-- SOURCE-BLOCK EK:57 END -->

[Previous chapter](4-compute-storage-and-protected-data.md) · [Chapter index](README.md) · [Next chapter](6-capacity-mtu-performance-and-failure-analysis.md)
