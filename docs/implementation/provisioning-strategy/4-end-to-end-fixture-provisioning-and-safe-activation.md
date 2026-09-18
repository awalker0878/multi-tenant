# 4. End-to-end fixture provisioning and safe activation

[Documentation home](../../README.md) · [Source document](../../../reference/Portable_Hosting_Delivery_Kits_v1_1/05_Reference_v1_4/04_Provisioning_and_Commissioning_v1_4.docx) · [Chapter index](README.md)

> **Source:** PROV — Draft v1.4. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: 483df77cff70166fbdfdf711135efa3beeecc8fe1015a58290cbebff5b80bdfd -->
<a id="__RefHeading___Toc7818_1525915568"></a>
<a id="PROV_s_004"></a>

Activation scope is explicit. A restricted non-production fixture can be built under its approved test authorization before platform qualification is complete, solely to produce the required evidence. Production activation requires accepted platform/service capability, current workload checks, applicable operational/recovery readiness and valid authority. The post-activation handover records the accepted as-built service; it does not defer selecting its owner, protection or recovery obligations.

Parent architecture: [RA §23](../../architecture/reference/23-tenant-domain-and-workload-provisioning-sequence.md#RA_s_023)  •  [RA §24](../../architecture/reference/24-terraform-across-the-vendor-stacks.md#RA_s_024)

This sequence builds the VND §1 reference fixture on one chosen stack. It assumes P0–P3 are accepted for the offered class; it does not silently perform procurement or platform installation. Repeat the same outcome on a second stack for portability evidence. The native resources differ, while the domain ownership, service paths and activation conditions remain the same.


<a id="source-table-58"></a>

| Step | Actual infrastructure deliverable | Gate and response to failure |
| --- | --- | --- |
| 1 · approve and place | Two tenant scopes, WSD requirements and eligible cells/pools selected. | Conflicting category, isolation, location or recovery requirement rejects before allocation. |
| 2 · reserve | Compute/data demand, four domain attachments and actual address allocations reserved under owner IDs. | Any scarce dependency failure releases unused reservations or leaves a clearly owned pending allocation. |
| 3 · establish native scope | D01O/D01R/D02O/D02R and their networks/gateway contexts created or explicitly reused. | Mandatory deny baseline effective; no endpoint activation yet. |
| 4 · connect boundary | A01O…A02R paired to accepted edge contexts; Z01/Z02 routes and narrow policies configured. | Unknown/native bypass path prevents subsequent exposure. |
| 5 · allocate endpoints/data | Approved processor/data test endpoints and owned storage attached within eligible pools. | No reassignment of another tenant’s disk or ineligible host on failure. |
| 6 · attach necessary services | Names, time, trust, logging and protection assignments established. | Initialization allows only the approved endpoint/protocol/identity scope. |
| 7 · verify under restriction | Healthy positive controls, cross-tenant/management denials, permitted data service, route ownership and protection verified. | Failed or missing evidence leaves service restricted; preserve test data for diagnosis. |
| 8 · controlled activation | Activate only the approved access and mode. Production requires applicable G4 readiness and operating authority; a qualification fixture remains restricted and non-production. | Failed immediate live-path check withdraws new exposure and sessions according to policy. |
| 9 · hand over | As-built resources, service parameters, operating owner and required authorization recorded. | The final record confirms already accepted ownership and authorization; neither may first be obtained after production exposure. |

Treat network attachment and exposure as explicit activation boundaries. During assembly, endpoints may be absent, disconnected or held in a verified quarantine policy. A temporary bootstrap permit needs a named endpoint, reason, protocol set, owner and withdrawal condition. It must not permit arbitrary access to management or the whole shared-services network. Retain essential service access after activation only where it is part of the approved steady-state design.


<a id="source-table-61"></a>

| Interrupted stage | Safe recovery action | Do not do |
| --- | --- | --- |
| Before endpoint/data creation | Discover actual reservations and native network state; retry with original identities or remove unused owned objects. | Allocate another prefix because a response was lost. |
| After endpoint/data creation | Keep isolation, identify actual completed tasks and preserve owned data; resume or approve a data-safe removal. | Blindly destroy the stack to force a clean rerun. |
| After exposure or writes | Withdraw affected access, retain evidence and choose forward repair or recovery with the data owner. | Assume reverting Terraform state restores old infrastructure or old data. |
| During shared-service change | Coordinate consumer impact and retain an accepted previous service path where safe. | Delete shared domains or keys merely because one WSD failed. |

Post-activation verification checks the actual entry and reply path, not only the pre-activation internal fixture. An exposure change can alter DNS, NAT, load-balancer health or routing. Where public ingress is offered, use a separately approved PAZ test path and scope before production; the base fixture does not acquire public access merely to simplify testing.

Related engineering: [Expected traffic outcomes](../../engineering/fabric/3-worked-inter-zone-routing-and-enforcement-schedule.md#NET_s_003)  •  [Narrow service protocols](../../architecture/shared-services/2-name-time-initialization-and-telemetry-profiles.md#SVC_s_002)  •  [Activation evidence](../../assurance/site-qualification/5-qualification-stages-applicability-and-evidence.md#QUAL_s_005)

[Previous chapter](3-terraform-native-tools-and-operation-level-support.md) · [Chapter index](README.md) · [Next chapter](5-concurrency-ownership-and-failed-execution.md)

<!-- BEGIN GENERATED DECISION LINKS -->

## Related decision records

- [ADR-0015 — Build under deny and verify before and after activation](../../adr/0015-build-under-deny-and-verify-before-and-after-activation.md)
- [ADR-0020 — Use authoritative unique-by-default address allocation and controlled reuse](../../adr/0020-use-authoritative-unique-by-default-address-allocation-and-controlled-reuse.md)

<!-- END GENERATED DECISION LINKS -->
