# 14. Availability, multi-site operation and recovery topology

[Documentation home](../../README.md) · [Source document](../../../reference/Portable_Hosting_Delivery_Kits_v1_1/05_Reference_v1_4/00_Reference_Architecture_v1_4.docx) · [Chapter index](README.md)

> **Source:** RA — Draft v1.4. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: e50894d7f7b87cef50a283399b85925c8a96c5b9cd0428ce71ca0143d9be8d19 -->
<!-- SOURCE-BLOCK RA:209 BEGIN -->

<a id="__RefHeading___Toc3666_865363315"></a>
<a id="RA_s_014"></a>

<!-- SOURCE-BLOCK RA:209 END -->

<!-- SOURCE-BLOCK RA:210 BEGIN -->

The reference uses site-local domain instances, local security enforcement and an explicit routed inter-site service. It does not stretch every tenant Layer 2 network between sites. A WSD can have instances in more than one site while retaining its security purpose and service identity. Different site labels are not evidence of independence when they share storage, power, control, identity or security-edge dependencies.

<!-- SOURCE-BLOCK RA:210 END -->

<!-- SOURCE-BLOCK RA:211 BEGIN -->


<a id="source-table-211"></a>

| Service pattern | Reference topology | Recovery consequence |
| --- | --- | --- |
| Single site, resilient | Redundant qualified hosts, storage and security paths inside the site | Survives the specified local failure, not an undeclared complete-site loss |
| Primary and recovery site | Independent target instance and preauthorized recovery/service paths | Restore or replicate, fence old writers, validate target and switch service exposure |
| Active across sites | Independent local instances with application/data coordination explicitly supplied by the service owner | Requires consistency, split-brain, latency and dependency analysis beyond VM restart |
| Layer-2 stretch variation | Only for a documented requirement with supported topology and failure controls | Partition, gateway ownership, failure blast radius and failback are separately qualified |

<!-- SOURCE-BLOCK RA:211 END -->

<!-- SOURCE-BLOCK RA:212 BEGIN -->

<!-- SOURCE-BLOCK RA:212 END -->

<!-- SOURCE-BLOCK RA:213 BEGIN -->

Availability classes define a measurable service indicator, observation period, maintenance treatment and tolerated failure. Recovery classes define the scope, recovery time objective (RTO), recovery point objective (RPO), data consistency and acceptance responsibility. Medium availability impact is not a numerical uptime target. The site implementation must populate and approve actual objectives; this revision does not invent measured values for an unspecified environment.

<!-- SOURCE-BLOCK RA:213 END -->

<!-- SOURCE-BLOCK RA:214 BEGIN -->

Security and recovery capacity are sized for surviving operation. Evaluate compute evacuation, storage rebuild, edge inspection/session load, routed inter-site capacity, IP pools, service dependencies and log ingestion together. A service cannot meet its failure promise by disabling inspection, moving to an ineligible host or sharing a key outside its approved scope. A useful admission rule is: accepted demand must not exceed measured surviving qualified capacity minus the operational reserve for the agreed failure model.

<!-- SOURCE-BLOCK RA:214 END -->

<!-- SOURCE-BLOCK RA:215 BEGIN -->

Control-plane failure and data-plane failure are assessed separately. Existing workloads can continue only where the selected stack demonstrably maintains forwarding, storage access and enforcement without its management component. New changes stop when required authority, IPAM, state or policy checks are unavailable. Logging loss triggers buffering, alerting and the profile’s operating restrictions; it never opens traffic by default.

<!-- SOURCE-BLOCK RA:215 END -->

<!-- SOURCE-BLOCK RA:216 BEGIN -->

Recovery re-establishes trusted administration and minimum identity/time/name services, then the fabric/platform/storage and security foundations, then workloads and service access. Exposure changes occur after current isolation and recovery checks pass. Fencing prevents the original and recovered copies becoming independent writers. Failback is a planned migration with its own consistency point, not an automatic reversal during an unresolved partition.

<!-- SOURCE-BLOCK RA:216 END -->

<!-- SOURCE-BLOCK RA:217 BEGIN -->

Related engineering: [SVC §6 — Failure, recovery, migration and failback topology](../shared-services/6-failure-recovery-migration-and-failback-topology.md#SVC_s_006)  •  [QUAL §4 — Service parameter and requirement decisions](../../assurance/site-qualification/4-service-parameter-and-requirement-decisions.md#QUAL_s_004)

<!-- SOURCE-BLOCK RA:217 END -->

<!-- SOURCE-BLOCK RA:218 BEGIN -->

PART 3  /  Vendor realization

<!-- SOURCE-BLOCK RA:218 END -->

[Previous chapter](13-identity-cryptography-and-service-trust.md) · [Chapter index](README.md) · [Next chapter](15-cross-vendor-realization-model.md)

<!-- BEGIN GENERATED DECISION LINKS -->

## Related decision records

- [ADR-0011 — Default to site-local domains and routed recovery](../../adr/0011-default-to-site-local-domains-and-routed-recovery.md)
- [ADR-0019 — Separate information impacts from service-level and recovery promises](../../adr/0019-separate-information-impacts-from-service-level-and-recovery-promises.md)

<!-- END GENERATED DECISION LINKS -->
