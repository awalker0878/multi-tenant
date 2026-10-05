# Next work — P01 delivery and runtime foundation

Active branch: `greenfield/enterprise-microservices-plan`. The requesting user approved advancement from G00 on 2026-10-04. The [accountable decision](docs/qualification/gate-reviews/g00-user-decision-2026-10-04.md) accepts the product, architecture and development baseline and explicitly carries remaining work to its receiving checkpoints. **P01 is the active phase; G01 is the next exit gate.** The [delivery register](docs/implementation/delivery-register.yaml) owns state; [progress](docs/implementation/progress.md) and [traceability](docs/implementation/traceability.md) are generated views.

## Current handoff

**The image-security blocker BL-P01-002 is resolved for the development candidate
set.** All nine pinned Alpine replacements pass exact-image admission at source
`b7705eef994c50863d87b4d8f9ff272f9397ca37`. No finding was waived and no severity or scanner
exclusion was relaxed. The [candidate manifest](release/p01-candidate-set.json)
now records zero held components and `REQUIRES_INDEPENDENT_QUALIFICATION`;
`promotion_authorized` remains false. [EV-P01-024 and the remediation record](docs/implementation/p01-image-remediation.md)
retain the original failures, complete APK correction and passing results.

- **Artifact trust:** all nine isolated builds pass, with 18 CycloneDX image/source
  SBOMs, nine verified development signatures, 63 expected denials and nine
  unchanged-byte development transfers. Retrieval verified 206 build logs and
  231 unique source bindings.
- **Runtime and resources:** EV-P01-025/026 retain 179 Compose and 196 Kubernetes
  checks on the replacements. Existing isolation, encrypted shared state,
  restart and failed-deployment recovery pass. Each environment now records 30
  cgroup-v2 resource samples across all 15 containers before/after recovery,
  including effective limits and zero observed OOM kills. Compose's observed
  limits are unlimited; production budgets remain an OP01 decision. See
  [the resource record](docs/implementation/p01-resource-observation.md).
- **Affected requalification:** EV-P01-027 retains 35 real messaging checks,
  16 event fixtures, 28 HTTP fixtures, 40 stateful-dependency checks, 79 Permit
  Desk recovery checks and 59 policy-control tests. All pass. The repository
  secret scan reports zero findings across 9,806 tracked files. All principal
  application/worker package checks also pass at the same source.
- **Evidence scope:** synthetic alert receipts, selected retained-object recovery
  and the complete Permit Desk fixture retain their separate measured boundaries.
  No native effects, full-store recovery, accepted RTO/RPO or operating acceptance
  is inferred. Historical failures remain available and are not relabeled.

**Next concrete actions:**

1. Activate repository admission (BL-P01-001): obtain verified reviewer GitHub
   IDs/logins and the authorized administration/independent reporting path, then
   install the trusted default-branch hook, role-based CODEOWNERS and required
   exact-PR checks. The [fresh settings observation](verification/p01/admission/remediation-settings-observation.json)
   still shows `protected: false` and no rulesets. The implemented policy and
   prepared settings body are not active enforcement.
2. Complete actual [OP01–OP07 inputs](release/operating-inputs.json): runtime/BOM
   and resource/network budgets; registries/signer/trust; secret/PKI/evidence/key
   custody; reviewer assignments; real alert route/response owner; recovery and
   retained inventory; support/accessibility ownership. The strict readiness
   command still returns HELD for all seven; development fixtures cannot supply
   these identities or decisions.
3. Continue P01.06 with correlated application logs/traces/metrics and collection
   failure coverage against the selected operating route. Resource-cost sampling
   is now implemented and measured; actual receiving acknowledgement, custody
   and operational review remain outstanding.
4. Complete independent criterion-by-criterion receiving reviews using
   [the refreshed G01 assessment](docs/qualification/gate-reviews/g01-engineering-assessment-2026-10-05.md).
   Record an accountable decision before advancing the phase.

**P01 work and verification are IN_PROGRESS; G01 remains NOT_REVIEWED.** The
previous FAILED roll-up is cleared by retained remediation/requalification,
not by ignoring the mandatory image check. Keep the accepted G00 decision and
completed foundation campaigns; do not restart P00 or ask for G00 approval again.

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

Use the [engineering standards](docs/engineering/README.md) and [coverage map](docs/engineering/coverage.md) when refining P00/P01. P00.03 has measured framework/tool locks, candidate image builds and schema/client tooling. Production adoption, complete service dependencies, managed-browser requirements and the actual mirror/trust path still need operating decisions and evidence. P01 must implement the documented structure, ownership, static analysis, contract and runtime checks before feature expansion; the written standards are not a completed foundation.

Apply the [pragmatic Laravel convention](docs/decisions/adr-024-pragmatic-laravel-domain-convention.md) within the [owning microservice](docs/architecture/context-code-structure.md): capability-based `app/Domain/` and `app/Application/`, Eloquent model behavior, Actions with `handle()`, external adapters in `app/Infrastructure/`, and normal Laravel entrypoints. Capabilities do not automatically become microservices. P00.02 aligns [the context registry](architecture/context-map.yaml) with that accepted convention and settles the remaining service decisions. P00.03 has verified the candidate architecture tools against actual spike locks and intentional violations; P01 must map these rules to the complete registered product source. P01.01/P01.04 implement PHP/Python/frontend dependency checks and actual ownership/review protection. The current registry/fixture workflow has explicit analysis limits; a source-empty pass does not close those packages.

For every coherent change, identify requirement/package IDs and the owning service. Update its behavior/contract specification and any affected ADR; put future API/event schemas in the contract tree, operational procedures under `docs/operations/runbooks/`, and qualification definitions/evidence indexes under `docs/qualification/`. The [documentation guide](docs/documentation-guide.md) defines the complete placement and naming rules.

Record actual source/artifact revisions, environment, positive/negative/recovery results, evidence identity and reviewer in `delivery-register.yaml`. Add a blocker with owner and unblock condition when necessary. Regenerate the progress/traceability views and validate references. Update this file to name the next concrete task, without copying a second status table here.

Use small coherent commits and the established GitHub connector workflow. No historical passing test, approval, credential, native support claim or operational acceptance transfers from the old programme. Scaffolding and design examples cannot be described as completed product behavior.
