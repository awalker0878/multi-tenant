# 3. Apply gate dependencies rather than numerical order

[Documentation home](../../README.md) · [Source document](../../../reference/Portable_Hosting_Delivery_Kits_v1_1/00_Delivery_Map.docx) · [Chapter index](README.md)

> **Source:** DEL — Delivery-kit v1.1 collection; original document version retained in the front matter. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: d8c2790ff7bb408283a9156a369cc6c4394131e7d44bfd130bfa27e7d82b5783 -->
<!-- SOURCE-BLOCK DEL:36 BEGIN -->

<a id="DEL_03"></a>

<!-- SOURCE-BLOCK DEL:36 END -->

<!-- SOURCE-BLOCK DEL:37 BEGIN -->

G0–G4 remain the parent’s acceptance identifiers. They are not a simple chronological ladder: applicable G4 initial readiness precedes G3 production activation.

<!-- SOURCE-BLOCK DEL:37 END -->

<!-- SOURCE-BLOCK DEL:38 BEGIN -->

Design basis and related records: [WD §9](../../solutions/internal-protected-workload/9-build-sequence-with-explicit-acceptance-dependencies.md#WD14_S09)  •  [QUAL §5](../../assurance/site-qualification/5-qualification-stages-applicability-and-evidence.md#QUAL_s_005)

<!-- SOURCE-BLOCK DEL:38 END -->

<!-- SOURCE-BLOCK DEL:39 BEGIN -->


<a id="source-table-39"></a>

| Decision | Required preceding condition | What it does not authorize |
| --- | --- | --- |
| G0: design adoption | Accepted scope and design decisions. | Does not itself authorize a build or production operation. |
| G1: foundation acceptance | G0 for affected scope; actual trusted access and transport evidence. | API reachability is not complete commissioning. |
| Restricted fixture permission | G1 and safeguarded installed candidate resources; authorized test scope. | Does not permit production data or claim platform qualification. |
| G2: platform/service qualification | Applicable single-stack observations, supported tuple and actual limits. | Does not automatically grant operational or security authorization. |
| G4 initial: readiness | Relevant qualified service; required owners, protection and recovery evidence. | Cannot be deferred until after the service promise is activated. |
| G3: production activation | G0/G1/G2, applicable G4 initial, current tenant evidence and valid authority. | Neither a workbook nor tool exit code grants this decision. |
| G4 continuing: reacceptance | Activated scope, approved cadence and material-change triggers. | Historical evidence does not validate a changed topology. |

<!-- SOURCE-BLOCK DEL:39 END -->

<!-- SOURCE-BLOCK DEL:40 BEGIN -->

<!-- SOURCE-BLOCK DEL:40 END -->

<!-- SOURCE-BLOCK DEL:41 BEGIN -->

Resolve service-level qualification and workload-specific acceptance at their actual scopes. Controlled preproduction validation can build the evidence needed for readiness without creating a circular requirement for an already active production service. Record that permission separately and restrict the fixture accordingly.

<!-- SOURCE-BLOCK DEL:41 END -->

<!-- SOURCE-BLOCK DEL:42 BEGIN -->

The gate record identifies the actual approver, scope, evidence and conditions. Missing or blocked evidence remains visible; changing a cell status cannot create the authority or control it references.

<!-- SOURCE-BLOCK DEL:42 END -->

<!-- SOURCE-BLOCK DEL:43 BEGIN -->

Continue with: [QCP §1](../../assurance/qualification-campaign/1-select-the-qualification-scope-and-acceptance-claim.md#QCP_01)  •  [QCP §8](../../assurance/qualification-campaign/8-close-defects-and-issue-a-scoped-campaign-disposition.md#QCP_08)  •  [OPS §8](../../operations/recovery-transition/8-accept-operational-responsibility-for-the-delivered-scope.md#OPS_08)

<!-- SOURCE-BLOCK DEL:43 END -->

<!-- SOURCE-BLOCK DEL:44 BEGIN -->

<!-- SOURCE-BLOCK DEL:44 END -->

[Previous chapter](2-preserve-stable-deliverables-and-explicit-handoffs.md) · [Chapter index](README.md) · [Next chapter](4-use-working-records-without-creating-duplicate-truth.md)

<!-- BEGIN GENERATED DECISION LINKS -->

## Related decision records

- [ADR-0036 — Require initial operational and recovery readiness before production activation](../../adr/0036-require-initial-operational-and-recovery-readiness-before-production-activation.md)

<!-- END GENERATED DECISION LINKS -->
