# 48. Architecture Review Checklist

[Documentation home](../../README.md) · [Source document](../../../reference/migration-source-documents/Handbook_v1_0.docx) · [Chapter index](README.md)

> **Source:** HB10 — Draft v1.0. Historical source; not the active design.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: 100c760003b9ff956ae369ece65c5ffe7736f6d481496d8df4c99dd6105d4190 -->

> **Historical only.** Use the [v1.4 reference architecture](../../architecture/reference/README.md) for the active design baseline. Conflicting historical text has not been silently reconciled.
☐ Does the design use portable contract objects rather than vendor IDs in consumer-facing interfaces?

☐ Are tenant, WSD, Security Domain, and platform scopes distinct?

☐ Does every inter-zone path traverse a declared ZIP/security edge?

☐ Can any route leak, shared-services route, or alternate protocol bypass that edge?

☐ Is management/OOB separated from workload data paths?

☐ Can the design onboard a normal tenant without leaf/spine changes?

☐ Are Internet ingress and egress explicit service outcomes?

☐ Are shared services represented as bindings rather than broad routing?

☐ Are IP addresses allocated by authoritative IPAM?

☐ Are IPv4 and IPv6 treated equivalently?

☐ Are automation identities least privileged and separated by state/control domain?

☐ Are negative-path tests defined?

☐ Is failure behaviour fail-secure?

☐ Are capacity, HA and noisy-neighbour limits defined for security services?

☐ Does offboarding remove routes, policies, identities and evidence dependencies?

[Previous chapter](47-operating-model-and-separation-of-duties.md) · [Chapter index](README.md) · [Next chapter](49-tenant-wsd-onboarding-checklist.md)
