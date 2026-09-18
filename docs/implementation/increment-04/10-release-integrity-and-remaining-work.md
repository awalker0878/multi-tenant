# Release integrity and remaining work

[Documentation home](../../README.md) · [Source document](../../../Implementation_Execution_Guide.docx) · [Chapter index](README.md)

> **Source:** IMP04 — Implementation Increment 04. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: 9ca5c85333dcb51137ca694aea7b034e393fa8927831f0b475b3b88e842418f7 -->
<!-- SOURCE-BLOCK IMP04:127 BEGIN -->

<a id="chapter_10"></a>

<!-- SOURCE-BLOCK IMP04:127 END -->

<!-- SOURCE-BLOCK IMP04:128 BEGIN -->

[Contents and release status](01-implementation-increment-04.md#chapter_1)

<!-- SOURCE-BLOCK IMP04:128 END -->

<!-- SOURCE-BLOCK IMP04:129 BEGIN -->

## Remaining native scope

<!-- SOURCE-BLOCK IMP04:129 END -->

<!-- SOURCE-BLOCK IMP04:130 BEGIN -->

Qualify the selected readback profiles against real API behavior, expected-field omission, identity, task scope and RBAC before relying on them. Add supported VM/Flow/route and composite-task readback deliberately; do not claim the current readers cover them. Actual writer fencing, state reconciliation and forward repair remain native-owner work.

<!-- SOURCE-BLOCK IMP04:130 END -->

<!-- SOURCE-BLOCK IMP04:131 BEGIN -->

The next infrastructure dependencies remain the selected EC/SE firewall and installed platform combination, real attachment/policy/inspection/HA implementation, IPAM and production service integrations, native IPv6 and actual operating qualification. No native ALLOW policy, provider switch, unverified state import or automatic activation is introduced.

<!-- SOURCE-BLOCK IMP04:131 END -->

<!-- SOURCE-BLOCK IMP04:132 BEGIN -->

## Scope the next accepted native increment

<!-- SOURCE-BLOCK IMP04:132 END -->

<!-- SOURCE-BLOCK IMP04:133 BEGIN -->


<a id="source-table-133"></a>

| Required owner input | What it enables |
| --- | --- |
| Installed NSX or Nutanix tuple, native read principal and exact disposable target | Validate the candidate profile against real field omission, token and status behavior. |
| Actual EC/SE firewall and attachment implementation | Build the domain and service contexts, policy/inspection, interfaces, return routes and HA. |
| Native execution and fencing mechanism | Track and control outstanding tasks, reconcile state and design an authorized forward repair. |
| Shared-service and recovery acceptance | Integrate actual IPAM, DNS, identity, keys, storage and backup with the required operating evidence. |

<!-- SOURCE-BLOCK IMP04:133 END -->

<!-- SOURCE-BLOCK IMP04:134 BEGIN -->

## Release handling

<!-- SOURCE-BLOCK IMP04:134 END -->

<!-- SOURCE-BLOCK IMP04:135 BEGIN -->

Verify release hashes immediately after extraction. The hash manifest detects byte differences; it does not authenticate the publisher or approver. Local tests intentionally refresh their quality reports. Do not replace a historical source record with a new successful result or interpret a previous release’s report as evidence for changed code.

<!-- SOURCE-BLOCK IMP04:135 END -->

<!-- SOURCE-BLOCK IMP04:136 BEGIN -->

The package contains source and documentation only: no provider cache, native state, saved live plan, private key or generated fixture credential. Re-extraction verification is recorded separately. Frozen reference documents and workbooks are preserved, not newly rendered, recalculated or authorized.

<!-- SOURCE-BLOCK IMP04:136 END -->

<!-- SOURCE-BLOCK IMP04:137 BEGIN -->

[Complete source review register](../../../sources/increment04_references.json)

<!-- SOURCE-BLOCK IMP04:137 END -->

<!-- SOURCE-BLOCK IMP04:138 BEGIN -->

[Increment03 source fingerprints](../../../sources/increment03_manifest.json)

<!-- SOURCE-BLOCK IMP04:138 END -->

<!-- SOURCE-BLOCK IMP04:139 BEGIN -->

Public documentation supports the stated interface shapes. Version pins and local response fixtures do not establish installed compatibility, organizational approval or full security assurance. No third-party SDK, private key, provider binary or font file is shipped.

<!-- SOURCE-BLOCK IMP04:139 END -->

[Previous chapter](09-primary-native-interface-sources.md) · [Chapter index](README.md)
