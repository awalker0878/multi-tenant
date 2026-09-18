# 28. Architecture acceptance and verification

[Documentation home](../../README.md) · [Source document](../../../reference/Portable_Hosting_Delivery_Kits_v1_1/05_Reference_v1_4/00_Reference_Architecture_v1_4.docx) · [Chapter index](README.md)

> **Source:** RA — Draft v1.4. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: e50894d7f7b87cef50a283399b85925c8a96c5b9cd0428ce71ca0143d9be8d19 -->
<a id="__RefHeading___Toc3694_865363315"></a>
<a id="RA_s_028"></a>

Acceptance dependency: gate IDs identify decision types rather than chronology. Before production activation, the delivered service must already have the applicable operational and promised recovery readiness described by G4, current platform/service qualification and valid operating authority. Restricted non-production qualification is separately authorized and may precede G2 acceptance. WD §9 defines the complete relationship.

Acceptance has three distinct levels: the document describes a coherent reference architecture; an implementation qualifies a specific component/version/topology combination; and an authorized service is accepted for operation. This revision addresses the first level and defines evidence for the other two. It does not mark an unexecuted infrastructure test as passed or issue formal authorization.


<a id="source-table-391"></a>

| Architecture question | Required implementation evidence |
| --- | --- |
| Does the built topology match the design? | As-built component/connection inventory, management and data-path diagrams, release tuple and declared variations |
| Are independent tenants and zones isolated? | Positive/negative tests including same-host, shared attachment, native route propagation, alternative NIC and both offered address families |
| Are management and shared services separated? | Actual management routes/roles and bounded service/data access; no broad provider-network permission |
| Are compute and data boundaries real? | Scheduler/HA/migration behaviour, storage attachment/copy isolation, key custody and protected recovery |
| Does provisioning preserve the architecture? | Successful create/update/adopt/delete, partial-failure reconciliation, authority separation and no orphan resources |
| Does the service survive its promised failures? | Measured load, convergence/session behaviour, quorum/fencing and recovery of key/identity/control dependencies |
| Can it be operated and exited? | Named owners, monitoring/support, restore/cutover/retirement procedures and representative second-platform evidence |

The retained 80-test catalogue is an assurance specification, not a deployment report. Select tests by the offered service and actual topology; add path-specific procedures for the new realization choices. An automated test must verify that its endpoints and allowed control paths are healthy before treating denied traffic as a security success. Blocked, not-run or unjustified not-applicable results do not satisfy a mandatory gate.

Fault injection, spoofing and outage tests run only in an approved representative environment or controlled production safety envelope. Test scope protects unrelated tenants and includes a restoration procedure. Verification depth grows with exposure, sharing and failure risk. A small laboratory test does not establish the maximum production scale or prove the absence of every possible path.

## Evidence and authorization

The evidence set ties the approved design and deployment change to actual resources, routing/policy, service versions, tests, time and active exceptions. It preserves access controls and artifact integrity. Evidence freshness is evaluated after material changes: yesterday’s successful path check does not prove a newly advertised route is safe. Technical conformance and service readiness can change without rewriting historical authorization decisions.

Platform qualification is scoped. A stack may be eligible for one IPv4 internal class but not dual-stack, dedicated isolation or public ingress. Unsupported or expired capabilities stop new placement for the affected service class, while existing service handling follows the approved risk/continuity decision. Formal authorization remains the responsibility of its designated authority and requires the applicable control tailoring and assessment.

Reference implementation gate — Demonstrate two tenants with independent OZ/RZ domains, controlled shared services, protected management, correct placement, restore and complete retirement on the first stack. Repeat the same architectural outcomes on a second stack before claiming multi-platform portability. The third stack is not accepted merely because its object names have been mapped in a table.

Select verification by assertion, service class, topology and stage. First-stack qualification uses the applicable single-stack observations; second-stack comparison and representative data/image recovery then establish the separately claimed portability scope. Do not make two already-qualified platforms a prerequisite to the first platform’s qualification. QUAL §5 records this applicability method while preserving the inherited procedures as not-run.

Related engineering: [QUAL §5 — Qualification stages, applicability and evidence](../../assurance/site-qualification/5-qualification-stages-applicability-and-evidence.md#QUAL_s_005)  •  [QUAL §6 — Control inheritance, assurance and organizational interfaces](../../assurance/site-qualification/6-control-inheritance-assurance-and-organizational-interfaces.md#QUAL_s_006)

PART 6  /  Decisions and implementation

[Previous chapter](27-recovery-migration-and-retirement.md) · [Chapter index](README.md) · [Next chapter](29-architecture-decisions-and-alternatives.md)

<!-- BEGIN GENERATED DECISION LINKS -->

## Related decision records

- [ADR-0015 — Build under deny and verify before and after activation](../../adr/0015-build-under-deny-and-verify-before-and-after-activation.md)
- [ADR-0017 — Separate reference adoption, technical qualification and authorization](../../adr/0017-separate-reference-adoption-technical-qualification-and-authorization.md)
- [ADR-0036 — Require initial operational and recovery readiness before production activation](../../adr/0036-require-initial-operational-and-recovery-readiness-before-production-activation.md)

<!-- END GENERATED DECISION LINKS -->
