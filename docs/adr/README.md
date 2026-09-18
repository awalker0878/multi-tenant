# Architecture decision register

Source-derived records remain Proposed until actual adoption is recorded. The structured registry is the canonical ADR authoring record; pages, indexes and crosswalks are rendered from it. No status is invented by generation or by a passing test.

| Record | Original identifier | Status | Accountable role |
|---|---|---|---|
| [ADR-0001 — Repository structure](0001-architecture-first-repository.md) | Repository convention | Proposed | Repository owner |
| [ADR-0002 — Markdown maintenance](0002-markdown-first-source-backed-documentation.md) | Editorial proposal | Proposed | Documentation owner |
| [ADR-0003 — Let the infrastructure architecture lead the tooling](0003-let-the-infrastructure-architecture-lead-the-tooling.md) | AD-01 | Proposed | Architecture authority / Automation platform |
| [ADR-0004 — Scale through commissioned hosting cells and capacity pools](0004-scale-through-commissioned-hosting-cells-and-capacity-pools.md) | AD-02 | Proposed | Architecture authority / Network engineering / Capacity management |
| [ADR-0005 — Keep vendor overlays local and connect through controlled handoffs](0005-keep-vendor-overlays-local-and-connect-through-controlled-handoffs.md) | AD-03 | Proposed | Platform engineering / Network engineering / Architecture authority |
| [ADR-0006 — Use an explicit governed ZIP for inter-domain trust transitions](0006-use-an-explicit-governed-zip-for-inter-domain-trust-transitions.md) | AD-04, DEV-ADR-01, RD14-01 | Proposed | Architecture authority / Security-edge operations / Security authority |
| [ADR-0007 — Allocate isolated domain attachments and qualify sharing](0007-allocate-isolated-domain-attachments-and-qualify-sharing.md) | AD-05 | Proposed | Network engineering / Security authority / Platform engineering |
| [ADR-0008 — Preserve zone-aware host placement and disclose every shared layer](0008-preserve-zone-aware-host-placement-and-disclose-every-shared-layer.md) | AD-06 | Proposed | Platform engineering / Architecture authority / Security authority |
| [ADR-0009 — Separate management security, platform control and OOB recovery](0009-separate-management-security-platform-control-and-oob-recovery.md) | AD-07 | Proposed | Architecture authority / Management operations / Identity operations |
| [ADR-0010 — Expose shared services through scoped consumption endpoints](0010-expose-shared-services-through-scoped-consumption-endpoints.md) | AD-08 | Proposed | Service operations / Architecture authority |
| [ADR-0011 — Default to site-local domains and routed recovery](0011-default-to-site-local-domains-and-routed-recovery.md) | AD-09 | Proposed | Platform engineering / Architecture authority / Recovery operations |
| [ADR-0012 — Distinguish persistent platform transports from temporary migration access](0012-distinguish-persistent-platform-transports-from-temporary-migration-access.md) | AD-10 | Proposed | Architecture authority / Migration owner |
| [ADR-0013 — Compose provisioning across separate platform and service authorities](0013-compose-provisioning-across-separate-platform-and-service-authorities.md) | AD-11 | Proposed | Automation platform |
| [ADR-0014 — Bootstrap management and trust before consuming native APIs](0014-bootstrap-management-and-trust-before-consuming-native-apis.md) | AD-12 | Proposed | Automation platform / Management operations / Continuity management |
| [ADR-0015 — Build under deny and verify before and after activation](0015-build-under-deny-and-verify-before-and-after-activation.md) | AD-13 | Proposed | Automation platform / Service management / Security authority |
| [ADR-0016 — Assign one authoritative writer per native object and sensitive subresource](0016-assign-one-authoritative-writer-per-native-object-and-sensitive-subresource.md) | AD-14, RD14-05 | Proposed | Automation platform / Service owner / Service management |
| [ADR-0017 — Separate reference adoption, technical qualification and authorization](0017-separate-reference-adoption-technical-qualification-and-authorization.md) | AD-15 | Proposed | Security authority / Assurance engineering / Delivery owner |
| [ADR-0018 — Separate tenant administration, WSD lifecycle and domain realization](0018-separate-tenant-administration-wsd-lifecycle-and-domain-realization.md) | Chapter-derived | Proposed | Architecture authority / Automation platform / Service owner |
| [ADR-0019 — Separate information impacts from service-level and recovery promises](0019-separate-information-impacts-from-service-level-and-recovery-promises.md) | Chapter-derived | Proposed | Security authority / Service owner / Continuity management |
| [ADR-0020 — Use authoritative unique-by-default address allocation and controlled reuse](0020-use-authoritative-unique-by-default-address-allocation-and-controlled-reuse.md) | Chapter-derived | Proposed | Network engineering / Automation platform |
| [ADR-0021 — Offer address families explicitly across the whole service path](0021-offer-address-families-explicitly-across-the-whole-service-path.md) | Chapter-derived | Proposed | Network engineering / Platform engineering |
| [ADR-0022 — Treat public access and egress as explicit service extensions](0022-treat-public-access-and-egress-as-explicit-service-extensions.md) | Chapter-derived | Proposed | Security-edge operations / Service owner |
| [ADR-0023 — Protect mandatory policy and identity selectors from tenant mutation](0023-protect-mandatory-policy-and-identity-selectors-from-tenant-mutation.md) | RD14-03 | Proposed | Platform engineering |
| [ADR-0024 — Use independent Nutanix VPC domain realizations with qualified handoffs](0024-use-independent-nutanix-vpc-domain-realizations-with-qualified-handoffs.md) | Chapter-derived | Proposed | Platform engineering |
| [ADR-0025 — Use isolated NSX upstream routing rather than a common unrestricted table](0025-use-isolated-nsx-upstream-routing-rather-than-a-common-unrestricted-table.md) | Chapter-derived | Proposed | Platform engineering |
| [ADR-0026 — Choose and own the actual OpenStack backend and domain boundaries](0026-choose-and-own-the-actual-openstack-backend-and-domain-boundaries.md) | Chapter-derived | Proposed | Platform engineering |
| [ADR-0027 — Separate virtual-disk, guest-data, replication and administration paths](0027-separate-virtual-disk-guest-data-replication-and-administration-paths.md) | Chapter-derived | Proposed | Storage operations |
| [ADR-0028 — Protect backup administration and prove isolated usable restore](0028-protect-backup-administration-and-prove-isolated-usable-restore.md) | Chapter-derived | Proposed | Backup operations / Continuity management |
| [ADR-0029 — Keep recovery trust material independent of the platform it unlocks](0029-keep-recovery-trust-material-independent-of-the-platform-it-unlocks.md) | Chapter-derived | Proposed | Identity operations / Security authority / Key-management operations |
| [ADR-0030 — Admit demand against every surviving-capacity bottleneck](0030-admit-demand-against-every-surviving-capacity-bottleneck.md) | Chapter-derived | Proposed | Capacity management / Service management / Service owner |
| [ADR-0031 — Discover uncertain native outcomes instead of blind replay or rollback](0031-discover-uncertain-native-outcomes-instead-of-blind-replay-or-rollback.md) | Chapter-derived | Proposed | Automation platform |
| [ADR-0032 — Keep incident containment above routine reconciliation](0032-keep-incident-containment-above-routine-reconciliation.md) | Chapter-derived | Proposed | Operations/SRE / Incident response |
| [ADR-0033 — Separate live-service retirement from retained-data disposal](0033-separate-live-service-retirement-from-retained-data-disposal.md) | Chapter-derived | Proposed | Service management / Data owner / Storage operations |
| [ADR-0034 — Classify change by architectural impact rather than file location](0034-classify-change-by-architectural-impact-rather-than-file-location.md) | Chapter-derived | Proposed | Change authority / Automation platform / Vulnerability management |
| [ADR-0035 — Make shared-service replies select the originating security context](0035-make-shared-service-replies-select-the-originating-security-context.md) | RD14-02 | Proposed | Service operations / Security authority / Network engineering |
| [ADR-0036 — Require initial operational and recovery readiness before production activation](0036-require-initial-operational-and-recovery-readiness-before-production-activation.md) | RD14-04 | Proposed | Service management / Service owner / Continuity management |
| [ADR-0037 — Keep attributable telemetry independent and define collection-loss behaviour](0037-keep-attributable-telemetry-independent-and-define-collection-loss-behaviour.md) | Chapter-derived | Proposed | Platform, telemetry and security service owners |
| [ADR-0038 — Govern image and privileged dependency provenance across their lifecycle](0038-govern-image-and-privileged-dependency-provenance-across-their-lifecycle.md) | Chapter-derived | Proposed | Platform/image, execution and supply-chain service owners |

## Authoring and acceptance

Edit `sources/documentation/adr_records.json`, then run `python scripts/build_documentation.py`. Accepted, Rejected and Superseded records require an actual deciding authority, date and evidence; rejection/supersession also needs rationale. Supersession references are reciprocal and cycle-free. Proposed records cannot claim acceptance. A status transition must be backed by the stated actual evidence; no record is automatically promoted.

[ADR template](template.md) · [Assertion-level allocation](../assurance/implementation-allocation.md)
