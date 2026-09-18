# 1. From proposed architecture to accepted service

[Documentation home](../../README.md) · [Source document](../../../reference/Portable_Hosting_Delivery_Kits_v1_1/05_Reference_v1_4/06_Site_Design_Qualification_and_Operations_v1_4.docx) · [Chapter index](README.md)

> **Source:** QUAL — Draft v1.4. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: 783edbba45483d0d3c3b966765589762698836320237906a0f9a60080574af37 -->
<!-- SOURCE-BLOCK QUAL:25 BEGIN -->

<a id="__RefHeading___Toc10033_1525915568"></a>
<a id="QUAL_s_001"></a>

<!-- SOURCE-BLOCK QUAL:25 END -->

<!-- SOURCE-BLOCK QUAL:26 BEGIN -->

Clarification of G3 and G4: the IDs classify decisions and are not a strict ascending execution sequence. G4 initial readiness for the offered operational/recovery scope is a prerequisite of production G3. G4 also includes continuing and recurring acceptance after activation. Restricted non-production fixtures are separately authorized and may exist before G2 to generate its qualification evidence.

<!-- SOURCE-BLOCK QUAL:26 END -->

<!-- SOURCE-BLOCK QUAL:27 BEGIN -->

Parent architecture: [RA §1](../../architecture/reference/1-purpose-scope-and-architectural-authority.md#RA_s_001)  •  [RA §28](../../architecture/reference/28-architecture-acceptance-and-verification.md#RA_s_028)  •  [RA §30](../../architecture/reference/30-implementation-handoff-and-delivery-sequence.md#RA_s_030)

<!-- SOURCE-BLOCK QUAL:27 END -->

<!-- SOURCE-BLOCK QUAL:28 BEGIN -->

The document family supplies a reference architecture and engineering knowledge. A site design selects actual values and resolves local decisions. An as-built record describes what was deployed. Qualification records observed outcomes on that deployment, and formal authorization is issued separately by its designated authority. None of these records can be substituted merely by changing a document status. \[[B2](09-references-parent-basis-and-external-context.md#QUAL_src_B2) §§1, 28, 30\]

<!-- SOURCE-BLOCK QUAL:28 END -->

<!-- SOURCE-BLOCK QUAL:29 BEGIN -->


<a id="source-table-29"></a>

| Gate | Decision and deliverable | What remains unproven after this gate |
| --- | --- | --- |
| G0 · design adoption | Architecture, isolation choices, service envelope, responsibilities and source applicability accepted. | Hardware installation, actual provider coverage and live enforcement. |
| G1 · foundation acceptance | Physical/fault inventory, OOB/management, fabric and bootstrap dependencies built and observed. | Complete platform and shared-service capability for tenants. |
| G2 · platform/service acceptance | Exact stack and shared-service topology, supported operations, capacity and applicable qualification accepted. | An individual workload’s readiness or general portability to every other stack. |
| G3 — Workload activation; scope explicit | Current workload/domain/path evidence. Production also requires applicable G0/G1/G2 acceptance, initial G4 operational and promised recovery readiness, and valid authority to operate. A restricted qualification fixture is separately authorized and is not production readiness. | Does not authorize deferral of required recovery, ownership, key/catalogue custody, support or operating authority until a later gate. |
| G4 — Initial readiness and continuing acceptance | Before relevant production activation: accepted operations, custody, support, and the offered protection/recovery capability. After activation: recurring and material-change evidence maintains acceptance at the approved cadence. | A later exercise cannot retroactively replace initial evidence for a promised service. Scope depends on the actual offered class; unsupported capabilities remain excluded. |

<!-- SOURCE-BLOCK QUAL:29 END -->

<!-- SOURCE-BLOCK QUAL:30 BEGIN -->

<!-- SOURCE-BLOCK QUAL:30 END -->

<!-- SOURCE-BLOCK QUAL:31 BEGIN -->

These gate IDs are a v1.3 coordination aid and do not replace organizational approval processes. One existing change, service or assessment process may implement several gates, provided responsibility and evidence remain clear. An adopting authority can approve the architecture before every stack is qualified, while keeping unsupported service classes explicitly unavailable.

<!-- SOURCE-BLOCK QUAL:31 END -->

<!-- SOURCE-BLOCK QUAL:32 BEGIN -->

Related engineering: [Gap-to-gate map](../gap-map/3-detailed-gap-register-and-treatment.md#GM_s_003)  •  [P0–P6 delivery ownership](../../implementation/provisioning-strategy/1-provisioning-scopes-ownership-and-accepted-handoffs.md#PROV_s_001)

<!-- SOURCE-BLOCK QUAL:32 END -->

[Chapter index](README.md) · [Next chapter](2-site-low-level-design-and-dependency-schedule.md)

<!-- BEGIN GENERATED DECISION LINKS -->

## Related decision records

- [ADR-0036 — Require initial operational and recovery readiness before production activation](../../adr/0036-require-initial-operational-and-recovery-readiness-before-production-activation.md)

<!-- END GENERATED DECISION LINKS -->
