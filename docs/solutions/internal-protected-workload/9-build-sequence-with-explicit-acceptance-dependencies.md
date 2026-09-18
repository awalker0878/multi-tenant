# 9. Build sequence with explicit acceptance dependencies

[Documentation home](../../README.md) · [Source document](../../../reference/Portable_Hosting_Delivery_Kits_v1_1/05_Reference_v1_4/07_Worked_Infrastructure_Design_and_Acceptance_v1_4.docx) · [Chapter index](README.md)

> **Source:** WD — Draft v1.4. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: e4a2e42888349b5967f7b3174c78e53171728b13e99e4c78bc3cfb53310f68db -->
<!-- SOURCE-BLOCK WD:98 BEGIN -->

<a id="WD14_S09"></a>

<!-- SOURCE-BLOCK WD:98 END -->

<!-- SOURCE-BLOCK WD:99 BEGIN -->

Gate IDs identify decisions, not a chronological permission ladder. G3 does not authorize production before the applicable operational and recovery requirements covered by G4 are ready. A restricted qualification fixture can exist before G2 is complete, under a separately approved non-production test scope. It must not contain unapproved production data or be represented as a production service.

<!-- SOURCE-BLOCK WD:99 END -->

<!-- SOURCE-BLOCK WD:100 BEGIN -->

G4 has two uses: readiness evidence required before the relevant production activation, and recurring operational/recovery acceptance after change or at the approved cadence. The later recurring exercise does not replace the initial proof needed for a promised recovery class. A workload that does not buy site recovery still needs its applicable backup, management recovery, operating ownership and continuity requirements accepted.

<!-- SOURCE-BLOCK WD:100 END -->

<!-- SOURCE-BLOCK WD:101 BEGIN -->

Platform installation and shared-service commissioning can have mutual dependencies. Break the cycle with explicitly authorized bootstrap services and distinguish installation from offered-service acceptance. Joint P2/P3 qualification completes before those resources are advertised to ordinary tenants.

<!-- SOURCE-BLOCK WD:101 END -->

<!-- SOURCE-BLOCK WD:102 BEGIN -->

Handover preparation, credential custody, incident routing, required protection and the applicable authorization are pre-activation conditions. The final post-activation handover record confirms the already accepted scope and as-built result; it must not be the first point at which an operating owner or recovery obligation is discovered.

<!-- SOURCE-BLOCK WD:102 END -->

<!-- SOURCE-BLOCK WD:103 BEGIN -->


<a id="source-table-103"></a>

| Stage / work package | Infrastructure deliverable | Gate / safe stop |
| --- | --- | --- |
| B14-01 / G0 | Approve topology, sharing, source applicability, offered service scope and test authorization. | Unknown mandatory site or support decision blocks the affected build. |
| B14-02 / P0–P1 | Trusted bootstrap, management/OOB, fabric and physical attachment capacity. | G1 acceptance before dependent platform capability is consumed. |
| B14-03 / P2 install + P3 build | Native platforms and provider services installed under restricted authority. | Not yet advertised as qualified tenant capacity. |
| B14-04 / restricted P4–P5 fixture | Create the owned test domains, routes, policies and disposable endpoints; run approved observations. | Pre-production test authorization only; results remain actual observed results, not design assumptions. |
| B14-05 / G2 | Accept exact platform/service tuple, operation coverage and measured service envelope. | No ordinary placement onto an unqualified offered capability. |
| B14-06 / applicable G4 readiness | Accept operating owners, keys/catalogue custody, required restore/recovery proof, support and incident paths. | These are prerequisites for the corresponding production service promise. |
| B14-07 / production P4–P5 and G3 | Provision approved tenant resources; verify current paths and constraints; authorize controlled activation. | Requires G0/G1/G2, applicable G4 readiness and valid authority to operate. |
| B14-08 / P6 and continuing G4 | Observe, maintain, requalify changed capabilities, exercise recovery and retire safely. | Material change can invalidate prior acceptance; historical approval is not rewritten. |

<!-- SOURCE-BLOCK WD:103 END -->

<!-- SOURCE-BLOCK WD:104 BEGIN -->

<!-- SOURCE-BLOCK WD:104 END -->

<!-- SOURCE-BLOCK WD:105 BEGIN -->

Related documents: [QUAL — Gate definitions and acceptance](../../assurance/site-qualification/README.md#V14_QUAL_START)  \|  [PROV — Commissioning and execution sequence](../../implementation/provisioning-strategy/README.md#V14_PROV_START)  \|  [GM — G35 gate clarification](../../assurance/gap-map/README.md#V14_GM_START)

<!-- SOURCE-BLOCK WD:105 END -->

<!-- SOURCE-BLOCK WD:106 BEGIN -->

<!-- SOURCE-BLOCK WD:106 END -->

[Previous chapter](8-mapping-the-schedules-into-each-vendor-stack.md) · [Chapter index](README.md) · [Next chapter](10-resource-ownership-protection-and-change-receipts.md)

<!-- BEGIN GENERATED DECISION LINKS -->

## Related decision records

- [ADR-0015 — Build under deny and verify before and after activation](../../adr/0015-build-under-deny-and-verify-before-and-after-activation.md)
- [ADR-0036 — Require initial operational and recovery readiness before production activation](../../adr/0036-require-initial-operational-and-recovery-readiness-before-production-activation.md)

<!-- END GENERATED DECISION LINKS -->
