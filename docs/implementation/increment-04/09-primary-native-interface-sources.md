# Primary native-interface sources

[Documentation home](../../README.md) · [Source document](../../../Implementation_Execution_Guide.docx) · [Chapter index](README.md)

> **Source:** IMP04 — Implementation Increment 04. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: 9ca5c85333dcb51137ca694aea7b034e393fa8927831f0b475b3b88e842418f7 -->
<a id="chapter_9"></a>

[Contents and release status](01-implementation-increment-04.md#chapter_1)

Immediate baseline: Implementation Increment03. All 139 frozen reference files and 50 Terraform source files are preserved. The source manifest records the baseline; the new code and documents are separately identified. The existing architecture, resource owners and required initial-readiness gates have not been replaced by a software-controller design.

## Primary native-interface sources

N1 — NSX Local Manager: ReadIntentStatus

GET intent status; intent\_version, publish\_status, consolidated and per-enforcement-point status. API latest documentation snapshot (page identifies 9.1.1.0); not installed-release qualification. Reviewed 17 September 2026.

[N1 official source](https://developer.broadcom.com/xapis/nsx-t-data-center-rest-api/latest/method_ReadIntentStatus.html)

N2 / N3 / N4 — NSX: ReadGatewayPolicyForDomain

Exact gateway policy GET, revision and nested rule structure. Rule order, source/destination negation, inline services and profiles. Local Manager segment path and resource representation. API latest documentation snapshot; only Local Manager root implemented. Reviewed 17 September 2026.

[N2 official source](https://developer.broadcom.com/xapis/nsx-t-data-center-rest-api/latest/method_ReadGatewayPolicyForDomain.html)

[N3 official source](https://developer.broadcom.com/xapis/nsx-t-data-center-rest-api/latest/method_ReadGatewayRule.html)

[N4 official source](https://developer.broadcom.com/xapis/nsx-t-data-center-rest-api/latest/method_ReadInfraSegment.html)

U1 / U2 — Nutanix prism Go SDK v4.3.1: TasksApi

GetTaskById: GET /api/prism/v4.3/config/tasks/{extId}. Task identity/status/times, entity counts and limited subtask/entity lists. Pinned SDK reference, no SDK package or vendor runtime executed. Reviewed 17 September 2026.

[U1 official source](https://raw.githubusercontent.com/nutanix/ntnx-api-golang-clients/prism-go-client/v4.3.1/prism-go-client/api/tasks_api.go)

[U2 official source](https://raw.githubusercontent.com/nutanix/ntnx-api-golang-clients/prism-go-client/v4.3.1/prism-go-client/models/prism/v4/config/config_model.go)

U3 / U4 / U5 — Nutanix networking Go SDK v4.3.1: VpcsApi

GetVpcById: GET /api/networking/v4.3/config/vpcs/{extId}. GetSubnetById: GET /api/networking/v4.3/config/subnets/{extId}. Vpc and Subnet: extId, native tenantId, subnet membership and routable prefixes. Selected networking v4.3 profile; no fallback negotiation. Reviewed 17 September 2026.

[U3 official source](https://raw.githubusercontent.com/nutanix/ntnx-api-golang-clients/networking-go-client/v4.3.1/networking-go-client/api/vpcs_api.go)

[U4 official source](https://raw.githubusercontent.com/nutanix/ntnx-api-golang-clients/networking-go-client/v4.3.1/networking-go-client/api/subnets_api.go)

[U5 official source](https://raw.githubusercontent.com/nutanix/ntnx-api-golang-clients/networking-go-client/v4.3.1/networking-go-client/models/networking/v4/config/config_model.go)

U6 — Nutanix Terraform provider v2.4.2 dependencies

Networking and prism SDK dependency versions. Provenance context only; no installed-platform compatibility inferred. Reviewed 17 September 2026.

[U6 official source](https://raw.githubusercontent.com/nutanix/terraform-provider-nutanix/v2.4.2/go.mod)

T4 — Terraform 1.13.5 release index

Linux amd64 binary location for toolchain retry. Public index inspected; container DNS failed; no binary or checksum obtained. Reviewed 17 September 2026.

[T4 official source](https://releases.hashicorp.com/terraform/1.13.5/)

[Previous chapter](08-native-commissioning-and-stopping-conditions.md) · [Chapter index](README.md) · [Next chapter](10-release-integrity-and-remaining-work.md)
