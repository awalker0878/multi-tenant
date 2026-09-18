# 48. Architecture Review Checklist

[Documentation home](../../README.md) · [Source document](../../../reference/migration-source-documents/Handbook_v1_0.docx) · [Chapter index](README.md)

> **Source:** HB10 — Draft v1.0. Historical source; not the active design.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: 100c760003b9ff956ae369ece65c5ffe7736f6d481496d8df4c99dd6105d4190 -->

> **Historical only.** Use the [v1.4 reference architecture](../../architecture/reference/README.md) for the active design baseline. Conflicting historical text has not been silently reconciled.
<!-- SOURCE-BLOCK HB10:357 BEGIN -->

<!-- SOURCE-BLOCK HB10:357 END -->

<!-- SOURCE-BLOCK HB10:358 BEGIN -->

☐ Does the design use portable contract objects rather than vendor IDs in consumer-facing interfaces?

<!-- SOURCE-BLOCK HB10:358 END -->

<!-- SOURCE-BLOCK HB10:359 BEGIN -->

☐ Are tenant, WSD, Security Domain, and platform scopes distinct?

<!-- SOURCE-BLOCK HB10:359 END -->

<!-- SOURCE-BLOCK HB10:360 BEGIN -->

☐ Does every inter-zone path traverse a declared ZIP/security edge?

<!-- SOURCE-BLOCK HB10:360 END -->

<!-- SOURCE-BLOCK HB10:361 BEGIN -->

☐ Can any route leak, shared-services route, or alternate protocol bypass that edge?

<!-- SOURCE-BLOCK HB10:361 END -->

<!-- SOURCE-BLOCK HB10:362 BEGIN -->

☐ Is management/OOB separated from workload data paths?

<!-- SOURCE-BLOCK HB10:362 END -->

<!-- SOURCE-BLOCK HB10:363 BEGIN -->

☐ Can the design onboard a normal tenant without leaf/spine changes?

<!-- SOURCE-BLOCK HB10:363 END -->

<!-- SOURCE-BLOCK HB10:364 BEGIN -->

☐ Are Internet ingress and egress explicit service outcomes?

<!-- SOURCE-BLOCK HB10:364 END -->

<!-- SOURCE-BLOCK HB10:365 BEGIN -->

☐ Are shared services represented as bindings rather than broad routing?

<!-- SOURCE-BLOCK HB10:365 END -->

<!-- SOURCE-BLOCK HB10:366 BEGIN -->

☐ Are IP addresses allocated by authoritative IPAM?

<!-- SOURCE-BLOCK HB10:366 END -->

<!-- SOURCE-BLOCK HB10:367 BEGIN -->

☐ Are IPv4 and IPv6 treated equivalently?

<!-- SOURCE-BLOCK HB10:367 END -->

<!-- SOURCE-BLOCK HB10:368 BEGIN -->

☐ Are automation identities least privileged and separated by state/control domain?

<!-- SOURCE-BLOCK HB10:368 END -->

<!-- SOURCE-BLOCK HB10:369 BEGIN -->

☐ Are negative-path tests defined?

<!-- SOURCE-BLOCK HB10:369 END -->

<!-- SOURCE-BLOCK HB10:370 BEGIN -->

☐ Is failure behaviour fail-secure?

<!-- SOURCE-BLOCK HB10:370 END -->

<!-- SOURCE-BLOCK HB10:371 BEGIN -->

☐ Are capacity, HA and noisy-neighbour limits defined for security services?

<!-- SOURCE-BLOCK HB10:371 END -->

<!-- SOURCE-BLOCK HB10:372 BEGIN -->

☐ Does offboarding remove routes, policies, identities and evidence dependencies?

<!-- SOURCE-BLOCK HB10:372 END -->

[Previous chapter](47-operating-model-and-separation-of-duties.md) · [Chapter index](README.md) · [Next chapter](49-tenant-wsd-onboarding-checklist.md)
