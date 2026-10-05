# Next work — P02 completion review

Active branch: `greenfield/enterprise-microservices-plan`. The requesting user
authorized continued P02 development through completion. The implementation
continuation is committed through `fe88107aac0aca028170fd5f39f06e0b0d30cb7f`;
original evidence is retained through `b2ccd21eb8dcba08a8b2338669e62ed2d6413230`.
The [delivery register](docs/implementation/delivery-register.yaml) owns status.
**P02 remains IN_PROGRESS and G02 NOT_REVIEWED** because the existing phase scope
still has the concrete owner-dependent obligations below. G01 receiving review
also remains open. Development authorization does not invent receiving approval.

## Completed continuation

- [Installation notifications](docs/implementation/p02-console-notifications.md):
  the durable Console inbox now handles the twelve identity routes as well as
  tenant changes. Current owner authorization precedes setup hints; bounded polling
  preserves drafts, and explicit refresh clears discarded secret input.
- [Identity recovery admission](docs/implementation/p02-identity-recovery.md):
  current external installation/epoch custody is required at new user/service
  admission. Missing, held or mismatched custody denies access; initialized or
  restored state cannot automatically rebind or revive bootstrap credentials.
- Complete application-table process restart/current restore, stale-bootstrap
  restore denial and a separate nonempty approval-history restore are now measured.
  Two terminal decisions and five decision audit events survive the latter restore.

## Retained verification

| Evidence | Result |
| --- | --- |
| EV-P02-016 | Directory baseline: all three engines pass 59 checks each; Firefox/WebKit are no longer queued. |
| EV-P02-017 | Final local E1: 155 Governance and 135 Console cases pass; all 12 commands, 24 distinct logs and 294 exact source bindings verified. Thirteen broker cases are explicitly skipped locally. |
| EV-P02-018 | Recovery/installation-consumer source: all three engines pass 98 checks each. |
| EV-P02-019 | Final source `fe88107`: Chromium, Firefox and WebKit each pass 100 checks, 119 Governance and 66 Console PostgreSQL/TLS cases, two browser journeys with no skips/retries/failures and nonempty approval-history restore. |

The [hosted receipt](verification/p02/completion-hosted-final.json) records successful completion of all nine workflows at `fe88107`, including
all nine independent packages, images, contracts, events, policy, Compose and
Kubernetes. Passing identity evidence includes original ZIP bytes, ten artifact hashes
and 302 exact source bindings per engine. Earlier evidence remains in
EV-P02-001–015; original failures remain in
[the corrections record](verification/p02/corrections.md). No failed run is
relabelled, contract freeze weakened or unexecuted manual task counted as passed.

## Remaining actions to complete P02

The [completion review packet](docs/implementation/p02-completion-review.md)
contains the exact proposal, input tables and manual task sheet. Use it directly:

1. **BL-P02-001 — IAM/security and Governance:** accept or amend the proposed
   exceptional-support action list, independent approver assignment, lifetime and
   audit/review custody; then implement and qualify that selected contract.
   Unknown/support actions remain denied. An exclusion requires explicit phase
   scope review; deny-by-default alone does not deliver the requested contract.
2. **BL-P02-002 — IAM/SRE and the independent custodian:** supply OP03/OP06 actual
   descriptor/key custody, supported identity topology, current revocation records
   and the authenticated lost-bootstrap/reconciled resumption procedure. The fence
   requires custody hold/rotation before restore and cannot detect co-restoration
   of an old active descriptor with its database.
3. **BL-P02-003 — Product/quality:** select OP07's exact managed browser/OS/policy
   and assistive combinations and support owner; execute the five manual tasks,
   including actual history-cache behavior, and resolve mandatory defects.
4. **BL-P02-004 — Actual independent reviewers:** examine all four criteria and
   record the G02 receiving outcome with names, dates and immutable evidence.

Follow the [G02 engineering assessment](docs/qualification/gate-reviews/g02-engineering-assessment-2026-10-05.md)
for the measured boundary. P03 owns real Catalogue resource/wire integration;
P05.04 owns the real immutable-plan producer; P06.03 owns immediate native-effect
rechecks. They retain their own checkpoints. Provider values remain Console-managed
application settings. No production OIDC registration is needed to continue P02
development, and no gate pass or promotion is inferred.

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
