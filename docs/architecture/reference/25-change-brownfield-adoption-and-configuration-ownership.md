# 25. Change, brownfield adoption and configuration ownership

[Documentation home](../../README.md) · [Source document](../../../reference/Portable_Hosting_Delivery_Kits_v1_1/05_Reference_v1_4/00_Reference_Architecture_v1_4.docx) · [Chapter index](README.md)

> **Source:** RA — Draft v1.4. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: e50894d7f7b87cef50a283399b85925c8a96c5b9cd0428ce71ca0143d9be8d19 -->
<!-- SOURCE-BLOCK RA:352 BEGIN -->

<a id="__RefHeading___Toc3688_865363315"></a>
<a id="RA_s_025"></a>

<!-- SOURCE-BLOCK RA:352 END -->

<!-- SOURCE-BLOCK RA:353 BEGIN -->

Infrastructure changes are classified by their effect on service, isolation and shared failure domains. Ordinary workload scaling within a qualified envelope is different from changing a fabric, storage backend, edge routing, management path or isolation policy. A file in a tenant repository cannot downgrade a foundation-level change simply because Terraform can address the target.

<!-- SOURCE-BLOCK RA:353 END -->

<!-- SOURCE-BLOCK RA:354 BEGIN -->


<a id="source-table-354"></a>

| Change class | Required handling |
| --- | --- |
| Routine allocation/resize | Validate quota, placement, current state and surviving capacity; preserve mandatory controls |
| Connectivity/security change | Obtain relevant domain and security authority; verify routes, policy precedence, sessions and both address families |
| Shared foundation or platform upgrade | Compatibility review, representative test/canary, surviving capacity, backup and supported rollback/recovery |
| Emergency containment | Scoped authority, evidence where feasible and explicit override protected from ordinary reconciliation |
| Profile or trust change | Assess all dependent placements and inherited controls; define transition and current-service restrictions |
| Retirement/disposal | Dependency and retention review; remove live authority and sanitize only the data/resources approved for destruction |

<!-- SOURCE-BLOCK RA:354 END -->

<!-- SOURCE-BLOCK RA:355 BEGIN -->

<!-- SOURCE-BLOCK RA:355 END -->

<!-- SOURCE-BLOCK RA:356 BEGIN -->

## Brownfield onboarding

<!-- SOURCE-BLOCK RA:356 END -->

<!-- SOURCE-BLOCK RA:357 BEGIN -->

An existing environment is discovered before it is adopted. Inventory physical and logical topology, ownership, active routes, security policies, data locations, credentials, images and operational dependencies. Compare actual behaviour with the reference architecture. Register gaps explicitly; do not call an imported resource compliant because Terraform has a state record for it.

<!-- SOURCE-BLOCK RA:357 END -->

<!-- SOURCE-BLOCK RA:358 BEGIN -->

Adoption proceeds in controlled scopes. Assign one authoritative owner/tool to each resource, reconcile desired configuration against current state, review a non-destructive plan, and then import or adopt using the supported mechanism. Prevent accidental replacement of VMs, disks, gateways or shared networks. Resources owned by another controller remain under that owner unless a deliberate handover removes dual management. Importing configuration is not authorization to tear down live infrastructure.

<!-- SOURCE-BLOCK RA:358 END -->

<!-- SOURCE-BLOCK RA:359 BEGIN -->

A brownfield migration may require temporary translation, parallel gateways or a staged tenant move. Those are explicit transition designs with owners, expiry, permitted flows and rollback limits. The reference’s steady-state topology remains the target; a transition exception must not become an undocumented permanent shared transit path.

<!-- SOURCE-BLOCK RA:359 END -->

<!-- SOURCE-BLOCK RA:360 BEGIN -->

## Support and drift

<!-- SOURCE-BLOCK RA:360 END -->

<!-- SOURCE-BLOCK RA:361 BEGIN -->

Version and vulnerability management cover hardware/firmware, hypervisors, platform controllers, storage, SDN/security edges, images, providers/modules and privileged execution environments. Remediation windows come from the adopted risk and maintenance policy, not invented universal deadlines. Qualify upgrades against used features and APIs, then promote in stages. Some changes require restore or forward repair because a software downgrade is not supported.

<!-- SOURCE-BLOCK RA:361 END -->

<!-- SOURCE-BLOCK RA:362 BEGIN -->

Configuration drift is compared against both the approved design and actual operation. Security-significant drift triggers an accountable decision to restrict, contain or repair. Historical authorization evidence is retained rather than rewritten to suggest it never existed. Exceptions identify scope, authority, compensating controls, review/expiry and closure evidence; an expired exception does not silently become the new architecture.

<!-- SOURCE-BLOCK RA:362 END -->

<!-- SOURCE-BLOCK RA:363 BEGIN -->

Related engineering: [PROV §5 — Concurrency, ownership and failed execution](../../implementation/provisioning-strategy/5-concurrency-ownership-and-failed-execution.md#PROV_s_005)  •  [PROV §6 — Brownfield adoption, growth and retirement](../../implementation/provisioning-strategy/6-brownfield-adoption-growth-and-retirement.md#PROV_s_006)

<!-- SOURCE-BLOCK RA:363 END -->

[Previous chapter](24-terraform-across-the-vendor-stacks.md) · [Chapter index](README.md) · [Next chapter](26-operating-model-capacity-and-observability.md)

<!-- BEGIN GENERATED DECISION LINKS -->

## Related decision records

- [ADR-0016 — Assign one authoritative writer per native object and sensitive subresource](../../adr/0016-assign-one-authoritative-writer-per-native-object-and-sensitive-subresource.md)
- [ADR-0032 — Keep incident containment above routine reconciliation](../../adr/0032-keep-incident-containment-above-routine-reconciliation.md)
- [ADR-0034 — Classify change by architectural impact rather than file location](../../adr/0034-classify-change-by-architectural-impact-rather-than-file-location.md)

<!-- END GENERATED DECISION LINKS -->
