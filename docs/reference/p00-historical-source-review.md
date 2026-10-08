# P00 historical source review

Review date: 2026-10-04. Reviewed by Codex for P00.01 and supporting P00.02/P00.04/P00.05. This is a source-analysis record, not product-owner acceptance, execution evidence or native qualification.

The user requested the previous `implementation/all-waves` branch as an information source while preserving the new direction. The reviewed snapshot is **`a2963d8d43e25f08d70fbd99b0e5e19ab5c9828e`**. The current greenfield baseline at the start of this review is **`7080178`** on `greenfield/enterprise-microservices-plan`. Later edits on either branch do not silently alter this comparison.

## Precedence and method

The current [source precedence](sources-and-reset.md), [product scope](../product/scope.md), [domain model](../product/domain-model.md), [phase plan](../implementation/phased-plan.md) and [ADR-024](../decisions/adr-024-pragmatic-laravel-domain-convention.md) remain authoritative. Historical documents supply requirements and failure lessons. Their implementation claims were read as historical claims; this review did not independently execute the old code or verify its test reports.

During P00, the user asked whether rebuild/restore should be preferred. The current recommendation is application rebuild/restore for the first reproducible application, with whole-VM disk conversion separately scoped to P09. This is an explicit revision of the earlier greenfield cold-conversion proposal, not an automatic adoption of historical code or an accepted ADR-014 decision.

No old runtime code, manifests, dependency locks, migration scripts, fixture permissions or deployment settings are imported. Historical B01–B50 identifiers help explain provenance only; P00–P11, R01–R36 and the current gate/campaign IDs remain the delivery system.

## Reviewed sources

All links below use the same immutable source commit. Blob IDs identify the exact files returned by the GitHub connector.

| Source | Blob ID | Reviewed subject |
| --- | --- | --- |
| [README.md](https://github.com/awalker0878/multi-tenant/blob/a2963d8d43e25f08d70fbd99b0e5e19ab5c9828e/README.md) | `b22aff7304f3fbb827dbf7b5e7ae5fb691160f97` | Product purpose, native/implementation distinctions, existing mechanisms and historical reference realization |
| [docs/product/enterprise-workload-mobility-execution-plan.md](https://github.com/awalker0878/multi-tenant/blob/a2963d8d43e25f08d70fbd99b0e5e19ab5c9828e/docs/product/enterprise-workload-mobility-execution-plan.md) | `2000b3484d25b6fb8bee87c95dff2fe53f07ba50` | Current-position and selected-application sections, wave obligations, external holds and research-driven acceptance delta |
| [docs/product/decisions/product-mandate.md](https://github.com/awalker0878/multi-tenant/blob/a2963d8d43e25f08d70fbd99b0e5e19ab5c9828e/docs/product/decisions/product-mandate.md) | `3a35799d43a6f32ebc918117ac6f3f524674105f` | User-facing lifecycle, one governed authority and separation from native systems |
| [docs/product/decisions/workload-and-security-boundary.md](https://github.com/awalker0878/multi-tenant/blob/a2963d8d43e25f08d70fbd99b0e5e19ab5c9828e/docs/product/decisions/workload-and-security-boundary.md) | `50913e1932ef4477f847bb59cb2ab9fe1cbf01e5` | Application/workload identity, WSD distinction, datasets and source/target bindings |
| [docs/product/decisions/state-ownership.md](https://github.com/awalker0878/multi-tenant/blob/a2963d8d43e25f08d70fbd99b0e5e19ab5c9828e/docs/product/decisions/state-ownership.md) | `5d52c2972cb9c46200af7ba64a947562eb75fc98` | Authoritative writers, unknown effects, outbox and retained-state transition |
| [docs/engineering/application-migration-runtime.md](https://github.com/awalker0878/multi-tenant/blob/a2963d8d43e25f08d70fbd99b0e5e19ab5c9828e/docs/engineering/application-migration-runtime.md) | `9e5c0ab926f983ac6a4b5dc456e28bf1413e72eb` | Selected rebuild/restore boundary, per-dataset identity, current command authority and held outcomes |
| [docs/operations/retained-state-conversion-rehearsal.md](https://github.com/awalker0878/multi-tenant/blob/a2963d8d43e25f08d70fbd99b0e5e19ab5c9828e/docs/operations/retained-state-conversion-rehearsal.md) | `588972308b85d50712c8c7316044527c40b00af7` | Original custody, count/digest reconciliation, unknown starts and observation-only handover |

## Disposition into the new product

“Adopt” retains an outcome or invariant, not its implementation. “Refine” adapts the historical meaning to the new context/service model. “Reject” declines a historical choice or inference that conflicts with current direction.

| Historical finding and source | Disposition | Current requirement and delivery destination |
| --- | --- | --- |
| Product mandate requires operators to describe, discover, compare, plan, approve, execute and recover an application, including its useful services | **Adopt.** Use the current console journey and synthetic Permit Desk case; successful VM creation alone never means successful application delivery | R01, R05, R18, R21, R33; P00.01 and P03–P08 |
| Workload/security decision distinguishes stable workload identity, application membership, WSD scope, native bindings and datasets | **Refine.** Use current `Application`, `ApplicationDeployment`, `Workload`, `IntentRevision`, `WSD`, `SecurityDomain` and `DomainInstance`; do not introduce `ApplicationGroup` as a second model | R05–R07, R19; P00.02, P03, P05 |
| State-ownership decision describes one product database and one installable application | **Refine.** Preserve one authority for each fact/effect through six business contexts and the console boundary, service-private stores and versioned APIs/events. Do not restore a shared product schema or monolithic source layout | R01–R02, R15–R17; P00.02 and P01/P06 |
| Old selected application is VMware → OpenStack **REBUILD_RESTORE**, Ubuntu 24.04; lower cold-capture work does not complete target boot/remediation | **Refine with explicit current direction.** Rebuild/restore is now the preferred P00 proposal for a reproducible application. Keep ADR-014/P00.04 feasibility and owner review open; do not inherit the old guest/image tuple, code or verification. Whole-VM conversion is a separately qualified P09 option | R19, R22–R24, R27; P00.04, P08 and P09 |
| Old migration runtime requires complete dataset mapping, exact selected inputs, live command authority and held uncertain effects | **Adopt safety outcomes.** Reimplement through the new Lifecycle/native-operation boundaries; no old descriptors, activity names or helper imports become current wire contracts | R14–R17, R22–R24; P05–P08 |
| Old execution plan distinguishes repository verification, native qualification and operating acceptance, with unqualified installed tuples | **Adopt.** Preserve four independent state axes and exact-tuple evidence in the current register. Never copy old completion labels, counts or passing reports onto this branch | R13, R31, R35; all phase gates |
| Historical profiles represent many capabilities and typed properties, including boot, disks, keys, datapath bypass and recovery | **Refine.** Use the current capability dimensions and qualification matrix. Historical coverage counts are a review aid, not a frozen schema, support claim or reason to skip a missing dimension | R09, R13, R19–R20, R26–R27; P04/P05/P07/P09 |
| Historical realization names NetBox, GitLab state, restic, Ubuntu and a provider-owned edge | **Reject automatic selection.** Each is historical configuration. P00 chooses dependency/service contracts and the exact feasibility tuple; no enterprise deployment, entitlement or endpoint is inferred | R08, R17–R22, R29, R32; P00.03–P00.05 |
| Retained-state rehearsal preserves originals and unknown starts, inventories source counts and starts new ownership observation-only | **Adopt conditional safeguards.** Actual retained operational state remains unconfirmed. ADR-021 requires a records-owner inventory/applicability decision before selecting archive/import work | R11, R16, R29, R36; P00.01/P00.05 and P10 |
| Historical delivery sequence includes all routes, Windows and other whole-VM/database methods | **Refine.** Retain expansion visibility in the current support matrix; first delivery is selected Linux/OpenStack provisioning and VMware → OpenStack application rebuild/restore, with an accepted final application outage | R22, R26–R28, R35; P00.01 and P09–P11 |

## Findings that change implementation preparation

1. **Verify the newly preferred method independently.** Historical rebuild/restore code does not demonstrate the new implementation. P00.04 needs reproducible target artifacts, application/database restore compatibility, complete data/key handling, source fencing, cutover/recovery design and bounded executable results. Unrebuildable applications remain blocked for this method; they do not trigger automatic disk conversion.
2. **Do not import a shared database assumption.** Earlier authority tables describe ownership principles; the new service registry assigns each private store, contract and writer. Cross-service SQL remains prohibited.
3. **Do not mistake historical import tools for a deployed estate.** No operational inventory, retained originals or old-writer roster was supplied in this review. Both “no state exists” and “an importer is required” remain unproved.
4. **Keep useful-service and uncertainty tests early.** Plan the negative/recovery obligations before native implementation: expired approval, partial reservation, missing dataset, interrupted effect, unresolved source writer and a target write followed by failure.

The greenfield safety obligations are retained while the first-method proposal is explicitly revised to rebuild/restore following the current discussion. The [P00 scope review](../implementation/p00-scope-review.md) turns that proposal into concrete review questions and acceptance cases. No historical implementation or qualification status is carried forward.

## Review limits and follow-up

This review reads documents at a pinned revision. It does not audit every historical source file, re-run the earlier branch, assess current site access or authenticate any operational acceptance. Historical implementation claims are neither accepted nor disproved by this document.

Prospective product/application/service reviewers must confirm the first-slice scope. The records owner must determine retained-state applicability. Platform and qualification reviewers must resolve the proposed migration method with actual bounded feasibility evidence. Record those decisions against G00 rather than editing this historical comparison to imply they already occurred.

## Tooling continuation source check

The [Python tooling continuation](../implementation/p00-python-tooling-results.md) re-read the pinned historical `pyproject.toml` (blob `e160485bab8a2e665843e303e0caa2e69b9c8dfa`) and engineering TAD navigation (blob `ad51d70454cbcfd0071a943478bf844496b26631`). Exact dependency identity and explicit composition are useful review inputs. The earlier single `provisioner` package, optional infrastructure libraries and historical verification claims are not current service boundaries or implementation evidence. The new probe uses two synthetic service namespaces and the current four-layer Python rule, while PHP independently follows ADR-024.
