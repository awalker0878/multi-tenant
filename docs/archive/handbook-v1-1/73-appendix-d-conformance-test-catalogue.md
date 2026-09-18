# Appendix D — Conformance test catalogue

[Documentation home](../../README.md) · [Source document](../../../reference/migration-source-documents/Handbook_v1_1.docx) · [Chapter index](README.md)

> **Source:** HB11 — Draft v1.1. Historical source; not the active design.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: afbe9313dda4c68d5bb3af9ae6e9fcb5f098894c59e5f443270795bf2f9c21a1 -->

> **Historical only.** Use the [v1.4 reference architecture](../../architecture/reference/README.md) for the active design baseline. Conflicting historical text has not been silently reconciled.
<a id="__RefHeading___Toc13435_1645000677"></a>
<a id="app_D"></a>

All 80 entries are execution specifications. Result: NOT RUN for every infrastructure test in this release. Implement each procedure in an authorized target environment, bind exact versions and test-suite digest, record observed evidence, and assess the applicable profile. Local schema/package test results are reported separately and do not satisfy these infrastructure procedures.

<a id="test_CT_001"></a>

CT-001 — Cross-tenant IPv4 isolation

Preconditions: Two authorized test tenants; live endpoints and a same-tenant positive control.

Procedure: Probe disallowed TCP/UDP services in both directions, including same-host and different-host placements. Compare platform policy and edge telemetry.

Expected outcome: All unapproved flows are denied; positive controls succeed; no misleading pass caused by a dead endpoint.

Evidence: Probe results, endpoint health, routing/policy snapshots and attribution.

Mode: automated  \|  Cadence: qualification; security-significant change  \|  Execution: not-run

Requirement links: TEN-001, SDI-002, TEST-001, DEL-001

<a id="test_CT_002"></a>

CT-002 — Cross-tenant IPv6 isolation

Preconditions: IPv6-qualified test endpoints; both tenants have allocated prefixes.

Procedure: Repeat CT-001 over global/unique-local IPv6; inspect link-local exposure at each segment boundary.

Expected outcome: Unapproved IPv6 flows are denied without breaking required local IPv6 operation.

Evidence: IPv6 probes, neighbor state, policy and deny telemetry.

Mode: automated  \|  Cadence: qualification; security-significant change  \|  Execution: not-run

Requirement links: TEN-001, SDI-002, IPV6-001, IPV6-002, TEST-001

<a id="test_CT_003"></a>

CT-003 — Zone-boundary bypass prevention

Preconditions: Two distinct zone domains with one approved test flow.

Procedure: Inspect all native, static, policy-based and external-network paths; test same-host, cross-host and shared-attachment cases. Correlate the allowed flow at the declared logical ZIP.

Expected outcome: No undeclared path exists; allowed traffic is enforced by the ZIP realization; removing that authorization denies it.

Evidence: Topology graph, routes, packet-path or enforcement trace and policy digests.

Mode: automated  \|  Cadence: qualification; security-significant change  \|  Execution: not-run

Requirement links: ARCH-003, ZIP-001, ZIP-007, OVL-002, RTE-002, IPV6-002, NUT-002, NSX-002, NSX-003, TEST-001, MIG-002, DEL-001

<a id="test_CT_004"></a>

CT-004 — Infrastructure management isolation

Preconditions: Inventory of management APIs, BMCs, consoles, storage administration and backup administration.

Procedure: From test workloads, attempt the enumerated management endpoints over all enabled families. Separately verify approved management access.

Expected outcome: Workloads cannot access infrastructure management; dedicated authorized administration still works.

Evidence: Inventory coverage, negative probes and management access audit.

Mode: automated  \|  Cadence: qualification; security-significant change  \|  Execution: not-run

Requirement links: ARCH-004, MODEL-002, ZIP-004, MGT-001, MGT-005, BKP-001, DEL-001

<a id="test_CT_005"></a>

CT-005 — Default Internet denial

Preconditions: WSD has no egress Exposure; a provider-controlled external test endpoint is available.

Procedure: Attempt direct and proxy-mediated external access, including IPv6, alternate DNS and common tunnel paths allowed by the test plan.

Expected outcome: No unapproved egress succeeds; no default-route or NAT shortcut defeats policy.

Evidence: Route/NAT inventory, probes and egress logs.

Mode: automated  \|  Cadence: qualification; security-significant change  \|  Execution: not-run

Requirement links: EGR-001, OS-001

<a id="test_CT_006"></a>

CT-006 — Public ingress protection

Preconditions: Internal test service and a controlled external test client.

Procedure: Probe an internal workload directly, then exercise a separately approved PAZ ingress service.

Expected outcome: Direct exposure is denied; the approved ingress reaches only its declared backend and port.

Evidence: Exposure object, DNS/certificate records and ingress/backend traces.

Mode: automated  \|  Cadence: qualification; security-significant change  \|  Execution: not-run

Requirement links: ING-001, ING-002

<a id="test_CT_007"></a>

CT-007 — Approved stateful flow

Preconditions: Versioned FlowProfile and approved source/destination identities.

Procedure: Open the authorized application session and its reply path; test unsolicited reverse sessions and a nearby disallowed service.

Expected outcome: Intended request/reply works; reverse initiation is allowed only when separately declared.

Evidence: Flow intent, compiled rule and application-level probe results.

Mode: automated  \|  Cadence: each deployment; flow change  \|  Execution: not-run

Requirement links: ZIP-003, NSX-002, FLOW-001, TEST-001

<a id="test_CT_008"></a>

CT-008 — Service-binding scope

Preconditions: One bound and one unbound provider service endpoint.

Procedure: Exercise required DNS, time, identity or backup consumption; probe the rest of the service subnet and administrative interface.

Expected outcome: Only declared service endpoints/directions are reachable; consuming one service does not expose its subnet or management.

Evidence: Binding resolution, probes and service-side attribution.

Mode: automated  \|  Cadence: each deployment; binding change  \|  Execution: not-run

Requirement links: INV-004, MODEL-002, SVC-001, SVC-002, SVC-003, DEL-001

<a id="test_CT_009"></a>

CT-009 — Route-authority integrity

Preconditions: Approved route graph and realized routing snapshots.

Procedure: Compare imported/exported prefixes, defaults, next hops and BGP neighbors with the compiled plan; check recursive next-hop reachability and summaries.

Expected outcome: No unauthorized route or advertisement exists; summaries cannot expose excluded domains.

Evidence: Compiler output, RIB/FIB snapshots and semantic diff.

Mode: automated  \|  Cadence: qualification; security-significant change  \|  Execution: not-run

Requirement links: INV-003, RTE-001, RTE-002, RTE-003, RTE-004, FAB-002, EVPN-001, NSX-002, POL-002

<a id="test_CT_010"></a>

CT-010 — Security-event attribution

Preconditions: Central collector reachable and time synchronization healthy.

Procedure: Generate an allowed and denied flow plus an administrative change; find the correlated records centrally.

Expected outcome: Records identify tenant, WSD/domain, policy, actor, timestamp and deployment; timestamps satisfy the logging profile.

Evidence: Events, correlation query and collection-delay measurement.

Mode: automated  \|  Cadence: each deployment; scheduled synthetic  \|  Execution: not-run

Requirement links: EGR-002, OBS-001, OBS-002, OBS-003

<a id="test_CT_011"></a>

CT-011 — Control-plane loss

Preconditions: Approved isolated test environment; outage and restoration plan.

Procedure: Remove catalogue/controller or platform-management connectivity independently; observe existing enforcement and attempts to provision.

Expected outcome: Existing approved paths retain enforcement; new unsafe changes stop; recovery converges without bypass.

Evidence: Before/during/after policy snapshots, alerts and operation journal.

Mode: controlled-fault  \|  Cadence: qualification; relevant upgrade  \|  Execution: not-run

Requirement links: INV-007, AUTO-001, TEST-004, FAIL-001, FAIL-002

<a id="test_CT_012"></a>

CT-012 — Security-edge node failure

Preconditions: Measured production-like load within the selected profile; spare capacity available.

Procedure: Fail one edge node or its uplink under an approved test plan and measure sessions, drops, recovery and policy continuity.

Expected outcome: No unauthorized traffic is permitted; recovery and remaining capacity meet the accepted profile.

Evidence: Time-series traffic, failover timeline and enforcement traces.

Mode: controlled-fault  \|  Cadence: qualification; scheduled resilience exercise  \|  Execution: not-run

Requirement links: REL-001, REL-002, TEST-004, CAP-001, FAIL-001, FAIL-002

<a id="test_CT_013"></a>

CT-013 — Offboarding residuals

Preconditions: Disposable WSD, retention policy and resource graph recorded.

Procedure: Run retirement; query routes, policy, identities, addresses, DNS, certificates and storage/backup records by stable WSD ID.

Expected outcome: Active connectivity and grants are removed; retained copies are explicitly owned/locked; the tombstone explains every remaining object.

Evidence: Deletion ledger, scans, retention receipts and sanitization references.

Mode: automated  \|  Cadence: qualification; security-significant change  \|  Execution: not-run

Requirement links: IPAM-003, LIFE-001, LIFE-002, DEL-001

<a id="test_CT_014"></a>

CT-014 — Security drift detection

Preconditions: Non-production object with a known authorized baseline.

Procedure: Introduce a reversible out-of-band security change; observe detection, containment decision and reconciliation.

Expected outcome: Drift changes technical compliance status and alerts the owner; incident containment is not silently reverted.

Evidence: Drift event, policy generation and recovery journal.

Mode: controlled-fault  \|  Cadence: qualification; drift-engine change  \|  Execution: not-run

Requirement links: IMG-002, DRIFT-001, DRIFT-002

<a id="test_CT_015"></a>

CT-015 — Platform/provider upgrade regression

Preconditions: Exact old/new tuples, release notes and canary tenant.

Procedure: Run the applicable suite against the new tuple, including create/update/import/delete and failure paths; evaluate rollback or forward repair.

Expected outcome: No mandatory outcome regresses; the new certification is approved before broad placement.

Evidence: Tuple manifest, test reports, limitations and promotion decision.

Mode: automated  \|  Cadence: qualification; security-significant change  \|  Execution: not-run

Requirement links: PORT-001, QUAL-001, NUT-001, NUT-004, NSX-003, OS-003, FUT-001, TF-002, TEST-002, VULN-002

<a id="test_CT_016"></a>

CT-016 — Portable contract and object identity

Preconditions: Same versioned request and two independently qualified adapters.

Procedure: Validate stable consumer fields and compile for both targets; compare semantic outputs without requiring matching topology or vendor IDs.

Expected outcome: Equivalent mandatory intent is preserved; unsupported capabilities reject placement rather than silently degrade.

Evidence: Normalized requests, adapter plans and semantic comparison.

Mode: design-and-automated  \|  Cadence: qualification; contract change  \|  Execution: not-run

Requirement links: ARCH-001, INV-001, INV-005, REF-001, REF-002, WSD-002, OVL-001, PORT-003, API-001, TF-003, DEL-002

<a id="test_CT_017"></a>

CT-017 — Admission and authorization negatives

Preconditions: Schema/profile registry and scoped test identities.

Procedure: Submit unknown fields, unresolved profile versions, forged approval references, foreign-tenant references and consumer-supplied status.

Expected outcome: All invalid or unauthorized requests are rejected before any allocation or provider action.

Evidence: Admission decisions and zero-side-effect audit.

Mode: automated  \|  Cadence: each contract/policy change  \|  Execution: not-run

Requirement links: ARCH-001, CAT-001, CAT-002, MODEL-001, WSD-001, WSD-002, ZONE-001, API-002, API-003, POL-001, EXC-003, ONB-001

<a id="test_CT_018"></a>

CT-018 — Unsupported capability and expired certification

Preconditions: Candidate and expired platform profiles.

Procedure: Request dual-stack, inspection or dedicated placement on a profile lacking that qualified capability.

Expected outcome: Placement fails with an actionable capability reason; candidate/expired records cannot authorize production.

Evidence: Placement decisions, capability digests and status.

Mode: automated  \|  Cadence: each placement-engine change  \|  Execution: not-run

Requirement links: SCOPE-001, REF-002, CAT-002, SDI-003, OVL-001, IPV6-003, PLACE-001, PORT-001, PORT-002, QUAL-001, NUT-001, OS-003, FUT-001, FUT-002, ASSUR-002, ASSUR-003, TEST-002, ONB-001, ACPT-001

<a id="test_CT_019"></a>

CT-019 — Ownership, quota and separation of duties

Preconditions: Tenant quotas and identity/control-plane roles are defined.

Procedure: Test permitted workload operations and forbidden foundation/edge/profile edits; race two allocations against the same quota.

Expected outcome: Only allowed roles succeed; quota reservation is atomic; no resource is created above a hard entitlement.

Evidence: Authorization matrix, concurrent request results and allocation journal.

Mode: automated  \|  Cadence: qualification; security-significant change  \|  Execution: not-run

Requirement links: TEN-001, TEN-002, TEN-003, MGT-003, IAM-001, SVCM-001, NSX-001, OS-002, API-002, STATE-001, SEC-002, OPS-001, OPS-002

<a id="test_CT_020"></a>

CT-020 — Security-label integrity

Preconditions: Provider-owned selectors and tenant-editable labels are distinguishable.

Procedure: Attempt to add/remove security labels, impersonate another group or move a workload to a privileged selector.

Expected outcome: Tenant changes cannot expand effective permissions; mandatory policy precedence is preserved.

Evidence: RBAC results, label audit and effective-rule evaluation.

Mode: automated  \|  Cadence: qualification; security-significant change  \|  Execution: not-run

Requirement links: MICRO-002, MICRO-003, NUT-003, NSX-001, FLOW-001

<a id="test_CT_021"></a>

CT-021 — Same-domain east-west isolation

Preconditions: Two WSDs deliberately share one approved Security Domain Instance.

Procedure: Test same-subnet and cross-subnet traffic with and without explicit FlowIntent; verify traffic on one hypervisor as well as between hosts.

Expected outcome: Unapproved east-west communication is denied; allowed flows and required local services function.

Evidence: Enforcement location, probes and applied policy.

Mode: automated  \|  Cadence: qualification; security-significant change  \|  Execution: not-run

Requirement links: SDI-002, OVL-002, MICRO-001, MICRO-003, OS-001

<a id="test_CT_022"></a>

CT-022 — Spoofing and virtual NIC controls

Preconditions: Provider-approved packet tests on dedicated non-production endpoints.

Procedure: Exercise incorrect source addressing, unauthorized address pairs and additional NIC attachments within the bounded test plan.

Expected outcome: Source identities cannot impersonate another domain; platform exceptions have explicit owners and expiration.

Evidence: Port/NIC policy, bounded test output and exception records.

Mode: automated  \|  Cadence: qualification; security-significant change  \|  Execution: not-run

Requirement links: OVL-003, MICRO-003, OS-002, OS-003

<a id="test_CT_023"></a>

CT-023 — Shared edge-attachment isolation

Preconditions: Two domains use an intentionally shared provider attachment network.

Procedure: Exercise direct same-segment paths, ARP/ND interaction, external gateway routing and NAT hairpin in both directions.

Expected outcome: No path bypasses per-domain identity and ZIP enforcement; otherwise the shared attachment is ineligible.

Evidence: Attachment topology, neighbor state, routes and bidirectional probes.

Mode: automated  \|  Cadence: qualification; security-significant change  \|  Execution: not-run

Requirement links: ZIP-002, ZIP-007, OVL-002, RTE-002, RTE-004, EDGE-001, EDGE-002, NUT-002, NUT-004, OS-002

<a id="test_CT_024"></a>

CT-024 — Stateful symmetry and policy routing

Preconditions: Multiple eligible edge paths and asymmetric-failure scenario.

Procedure: Verify forward/return ownership before and during failover; change PBR to a permitted alternative in the test environment.

Expected outcome: Stateful enforcement remains correct; unsupported asymmetry is denied, not resolved by permissive bypass.

Evidence: Session traces, PBR precedence and HA counters.

Mode: automated  \|  Cadence: qualification; security-significant change  \|  Execution: not-run

Requirement links: RTE-004, EDGE-001, EDGE-002, EVPN-002, NUT-002, NSX-003, FAIL-001

<a id="test_CT_025"></a>

CT-025 — Zone adjacency and joint authority

Preconditions: Versioned zone graph and authority registry.

Procedure: Submit prohibited adjacencies, RZ public attachment, REZ without partner agreement, and a ZIP without both authority approvals.

Expected outcome: Invalid graphs are rejected; valid bindings resolve to the explicitly authorized adjacent domains.

Evidence: Graph decision report and approval provenance.

Mode: design-and-automated  \|  Cadence: each policy/profile change  \|  Execution: not-run

Requirement links: ARCH-003, INV-002, MODEL-001, SDI-001, SDI-004, ZONE-001, ZONE-002, ZIP-002, ZIP-003, SVC-002, ING-001, FAB-003, POL-001

<a id="test_CT_026"></a>

CT-026 — MZ, OOB and remote administration

Preconditions: Approved management architecture and recovery credentials.

Procedure: Trace remote privileged access through its authorized boundary; test workload isolation, ordinary browsing restriction and BMC access controls.

Expected outcome: MZ semantics and OOB transport remain distinct; only approved privileged paths reach management targets.

Evidence: Management diagrams, endpoint policy and session audit.

Mode: design-and-automated  \|  Cadence: qualification; management change  \|  Execution: not-run

Requirement links: ARCH-004, MODEL-002, TEN-002, ZIP-004, ZIP-005, MGT-001, MGT-002, MGT-005, IAM-002, FAB-004

<a id="test_CT_027"></a>

CT-027 — Break-glass and identity-provider loss

Preconditions: Approved emergency identity, dual-custodian procedure and test window.

Procedure: Make normal federation unavailable; exercise limited emergency access, alerting, revocation and post-use credential rotation.

Expected outcome: Access remains accountable and scoped; no shared anonymous administrator or permanent bypass is created.

Evidence: Emergency access log, custodial approval and revocation evidence.

Mode: controlled-fault  \|  Cadence: quarterly; identity change  \|  Execution: not-run

Requirement links: MGT-002, MGT-004, IAM-001, IAM-002, SEC-003, FAIL-002, FAIL-003

<a id="test_CT_028"></a>

CT-028 — Workload identity and certificate lifecycle

Preconditions: Scoped service identity, trusted CA and rotatable certificate.

Procedure: Rotate credentials/certificates; revoke the old identity and test an expired/untrusted certificate.

Expected outcome: Approved service continues with new material; old/revoked credentials are unusable within the accepted propagation interval.

Evidence: Issuer records, endpoint TLS results and revocation timeline.

Mode: automated  \|  Cadence: qualification; security-significant change  \|  Execution: not-run

Requirement links: SVC-003, IAM-001, IAM-003, CRY-001, CRY-003, SEC-003

<a id="test_CT_029"></a>

CT-029 — IPAM concurrency, overlap and exhaustion

Preconditions: Small disposable address pool and approved overlap policy.

Procedure: Issue concurrent allocations, exhaust the pool, retry requests and request a conflicting prefix.

Expected outcome: One authoritative reservation per allocation; retries are idempotent; exhaustion/unauthorized overlap stops provisioning.

Evidence: Allocation ledger, request IDs and conflict decisions.

Mode: automated  \|  Cadence: qualification; security-significant change  \|  Execution: not-run

Requirement links: IPAM-001, IPAM-002, IPAM-004, AUTO-001

<a id="test_CT_030"></a>

CT-030 — DNS/DHCP lifecycle and reuse

Preconditions: Forward/reverse zones, address lease policy and reusable test address.

Procedure: Provision, rename, recover and retire a network endpoint; confirm lease/DNS reconciliation and address quarantine.

Expected outcome: No duplicate active ownership or premature reuse; stale records disappear within the approved timing profile.

Evidence: DNS/DHCP/IPAM timelines and ownership comparisons.

Mode: automated  \|  Cadence: qualification; security-significant change  \|  Execution: not-run

Requirement links: IPAM-001, IPAM-003, IPAM-004

<a id="test_CT_031"></a>

CT-031 — IPv6 local control and IPv4-only posture

Preconditions: Platform offers either a dual-stack or explicit IPv4-only profile.

Procedure: Check router advertisements, neighbor discovery, DHCPv6, source validation and unapproved transition paths; preserve required ICMPv6.

Expected outcome: No alternate-protocol bypass; enabled IPv6 works correctly and disabled service does not create ungoverned reachability.

Evidence: Protocol-specific controls, probes and qualification result.

Mode: automated  \|  Cadence: qualification; security-significant change  \|  Execution: not-run

Requirement links: RTE-004, IPV6-001, IPV6-002, IPV6-003

<a id="test_CT_032"></a>

CT-032 — MTU and path-MTU discovery

Preconditions: Known encapsulation stack and both local/remote paths.

Procedure: Test supported workload packet sizes end-to-end, including security edge, nested overlay if offered and recovery site.

Expected outcome: Accepted MTU is reachable without silent black holes; required PMTU feedback is delivered or a documented alternative works.

Evidence: Packet-size matrix, encapsulation budget and loss traces.

Mode: automated  \|  Cadence: qualification; security-significant change  \|  Execution: not-run

Requirement links: IPV6-001, IPV6-003, EDGE-001, FAB-004, EVPN-002

<a id="test_CT_033"></a>

CT-033 — BGP and EVPN import/export boundaries

Preconditions: Provider-owned non-production peers and known approved routes.

Procedure: Validate neighbor authentication/control-plane limits; advertise bounded unauthorized test prefixes/route targets through the test fixture.

Expected outcome: Only authorized advertisements install; route leaks, excess prefixes and unapproved defaults are rejected and alerted.

Evidence: Neighbor config, route-policy results and RIB/FIB diff.

Mode: automated  \|  Cadence: qualification; security-significant change  \|  Execution: not-run

Requirement links: INV-003, RTE-001, FAB-004, EVPN-001

<a id="test_CT_034"></a>

CT-034 — Leaf/link and multihoming failures

Preconditions: Approved MLAG or EVPN multihoming profile; topology-specific rollback.

Procedure: Fail an uplink, peer link, keepalive or Ethernet-segment member individually, then restore it; test split-brain containment.

Expected outcome: No loop, unintended duplicate forwarding or security bypass; measured convergence meets the fabric profile.

Evidence: Fault timeline, MAC/route state, packet-loss and control-plane telemetry.

Mode: controlled-fault  \|  Cadence: qualification; fabric upgrade  \|  Execution: not-run

Requirement links: FAB-004, EVPN-002, TEST-004

<a id="test_CT_035"></a>

CT-035 — Compute co-residency and evacuation

Preconditions: Placement policy names tenant/domain/zone host-sharing boundaries.

Procedure: Attempt disallowed placement and evacuate a host; repeat after a scheduler restart.

Expected outcome: Placement, migration and HA restart all preserve the approved co-residency rules; insufficient eligible capacity rejects the action.

Evidence: Scheduler decisions, host inventory and policy references.

Mode: automated  \|  Cadence: qualification; security-significant change  \|  Execution: not-run

Requirement links: THR-001, SDI-001, SDI-003, SDI-004, ZIP-005, SITE-004, CMP-001, CMP-003, PLACE-001, FUT-003, ASSUR-001, ASSUR-002

<a id="test_CT_036"></a>

CT-036 — Hypervisor and firmware baseline

Preconditions: Supported hardware/software tuple and security baseline.

Procedure: Verify secure boot/attestation where required, disabled unnecessary services, administrative separation and inventory of firmware/drivers.

Expected outcome: All mandatory baseline items are enforced; unsupported or unattested hosts are ineligible for the affected profile.

Evidence: Baseline report, attestation/config output and exception ledger.

Mode: design-and-automated  \|  Cadence: qualification; host onboarding; scheduled  \|  Execution: not-run

Requirement links: CMP-002, IMG-001, IMG-002

<a id="test_CT_037"></a>

CT-037 — Storage tenant isolation

Preconditions: Two tenants with block/file/object resources and separate access identities.

Procedure: Attempt foreign volume attachment, snapshot clone, file access and object access; include backup/export paths.

Expected outcome: Only the owning or explicitly authorized scope accesses data; no clone or mount circumvents zone/categorization policy.

Evidence: API decisions, storage ACLs and data-path tests.

Mode: automated  \|  Cadence: qualification; security-significant change  \|  Execution: not-run

Requirement links: SVC-001, STO-001, FUT-003, ASSUR-002

<a id="test_CT_038"></a>

CT-038 — Encryption, key isolation and KMS outage

Preconditions: Qualified cryptographic profile; disposable encrypted data and test key.

Procedure: Validate encryption context and key-use permissions; rotate a test key and remove KMS connectivity under the approved runbook.

Expected outcome: No unauthorized decrypt or plaintext fallback; documented cache/restart behavior matches policy; recovery preserves authorized data.

Evidence: Crypto configuration, key audit, outage timeline and recovery test.

Mode: controlled-fault  \|  Cadence: qualification; key-service change  \|  Execution: not-run

Requirement links: SITE-004, CRY-001, CRY-002, CRY-003, BKP-004, FAIL-002, FAIL-003

<a id="test_CT_039"></a>

CT-039 — Storage performance and contention

Preconditions: Defined capacity/latency/throughput class and bounded load generators.

Procedure: Measure steady load, contention and rebuild/degraded state with the same workload data pattern.

Expected outcome: Class limits and protected minimums hold under the accepted failure budget; overload rejects growth rather than bypassing controls.

Evidence: Latency percentiles, IOPS/throughput, capacity and noisy-neighbor results.

Mode: automated  \|  Cadence: qualification; security-significant change  \|  Execution: not-run

Requirement links: CMP-002, STO-002, REL-002, CAP-002

<a id="test_CT_040"></a>

CT-040 — Golden image provenance

Preconditions: Approved image digest, build manifest and denied image fixture.

Procedure: Verify signature/provenance, scan status, boot mode and hardening; attempt deployment of retired/tampered images.

Expected outcome: Only eligible images deploy; exceptions are explicit; rebuild output links to its source and component inventory.

Evidence: Image manifest, signature validation, scan and admission decisions.

Mode: automated  \|  Cadence: qualification; security-significant change  \|  Execution: not-run

Requirement links: IMG-001, IMG-002, VULN-002

<a id="test_CT_041"></a>

CT-041 — Patch and vulnerability lifecycle

Preconditions: Inventory, severity policy and an approved non-production patch scenario.

Procedure: Create a finding, classify exposure, execute canary remediation, verify fix and record time against the selected deadline.

Expected outcome: No asset or firmware layer is omitted; overdue risk escalates; roll-forward/rollback preserves service and security.

Evidence: Finding-to-change-to-verification chain and deadline report.

Mode: automated  \|  Cadence: qualification; security-significant change  \|  Execution: not-run

Requirement links: IMG-001, SUP-001, VULN-001, VULN-002

<a id="test_CT_042"></a>

CT-042 — Supply-chain and package provenance

Preconditions: Approved provider/module mirror and a tampered package fixture.

Procedure: Verify package checksums, immutable module references and execution image; test rejection of an unapproved provider/module source.

Expected outcome: Tampered/unapproved artifacts never reach a privileged apply; lockfile changes require reviewed provenance.

Evidence: Package manifests, verification output and CI policy decision.

Mode: automated  \|  Cadence: qualification; security-significant change  \|  Execution: not-run

Requirement links: TF-001, TF-002, TF-005, CICD-002, SUP-001, VULN-001, VULN-002

<a id="test_CT_043"></a>

CT-043 — Terraform plan and state confidentiality

Preconditions: Disposable secrets and restricted plan/state storage.

Procedure: Inspect source, logs, binary/JSON plan and state using controlled test values; verify supported ephemeral/write-only behavior.

Expected outcome: Secrets are absent where promised; unavoidable secret-bearing artifacts remain encrypted, access-controlled and redacted from logs.

Evidence: Secret-handling scan, backend ACLs and artifact classification.

Mode: automated  \|  Cadence: qualification; security-significant change  \|  Execution: not-run

Requirement links: TF-001, STATE-002, SEC-001, SEC-003, SEC-004

<a id="test_CT_044"></a>

CT-044 — State locking, recovery and grants

Preconditions: Two authorized runners, versioned state and documented lock recovery.

Procedure: Race updates to one state, restore a known state version in isolation and test a workload runner against foundation state.

Expected outcome: Only one writer operates; restore is auditable; unauthorized state reads/writes fail; state rollback is not misrepresented as resource rollback.

Evidence: Lock timeline, recovery report and access decisions.

Mode: automated  \|  Cadence: qualification; security-significant change  \|  Execution: not-run

Requirement links: MGT-003, TF-003, TF-004, STATE-001, STATE-002, STATE-003, SEC-002, SEC-004, FAIL-003

<a id="test_CT_045"></a>

CT-045 — Partial apply and compensation

Preconditions: Disposable multi-stage deployment and a failure-injection point.

Procedure: Interrupt after allocation or one provider action; restart with the same operation ID and observe discovery/repair.

Expected outcome: No duplicate allocation or accidental destruction; unfinished resources remain quarantined; the journal supports safe resume or controlled compensation.

Evidence: Operation journal, state generations and residual-resource scan.

Mode: controlled-fault  \|  Cadence: controller/adapter change  \|  Execution: not-run

Requirement links: INV-007, IPAM-004, NUT-004, AUTO-001, AUTO-002, AUTO-003, STATE-003

<a id="test_CT_046"></a>

CT-046 — Retries, optimistic concurrency and idempotency

Preconditions: Controller accepts request ID and expected resource generation.

Procedure: Replay an operation, submit stale updates, and interrupt response delivery after successful allocation.

Expected outcome: Replay returns the existing operation; stale updates conflict; one desired generation yields one accountable realization.

Evidence: API responses, generation history and allocation counts.

Mode: automated  \|  Cadence: each controller change  \|  Execution: not-run

Requirement links: IPAM-004, API-003, AUTO-002, AUTO-003

<a id="test_CT_047"></a>

CT-047 — API rate limit and backpressure

Preconditions: Finite controller queue and test provider throttling.

Procedure: Increase authorized test demand to the configured limit; inject retryable throttling/timeouts and permanent errors.

Expected outcome: Backpressure is visible and bounded; retry honors policy/jitter; permanent errors do not loop indefinitely or consume unbounded capacity.

Evidence: Queue metrics, retries, deadlines and final operation states.

Mode: automated  \|  Cadence: qualification; security-significant change  \|  Execution: not-run

Requirement links: AUTO-003, CAP-002

<a id="test_CT_048"></a>

CT-048 — Approved-plan freshness

Preconditions: Signed plan, immutable inputs and an intervening policy or state change.

Procedure: Change state generation, policy bundle or approval-sensitive intent after planning; try to apply the old artifact.

Expected outcome: Stale/unapproved plans are rejected and replanned; approved artifacts bind source, inputs, policy, identity and expiration.

Evidence: Plan digest, approvals and rejected apply audit.

Mode: automated  \|  Cadence: qualification; security-significant change  \|  Execution: not-run

Requirement links: SDI-004, POL-002, AUTO-002, TF-002, TF-005, CICD-001, CICD-002, EVID-002

<a id="test_CT_049"></a>

CT-049 — Evidence integrity and authorization separation

Preconditions: Signed evidence manifest and separately signed authorization decision.

Procedure: Tamper with an artifact; expire a decision; fail a technical test while preserving the historical authorization record.

Expected outcome: Tampering is detected; technical status never self-issues authorization; readiness follows current evidence and decision conditions.

Evidence: Digests/signature checks, readiness evaluation and decision history.

Mode: automated  \|  Cadence: qualification; security-significant change  \|  Execution: not-run

Requirement links: INV-006, AUTH-001, DRIFT-001, TEST-003, EVID-001, EVID-002, EVID-003, OBS-001, IR-002, ONB-001, ACPT-001

<a id="test_CT_050"></a>

CT-050 — Telemetry outage, buffering and retention

Preconditions: Logging profile specifies export latency, buffer limits and retention/disposal policy.

Procedure: Disconnect the collector; generate bounded events; restore connectivity and reconcile sequence/time gaps.

Expected outcome: Loss/overflow is alerted; buffering behavior matches profile; mandatory evidence gaps are visible; no silent control bypass.

Evidence: Buffer metrics, event reconciliation and retention configuration.

Mode: controlled-fault  \|  Cadence: qualification; logging change  \|  Execution: not-run

Requirement links: OBS-002, OBS-003, FAIL-002, FAIL-003

<a id="test_CT_051"></a>

CT-051 — Backup administrative separation and immutability

Preconditions: Test backup policy includes an isolated locked copy.

Procedure: Try deletion or retention reduction with production and backup-operator identities; test approved custodial operations separately.

Expected outcome: Compromised production authority cannot alter the protected copy or its retention; authorized actions are separately accountable.

Evidence: Role tests, object-lock/immutability configuration and audit.

Mode: automated  \|  Cadence: qualification; security-significant change  \|  Execution: not-run

Requirement links: BKP-001, BKP-003, BKP-004

<a id="test_CT_052"></a>

CT-052 — Application-consistent isolated restore

Preconditions: Known application dataset, consistency markers and accepted RTO/RPO.

Procedure: Restore to an isolated recovery domain; verify integrity, application start and required dependencies before controlled reconnection.

Expected outcome: Recovered data meets consistency/RPO and recovery timing; no production connection appears until authorized.

Evidence: Recovery timestamps, integrity markers, application checks and isolation probes.

Mode: controlled-recovery  \|  Cadence: quarterly; material application change  \|  Execution: not-run

Requirement links: SITE-003, STO-002, BKP-002, BKP-003, REL-001, FAIL-001, REC-001, REC-002, DEL-001

<a id="test_CT_053"></a>

CT-053 — Backup retention, holds and key survival

Preconditions: A test hold, expiring backup and keys needed by retained copies.

Procedure: Retire the WSD while retaining the held copy; attempt key deletion and validate an authorized restore of retained data.

Expected outcome: Hold and retention are enforced; key lifetime supports required recovery; data is not prematurely destroyed.

Evidence: Hold/retention decision, key dependencies and restore evidence.

Mode: automated  \|  Cadence: qualification; security-significant change  \|  Execution: not-run

Requirement links: STO-001, STO-003, CRY-002, BKP-003, BKP-004, LIFE-002, LIFE-003

<a id="test_CT_054"></a>

CT-054 — Site loss, fencing and failback

Preconditions: Two qualified sites; isolated exercise scope and owner-approved recovery plan.

Procedure: Declare simulated primary loss, fence writers, restore/promote at recovery site, verify DNS/identity/policy, then perform controlled failback.

Expected outcome: No split-brain or policy relaxation; measured RTO/RPO and data ownership match the recovery profile.

Evidence: Failure timeline, fencing proof, replication checkpoints and end-to-end tests.

Mode: controlled-recovery  \|  Cadence: qualification; scheduled recovery exercise  \|  Execution: not-run

Requirement links: SITE-001, SITE-002, SITE-003, SITE-004, BKP-002, REL-001, REL-002, TEST-004, FAIL-002, FAIL-003, REC-001, REC-002, MIG-003

<a id="test_CT_055"></a>

CT-055 — Management/control-plane bootstrap recovery

Preconditions: Offline recovery manifest and independent access to state, DNS/time, trust and keys.

Procedure: Recover essential management/controller services in the documented dependency order in an isolated environment.

Expected outcome: Recovery does not require the unavailable production service it is restoring; credentials and old state remain accountable.

Evidence: Dependency graph, recovery steps, integrity checks and measured recovery time.

Mode: controlled-recovery  \|  Cadence: annual; foundation redesign  \|  Execution: not-run

Requirement links: MGT-005, SITE-001, CRY-003, STATE-002, FAIL-002, FAIL-003, REC-001, REC-002

<a id="test_CT_056"></a>

CT-056 — Resource and address capacity exhaustion

Preconditions: Hard quotas, reservations and admission thresholds.

Procedure: Exhaust test compute/storage/edge context/address capacity, then request both ordinary and dedicated service classes.

Expected outcome: Requests stop with an explicit reason; required HA/security headroom is not consumed or silently weakened.

Evidence: Reservation ledger, rejected decisions and remaining-headroom report.

Mode: automated  \|  Cadence: qualification; security-significant change  \|  Execution: not-run

Requirement links: CMP-001, REL-002, PLACE-001, SVCM-001, CAP-001, CAP-002

<a id="test_CT_057"></a>

CT-057 — Incident quarantine and reconciler precedence

Preconditions: Scoped incident role and expiring emergency override.

Procedure: Quarantine one WSD, remove exposure and run normal reconciliation; test unaffected tenants.

Expected outcome: Containment persists under higher-priority incident policy until released; unrelated tenants remain available.

Evidence: Override object, effective policy, reconciliation audit and tenant probes.

Mode: controlled-fault  \|  Cadence: quarterly; containment change  \|  Execution: not-run

Requirement links: TEN-003, SUP-001, DRIFT-001, DRIFT-002, DRIFT-003, IR-001, IR-002

<a id="test_CT_058"></a>

CT-058 — Exception approval and expiry

Preconditions: Versioned exception with risk owner, affected requirement and end time.

Procedure: Test unapproved, expired and valid exceptions; expire one during a running operation.

Expected outcome: No unapproved exception grants access; expiry changes posture and triggers the documented action without indiscriminate destruction.

Evidence: Approval records, admission results and expiry event.

Mode: automated  \|  Cadence: each policy/controller change  \|  Execution: not-run

Requirement links: RTE-003, CICD-001, DRIFT-003, ASSUR-003, EVID-003, IR-002, MIG-001, EXC-001, EXC-002, EXC-003

<a id="test_CT_059"></a>

CT-059 — Data sanitization and resource reuse

Preconditions: Disposable data, snapshot/clone inventory and approved media method.

Procedure: Retire the storage object, verify retained copies, sanitize according to the approved method and allocate to another test tenant.

Expected outcome: New tenant cannot recover prior data; retained evidence identifies method, scope, exceptions and all surviving copies.

Evidence: Sanitization receipt, reuse test and copy/dependency ledger.

Mode: design-and-automated  \|  Cadence: qualification; storage lifecycle change  \|  Execution: not-run

Requirement links: STO-003, CRY-002, FUT-003, LIFE-001, LIFE-002, LIFE-003

<a id="test_CT_060"></a>

CT-060 — Portability and exit rehearsal

Preconditions: Two target profiles plus an exit manifest containing data and application dependencies.

Procedure: Export/rebuild the workload, convert only supported formats, import data and rebind identity/network/keys; run functional and security checks.

Expected outcome: Consumer semantics survive; downtime, data loss, format limitations and cost drivers are recorded; no untested live-migration claim.

Evidence: Exit manifest, conversion logs, reconciliation report and conformance results.

Mode: controlled-recovery  \|  Cadence: qualification; annual representative rehearsal  \|  Execution: not-run

Requirement links: INV-005, REF-001, STO-002, PLACE-003, PORT-003, REC-002, MIG-001, MIG-002, MIG-003, DEL-002

<a id="test_CT_061"></a>

CT-061 — Location, privacy and support access

Preconditions: PlacementProfile states permitted data, backup, telemetry, key and administrative locations.

Procedure: Compare all components and support paths to those constraints; test a placement or support session outside allowed scope.

Expected outcome: Nonconforming placement/access is rejected; exceptions require the designated authority; residency is not asserted to settle jurisdiction.

Evidence: Location inventory, access logs and approval decisions.

Mode: design-and-automated  \|  Cadence: qualification; provider/location change  \|  Execution: not-run

Requirement links: IPAM-002, SITE-004, PLACE-001, PLACE-002, PORT-002

<a id="test_CT_062"></a>

CT-062 — Shared responsibility and control inheritance

Preconditions: System control profile, service ownership and inheritance declarations.

Procedure: For each applicable control, identify provider, tenant or shared implementation, evidence and unresolved dependency.

Expected outcome: No control is ownerless; inherited evidence is scoped, current and accepted; gaps block required readiness.

Evidence: Control allocation matrix and assessor review.

Mode: manual-review  \|  Cadence: onboarding; major change; periodic review  \|  Execution: not-run

Requirement links: SCOPE-001, STD-001, STD-002, CAT-001, THR-001, WSD-003, CMP-003, REL-001, SVCM-001, RESP-001, ASSUR-001, ASSUR-002, OPS-001, OPS-002, EXC-001, ONB-001, ACPT-001

<a id="test_CT_063"></a>

CT-063 — Public certificate and trusted proxy identity

Preconditions: Approved ingress with backend encryption and trusted proxy policy.

Procedure: Rotate the certificate, test expiry/incorrect hostname and submit forged client-identity headers through the controlled test client.

Expected outcome: TLS identity is validated; backend trust is explicit; untrusted headers cannot impersonate the originating client.

Evidence: TLS checks, proxy policy and attributed requests.

Mode: automated  \|  Cadence: qualification; security-significant change  \|  Execution: not-run

Requirement links: ING-002, EXP-001, CRY-001

<a id="test_CT_064"></a>

CT-064 — Egress policy and service-specific protocols

Preconditions: Approved egress service includes protocol, destination and DNS resolution policy.

Procedure: Test permitted and nearby disallowed destinations; verify NAT identity logs and stateful return traffic.

Expected outcome: Only approved egress semantics work; DNS/FQDN changes cannot silently widen policy; NAT is not treated as a security control by itself.

Evidence: Egress rules, DNS resolution history, NAT mappings and probes.

Mode: automated  \|  Cadence: qualification; security-significant change  \|  Execution: not-run

Requirement links: EGR-001, EGR-002

<a id="test_CT_065"></a>

CT-065 — Privileged workload and container isolation

Preconditions: A container/bare-metal profile with explicit isolation capabilities.

Procedure: Test namespace/project boundaries, node access, privileged workloads and host-network access against the approved baseline.

Expected outcome: Unapproved privilege escalation or host access is denied; namespace alone is not accepted as a qualified zone boundary.

Evidence: Admission/RBAC policy, runtime posture and cross-scope tests.

Mode: automated  \|  Cadence: qualification; security-significant change  \|  Execution: not-run

Requirement links: MICRO-003, FUT-001, FUT-002, FUT-003

<a id="test_CT_066"></a>

CT-066 — Policy precedence and immutable baseline

Preconditions: Mandatory provider rules plus lower-priority tenant and service rules.

Procedure: Compile overlapping allow/deny intents and update membership while a test workload is running.

Expected outcome: Mandatory denies cannot be overridden by tenant policy; membership changes do not create a transient unrestricted interval.

Evidence: Effective-rule order, membership transitions and timed probes.

Mode: automated  \|  Cadence: qualification; security-significant change  \|  Execution: not-run

Requirement links: ZONE-002, ZIP-003, OVL-003, MICRO-001, MICRO-002, NUT-003, NSX-001, OS-001, POL-001, POL-002, FLOW-001, DRIFT-003, IR-002

<a id="test_CT_067"></a>

CT-067 — ZIP sensors, heightened posture and authority

Preconditions: ZIP profile identifies both zone authorities, inspection/sensor policy and heightened mode.

Procedure: Verify access-control and telemetry placement; activate heightened posture, test essential flows and restore under approved authority.

Expected outcome: Posture change restricts intended flows, preserves declared essentials, and leaves a complete joint-authority record.

Evidence: ZIP profile, sensor coverage, change approval and test traces.

Mode: automated  \|  Cadence: qualification; security-significant change  \|  Execution: not-run

Requirement links: ZIP-006, IR-001

<a id="test_CT_068"></a>

CT-068 — Time synchronization and correlation

Preconditions: Approved independent time sources and skew threshold.

Procedure: Measure time across hosts, controllers, edge and collectors; introduce bounded skew in a disposable node.

Expected outcome: Excess skew is detected; certificate/evidence validation follows defined failure behavior; record ordering remains explainable.

Evidence: Skew metrics, alerts and signed/ordered event samples.

Mode: automated  \|  Cadence: qualification; security-significant change  \|  Execution: not-run

Requirement links: OBS-003

<a id="test_CT_069"></a>

CT-069 — Technical readiness gate

Preconditions: Healthy and deliberately failed evidence fixtures at the same desired generation.

Procedure: Evaluate readiness with missing/expired evidence, unsupported capability, unresolved owner and absent authorization.

Expected outcome: Service Ready is false unless every mandatory condition for the current generation is satisfied.

Evidence: Condition evaluation, policy version and blocked exposure events.

Mode: automated  \|  Cadence: each controller/policy change  \|  Execution: not-run

Requirement links: INV-006, AUTH-001, CAT-001, WSD-003, OVL-003, EXP-001, RESP-001, QUAL-001, AUTO-002, ASSUR-003, TEST-003, EVID-001, EVID-002, EVID-003, OPS-002, EXC-002, EXC-003, ONB-001, DEL-001, ACPT-001

<a id="test_CT_070"></a>

CT-070 — Contract upgrades and deletion finalizers

Preconditions: Objects at old schema version; shared domain has two dependent WSDs.

Procedure: Convert schema with explicit defaults; delete one WSD; test removal with outstanding retention/evidence finalizers.

Expected outcome: No silent security expansion; shared resources survive while referenced; deletion cannot bypass approved finalizers.

Evidence: Conversion diff, ownership graph and tombstones.

Mode: automated  \|  Cadence: contract/lifecycle engine change  \|  Execution: not-run

Requirement links: INV-001, MODEL-001, TEN-003, WSD-001, API-001, API-003, TF-004, STATE-003, LIFE-001, LIFE-002

<a id="test_CT_071"></a>

CT-071 — Foundation stability for overlay lifecycle

Preconditions: Commissioned overlay capacity and physical fabric configuration snapshot.

Procedure: Create, update and retire a routine overlay WSD; compare leaf/spine configuration before and after.

Expected outcome: No per-WSD switch change occurs; physical-capacity growth is classified as a separate foundation operation.

Evidence: Switch config digests, service class and operation audit.

Mode: automated  \|  Cadence: qualification; security-significant change  \|  Execution: not-run

Requirement links: ARCH-002, EDGE-001, FAB-001

<a id="test_CT_072"></a>

CT-072 — Bare-metal/fabric-routed service boundary

Preconditions: Explicit fabric-routed service class and authorized foundation workflow.

Procedure: Provision a test physical attachment under separate authority; inspect VRF/RT/interface ownership and retire it.

Expected outcome: Consumer contract remains portable; exceptions to overlay workflow are explicit; no unrestricted cross-domain route is introduced.

Evidence: Service-class declaration, foundation change and isolation tests.

Mode: automated  \|  Cadence: qualification; security-significant change  \|  Execution: not-run

Requirement links: ARCH-002, FAB-001, FAB-002, FAB-003, EVPN-001, FUT-003

<a id="test_CT_073"></a>

CT-073 — Image/data export compatibility

Preconditions: Supported boot mode, drivers, virtual hardware and encrypted-disk context.

Procedure: Recreate the workload on the target with a test image; verify guest drivers, time, certificates, application checks and unsupported device handling.

Expected outcome: Incompatibilities reject the selected exit path; data/identity are not assumed portable merely because a disk file converts.

Evidence: Compatibility checklist, boot logs, application and security tests.

Mode: automated  \|  Cadence: qualification; security-significant change  \|  Execution: not-run

Requirement links: CMP-002, PLACE-003, PORT-003, MIG-003, DEL-002

<a id="test_CT_074"></a>

CT-074 — Procured-capacity and service inventory reconciliation

Preconditions: Procurement/asset inventory, installed capacity and tenant reservations.

Procedure: Reconcile ordered, received, staged, commissioned, available, reserved and consumed quantities with accountable owners.

Expected outcome: No orphaned or double-counted capacity; unused procured capacity and support expiry are visible for planning.

Evidence: Inventory reconciliation and allocation/age report.

Mode: manual-and-automated  \|  Cadence: monthly; capacity change  \|  Execution: not-run

Requirement links: SVCM-002, CAP-003, VULN-001

<a id="test_CT_075"></a>

CT-075 — Document and catalogue completeness

Preconditions: Handbook source, schemas, examples, requirements and tests in the release package.

Procedure: Check unique IDs, full original-ID migration, references, source links, test mappings, schema validation and generated catalogue parity.

Expected outcome: No missing or dangling item; counts and release digest agree; document status does not claim unexecuted platform tests passed.

Evidence: Package validation report and manifest.

Mode: automated  \|  Cadence: each document release  \|  Execution: not-run

Requirement links: DOC-001, STD-001, STD-002, TEST-003, EVID-001

<a id="test_CT_076"></a>

CT-076 — External partner agreement and revocation

Preconditions: ExternalDomain has trust basis, authenticated endpoints and named agreement owner.

Procedure: Admit an approved binding, then revoke the agreement and check active/new session handling under its profile.

Expected outcome: Revocation removes intended access within the agreed interval; no REZ assumption is inferred merely from a private circuit.

Evidence: Agreement revision, revocation event and connectivity checks.

Mode: automated  \|  Cadence: qualification; security-significant change  \|  Execution: not-run

Requirement links: ZONE-001, MIG-001

<a id="test_CT_077"></a>

CT-077 — Flow revocation and live session semantics

Preconditions: Approved long-lived test flow with a revocation profile.

Procedure: Revoke permission and measure established sessions, cached policies and newly attempted sessions across enforcement points.

Expected outcome: New sessions are denied immediately upon committed policy; existing sessions are terminated or drained within the explicitly approved interval.

Evidence: Rule generation timeline, session table and probes.

Mode: automated  \|  Cadence: qualification; security-significant change  \|  Execution: not-run

Requirement links: ZIP-006, RTE-003, SVC-003, EXP-001, IAM-003, FLOW-001

<a id="test_CT_078"></a>

CT-078 — Storage clone, snapshot and export classification

Preconditions: Protected test volume with snapshot and clone operations enabled.

Procedure: Attempt cross-zone clone/export and a lower-categorization target using both tenant and service identities.

Expected outcome: Data copies preserve classification and key/access constraints; unapproved downgrade or public export is denied.

Evidence: Copy lineage, target checks, key references and audit.

Mode: automated  \|  Cadence: qualification; security-significant change  \|  Execution: not-run

Requirement links: STO-001, STO-003, LIFE-002, MIG-003

<a id="test_CT_079"></a>

CT-079 — Provider/support access time limit

Preconditions: Support role, approved session and export/logging rules.

Procedure: Open a time-bound support session, test scoped capabilities, expire it and verify all delegated grants are revoked.

Expected outcome: No unattended permanent privileged access remains; transferred diagnostics follow approved location and redaction rules.

Evidence: Session record, approval, scope tests and revocation receipts.

Mode: automated  \|  Cadence: qualification; security-significant change  \|  Execution: not-run

Requirement links: MGT-004, IAM-002, IAM-003, PLACE-002, SEC-002, OPS-001

<a id="test_CT_080"></a>

CT-080 — Distributed ZIP equivalence

Preconditions: A proposed distributed-enforcement profile and the required ZIP function list.

Procedure: Map every required boundary function to its actual enforcement/control component; test same-host and bypass paths plus controller/agent failure.

Expected outcome: Logical ZIP semantics are fully met; missing inspection, attribution, failure isolation or authority support rejects qualification.

Evidence: Function coverage, topology, policy and fault-test evidence.

Mode: design-and-automated  \|  Cadence: qualification; enforcement-stack change  \|  Execution: not-run

Requirement links: INV-002, THR-001, ZIP-001, ZIP-005, ZIP-006, ZIP-007, OVL-001, EDGE-002, PORT-001, NUT-004, NSX-003, OS-003, FUT-001

[Previous chapter](72-appendix-c-complete-normative-requirement-and-verification-index.md) · [Chapter index](README.md) · [Next chapter](74-appendix-e-source-control-traceability-and-responsibility.md)
