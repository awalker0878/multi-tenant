# 38. Deployment Evidence

[Documentation home](../../README.md) · [Source document](../../../reference/migration-source-documents/Handbook_v1_0.docx) · [Chapter index](README.md)

> **Source:** HB10 — Draft v1.0. Historical source; not the active design.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: 100c760003b9ff956ae369ece65c5ffe7736f6d481496d8df4c99dd6105d4190 -->

> **Historical only.** Use the [v1.4 reference architecture](../../architecture/reference/README.md) for the active design baseline. Conflicting historical text has not been silently reconciled.
<!-- SOURCE-BLOCK HB10:291 BEGIN -->

<!-- SOURCE-BLOCK HB10:291 END -->

<!-- SOURCE-BLOCK HB10:292 BEGIN -->

Every deployment should produce a machine-readable evidence record so operators and assessors can determine why connectivity exists and which version of policy, modules and provider produced it.

<!-- SOURCE-BLOCK HB10:292 END -->

<!-- SOURCE-BLOCK HB10:293 BEGIN -->


<a id="source-table-293"></a>

| evidence:<br>  deployment\_id: &lt;uuid&gt;<br>  tenant: tenant-001<br>  wsd: application-prod<br>  security\_profile: protected-b-medium<br>  assurance\_profile: standard<br>  platform\_profile: &lt;name + version&gt;<br>  site: &lt;site-id&gt;<br>  security\_domains: \[...\]<br>  networks: \[...\]<br>  zip\_relationships: \[...\]<br>  approved\_flows: \[...\]<br>  service\_bindings: \[...\]<br>  exposures: \[...\]<br>  policy\_bundle\_version: &lt;sha&gt;<br>  terraform\_source\_revision: &lt;sha&gt;<br>  provider\_lock\_digest: &lt;digest&gt;<br>  tests: \[...\]<br>  exceptions: \[...\]<br>  timestamp: &lt;utc&gt;<br>  authorization\_state: compliant \| exception \| failed<br> |
| --- |

<!-- SOURCE-BLOCK HB10:293 END -->

<!-- SOURCE-BLOCK HB10:294 BEGIN -->


<a id="source-table-294"></a>

| EVID-001 | The evidence record SHALL identify the source revision, policy version, provider/module versions, realized security relationships, test results, and active exceptions. |
| --- | --- |

<!-- SOURCE-BLOCK HB10:294 END -->

[Previous chapter](37-conformance-test-framework.md) · [Chapter index](README.md) · [Next chapter](39-logging-telemetry-and-observability.md)
