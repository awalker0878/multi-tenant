# 5. Qualification stages, applicability and evidence

[Documentation home](../../README.md) · [Source document](../../../reference/Portable_Hosting_Delivery_Kits_v1_1/05_Reference_v1_4/06_Site_Design_Qualification_and_Operations_v1_4.docx) · [Chapter index](README.md)

> **Source:** QUAL — Draft v1.4. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: 783edbba45483d0d3c3b966765589762698836320237906a0f9a60080574af37 -->
<!-- SOURCE-BLOCK QUAL:63 BEGIN -->

<a id="__RefHeading___Toc10041_1525915568"></a>
<a id="QUAL_s_005"></a>

<!-- SOURCE-BLOCK QUAL:63 END -->

<!-- SOURCE-BLOCK QUAL:64 BEGIN -->

WD §13 adds twelve connected-design assertions with all execution statuses not-run. Same-domain qualification requires an actual endpoint pair and approved placement; the four-endpoint base fixture alone cannot supply it. WD §11 records the extra temporary resource demand. No test is deemed passed from a diagram, a schema check or a count of linked requirements.

<!-- SOURCE-BLOCK QUAL:64 END -->

<!-- SOURCE-BLOCK QUAL:65 BEGIN -->

Parent architecture: [RA §15](../../architecture/reference/15-cross-vendor-realization-model.md#RA_s_015)  •  [RA §28](../../architecture/reference/28-architecture-acceptance-and-verification.md#RA_s_028)  •  [RA §30](../../architecture/reference/30-implementation-handoff-and-delivery-sequence.md#RA_s_030)

<!-- SOURCE-BLOCK QUAL:65 END -->

<!-- SOURCE-BLOCK QUAL:66 BEGIN -->

The retained 80 CT procedures and 12 realization addenda are reference specifications, all carried forward as not-run. This release does not execute infrastructure tests. Select procedures and individual required observations against the actual offered service class, topology, address family, sharing mode and change. A reference list is not itself a test campaign or proof that every assertion is covered. \[[B2](09-references-parent-basis-and-external-context.md#QUAL_src_B2) §28\]

<!-- SOURCE-BLOCK QUAL:66 END -->

<!-- SOURCE-BLOCK QUAL:67 BEGIN -->


<a id="source-table-67"></a>

| Qualification stage | Scope | Avoid circular or overstated acceptance |
| --- | --- | --- |
| First-stack foundation/service qualification | All applicable single-stack isolation, resource, management, lifecycle, failure and recovery observations. | Do not require two already-qualified platforms as a prerequisite to qualifying the first. |
| Second-stack outcome comparison | Repeat the common fixture and expected service/security outcomes on the second eligible realization. | Equivalent semantics, not identical native object IDs. |
| Portability/exit qualification | Representative image/data transfer or restore, identity/key/network rebinding and service acceptance. | Provisioning on two platforms alone does not prove migration or data portability. |
| Routine tenant deployment/change | Affected paths/resources plus stable critical isolation, service and ownership checks. | Avoid destructive shared-platform fault injection on every tenant create. |
| Shared foundation upgrade | Representative affected lifecycle, path, capacity and failure regression before broad rollout. | A provider/version change can alter behaviour even when request syntax is unchanged. |
| Operational recovery and retirement | Accepted cadence plus material changes; isolated restore, writer control, access/copy cleanup. | Not-run or unknown outcome cannot satisfy a mandatory service promise. |

<!-- SOURCE-BLOCK QUAL:67 END -->

<!-- SOURCE-BLOCK QUAL:68 BEGIN -->

<!-- SOURCE-BLOCK QUAL:68 END -->

<!-- SOURCE-BLOCK QUAL:69 BEGIN -->

For a compound requirement, list its assertions and show the observation supporting each. For example, management separation includes routing isolation, native API permission and surviving recovery access; one ping failure cannot prove all three. Many-to-many requirement/test links are useful navigation but do not substitute for assertion coverage. This is an assurance record, not a demand for a new evidence microservice.

<!-- SOURCE-BLOCK QUAL:69 END -->

<!-- SOURCE-BLOCK QUAL:70 BEGIN -->


<a id="source-table-70"></a>

| Observation class | Example from the reference fixture | Required evidence |
| --- | --- | --- |
| Tenant/domain isolation | D01O/R cannot reach D02O/R; processor-01 reaches only the declared data-01 service. | Healthy allowed controls, actual policy/routing and attributed deny/allow observations. |
| Native boundary path | No VPC connected, Tier-0/inter-VRF or Neutron distributed/provider shortcut. | Native configuration and data-path/enforcement trace on selected tuple. |
| Resource and trust isolation | Foreign disk/copy/key use and administrative scope denied. | Target-service decisions and actual ownership/custody records. |
| Safe lifecycle | Lost API response, changed approval, import, update and delete reconcile correctly. | Native task/state comparison, no unexpected replacement or orphaned authority. |
| Failure and recovery | Edge loss, eligible host restart, KMS/control outage and isolated restore. | Authorized fault scope, timestamps, survivor capacity, consistency and controlled recovery. |

<!-- SOURCE-BLOCK QUAL:70 END -->

<!-- SOURCE-BLOCK QUAL:71 BEGIN -->

<!-- SOURCE-BLOCK QUAL:71 END -->

<!-- SOURCE-BLOCK QUAL:72 BEGIN -->

Each actual execution identifies the exact component/API/provider releases, topology, service parameters, applicable requirement assertions, address families, endpoints, preconditions, observed result, artifact identity and reviewer. Acceptable outcomes distinguish passed, failed, blocked, not-run and not-applicable with approved rationale. No unexecuted test is prefilled as passed, and an unsigned status string is not a formal risk decision.

<!-- SOURCE-BLOCK QUAL:72 END -->

<!-- SOURCE-BLOCK QUAL:73 BEGIN -->

Intrusive negative tests and fault injection require authorization, an isolated or controlled scope and a recovery procedure protecting unrelated tenants. Tests establish outcomes for the measured scope; a small fixture is not proof of maximum production scale or every possible path. Requalification follows changes to the used enforcement, topology, backend, sharing or service constraints.

<!-- SOURCE-BLOCK QUAL:73 END -->

<!-- SOURCE-BLOCK QUAL:74 BEGIN -->

Related engineering: [Paths and expected denials](../../engineering/fabric/3-worked-inter-zone-routing-and-enforcement-schedule.md#NET_s_003)  •  [Actual qualification tuple](../../engineering/platform-realizations/7-implementation-tuple-and-decision-package.md#VND_s_007)  •  [Control responsibility](6-control-inheritance-assurance-and-organizational-interfaces.md#QUAL_s_006)

<!-- SOURCE-BLOCK QUAL:74 END -->

[Previous chapter](4-service-parameter-and-requirement-decisions.md) · [Chapter index](README.md) · [Next chapter](6-control-inheritance-assurance-and-organizational-interfaces.md)

<!-- BEGIN GENERATED DECISION LINKS -->

## Related decision records

- [ADR-0017 — Separate reference adoption, technical qualification and authorization](../../adr/0017-separate-reference-adoption-technical-qualification-and-authorization.md)

<!-- END GENERATED DECISION LINKS -->
