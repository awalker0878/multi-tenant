# 6. Brownfield adoption, growth and retirement

[Documentation home](../../README.md) · [Source document](../../../reference/Portable_Hosting_Delivery_Kits_v1_1/05_Reference_v1_4/04_Provisioning_and_Commissioning_v1_4.docx) · [Chapter index](README.md)

> **Source:** PROV — Draft v1.4. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: 483df77cff70166fbdfdf711135efa3beeecc8fe1015a58290cbebff5b80bdfd -->
<!-- SOURCE-BLOCK PROV:73 BEGIN -->

<a id="__RefHeading___Toc7822_1525915568"></a>
<a id="PROV_s_006"></a>

<!-- SOURCE-BLOCK PROV:73 END -->

<!-- SOURCE-BLOCK PROV:74 BEGIN -->

Parent architecture: [RA §25](../../architecture/reference/25-change-brownfield-adoption-and-configuration-ownership.md#RA_s_025)  •  [RA §27](../../architecture/reference/27-recovery-migration-and-retirement.md#RA_s_027)  •  [RA §30](../../architecture/reference/30-implementation-handoff-and-delivery-sequence.md#RA_s_030)

<!-- SOURCE-BLOCK PROV:74 END -->

<!-- SOURCE-BLOCK PROV:75 BEGIN -->

Adopt an existing environment without treating discovery as permission to mutate it. First record the actual physical/logical topology, native identifiers, routes, policy, data copies, management tools and operating owners. Compare it with the parent architecture and distinguish a supported legacy variation from an unexplained gap. An imported state record does not prove conformance. \[[B2](07-references-parent-basis-and-external-context.md#PROV_src_B2) §25\]

<!-- SOURCE-BLOCK PROV:75 END -->

<!-- SOURCE-BLOCK PROV:76 BEGIN -->


<a id="source-table-76"></a>

| Adoption stage | Required artefact | Stop condition |
| --- | --- | --- |
| Discover and protect | Inventory, dependency/owner map, backup/recovery and agreed change freeze scope. | Unknown critical ownership or unverified recovery path. |
| Select authoritative owner | Object-by-object assignment to existing tool, new tool or controlled handover. | Two controllers remain able to overwrite the same object. |
| Model current accepted configuration | Actual identifiers, current routes and approved variation recorded. | New desired defaults would silently change live security or availability. |
| Import/adopt using supported mechanism | Reviewed import operation and protected state; no implicit resource recreation. | Provider cannot represent required state without destructive replacement. |
| Review no-op or explicit delta | Plan shows no unexpected replace/delete/exposure; peer review of unavoidable differences. | Unexplained diff on a disk, network, gateway or shared service. |
| Canary change and observe | Small approved change, native observations and service/security checks. | Conformance or operating outcome differs from the accepted plan. |
| Transfer and operate | Old writer removed; owner, monitoring and recovery runbook accepted. | Undocumented ongoing dual management or stranded credentials. |

<!-- SOURCE-BLOCK PROV:76 END -->

<!-- SOURCE-BLOCK PROV:77 BEGIN -->

<!-- SOURCE-BLOCK PROV:77 END -->

<!-- SOURCE-BLOCK PROV:78 BEGIN -->

Capacity growth uses the same logic at a foundation boundary: admit hardware or new pools only after supported versions, physical dependency, routing/MTU, storage rebuild, inspection load and operating ownership checks. A tenant allocation consumes commissioned capacity; it does not silently expand a host-sharing domain or create a shared fallback network when capacity is exhausted.

<!-- SOURCE-BLOCK PROV:78 END -->

<!-- SOURCE-BLOCK PROV:79 BEGIN -->

Retirement starts with shared resources, required exports/backups and retention decisions. Preserve the paths and keys needed to meet those obligations; then withdraw optional exposure, remove endpoints and obsolete bindings, reconcile routes/names/addresses, revoke live authority and sanitize approved data. Retained copies keep a separate accountable recovery/retention scope. The final receipt states what remains and why instead of claiming complete destruction from a successful destroy command.

<!-- SOURCE-BLOCK PROV:79 END -->

<!-- SOURCE-BLOCK PROV:80 BEGIN -->

Related engineering: [Data and retention ledger](../../architecture/shared-services/4-storage-copies-and-retained-data-ownership.md#SVC_s_004)  •  [Migration and failback](../../architecture/shared-services/6-failure-recovery-migration-and-failback-topology.md#SVC_s_006)  •  [Operational handover](../../assurance/site-qualification/7-operating-accountability-handover-and-change.md#QUAL_s_007)

<!-- SOURCE-BLOCK PROV:80 END -->

[Previous chapter](5-concurrency-ownership-and-failed-execution.md) · [Chapter index](README.md) · [Next chapter](07-references-parent-basis-and-external-context.md)

<!-- BEGIN GENERATED DECISION LINKS -->

## Related decision records

- [ADR-0033 — Separate live-service retirement from retained-data disposal](../../adr/0033-separate-live-service-retirement-from-retained-data-disposal.md)

<!-- END GENERATED DECISION LINKS -->
