# Next work — P02 identity, tenancy and governance

Active branch: `greenfield/enterprise-microservices-plan`. The requesting user authorized P02 development on 2026-10-05 in [the entry record](docs/implementation/p02-development-entry.md). **P02 is active across identity, tenancy, authorization, approvals and console navigation. G01 receiving review remains open and G02 is not passed.** The [delivery register](docs/implementation/delivery-register.yaml) owns state; progress and traceability are generated views.

## P02 handoff

Console-managed [OIDC setup and tested handover](docs/implementation/p02-federation.md),
[tenant authority and plan-bound approvals](docs/implementation/p02-tenancy-and-approvals.md),
and tenant membership/quota administration are implemented. P02.01–P02.05 remain
IN_PROGRESS; receiving and the remaining integration scope are open.

The current retained increments are:

- **EV-P02-004 — Governance event delivery and background expiry.** Explicit
  schema/AsyncAPI contracts, bounded scheduler commands, routed confirmations,
  retry/quarantine and system-attributed expiry. The corrected PostgreSQL/TLS
  broker campaign passes 32 tests (719 assertions), including competing relays,
  process death after confirmation and duplicate delivery. Original timestamp
  precision and broker-readiness failures remain retained with their correction.
- **EV-P02-005 — Short-lived service actor delegation and Catalogue guard.**
  Opaque sixty-second handles bind exact audience/action/scope and current
  session/membership/grant/workload credentials. Logout, revocation/regrant,
  suspension and credential rotation deny reuse. The hosted identity campaign
  passes 80 PostgreSQL feature cases (1,427 assertions). Catalogue passes 50
  boundary/package cases (207 assertions); its owner route and Governance
  transport are explicit test fixtures, not deployed product integration.
- **EV-P02-006 — Expanded compiled Console journey.** The latest 47-check
  campaign at `512fd5c2580e5cd40bf0089662cff8d84718a877` passes two browser
  journeys with four HTTPS/PKCE exchanges, six artifact hashes and 248 source
  bindings. A controlled late tenant response cannot replace the newer page;
  drafts stay separate between tabs and sign-out clears same-session tabs.
  Protected back/forward-cache restores now reauthenticate; actual browser-cache
  interoperability and manual assistive-technology qualification remain open.

EV-P02-001–003 retain the bootstrap, federation and tenancy/approval baselines.
The [correction record](verification/p02/corrections.md) preserves historical
failures without changing their outcomes. The published v1 contracts retain their
original bytes; new behavior uses new contracts. No validation rule was weakened.
The [regression snapshot](verification/p02/governance-delegation-regression-runs.json)
records workflow source identities and actual outcomes, including any pending
runs; the P02 campaign is separate from foundation runtime qualification.

Implementation and limits are in [event delivery](docs/implementation/p02-governance-events.md),
[service delegation](docs/implementation/p02-service-delegation.md) and
[tenant/browser behavior](docs/implementation/p02-tenancy-and-approvals.md).

**EV-P02-007 — Identity notifications and browser-engine campaign.** The distinct
[identity relay](docs/implementation/p02-identity-events.md) is implemented with
versioned contracts, additive migration, restricted routing, retry/quarantine and
unchanged-wire replay. Local E1 verification passes 141 Governance cases (1,714
assertions), static/dependency/format checks, Console types and three-engine test
discovery; six real-broker cases are explicitly skipped locally. Nine logs and
158 source bindings match `7b24476c71a778dcf9a865b04c13aa35aa8b3992`.

**EV-P02-008/009 — Hosted identity delivery and Firefox.** The event campaign at
`1d45f11` passes 60 PostgreSQL/TLS broker cases (854 assertions), five checks,
153 source bindings and ten log hashes. Firefox at `7b24476` passes 50 checks,
105 PostgreSQL cases (1,542 assertions), two compiled journeys, four HTTPS/PKCE
exchanges, 259 source and six artifact hashes. Original ZIP bytes were verified
before retention; neither result supplies a product consumer or receiving decision.

**EV-P02-010–012 — Console consumer and relay replay.** The
[Console notification consumer](docs/implementation/p02-console-notifications.md)
now records durable receipts/quarantine, acknowledges after commit and offers an
owner-authorized refresh without replacing drafts. Local E1 passes 114 tests
(520 assertions), thirteen logs and 134 source bindings. Chromium at `283e6f4`
passes 58 checks, 105 Governance cases (1,542 assertions), 44 Console notification
cases (163 assertions), two journeys and six real owner-to-Console deliveries;
284 source and nine artifact hashes match. The older `7b24476` relay regression
passes on rerun: 60 cases, 854 assertions, five checks and ten logs. Historical
snapshots remain unchanged.

**EV-P01-032 — Corrected image/runtime replay.** The first Console image build
failed because AMQP requires `ext-sockets`. `b13996d` compiles and declares it;
no platform check or package version is relaxed. The corrected Compose campaign
`37371858448` passes 249 checks, all seven image builds, 612 log hashes and 451
unique source bindings. Its complete archive and the original failure are retained.
This is separate from package replay, image-security admission and Kubernetes.

**Immediate verification:** the remaining Firefox/WebKit jobs in consumer run
`37371273531` were cancelled. WebKit at `b13996d` (run `37371858388`) exposed a
quota-save test race; its original failure is retained. The concurrent
[`9716803` synchronization correction](docs/implementation/p02-browser-synchronization.md)
waits for the committed owner response before navigating. Retrieve all browser
results at that corrected source and affected foundation package/image/Kubernetes
campaigns. Retain exact source
and original-byte evidence for every result. Package/image/Compose/Kubernetes
workflows now use GitHub's bounded FIFO queue (`queue: max`, up to 100 pending)
so a later push does not replace an earlier pending check. Verify the fresh full
selection triggered by this workflow correction. The cancelled pre-job image run
`37371858446` could not be retried through the failed-jobs endpoint; its corrected
product source is included in the new full campaign. Documentation-only passes
cannot replace changed-source builds. The old `7b24476` Chromium rerun
is queued; GitHub rejects its WebKit retry while that workflow attempt is active.
Retry WebKit after it finishes. The
[notification workflow snapshot](verification/p02/console-notification-hosted-runs.json)
records those boundaries; the later Compose pass has its own retained receipt.

**Next concrete work:** finish notification restart/restore and browser-floor
qualification, explicit owner-scoped installation consumers, and Console pagination
for the currently bounded lists. Bind Catalogue's guard to owner resources
and qualify the Console-to-Catalogue-to-Governance wire path as P03 resources are
implemented under their entry conditions. Resolve the approved support-access/break-glass contract
and independent restore/revocation custody before those authority changes. Extend
the browser campaign to the supported browser floor and manual accessibility.
The real immutable plan producer belongs to P05.04; the native effect boundary
belongs to P06.03. P02 uses synthetic plans only in tests and production fails
closed without the owner. Follow the
[G02 engineering assessment](docs/qualification/gate-reviews/g02-engineering-assessment-2026-10-05.md)
for criterion gaps and accountable reviewers. Provider values remain
Console-managed application settings. No gate pass or promotion is inferred.

## Retained P01 handoff

**Correlated diagnostic telemetry is implemented and measured in both runtimes;
image-security blocker BL-P01-002 remains resolved.** All nine pinned Alpine
candidates pass exact-image admission at source
`36a14811b5afa23717566d5e8a08632e011f44a5`. No finding was waived and no severity or scanner
exclusion was relaxed. The [candidate manifest](release/p01-candidate-set.json)
now records zero held components and `REQUIRES_INDEPENDENT_QUALIFICATION`;
`promotion_authorized` remains false. [EV-P01-024 and the remediation record](docs/implementation/p01-image-remediation.md)
retain the original failures, complete APK correction and passing results.

- **Artifact trust:** all nine isolated builds pass, with 18 CycloneDX image/source
  SBOMs, nine verified development signatures, 63 expected denials and nine
  unchanged-byte development transfers. EV-P01-028 verifies 206 build logs and
  253 unique source bindings, plus all nine package passes with 346 command logs,
  388 artifact files and 412 unique source bindings.
- **Runtime, telemetry and resources:** EV-P01-029/030 retain 249 Compose and 266
  Kubernetes checks, including 70 telemetry checks each. Existing isolation,
  encrypted shared state, restart and failed-deployment recovery pass. Each
  environment retains 22 telemetry snapshots and three signal exports, including
  diagnostic correlation, public-reader denial, real buffer exhaustion, explicit
  loss, stale-acknowledgment preservation and collection recovery. Seven authorized
  diagnostic spans match the common caller trace; denial responses and concurrent
  readiness probes remain in the collected population. See
  [the telemetry record](docs/implementation/p01-telemetry.md). Each also records 30
  cgroup-v2 resource samples across all 15 containers before/after recovery,
  including effective limits and zero observed OOM kills. Compose's observed
  limits are unlimited; production budgets remain an OP01 decision. See
  [the resource record](docs/implementation/p01-resource-observation.md).
- **Affected requalification:** EV-P01-031 retains 28 HTTP fixtures, 79 Permit
  Desk recovery checks and 59 policy-control tests at the current source. All
  pass; the repository secret scan reports zero findings across 10,187 tracked
  files. EV-P01-027 retains 35 real messaging checks, 16 event fixtures and 40
  stateful-dependency checks at `b7705eef994c50863d87b4d8f9ff272f9397ca37`; those
  distinct campaign sources and measured boundaries remain unchanged.
- **Evidence scope:** synthetic alert receipts, selected retained-object recovery
  and the complete Permit Desk fixture retain their separate measured boundaries.
  No native effects, full-store recovery, accepted RTO/RPO or operating acceptance
  is inferred. Historical failures remain available and are not relabeled.

**Open foundation receiving conditions:**

1. Activate repository admission (BL-P01-001): obtain verified reviewer GitHub
   IDs/logins and the authorized administration/independent reporting path, then
   install the trusted default-branch hook, role-based CODEOWNERS and required
   exact-PR checks. The [fresh settings observation](verification/p01/admission/telemetry-settings-observation.json)
   still shows `protected: false` and no rulesets. The implemented policy and
   prepared settings body are not active enforcement.
2. Complete actual [OP01–OP07 inputs](release/operating-inputs.json): runtime/BOM
   and resource/network budgets; registries/signer/trust; secret/PKI/evidence/key
   custody; reviewer assignments; real alert route/response owner; recovery and
   retained inventory; support/accessibility ownership. The strict readiness
   command still returns HELD for all seven; development fixtures cannot supply
   these identities or decisions.
3. Integrate and qualify the measured diagnostics with the actual operating
   receiver once OP03/OP05 supply the route, access/custody owners, collection
   cadence and accepted loss/retention policy. Confirm real receiving
   acknowledgment and response ownership. Correlated application signals,
   collection-failure recovery and resource sampling are already implemented
   and measured in the disposable Compose/Kubernetes environments.
4. Complete independent criterion-by-criterion receiving reviews using
   [the refreshed G01 assessment](docs/qualification/gate-reviews/g01-engineering-assessment-2026-10-05.md).
   Record the accountable receiving decision; P02 development entry does not pass G01.

**P01 receiving work and verification remain IN_PROGRESS; G01 remains NOT_REVIEWED.** The
previous FAILED roll-up is cleared by retained remediation/requalification,
not by ignoring the mandatory image check. Keep the accepted G00 decision and
completed foundation campaigns; do not restart P00 or ask for G00 approval again.

## P02 identity baseline

[ADR-009](docs/decisions/adr-009-identity-delegation-and-authorization.md) defines
console-managed external OIDC and a deployment-created local administrator.
Initial deployment generates a random temporary password and displays it once
to the authorized installer. First login requires a different password before
any other protected function. The administrator configures and tests OIDC
through the console; verified federated administrator activation disables local
login and revokes its sessions. Provider values are application settings, not
deployment configuration. Retries, restarts and provider outages cannot recreate
the account or reopen local login after activation.

Implement through P02.01/P02.05 and qualify Q01.17–Q01.20 at G02. The identity
baseline is accepted design; P02.01/P02.05 implementation is IN_PROGRESS under
the user-authorized development entry. No G01 pass is inferred. Workload trust, custody and repository admission retain
their distinct receiving inputs.

## Carried inputs and checkpoint ownership

The user's reviewer identity, G00 approval, baseline decision scope, migration direction/method and later checkpoints are recorded with immutable provenance in the [input record](docs/qualification/feasibility/input-record.md). Do not request that baseline approval again. Remaining unknown integration and native fields describe actual inputs still needed, not a reason to stop independent foundation work.

- Review the completed representative Permit Desk fixture and bounded Compose application/configuration recovery in P01.02/P01.06 before G01. Retain EV-P01-013 and the two original P00 database/attachment recovery boundaries with their distinct measured scopes.
- Review EV-P01-014 against G01.02/G01.05/G01.06 using the [dependency recovery runbook](docs/operations/runbooks/stateful-dependency-recovery.md). Its single-node synthetic probes and one selected object version do not establish product integration, whole-store recovery, HA, retention authority or operational acceptance.
- Obtain actual runtime, registry/signer, trust, network and dependency facts before the affected P01 integration. Local development artifacts do not establish operated deployment or promotion controls.
- Obtain installed VMware/OpenStack facts and permitted discovery scope before G04 work, and exact campaign effects/authority before G07/G08 native tests. Native qualifications remain unrun.
- Retain application outage/data objectives before P08, operating/retained-state obligations at P10/P11, and staffing/dependency dates when supplied. Approval does not invent these facts.

The original P00 task axes continue to show any carried incomplete work; the accountable G00 advancement decision is recorded separately. No unperformed check becomes a pass. Whole-VM conversion stays a separate P09 option; the approved first migration direction uses `application_rebuild_restore`.

Historical `implementation/all-waves` source is pinned at `a2963d8d43e25f08d70fbd99b0e5e19ab5c9828e` for reference. Current documentation, stack and ADR-024 take precedence; no historical implementation, passing result or authority transfers.

## Document each implementation increment

Use the [engineering standards](docs/engineering/README.md) and [coverage map](docs/engineering/coverage.md) when refining P02 and the carried foundation work. P00.03 has measured framework/tool locks, candidate image builds and schema/client tooling. Production adoption, complete service dependencies, managed-browser requirements and the actual mirror/trust path still need operating decisions and evidence. P01 must implement the documented structure, ownership, static analysis, contract and runtime checks before feature expansion; the written standards are not a completed foundation.

Apply the [pragmatic Laravel convention](docs/decisions/adr-024-pragmatic-laravel-domain-convention.md) within the [owning microservice](docs/architecture/context-code-structure.md): capability-based `app/Domain/` and `app/Application/`, Eloquent model behavior, Actions with `handle()`, external adapters in `app/Infrastructure/`, and normal Laravel entrypoints. Capabilities do not automatically become microservices. P00.02 aligns [the context registry](architecture/context-map.yaml) with that accepted convention and settles the remaining service decisions. P00.03 has verified the candidate architecture tools against actual spike locks and intentional violations; P01 must map these rules to the complete registered product source. P01.01/P01.04 implement PHP/Python/frontend dependency checks and actual ownership/review protection. The current registry/fixture workflow has explicit analysis limits; a source-empty pass does not close those packages.

For every coherent change, identify requirement/package IDs and the owning service. Update its behavior/contract specification and any affected ADR; put future API/event schemas in the contract tree, operational procedures under `docs/operations/runbooks/`, and qualification definitions/evidence indexes under `docs/qualification/`. The [documentation guide](docs/documentation-guide.md) defines the complete placement and naming rules.

Record actual source/artifact revisions, environment, positive/negative/recovery results, evidence identity and reviewer in `delivery-register.yaml`. Add a blocker with owner and unblock condition when necessary. Regenerate the progress/traceability views and validate references. Update this file to name the next concrete task, without copying a second status table here.

Use small coherent commits and the established GitHub connector workflow. No historical passing test, approval, credential, native support claim or operational acceptance transfers from the old programme. Scaffolding and design examples cannot be described as completed product behavior.
