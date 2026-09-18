# v1.4 — Connected infrastructure design and acceptance

[Documentation home](../../README.md) · [Source document](../../../reference/Portable_Hosting_Delivery_Kits_v1_1/05_Reference_v1_4/01_Gap_Map_and_Decision_Register_v1_4.docx) · [Chapter index](README.md)

> **Source:** GM — Draft v1.4. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: 26dbaac8c13797b58ca5d057f76df8b3da63ec3f4b336036f18f5c6902512207 -->
<!-- SOURCE-BLOCK GM:270 BEGIN -->

<a id="__RefHeading___Toc5184_1692646980"></a>
<a id="V14_GM_REVISION"></a>

<!-- SOURCE-BLOCK GM:270 END -->

<!-- SOURCE-BLOCK GM:271 BEGIN -->

## v1.4 gap treatment and acceptance correction

<!-- SOURCE-BLOCK GM:271 END -->

<!-- SOURCE-BLOCK GM:272 BEGIN -->

The v1.4 progress register adds G35–G40 and retains the G01–G34 history. The additions address acceptance dependency, connected design schedules, shared-service return routing, test-resource accounting, effective mandatory-policy ownership and layer-consistent capacity/MTU arithmetic. They distinguish authored documentation from open site choices and not-run infrastructure verification. Gate IDs describe decision types, not a sequence allowing production activation before required operating and recovery readiness.

<!-- SOURCE-BLOCK GM:272 END -->

<!-- SOURCE-BLOCK GM:273 BEGIN -->

Authoritative linked treatment: [WD — Worked Infrastructure Design, Build Schedules and Acceptance](../../solutions/internal-protected-workload/README.md#V14_WD_START)

<!-- SOURCE-BLOCK GM:273 END -->

<!-- SOURCE-BLOCK GM:274 BEGIN -->

Read this clarification with the original chapter. It does not create an exemption to an adopted requirement, waive a mandatory control, select an unknown site value or report a live test as passed.

<!-- SOURCE-BLOCK GM:274 END -->

<!-- SOURCE-BLOCK GM:275 BEGIN -->


<a id="source-table-275"></a>

| New gap | Documentation treatment | Open closure evidence |
| --- | --- | --- |
| G35 — Production activation versus operational readiness | Clarified that applicable G4 readiness is a production prerequisite; restricted qualification is separately authorized. | Open: adopt actual gate owners, prerequisites and current evidence. Observed activation refusal when a required owner, recovery proof or authorization is missing. |
| G36 — No single connected design and build schedule | Added common component, address, route, service, native mapping and handoff schedules. | Open: bind actual site values and supported native objects. Accepted as-built schedules and matching actual forwarding and resource observations. |
| G37 — Shared-service return routing and transit risk | Specified dedicated service handoffs, service-side returns, endpoint entitlement and residual compromise risk. | Open: qualify EC/SE and service endpoint routing or an approved alternative. Positive replies and negative cross-tenant/provider-management paths in normal and fault states. |
| G38 — Fixture lacks a second same-domain endpoint | Added one sequential temporary probe and explicit peak resource accounting; no prohibited co-residency forced. | Open: authorize probe placement and execute applicable tests. Actual same-domain controls verified with healthy controls at allowed same-host and cross-host placements. |
| G39 — OpenStack mandatory policy left as an unspecified layer | Selected provider-owned mutation authority for the base service; delegation is separately qualified. | Open: implement and test actual Keystone/Neutron roles, APIs and protected policies. Tenant cannot widen effective permissions through groups, ports, external attachments or alternate paths. |
| G40 — Worked capacity and MTU units not tied to resources | Added guest resource demand, temporary probe peak and field-by-field MTU arithmetic with declared assumptions. | Open: replace examples with actual measured qualified surviving capacity and encapsulation. Unit-consistent admission and all-path packet-size evidence under the selected failure model. |

<!-- SOURCE-BLOCK GM:275 END -->

<!-- SOURCE-BLOCK GM:276 BEGIN -->

<!-- SOURCE-BLOCK GM:276 END -->

<!-- SOURCE-BLOCK GM:277 BEGIN -->

Code disambiguation: gap-priority P0/P1/P2 describes urgency. Provisioning work-package P0–P6 describes lifecycle scope. They are separate columns and must not be interpreted as the same sequence or authority.

<!-- SOURCE-BLOCK GM:277 END -->

[Previous chapter](06-references-parent-basis-and-external-context.md) · [Chapter index](README.md)
