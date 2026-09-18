# 41. Zero-touch provisioning and reconciliation workflow

[Documentation home](../../README.md) · [Source document](../../../reference/migration-source-documents/Handbook_v1_1.docx) · [Chapter index](README.md)

> **Source:** HB11 — Draft v1.1. Historical source; not the active design.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: afbe9313dda4c68d5bb3af9ae6e9fcb5f098894c59e5f443270795bf2f9c21a1 -->

> **Historical only.** Use the [v1.4 reference architecture](../../architecture/reference/README.md) for the active design baseline. Conflicting historical text has not been silently reconciled.
<a id="__RefHeading___Toc13375_1645000677"></a>
<a id="sec_41"></a>

Zero-touch means routine approved intent can be realized without manual device editing; it does not remove risk-based approval, initial platform commissioning or safe failure handling. Placement, IPAM and route compilation are mutually constrained: first resolve candidate site/domain/address eligibility, reserve the selected resources, then compile the final graph. Do not allocate a site-specific address before knowing that the selected platform can satisfy it.

![Request enters authorization/schema/profile admission, then candidate placement and reservation. Policy and route compilation precede immutable planning and approval. Authority-specific actuators create deny-protected resources, then realization tests and evidence complete. Only the final readiness gate enables exposure. Failures return to journaled reconciliation or restricted state, not an alternate permissive path.](../../assets/diagrams/79b6906a685db0397303.png)

<a id="fig_pipeline"></a>

Figure 4. A journaled reconciliation pipeline with readiness as a gated state


<a id="source-table-573"></a>

| Stage | Commit condition and failure handling |
| --- | --- |
| 1. Admit intent | Resolve identity/profiles, schema and semantic constraints; reject before allocation on failure. |
| 2. Select and reserve | Choose qualified candidate; atomically reserve quota, capacity and addresses with operation ID. |
| 3. Compile and plan | Generate route/policy/attachment graph; create immutable input and provider-plan digests. |
| 4. Approve and execute | Check fresh approval/state generations; run separate least-privileged actuators in dependency order. |
| 5. Realize under deny | Wait for native readiness; maintain quarantine/default deny before exposure. |
| 6. Verify and record | Run required tests; reconcile inventory and protected evidence for current generation. |
| 7. Activate service | Evaluate technical and authorization conditions, then enable approved exposure and mark Ready. |
| 8. Reconcile continuously | Detect drift/dependency changes; journal retries, compensation or operator intervention. |

The controller owns an operation journal containing idempotency keys, resource identities, reservation leases, intended steps, executed actions, state generations, native request IDs and evidence. Retrying reuses identities and discovers actual state; it does not assume the previous operation failed because its response was lost. A failed operation enters Restricted or Failed with a resumable plan. Partial infrastructure remains denied and owned until safely converged or removed.

<a id="req_AUTO_001"></a>

AUTO-001  If security admission, IPAM, route authority, or mandatory policy validation is unavailable, new provisioning SHALL stop rather than inventing or bypassing required state.

Automation platform  \|  Verify: [CT-011](73-appendix-d-conformance-test-catalogue.md#test_CT_011), [CT-029](73-appendix-d-conformance-test-catalogue.md#test_CT_029), [CT-045](73-appendix-d-conformance-test-catalogue.md#test_CT_045)  \|  Basis: [S00](77-appendix-h-primary-sources-and-implementation-references.md#S00)  \|  retained-v1.0

<a id="req_AUTO_002"></a>

AUTO-002  Provisioning SHALL be journaled and idempotent, reserve only eligible capacity/addresses, enforce deny before attachment/exposure, and gate activation on realized current-generation evidence and authorization.

Automation platform  \|  Verify: [CT-045](73-appendix-d-conformance-test-catalogue.md#test_CT_045), [CT-046](73-appendix-d-conformance-test-catalogue.md#test_CT_046), [CT-048](73-appendix-d-conformance-test-catalogue.md#test_CT_048), [CT-069](73-appendix-d-conformance-test-catalogue.md#test_CT_069)  \|  Basis: [S00](77-appendix-h-primary-sources-and-implementation-references.md#S00)  \|  new-v1.1

<a id="req_AUTO_003"></a>

AUTO-003  Retries SHALL distinguish transient, permanent and conflict failures, use bounded backoff/deadlines and preserve resource identity; uncertain outcomes SHALL be discovered and reconciled rather than duplicated.

Automation platform  \|  Verify: [CT-045](73-appendix-d-conformance-test-catalogue.md#test_CT_045), [CT-046](73-appendix-d-conformance-test-catalogue.md#test_CT_046), [CT-047](73-appendix-d-conformance-test-catalogue.md#test_CT_047)  \|  Basis: [S00](77-appendix-h-primary-sources-and-implementation-references.md#S00)  \|  new-v1.1

[Previous chapter](40-admission-flow-intention-and-policy-compilation.md) · [Chapter index](README.md) · [Next chapter](42-terraform-roots-adapters-and-reproducible-inputs.md)
