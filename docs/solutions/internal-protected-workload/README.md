# Worked infrastructure design, build schedules and acceptance

[Documentation home](../../README.md) · [Source document](../../../reference/Portable_Hosting_Delivery_Kits_v1_1/05_Reference_v1_4/07_Worked_Infrastructure_Design_and_Acceptance_v1_4.docx)

> **Source:** WD — Draft v1.4. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: e4a2e42888349b5967f7b3174c78e53171728b13e99e4c78bc3cfb53310f68db -->

## Chapters

- [1. Purpose, status and reading order](1-purpose-status-and-reading-order.md)
- [2. Reference decisions and infrastructure boundaries](2-reference-decisions-and-infrastructure-boundaries.md)
- [3. Component and dependency schedule](3-component-and-dependency-schedule.md)
- [4. Tenant, attachment and address schedule](4-tenant-attachment-and-address-schedule.md)
- [5. Dedicated handoff inventory and route ownership](5-dedicated-handoff-inventory-and-route-ownership.md)
- [6. Worked forwarding and return-route schedule](6-worked-forwarding-and-return-route-schedule.md)
- [7. Service permissions and non-IP storage paths](7-service-permissions-and-non-ip-storage-paths.md)
- [8. Mapping the schedules into each vendor stack](8-mapping-the-schedules-into-each-vendor-stack.md)
- [9. Build sequence with explicit acceptance dependencies](9-build-sequence-with-explicit-acceptance-dependencies.md)
- [10. Resource ownership, protection and change receipts](10-resource-ownership-protection-and-change-receipts.md)
- [11. Test-resource, capacity and MTU accounting](11-test-resource-capacity-and-mtu-accounting.md)
- [12. Failure and partition decision schedule](12-failure-and-partition-decision-schedule.md)
- [13. Verification assertions and actual evidence](13-verification-assertions-and-actual-evidence.md)
- [14. Remaining decisions and release boundaries](14-remaining-decisions-and-release-boundaries.md)
- [References and source status](15-references-and-source-status.md)

## Source front matter
<a id="V14_WD_START"></a>

INFRASTRUCTURE DESIGN / WORKED REFERENCE

## Portable Multi-Tenant<br>Secure Hosting

*Worked Infrastructure Design,<br>Build Schedules and Acceptance*

Draft v1.4 \| 16 September 2026

A connected reference design from component and route ownership to controlled activation, recovery and retirement.


<a id="source-table-5"></a>

| Document control | Record |
| --- | --- |
| Document ID / parent | WD — supplement to RA v1.4 |
| Status | Proposed reference design. Actual site decisions, support and qualification remain separate. |
| Baseline | The seven-document v1.3 architecture library, retained without silent removal of requirement history. |
| Release boundary | Documentation and local arithmetic/link checks only. No infrastructure operations performed. |
| Address and capacity status | Documentation examples; not deployment allocations, product minima or measured capability. |

Related documents: [RA — Parent architecture](../../architecture/reference/README.md#V14_RA_START)  \|  [GM — Gaps and decisions](../../assurance/gap-map/README.md#V14_GM_START)  \|  [QUAL — Acceptance](../../assurance/site-qualification/README.md#V14_QUAL_START)

[1. Purpose, status and reading order](1-purpose-status-and-reading-order.md#WD14_S01)

[2. Reference decisions and infrastructure boundaries](2-reference-decisions-and-infrastructure-boundaries.md#WD14_S02)

[3. Component and dependency schedule](3-component-and-dependency-schedule.md#WD14_S03)

[4. Tenant, attachment and address schedule](4-tenant-attachment-and-address-schedule.md#WD14_S04)

[5. Dedicated handoff inventory and route ownership](5-dedicated-handoff-inventory-and-route-ownership.md#WD14_S05)

[6. Worked forwarding and return-route schedule](6-worked-forwarding-and-return-route-schedule.md#WD14_S06)

[7. Service permissions and non-IP storage paths](7-service-permissions-and-non-ip-storage-paths.md#WD14_S07)

[8. Mapping the schedules into each vendor stack](8-mapping-the-schedules-into-each-vendor-stack.md#WD14_S08)

[9. Build sequence with explicit acceptance dependencies](9-build-sequence-with-explicit-acceptance-dependencies.md#WD14_S09)

[10. Resource ownership, protection and change receipts](10-resource-ownership-protection-and-change-receipts.md#WD14_S10)

[11. Test-resource, capacity and MTU accounting](11-test-resource-capacity-and-mtu-accounting.md#WD14_S11)

[12. Failure and partition decision schedule](12-failure-and-partition-decision-schedule.md#WD14_S12)

[13. Verification assertions and actual evidence](13-verification-assertions-and-actual-evidence.md#WD14_S13)

[14. Remaining decisions and release boundaries](14-remaining-decisions-and-release-boundaries.md#WD14_S14)

[References and source status](15-references-and-source-status.md#WD14_SOURCES)

Section links are used instead of unstable manually entered page numbers. The Word navigation pane also lists the headings.
