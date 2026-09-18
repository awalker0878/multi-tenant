# 1. Trace one decision into engineering and evidence

[Documentation home](../../README.md) · [Source document](../../../reference/Portable_Hosting_Delivery_Kits_v1_1/04_Shared/Worked_Delivery_Example.docx) · [Chapter index](README.md)

> **Source:** WDE — Delivery-kit v1.1 collection; original document version retained in the front matter. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: ae4ea65ea564fe848f214f5154ca4b67726eb6628d07a4b4f7714210e49ccd0d -->
<!-- SOURCE-BLOCK WDE:16 BEGIN -->

<a id="EX_01"></a>

<!-- SOURCE-BLOCK WDE:16 END -->

<!-- SOURCE-BLOCK WDE:17 BEGIN -->

Follow the chain from a reasoned architecture selection to a measurable infrastructure result. The same identity appears in the HLD decision, LLD schedule, build step and observation.

<!-- SOURCE-BLOCK WDE:17 END -->

<!-- SOURCE-BLOCK WDE:18 BEGIN -->

Baseline and related records: [WD §2](../internal-protected-workload/2-reference-decisions-and-infrastructure-boundaries.md#WD14_S02)  •  [AK §5](../../architecture/delivery-guide/5-service-resilience-capacity-and-portability.md#AK_05)  •  [ET §4](../../templates/lld/4-routes-zips-and-permitted-flows.md#ET_04)  •  [IT §4](../../templates/implementation-mop/4-test-procedure-and-actual-execution-record.md#IT_04)

<!-- SOURCE-BLOCK WDE:18 END -->

<!-- SOURCE-BLOCK WDE:19 BEGIN -->


<a id="source-table-19"></a>

| Layer / example record | Content | Disposition |
| --- | --- | --- |
| Architecture / ADR-EX-01 | Use dedicated domain-to-edge handoffs until a shared attachment has proven connected-route, neighbour, source and return-path isolation. | Proposed selection; authority not assigned. |
| Requirement / ARCH-003, ZIP-001 | Independent zone traffic traverses the applicable qualified boundary. | Inherited baseline; target applicability/review required. |
| Engineering / NET-EX-A01O | D01O native gateway connects to EC-01 through the A01O handoff; forward and reply routes are identified. | Documentation addresses only; native support not established. |
| Implementation / STEP-EX-01 | Owning network/platform executors instantiate the accepted attachment and baseline; edge owner supplies scoped policy. | Not executed; exact site artifact still required. |
| Verification / OBS-EX-01 | W14-01 and relevant CT-003/009/023/024 observations compare actual routes and enforcement with the schedule. | NOT RUN; no observed artifacts. |
| Acceptance / GATE-EX-01 | Relevant G2 qualification and initial G4 readiness precede production G3 and valid operating authority. | NOT ISSUED; example does not grant permission. |

<!-- SOURCE-BLOCK WDE:19 END -->

<!-- SOURCE-BLOCK WDE:20 BEGIN -->

<!-- SOURCE-BLOCK WDE:20 END -->

<!-- SOURCE-BLOCK WDE:21 BEGIN -->

An accepted topology choice would not by itself prove native compatibility. If engineering selects a supported alternative, the changed boundary and evidence must return to the architecture decision owner rather than silently rewriting the intended outcome.

<!-- SOURCE-BLOCK WDE:21 END -->

<!-- SOURCE-BLOCK WDE:22 BEGIN -->

<!-- SOURCE-BLOCK WDE:22 END -->

[Chapter index](README.md) · [Next chapter](2-resource-and-boundary-schedule.md)
