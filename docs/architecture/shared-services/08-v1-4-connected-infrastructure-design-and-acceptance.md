# v1.4 — Connected infrastructure design and acceptance

[Documentation home](../../README.md) · [Source document](../../../reference/Portable_Hosting_Delivery_Kits_v1_1/05_Reference_v1_4/05_Shared_Services_Data_and_Recovery_v1_4.docx) · [Chapter index](README.md)

> **Source:** SVC — Draft v1.4. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: 2257e6f3badac48b07989244fbfae96643d68cc6633b28e9799a14733bccea3a -->
<a id="__RefHeading___Toc9353_1692646980"></a>
<a id="V14_SVC_REVISION"></a>

## Concrete provider-service boundary and residual risk

WD §§3–7 makes the provider service domain and dedicated tenant service handoffs explicit. Service endpoints have a supported return route through the originating tenant service-edge context. They do not become transit routers or acquire general reverse-session permission. Network controls do not eliminate the residual risk of a compromised shared resolver, collector or repository operating within its legitimate service permissions; service identities, resource entitlement, content/provenance checks and compromise response remain required. Virtual-disk key clients and backup API/data movers are designed separately from guest service access.

Authoritative linked treatment: [WD — Worked Infrastructure Design, Build Schedules and Acceptance](../../solutions/internal-protected-workload/README.md#V14_WD_START)

Read this clarification with the original chapter. It does not create an exemption to an adopted requirement, waive a mandatory control, select an unknown site value or report a live test as passed.

[Previous chapter](07-references-parent-basis-and-external-context.md) · [Chapter index](README.md)
