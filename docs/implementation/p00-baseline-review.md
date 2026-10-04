# P00 baseline review and delivery handoff

Review started: 2026-10-04. Prepared by Codex during the user-authorized P00 work. This is an engineering assessment and review packet, not an accountable-owner approval. Actual package, requirement, evidence and blocker states belong to the [delivery register](delivery-register.yaml).

## Source precedence and work performed

The greenfield branch at `7080178b4df51c836a05349ed2c91d190d15fcfa` is the starting design baseline. Historical `implementation/all-waves` material was inspected at `a2963d8d43e25f08d70fbd99b0e5e19ab5c9828e`. The [source review](../reference/p00-historical-source-review.md) identifies the files examined and the disposition of their information. No old runtime, passing test, credential, support claim or operating acceptance was imported.

The current P00 discussion identifies application rebuild/restore as the preferred first migration recommendation for applications that can be reproduced. This is a reasoned revision to the earlier proposed cold-conversion route, not inheritance of the historical driver's implementation status. ADR-014 remains proposed until its method/profile and feasibility are reviewed. The greenfield stack, independently owned microservices and convention-only ADR-024 remain unchanged.

| Package | Inspectable work prepared | Remaining acceptance obligation |
| --- | --- | --- |
| P00.01 | [Scope review](p00-scope-review.md): personas, permitted actions, first journey, release exclusions and retained-state alternatives | Product/application/service owners and records owner confirm scope, accountability and retained-state applicability |
| P00.02 | [Domain review](p00-domain-review.md): positive/negative association cases, authoritative writers, field ownership and command/event concurrency | Architecture, security and context reviewers accept or revise the explicit recommendations before schemas freeze |
| P00.03 | [Compatibility index](p00-compatibility-results.md), [Python tools](p00-python-tooling-results.md), [Laravel HTTP/quality](p00-integration-results.md), [browser results](p00-browser-results.md), [candidate image/BOM](p00-image-results.md) and [contract tooling](p00-contract-tooling-results.md): implemented probes with source-bound inputs and report-specific execution outcomes | Review each actual result and unresolved execution limit; select operated image/mirror, managed-browser, contract dialect/tool and runtime/trust dependencies with accountable owners; no product-runtime claim follows from a spike |
| P00.04 | [Route review](p00-route-and-operations-review.md) and [feasibility record](../qualification/feasibility/initial-route.md): method-specific input and experiment matrix | Pinned candidate and approved reproducible application fixture, bounded deployment/restore/recovery observations; actual native facts/authority apply to any native cases performed |
| P00.05 | Route/operations review and [operating measures](../product/operating-targets.md): workload distributions, measurement definitions and failure/recovery cases | Owners select measurable workload, outage/data, custody, retention and support constraints |
| P00.06 | This handoff, [consolidated decision/input review](p00-decision-and-input-review.md), package/checkpoint audit, regenerated views and executable documentation/control checks | Named review capacity, dependency dates, remaining evidence and accountable G00 review |

## Decisions to review against concrete recommendations

These recommendations develop the existing proposals. They do not change the [decision register](../decisions/decision-register.md) to accepted by implication. The [decision/input review](p00-decision-and-input-review.md) turns them into DC01–DC10 choices, IP01–IP07 finite input packages and a criterion-by-criterion G00 examination. It distinguishes engineering that can execute now from the actual unprovided owner, operating and lab inputs; it adds no blanket permission step.

| Decision group | Working recommendation and rationale | Blocking checkpoint |
| --- | --- | --- |
| ADR-004/005 | Retain six business services plus the console, with one authoritative owner for each model and separate builds. The domain case matrix does not identify a reason to split every capability into a new deployable. | Before P01.01/contract scaffolding |
| ADR-006 | Retain PostgreSQL with separate service databases/roles and controlled migrator identities. A shared operated cluster is an initial deployment option, subject to trust and recovery requirements. | Before P01.05 |
| ADR-007/008 | Retain Temporal/Python for durable workflows and RabbitMQ as the candidate event broker. Outbox/inbox, replay/retention and transport ACLs still need real integration proof; broker delivery does not grant native-effect authority. | Before P01.03/P01.05; workflow semantics before P06 |
| ADR-009/010 | Use enterprise OIDC and separately scoped service/delegated identities, external secrets/key custody and protected S3-compatible evidence. Keep provider and issuer choices open until installation owners supply actual capabilities. | Trust prerequisites before P01.06; authorization semantics before P02 |
| ADR-011/020 | Retain the proposed central Kubernetes topology and scoped site workers. Select distribution, CNI, registry/mirrors and required disconnected behavior together with an operating owner. Public registry access in this spike does not prove an enterprise installation path. | Before P01.02/P01.04 |
| ADR-012/013 | Preserve schema-first API/events, immutable intent revisions, one writer per state and the service-private model. Review the contract-tool experiment's explicit dialect and generated-client validation limits; generation does not select domain semantics. Adopt the domain review's dataset/native-identity/reservation distinctions through the owning review. | Before public schema freeze and P03 persistence |
| ADR-014/015/018 | Prefer `application_rebuild_restore` for the initial reproducible Linux application; pin an exact source/target/application tuple and separate lab authority. Whole-VM conversion is independently selected and qualified in P09. | G00.04 and before native campaigns |
| ADR-017/021/022 | Keep initial/growth workload and service targets as proposed inputs; make retained-state and release breadth decisions explicit. No estate-wide capacity, retention period or application outage objective is inferred from historical documentation. | G00.01/G00.05; final release scope before P09/P10 |
| ADR-019 | Retain compiled assets, server sessions and polling initially. The actual Vue/Inertia build informs compatibility but does not prove authenticated browser behavior. | Before P01.01; browser/session evidence in P02 |
| ADR-001/002/024 | Preserve the accepted greenfield reset, requested stack and pragmatic Laravel convention. Do not add Boost or its DDD package. | Binding directions throughout delivery |

## P01 readiness and sequence

| Package | Work that can be prepared now | Entry condition before implementation is claimed ready |
| --- | --- | --- |
| P01.01 | Service-local source maps, synthetic convention fixtures, measured dependency candidates and the implemented candidate image/BOM experiment | Applicable NOW decisions, accepted build inputs and independent builds of the actual service images; a synthetic image probe does not build seven product services |
| P01.02 | Compose deployment/runbook inputs and isolated integration configuration | Selected platform, dependency endpoints and trust/custody constraints; no production credentials |
| P01.03 | Owned API/event examples, positive/negative schema cases and the implemented contract generation/validation experiment | Reviewed domain/service ownership, selected dialect/tool tuple, broker choice, compatibility rules and real outbox/inbox test environment |
| P01.04 | Required-check definitions, narrow workflow permissions and reviewed action pins | Actual authorized reviewer identities and verified merge/release settings; a workflow file alone is insufficient |
| P01.05 | Private database/role and dependency restore designs | Approved runtime images, stateful dependency choices and operated ownership |
| P01.06 | Tenant reset, failure/drain and recovery test designs | Implemented identities/dependencies and usable integration restore path |

The current cards contain 36 requirements, 67 packages, 12 phase gates and 24 engineering controls. Their joins and document references are checked by `scripts/validate_docs.py`; meaningful native-negative and recovery coverage is also reviewed in the domain and route matrices. Count consistency is not proof that a product requirement is implemented.

No staffing roster or confirmed external dates was supplied in this session. Retain the [conditional estimate assumptions](estimation-and-dependencies.md); do not turn parallel agent drafting or short spike duration into a revised enterprise delivery commitment. Re-estimate implementation after the first real P01 integration slice and native work after fixture/access availability is known.

## Evidence and review discipline

Registered EV-P00-001–007 bind successful frontend, Python library/tooling and remote Laravel HTTP/quality/browser observations to immutable source/artifact revisions. The [image](p00-image-results.md) and [contract](p00-contract-tooling-results.md) reports record the separate continuation inputs, execution outcomes and limitations; consult the canonical register for their evidence bindings as results are retained. Implemented scripts, a queued workflow and generated PHP text are not by themselves proof of an executed image or PHP-client pass. Keep experiment inputs, commands, outputs and digests under the compatibility spike. A failed or unavailable command remains visible even when a later attempt succeeds. Design documents are E0 candidates until the required accountable review is recorded. Codex's source and consistency review is not a substitute for product, security, application or operating acceptance.

G00 remains open while any criterion lacks its mandatory input, experiment or reviewer. The current unresolved inputs and exact unblock actions are maintained in the delivery register; this packet supplies the concrete material for those decisions. No native operation was attempted by this P00 increment.

The Python tool candidate and full Laravel HTTP/quality/Chromium flow have passing execution evidence, including semantic negative cases and fresh dependency installation. Candidate image/build and contract-tool probes are now implemented, with their actual outcomes and any unresolved execution work maintained in the linked reports. Resolve concrete failures and retain the resulting evidence before treating an experiment as measured; no owner decision is required merely to run that already authorized engineering. Synthetic checks do not become implemented service or qualification evidence. Owner/decision acceptance and exact platform/application/lab inputs remain separately recorded as BL-P00-001 and BL-P00-002. Use the DC/IP packet to close those specific inputs when they are supplied.


## Decision and feasibility continuation

The [engineering selections](p00-engineering-selections.md) now record concrete DC01–DC10 implementation choices. The [G00 assessment](../qualification/gate-reviews/g00-engineering-assessment-2026-10-04.md) examines actual evidence criterion by criterion, and the [input record](../qualification/feasibility/input-record.md) identifies missing fields mechanically. The [restore fixture report](p00-restore-fixture-results.md) records actual stateful experiment outcomes separately from design and native claims.

G00.04 requires bounded E1/E2 feasibility and candidate/fixture review. Full E3 native migration qualification remains later; absence of native credentials must not be used to block independent isolated engineering. Remaining full-application and candidate-profile gaps stay explicit, as do actual owner/operating decisions. The canonical gate record can be in engineering review while accountable acceptance is still incomplete.
