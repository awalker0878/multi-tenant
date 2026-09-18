# 44. CI/CD, signed plans and supply-chain integrity

[Documentation home](../../README.md) · [Source document](../../../reference/migration-source-documents/Handbook_v1_1.docx) · [Chapter index](README.md)

> **Source:** HB11 — Draft v1.1. Historical source; not the active design.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: afbe9313dda4c68d5bb3af9ae6e9fcb5f098894c59e5f443270795bf2f9c21a1 -->

> **Historical only.** Use the [v1.4 reference architecture](../../architecture/reference/README.md) for the active design baseline. Conflicting historical text has not been silently reconciled.
<!-- SOURCE-BLOCK HB11:607 BEGIN -->

<a id="__RefHeading___Toc13381_1645000677"></a>
<a id="sec_44"></a>

<!-- SOURCE-BLOCK HB11:607 END -->

<!-- SOURCE-BLOCK HB11:608 BEGIN -->

The pipeline validates source and contracts, tests admission, verifies dependencies/provenance, classifies the change, builds an immutable plan, obtains appropriate approval, executes with a scoped identity, waits for realization, validates security/service outcomes and publishes protected evidence. Peer review and policy checks are independent of the privileged runner. An attacker who alters a plan or module after approval must not be able to reuse the approval.

<!-- SOURCE-BLOCK HB11:608 END -->

<!-- SOURCE-BLOCK HB11:609 BEGIN -->

Bind the plan to source revision, input digest, policy/profile/capability digests, provider lock digest, module digests, runner image, state generations, requesting identity, approving authority and expiry. Recheck those facts immediately before apply. A state/policy/profile change requires re-evaluation and normally a new plan/approval. Keep secrets out of public CI logs and do not expose plan artifacts to identities unable to access the underlying protected state.

<!-- SOURCE-BLOCK HB11:609 END -->

<!-- SOURCE-BLOCK HB11:610 BEGIN -->


<a id="source-table-610"></a>

| Gate | Release condition |
| --- | --- |
| Source and contract | Peer review, formatting, schema/semantic tests, secret scanning and normative traceability |
| Dependencies | Approved source, immutable module/runner digest, provider package verification and vulnerability disposition |
| Plan | No unexpected deletion/replacement, exposure, authority change or policy bypass; current state known |
| Approval | Right authority and change class; signed/recorded immutable plan; time-limited permission |
| Execution | Scoped ephemeral runner, locked state, bounded retries and complete journal |
| Qualification/promotion | Required conformance and recovery tests; evidence retention; no candidate-only capability promoted |

<!-- SOURCE-BLOCK HB11:610 END -->

<!-- SOURCE-BLOCK HB11:611 BEGIN -->

Maintain controlled mirrors/repositories where environments are disconnected. Mirrors do not remove the need to verify provenance and revocation. A compromised provider/module triggers suspension of affected runs, preservation of evidence, credential review/rotation, assessment of impacted resources, trusted rebuild and requalification. The incident response must cover artefacts already installed, not only future downloads.

<!-- SOURCE-BLOCK HB11:611 END -->

<!-- SOURCE-BLOCK HB11:612 BEGIN -->

<a id="req_CICD_001"></a>

CICD-001  A change that modifies inter-zone policy, external exposure, route authority, management access, or assurance profile SHALL receive a higher change classification than an ordinary workload scale operation.

<!-- SOURCE-BLOCK HB11:612 END -->

<!-- SOURCE-BLOCK HB11:613 BEGIN -->

Change authority  \|  Verify: [CT-048](73-appendix-d-conformance-test-catalogue.md#test_CT_048), [CT-058](73-appendix-d-conformance-test-catalogue.md#test_CT_058)  \|  Basis: [S00](77-appendix-h-primary-sources-and-implementation-references.md#S00)  \|  retained-v1.0

<!-- SOURCE-BLOCK HB11:613 END -->

<!-- SOURCE-BLOCK HB11:614 BEGIN -->

<a id="req_CICD_002"></a>

CICD-002  An approval SHALL bind the immutable plan and all security-relevant input/policy/state/dependency digests; stale, changed or expired artifacts SHALL be rejected at apply.

<!-- SOURCE-BLOCK HB11:614 END -->

<!-- SOURCE-BLOCK HB11:615 BEGIN -->

Automation platform  \|  Verify: [CT-042](73-appendix-d-conformance-test-catalogue.md#test_CT_042), [CT-048](73-appendix-d-conformance-test-catalogue.md#test_CT_048)  \|  Basis: [S00](77-appendix-h-primary-sources-and-implementation-references.md#S00)  \|  new-v1.1

<!-- SOURCE-BLOCK HB11:615 END -->

<!-- SOURCE-BLOCK HB11:616 BEGIN -->

<a id="req_SUP_001"></a>

SUP-001  Privileged software/provider/module supply chains SHALL use approved sources, integrity verification, revocation and a compromise-response procedure covering already-executed artifacts and credentials.

<!-- SOURCE-BLOCK HB11:616 END -->

<!-- SOURCE-BLOCK HB11:617 BEGIN -->

Automation platform  \|  Verify: [CT-041](73-appendix-d-conformance-test-catalogue.md#test_CT_041), [CT-042](73-appendix-d-conformance-test-catalogue.md#test_CT_042), [CT-057](73-appendix-d-conformance-test-catalogue.md#test_CT_057)  \|  Basis: [S05](77-appendix-h-primary-sources-and-implementation-references.md#S05) / [S14](77-appendix-h-primary-sources-and-implementation-references.md#S14)  \|  new-v1.1

<!-- SOURCE-BLOCK HB11:617 END -->

[Previous chapter](43-state-boundaries-cross-state-transactions-and-partial-failure.md) · [Chapter index](README.md) · [Next chapter](45-secrets-and-automation-credentials.md)
