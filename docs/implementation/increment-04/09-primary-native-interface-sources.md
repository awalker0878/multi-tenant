# Primary native-interface sources

[Documentation home](../../README.md) · [Source document](../../../Implementation_Execution_Guide.docx) · [Chapter index](README.md)

> **Source:** IMP04 — Implementation Increment 04. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: 9ca5c85333dcb51137ca694aea7b034e393fa8927831f0b475b3b88e842418f7 -->
<!-- SOURCE-BLOCK IMP04:99 BEGIN -->

<a id="chapter_9"></a>

<!-- SOURCE-BLOCK IMP04:99 END -->

<!-- SOURCE-BLOCK IMP04:100 BEGIN -->

[Contents and release status](01-implementation-increment-04.md#chapter_1)

<!-- SOURCE-BLOCK IMP04:100 END -->

<!-- SOURCE-BLOCK IMP04:101 BEGIN -->

Immediate baseline: Implementation Increment03. All 139 frozen reference files and 50 Terraform source files are preserved. The source manifest records the baseline; the new code and documents are separately identified. The existing architecture, resource owners and required initial-readiness gates have not been replaced by a software-controller design.

<!-- SOURCE-BLOCK IMP04:101 END -->

<!-- SOURCE-BLOCK IMP04:102 BEGIN -->

## Primary native-interface sources

<!-- SOURCE-BLOCK IMP04:102 END -->

<!-- SOURCE-BLOCK IMP04:103 BEGIN -->

N1 — NSX Local Manager: ReadIntentStatus

<!-- SOURCE-BLOCK IMP04:103 END -->

<!-- SOURCE-BLOCK IMP04:104 BEGIN -->

GET intent status; intent\_version, publish\_status, consolidated and per-enforcement-point status. API latest documentation snapshot (page identifies 9.1.1.0); not installed-release qualification. Reviewed 17 September 2026.

<!-- SOURCE-BLOCK IMP04:104 END -->

<!-- SOURCE-BLOCK IMP04:105 BEGIN -->

[N1 official source](https://developer.broadcom.com/xapis/nsx-t-data-center-rest-api/latest/method_ReadIntentStatus.html)

<!-- SOURCE-BLOCK IMP04:105 END -->

<!-- SOURCE-BLOCK IMP04:106 BEGIN -->

N2 / N3 / N4 — NSX: ReadGatewayPolicyForDomain

<!-- SOURCE-BLOCK IMP04:106 END -->

<!-- SOURCE-BLOCK IMP04:107 BEGIN -->

Exact gateway policy GET, revision and nested rule structure. Rule order, source/destination negation, inline services and profiles. Local Manager segment path and resource representation. API latest documentation snapshot; only Local Manager root implemented. Reviewed 17 September 2026.

<!-- SOURCE-BLOCK IMP04:107 END -->

<!-- SOURCE-BLOCK IMP04:108 BEGIN -->

[N2 official source](https://developer.broadcom.com/xapis/nsx-t-data-center-rest-api/latest/method_ReadGatewayPolicyForDomain.html)

<!-- SOURCE-BLOCK IMP04:108 END -->

<!-- SOURCE-BLOCK IMP04:109 BEGIN -->

[N3 official source](https://developer.broadcom.com/xapis/nsx-t-data-center-rest-api/latest/method_ReadGatewayRule.html)

<!-- SOURCE-BLOCK IMP04:109 END -->

<!-- SOURCE-BLOCK IMP04:110 BEGIN -->

[N4 official source](https://developer.broadcom.com/xapis/nsx-t-data-center-rest-api/latest/method_ReadInfraSegment.html)

<!-- SOURCE-BLOCK IMP04:110 END -->

<!-- SOURCE-BLOCK IMP04:111 BEGIN -->

U1 / U2 — Nutanix prism Go SDK v4.3.1: TasksApi

<!-- SOURCE-BLOCK IMP04:111 END -->

<!-- SOURCE-BLOCK IMP04:112 BEGIN -->

GetTaskById: GET /api/prism/v4.3/config/tasks/{extId}. Task identity/status/times, entity counts and limited subtask/entity lists. Pinned SDK reference, no SDK package or vendor runtime executed. Reviewed 17 September 2026.

<!-- SOURCE-BLOCK IMP04:112 END -->

<!-- SOURCE-BLOCK IMP04:113 BEGIN -->

[U1 official source](https://raw.githubusercontent.com/nutanix/ntnx-api-golang-clients/prism-go-client/v4.3.1/prism-go-client/api/tasks_api.go)

<!-- SOURCE-BLOCK IMP04:113 END -->

<!-- SOURCE-BLOCK IMP04:114 BEGIN -->

[U2 official source](https://raw.githubusercontent.com/nutanix/ntnx-api-golang-clients/prism-go-client/v4.3.1/prism-go-client/models/prism/v4/config/config_model.go)

<!-- SOURCE-BLOCK IMP04:114 END -->

<!-- SOURCE-BLOCK IMP04:115 BEGIN -->

U3 / U4 / U5 — Nutanix networking Go SDK v4.3.1: VpcsApi

<!-- SOURCE-BLOCK IMP04:115 END -->

<!-- SOURCE-BLOCK IMP04:116 BEGIN -->

GetVpcById: GET /api/networking/v4.3/config/vpcs/{extId}. GetSubnetById: GET /api/networking/v4.3/config/subnets/{extId}. Vpc and Subnet: extId, native tenantId, subnet membership and routable prefixes. Selected networking v4.3 profile; no fallback negotiation. Reviewed 17 September 2026.

<!-- SOURCE-BLOCK IMP04:116 END -->

<!-- SOURCE-BLOCK IMP04:117 BEGIN -->

[U3 official source](https://raw.githubusercontent.com/nutanix/ntnx-api-golang-clients/networking-go-client/v4.3.1/networking-go-client/api/vpcs_api.go)

<!-- SOURCE-BLOCK IMP04:117 END -->

<!-- SOURCE-BLOCK IMP04:118 BEGIN -->

[U4 official source](https://raw.githubusercontent.com/nutanix/ntnx-api-golang-clients/networking-go-client/v4.3.1/networking-go-client/api/subnets_api.go)

<!-- SOURCE-BLOCK IMP04:118 END -->

<!-- SOURCE-BLOCK IMP04:119 BEGIN -->

[U5 official source](https://raw.githubusercontent.com/nutanix/ntnx-api-golang-clients/networking-go-client/v4.3.1/networking-go-client/models/networking/v4/config/config_model.go)

<!-- SOURCE-BLOCK IMP04:119 END -->

<!-- SOURCE-BLOCK IMP04:120 BEGIN -->

U6 — Nutanix Terraform provider v2.4.2 dependencies

<!-- SOURCE-BLOCK IMP04:120 END -->

<!-- SOURCE-BLOCK IMP04:121 BEGIN -->

Networking and prism SDK dependency versions. Provenance context only; no installed-platform compatibility inferred. Reviewed 17 September 2026.

<!-- SOURCE-BLOCK IMP04:121 END -->

<!-- SOURCE-BLOCK IMP04:122 BEGIN -->

[U6 official source](https://raw.githubusercontent.com/nutanix/terraform-provider-nutanix/v2.4.2/go.mod)

<!-- SOURCE-BLOCK IMP04:122 END -->

<!-- SOURCE-BLOCK IMP04:123 BEGIN -->

T4 — Terraform 1.13.5 release index

<!-- SOURCE-BLOCK IMP04:123 END -->

<!-- SOURCE-BLOCK IMP04:124 BEGIN -->

Linux amd64 binary location for toolchain retry. Public index inspected; container DNS failed; no binary or checksum obtained. Reviewed 17 September 2026.

<!-- SOURCE-BLOCK IMP04:124 END -->

<!-- SOURCE-BLOCK IMP04:125 BEGIN -->

[T4 official source](https://releases.hashicorp.com/terraform/1.13.5/)

<!-- SOURCE-BLOCK IMP04:125 END -->

<!-- SOURCE-BLOCK IMP04:126 BEGIN -->

<!-- SOURCE-BLOCK IMP04:126 END -->

[Previous chapter](08-native-commissioning-and-stopping-conditions.md) · [Chapter index](README.md) · [Next chapter](10-release-integrity-and-remaining-work.md)
