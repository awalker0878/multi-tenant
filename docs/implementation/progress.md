# Delivery progress

Generated from [delivery-register.yaml](delivery-register.yaml). Edit the register and run `python scripts/render_delivery_views.py` from the repository root. Do not edit this view independently.

Status meanings and review rules are in [status-model.md](status-model.md). Empty evidence fields mean no reviewed evidence has been registered; document existence is not implementation.

Baseline: 2026-10-04. Branch: `greenfield/enterprise-microservices-plan`.

## Phases

| Phase | Outcome | Work | Verification | Native qualification | Operating acceptance | Gate | Evidence / blockers |
| --- | --- | --- | --- | --- | --- | --- | --- |
| P00 | Product and architecture baseline | IN_PROGRESS | IN_PROGRESS | NOT_STARTED | NOT_STARTED | G00: IN_REVIEW | 10 / 2 |
| P01 | Delivery and runtime foundation | NOT_STARTED | NOT_RUN | NOT_STARTED | NOT_STARTED | G01: NOT_REVIEWED | 0 / 0 |
| P02 | Identity, tenancy and governance | NOT_STARTED | NOT_RUN | NOT_STARTED | NOT_STARTED | G02: NOT_REVIEWED | 0 / 0 |
| P03 | Application catalogue and workspace | NOT_STARTED | NOT_RUN | NOT_STARTED | NOT_STARTED | G03: NOT_REVIEWED | 0 / 0 |
| P04 | Site commissioning and inventory | NOT_STARTED | NOT_RUN | NOT_STARTED | NOT_STARTED | G04: NOT_REVIEWED | 0 / 0 |
| P05 | Capabilities and immutable plans | NOT_STARTED | NOT_RUN | NOT_STARTED | NOT_STARTED | G05: NOT_REVIEWED | 0 / 0 |
| P06 | Durable execution in simulation | NOT_STARTED | NOT_RUN | NOT_STARTED | NOT_STARTED | G06: NOT_REVIEWED | 0 / 0 |
| P07 | Native OpenStack provisioning | NOT_STARTED | NOT_RUN | NOT_STARTED | NOT_STARTED | G07: NOT_REVIEWED | 0 / 0 |
| P08 | VMware-to-OpenStack migration | NOT_STARTED | NOT_RUN | NOT_STARTED | NOT_STARTED | G08: NOT_REVIEWED | 0 / 0 |
| P09 | Platform and capability expansion | NOT_STARTED | NOT_RUN | NOT_STARTED | NOT_STARTED | G09: NOT_REVIEWED | 0 / 0 |
| P10 | Enterprise operating qualification | NOT_STARTED | NOT_RUN | NOT_STARTED | NOT_STARTED | G10: NOT_REVIEWED | 0 / 0 |
| P11 | Pilot and supported release | NOT_STARTED | NOT_RUN | NOT_STARTED | NOT_STARTED | G11: NOT_REVIEWED | 0 / 0 |

## Packages

Package state is independent of phase roll-up. Detailed work appears in the [phase documents](phases/README.md); review each specification against current decisions and evidence before implementation.

| Package | Output | Owner role | Work | Verification | Native qualification | Operating acceptance | Evidence / blockers |
| --- | --- | --- | --- | --- | --- | --- | --- |
| P00.01 | Scope and journeys | Product | IN_PROGRESS | NOT_RUN | NOT_STARTED | NOT_STARTED | 1 / 1 |
| P00.02 | Domain and ownership | Architecture | IN_PROGRESS | NOT_RUN | NOT_STARTED | NOT_STARTED | 1 / 1 |
| P00.03 | Technical decisions | Engineering/SRE | IN_PROGRESS | IN_PROGRESS | NOT_STARTED | NOT_STARTED | 8 / 1 |
| P00.04 | Qualification design | Quality/platform owners | IN_PROGRESS | IN_PROGRESS | NOT_STARTED | NOT_STARTED | 3 / 1 |
| P00.05 | Operating requirements | SRE/security | IN_PROGRESS | NOT_RUN | NOT_STARTED | NOT_STARTED | 1 / 1 |
| P00.06 | Delivery decomposition | Leads | IN_PROGRESS | IN_PROGRESS | NOT_STARTED | NOT_STARTED | 2 / 1 |
| P01.01 | Repository scaffolding | Engineering | NOT_STARTED | NOT_RUN | NOT_STARTED | NOT_STARTED | 0 / 0 |
| P01.02 | Local and integration runtime | SRE | NOT_STARTED | NOT_RUN | NOT_STARTED | NOT_STARTED | 0 / 0 |
| P01.03 | Contracts and messaging | Architecture | NOT_STARTED | NOT_RUN | NOT_STARTED | NOT_STARTED | 0 / 0 |
| P01.04 | CI and supply chain | SRE | NOT_STARTED | NOT_RUN | NOT_STARTED | NOT_STARTED | 0 / 0 |
| P01.05 | Runtime dependencies | SRE | NOT_STARTED | NOT_RUN | NOT_STARTED | NOT_STARTED | 0 / 0 |
| P01.06 | Baseline operations | SRE/security | NOT_STARTED | NOT_RUN | NOT_STARTED | NOT_STARTED | 0 / 0 |
| P02.01 | Authentication | Product/IAM | NOT_STARTED | NOT_RUN | NOT_STARTED | NOT_STARTED | 0 / 0 |
| P02.02 | Tenancy | Governance | NOT_STARTED | NOT_RUN | NOT_STARTED | NOT_STARTED | 0 / 0 |
| P02.03 | Authorization | Governance/security | NOT_STARTED | NOT_RUN | NOT_STARTED | NOT_STARTED | 0 / 0 |
| P02.04 | Approval lifecycle | Governance | NOT_STARTED | NOT_RUN | NOT_STARTED | NOT_STARTED | 0 / 0 |
| P02.05 | Console foundation | Console | NOT_STARTED | NOT_RUN | NOT_STARTED | NOT_STARTED | 0 / 0 |
| P03.01 | Core aggregates | Catalogue | NOT_STARTED | NOT_RUN | NOT_STARTED | NOT_STARTED | 0 / 0 |
| P03.02 | Intent semantics | Catalogue | NOT_STARTED | NOT_RUN | NOT_STARTED | NOT_STARTED | 0 / 0 |
| P03.03 | Revision behavior | Catalogue | NOT_STARTED | NOT_RUN | NOT_STARTED | NOT_STARTED | 0 / 0 |
| P03.04 | Product workflows | Console/catalogue | NOT_STARTED | NOT_RUN | NOT_STARTED | NOT_STARTED | 0 / 0 |
| P03.05 | Domain verification | Quality | NOT_STARTED | NOT_RUN | NOT_STARTED | NOT_STARTED | 0 / 0 |
| P04.01 | Site enrollment | Inventory/SRE | NOT_STARTED | NOT_RUN | NOT_STARTED | NOT_STARTED | 0 / 0 |
| P04.02 | Collectors | Inventory | NOT_STARTED | NOT_RUN | NOT_STARTED | NOT_STARTED | 0 / 0 |
| P04.03 | Observation store | Inventory | NOT_STARTED | NOT_RUN | NOT_STARTED | NOT_STARTED | 0 / 0 |
| P04.04 | Discovery controls | Infrastructure | NOT_STARTED | NOT_RUN | NOT_STARTED | NOT_STARTED | 0 / 0 |
| P04.05 | Inventory experience | Console | NOT_STARTED | NOT_RUN | NOT_STARTED | NOT_STARTED | 0 / 0 |
| P05.01 | Capability registry | Planning | NOT_STARTED | NOT_RUN | NOT_STARTED | NOT_STARTED | 0 / 0 |
| P05.02 | Policy and assessment | Planning | NOT_STARTED | NOT_RUN | NOT_STARTED | NOT_STARTED | 0 / 0 |
| P05.03 | Capacity and reservations | Planning/lifecycle | NOT_STARTED | NOT_RUN | NOT_STARTED | NOT_STARTED | 0 / 0 |
| P05.04 | Plan compilation | Planning | NOT_STARTED | NOT_RUN | NOT_STARTED | NOT_STARTED | 0 / 0 |
| P05.05 | Review experience | Console | NOT_STARTED | NOT_RUN | NOT_STARTED | NOT_STARTED | 0 / 0 |
| P05.06 | Admission contract | Planning/governance/lifecycle | NOT_STARTED | NOT_RUN | NOT_STARTED | NOT_STARTED | 0 / 0 |
| P06.01 | Admission and dispatch | Lifecycle | NOT_STARTED | NOT_RUN | NOT_STARTED | NOT_STARTED | 0 / 0 |
| P06.02 | Workflow state | Lifecycle | NOT_STARTED | NOT_RUN | NOT_STARTED | NOT_STARTED | 0 / 0 |
| P06.03 | Execution authority | Lifecycle/workers | NOT_STARTED | NOT_RUN | NOT_STARTED | NOT_STARTED | 0 / 0 |
| P06.04 | Evidence custody | Assurance | NOT_STARTED | NOT_RUN | NOT_STARTED | NOT_STARTED | 0 / 0 |
| P06.05 | Simulation and fault injection | Quality | NOT_STARTED | NOT_RUN | NOT_STARTED | NOT_STARTED | 0 / 0 |
| P06.06 | Jobs experience | Console | NOT_STARTED | NOT_RUN | NOT_STARTED | NOT_STARTED | 0 / 0 |
| P07.01 | Native site readiness | SRE/platform owners | NOT_STARTED | NOT_RUN | NOT_STARTED | NOT_STARTED | 0 / 0 |
| P07.02 | Infrastructure automation | Infrastructure | NOT_STARTED | NOT_RUN | NOT_STARTED | NOT_STARTED | 0 / 0 |
| P07.03 | Guest and service integration | Infrastructure/service owners | NOT_STARTED | NOT_RUN | NOT_STARTED | NOT_STARTED | 0 / 0 |
| P07.04 | Activation and verification | Lifecycle/quality | NOT_STARTED | NOT_RUN | NOT_STARTED | NOT_STARTED | 0 / 0 |
| P07.05 | Failure and retirement | Lifecycle | NOT_STARTED | NOT_RUN | NOT_STARTED | NOT_STARTED | 0 / 0 |
| P07.06 | Native support dossier | Assurance | NOT_STARTED | NOT_RUN | NOT_STARTED | NOT_STARTED | 0 / 0 |
| P08.01 | Source readiness | Inventory/lifecycle | NOT_STARTED | NOT_RUN | NOT_STARTED | NOT_STARTED | 0 / 0 |
| P08.02 | Method and data movement | Infrastructure | NOT_STARTED | NOT_RUN | NOT_STARTED | NOT_STARTED | 0 / 0 |
| P08.03 | Rehearsal | Lifecycle/application owner | NOT_STARTED | NOT_RUN | NOT_STARTED | NOT_STARTED | 0 / 0 |
| P08.04 | Cutover | Lifecycle/governance | NOT_STARTED | NOT_RUN | NOT_STARTED | NOT_STARTED | 0 / 0 |
| P08.05 | Recovery decisions | Infrastructure/application owner | NOT_STARTED | NOT_RUN | NOT_STARTED | NOT_STARTED | 0 / 0 |
| P08.06 | Acceptance | Quality/assurance | NOT_STARTED | NOT_RUN | NOT_STARTED | NOT_STARTED | 0 / 0 |
| P09.01 | Platform tranches | Infrastructure | NOT_STARTED | NOT_RUN | NOT_STARTED | NOT_STARTED | 0 / 0 |
| P09.02 | Migration matrix | Infrastructure/quality | NOT_STARTED | NOT_RUN | NOT_STARTED | NOT_STARTED | 0 / 0 |
| P09.03 | Brownfield adoption | Inventory/lifecycle | NOT_STARTED | NOT_RUN | NOT_STARTED | NOT_STARTED | 0 / 0 |
| P09.04 | Enterprise capabilities | Planning/workers | NOT_STARTED | NOT_RUN | NOT_STARTED | NOT_STARTED | 0 / 0 |
| P09.05 | Extension contract | Architecture | NOT_STARTED | NOT_RUN | NOT_STARTED | NOT_STARTED | 0 / 0 |
| P10.01 | Resilience and performance | SRE/quality | NOT_STARTED | NOT_RUN | NOT_STARTED | NOT_STARTED | 0 / 0 |
| P10.02 | Recovery and upgrades | SRE | NOT_STARTED | NOT_RUN | NOT_STARTED | NOT_STARTED | 0 / 0 |
| P10.03 | Security assurance | Security | NOT_STARTED | NOT_RUN | NOT_STARTED | NOT_STARTED | 0 / 0 |
| P10.04 | Operations | SRE/service owner | NOT_STARTED | NOT_RUN | NOT_STARTED | NOT_STARTED | 0 / 0 |
| P10.05 | Installation qualification | SRE/quality | NOT_STARTED | NOT_RUN | NOT_STARTED | NOT_STARTED | 0 / 0 |
| P10.06 | Release dossier | Quality/product | NOT_STARTED | NOT_RUN | NOT_STARTED | NOT_STARTED | 0 / 0 |
| P11.01 | Production commissioning | SRE/service owners | NOT_STARTED | NOT_RUN | NOT_STARTED | NOT_STARTED | 0 / 0 |
| P11.02 | Controlled pilot | Product/operators | NOT_STARTED | NOT_RUN | NOT_STARTED | NOT_STARTED | 0 / 0 |
| P11.03 | Acceptance | Application/security/service owners | NOT_STARTED | NOT_RUN | NOT_STARTED | NOT_STARTED | 0 / 0 |
| P11.04 | Release publication | Engineering/SRE | NOT_STARTED | NOT_RUN | NOT_STARTED | NOT_STARTED | 0 / 0 |
| P11.05 | Historical disposition | Product/records owner | NOT_STARTED | NOT_RUN | NOT_STARTED | NOT_STARTED | 0 / 0 |

## Registered evidence and blockers

Evidence records: **10**. Blocker records: **2**. Planning inputs awaiting selection are described in the phase cards; an empty blocker register does not mean those inputs are already available.

| ID | Level | Environment | Revision | Limitations |
| --- | --- | --- | --- | --- |
| EV-P00-001 | E1 | Local Linux x86-64; Node 24.19.0; npm 11.9.0 | 9a214f6ea2f0bba02abb7959cbd2f3523efbba1c | Isolated compatibility evidence only; no product service, full HTTP/browser integration, production image, native qualification or operating acceptance. Historical fixed-input observation has no time expiry; changed inputs require a new run. Failed earlier attempts remain in the spike results. |
| EV-P00-002 | E1 | Local Linux x86-64; Python 3.12.14; uv 0.12.19 | 9a214f6ea2f0bba02abb7959cbd2f3523efbba1c | Isolated compatibility evidence only; no product service, full HTTP/browser integration, production image, native qualification or operating acceptance. Historical fixed-input observation has no time expiry; changed inputs require a new run. Failed earlier attempts remain in the spike results. |
| EV-P00-003 | E1 | GitHub-hosted ubuntu-24.04 x64; PHP 8.5.11; Composer 2.10.3 | 06df7bfb15d83eb5a180e10c0d6c65970c5b0a54 | Isolated compatibility evidence only; no product service, full HTTP/browser integration, production image, native qualification or operating acceptance. Historical fixed-input observation has no time expiry; changed inputs require a new run. Failed earlier attempts remain in the spike results. |
| EV-P00-004 | E1 | Local Linux x86-64; Python 3.12.14; uv 0.12.19; new isolated temporary environment | aa452ec53909cb2c059e8cf2d0e2e7ddbae24055 | Synthetic non-product compatibility evidence; no actual service source analyzed, production image, native qualification or operating acceptance. External-library prohibition covers HTTPX and Pydantic in these fixtures, not every future SDK. Advisory observation is time-specific. Historical fixed-input observation has no time expiry; changed inputs require new execution. |
| EV-P00-005 | E1 | GitHub-hosted Ubuntu 24.04 x64; PHP 8.5.11; Composer 2.10.3; Node 24.19.0; npm 11.17.0; Playwright 1.63.0; Chromium 153.0.8010.12 | fb03c98478ba0d533d330174f34dc50227de8a18 | Isolated synthetic Laravel/SQLite and Chromium evidence. No product service or public contract, PostgreSQL concurrency, real SSO, cross-service runtime integration, managed-browser/accessibility matrix, production image/mirror, native qualification or operating acceptance. Negative controls cover the declared fixture rules. Historical fixed-input observation has no time expiry; changed inputs require a new run. Advisory lookups are time-specific. Earlier failed attempts remain retained. |
| EV-P00-006 | E1 | GitHub-hosted Ubuntu 24.04 x64; Docker 28.0.4 / Buildx 0.37.1; Debian Bookworm linux/amd64; PHP 8.5.11; Python 3.12.14; Node 24.19.0; Composer 2.10.3; uv 0.12.19 | d988cfe5d09e32a22da93c9c1b4816878fe4c495 | Candidate fixture evidence only; no product service, native platform, actual PostgreSQL server, production FPM/ingress, mirror/offline installation, operating acceptance, signed/published image, full SBOM or OS vulnerability qualification. Package inventories match across runs; derived config digests differ, so no byte-identical image claim. Inherited PHP development headers remain recorded. Fixed-input observations have no time expiry; changed inputs need new execution. |
| EV-P00-007 | E1 | GitHub-hosted Ubuntu 24.04 x64; PHP 8.5.11; Python 3.12.14; Node 24.19.0 / npm 11.17.0; uv 0.12.19; Temurin 17.0.20.1+1; OpenAPI Generator 7.25.0 | 9843a0ab62452f8edcb0f5e19f25eb692ba3d723 | Synthetic OpenAPI 3.0.4 subset and JSON Schema 2020-12 event envelope only; no product or AsyncAPI channel/broker/outbox/inbox implementation, live HTTP, authorization, canonical digest vectors, compatibility window or operating acceptance. Generated decoders have observed gaps and require wire-schema validation before domain translation. PHP HTTP transport is not tested. Fixed-input observations have no time expiry; changed inputs require new execution. |
| EV-P00-008 | E2 | GitHub-hosted Ubuntu 24.04 x64; Docker 28.0.4; PostgreSQL 18.6 Debian Bookworm linux/amd64; source, target and recovery databases on one isolated container; attachment files on disposable runner | fcb9fe0ea9bde275b09dfc8c0547e89021edafc9 | Synthetic real-dependency E2 evidence, not native qualification or full Permit Desk deployment. No VMware/OpenStack endpoint, independent native fence, real identity/service/network integration or operating acceptance. Fixture gates do not fence administrator access. Target-forward recovery requires readable target and new complete capture; uncaptured target loss and concurrent database/file crash consistency are not proved. Fixed-input observation has no time expiry; changed inputs require affected re-execution. |
| EV-P00-009 | E1 | Local Linux x86-64; Python 3.12.14; standard library; no network or native API | bc42d17a31aca91ea8736dee3a73f1124bb59eed | Validates declared input structure and completeness only. Does not authenticate observers/reviewers, retrieve or verify evidence content, establish installed facts, check current native permission, authorize an action or pass G00. Synthetic test identities remain only in tests. Full route completeness is not a prerequisite for unrelated isolated engineering. Fixed-input observation has no time expiry; changed record or validator requires revalidation. |
| EV-P00-010 | E0 | Repository engineering examination by Codex on 2026-10-04; initial baseline eb78e463e66d154e58fcfce7e65fad1eaab38914 plus explicitly identified restore/input source revisions | eb78e463e66d154e58fcfce7e65fad1eaab38914 | Reviewed design/evidence assessment only; no named organizational owner approval, accepted service target, installed tuple, staffing commitment, native qualification or operational acceptance. Earlier seven artifacts retain their original source/environment limits. Later decisions require attributable reviewer/evidence records; this examination starts IN_REVIEW and does not pass G00. No fixed historical expiry; material changes require scoped re-examination. |
| ID | Scope | Owner | State | Unblock condition | Next action |
| --- | --- | --- | --- | --- | --- |
| BL-P00-001 | P00, P00.01, P00.02, P00.03, P00.05, P00.06, R01, R06, R32, R34, R36, G00 | Requesting user — accountable G00 reviewer; remaining product/architecture/SRE/security and records owner assignments not supplied | OPEN | Record remaining subject-owner assignments and the G00 reviewer's acceptance or revision of the scope/domain/runtime/operating recommendations, retained-state disposition and assigned later checkpoints. | Review docs/implementation/p00-engineering-selections.md and the criterion-level G00 assessment; record attributable scope/domain/operating/retention decisions and actual owner/capacity inputs in the existing RT/IP record. One decision record may cover multiple fields. |
| BL-P00-002 | P00, P00.04, R01, G00 | Platform, application and qualification owners; named assignments not supplied | OPEN | Supply and review the candidate/application profile, complete reproducible fixture and application recovery bounds; execute the uncovered bounded G00.04 checks. Before any native calls/effects, additionally supply verified installation/resource facts and current permitted campaign scope through the approved access mechanism. | Use docs/qualification/feasibility/input-record.md and the G00 engineering assessment to distinguish supplied fixture evidence, untested full-application behavior and native-only inputs. Extend the fixture only against the reviewed representative application; preserve the passing state-recovery evidence at its true scope. |
