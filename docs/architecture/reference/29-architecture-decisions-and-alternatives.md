# 29. Architecture decisions and alternatives

[Documentation home](../../README.md) · [Source document](../../../reference/Portable_Hosting_Delivery_Kits_v1_1/05_Reference_v1_4/00_Reference_Architecture_v1_4.docx) · [Chapter index](README.md)

> **Source:** RA — Draft v1.4. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: e50894d7f7b87cef50a283399b85925c8a96c5b9cd0428ce71ca0143d9be8d19 -->
<a id="__RefHeading___Toc3696_865363315"></a>
<a id="RA_s_029"></a>

The following decisions make the reference design specific without pretending to select an unknown site’s product versions or hardware counts. They are proposed for architecture adoption. Each implementation records acceptance or an explicit variation, its rationale and the controls and tests affected. The terms cell and work package are architecture concepts; they do not require corresponding software services.


<a id="source-table-404"></a>

| Decision | Selected baseline and rationale | Alternative and acceptance condition |
| --- | --- | --- |
| AD-01 — Infrastructure first | Describe components, connections and failure/authority boundaries before automation. Terraform implements that design. | Use existing delivery tools; no custom-controller project is required |
| AD-02 — Bounded cells | Scale through qualified platform capacity and explicit attachments rather than tenant-driven physical topology churn. | Small-site consolidation requires a documented isolation and recovery design |
| AD-03 — Native overlays | Vendor overlays remain local to their platform; controlled routed/security handoffs connect stacks. | Direct overlay federation requires an independently qualified interoperability architecture |
| AD-04 — Explicit ZIP edge | Routed stateful provider boundary with independent logical contexts is the default inter-domain pattern. | Distributed/native ZIP only with complete functional, authority and failure equivalence |
| AD-05 — Isolated attachments | Use independently isolated domain attachments; do not assume shared connected networks enforce separation. | Shared attachment only with direct-path, neighbour, NAT and failover proof |
| AD-06 — Zone-aware hosts | Retain zone-specific host-pool baseline and disclose HCI/storage/control sharing. | Alternative co-residency requires explicit security analysis and authorized variation |
| AD-07 — Management independence | Separate MZ semantics, platform control and OOB recovery transport. | A logically isolated shared transport cannot be labelled physically independent |
| AD-08 — Consumption endpoints | Shared services expose scoped data/service interfaces; management remains separately governed. | A shared backend is acceptable only with documented authorization and dependency boundaries |
| AD-09 — Site-local default | Use independent site domain instances and routed replication/recovery. | L2 stretch only for a demonstrated need with partition/fencing analysis |
| AD-10 — Persistent platform traffic | Storage replication and live mobility may be enduring provider transports; cross-domain migration grants are bounded. | Routing separation follows actual trust/forwarding need, not a functional name |
| AD-11 — Composite provisioning | Coordinate selected platform providers and shared infrastructure integrations with separate authority/state. | One module/provider cannot be assumed to provision every dependency |
| AD-12 — Explicit bootstrap boundary | Installers and supported hardware/platform lifecycle tools establish the APIs that declarative provisioning consumes. | Unsupported operations require a declared alternative, not a hidden no-op or unmanaged script |
| AD-13 — Safe activation | Default-deny infrastructure and mandatory services precede production exposure; verify after activation too. | A failed verification withdraws exposure while preserving owned data for recovery |
| AD-14 — Single configuration owner | One accountable controller/tool owns each native object; brownfield adoption is reviewed before mutation. | Ownership transfer requires explicit reconciliation and removal of dual writers |
| AD-15 — Evidence, not counts | Qualification depends on actual outcomes and current topology; page/schema/test counts are not security proof. | Reference documentation, live conformance and formal authorization remain distinct |

These decisions intentionally separate a stable target architecture from choices that belong in a low-level implementation. A permitted variation does not silently alter the common service promise. Where an alternative cannot satisfy the mandatory outcome, either exclude that service class or obtain an explicit change to the approved architecture and its assurance basis.

Related engineering: [GM §4 — Open decision package for implementation](../../assurance/gap-map/4-open-decision-package-for-implementation.md#GM_s_004)

[Previous chapter](28-architecture-acceptance-and-verification.md) · [Chapter index](README.md) · [Next chapter](30-implementation-handoff-and-delivery-sequence.md)

<!-- BEGIN GENERATED DECISION LINKS -->

## Related decision records

- [ADR-0003 — Let the infrastructure architecture lead the tooling](../../adr/0003-let-the-infrastructure-architecture-lead-the-tooling.md)
- [ADR-0006 — Use an explicit governed ZIP for inter-domain trust transitions](../../adr/0006-use-an-explicit-governed-zip-for-inter-domain-trust-transitions.md)

<!-- END GENERATED DECISION LINKS -->
