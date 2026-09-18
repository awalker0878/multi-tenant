# Local execution and observed results

[Documentation home](../../README.md) · [Source document](../../../Implementation_Execution_Guide.docx) · [Chapter index](README.md)

> **Source:** IMP04 — Implementation Increment 04. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: 9ca5c85333dcb51137ca694aea7b034e393fa8927831f0b475b3b88e842418f7 -->
<a id="chapter_7"></a>

[Contents and release status](01-implementation-increment-04.md#chapter_1)

The new fixture uses actual loopback TLS and HTTP GET exchanges with scripted published response shapes. It is not a vendor emulator. Task responses, fencing and quarantine records are controlled fault fixtures; actual native task execution, RBAC, fencing and HA were not exercised.


<a id="source-table-76"></a>

| Check | Current executed result / scope |
| --- | --- |
| Python unit/source/local protocol suite | 388 run; zero failures, errors or skips. Includes the new reader/recovery regressions. |
| Native-readback fault campaign | 16 passed; 0 failed. End-to-end local observation plus offline recovery triage, not additional unique unit coverage. |
| Existing DNS wire campaign | 32 passed. TCP/TSIG authority fixture; subset of unit suite, not production DNS qualification. |
| Existing IPv4 packet/mTLS campaign | 47 passed. Fixed 17-namespace fixture; original namespace configuration unchanged. |
| Offline dual-family route checks | 80 passed. Model calculations, not native or routed IPv6 execution. |
| Terraform and native qualification | BLOCKED / NOT RUN. No actual plugin schema, lockfile, mocked-plan pass or vendor-side read claimed. |

## Faults that change the recovery decision

The campaign exercises delayed task/publication completion, NSX configuration changing around status reads, stale intent versions, incomplete enforcing-system span, a failed Nutanix task with an existing resource, HTTP 404, wrong native tenant, changed ETag and incomplete affected entities. Unverified writer fencing, active containment and superseding generations remain holds even after selected-state match.

Additional regressions cover untrusted TLS, redirects, proxy/keylog inheritance, malformed/ambiguous data, absent optional fields, rule order/negation/inline services, slow body delivery, exclusive journal creation, stale/future observations and tampered history. Passing local fixtures proves the implemented handling of those cases, not truthfulness or completeness of a real management plane.

[Current local regression record](../../../quality/local_validation.json)

[Native-readback campaign observations](../../../quality/local_native_readback.json)

[Retained routed packet and identity campaign](../../../quality/local_packet_lab.json)

[Actual Terraform blocker and download attempt](../../../quality/toolchain_access.json)

[Previous chapter](06-transport-credentials-and-protected-evidence.md) · [Chapter index](README.md) · [Next chapter](08-native-commissioning-and-stopping-conditions.md)
