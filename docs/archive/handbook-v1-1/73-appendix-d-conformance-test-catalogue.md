# Appendix D — Conformance test catalogue

[Documentation home](../../README.md) · [Source document](../../../reference/migration-source-documents/Handbook_v1_1.docx) · [Chapter index](README.md)

> **Source:** HB11 — Draft v1.1. Historical source; not the active design.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: afbe9313dda4c68d5bb3af9ae6e9fcb5f098894c59e5f443270795bf2f9c21a1 -->

> **Historical only.** Use the [v1.4 reference architecture](../../architecture/reference/README.md) for the active design baseline. Conflicting historical text has not been silently reconciled.
<!-- SOURCE-BLOCK HB11:969 BEGIN -->

<a id="__RefHeading___Toc13435_1645000677"></a>
<a id="app_D"></a>

<!-- SOURCE-BLOCK HB11:969 END -->

<!-- SOURCE-BLOCK HB11:970 BEGIN -->

All 80 entries are execution specifications. Result: NOT RUN for every infrastructure test in this release. Implement each procedure in an authorized target environment, bind exact versions and test-suite digest, record observed evidence, and assess the applicable profile. Local schema/package test results are reported separately and do not satisfy these infrastructure procedures.

<!-- SOURCE-BLOCK HB11:970 END -->

<!-- SOURCE-BLOCK HB11:971 BEGIN -->

<a id="test_CT_001"></a>

CT-001 — Cross-tenant IPv4 isolation

<!-- SOURCE-BLOCK HB11:971 END -->

<!-- SOURCE-BLOCK HB11:972 BEGIN -->

Preconditions: Two authorized test tenants; live endpoints and a same-tenant positive control.

<!-- SOURCE-BLOCK HB11:972 END -->

<!-- SOURCE-BLOCK HB11:973 BEGIN -->

Procedure: Probe disallowed TCP/UDP services in both directions, including same-host and different-host placements. Compare platform policy and edge telemetry.

<!-- SOURCE-BLOCK HB11:973 END -->

<!-- SOURCE-BLOCK HB11:974 BEGIN -->

Expected outcome: All unapproved flows are denied; positive controls succeed; no misleading pass caused by a dead endpoint.

<!-- SOURCE-BLOCK HB11:974 END -->

<!-- SOURCE-BLOCK HB11:975 BEGIN -->

Evidence: Probe results, endpoint health, routing/policy snapshots and attribution.

<!-- SOURCE-BLOCK HB11:975 END -->

<!-- SOURCE-BLOCK HB11:976 BEGIN -->

Mode: automated  \|  Cadence: qualification; security-significant change  \|  Execution: not-run

<!-- SOURCE-BLOCK HB11:976 END -->

<!-- SOURCE-BLOCK HB11:977 BEGIN -->

Requirement links: TEN-001, SDI-002, TEST-001, DEL-001

<!-- SOURCE-BLOCK HB11:977 END -->

<!-- SOURCE-BLOCK HB11:978 BEGIN -->

<a id="test_CT_002"></a>

CT-002 — Cross-tenant IPv6 isolation

<!-- SOURCE-BLOCK HB11:978 END -->

<!-- SOURCE-BLOCK HB11:979 BEGIN -->

Preconditions: IPv6-qualified test endpoints; both tenants have allocated prefixes.

<!-- SOURCE-BLOCK HB11:979 END -->

<!-- SOURCE-BLOCK HB11:980 BEGIN -->

Procedure: Repeat CT-001 over global/unique-local IPv6; inspect link-local exposure at each segment boundary.

<!-- SOURCE-BLOCK HB11:980 END -->

<!-- SOURCE-BLOCK HB11:981 BEGIN -->

Expected outcome: Unapproved IPv6 flows are denied without breaking required local IPv6 operation.

<!-- SOURCE-BLOCK HB11:981 END -->

<!-- SOURCE-BLOCK HB11:982 BEGIN -->

Evidence: IPv6 probes, neighbor state, policy and deny telemetry.

<!-- SOURCE-BLOCK HB11:982 END -->

<!-- SOURCE-BLOCK HB11:983 BEGIN -->

Mode: automated  \|  Cadence: qualification; security-significant change  \|  Execution: not-run

<!-- SOURCE-BLOCK HB11:983 END -->

<!-- SOURCE-BLOCK HB11:984 BEGIN -->

Requirement links: TEN-001, SDI-002, IPV6-001, IPV6-002, TEST-001

<!-- SOURCE-BLOCK HB11:984 END -->

<!-- SOURCE-BLOCK HB11:985 BEGIN -->

<a id="test_CT_003"></a>

CT-003 — Zone-boundary bypass prevention

<!-- SOURCE-BLOCK HB11:985 END -->

<!-- SOURCE-BLOCK HB11:986 BEGIN -->

Preconditions: Two distinct zone domains with one approved test flow.

<!-- SOURCE-BLOCK HB11:986 END -->

<!-- SOURCE-BLOCK HB11:987 BEGIN -->

Procedure: Inspect all native, static, policy-based and external-network paths; test same-host, cross-host and shared-attachment cases. Correlate the allowed flow at the declared logical ZIP.

<!-- SOURCE-BLOCK HB11:987 END -->

<!-- SOURCE-BLOCK HB11:988 BEGIN -->

Expected outcome: No undeclared path exists; allowed traffic is enforced by the ZIP realization; removing that authorization denies it.

<!-- SOURCE-BLOCK HB11:988 END -->

<!-- SOURCE-BLOCK HB11:989 BEGIN -->

Evidence: Topology graph, routes, packet-path or enforcement trace and policy digests.

<!-- SOURCE-BLOCK HB11:989 END -->

<!-- SOURCE-BLOCK HB11:990 BEGIN -->

Mode: automated  \|  Cadence: qualification; security-significant change  \|  Execution: not-run

<!-- SOURCE-BLOCK HB11:990 END -->

<!-- SOURCE-BLOCK HB11:991 BEGIN -->

Requirement links: ARCH-003, ZIP-001, ZIP-007, OVL-002, RTE-002, IPV6-002, NUT-002, NSX-002, NSX-003, TEST-001, MIG-002, DEL-001

<!-- SOURCE-BLOCK HB11:991 END -->

<!-- SOURCE-BLOCK HB11:992 BEGIN -->

<a id="test_CT_004"></a>

CT-004 — Infrastructure management isolation

<!-- SOURCE-BLOCK HB11:992 END -->

<!-- SOURCE-BLOCK HB11:993 BEGIN -->

Preconditions: Inventory of management APIs, BMCs, consoles, storage administration and backup administration.

<!-- SOURCE-BLOCK HB11:993 END -->

<!-- SOURCE-BLOCK HB11:994 BEGIN -->

Procedure: From test workloads, attempt the enumerated management endpoints over all enabled families. Separately verify approved management access.

<!-- SOURCE-BLOCK HB11:994 END -->

<!-- SOURCE-BLOCK HB11:995 BEGIN -->

Expected outcome: Workloads cannot access infrastructure management; dedicated authorized administration still works.

<!-- SOURCE-BLOCK HB11:995 END -->

<!-- SOURCE-BLOCK HB11:996 BEGIN -->

Evidence: Inventory coverage, negative probes and management access audit.

<!-- SOURCE-BLOCK HB11:996 END -->

<!-- SOURCE-BLOCK HB11:997 BEGIN -->

Mode: automated  \|  Cadence: qualification; security-significant change  \|  Execution: not-run

<!-- SOURCE-BLOCK HB11:997 END -->

<!-- SOURCE-BLOCK HB11:998 BEGIN -->

Requirement links: ARCH-004, MODEL-002, ZIP-004, MGT-001, MGT-005, BKP-001, DEL-001

<!-- SOURCE-BLOCK HB11:998 END -->

<!-- SOURCE-BLOCK HB11:999 BEGIN -->

<a id="test_CT_005"></a>

CT-005 — Default Internet denial

<!-- SOURCE-BLOCK HB11:999 END -->

<!-- SOURCE-BLOCK HB11:1000 BEGIN -->

Preconditions: WSD has no egress Exposure; a provider-controlled external test endpoint is available.

<!-- SOURCE-BLOCK HB11:1000 END -->

<!-- SOURCE-BLOCK HB11:1001 BEGIN -->

Procedure: Attempt direct and proxy-mediated external access, including IPv6, alternate DNS and common tunnel paths allowed by the test plan.

<!-- SOURCE-BLOCK HB11:1001 END -->

<!-- SOURCE-BLOCK HB11:1002 BEGIN -->

Expected outcome: No unapproved egress succeeds; no default-route or NAT shortcut defeats policy.

<!-- SOURCE-BLOCK HB11:1002 END -->

<!-- SOURCE-BLOCK HB11:1003 BEGIN -->

Evidence: Route/NAT inventory, probes and egress logs.

<!-- SOURCE-BLOCK HB11:1003 END -->

<!-- SOURCE-BLOCK HB11:1004 BEGIN -->

Mode: automated  \|  Cadence: qualification; security-significant change  \|  Execution: not-run

<!-- SOURCE-BLOCK HB11:1004 END -->

<!-- SOURCE-BLOCK HB11:1005 BEGIN -->

Requirement links: EGR-001, OS-001

<!-- SOURCE-BLOCK HB11:1005 END -->

<!-- SOURCE-BLOCK HB11:1006 BEGIN -->

<a id="test_CT_006"></a>

CT-006 — Public ingress protection

<!-- SOURCE-BLOCK HB11:1006 END -->

<!-- SOURCE-BLOCK HB11:1007 BEGIN -->

Preconditions: Internal test service and a controlled external test client.

<!-- SOURCE-BLOCK HB11:1007 END -->

<!-- SOURCE-BLOCK HB11:1008 BEGIN -->

Procedure: Probe an internal workload directly, then exercise a separately approved PAZ ingress service.

<!-- SOURCE-BLOCK HB11:1008 END -->

<!-- SOURCE-BLOCK HB11:1009 BEGIN -->

Expected outcome: Direct exposure is denied; the approved ingress reaches only its declared backend and port.

<!-- SOURCE-BLOCK HB11:1009 END -->

<!-- SOURCE-BLOCK HB11:1010 BEGIN -->

Evidence: Exposure object, DNS/certificate records and ingress/backend traces.

<!-- SOURCE-BLOCK HB11:1010 END -->

<!-- SOURCE-BLOCK HB11:1011 BEGIN -->

Mode: automated  \|  Cadence: qualification; security-significant change  \|  Execution: not-run

<!-- SOURCE-BLOCK HB11:1011 END -->

<!-- SOURCE-BLOCK HB11:1012 BEGIN -->

Requirement links: ING-001, ING-002

<!-- SOURCE-BLOCK HB11:1012 END -->

<!-- SOURCE-BLOCK HB11:1013 BEGIN -->

<a id="test_CT_007"></a>

CT-007 — Approved stateful flow

<!-- SOURCE-BLOCK HB11:1013 END -->

<!-- SOURCE-BLOCK HB11:1014 BEGIN -->

Preconditions: Versioned FlowProfile and approved source/destination identities.

<!-- SOURCE-BLOCK HB11:1014 END -->

<!-- SOURCE-BLOCK HB11:1015 BEGIN -->

Procedure: Open the authorized application session and its reply path; test unsolicited reverse sessions and a nearby disallowed service.

<!-- SOURCE-BLOCK HB11:1015 END -->

<!-- SOURCE-BLOCK HB11:1016 BEGIN -->

Expected outcome: Intended request/reply works; reverse initiation is allowed only when separately declared.

<!-- SOURCE-BLOCK HB11:1016 END -->

<!-- SOURCE-BLOCK HB11:1017 BEGIN -->

Evidence: Flow intent, compiled rule and application-level probe results.

<!-- SOURCE-BLOCK HB11:1017 END -->

<!-- SOURCE-BLOCK HB11:1018 BEGIN -->

Mode: automated  \|  Cadence: each deployment; flow change  \|  Execution: not-run

<!-- SOURCE-BLOCK HB11:1018 END -->

<!-- SOURCE-BLOCK HB11:1019 BEGIN -->

Requirement links: ZIP-003, NSX-002, FLOW-001, TEST-001

<!-- SOURCE-BLOCK HB11:1019 END -->

<!-- SOURCE-BLOCK HB11:1020 BEGIN -->

<a id="test_CT_008"></a>

CT-008 — Service-binding scope

<!-- SOURCE-BLOCK HB11:1020 END -->

<!-- SOURCE-BLOCK HB11:1021 BEGIN -->

Preconditions: One bound and one unbound provider service endpoint.

<!-- SOURCE-BLOCK HB11:1021 END -->

<!-- SOURCE-BLOCK HB11:1022 BEGIN -->

Procedure: Exercise required DNS, time, identity or backup consumption; probe the rest of the service subnet and administrative interface.

<!-- SOURCE-BLOCK HB11:1022 END -->

<!-- SOURCE-BLOCK HB11:1023 BEGIN -->

Expected outcome: Only declared service endpoints/directions are reachable; consuming one service does not expose its subnet or management.

<!-- SOURCE-BLOCK HB11:1023 END -->

<!-- SOURCE-BLOCK HB11:1024 BEGIN -->

Evidence: Binding resolution, probes and service-side attribution.

<!-- SOURCE-BLOCK HB11:1024 END -->

<!-- SOURCE-BLOCK HB11:1025 BEGIN -->

Mode: automated  \|  Cadence: each deployment; binding change  \|  Execution: not-run

<!-- SOURCE-BLOCK HB11:1025 END -->

<!-- SOURCE-BLOCK HB11:1026 BEGIN -->

Requirement links: INV-004, MODEL-002, SVC-001, SVC-002, SVC-003, DEL-001

<!-- SOURCE-BLOCK HB11:1026 END -->

<!-- SOURCE-BLOCK HB11:1027 BEGIN -->

<a id="test_CT_009"></a>

CT-009 — Route-authority integrity

<!-- SOURCE-BLOCK HB11:1027 END -->

<!-- SOURCE-BLOCK HB11:1028 BEGIN -->

Preconditions: Approved route graph and realized routing snapshots.

<!-- SOURCE-BLOCK HB11:1028 END -->

<!-- SOURCE-BLOCK HB11:1029 BEGIN -->

Procedure: Compare imported/exported prefixes, defaults, next hops and BGP neighbors with the compiled plan; check recursive next-hop reachability and summaries.

<!-- SOURCE-BLOCK HB11:1029 END -->

<!-- SOURCE-BLOCK HB11:1030 BEGIN -->

Expected outcome: No unauthorized route or advertisement exists; summaries cannot expose excluded domains.

<!-- SOURCE-BLOCK HB11:1030 END -->

<!-- SOURCE-BLOCK HB11:1031 BEGIN -->

Evidence: Compiler output, RIB/FIB snapshots and semantic diff.

<!-- SOURCE-BLOCK HB11:1031 END -->

<!-- SOURCE-BLOCK HB11:1032 BEGIN -->

Mode: automated  \|  Cadence: qualification; security-significant change  \|  Execution: not-run

<!-- SOURCE-BLOCK HB11:1032 END -->

<!-- SOURCE-BLOCK HB11:1033 BEGIN -->

Requirement links: INV-003, RTE-001, RTE-002, RTE-003, RTE-004, FAB-002, EVPN-001, NSX-002, POL-002

<!-- SOURCE-BLOCK HB11:1033 END -->

<!-- SOURCE-BLOCK HB11:1034 BEGIN -->

<a id="test_CT_010"></a>

CT-010 — Security-event attribution

<!-- SOURCE-BLOCK HB11:1034 END -->

<!-- SOURCE-BLOCK HB11:1035 BEGIN -->

Preconditions: Central collector reachable and time synchronization healthy.

<!-- SOURCE-BLOCK HB11:1035 END -->

<!-- SOURCE-BLOCK HB11:1036 BEGIN -->

Procedure: Generate an allowed and denied flow plus an administrative change; find the correlated records centrally.

<!-- SOURCE-BLOCK HB11:1036 END -->

<!-- SOURCE-BLOCK HB11:1037 BEGIN -->

Expected outcome: Records identify tenant, WSD/domain, policy, actor, timestamp and deployment; timestamps satisfy the logging profile.

<!-- SOURCE-BLOCK HB11:1037 END -->

<!-- SOURCE-BLOCK HB11:1038 BEGIN -->

Evidence: Events, correlation query and collection-delay measurement.

<!-- SOURCE-BLOCK HB11:1038 END -->

<!-- SOURCE-BLOCK HB11:1039 BEGIN -->

Mode: automated  \|  Cadence: each deployment; scheduled synthetic  \|  Execution: not-run

<!-- SOURCE-BLOCK HB11:1039 END -->

<!-- SOURCE-BLOCK HB11:1040 BEGIN -->

Requirement links: EGR-002, OBS-001, OBS-002, OBS-003

<!-- SOURCE-BLOCK HB11:1040 END -->

<!-- SOURCE-BLOCK HB11:1041 BEGIN -->

<a id="test_CT_011"></a>

CT-011 — Control-plane loss

<!-- SOURCE-BLOCK HB11:1041 END -->

<!-- SOURCE-BLOCK HB11:1042 BEGIN -->

Preconditions: Approved isolated test environment; outage and restoration plan.

<!-- SOURCE-BLOCK HB11:1042 END -->

<!-- SOURCE-BLOCK HB11:1043 BEGIN -->

Procedure: Remove catalogue/controller or platform-management connectivity independently; observe existing enforcement and attempts to provision.

<!-- SOURCE-BLOCK HB11:1043 END -->

<!-- SOURCE-BLOCK HB11:1044 BEGIN -->

Expected outcome: Existing approved paths retain enforcement; new unsafe changes stop; recovery converges without bypass.

<!-- SOURCE-BLOCK HB11:1044 END -->

<!-- SOURCE-BLOCK HB11:1045 BEGIN -->

Evidence: Before/during/after policy snapshots, alerts and operation journal.

<!-- SOURCE-BLOCK HB11:1045 END -->

<!-- SOURCE-BLOCK HB11:1046 BEGIN -->

Mode: controlled-fault  \|  Cadence: qualification; relevant upgrade  \|  Execution: not-run

<!-- SOURCE-BLOCK HB11:1046 END -->

<!-- SOURCE-BLOCK HB11:1047 BEGIN -->

Requirement links: INV-007, AUTO-001, TEST-004, FAIL-001, FAIL-002

<!-- SOURCE-BLOCK HB11:1047 END -->

<!-- SOURCE-BLOCK HB11:1048 BEGIN -->

<a id="test_CT_012"></a>

CT-012 — Security-edge node failure

<!-- SOURCE-BLOCK HB11:1048 END -->

<!-- SOURCE-BLOCK HB11:1049 BEGIN -->

Preconditions: Measured production-like load within the selected profile; spare capacity available.

<!-- SOURCE-BLOCK HB11:1049 END -->

<!-- SOURCE-BLOCK HB11:1050 BEGIN -->

Procedure: Fail one edge node or its uplink under an approved test plan and measure sessions, drops, recovery and policy continuity.

<!-- SOURCE-BLOCK HB11:1050 END -->

<!-- SOURCE-BLOCK HB11:1051 BEGIN -->

Expected outcome: No unauthorized traffic is permitted; recovery and remaining capacity meet the accepted profile.

<!-- SOURCE-BLOCK HB11:1051 END -->

<!-- SOURCE-BLOCK HB11:1052 BEGIN -->

Evidence: Time-series traffic, failover timeline and enforcement traces.

<!-- SOURCE-BLOCK HB11:1052 END -->

<!-- SOURCE-BLOCK HB11:1053 BEGIN -->

Mode: controlled-fault  \|  Cadence: qualification; scheduled resilience exercise  \|  Execution: not-run

<!-- SOURCE-BLOCK HB11:1053 END -->

<!-- SOURCE-BLOCK HB11:1054 BEGIN -->

Requirement links: REL-001, REL-002, TEST-004, CAP-001, FAIL-001, FAIL-002

<!-- SOURCE-BLOCK HB11:1054 END -->

<!-- SOURCE-BLOCK HB11:1055 BEGIN -->

<a id="test_CT_013"></a>

CT-013 — Offboarding residuals

<!-- SOURCE-BLOCK HB11:1055 END -->

<!-- SOURCE-BLOCK HB11:1056 BEGIN -->

Preconditions: Disposable WSD, retention policy and resource graph recorded.

<!-- SOURCE-BLOCK HB11:1056 END -->

<!-- SOURCE-BLOCK HB11:1057 BEGIN -->

Procedure: Run retirement; query routes, policy, identities, addresses, DNS, certificates and storage/backup records by stable WSD ID.

<!-- SOURCE-BLOCK HB11:1057 END -->

<!-- SOURCE-BLOCK HB11:1058 BEGIN -->

Expected outcome: Active connectivity and grants are removed; retained copies are explicitly owned/locked; the tombstone explains every remaining object.

<!-- SOURCE-BLOCK HB11:1058 END -->

<!-- SOURCE-BLOCK HB11:1059 BEGIN -->

Evidence: Deletion ledger, scans, retention receipts and sanitization references.

<!-- SOURCE-BLOCK HB11:1059 END -->

<!-- SOURCE-BLOCK HB11:1060 BEGIN -->

Mode: automated  \|  Cadence: qualification; security-significant change  \|  Execution: not-run

<!-- SOURCE-BLOCK HB11:1060 END -->

<!-- SOURCE-BLOCK HB11:1061 BEGIN -->

Requirement links: IPAM-003, LIFE-001, LIFE-002, DEL-001

<!-- SOURCE-BLOCK HB11:1061 END -->

<!-- SOURCE-BLOCK HB11:1062 BEGIN -->

<a id="test_CT_014"></a>

CT-014 — Security drift detection

<!-- SOURCE-BLOCK HB11:1062 END -->

<!-- SOURCE-BLOCK HB11:1063 BEGIN -->

Preconditions: Non-production object with a known authorized baseline.

<!-- SOURCE-BLOCK HB11:1063 END -->

<!-- SOURCE-BLOCK HB11:1064 BEGIN -->

Procedure: Introduce a reversible out-of-band security change; observe detection, containment decision and reconciliation.

<!-- SOURCE-BLOCK HB11:1064 END -->

<!-- SOURCE-BLOCK HB11:1065 BEGIN -->

Expected outcome: Drift changes technical compliance status and alerts the owner; incident containment is not silently reverted.

<!-- SOURCE-BLOCK HB11:1065 END -->

<!-- SOURCE-BLOCK HB11:1066 BEGIN -->

Evidence: Drift event, policy generation and recovery journal.

<!-- SOURCE-BLOCK HB11:1066 END -->

<!-- SOURCE-BLOCK HB11:1067 BEGIN -->

Mode: controlled-fault  \|  Cadence: qualification; drift-engine change  \|  Execution: not-run

<!-- SOURCE-BLOCK HB11:1067 END -->

<!-- SOURCE-BLOCK HB11:1068 BEGIN -->

Requirement links: IMG-002, DRIFT-001, DRIFT-002

<!-- SOURCE-BLOCK HB11:1068 END -->

<!-- SOURCE-BLOCK HB11:1069 BEGIN -->

<a id="test_CT_015"></a>

CT-015 — Platform/provider upgrade regression

<!-- SOURCE-BLOCK HB11:1069 END -->

<!-- SOURCE-BLOCK HB11:1070 BEGIN -->

Preconditions: Exact old/new tuples, release notes and canary tenant.

<!-- SOURCE-BLOCK HB11:1070 END -->

<!-- SOURCE-BLOCK HB11:1071 BEGIN -->

Procedure: Run the applicable suite against the new tuple, including create/update/import/delete and failure paths; evaluate rollback or forward repair.

<!-- SOURCE-BLOCK HB11:1071 END -->

<!-- SOURCE-BLOCK HB11:1072 BEGIN -->

Expected outcome: No mandatory outcome regresses; the new certification is approved before broad placement.

<!-- SOURCE-BLOCK HB11:1072 END -->

<!-- SOURCE-BLOCK HB11:1073 BEGIN -->

Evidence: Tuple manifest, test reports, limitations and promotion decision.

<!-- SOURCE-BLOCK HB11:1073 END -->

<!-- SOURCE-BLOCK HB11:1074 BEGIN -->

Mode: automated  \|  Cadence: qualification; security-significant change  \|  Execution: not-run

<!-- SOURCE-BLOCK HB11:1074 END -->

<!-- SOURCE-BLOCK HB11:1075 BEGIN -->

Requirement links: PORT-001, QUAL-001, NUT-001, NUT-004, NSX-003, OS-003, FUT-001, TF-002, TEST-002, VULN-002

<!-- SOURCE-BLOCK HB11:1075 END -->

<!-- SOURCE-BLOCK HB11:1076 BEGIN -->

<a id="test_CT_016"></a>

CT-016 — Portable contract and object identity

<!-- SOURCE-BLOCK HB11:1076 END -->

<!-- SOURCE-BLOCK HB11:1077 BEGIN -->

Preconditions: Same versioned request and two independently qualified adapters.

<!-- SOURCE-BLOCK HB11:1077 END -->

<!-- SOURCE-BLOCK HB11:1078 BEGIN -->

Procedure: Validate stable consumer fields and compile for both targets; compare semantic outputs without requiring matching topology or vendor IDs.

<!-- SOURCE-BLOCK HB11:1078 END -->

<!-- SOURCE-BLOCK HB11:1079 BEGIN -->

Expected outcome: Equivalent mandatory intent is preserved; unsupported capabilities reject placement rather than silently degrade.

<!-- SOURCE-BLOCK HB11:1079 END -->

<!-- SOURCE-BLOCK HB11:1080 BEGIN -->

Evidence: Normalized requests, adapter plans and semantic comparison.

<!-- SOURCE-BLOCK HB11:1080 END -->

<!-- SOURCE-BLOCK HB11:1081 BEGIN -->

Mode: design-and-automated  \|  Cadence: qualification; contract change  \|  Execution: not-run

<!-- SOURCE-BLOCK HB11:1081 END -->

<!-- SOURCE-BLOCK HB11:1082 BEGIN -->

Requirement links: ARCH-001, INV-001, INV-005, REF-001, REF-002, WSD-002, OVL-001, PORT-003, API-001, TF-003, DEL-002

<!-- SOURCE-BLOCK HB11:1082 END -->

<!-- SOURCE-BLOCK HB11:1083 BEGIN -->

<a id="test_CT_017"></a>

CT-017 — Admission and authorization negatives

<!-- SOURCE-BLOCK HB11:1083 END -->

<!-- SOURCE-BLOCK HB11:1084 BEGIN -->

Preconditions: Schema/profile registry and scoped test identities.

<!-- SOURCE-BLOCK HB11:1084 END -->

<!-- SOURCE-BLOCK HB11:1085 BEGIN -->

Procedure: Submit unknown fields, unresolved profile versions, forged approval references, foreign-tenant references and consumer-supplied status.

<!-- SOURCE-BLOCK HB11:1085 END -->

<!-- SOURCE-BLOCK HB11:1086 BEGIN -->

Expected outcome: All invalid or unauthorized requests are rejected before any allocation or provider action.

<!-- SOURCE-BLOCK HB11:1086 END -->

<!-- SOURCE-BLOCK HB11:1087 BEGIN -->

Evidence: Admission decisions and zero-side-effect audit.

<!-- SOURCE-BLOCK HB11:1087 END -->

<!-- SOURCE-BLOCK HB11:1088 BEGIN -->

Mode: automated  \|  Cadence: each contract/policy change  \|  Execution: not-run

<!-- SOURCE-BLOCK HB11:1088 END -->

<!-- SOURCE-BLOCK HB11:1089 BEGIN -->

Requirement links: ARCH-001, CAT-001, CAT-002, MODEL-001, WSD-001, WSD-002, ZONE-001, API-002, API-003, POL-001, EXC-003, ONB-001

<!-- SOURCE-BLOCK HB11:1089 END -->

<!-- SOURCE-BLOCK HB11:1090 BEGIN -->

<a id="test_CT_018"></a>

CT-018 — Unsupported capability and expired certification

<!-- SOURCE-BLOCK HB11:1090 END -->

<!-- SOURCE-BLOCK HB11:1091 BEGIN -->

Preconditions: Candidate and expired platform profiles.

<!-- SOURCE-BLOCK HB11:1091 END -->

<!-- SOURCE-BLOCK HB11:1092 BEGIN -->

Procedure: Request dual-stack, inspection or dedicated placement on a profile lacking that qualified capability.

<!-- SOURCE-BLOCK HB11:1092 END -->

<!-- SOURCE-BLOCK HB11:1093 BEGIN -->

Expected outcome: Placement fails with an actionable capability reason; candidate/expired records cannot authorize production.

<!-- SOURCE-BLOCK HB11:1093 END -->

<!-- SOURCE-BLOCK HB11:1094 BEGIN -->

Evidence: Placement decisions, capability digests and status.

<!-- SOURCE-BLOCK HB11:1094 END -->

<!-- SOURCE-BLOCK HB11:1095 BEGIN -->

Mode: automated  \|  Cadence: each placement-engine change  \|  Execution: not-run

<!-- SOURCE-BLOCK HB11:1095 END -->

<!-- SOURCE-BLOCK HB11:1096 BEGIN -->

Requirement links: SCOPE-001, REF-002, CAT-002, SDI-003, OVL-001, IPV6-003, PLACE-001, PORT-001, PORT-002, QUAL-001, NUT-001, OS-003, FUT-001, FUT-002, ASSUR-002, ASSUR-003, TEST-002, ONB-001, ACPT-001

<!-- SOURCE-BLOCK HB11:1096 END -->

<!-- SOURCE-BLOCK HB11:1097 BEGIN -->

<a id="test_CT_019"></a>

CT-019 — Ownership, quota and separation of duties

<!-- SOURCE-BLOCK HB11:1097 END -->

<!-- SOURCE-BLOCK HB11:1098 BEGIN -->

Preconditions: Tenant quotas and identity/control-plane roles are defined.

<!-- SOURCE-BLOCK HB11:1098 END -->

<!-- SOURCE-BLOCK HB11:1099 BEGIN -->

Procedure: Test permitted workload operations and forbidden foundation/edge/profile edits; race two allocations against the same quota.

<!-- SOURCE-BLOCK HB11:1099 END -->

<!-- SOURCE-BLOCK HB11:1100 BEGIN -->

Expected outcome: Only allowed roles succeed; quota reservation is atomic; no resource is created above a hard entitlement.

<!-- SOURCE-BLOCK HB11:1100 END -->

<!-- SOURCE-BLOCK HB11:1101 BEGIN -->

Evidence: Authorization matrix, concurrent request results and allocation journal.

<!-- SOURCE-BLOCK HB11:1101 END -->

<!-- SOURCE-BLOCK HB11:1102 BEGIN -->

Mode: automated  \|  Cadence: qualification; security-significant change  \|  Execution: not-run

<!-- SOURCE-BLOCK HB11:1102 END -->

<!-- SOURCE-BLOCK HB11:1103 BEGIN -->

Requirement links: TEN-001, TEN-002, TEN-003, MGT-003, IAM-001, SVCM-001, NSX-001, OS-002, API-002, STATE-001, SEC-002, OPS-001, OPS-002

<!-- SOURCE-BLOCK HB11:1103 END -->

<!-- SOURCE-BLOCK HB11:1104 BEGIN -->

<a id="test_CT_020"></a>

CT-020 — Security-label integrity

<!-- SOURCE-BLOCK HB11:1104 END -->

<!-- SOURCE-BLOCK HB11:1105 BEGIN -->

Preconditions: Provider-owned selectors and tenant-editable labels are distinguishable.

<!-- SOURCE-BLOCK HB11:1105 END -->

<!-- SOURCE-BLOCK HB11:1106 BEGIN -->

Procedure: Attempt to add/remove security labels, impersonate another group or move a workload to a privileged selector.

<!-- SOURCE-BLOCK HB11:1106 END -->

<!-- SOURCE-BLOCK HB11:1107 BEGIN -->

Expected outcome: Tenant changes cannot expand effective permissions; mandatory policy precedence is preserved.

<!-- SOURCE-BLOCK HB11:1107 END -->

<!-- SOURCE-BLOCK HB11:1108 BEGIN -->

Evidence: RBAC results, label audit and effective-rule evaluation.

<!-- SOURCE-BLOCK HB11:1108 END -->

<!-- SOURCE-BLOCK HB11:1109 BEGIN -->

Mode: automated  \|  Cadence: qualification; security-significant change  \|  Execution: not-run

<!-- SOURCE-BLOCK HB11:1109 END -->

<!-- SOURCE-BLOCK HB11:1110 BEGIN -->

Requirement links: MICRO-002, MICRO-003, NUT-003, NSX-001, FLOW-001

<!-- SOURCE-BLOCK HB11:1110 END -->

<!-- SOURCE-BLOCK HB11:1111 BEGIN -->

<a id="test_CT_021"></a>

CT-021 — Same-domain east-west isolation

<!-- SOURCE-BLOCK HB11:1111 END -->

<!-- SOURCE-BLOCK HB11:1112 BEGIN -->

Preconditions: Two WSDs deliberately share one approved Security Domain Instance.

<!-- SOURCE-BLOCK HB11:1112 END -->

<!-- SOURCE-BLOCK HB11:1113 BEGIN -->

Procedure: Test same-subnet and cross-subnet traffic with and without explicit FlowIntent; verify traffic on one hypervisor as well as between hosts.

<!-- SOURCE-BLOCK HB11:1113 END -->

<!-- SOURCE-BLOCK HB11:1114 BEGIN -->

Expected outcome: Unapproved east-west communication is denied; allowed flows and required local services function.

<!-- SOURCE-BLOCK HB11:1114 END -->

<!-- SOURCE-BLOCK HB11:1115 BEGIN -->

Evidence: Enforcement location, probes and applied policy.

<!-- SOURCE-BLOCK HB11:1115 END -->

<!-- SOURCE-BLOCK HB11:1116 BEGIN -->

Mode: automated  \|  Cadence: qualification; security-significant change  \|  Execution: not-run

<!-- SOURCE-BLOCK HB11:1116 END -->

<!-- SOURCE-BLOCK HB11:1117 BEGIN -->

Requirement links: SDI-002, OVL-002, MICRO-001, MICRO-003, OS-001

<!-- SOURCE-BLOCK HB11:1117 END -->

<!-- SOURCE-BLOCK HB11:1118 BEGIN -->

<a id="test_CT_022"></a>

CT-022 — Spoofing and virtual NIC controls

<!-- SOURCE-BLOCK HB11:1118 END -->

<!-- SOURCE-BLOCK HB11:1119 BEGIN -->

Preconditions: Provider-approved packet tests on dedicated non-production endpoints.

<!-- SOURCE-BLOCK HB11:1119 END -->

<!-- SOURCE-BLOCK HB11:1120 BEGIN -->

Procedure: Exercise incorrect source addressing, unauthorized address pairs and additional NIC attachments within the bounded test plan.

<!-- SOURCE-BLOCK HB11:1120 END -->

<!-- SOURCE-BLOCK HB11:1121 BEGIN -->

Expected outcome: Source identities cannot impersonate another domain; platform exceptions have explicit owners and expiration.

<!-- SOURCE-BLOCK HB11:1121 END -->

<!-- SOURCE-BLOCK HB11:1122 BEGIN -->

Evidence: Port/NIC policy, bounded test output and exception records.

<!-- SOURCE-BLOCK HB11:1122 END -->

<!-- SOURCE-BLOCK HB11:1123 BEGIN -->

Mode: automated  \|  Cadence: qualification; security-significant change  \|  Execution: not-run

<!-- SOURCE-BLOCK HB11:1123 END -->

<!-- SOURCE-BLOCK HB11:1124 BEGIN -->

Requirement links: OVL-003, MICRO-003, OS-002, OS-003

<!-- SOURCE-BLOCK HB11:1124 END -->

<!-- SOURCE-BLOCK HB11:1125 BEGIN -->

<a id="test_CT_023"></a>

CT-023 — Shared edge-attachment isolation

<!-- SOURCE-BLOCK HB11:1125 END -->

<!-- SOURCE-BLOCK HB11:1126 BEGIN -->

Preconditions: Two domains use an intentionally shared provider attachment network.

<!-- SOURCE-BLOCK HB11:1126 END -->

<!-- SOURCE-BLOCK HB11:1127 BEGIN -->

Procedure: Exercise direct same-segment paths, ARP/ND interaction, external gateway routing and NAT hairpin in both directions.

<!-- SOURCE-BLOCK HB11:1127 END -->

<!-- SOURCE-BLOCK HB11:1128 BEGIN -->

Expected outcome: No path bypasses per-domain identity and ZIP enforcement; otherwise the shared attachment is ineligible.

<!-- SOURCE-BLOCK HB11:1128 END -->

<!-- SOURCE-BLOCK HB11:1129 BEGIN -->

Evidence: Attachment topology, neighbor state, routes and bidirectional probes.

<!-- SOURCE-BLOCK HB11:1129 END -->

<!-- SOURCE-BLOCK HB11:1130 BEGIN -->

Mode: automated  \|  Cadence: qualification; security-significant change  \|  Execution: not-run

<!-- SOURCE-BLOCK HB11:1130 END -->

<!-- SOURCE-BLOCK HB11:1131 BEGIN -->

Requirement links: ZIP-002, ZIP-007, OVL-002, RTE-002, RTE-004, EDGE-001, EDGE-002, NUT-002, NUT-004, OS-002

<!-- SOURCE-BLOCK HB11:1131 END -->

<!-- SOURCE-BLOCK HB11:1132 BEGIN -->

<a id="test_CT_024"></a>

CT-024 — Stateful symmetry and policy routing

<!-- SOURCE-BLOCK HB11:1132 END -->

<!-- SOURCE-BLOCK HB11:1133 BEGIN -->

Preconditions: Multiple eligible edge paths and asymmetric-failure scenario.

<!-- SOURCE-BLOCK HB11:1133 END -->

<!-- SOURCE-BLOCK HB11:1134 BEGIN -->

Procedure: Verify forward/return ownership before and during failover; change PBR to a permitted alternative in the test environment.

<!-- SOURCE-BLOCK HB11:1134 END -->

<!-- SOURCE-BLOCK HB11:1135 BEGIN -->

Expected outcome: Stateful enforcement remains correct; unsupported asymmetry is denied, not resolved by permissive bypass.

<!-- SOURCE-BLOCK HB11:1135 END -->

<!-- SOURCE-BLOCK HB11:1136 BEGIN -->

Evidence: Session traces, PBR precedence and HA counters.

<!-- SOURCE-BLOCK HB11:1136 END -->

<!-- SOURCE-BLOCK HB11:1137 BEGIN -->

Mode: automated  \|  Cadence: qualification; security-significant change  \|  Execution: not-run

<!-- SOURCE-BLOCK HB11:1137 END -->

<!-- SOURCE-BLOCK HB11:1138 BEGIN -->

Requirement links: RTE-004, EDGE-001, EDGE-002, EVPN-002, NUT-002, NSX-003, FAIL-001

<!-- SOURCE-BLOCK HB11:1138 END -->

<!-- SOURCE-BLOCK HB11:1139 BEGIN -->

<a id="test_CT_025"></a>

CT-025 — Zone adjacency and joint authority

<!-- SOURCE-BLOCK HB11:1139 END -->

<!-- SOURCE-BLOCK HB11:1140 BEGIN -->

Preconditions: Versioned zone graph and authority registry.

<!-- SOURCE-BLOCK HB11:1140 END -->

<!-- SOURCE-BLOCK HB11:1141 BEGIN -->

Procedure: Submit prohibited adjacencies, RZ public attachment, REZ without partner agreement, and a ZIP without both authority approvals.

<!-- SOURCE-BLOCK HB11:1141 END -->

<!-- SOURCE-BLOCK HB11:1142 BEGIN -->

Expected outcome: Invalid graphs are rejected; valid bindings resolve to the explicitly authorized adjacent domains.

<!-- SOURCE-BLOCK HB11:1142 END -->

<!-- SOURCE-BLOCK HB11:1143 BEGIN -->

Evidence: Graph decision report and approval provenance.

<!-- SOURCE-BLOCK HB11:1143 END -->

<!-- SOURCE-BLOCK HB11:1144 BEGIN -->

Mode: design-and-automated  \|  Cadence: each policy/profile change  \|  Execution: not-run

<!-- SOURCE-BLOCK HB11:1144 END -->

<!-- SOURCE-BLOCK HB11:1145 BEGIN -->

Requirement links: ARCH-003, INV-002, MODEL-001, SDI-001, SDI-004, ZONE-001, ZONE-002, ZIP-002, ZIP-003, SVC-002, ING-001, FAB-003, POL-001

<!-- SOURCE-BLOCK HB11:1145 END -->

<!-- SOURCE-BLOCK HB11:1146 BEGIN -->

<a id="test_CT_026"></a>

CT-026 — MZ, OOB and remote administration

<!-- SOURCE-BLOCK HB11:1146 END -->

<!-- SOURCE-BLOCK HB11:1147 BEGIN -->

Preconditions: Approved management architecture and recovery credentials.

<!-- SOURCE-BLOCK HB11:1147 END -->

<!-- SOURCE-BLOCK HB11:1148 BEGIN -->

Procedure: Trace remote privileged access through its authorized boundary; test workload isolation, ordinary browsing restriction and BMC access controls.

<!-- SOURCE-BLOCK HB11:1148 END -->

<!-- SOURCE-BLOCK HB11:1149 BEGIN -->

Expected outcome: MZ semantics and OOB transport remain distinct; only approved privileged paths reach management targets.

<!-- SOURCE-BLOCK HB11:1149 END -->

<!-- SOURCE-BLOCK HB11:1150 BEGIN -->

Evidence: Management diagrams, endpoint policy and session audit.

<!-- SOURCE-BLOCK HB11:1150 END -->

<!-- SOURCE-BLOCK HB11:1151 BEGIN -->

Mode: design-and-automated  \|  Cadence: qualification; management change  \|  Execution: not-run

<!-- SOURCE-BLOCK HB11:1151 END -->

<!-- SOURCE-BLOCK HB11:1152 BEGIN -->

Requirement links: ARCH-004, MODEL-002, TEN-002, ZIP-004, ZIP-005, MGT-001, MGT-002, MGT-005, IAM-002, FAB-004

<!-- SOURCE-BLOCK HB11:1152 END -->

<!-- SOURCE-BLOCK HB11:1153 BEGIN -->

<a id="test_CT_027"></a>

CT-027 — Break-glass and identity-provider loss

<!-- SOURCE-BLOCK HB11:1153 END -->

<!-- SOURCE-BLOCK HB11:1154 BEGIN -->

Preconditions: Approved emergency identity, dual-custodian procedure and test window.

<!-- SOURCE-BLOCK HB11:1154 END -->

<!-- SOURCE-BLOCK HB11:1155 BEGIN -->

Procedure: Make normal federation unavailable; exercise limited emergency access, alerting, revocation and post-use credential rotation.

<!-- SOURCE-BLOCK HB11:1155 END -->

<!-- SOURCE-BLOCK HB11:1156 BEGIN -->

Expected outcome: Access remains accountable and scoped; no shared anonymous administrator or permanent bypass is created.

<!-- SOURCE-BLOCK HB11:1156 END -->

<!-- SOURCE-BLOCK HB11:1157 BEGIN -->

Evidence: Emergency access log, custodial approval and revocation evidence.

<!-- SOURCE-BLOCK HB11:1157 END -->

<!-- SOURCE-BLOCK HB11:1158 BEGIN -->

Mode: controlled-fault  \|  Cadence: quarterly; identity change  \|  Execution: not-run

<!-- SOURCE-BLOCK HB11:1158 END -->

<!-- SOURCE-BLOCK HB11:1159 BEGIN -->

Requirement links: MGT-002, MGT-004, IAM-001, IAM-002, SEC-003, FAIL-002, FAIL-003

<!-- SOURCE-BLOCK HB11:1159 END -->

<!-- SOURCE-BLOCK HB11:1160 BEGIN -->

<a id="test_CT_028"></a>

CT-028 — Workload identity and certificate lifecycle

<!-- SOURCE-BLOCK HB11:1160 END -->

<!-- SOURCE-BLOCK HB11:1161 BEGIN -->

Preconditions: Scoped service identity, trusted CA and rotatable certificate.

<!-- SOURCE-BLOCK HB11:1161 END -->

<!-- SOURCE-BLOCK HB11:1162 BEGIN -->

Procedure: Rotate credentials/certificates; revoke the old identity and test an expired/untrusted certificate.

<!-- SOURCE-BLOCK HB11:1162 END -->

<!-- SOURCE-BLOCK HB11:1163 BEGIN -->

Expected outcome: Approved service continues with new material; old/revoked credentials are unusable within the accepted propagation interval.

<!-- SOURCE-BLOCK HB11:1163 END -->

<!-- SOURCE-BLOCK HB11:1164 BEGIN -->

Evidence: Issuer records, endpoint TLS results and revocation timeline.

<!-- SOURCE-BLOCK HB11:1164 END -->

<!-- SOURCE-BLOCK HB11:1165 BEGIN -->

Mode: automated  \|  Cadence: qualification; security-significant change  \|  Execution: not-run

<!-- SOURCE-BLOCK HB11:1165 END -->

<!-- SOURCE-BLOCK HB11:1166 BEGIN -->

Requirement links: SVC-003, IAM-001, IAM-003, CRY-001, CRY-003, SEC-003

<!-- SOURCE-BLOCK HB11:1166 END -->

<!-- SOURCE-BLOCK HB11:1167 BEGIN -->

<a id="test_CT_029"></a>

CT-029 — IPAM concurrency, overlap and exhaustion

<!-- SOURCE-BLOCK HB11:1167 END -->

<!-- SOURCE-BLOCK HB11:1168 BEGIN -->

Preconditions: Small disposable address pool and approved overlap policy.

<!-- SOURCE-BLOCK HB11:1168 END -->

<!-- SOURCE-BLOCK HB11:1169 BEGIN -->

Procedure: Issue concurrent allocations, exhaust the pool, retry requests and request a conflicting prefix.

<!-- SOURCE-BLOCK HB11:1169 END -->

<!-- SOURCE-BLOCK HB11:1170 BEGIN -->

Expected outcome: One authoritative reservation per allocation; retries are idempotent; exhaustion/unauthorized overlap stops provisioning.

<!-- SOURCE-BLOCK HB11:1170 END -->

<!-- SOURCE-BLOCK HB11:1171 BEGIN -->

Evidence: Allocation ledger, request IDs and conflict decisions.

<!-- SOURCE-BLOCK HB11:1171 END -->

<!-- SOURCE-BLOCK HB11:1172 BEGIN -->

Mode: automated  \|  Cadence: qualification; security-significant change  \|  Execution: not-run

<!-- SOURCE-BLOCK HB11:1172 END -->

<!-- SOURCE-BLOCK HB11:1173 BEGIN -->

Requirement links: IPAM-001, IPAM-002, IPAM-004, AUTO-001

<!-- SOURCE-BLOCK HB11:1173 END -->

<!-- SOURCE-BLOCK HB11:1174 BEGIN -->

<a id="test_CT_030"></a>

CT-030 — DNS/DHCP lifecycle and reuse

<!-- SOURCE-BLOCK HB11:1174 END -->

<!-- SOURCE-BLOCK HB11:1175 BEGIN -->

Preconditions: Forward/reverse zones, address lease policy and reusable test address.

<!-- SOURCE-BLOCK HB11:1175 END -->

<!-- SOURCE-BLOCK HB11:1176 BEGIN -->

Procedure: Provision, rename, recover and retire a network endpoint; confirm lease/DNS reconciliation and address quarantine.

<!-- SOURCE-BLOCK HB11:1176 END -->

<!-- SOURCE-BLOCK HB11:1177 BEGIN -->

Expected outcome: No duplicate active ownership or premature reuse; stale records disappear within the approved timing profile.

<!-- SOURCE-BLOCK HB11:1177 END -->

<!-- SOURCE-BLOCK HB11:1178 BEGIN -->

Evidence: DNS/DHCP/IPAM timelines and ownership comparisons.

<!-- SOURCE-BLOCK HB11:1178 END -->

<!-- SOURCE-BLOCK HB11:1179 BEGIN -->

Mode: automated  \|  Cadence: qualification; security-significant change  \|  Execution: not-run

<!-- SOURCE-BLOCK HB11:1179 END -->

<!-- SOURCE-BLOCK HB11:1180 BEGIN -->

Requirement links: IPAM-001, IPAM-003, IPAM-004

<!-- SOURCE-BLOCK HB11:1180 END -->

<!-- SOURCE-BLOCK HB11:1181 BEGIN -->

<a id="test_CT_031"></a>

CT-031 — IPv6 local control and IPv4-only posture

<!-- SOURCE-BLOCK HB11:1181 END -->

<!-- SOURCE-BLOCK HB11:1182 BEGIN -->

Preconditions: Platform offers either a dual-stack or explicit IPv4-only profile.

<!-- SOURCE-BLOCK HB11:1182 END -->

<!-- SOURCE-BLOCK HB11:1183 BEGIN -->

Procedure: Check router advertisements, neighbor discovery, DHCPv6, source validation and unapproved transition paths; preserve required ICMPv6.

<!-- SOURCE-BLOCK HB11:1183 END -->

<!-- SOURCE-BLOCK HB11:1184 BEGIN -->

Expected outcome: No alternate-protocol bypass; enabled IPv6 works correctly and disabled service does not create ungoverned reachability.

<!-- SOURCE-BLOCK HB11:1184 END -->

<!-- SOURCE-BLOCK HB11:1185 BEGIN -->

Evidence: Protocol-specific controls, probes and qualification result.

<!-- SOURCE-BLOCK HB11:1185 END -->

<!-- SOURCE-BLOCK HB11:1186 BEGIN -->

Mode: automated  \|  Cadence: qualification; security-significant change  \|  Execution: not-run

<!-- SOURCE-BLOCK HB11:1186 END -->

<!-- SOURCE-BLOCK HB11:1187 BEGIN -->

Requirement links: RTE-004, IPV6-001, IPV6-002, IPV6-003

<!-- SOURCE-BLOCK HB11:1187 END -->

<!-- SOURCE-BLOCK HB11:1188 BEGIN -->

<a id="test_CT_032"></a>

CT-032 — MTU and path-MTU discovery

<!-- SOURCE-BLOCK HB11:1188 END -->

<!-- SOURCE-BLOCK HB11:1189 BEGIN -->

Preconditions: Known encapsulation stack and both local/remote paths.

<!-- SOURCE-BLOCK HB11:1189 END -->

<!-- SOURCE-BLOCK HB11:1190 BEGIN -->

Procedure: Test supported workload packet sizes end-to-end, including security edge, nested overlay if offered and recovery site.

<!-- SOURCE-BLOCK HB11:1190 END -->

<!-- SOURCE-BLOCK HB11:1191 BEGIN -->

Expected outcome: Accepted MTU is reachable without silent black holes; required PMTU feedback is delivered or a documented alternative works.

<!-- SOURCE-BLOCK HB11:1191 END -->

<!-- SOURCE-BLOCK HB11:1192 BEGIN -->

Evidence: Packet-size matrix, encapsulation budget and loss traces.

<!-- SOURCE-BLOCK HB11:1192 END -->

<!-- SOURCE-BLOCK HB11:1193 BEGIN -->

Mode: automated  \|  Cadence: qualification; security-significant change  \|  Execution: not-run

<!-- SOURCE-BLOCK HB11:1193 END -->

<!-- SOURCE-BLOCK HB11:1194 BEGIN -->

Requirement links: IPV6-001, IPV6-003, EDGE-001, FAB-004, EVPN-002

<!-- SOURCE-BLOCK HB11:1194 END -->

<!-- SOURCE-BLOCK HB11:1195 BEGIN -->

<a id="test_CT_033"></a>

CT-033 — BGP and EVPN import/export boundaries

<!-- SOURCE-BLOCK HB11:1195 END -->

<!-- SOURCE-BLOCK HB11:1196 BEGIN -->

Preconditions: Provider-owned non-production peers and known approved routes.

<!-- SOURCE-BLOCK HB11:1196 END -->

<!-- SOURCE-BLOCK HB11:1197 BEGIN -->

Procedure: Validate neighbor authentication/control-plane limits; advertise bounded unauthorized test prefixes/route targets through the test fixture.

<!-- SOURCE-BLOCK HB11:1197 END -->

<!-- SOURCE-BLOCK HB11:1198 BEGIN -->

Expected outcome: Only authorized advertisements install; route leaks, excess prefixes and unapproved defaults are rejected and alerted.

<!-- SOURCE-BLOCK HB11:1198 END -->

<!-- SOURCE-BLOCK HB11:1199 BEGIN -->

Evidence: Neighbor config, route-policy results and RIB/FIB diff.

<!-- SOURCE-BLOCK HB11:1199 END -->

<!-- SOURCE-BLOCK HB11:1200 BEGIN -->

Mode: automated  \|  Cadence: qualification; security-significant change  \|  Execution: not-run

<!-- SOURCE-BLOCK HB11:1200 END -->

<!-- SOURCE-BLOCK HB11:1201 BEGIN -->

Requirement links: INV-003, RTE-001, FAB-004, EVPN-001

<!-- SOURCE-BLOCK HB11:1201 END -->

<!-- SOURCE-BLOCK HB11:1202 BEGIN -->

<a id="test_CT_034"></a>

CT-034 — Leaf/link and multihoming failures

<!-- SOURCE-BLOCK HB11:1202 END -->

<!-- SOURCE-BLOCK HB11:1203 BEGIN -->

Preconditions: Approved MLAG or EVPN multihoming profile; topology-specific rollback.

<!-- SOURCE-BLOCK HB11:1203 END -->

<!-- SOURCE-BLOCK HB11:1204 BEGIN -->

Procedure: Fail an uplink, peer link, keepalive or Ethernet-segment member individually, then restore it; test split-brain containment.

<!-- SOURCE-BLOCK HB11:1204 END -->

<!-- SOURCE-BLOCK HB11:1205 BEGIN -->

Expected outcome: No loop, unintended duplicate forwarding or security bypass; measured convergence meets the fabric profile.

<!-- SOURCE-BLOCK HB11:1205 END -->

<!-- SOURCE-BLOCK HB11:1206 BEGIN -->

Evidence: Fault timeline, MAC/route state, packet-loss and control-plane telemetry.

<!-- SOURCE-BLOCK HB11:1206 END -->

<!-- SOURCE-BLOCK HB11:1207 BEGIN -->

Mode: controlled-fault  \|  Cadence: qualification; fabric upgrade  \|  Execution: not-run

<!-- SOURCE-BLOCK HB11:1207 END -->

<!-- SOURCE-BLOCK HB11:1208 BEGIN -->

Requirement links: FAB-004, EVPN-002, TEST-004

<!-- SOURCE-BLOCK HB11:1208 END -->

<!-- SOURCE-BLOCK HB11:1209 BEGIN -->

<a id="test_CT_035"></a>

CT-035 — Compute co-residency and evacuation

<!-- SOURCE-BLOCK HB11:1209 END -->

<!-- SOURCE-BLOCK HB11:1210 BEGIN -->

Preconditions: Placement policy names tenant/domain/zone host-sharing boundaries.

<!-- SOURCE-BLOCK HB11:1210 END -->

<!-- SOURCE-BLOCK HB11:1211 BEGIN -->

Procedure: Attempt disallowed placement and evacuate a host; repeat after a scheduler restart.

<!-- SOURCE-BLOCK HB11:1211 END -->

<!-- SOURCE-BLOCK HB11:1212 BEGIN -->

Expected outcome: Placement, migration and HA restart all preserve the approved co-residency rules; insufficient eligible capacity rejects the action.

<!-- SOURCE-BLOCK HB11:1212 END -->

<!-- SOURCE-BLOCK HB11:1213 BEGIN -->

Evidence: Scheduler decisions, host inventory and policy references.

<!-- SOURCE-BLOCK HB11:1213 END -->

<!-- SOURCE-BLOCK HB11:1214 BEGIN -->

Mode: automated  \|  Cadence: qualification; security-significant change  \|  Execution: not-run

<!-- SOURCE-BLOCK HB11:1214 END -->

<!-- SOURCE-BLOCK HB11:1215 BEGIN -->

Requirement links: THR-001, SDI-001, SDI-003, SDI-004, ZIP-005, SITE-004, CMP-001, CMP-003, PLACE-001, FUT-003, ASSUR-001, ASSUR-002

<!-- SOURCE-BLOCK HB11:1215 END -->

<!-- SOURCE-BLOCK HB11:1216 BEGIN -->

<a id="test_CT_036"></a>

CT-036 — Hypervisor and firmware baseline

<!-- SOURCE-BLOCK HB11:1216 END -->

<!-- SOURCE-BLOCK HB11:1217 BEGIN -->

Preconditions: Supported hardware/software tuple and security baseline.

<!-- SOURCE-BLOCK HB11:1217 END -->

<!-- SOURCE-BLOCK HB11:1218 BEGIN -->

Procedure: Verify secure boot/attestation where required, disabled unnecessary services, administrative separation and inventory of firmware/drivers.

<!-- SOURCE-BLOCK HB11:1218 END -->

<!-- SOURCE-BLOCK HB11:1219 BEGIN -->

Expected outcome: All mandatory baseline items are enforced; unsupported or unattested hosts are ineligible for the affected profile.

<!-- SOURCE-BLOCK HB11:1219 END -->

<!-- SOURCE-BLOCK HB11:1220 BEGIN -->

Evidence: Baseline report, attestation/config output and exception ledger.

<!-- SOURCE-BLOCK HB11:1220 END -->

<!-- SOURCE-BLOCK HB11:1221 BEGIN -->

Mode: design-and-automated  \|  Cadence: qualification; host onboarding; scheduled  \|  Execution: not-run

<!-- SOURCE-BLOCK HB11:1221 END -->

<!-- SOURCE-BLOCK HB11:1222 BEGIN -->

Requirement links: CMP-002, IMG-001, IMG-002

<!-- SOURCE-BLOCK HB11:1222 END -->

<!-- SOURCE-BLOCK HB11:1223 BEGIN -->

<a id="test_CT_037"></a>

CT-037 — Storage tenant isolation

<!-- SOURCE-BLOCK HB11:1223 END -->

<!-- SOURCE-BLOCK HB11:1224 BEGIN -->

Preconditions: Two tenants with block/file/object resources and separate access identities.

<!-- SOURCE-BLOCK HB11:1224 END -->

<!-- SOURCE-BLOCK HB11:1225 BEGIN -->

Procedure: Attempt foreign volume attachment, snapshot clone, file access and object access; include backup/export paths.

<!-- SOURCE-BLOCK HB11:1225 END -->

<!-- SOURCE-BLOCK HB11:1226 BEGIN -->

Expected outcome: Only the owning or explicitly authorized scope accesses data; no clone or mount circumvents zone/categorization policy.

<!-- SOURCE-BLOCK HB11:1226 END -->

<!-- SOURCE-BLOCK HB11:1227 BEGIN -->

Evidence: API decisions, storage ACLs and data-path tests.

<!-- SOURCE-BLOCK HB11:1227 END -->

<!-- SOURCE-BLOCK HB11:1228 BEGIN -->

Mode: automated  \|  Cadence: qualification; security-significant change  \|  Execution: not-run

<!-- SOURCE-BLOCK HB11:1228 END -->

<!-- SOURCE-BLOCK HB11:1229 BEGIN -->

Requirement links: SVC-001, STO-001, FUT-003, ASSUR-002

<!-- SOURCE-BLOCK HB11:1229 END -->

<!-- SOURCE-BLOCK HB11:1230 BEGIN -->

<a id="test_CT_038"></a>

CT-038 — Encryption, key isolation and KMS outage

<!-- SOURCE-BLOCK HB11:1230 END -->

<!-- SOURCE-BLOCK HB11:1231 BEGIN -->

Preconditions: Qualified cryptographic profile; disposable encrypted data and test key.

<!-- SOURCE-BLOCK HB11:1231 END -->

<!-- SOURCE-BLOCK HB11:1232 BEGIN -->

Procedure: Validate encryption context and key-use permissions; rotate a test key and remove KMS connectivity under the approved runbook.

<!-- SOURCE-BLOCK HB11:1232 END -->

<!-- SOURCE-BLOCK HB11:1233 BEGIN -->

Expected outcome: No unauthorized decrypt or plaintext fallback; documented cache/restart behavior matches policy; recovery preserves authorized data.

<!-- SOURCE-BLOCK HB11:1233 END -->

<!-- SOURCE-BLOCK HB11:1234 BEGIN -->

Evidence: Crypto configuration, key audit, outage timeline and recovery test.

<!-- SOURCE-BLOCK HB11:1234 END -->

<!-- SOURCE-BLOCK HB11:1235 BEGIN -->

Mode: controlled-fault  \|  Cadence: qualification; key-service change  \|  Execution: not-run

<!-- SOURCE-BLOCK HB11:1235 END -->

<!-- SOURCE-BLOCK HB11:1236 BEGIN -->

Requirement links: SITE-004, CRY-001, CRY-002, CRY-003, BKP-004, FAIL-002, FAIL-003

<!-- SOURCE-BLOCK HB11:1236 END -->

<!-- SOURCE-BLOCK HB11:1237 BEGIN -->

<a id="test_CT_039"></a>

CT-039 — Storage performance and contention

<!-- SOURCE-BLOCK HB11:1237 END -->

<!-- SOURCE-BLOCK HB11:1238 BEGIN -->

Preconditions: Defined capacity/latency/throughput class and bounded load generators.

<!-- SOURCE-BLOCK HB11:1238 END -->

<!-- SOURCE-BLOCK HB11:1239 BEGIN -->

Procedure: Measure steady load, contention and rebuild/degraded state with the same workload data pattern.

<!-- SOURCE-BLOCK HB11:1239 END -->

<!-- SOURCE-BLOCK HB11:1240 BEGIN -->

Expected outcome: Class limits and protected minimums hold under the accepted failure budget; overload rejects growth rather than bypassing controls.

<!-- SOURCE-BLOCK HB11:1240 END -->

<!-- SOURCE-BLOCK HB11:1241 BEGIN -->

Evidence: Latency percentiles, IOPS/throughput, capacity and noisy-neighbor results.

<!-- SOURCE-BLOCK HB11:1241 END -->

<!-- SOURCE-BLOCK HB11:1242 BEGIN -->

Mode: automated  \|  Cadence: qualification; security-significant change  \|  Execution: not-run

<!-- SOURCE-BLOCK HB11:1242 END -->

<!-- SOURCE-BLOCK HB11:1243 BEGIN -->

Requirement links: CMP-002, STO-002, REL-002, CAP-002

<!-- SOURCE-BLOCK HB11:1243 END -->

<!-- SOURCE-BLOCK HB11:1244 BEGIN -->

<a id="test_CT_040"></a>

CT-040 — Golden image provenance

<!-- SOURCE-BLOCK HB11:1244 END -->

<!-- SOURCE-BLOCK HB11:1245 BEGIN -->

Preconditions: Approved image digest, build manifest and denied image fixture.

<!-- SOURCE-BLOCK HB11:1245 END -->

<!-- SOURCE-BLOCK HB11:1246 BEGIN -->

Procedure: Verify signature/provenance, scan status, boot mode and hardening; attempt deployment of retired/tampered images.

<!-- SOURCE-BLOCK HB11:1246 END -->

<!-- SOURCE-BLOCK HB11:1247 BEGIN -->

Expected outcome: Only eligible images deploy; exceptions are explicit; rebuild output links to its source and component inventory.

<!-- SOURCE-BLOCK HB11:1247 END -->

<!-- SOURCE-BLOCK HB11:1248 BEGIN -->

Evidence: Image manifest, signature validation, scan and admission decisions.

<!-- SOURCE-BLOCK HB11:1248 END -->

<!-- SOURCE-BLOCK HB11:1249 BEGIN -->

Mode: automated  \|  Cadence: qualification; security-significant change  \|  Execution: not-run

<!-- SOURCE-BLOCK HB11:1249 END -->

<!-- SOURCE-BLOCK HB11:1250 BEGIN -->

Requirement links: IMG-001, IMG-002, VULN-002

<!-- SOURCE-BLOCK HB11:1250 END -->

<!-- SOURCE-BLOCK HB11:1251 BEGIN -->

<a id="test_CT_041"></a>

CT-041 — Patch and vulnerability lifecycle

<!-- SOURCE-BLOCK HB11:1251 END -->

<!-- SOURCE-BLOCK HB11:1252 BEGIN -->

Preconditions: Inventory, severity policy and an approved non-production patch scenario.

<!-- SOURCE-BLOCK HB11:1252 END -->

<!-- SOURCE-BLOCK HB11:1253 BEGIN -->

Procedure: Create a finding, classify exposure, execute canary remediation, verify fix and record time against the selected deadline.

<!-- SOURCE-BLOCK HB11:1253 END -->

<!-- SOURCE-BLOCK HB11:1254 BEGIN -->

Expected outcome: No asset or firmware layer is omitted; overdue risk escalates; roll-forward/rollback preserves service and security.

<!-- SOURCE-BLOCK HB11:1254 END -->

<!-- SOURCE-BLOCK HB11:1255 BEGIN -->

Evidence: Finding-to-change-to-verification chain and deadline report.

<!-- SOURCE-BLOCK HB11:1255 END -->

<!-- SOURCE-BLOCK HB11:1256 BEGIN -->

Mode: automated  \|  Cadence: qualification; security-significant change  \|  Execution: not-run

<!-- SOURCE-BLOCK HB11:1256 END -->

<!-- SOURCE-BLOCK HB11:1257 BEGIN -->

Requirement links: IMG-001, SUP-001, VULN-001, VULN-002

<!-- SOURCE-BLOCK HB11:1257 END -->

<!-- SOURCE-BLOCK HB11:1258 BEGIN -->

<a id="test_CT_042"></a>

CT-042 — Supply-chain and package provenance

<!-- SOURCE-BLOCK HB11:1258 END -->

<!-- SOURCE-BLOCK HB11:1259 BEGIN -->

Preconditions: Approved provider/module mirror and a tampered package fixture.

<!-- SOURCE-BLOCK HB11:1259 END -->

<!-- SOURCE-BLOCK HB11:1260 BEGIN -->

Procedure: Verify package checksums, immutable module references and execution image; test rejection of an unapproved provider/module source.

<!-- SOURCE-BLOCK HB11:1260 END -->

<!-- SOURCE-BLOCK HB11:1261 BEGIN -->

Expected outcome: Tampered/unapproved artifacts never reach a privileged apply; lockfile changes require reviewed provenance.

<!-- SOURCE-BLOCK HB11:1261 END -->

<!-- SOURCE-BLOCK HB11:1262 BEGIN -->

Evidence: Package manifests, verification output and CI policy decision.

<!-- SOURCE-BLOCK HB11:1262 END -->

<!-- SOURCE-BLOCK HB11:1263 BEGIN -->

Mode: automated  \|  Cadence: qualification; security-significant change  \|  Execution: not-run

<!-- SOURCE-BLOCK HB11:1263 END -->

<!-- SOURCE-BLOCK HB11:1264 BEGIN -->

Requirement links: TF-001, TF-002, TF-005, CICD-002, SUP-001, VULN-001, VULN-002

<!-- SOURCE-BLOCK HB11:1264 END -->

<!-- SOURCE-BLOCK HB11:1265 BEGIN -->

<a id="test_CT_043"></a>

CT-043 — Terraform plan and state confidentiality

<!-- SOURCE-BLOCK HB11:1265 END -->

<!-- SOURCE-BLOCK HB11:1266 BEGIN -->

Preconditions: Disposable secrets and restricted plan/state storage.

<!-- SOURCE-BLOCK HB11:1266 END -->

<!-- SOURCE-BLOCK HB11:1267 BEGIN -->

Procedure: Inspect source, logs, binary/JSON plan and state using controlled test values; verify supported ephemeral/write-only behavior.

<!-- SOURCE-BLOCK HB11:1267 END -->

<!-- SOURCE-BLOCK HB11:1268 BEGIN -->

Expected outcome: Secrets are absent where promised; unavoidable secret-bearing artifacts remain encrypted, access-controlled and redacted from logs.

<!-- SOURCE-BLOCK HB11:1268 END -->

<!-- SOURCE-BLOCK HB11:1269 BEGIN -->

Evidence: Secret-handling scan, backend ACLs and artifact classification.

<!-- SOURCE-BLOCK HB11:1269 END -->

<!-- SOURCE-BLOCK HB11:1270 BEGIN -->

Mode: automated  \|  Cadence: qualification; security-significant change  \|  Execution: not-run

<!-- SOURCE-BLOCK HB11:1270 END -->

<!-- SOURCE-BLOCK HB11:1271 BEGIN -->

Requirement links: TF-001, STATE-002, SEC-001, SEC-003, SEC-004

<!-- SOURCE-BLOCK HB11:1271 END -->

<!-- SOURCE-BLOCK HB11:1272 BEGIN -->

<a id="test_CT_044"></a>

CT-044 — State locking, recovery and grants

<!-- SOURCE-BLOCK HB11:1272 END -->

<!-- SOURCE-BLOCK HB11:1273 BEGIN -->

Preconditions: Two authorized runners, versioned state and documented lock recovery.

<!-- SOURCE-BLOCK HB11:1273 END -->

<!-- SOURCE-BLOCK HB11:1274 BEGIN -->

Procedure: Race updates to one state, restore a known state version in isolation and test a workload runner against foundation state.

<!-- SOURCE-BLOCK HB11:1274 END -->

<!-- SOURCE-BLOCK HB11:1275 BEGIN -->

Expected outcome: Only one writer operates; restore is auditable; unauthorized state reads/writes fail; state rollback is not misrepresented as resource rollback.

<!-- SOURCE-BLOCK HB11:1275 END -->

<!-- SOURCE-BLOCK HB11:1276 BEGIN -->

Evidence: Lock timeline, recovery report and access decisions.

<!-- SOURCE-BLOCK HB11:1276 END -->

<!-- SOURCE-BLOCK HB11:1277 BEGIN -->

Mode: automated  \|  Cadence: qualification; security-significant change  \|  Execution: not-run

<!-- SOURCE-BLOCK HB11:1277 END -->

<!-- SOURCE-BLOCK HB11:1278 BEGIN -->

Requirement links: MGT-003, TF-003, TF-004, STATE-001, STATE-002, STATE-003, SEC-002, SEC-004, FAIL-003

<!-- SOURCE-BLOCK HB11:1278 END -->

<!-- SOURCE-BLOCK HB11:1279 BEGIN -->

<a id="test_CT_045"></a>

CT-045 — Partial apply and compensation

<!-- SOURCE-BLOCK HB11:1279 END -->

<!-- SOURCE-BLOCK HB11:1280 BEGIN -->

Preconditions: Disposable multi-stage deployment and a failure-injection point.

<!-- SOURCE-BLOCK HB11:1280 END -->

<!-- SOURCE-BLOCK HB11:1281 BEGIN -->

Procedure: Interrupt after allocation or one provider action; restart with the same operation ID and observe discovery/repair.

<!-- SOURCE-BLOCK HB11:1281 END -->

<!-- SOURCE-BLOCK HB11:1282 BEGIN -->

Expected outcome: No duplicate allocation or accidental destruction; unfinished resources remain quarantined; the journal supports safe resume or controlled compensation.

<!-- SOURCE-BLOCK HB11:1282 END -->

<!-- SOURCE-BLOCK HB11:1283 BEGIN -->

Evidence: Operation journal, state generations and residual-resource scan.

<!-- SOURCE-BLOCK HB11:1283 END -->

<!-- SOURCE-BLOCK HB11:1284 BEGIN -->

Mode: controlled-fault  \|  Cadence: controller/adapter change  \|  Execution: not-run

<!-- SOURCE-BLOCK HB11:1284 END -->

<!-- SOURCE-BLOCK HB11:1285 BEGIN -->

Requirement links: INV-007, IPAM-004, NUT-004, AUTO-001, AUTO-002, AUTO-003, STATE-003

<!-- SOURCE-BLOCK HB11:1285 END -->

<!-- SOURCE-BLOCK HB11:1286 BEGIN -->

<a id="test_CT_046"></a>

CT-046 — Retries, optimistic concurrency and idempotency

<!-- SOURCE-BLOCK HB11:1286 END -->

<!-- SOURCE-BLOCK HB11:1287 BEGIN -->

Preconditions: Controller accepts request ID and expected resource generation.

<!-- SOURCE-BLOCK HB11:1287 END -->

<!-- SOURCE-BLOCK HB11:1288 BEGIN -->

Procedure: Replay an operation, submit stale updates, and interrupt response delivery after successful allocation.

<!-- SOURCE-BLOCK HB11:1288 END -->

<!-- SOURCE-BLOCK HB11:1289 BEGIN -->

Expected outcome: Replay returns the existing operation; stale updates conflict; one desired generation yields one accountable realization.

<!-- SOURCE-BLOCK HB11:1289 END -->

<!-- SOURCE-BLOCK HB11:1290 BEGIN -->

Evidence: API responses, generation history and allocation counts.

<!-- SOURCE-BLOCK HB11:1290 END -->

<!-- SOURCE-BLOCK HB11:1291 BEGIN -->

Mode: automated  \|  Cadence: each controller change  \|  Execution: not-run

<!-- SOURCE-BLOCK HB11:1291 END -->

<!-- SOURCE-BLOCK HB11:1292 BEGIN -->

Requirement links: IPAM-004, API-003, AUTO-002, AUTO-003

<!-- SOURCE-BLOCK HB11:1292 END -->

<!-- SOURCE-BLOCK HB11:1293 BEGIN -->

<a id="test_CT_047"></a>

CT-047 — API rate limit and backpressure

<!-- SOURCE-BLOCK HB11:1293 END -->

<!-- SOURCE-BLOCK HB11:1294 BEGIN -->

Preconditions: Finite controller queue and test provider throttling.

<!-- SOURCE-BLOCK HB11:1294 END -->

<!-- SOURCE-BLOCK HB11:1295 BEGIN -->

Procedure: Increase authorized test demand to the configured limit; inject retryable throttling/timeouts and permanent errors.

<!-- SOURCE-BLOCK HB11:1295 END -->

<!-- SOURCE-BLOCK HB11:1296 BEGIN -->

Expected outcome: Backpressure is visible and bounded; retry honors policy/jitter; permanent errors do not loop indefinitely or consume unbounded capacity.

<!-- SOURCE-BLOCK HB11:1296 END -->

<!-- SOURCE-BLOCK HB11:1297 BEGIN -->

Evidence: Queue metrics, retries, deadlines and final operation states.

<!-- SOURCE-BLOCK HB11:1297 END -->

<!-- SOURCE-BLOCK HB11:1298 BEGIN -->

Mode: automated  \|  Cadence: qualification; security-significant change  \|  Execution: not-run

<!-- SOURCE-BLOCK HB11:1298 END -->

<!-- SOURCE-BLOCK HB11:1299 BEGIN -->

Requirement links: AUTO-003, CAP-002

<!-- SOURCE-BLOCK HB11:1299 END -->

<!-- SOURCE-BLOCK HB11:1300 BEGIN -->

<a id="test_CT_048"></a>

CT-048 — Approved-plan freshness

<!-- SOURCE-BLOCK HB11:1300 END -->

<!-- SOURCE-BLOCK HB11:1301 BEGIN -->

Preconditions: Signed plan, immutable inputs and an intervening policy or state change.

<!-- SOURCE-BLOCK HB11:1301 END -->

<!-- SOURCE-BLOCK HB11:1302 BEGIN -->

Procedure: Change state generation, policy bundle or approval-sensitive intent after planning; try to apply the old artifact.

<!-- SOURCE-BLOCK HB11:1302 END -->

<!-- SOURCE-BLOCK HB11:1303 BEGIN -->

Expected outcome: Stale/unapproved plans are rejected and replanned; approved artifacts bind source, inputs, policy, identity and expiration.

<!-- SOURCE-BLOCK HB11:1303 END -->

<!-- SOURCE-BLOCK HB11:1304 BEGIN -->

Evidence: Plan digest, approvals and rejected apply audit.

<!-- SOURCE-BLOCK HB11:1304 END -->

<!-- SOURCE-BLOCK HB11:1305 BEGIN -->

Mode: automated  \|  Cadence: qualification; security-significant change  \|  Execution: not-run

<!-- SOURCE-BLOCK HB11:1305 END -->

<!-- SOURCE-BLOCK HB11:1306 BEGIN -->

Requirement links: SDI-004, POL-002, AUTO-002, TF-002, TF-005, CICD-001, CICD-002, EVID-002

<!-- SOURCE-BLOCK HB11:1306 END -->

<!-- SOURCE-BLOCK HB11:1307 BEGIN -->

<a id="test_CT_049"></a>

CT-049 — Evidence integrity and authorization separation

<!-- SOURCE-BLOCK HB11:1307 END -->

<!-- SOURCE-BLOCK HB11:1308 BEGIN -->

Preconditions: Signed evidence manifest and separately signed authorization decision.

<!-- SOURCE-BLOCK HB11:1308 END -->

<!-- SOURCE-BLOCK HB11:1309 BEGIN -->

Procedure: Tamper with an artifact; expire a decision; fail a technical test while preserving the historical authorization record.

<!-- SOURCE-BLOCK HB11:1309 END -->

<!-- SOURCE-BLOCK HB11:1310 BEGIN -->

Expected outcome: Tampering is detected; technical status never self-issues authorization; readiness follows current evidence and decision conditions.

<!-- SOURCE-BLOCK HB11:1310 END -->

<!-- SOURCE-BLOCK HB11:1311 BEGIN -->

Evidence: Digests/signature checks, readiness evaluation and decision history.

<!-- SOURCE-BLOCK HB11:1311 END -->

<!-- SOURCE-BLOCK HB11:1312 BEGIN -->

Mode: automated  \|  Cadence: qualification; security-significant change  \|  Execution: not-run

<!-- SOURCE-BLOCK HB11:1312 END -->

<!-- SOURCE-BLOCK HB11:1313 BEGIN -->

Requirement links: INV-006, AUTH-001, DRIFT-001, TEST-003, EVID-001, EVID-002, EVID-003, OBS-001, IR-002, ONB-001, ACPT-001

<!-- SOURCE-BLOCK HB11:1313 END -->

<!-- SOURCE-BLOCK HB11:1314 BEGIN -->

<a id="test_CT_050"></a>

CT-050 — Telemetry outage, buffering and retention

<!-- SOURCE-BLOCK HB11:1314 END -->

<!-- SOURCE-BLOCK HB11:1315 BEGIN -->

Preconditions: Logging profile specifies export latency, buffer limits and retention/disposal policy.

<!-- SOURCE-BLOCK HB11:1315 END -->

<!-- SOURCE-BLOCK HB11:1316 BEGIN -->

Procedure: Disconnect the collector; generate bounded events; restore connectivity and reconcile sequence/time gaps.

<!-- SOURCE-BLOCK HB11:1316 END -->

<!-- SOURCE-BLOCK HB11:1317 BEGIN -->

Expected outcome: Loss/overflow is alerted; buffering behavior matches profile; mandatory evidence gaps are visible; no silent control bypass.

<!-- SOURCE-BLOCK HB11:1317 END -->

<!-- SOURCE-BLOCK HB11:1318 BEGIN -->

Evidence: Buffer metrics, event reconciliation and retention configuration.

<!-- SOURCE-BLOCK HB11:1318 END -->

<!-- SOURCE-BLOCK HB11:1319 BEGIN -->

Mode: controlled-fault  \|  Cadence: qualification; logging change  \|  Execution: not-run

<!-- SOURCE-BLOCK HB11:1319 END -->

<!-- SOURCE-BLOCK HB11:1320 BEGIN -->

Requirement links: OBS-002, OBS-003, FAIL-002, FAIL-003

<!-- SOURCE-BLOCK HB11:1320 END -->

<!-- SOURCE-BLOCK HB11:1321 BEGIN -->

<a id="test_CT_051"></a>

CT-051 — Backup administrative separation and immutability

<!-- SOURCE-BLOCK HB11:1321 END -->

<!-- SOURCE-BLOCK HB11:1322 BEGIN -->

Preconditions: Test backup policy includes an isolated locked copy.

<!-- SOURCE-BLOCK HB11:1322 END -->

<!-- SOURCE-BLOCK HB11:1323 BEGIN -->

Procedure: Try deletion or retention reduction with production and backup-operator identities; test approved custodial operations separately.

<!-- SOURCE-BLOCK HB11:1323 END -->

<!-- SOURCE-BLOCK HB11:1324 BEGIN -->

Expected outcome: Compromised production authority cannot alter the protected copy or its retention; authorized actions are separately accountable.

<!-- SOURCE-BLOCK HB11:1324 END -->

<!-- SOURCE-BLOCK HB11:1325 BEGIN -->

Evidence: Role tests, object-lock/immutability configuration and audit.

<!-- SOURCE-BLOCK HB11:1325 END -->

<!-- SOURCE-BLOCK HB11:1326 BEGIN -->

Mode: automated  \|  Cadence: qualification; security-significant change  \|  Execution: not-run

<!-- SOURCE-BLOCK HB11:1326 END -->

<!-- SOURCE-BLOCK HB11:1327 BEGIN -->

Requirement links: BKP-001, BKP-003, BKP-004

<!-- SOURCE-BLOCK HB11:1327 END -->

<!-- SOURCE-BLOCK HB11:1328 BEGIN -->

<a id="test_CT_052"></a>

CT-052 — Application-consistent isolated restore

<!-- SOURCE-BLOCK HB11:1328 END -->

<!-- SOURCE-BLOCK HB11:1329 BEGIN -->

Preconditions: Known application dataset, consistency markers and accepted RTO/RPO.

<!-- SOURCE-BLOCK HB11:1329 END -->

<!-- SOURCE-BLOCK HB11:1330 BEGIN -->

Procedure: Restore to an isolated recovery domain; verify integrity, application start and required dependencies before controlled reconnection.

<!-- SOURCE-BLOCK HB11:1330 END -->

<!-- SOURCE-BLOCK HB11:1331 BEGIN -->

Expected outcome: Recovered data meets consistency/RPO and recovery timing; no production connection appears until authorized.

<!-- SOURCE-BLOCK HB11:1331 END -->

<!-- SOURCE-BLOCK HB11:1332 BEGIN -->

Evidence: Recovery timestamps, integrity markers, application checks and isolation probes.

<!-- SOURCE-BLOCK HB11:1332 END -->

<!-- SOURCE-BLOCK HB11:1333 BEGIN -->

Mode: controlled-recovery  \|  Cadence: quarterly; material application change  \|  Execution: not-run

<!-- SOURCE-BLOCK HB11:1333 END -->

<!-- SOURCE-BLOCK HB11:1334 BEGIN -->

Requirement links: SITE-003, STO-002, BKP-002, BKP-003, REL-001, FAIL-001, REC-001, REC-002, DEL-001

<!-- SOURCE-BLOCK HB11:1334 END -->

<!-- SOURCE-BLOCK HB11:1335 BEGIN -->

<a id="test_CT_053"></a>

CT-053 — Backup retention, holds and key survival

<!-- SOURCE-BLOCK HB11:1335 END -->

<!-- SOURCE-BLOCK HB11:1336 BEGIN -->

Preconditions: A test hold, expiring backup and keys needed by retained copies.

<!-- SOURCE-BLOCK HB11:1336 END -->

<!-- SOURCE-BLOCK HB11:1337 BEGIN -->

Procedure: Retire the WSD while retaining the held copy; attempt key deletion and validate an authorized restore of retained data.

<!-- SOURCE-BLOCK HB11:1337 END -->

<!-- SOURCE-BLOCK HB11:1338 BEGIN -->

Expected outcome: Hold and retention are enforced; key lifetime supports required recovery; data is not prematurely destroyed.

<!-- SOURCE-BLOCK HB11:1338 END -->

<!-- SOURCE-BLOCK HB11:1339 BEGIN -->

Evidence: Hold/retention decision, key dependencies and restore evidence.

<!-- SOURCE-BLOCK HB11:1339 END -->

<!-- SOURCE-BLOCK HB11:1340 BEGIN -->

Mode: automated  \|  Cadence: qualification; security-significant change  \|  Execution: not-run

<!-- SOURCE-BLOCK HB11:1340 END -->

<!-- SOURCE-BLOCK HB11:1341 BEGIN -->

Requirement links: STO-001, STO-003, CRY-002, BKP-003, BKP-004, LIFE-002, LIFE-003

<!-- SOURCE-BLOCK HB11:1341 END -->

<!-- SOURCE-BLOCK HB11:1342 BEGIN -->

<a id="test_CT_054"></a>

CT-054 — Site loss, fencing and failback

<!-- SOURCE-BLOCK HB11:1342 END -->

<!-- SOURCE-BLOCK HB11:1343 BEGIN -->

Preconditions: Two qualified sites; isolated exercise scope and owner-approved recovery plan.

<!-- SOURCE-BLOCK HB11:1343 END -->

<!-- SOURCE-BLOCK HB11:1344 BEGIN -->

Procedure: Declare simulated primary loss, fence writers, restore/promote at recovery site, verify DNS/identity/policy, then perform controlled failback.

<!-- SOURCE-BLOCK HB11:1344 END -->

<!-- SOURCE-BLOCK HB11:1345 BEGIN -->

Expected outcome: No split-brain or policy relaxation; measured RTO/RPO and data ownership match the recovery profile.

<!-- SOURCE-BLOCK HB11:1345 END -->

<!-- SOURCE-BLOCK HB11:1346 BEGIN -->

Evidence: Failure timeline, fencing proof, replication checkpoints and end-to-end tests.

<!-- SOURCE-BLOCK HB11:1346 END -->

<!-- SOURCE-BLOCK HB11:1347 BEGIN -->

Mode: controlled-recovery  \|  Cadence: qualification; scheduled recovery exercise  \|  Execution: not-run

<!-- SOURCE-BLOCK HB11:1347 END -->

<!-- SOURCE-BLOCK HB11:1348 BEGIN -->

Requirement links: SITE-001, SITE-002, SITE-003, SITE-004, BKP-002, REL-001, REL-002, TEST-004, FAIL-002, FAIL-003, REC-001, REC-002, MIG-003

<!-- SOURCE-BLOCK HB11:1348 END -->

<!-- SOURCE-BLOCK HB11:1349 BEGIN -->

<a id="test_CT_055"></a>

CT-055 — Management/control-plane bootstrap recovery

<!-- SOURCE-BLOCK HB11:1349 END -->

<!-- SOURCE-BLOCK HB11:1350 BEGIN -->

Preconditions: Offline recovery manifest and independent access to state, DNS/time, trust and keys.

<!-- SOURCE-BLOCK HB11:1350 END -->

<!-- SOURCE-BLOCK HB11:1351 BEGIN -->

Procedure: Recover essential management/controller services in the documented dependency order in an isolated environment.

<!-- SOURCE-BLOCK HB11:1351 END -->

<!-- SOURCE-BLOCK HB11:1352 BEGIN -->

Expected outcome: Recovery does not require the unavailable production service it is restoring; credentials and old state remain accountable.

<!-- SOURCE-BLOCK HB11:1352 END -->

<!-- SOURCE-BLOCK HB11:1353 BEGIN -->

Evidence: Dependency graph, recovery steps, integrity checks and measured recovery time.

<!-- SOURCE-BLOCK HB11:1353 END -->

<!-- SOURCE-BLOCK HB11:1354 BEGIN -->

Mode: controlled-recovery  \|  Cadence: annual; foundation redesign  \|  Execution: not-run

<!-- SOURCE-BLOCK HB11:1354 END -->

<!-- SOURCE-BLOCK HB11:1355 BEGIN -->

Requirement links: MGT-005, SITE-001, CRY-003, STATE-002, FAIL-002, FAIL-003, REC-001, REC-002

<!-- SOURCE-BLOCK HB11:1355 END -->

<!-- SOURCE-BLOCK HB11:1356 BEGIN -->

<a id="test_CT_056"></a>

CT-056 — Resource and address capacity exhaustion

<!-- SOURCE-BLOCK HB11:1356 END -->

<!-- SOURCE-BLOCK HB11:1357 BEGIN -->

Preconditions: Hard quotas, reservations and admission thresholds.

<!-- SOURCE-BLOCK HB11:1357 END -->

<!-- SOURCE-BLOCK HB11:1358 BEGIN -->

Procedure: Exhaust test compute/storage/edge context/address capacity, then request both ordinary and dedicated service classes.

<!-- SOURCE-BLOCK HB11:1358 END -->

<!-- SOURCE-BLOCK HB11:1359 BEGIN -->

Expected outcome: Requests stop with an explicit reason; required HA/security headroom is not consumed or silently weakened.

<!-- SOURCE-BLOCK HB11:1359 END -->

<!-- SOURCE-BLOCK HB11:1360 BEGIN -->

Evidence: Reservation ledger, rejected decisions and remaining-headroom report.

<!-- SOURCE-BLOCK HB11:1360 END -->

<!-- SOURCE-BLOCK HB11:1361 BEGIN -->

Mode: automated  \|  Cadence: qualification; security-significant change  \|  Execution: not-run

<!-- SOURCE-BLOCK HB11:1361 END -->

<!-- SOURCE-BLOCK HB11:1362 BEGIN -->

Requirement links: CMP-001, REL-002, PLACE-001, SVCM-001, CAP-001, CAP-002

<!-- SOURCE-BLOCK HB11:1362 END -->

<!-- SOURCE-BLOCK HB11:1363 BEGIN -->

<a id="test_CT_057"></a>

CT-057 — Incident quarantine and reconciler precedence

<!-- SOURCE-BLOCK HB11:1363 END -->

<!-- SOURCE-BLOCK HB11:1364 BEGIN -->

Preconditions: Scoped incident role and expiring emergency override.

<!-- SOURCE-BLOCK HB11:1364 END -->

<!-- SOURCE-BLOCK HB11:1365 BEGIN -->

Procedure: Quarantine one WSD, remove exposure and run normal reconciliation; test unaffected tenants.

<!-- SOURCE-BLOCK HB11:1365 END -->

<!-- SOURCE-BLOCK HB11:1366 BEGIN -->

Expected outcome: Containment persists under higher-priority incident policy until released; unrelated tenants remain available.

<!-- SOURCE-BLOCK HB11:1366 END -->

<!-- SOURCE-BLOCK HB11:1367 BEGIN -->

Evidence: Override object, effective policy, reconciliation audit and tenant probes.

<!-- SOURCE-BLOCK HB11:1367 END -->

<!-- SOURCE-BLOCK HB11:1368 BEGIN -->

Mode: controlled-fault  \|  Cadence: quarterly; containment change  \|  Execution: not-run

<!-- SOURCE-BLOCK HB11:1368 END -->

<!-- SOURCE-BLOCK HB11:1369 BEGIN -->

Requirement links: TEN-003, SUP-001, DRIFT-001, DRIFT-002, DRIFT-003, IR-001, IR-002

<!-- SOURCE-BLOCK HB11:1369 END -->

<!-- SOURCE-BLOCK HB11:1370 BEGIN -->

<a id="test_CT_058"></a>

CT-058 — Exception approval and expiry

<!-- SOURCE-BLOCK HB11:1370 END -->

<!-- SOURCE-BLOCK HB11:1371 BEGIN -->

Preconditions: Versioned exception with risk owner, affected requirement and end time.

<!-- SOURCE-BLOCK HB11:1371 END -->

<!-- SOURCE-BLOCK HB11:1372 BEGIN -->

Procedure: Test unapproved, expired and valid exceptions; expire one during a running operation.

<!-- SOURCE-BLOCK HB11:1372 END -->

<!-- SOURCE-BLOCK HB11:1373 BEGIN -->

Expected outcome: No unapproved exception grants access; expiry changes posture and triggers the documented action without indiscriminate destruction.

<!-- SOURCE-BLOCK HB11:1373 END -->

<!-- SOURCE-BLOCK HB11:1374 BEGIN -->

Evidence: Approval records, admission results and expiry event.

<!-- SOURCE-BLOCK HB11:1374 END -->

<!-- SOURCE-BLOCK HB11:1375 BEGIN -->

Mode: automated  \|  Cadence: each policy/controller change  \|  Execution: not-run

<!-- SOURCE-BLOCK HB11:1375 END -->

<!-- SOURCE-BLOCK HB11:1376 BEGIN -->

Requirement links: RTE-003, CICD-001, DRIFT-003, ASSUR-003, EVID-003, IR-002, MIG-001, EXC-001, EXC-002, EXC-003

<!-- SOURCE-BLOCK HB11:1376 END -->

<!-- SOURCE-BLOCK HB11:1377 BEGIN -->

<a id="test_CT_059"></a>

CT-059 — Data sanitization and resource reuse

<!-- SOURCE-BLOCK HB11:1377 END -->

<!-- SOURCE-BLOCK HB11:1378 BEGIN -->

Preconditions: Disposable data, snapshot/clone inventory and approved media method.

<!-- SOURCE-BLOCK HB11:1378 END -->

<!-- SOURCE-BLOCK HB11:1379 BEGIN -->

Procedure: Retire the storage object, verify retained copies, sanitize according to the approved method and allocate to another test tenant.

<!-- SOURCE-BLOCK HB11:1379 END -->

<!-- SOURCE-BLOCK HB11:1380 BEGIN -->

Expected outcome: New tenant cannot recover prior data; retained evidence identifies method, scope, exceptions and all surviving copies.

<!-- SOURCE-BLOCK HB11:1380 END -->

<!-- SOURCE-BLOCK HB11:1381 BEGIN -->

Evidence: Sanitization receipt, reuse test and copy/dependency ledger.

<!-- SOURCE-BLOCK HB11:1381 END -->

<!-- SOURCE-BLOCK HB11:1382 BEGIN -->

Mode: design-and-automated  \|  Cadence: qualification; storage lifecycle change  \|  Execution: not-run

<!-- SOURCE-BLOCK HB11:1382 END -->

<!-- SOURCE-BLOCK HB11:1383 BEGIN -->

Requirement links: STO-003, CRY-002, FUT-003, LIFE-001, LIFE-002, LIFE-003

<!-- SOURCE-BLOCK HB11:1383 END -->

<!-- SOURCE-BLOCK HB11:1384 BEGIN -->

<a id="test_CT_060"></a>

CT-060 — Portability and exit rehearsal

<!-- SOURCE-BLOCK HB11:1384 END -->

<!-- SOURCE-BLOCK HB11:1385 BEGIN -->

Preconditions: Two target profiles plus an exit manifest containing data and application dependencies.

<!-- SOURCE-BLOCK HB11:1385 END -->

<!-- SOURCE-BLOCK HB11:1386 BEGIN -->

Procedure: Export/rebuild the workload, convert only supported formats, import data and rebind identity/network/keys; run functional and security checks.

<!-- SOURCE-BLOCK HB11:1386 END -->

<!-- SOURCE-BLOCK HB11:1387 BEGIN -->

Expected outcome: Consumer semantics survive; downtime, data loss, format limitations and cost drivers are recorded; no untested live-migration claim.

<!-- SOURCE-BLOCK HB11:1387 END -->

<!-- SOURCE-BLOCK HB11:1388 BEGIN -->

Evidence: Exit manifest, conversion logs, reconciliation report and conformance results.

<!-- SOURCE-BLOCK HB11:1388 END -->

<!-- SOURCE-BLOCK HB11:1389 BEGIN -->

Mode: controlled-recovery  \|  Cadence: qualification; annual representative rehearsal  \|  Execution: not-run

<!-- SOURCE-BLOCK HB11:1389 END -->

<!-- SOURCE-BLOCK HB11:1390 BEGIN -->

Requirement links: INV-005, REF-001, STO-002, PLACE-003, PORT-003, REC-002, MIG-001, MIG-002, MIG-003, DEL-002

<!-- SOURCE-BLOCK HB11:1390 END -->

<!-- SOURCE-BLOCK HB11:1391 BEGIN -->

<a id="test_CT_061"></a>

CT-061 — Location, privacy and support access

<!-- SOURCE-BLOCK HB11:1391 END -->

<!-- SOURCE-BLOCK HB11:1392 BEGIN -->

Preconditions: PlacementProfile states permitted data, backup, telemetry, key and administrative locations.

<!-- SOURCE-BLOCK HB11:1392 END -->

<!-- SOURCE-BLOCK HB11:1393 BEGIN -->

Procedure: Compare all components and support paths to those constraints; test a placement or support session outside allowed scope.

<!-- SOURCE-BLOCK HB11:1393 END -->

<!-- SOURCE-BLOCK HB11:1394 BEGIN -->

Expected outcome: Nonconforming placement/access is rejected; exceptions require the designated authority; residency is not asserted to settle jurisdiction.

<!-- SOURCE-BLOCK HB11:1394 END -->

<!-- SOURCE-BLOCK HB11:1395 BEGIN -->

Evidence: Location inventory, access logs and approval decisions.

<!-- SOURCE-BLOCK HB11:1395 END -->

<!-- SOURCE-BLOCK HB11:1396 BEGIN -->

Mode: design-and-automated  \|  Cadence: qualification; provider/location change  \|  Execution: not-run

<!-- SOURCE-BLOCK HB11:1396 END -->

<!-- SOURCE-BLOCK HB11:1397 BEGIN -->

Requirement links: IPAM-002, SITE-004, PLACE-001, PLACE-002, PORT-002

<!-- SOURCE-BLOCK HB11:1397 END -->

<!-- SOURCE-BLOCK HB11:1398 BEGIN -->

<a id="test_CT_062"></a>

CT-062 — Shared responsibility and control inheritance

<!-- SOURCE-BLOCK HB11:1398 END -->

<!-- SOURCE-BLOCK HB11:1399 BEGIN -->

Preconditions: System control profile, service ownership and inheritance declarations.

<!-- SOURCE-BLOCK HB11:1399 END -->

<!-- SOURCE-BLOCK HB11:1400 BEGIN -->

Procedure: For each applicable control, identify provider, tenant or shared implementation, evidence and unresolved dependency.

<!-- SOURCE-BLOCK HB11:1400 END -->

<!-- SOURCE-BLOCK HB11:1401 BEGIN -->

Expected outcome: No control is ownerless; inherited evidence is scoped, current and accepted; gaps block required readiness.

<!-- SOURCE-BLOCK HB11:1401 END -->

<!-- SOURCE-BLOCK HB11:1402 BEGIN -->

Evidence: Control allocation matrix and assessor review.

<!-- SOURCE-BLOCK HB11:1402 END -->

<!-- SOURCE-BLOCK HB11:1403 BEGIN -->

Mode: manual-review  \|  Cadence: onboarding; major change; periodic review  \|  Execution: not-run

<!-- SOURCE-BLOCK HB11:1403 END -->

<!-- SOURCE-BLOCK HB11:1404 BEGIN -->

Requirement links: SCOPE-001, STD-001, STD-002, CAT-001, THR-001, WSD-003, CMP-003, REL-001, SVCM-001, RESP-001, ASSUR-001, ASSUR-002, OPS-001, OPS-002, EXC-001, ONB-001, ACPT-001

<!-- SOURCE-BLOCK HB11:1404 END -->

<!-- SOURCE-BLOCK HB11:1405 BEGIN -->

<a id="test_CT_063"></a>

CT-063 — Public certificate and trusted proxy identity

<!-- SOURCE-BLOCK HB11:1405 END -->

<!-- SOURCE-BLOCK HB11:1406 BEGIN -->

Preconditions: Approved ingress with backend encryption and trusted proxy policy.

<!-- SOURCE-BLOCK HB11:1406 END -->

<!-- SOURCE-BLOCK HB11:1407 BEGIN -->

Procedure: Rotate the certificate, test expiry/incorrect hostname and submit forged client-identity headers through the controlled test client.

<!-- SOURCE-BLOCK HB11:1407 END -->

<!-- SOURCE-BLOCK HB11:1408 BEGIN -->

Expected outcome: TLS identity is validated; backend trust is explicit; untrusted headers cannot impersonate the originating client.

<!-- SOURCE-BLOCK HB11:1408 END -->

<!-- SOURCE-BLOCK HB11:1409 BEGIN -->

Evidence: TLS checks, proxy policy and attributed requests.

<!-- SOURCE-BLOCK HB11:1409 END -->

<!-- SOURCE-BLOCK HB11:1410 BEGIN -->

Mode: automated  \|  Cadence: qualification; security-significant change  \|  Execution: not-run

<!-- SOURCE-BLOCK HB11:1410 END -->

<!-- SOURCE-BLOCK HB11:1411 BEGIN -->

Requirement links: ING-002, EXP-001, CRY-001

<!-- SOURCE-BLOCK HB11:1411 END -->

<!-- SOURCE-BLOCK HB11:1412 BEGIN -->

<a id="test_CT_064"></a>

CT-064 — Egress policy and service-specific protocols

<!-- SOURCE-BLOCK HB11:1412 END -->

<!-- SOURCE-BLOCK HB11:1413 BEGIN -->

Preconditions: Approved egress service includes protocol, destination and DNS resolution policy.

<!-- SOURCE-BLOCK HB11:1413 END -->

<!-- SOURCE-BLOCK HB11:1414 BEGIN -->

Procedure: Test permitted and nearby disallowed destinations; verify NAT identity logs and stateful return traffic.

<!-- SOURCE-BLOCK HB11:1414 END -->

<!-- SOURCE-BLOCK HB11:1415 BEGIN -->

Expected outcome: Only approved egress semantics work; DNS/FQDN changes cannot silently widen policy; NAT is not treated as a security control by itself.

<!-- SOURCE-BLOCK HB11:1415 END -->

<!-- SOURCE-BLOCK HB11:1416 BEGIN -->

Evidence: Egress rules, DNS resolution history, NAT mappings and probes.

<!-- SOURCE-BLOCK HB11:1416 END -->

<!-- SOURCE-BLOCK HB11:1417 BEGIN -->

Mode: automated  \|  Cadence: qualification; security-significant change  \|  Execution: not-run

<!-- SOURCE-BLOCK HB11:1417 END -->

<!-- SOURCE-BLOCK HB11:1418 BEGIN -->

Requirement links: EGR-001, EGR-002

<!-- SOURCE-BLOCK HB11:1418 END -->

<!-- SOURCE-BLOCK HB11:1419 BEGIN -->

<a id="test_CT_065"></a>

CT-065 — Privileged workload and container isolation

<!-- SOURCE-BLOCK HB11:1419 END -->

<!-- SOURCE-BLOCK HB11:1420 BEGIN -->

Preconditions: A container/bare-metal profile with explicit isolation capabilities.

<!-- SOURCE-BLOCK HB11:1420 END -->

<!-- SOURCE-BLOCK HB11:1421 BEGIN -->

Procedure: Test namespace/project boundaries, node access, privileged workloads and host-network access against the approved baseline.

<!-- SOURCE-BLOCK HB11:1421 END -->

<!-- SOURCE-BLOCK HB11:1422 BEGIN -->

Expected outcome: Unapproved privilege escalation or host access is denied; namespace alone is not accepted as a qualified zone boundary.

<!-- SOURCE-BLOCK HB11:1422 END -->

<!-- SOURCE-BLOCK HB11:1423 BEGIN -->

Evidence: Admission/RBAC policy, runtime posture and cross-scope tests.

<!-- SOURCE-BLOCK HB11:1423 END -->

<!-- SOURCE-BLOCK HB11:1424 BEGIN -->

Mode: automated  \|  Cadence: qualification; security-significant change  \|  Execution: not-run

<!-- SOURCE-BLOCK HB11:1424 END -->

<!-- SOURCE-BLOCK HB11:1425 BEGIN -->

Requirement links: MICRO-003, FUT-001, FUT-002, FUT-003

<!-- SOURCE-BLOCK HB11:1425 END -->

<!-- SOURCE-BLOCK HB11:1426 BEGIN -->

<a id="test_CT_066"></a>

CT-066 — Policy precedence and immutable baseline

<!-- SOURCE-BLOCK HB11:1426 END -->

<!-- SOURCE-BLOCK HB11:1427 BEGIN -->

Preconditions: Mandatory provider rules plus lower-priority tenant and service rules.

<!-- SOURCE-BLOCK HB11:1427 END -->

<!-- SOURCE-BLOCK HB11:1428 BEGIN -->

Procedure: Compile overlapping allow/deny intents and update membership while a test workload is running.

<!-- SOURCE-BLOCK HB11:1428 END -->

<!-- SOURCE-BLOCK HB11:1429 BEGIN -->

Expected outcome: Mandatory denies cannot be overridden by tenant policy; membership changes do not create a transient unrestricted interval.

<!-- SOURCE-BLOCK HB11:1429 END -->

<!-- SOURCE-BLOCK HB11:1430 BEGIN -->

Evidence: Effective-rule order, membership transitions and timed probes.

<!-- SOURCE-BLOCK HB11:1430 END -->

<!-- SOURCE-BLOCK HB11:1431 BEGIN -->

Mode: automated  \|  Cadence: qualification; security-significant change  \|  Execution: not-run

<!-- SOURCE-BLOCK HB11:1431 END -->

<!-- SOURCE-BLOCK HB11:1432 BEGIN -->

Requirement links: ZONE-002, ZIP-003, OVL-003, MICRO-001, MICRO-002, NUT-003, NSX-001, OS-001, POL-001, POL-002, FLOW-001, DRIFT-003, IR-002

<!-- SOURCE-BLOCK HB11:1432 END -->

<!-- SOURCE-BLOCK HB11:1433 BEGIN -->

<a id="test_CT_067"></a>

CT-067 — ZIP sensors, heightened posture and authority

<!-- SOURCE-BLOCK HB11:1433 END -->

<!-- SOURCE-BLOCK HB11:1434 BEGIN -->

Preconditions: ZIP profile identifies both zone authorities, inspection/sensor policy and heightened mode.

<!-- SOURCE-BLOCK HB11:1434 END -->

<!-- SOURCE-BLOCK HB11:1435 BEGIN -->

Procedure: Verify access-control and telemetry placement; activate heightened posture, test essential flows and restore under approved authority.

<!-- SOURCE-BLOCK HB11:1435 END -->

<!-- SOURCE-BLOCK HB11:1436 BEGIN -->

Expected outcome: Posture change restricts intended flows, preserves declared essentials, and leaves a complete joint-authority record.

<!-- SOURCE-BLOCK HB11:1436 END -->

<!-- SOURCE-BLOCK HB11:1437 BEGIN -->

Evidence: ZIP profile, sensor coverage, change approval and test traces.

<!-- SOURCE-BLOCK HB11:1437 END -->

<!-- SOURCE-BLOCK HB11:1438 BEGIN -->

Mode: automated  \|  Cadence: qualification; security-significant change  \|  Execution: not-run

<!-- SOURCE-BLOCK HB11:1438 END -->

<!-- SOURCE-BLOCK HB11:1439 BEGIN -->

Requirement links: ZIP-006, IR-001

<!-- SOURCE-BLOCK HB11:1439 END -->

<!-- SOURCE-BLOCK HB11:1440 BEGIN -->

<a id="test_CT_068"></a>

CT-068 — Time synchronization and correlation

<!-- SOURCE-BLOCK HB11:1440 END -->

<!-- SOURCE-BLOCK HB11:1441 BEGIN -->

Preconditions: Approved independent time sources and skew threshold.

<!-- SOURCE-BLOCK HB11:1441 END -->

<!-- SOURCE-BLOCK HB11:1442 BEGIN -->

Procedure: Measure time across hosts, controllers, edge and collectors; introduce bounded skew in a disposable node.

<!-- SOURCE-BLOCK HB11:1442 END -->

<!-- SOURCE-BLOCK HB11:1443 BEGIN -->

Expected outcome: Excess skew is detected; certificate/evidence validation follows defined failure behavior; record ordering remains explainable.

<!-- SOURCE-BLOCK HB11:1443 END -->

<!-- SOURCE-BLOCK HB11:1444 BEGIN -->

Evidence: Skew metrics, alerts and signed/ordered event samples.

<!-- SOURCE-BLOCK HB11:1444 END -->

<!-- SOURCE-BLOCK HB11:1445 BEGIN -->

Mode: automated  \|  Cadence: qualification; security-significant change  \|  Execution: not-run

<!-- SOURCE-BLOCK HB11:1445 END -->

<!-- SOURCE-BLOCK HB11:1446 BEGIN -->

Requirement links: OBS-003

<!-- SOURCE-BLOCK HB11:1446 END -->

<!-- SOURCE-BLOCK HB11:1447 BEGIN -->

<a id="test_CT_069"></a>

CT-069 — Technical readiness gate

<!-- SOURCE-BLOCK HB11:1447 END -->

<!-- SOURCE-BLOCK HB11:1448 BEGIN -->

Preconditions: Healthy and deliberately failed evidence fixtures at the same desired generation.

<!-- SOURCE-BLOCK HB11:1448 END -->

<!-- SOURCE-BLOCK HB11:1449 BEGIN -->

Procedure: Evaluate readiness with missing/expired evidence, unsupported capability, unresolved owner and absent authorization.

<!-- SOURCE-BLOCK HB11:1449 END -->

<!-- SOURCE-BLOCK HB11:1450 BEGIN -->

Expected outcome: Service Ready is false unless every mandatory condition for the current generation is satisfied.

<!-- SOURCE-BLOCK HB11:1450 END -->

<!-- SOURCE-BLOCK HB11:1451 BEGIN -->

Evidence: Condition evaluation, policy version and blocked exposure events.

<!-- SOURCE-BLOCK HB11:1451 END -->

<!-- SOURCE-BLOCK HB11:1452 BEGIN -->

Mode: automated  \|  Cadence: each controller/policy change  \|  Execution: not-run

<!-- SOURCE-BLOCK HB11:1452 END -->

<!-- SOURCE-BLOCK HB11:1453 BEGIN -->

Requirement links: INV-006, AUTH-001, CAT-001, WSD-003, OVL-003, EXP-001, RESP-001, QUAL-001, AUTO-002, ASSUR-003, TEST-003, EVID-001, EVID-002, EVID-003, OPS-002, EXC-002, EXC-003, ONB-001, DEL-001, ACPT-001

<!-- SOURCE-BLOCK HB11:1453 END -->

<!-- SOURCE-BLOCK HB11:1454 BEGIN -->

<a id="test_CT_070"></a>

CT-070 — Contract upgrades and deletion finalizers

<!-- SOURCE-BLOCK HB11:1454 END -->

<!-- SOURCE-BLOCK HB11:1455 BEGIN -->

Preconditions: Objects at old schema version; shared domain has two dependent WSDs.

<!-- SOURCE-BLOCK HB11:1455 END -->

<!-- SOURCE-BLOCK HB11:1456 BEGIN -->

Procedure: Convert schema with explicit defaults; delete one WSD; test removal with outstanding retention/evidence finalizers.

<!-- SOURCE-BLOCK HB11:1456 END -->

<!-- SOURCE-BLOCK HB11:1457 BEGIN -->

Expected outcome: No silent security expansion; shared resources survive while referenced; deletion cannot bypass approved finalizers.

<!-- SOURCE-BLOCK HB11:1457 END -->

<!-- SOURCE-BLOCK HB11:1458 BEGIN -->

Evidence: Conversion diff, ownership graph and tombstones.

<!-- SOURCE-BLOCK HB11:1458 END -->

<!-- SOURCE-BLOCK HB11:1459 BEGIN -->

Mode: automated  \|  Cadence: contract/lifecycle engine change  \|  Execution: not-run

<!-- SOURCE-BLOCK HB11:1459 END -->

<!-- SOURCE-BLOCK HB11:1460 BEGIN -->

Requirement links: INV-001, MODEL-001, TEN-003, WSD-001, API-001, API-003, TF-004, STATE-003, LIFE-001, LIFE-002

<!-- SOURCE-BLOCK HB11:1460 END -->

<!-- SOURCE-BLOCK HB11:1461 BEGIN -->

<a id="test_CT_071"></a>

CT-071 — Foundation stability for overlay lifecycle

<!-- SOURCE-BLOCK HB11:1461 END -->

<!-- SOURCE-BLOCK HB11:1462 BEGIN -->

Preconditions: Commissioned overlay capacity and physical fabric configuration snapshot.

<!-- SOURCE-BLOCK HB11:1462 END -->

<!-- SOURCE-BLOCK HB11:1463 BEGIN -->

Procedure: Create, update and retire a routine overlay WSD; compare leaf/spine configuration before and after.

<!-- SOURCE-BLOCK HB11:1463 END -->

<!-- SOURCE-BLOCK HB11:1464 BEGIN -->

Expected outcome: No per-WSD switch change occurs; physical-capacity growth is classified as a separate foundation operation.

<!-- SOURCE-BLOCK HB11:1464 END -->

<!-- SOURCE-BLOCK HB11:1465 BEGIN -->

Evidence: Switch config digests, service class and operation audit.

<!-- SOURCE-BLOCK HB11:1465 END -->

<!-- SOURCE-BLOCK HB11:1466 BEGIN -->

Mode: automated  \|  Cadence: qualification; security-significant change  \|  Execution: not-run

<!-- SOURCE-BLOCK HB11:1466 END -->

<!-- SOURCE-BLOCK HB11:1467 BEGIN -->

Requirement links: ARCH-002, EDGE-001, FAB-001

<!-- SOURCE-BLOCK HB11:1467 END -->

<!-- SOURCE-BLOCK HB11:1468 BEGIN -->

<a id="test_CT_072"></a>

CT-072 — Bare-metal/fabric-routed service boundary

<!-- SOURCE-BLOCK HB11:1468 END -->

<!-- SOURCE-BLOCK HB11:1469 BEGIN -->

Preconditions: Explicit fabric-routed service class and authorized foundation workflow.

<!-- SOURCE-BLOCK HB11:1469 END -->

<!-- SOURCE-BLOCK HB11:1470 BEGIN -->

Procedure: Provision a test physical attachment under separate authority; inspect VRF/RT/interface ownership and retire it.

<!-- SOURCE-BLOCK HB11:1470 END -->

<!-- SOURCE-BLOCK HB11:1471 BEGIN -->

Expected outcome: Consumer contract remains portable; exceptions to overlay workflow are explicit; no unrestricted cross-domain route is introduced.

<!-- SOURCE-BLOCK HB11:1471 END -->

<!-- SOURCE-BLOCK HB11:1472 BEGIN -->

Evidence: Service-class declaration, foundation change and isolation tests.

<!-- SOURCE-BLOCK HB11:1472 END -->

<!-- SOURCE-BLOCK HB11:1473 BEGIN -->

Mode: automated  \|  Cadence: qualification; security-significant change  \|  Execution: not-run

<!-- SOURCE-BLOCK HB11:1473 END -->

<!-- SOURCE-BLOCK HB11:1474 BEGIN -->

Requirement links: ARCH-002, FAB-001, FAB-002, FAB-003, EVPN-001, FUT-003

<!-- SOURCE-BLOCK HB11:1474 END -->

<!-- SOURCE-BLOCK HB11:1475 BEGIN -->

<a id="test_CT_073"></a>

CT-073 — Image/data export compatibility

<!-- SOURCE-BLOCK HB11:1475 END -->

<!-- SOURCE-BLOCK HB11:1476 BEGIN -->

Preconditions: Supported boot mode, drivers, virtual hardware and encrypted-disk context.

<!-- SOURCE-BLOCK HB11:1476 END -->

<!-- SOURCE-BLOCK HB11:1477 BEGIN -->

Procedure: Recreate the workload on the target with a test image; verify guest drivers, time, certificates, application checks and unsupported device handling.

<!-- SOURCE-BLOCK HB11:1477 END -->

<!-- SOURCE-BLOCK HB11:1478 BEGIN -->

Expected outcome: Incompatibilities reject the selected exit path; data/identity are not assumed portable merely because a disk file converts.

<!-- SOURCE-BLOCK HB11:1478 END -->

<!-- SOURCE-BLOCK HB11:1479 BEGIN -->

Evidence: Compatibility checklist, boot logs, application and security tests.

<!-- SOURCE-BLOCK HB11:1479 END -->

<!-- SOURCE-BLOCK HB11:1480 BEGIN -->

Mode: automated  \|  Cadence: qualification; security-significant change  \|  Execution: not-run

<!-- SOURCE-BLOCK HB11:1480 END -->

<!-- SOURCE-BLOCK HB11:1481 BEGIN -->

Requirement links: CMP-002, PLACE-003, PORT-003, MIG-003, DEL-002

<!-- SOURCE-BLOCK HB11:1481 END -->

<!-- SOURCE-BLOCK HB11:1482 BEGIN -->

<a id="test_CT_074"></a>

CT-074 — Procured-capacity and service inventory reconciliation

<!-- SOURCE-BLOCK HB11:1482 END -->

<!-- SOURCE-BLOCK HB11:1483 BEGIN -->

Preconditions: Procurement/asset inventory, installed capacity and tenant reservations.

<!-- SOURCE-BLOCK HB11:1483 END -->

<!-- SOURCE-BLOCK HB11:1484 BEGIN -->

Procedure: Reconcile ordered, received, staged, commissioned, available, reserved and consumed quantities with accountable owners.

<!-- SOURCE-BLOCK HB11:1484 END -->

<!-- SOURCE-BLOCK HB11:1485 BEGIN -->

Expected outcome: No orphaned or double-counted capacity; unused procured capacity and support expiry are visible for planning.

<!-- SOURCE-BLOCK HB11:1485 END -->

<!-- SOURCE-BLOCK HB11:1486 BEGIN -->

Evidence: Inventory reconciliation and allocation/age report.

<!-- SOURCE-BLOCK HB11:1486 END -->

<!-- SOURCE-BLOCK HB11:1487 BEGIN -->

Mode: manual-and-automated  \|  Cadence: monthly; capacity change  \|  Execution: not-run

<!-- SOURCE-BLOCK HB11:1487 END -->

<!-- SOURCE-BLOCK HB11:1488 BEGIN -->

Requirement links: SVCM-002, CAP-003, VULN-001

<!-- SOURCE-BLOCK HB11:1488 END -->

<!-- SOURCE-BLOCK HB11:1489 BEGIN -->

<a id="test_CT_075"></a>

CT-075 — Document and catalogue completeness

<!-- SOURCE-BLOCK HB11:1489 END -->

<!-- SOURCE-BLOCK HB11:1490 BEGIN -->

Preconditions: Handbook source, schemas, examples, requirements and tests in the release package.

<!-- SOURCE-BLOCK HB11:1490 END -->

<!-- SOURCE-BLOCK HB11:1491 BEGIN -->

Procedure: Check unique IDs, full original-ID migration, references, source links, test mappings, schema validation and generated catalogue parity.

<!-- SOURCE-BLOCK HB11:1491 END -->

<!-- SOURCE-BLOCK HB11:1492 BEGIN -->

Expected outcome: No missing or dangling item; counts and release digest agree; document status does not claim unexecuted platform tests passed.

<!-- SOURCE-BLOCK HB11:1492 END -->

<!-- SOURCE-BLOCK HB11:1493 BEGIN -->

Evidence: Package validation report and manifest.

<!-- SOURCE-BLOCK HB11:1493 END -->

<!-- SOURCE-BLOCK HB11:1494 BEGIN -->

Mode: automated  \|  Cadence: each document release  \|  Execution: not-run

<!-- SOURCE-BLOCK HB11:1494 END -->

<!-- SOURCE-BLOCK HB11:1495 BEGIN -->

Requirement links: DOC-001, STD-001, STD-002, TEST-003, EVID-001

<!-- SOURCE-BLOCK HB11:1495 END -->

<!-- SOURCE-BLOCK HB11:1496 BEGIN -->

<a id="test_CT_076"></a>

CT-076 — External partner agreement and revocation

<!-- SOURCE-BLOCK HB11:1496 END -->

<!-- SOURCE-BLOCK HB11:1497 BEGIN -->

Preconditions: ExternalDomain has trust basis, authenticated endpoints and named agreement owner.

<!-- SOURCE-BLOCK HB11:1497 END -->

<!-- SOURCE-BLOCK HB11:1498 BEGIN -->

Procedure: Admit an approved binding, then revoke the agreement and check active/new session handling under its profile.

<!-- SOURCE-BLOCK HB11:1498 END -->

<!-- SOURCE-BLOCK HB11:1499 BEGIN -->

Expected outcome: Revocation removes intended access within the agreed interval; no REZ assumption is inferred merely from a private circuit.

<!-- SOURCE-BLOCK HB11:1499 END -->

<!-- SOURCE-BLOCK HB11:1500 BEGIN -->

Evidence: Agreement revision, revocation event and connectivity checks.

<!-- SOURCE-BLOCK HB11:1500 END -->

<!-- SOURCE-BLOCK HB11:1501 BEGIN -->

Mode: automated  \|  Cadence: qualification; security-significant change  \|  Execution: not-run

<!-- SOURCE-BLOCK HB11:1501 END -->

<!-- SOURCE-BLOCK HB11:1502 BEGIN -->

Requirement links: ZONE-001, MIG-001

<!-- SOURCE-BLOCK HB11:1502 END -->

<!-- SOURCE-BLOCK HB11:1503 BEGIN -->

<a id="test_CT_077"></a>

CT-077 — Flow revocation and live session semantics

<!-- SOURCE-BLOCK HB11:1503 END -->

<!-- SOURCE-BLOCK HB11:1504 BEGIN -->

Preconditions: Approved long-lived test flow with a revocation profile.

<!-- SOURCE-BLOCK HB11:1504 END -->

<!-- SOURCE-BLOCK HB11:1505 BEGIN -->

Procedure: Revoke permission and measure established sessions, cached policies and newly attempted sessions across enforcement points.

<!-- SOURCE-BLOCK HB11:1505 END -->

<!-- SOURCE-BLOCK HB11:1506 BEGIN -->

Expected outcome: New sessions are denied immediately upon committed policy; existing sessions are terminated or drained within the explicitly approved interval.

<!-- SOURCE-BLOCK HB11:1506 END -->

<!-- SOURCE-BLOCK HB11:1507 BEGIN -->

Evidence: Rule generation timeline, session table and probes.

<!-- SOURCE-BLOCK HB11:1507 END -->

<!-- SOURCE-BLOCK HB11:1508 BEGIN -->

Mode: automated  \|  Cadence: qualification; security-significant change  \|  Execution: not-run

<!-- SOURCE-BLOCK HB11:1508 END -->

<!-- SOURCE-BLOCK HB11:1509 BEGIN -->

Requirement links: ZIP-006, RTE-003, SVC-003, EXP-001, IAM-003, FLOW-001

<!-- SOURCE-BLOCK HB11:1509 END -->

<!-- SOURCE-BLOCK HB11:1510 BEGIN -->

<a id="test_CT_078"></a>

CT-078 — Storage clone, snapshot and export classification

<!-- SOURCE-BLOCK HB11:1510 END -->

<!-- SOURCE-BLOCK HB11:1511 BEGIN -->

Preconditions: Protected test volume with snapshot and clone operations enabled.

<!-- SOURCE-BLOCK HB11:1511 END -->

<!-- SOURCE-BLOCK HB11:1512 BEGIN -->

Procedure: Attempt cross-zone clone/export and a lower-categorization target using both tenant and service identities.

<!-- SOURCE-BLOCK HB11:1512 END -->

<!-- SOURCE-BLOCK HB11:1513 BEGIN -->

Expected outcome: Data copies preserve classification and key/access constraints; unapproved downgrade or public export is denied.

<!-- SOURCE-BLOCK HB11:1513 END -->

<!-- SOURCE-BLOCK HB11:1514 BEGIN -->

Evidence: Copy lineage, target checks, key references and audit.

<!-- SOURCE-BLOCK HB11:1514 END -->

<!-- SOURCE-BLOCK HB11:1515 BEGIN -->

Mode: automated  \|  Cadence: qualification; security-significant change  \|  Execution: not-run

<!-- SOURCE-BLOCK HB11:1515 END -->

<!-- SOURCE-BLOCK HB11:1516 BEGIN -->

Requirement links: STO-001, STO-003, LIFE-002, MIG-003

<!-- SOURCE-BLOCK HB11:1516 END -->

<!-- SOURCE-BLOCK HB11:1517 BEGIN -->

<a id="test_CT_079"></a>

CT-079 — Provider/support access time limit

<!-- SOURCE-BLOCK HB11:1517 END -->

<!-- SOURCE-BLOCK HB11:1518 BEGIN -->

Preconditions: Support role, approved session and export/logging rules.

<!-- SOURCE-BLOCK HB11:1518 END -->

<!-- SOURCE-BLOCK HB11:1519 BEGIN -->

Procedure: Open a time-bound support session, test scoped capabilities, expire it and verify all delegated grants are revoked.

<!-- SOURCE-BLOCK HB11:1519 END -->

<!-- SOURCE-BLOCK HB11:1520 BEGIN -->

Expected outcome: No unattended permanent privileged access remains; transferred diagnostics follow approved location and redaction rules.

<!-- SOURCE-BLOCK HB11:1520 END -->

<!-- SOURCE-BLOCK HB11:1521 BEGIN -->

Evidence: Session record, approval, scope tests and revocation receipts.

<!-- SOURCE-BLOCK HB11:1521 END -->

<!-- SOURCE-BLOCK HB11:1522 BEGIN -->

Mode: automated  \|  Cadence: qualification; security-significant change  \|  Execution: not-run

<!-- SOURCE-BLOCK HB11:1522 END -->

<!-- SOURCE-BLOCK HB11:1523 BEGIN -->

Requirement links: MGT-004, IAM-002, IAM-003, PLACE-002, SEC-002, OPS-001

<!-- SOURCE-BLOCK HB11:1523 END -->

<!-- SOURCE-BLOCK HB11:1524 BEGIN -->

<a id="test_CT_080"></a>

CT-080 — Distributed ZIP equivalence

<!-- SOURCE-BLOCK HB11:1524 END -->

<!-- SOURCE-BLOCK HB11:1525 BEGIN -->

Preconditions: A proposed distributed-enforcement profile and the required ZIP function list.

<!-- SOURCE-BLOCK HB11:1525 END -->

<!-- SOURCE-BLOCK HB11:1526 BEGIN -->

Procedure: Map every required boundary function to its actual enforcement/control component; test same-host and bypass paths plus controller/agent failure.

<!-- SOURCE-BLOCK HB11:1526 END -->

<!-- SOURCE-BLOCK HB11:1527 BEGIN -->

Expected outcome: Logical ZIP semantics are fully met; missing inspection, attribution, failure isolation or authority support rejects qualification.

<!-- SOURCE-BLOCK HB11:1527 END -->

<!-- SOURCE-BLOCK HB11:1528 BEGIN -->

Evidence: Function coverage, topology, policy and fault-test evidence.

<!-- SOURCE-BLOCK HB11:1528 END -->

<!-- SOURCE-BLOCK HB11:1529 BEGIN -->

Mode: design-and-automated  \|  Cadence: qualification; enforcement-stack change  \|  Execution: not-run

<!-- SOURCE-BLOCK HB11:1529 END -->

<!-- SOURCE-BLOCK HB11:1530 BEGIN -->

Requirement links: INV-002, THR-001, ZIP-001, ZIP-005, ZIP-006, ZIP-007, OVL-001, EDGE-002, PORT-001, NUT-004, NSX-003, OS-003, FUT-001

<!-- SOURCE-BLOCK HB11:1530 END -->

[Previous chapter](72-appendix-c-complete-normative-requirement-and-verification-index.md) · [Chapter index](README.md) · [Next chapter](74-appendix-e-source-control-traceability-and-responsibility.md)
