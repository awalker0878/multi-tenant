# Phase exit gates

These checklists define required outcomes; checked delivery results live only in [delivery-register.yaml](delivery-register.yaml). All gates begin `NOT_REVIEWED`. Each criterion requires its own evidence references and review; a prose description or unrun command is not evidence. Reviewers below are roles to assign in P00, not fabricated signatories. See [status rules](status-model.md) for E0–E4 and independent state axes.

Gate Gxx closes phase Pxx. Entry dependencies come from the phased plan and canonical register. P09 is evaluated per selected tranche; P10 must include every expansion tuple advertised for release. Negative and recovery cases remain required when the happy path passes. A failed criterion blocks the gate until corrected or the supported scope is explicitly revised and re-reviewed.

The [engineering coverage map](../engineering/coverage.md) supplies concrete framework and code-quality proof for the existing criteria below. Evaluate applicable ENG controls with their package's evidence; document a reviewed applicability reason or exception when needed. A common standard or passed documentation validator is not proof of an implemented control.

## G00 — Product and architecture baseline

| Criterion | Required pass/fail check | Evidence | Environment | Reviewer role |
| --- | --- | --- | --- | --- |
| G00.01 — Scope and ownership | Review the first application journey, roles, release exclusions and accountable owner assignments; identify every missing input. | E0: signed baseline and owner roster | Design review | Product lead |
| G00.02 — Domain invariants | Review valid and invalid Tenant/WSD/SecurityDomain/DomainInstance/Application examples; every intent, observation, plan, approval and effect has one writer. | E0: domain cases and authority review | Design review | Architecture lead |
| G00.03 — Dependency and infrastructure decisions | Resolve requested dependency locks in an isolated spike; build/typecheck the frontend and PHP/Python checks; accept now-blocking ADRs or reject the candidate explicitly. | E1: lockfiles, image versions and actual spike logs; E0: ADR decisions | Isolated compatibility environment | Engineering and SRE leads |
| G00.04 — Route feasibility | Pin candidate source/target/guest/data/topology; examine boot, disks, conversion and consistency constraints; record supported test scope and failure/recovery strategy; do not substitute a different migration method silently. | E0: tuple/authority/test design; E1/E2: actual bounded feasibility results | Isolated spike with approved fixtures; read-only lab inputs where available | Platform and qualification leads |
| G00.05 — Operating targets | Approve measurable load tiers, outage/data targets, threat model, custody/sovereignty and retention; design failed-dependency and post-write recovery scenarios. | E0: target measures, trust flows and recovery acceptance cases | Design review | SRE, security and application owners |
| G00.06 — Executable delivery backlog | Map all 36 requirements to packages, gates and campaigns; give outstanding decisions blocking checkpoints; P01 cards include owners, estimates and unblock conditions. | E0: traceability review and reviewed backlog | Repository review | Delivery and qualification leads |

## G01 — Delivery and runtime foundation

| Criterion | Required pass/fail check | Evidence | Environment | Reviewer role |
| --- | --- | --- | --- | --- |
| G01.01 — Independent builds | A clean checkout builds seven principal application images and selected worker images from exact locks and declared inputs. Context/layer ownership agrees with the registry. Laravel checks admit owned Eloquent models, framework-using Actions and normal entrypoints; complete language-aware checks reject cross-service, inverted-layer and unclassified source fixtures. Architecture suites execute over real source; skipped absent layers do not establish acceptance. PSR-4, formatter and static/Vue checks pass; an isolated service build does not silently import sibling source. | E1: build/typecheck/test logs, positive/negative architecture fixtures, locked inputs and image digests | Clean developer/CI runners | Engineering lead |
| G01.02 — Clean integration install | Install into an empty isolated integration environment, seed synthetic data and exercise authenticated health; no production credentials or endpoints are present. | E2: install inventory, health/auth results and endpoint restriction check | Integration | SRE lead |
| G01.03 — Cross-language contracts | Validate PHP/Python payload compatibility and safe error/field handling; reject incompatible payload/version and wrong tenant/caller. Prove duplicate inbox delivery, atomic rollback and relay recovery after commit-before-publication failure against real dependencies. | E1/E2: conformance, transaction/crash and negative messaging reports | CI and real-dependency integration | Architecture and quality leads |
| G01.04 — Supply-chain provenance | Verify required checks and actual owner/role review enforcement, trusted policy changes, dependency-aware CI and locked dependency/security checks. Missing or failed checks, insufficient review and expired exceptions cannot admit a change. Publish signed images/SBOM/manifest; reject unsigned or mismatched artifacts. | E1/E2: actual repository policy and safe admission/rejection proof, digest/signature records and negative promotion result | CI, reviewed repository configuration and isolated registry | Security and SRE leads |
| G01.05 — Data and secret isolation | Prove runtime roles cannot read other service databases or execute schema administration; exercise controlled migrations and invalid/revoked workload identity. | E2: database/identity negative tests and dependency configuration | Integration | Security and service owners |
| G01.06 — Baseline recovery | Restore a synthetic database and evidence object, verify identity/digest, restart services, deliver a test alert and rehearse failed deployment recovery with native writes disabled. | E2: restore/restart/alert receipt and deployment recovery records | Integration | SRE and qualification leads |

## G02 — Identity, tenancy and governance

| Criterion | Required pass/fail check | Evidence | Environment | Reviewer role |
| --- | --- | --- | --- | --- |
| G02.01 — Identity and isolation | Q01 denies forged tenant, guessed IDs, wrong audience, expired token and unauthorized search/export/evidence access for at least two tenants. Include cache/file/job context, props/history, field permissions and real browser request-forgery/session boundaries. | E1/E2: permission/surface matrix, middleware/browser and negative results | Integration | IAM and security leads |
| G02.02 — Bound approvals | Plan digest, action, resource scope, expiry and separation of duties bind approval; edited/revoked plans cannot reuse it. | E2: approval and revocation scenarios | Integration | Governance owner and quality lead |
| G02.03 — Dependency failure | Issuer/key service loss follows the selected fail-closed behavior; rotation and revocation prevent new privileged admission. | E2: identity failure/recovery observations | Integration | IAM and SRE leads |
| G02.04 — Audit and usability | Approval/audit restart preserves immutable history; revocation does not discard already committed audit/custody facts. Delegated roles complete tenant selection and denied/session/conflict journeys under the selected accessibility scope; stale responses/history cannot cross tenant context. | E2: restart/revocation and browser/accessibility task reports | Integration | Product and quality leads |

## G03 — Application catalogue and workspace

| Criterion | Required pass/fail check | Evidence | Environment | Reviewer role |
| --- | --- | --- | --- | --- |
| G03.01 — Application intent | Register/revise the synthetic multi-workload, multi-domain application and inspect immutable history through service APIs. | E1/E2: Q01 domain and UI reports | Integration | Catalogue owner |
| G03.02 — Negative invariants | Cross-tenant/domain associations, dangling references, dependency cycles and concurrent stale edits fail deterministically. | E1/E2: invariant and conflict matrix | CI/integration | Architecture and quality leads |
| G03.03 — Retry and persistence failure | Duplicate command creates one revision; outbox failure rolls back mutation; restart and replay retain history without duplicate intent. | E2: transaction/fault and replay evidence | Integration PostgreSQL/broker | Quality lead |
| G03.04 — Operator task | Owner can explain validation errors, compare revisions and complete the journey with declared accessibility constraints. Query/payload bounds and safe resource serialization hold on representative tenant data. | E2: browser, query/bounds and representative-user review | Integration | Product owner |

## G04 — Site commissioning and inventory

| Criterion | Required pass/fail check | Evidence | Environment | Reviewer role |
| --- | --- | --- | --- | --- |
| G04.01 — Native read-only coverage | Selected OpenStack and VMware lab discovery returns stable native IDs/provenance; every VMware/AHV/OpenStack profile dimension has a fact contract or explicit gap. | E3: scoped read-only Q02 results; E0/E1: all profile contracts | Authorized native read-only lab | Inventory/platform owners and qualification lead |
| G04.02 — Incomplete and hostile input | Partial pages, hidden privilege gaps, reused IDs, stale generation and revoked collectors produce visible holds; guessed cross-tenant identifiers and unapproved endpoints fail. | E2/E3: Q02 negative coverage | Integration and native lab | Security and qualification leads |
| G04.03 — Budget and disconnection | Rate limits and fairness stay within approved endpoint budgets; lost connection expires freshness and recovery resumes/reconciles a complete generation. | E2/E3: fault/resumption and load measurements | Integration and native lab | SRE and inventory owners |
| G04.04 — No ownership inheritance | Discovered unowned resources stay observation-only; collision stops proposed adoption; verify discovery introduced no resource changes. | E3: before/after observations and ownership review | Native read-only lab | Independent platform observer |

## G05 — Capabilities and immutable plans

| Criterion | Required pass/fail check | Evidence | Environment | Reviewer role |
| --- | --- | --- | --- | --- |
| G05.01 — Explainable outcomes | Two authorized destinations produce eligible, blocked or unknown results with pinned facts, qualification and remediation. | E1/E2: Q03 assessment cases | Integration/simulation | Planning and quality leads |
| G05.02 — Plan integrity | Canonical plans fix versions, object mappings, budgets, effects and recovery boundaries; material changes invalidate approvals. | E1/E2: plan digest and invalidation reports | CI/integration | Architecture and governance owners |
| G05.03 — Safety denials | Stale facts, unknown mandatory capabilities, missing sovereignty/tenant controls and absent exact-tuple evidence cannot yield operational eligibility. | E1/E2: Q03 negative cases | Integration/simulation | Security and assurance owners |
| G05.04 — Reservation failure | Concurrent plans, partial reservations, timeout and expiry follow lifecycle journal/owner receipts; observed live allocations are not released on timer alone. | E2: simulated race/compensation/reconciliation reports | Integration/simulation | Lifecycle and quality leads |

## G06 — Durable execution in simulation

| Criterion | Required pass/fail check | Evidence | Environment | Reviewer role |
| --- | --- | --- | --- | --- |
| G06.01 — End-to-end simulation | Register, assess, plan, approve, admit, execute, observe and review evidence through all contexts; UI labels all synthetic outcomes. | E2: full Q01/Q03/Q04 journey | Integration with real persistence/Temporal and controlled adapters | Product and qualification leads |
| G06.02 — Authority enforcement | Reject stale/revoked approval, wrong worker/epoch, ownership collision and unsupported operational tuple; separate lab campaign endpoints/credentials/scope. | E2: Q03/Q04 denial matrix | Integration/simulation | Security and lifecycle owners |
| G06.03 — Unknown outcome recovery | Crash before/after effect acceptance, duplicate dispatch, lost acknowledgement, stale worker and partition produce one logical operation or a held unknown outcome; reconciliation precedes retry/release. | E2: Q04 fault timeline and independent simulated readback | Integration/simulation | Quality and SRE leads |
| G06.04 — Evidence and baseline controls | Validate digests, redaction, tenant access and tamper rejection; recover persisted jobs safely, deliver actual alert and exercise emergency stop at defined boundaries. | E2: evidence/restore/alert/stop reports | Integration/simulation | Assurance, security and SRE leads |

## G07 — Native OpenStack provisioning

| Criterion | Required pass/fail check | Evidence | Environment | Reviewer role |
| --- | --- | --- | --- | --- |
| G07.01 — Qualified provisioning | Commission exact OpenStack tuple; execute reviewed saved plan, hardening and real service integrations; independently observe readiness before activation. | E3: Q05 provisioning and owner receipts | Authorized native qualification lab | Platform, service and qualification owners |
| G07.02 — Policy and scope denials | Q06 proves allowed flows and denied tenant/tier/edge paths, same-host/subnet and relevant IPv6/return behavior; wrong plan/scope/ownership cannot mutate. | E3: Q05/Q06 traffic and authority matrix | Native lab exact topology | Security and independent observer |
| G07.03 — Failure and restore | Partial provision, lost response, restart, revocation and failed activation remain contained; restore application data and reconcile before further writes. | E3: Q04/Q05 fault/restore dossier | Native lab | SRE, application and qualification owners |
| G07.04 — Retirement and support bounds | Separate retirement authority preserves retention, confirms deletion/release of only owned resources and publishes exact tested tuple/limits. | E3: retirement receipts and qualification review | Native lab | Governance and assurance owners |

## G08 — VMware-to-OpenStack migration

| Criterion | Required pass/fail check | Evidence | Environment | Reviewer role |
| --- | --- | --- | --- | --- |
| G08.01 — Rehearsal and correctness | Selected VMware-to-OpenStack offline method handles all approved datasets and identities; isolated rehearsal suppresses business effects and meets accepted measures. | E3: Q07 method/tuple/correctness and timing evidence | Authorized migration lab | Application and qualification owners |
| G08.02 — Cutover authority | Independent source/other-writer fencing, final synchronization and validated target precede target traffic/writes; stale authority and unfenced source are denied. | E3: Q07 ordered observations and negative cutover tests | Native migration lab | Security and independent observer |
| G08.03 — Two recovery boundaries | Prove rollback before target writes; after a target write prove source-return with reconciliation or approved forward recovery without data loss outside accepted objectives. | E3: Q07 interruption, restore and data reconciliation evidence | Native migration lab | Application, SRE and qualification owners |
| G08.04 — Accepted application path | Service/policy paths and measured outage/data objectives pass; source retention and separate retirement criteria are reviewed; reverse route remains unqualified. | E3: Q05/Q06/Q07 dossier and bounded support review | Native migration lab | Application/service owners and assurance |

## G09 — Platform and capability expansion

| Criterion | Required pass/fail check | Evidence | Environment | Reviewer role |
| --- | --- | --- | --- | --- |
| G09.01 — Tranche scope | Freeze exact source/target directions, guest/method/topology/capability tuples and exclusions before qualification; map every selected expansion requirement. | E0: tranche baseline; E1/E2: adapter conformance | Design/CI/integration | Product and architecture leads |
| G09.02 — Independent route support | Each advertised tuple passes its own native positive/negative/security tests; no reverse-direction or vendor-wide inference. | E3: Q08 and applicable Q05–Q07 results | Authorized exact-tuple labs | Platform/security/qualification owners |
| G09.03 — Adoption safety | No-change import proves object/field scope and old writer transfer; collisions, drift and unknown outcomes block mutation and support detach/reconciliation. | E3: Q02/Q08 adoption and failure evidence | Authorized brownfield lab | Inventory/lifecycle and independent observer |
| G09.04 — Expansion operations | Rerun affected common paths; exercise adapter upgrade/recovery, scheduling pause/stop and concurrent-impact budgets; update support/runbooks with limitations. | E2/E3: Q04/Q08/Q10 results and reviewed support scope | Integration and native labs | SRE and qualification leads |

## G10 — Enterprise operating qualification

| Criterion | Required pass/fail check | Evidence | Environment | Reviewer role |
| --- | --- | --- | --- | --- |
| G10.01 — Measured resilience | Approved scale, latency/SLO, native endpoint limits, failure domains and control-plane RPO/RTO pass with representative mix. | E3/E4: Q09/Q10 performance/failure/restore measurements | Representative preproduction and qualified native labs | SRE, performance and service owners |
| G10.02 — Restore and upgrade safety | Restore DB/workflows/evidence/state/keys read-only, reconcile epochs/native outcomes and enable writes only after review. Prove mixed-version contracts/jobs, expand/contract and interrupted backfills, applied migration state, key rotation and worker draining with their recovery limits. | E3/E4: Q09 full restore and upgrade/failure evidence | Preproduction | Independent SRE and qualification reviewers |
| G10.03 — Security and installation | Applicable versioned security-verification requirements and required findings close; deployed browser/tenant/input controls, custody/sovereignty, key/identity rotation and clean/restricted-network installation pass for selected scope. Verify protected runtime configuration and probe behavior. | E3/E4: Q09 security/applicability, install and dependency-recovery records | Preproduction approved trust boundary | Security and service owners |
| G10.04 — Release support acceptance | Release candidate reruns affected tuples, delivers alerts/on-call exercises and reconciles artifacts/evidence/claims; receiving team accepts responsibilities and limitations. | E4: Q09/Q10 release dossier and receiving-owner decision | Preproduction/operational review | Service owner and qualification lead |

## G11 — Pilot and supported release

| Criterion | Required pass/fail check | Evidence | Environment | Reviewer role |
| --- | --- | --- | --- | --- |
| G11.01 — Production commissioning | Approved environment/tenant/site/credentials/backup/monitoring and change windows match qualified release scope. | E4: commissioning and authorization records | Production readiness review | SRE/security/service owners |
| G11.02 — Controlled pilot | Trained independent operators complete bounded application tasks, observe agreed period and meet usability/performance/integrity objectives. | E4: Q10 pilot outcomes and user acceptance | Approved production pilot | Product/application and service owners |
| G11.03 — Operational handover | An operator other than the developer installs/recovers through runbooks; support, escalation and audit export are exercised without unauthorized writes. | E4: observed handover and recovery exercise | Approved recovery environment and pilot | Receiving operations and qualification leads |
| G11.04 — Bounded release and history | Signed release manifest, installed digests, tested support matrix and limitations reconcile; historical state is explicitly archived/imported or reviewed inapplicable before retirement. | E4: release approval; E0/E3/E4 as applicable for historical disposition | Release review and approved disposition environment | Product/service/records owners |

## Gate review record

A gate review records the gate and individual criterion IDs, release/source revisions, selected scope, campaign and immutable evidence IDs, actual reviewer/date, failed or inapplicable criteria with reasons, blocker IDs and resulting decision. Store accepted records under the planned `docs/qualification/gate-reviews/` index, with sensitive evidence in the approved evidence store; register only immutable references. The register owns the current decision. An ADR proposal, role assignment or documentation approval is not an execution permit.
