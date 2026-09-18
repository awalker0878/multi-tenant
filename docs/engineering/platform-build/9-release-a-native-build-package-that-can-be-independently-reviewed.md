# 9. Release a native build package that can be independently reviewed

[Documentation home](../../README.md) · [Source document](../../../reference/Portable_Hosting_Delivery_Kits_v1_1/02_Engineering/Platform_Engineering_and_Build_Specifications.docx) · [Chapter index](README.md)

> **Source:** PBS — Delivery-kit v1.1 collection; original document version retained in the front matter. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: 8c2dd9e86b4ea021922777a963534c6b52d85dff8ee398c3a12cc81287356643 -->
<a id="PBS_09"></a>

This record sits beside the existing LLD and operation-coverage schedule. It is a specification for real build artifacts, not a substitute for them.

Design basis and related records: [ET §8](../../templates/lld/8-exact-platform-and-tool-operation-coverage.md#ET_08)  •  [ET §9](../../templates/lld/9-build-and-qualification-design.md#ET_09)  •  [EK §8](../delivery-guide/8-build-test-and-implementation-handoff.md#EK_08)  •  [IK §1](../../implementation/delivery-guide/1-implementation-workplan-and-required-inputs.md#IK_01)


<a id="source-table-108"></a>

| Release item | What must be resolved | Working reference |
| --- | --- | --- |
| Exact implementation | Hardware/firmware, stack/API/provider/installer versions, features, entitlements and support evidence. | \[Enter pbs implementation tuple\] |
| Native mapping | Logical components/interfaces mapped to actual resources; one writer per supported boundary. | \[Enter pbs native mapping\] |
| Build artifacts | Reviewed configuration/module/installer inputs, provenance, integrity and privileged custody references. | \[Enter pbs build artifacts\] |
| Lifecycle behaviour | Operation coverage, completion signals, replacement risk, task discovery and supported recovery. | \[Enter pbs lifecycle coverage\] |
| Qualification | Applicable observations, actual test resources, fault safety envelope and artifact collection. | \[Enter pbs qualification plan\] |
| Handoff decision | Recipient, unresolved blockers, accepted revision and signed scope decision. | \[Enter pbs handoff decision\] |

Review one creation, one policy change, one resource update, one uncertain task and one retirement before releasing the package. For each, identify the last safe stopping point and the data or authority that must be preserved. If no supported recovery or forward-repair path exists, narrow or defer the capability instead of calling a placeholder complete.

The actual MOP records native commands/API artifacts only after the configuration source and support combination are accepted. The reusable runbooks remain references. Permission to run a restricted qualification fixture is not permission to activate production, and a build receipt is not a passing test report.

This release supplies engineering specifications and record fields. All installed values, native execution artifacts and platform qualification evidence remain implementation inputs.

Continue with: [QCP §1](../../assurance/qualification-campaign/1-select-the-qualification-scope-and-acceptance-claim.md#QCP_01)  •  [IT §1](../../templates/implementation-mop/1-change-and-method-of-procedure-cover.md#IT_01)

[Previous chapter](8-publish-shared-service-handoffs-without-sharing-authority.md) · [Chapter index](README.md)
