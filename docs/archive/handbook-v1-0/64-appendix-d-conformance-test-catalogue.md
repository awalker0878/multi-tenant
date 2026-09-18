# Appendix D — Conformance Test Catalogue

[Documentation home](../../README.md) · [Source document](../../../reference/migration-source-documents/Handbook_v1_0.docx) · [Chapter index](README.md)

> **Source:** HB10 — Draft v1.0. Historical source; not the active design.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: 100c760003b9ff956ae369ece65c5ffe7736f6d481496d8df4c99dd6105d4190 -->

> **Historical only.** Use the [v1.4 reference architecture](../../architecture/reference/README.md) for the active design baseline. Conflicting historical text has not been silently reconciled.
<!-- SOURCE-BLOCK HB10:424 BEGIN -->

<!-- SOURCE-BLOCK HB10:424 END -->

<!-- SOURCE-BLOCK HB10:425 BEGIN -->


<a id="source-table-425"></a>

| ID | Test | Method | Expected |
| --- | --- | --- | --- |
| CT-001 | Cross-tenant IPv4 | Attempt reachability between tenant A and tenant B | Fail |
| CT-002 | Cross-tenant IPv6 | Attempt IPv6 reachability between tenant A and tenant B | Fail |
| CT-003 | Zone bypass | Attempt OZ→RZ path not traversing declared ZIP | Fail |
| CT-004 | Management isolation | Attempt workload→management API/OOB | Fail |
| CT-005 | Default Internet | Attempt Internet access with no egress profile | Fail |
| CT-006 | Public ingress | Attempt direct public access to internal workload | Fail |
| CT-007 | Approved flow | Execute declared application flow through policy | Pass |
| CT-008 | Service binding | Resolve/reach declared service endpoint | Pass |
| CT-009 | Route authority | Search realized routes for unauthorized prefixes/defaults | Pass: none found |
| CT-010 | Policy logging | Generate allow/deny and verify central event attribution | Pass |
| CT-011 | Control-plane loss | Simulate approved management/control-plane outage | Enforcement remains |
| CT-012 | HA failure | Fail one security-edge node | Traffic/policy within SLO |
| CT-013 | Offboarding | Destroy WSD and scan for stale routes/policy/identity | Pass: none found |
| CT-014 | Drift | Introduce controlled unauthorized change in test env | Detected |
| CT-015 | Provider upgrade | Run regression suite on target provider/platform version | Pass before promotion |

<!-- SOURCE-BLOCK HB10:425 END -->

[Previous chapter](63-appendix-c-baseline-policy-matrix.md) · [Chapter index](README.md) · [Next chapter](65-appendix-e-evidence-manifest.md)
