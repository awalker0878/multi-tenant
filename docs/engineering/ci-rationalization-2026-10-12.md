# GitHub Actions rationalization — 2026-10-12

Repository: `awalker0878/multi-tenant`; audited branch: `codex/capability-runtime-assurance-audit-fixes`.
Audit baseline commit: `9cfa6721376591b21d4ae3fa6f6381de496aa1d3`.

## Implementation and decision

33 original workflow definitions are reduced to three: `.github/workflows/ci.yml`,
`.github/workflows/qualification.yml`, and the separate trusted-base
`.github/workflows/p01-admission.yml`. The PR pipeline has one stable,
always-reported `CI / Required` job. Affected paths are compared against the
base/head; `scripts/p01/select_components.py` retains transitive consumer
selection. An unavailable diff runs all applicable lanes. Changed CI/shared
dependencies also run all lanes; skip is accepted only for an empty selection
or an unaffected lane. Pull requests cannot trigger deployments.

The manual qualification workflow retains PostgreSQL, real local/stateful/Kubernetes,
cross-service P02–P06, P07/P10 native, browser, image and source-bound artifact
campaigns behind explicit `workflow_dispatch` choices. These are engineering
qualification runs, not an authorization to provision production or claim
native-platform acceptance. Release/deployment secrets and permissions were
not introduced.

The trusted-base admission workflow is retained because its read-only
`pull_request_target` run evaluates *base* policy and never runs proposed
code with privileges. `release/review-policy.json` remains `UNCONFIGURED`;
this has **not** been activated or represented as an enforced merge gate.
Its candidate check-source binding now points to `CI / Required`, with a
successful SHA-bound receipt. Do not switch it to `ACTIVE` without verifying
required reviewer identities, credentials and repository settings.

## Every original workflow

| Original | Decision | Replacement / disposition | Rationale |
| --- | --- | --- | --- |
| `ahv-destination.yml` | Consolidate | qualification.yml (native/browser), ci.yml (Python/native) | Duplicate P08 component/browser campaign |
| `architecture-policy.yml` | Consolidate | ci.yml / architecture | Registry, fixtures and docs retained |
| `assurance-authority.yml` | Consolidate | ci.yml / authority | Preserves PostgreSQL role, trigger and transactional tests |
| `capability-assurance.yml` | Consolidate | ci.yml / python, contracts, native | Remove second Python matrix and redundant shadow runner |
| `contracts-artifacts.yml` | Redesign | qualification.yml / artifact-bindings, aggregate-bindings | Nine real image/wheel binding builds are explicit only |
| `contracts-integrity.yml` | Redesign | ci.yml / contracts, laravel-routes, native | Active source, schema, producer/consumer, route checks |
| `p00-image-compatibility.yml` | Remove | Historical P00 experiment; modern image qualification on demand | Retired disposable image spike |
| `p00-php-compatibility.yml` | Remove | Current service package and browser checks in CI/qualification | Retired compatibility experiment |
| `p00-restore-feasibility.yml` | Remove | qualification.yml / infrastructure | Old candidate restore experiment |
| `p01-admission-probe.yml` | Remove | Trusted-base p01-admission.yml; manual probe tool retained | Extra post-push observation was not an enforcement gate |
| `p01-admission.yml` | Retain | p01-admission.yml / admission | Unique base-checked read-only privileged review boundary |
| `p01-contracts.yml` | Consolidate | ci.yml / contracts; qualification.yml / integration | Original foundation fixtures superseded by canonical validation |
| `p01-dependency-inputs.yml` | Remove | Explicit resolver scripts remain operator-invoked | Input observations need not auto-run on each push |
| `p01-foundations.yml` | Consolidate | ci.yml / python, php, required | Transitive per-owner selection and tests, one final required check |
| `p01-image-remediation.yml` | Remove | Manual artifact campaign and locked tool verification | Unconsumed observation output |
| `p01-images.yml` | Redesign | qualification.yml / images | Nine matrix builds no longer automatic on a PR |
| `p01-kubernetes-integration.yml` | Consolidate | qualification.yml / infrastructure | Kind/Cilium campaign only by explicit dispatch |
| `p01-local-integration.yml` | Consolidate | qualification.yml / infrastructure | Compose installation only by explicit dispatch |
| `p01-messaging.yml` | Consolidate | ci.yml / contracts; qualification.yml / integration | No separate P01 conformance workflow |
| `p01-permit-desk-recovery.yml` | Consolidate | qualification.yml / infrastructure | Stateful recovery is a bounded manual campaign |
| `p01-policy-controls.yml` | Consolidate | ci.yml / security | Pinned cosign/trivy, secret scan and crypto negative controls |
| `p01-stateful-inputs.yml` | Remove | Manual stateful dependency resolver | Retired automatic input-observation workflow |
| `p01-stateful-integration.yml` | Consolidate | qualification.yml / infrastructure | Real stateful campaign explicitly requested |
| `p02-governance-events.yml` | Consolidate | qualification.yml / p02-events-governance-events | Same event verification commands |
| `p02-identity.yml` | Consolidate | qualification.yml / p02-identity-identity | Same identity/console integration commands |
| `p03-catalogue.yml` | Consolidate | ci.yml / PHP/contracts; qualification.yml / p03-* | Same catalogue PostgreSQL and live drivers |
| `p04-inventory.yml` | Consolidate | ci.yml / Python/contracts; qualification.yml / p04-* | Same inventory source and live tests |
| `p05-planning.yml` | Consolidate | ci.yml / Python/contracts/native; qualification.yml / p05-* | Same planning PostgreSQL and live verification |
| `p06-execution.yml` | Consolidate | ci.yml / Python/contracts; qualification.yml / p06-* | Same execution/journal and live scenario tests |
| `p07-native-readiness.yml` | Consolidate | qualification.yml / native | Provider/Temporal preparation and dispatch kept in explicit campaign |
| `p08-native-migration.yml` | Consolidate | ci.yml / native; qualification.yml / browser | Migration component and browser coverage consolidated |
| `p09-expansion.yml` | Consolidate | ci.yml / native; qualification.yml / native | Nine-direction synthetic expansion qual is not an independent workflow |
| `p10-operating-qualification.yml` | Consolidate | qualification.yml / native | Operating engineering qualification remains manual |

## Coverage and execution design

- **PR**: registry and docs, full locked quality for affected Python/Laravel
  components, active canonical contracts and consuming routes, bounded
  PostgreSQL authority transactions, source-bound synthetic native
  conformance and signing/secret controls. The final required job fails on
  failed, cancelled, missing or incorrectly skipped selected jobs.
- **Shared changes**: contracts, source dependency graph, architecture,
  workflow, release and CI inputs reselect dependent products. Unknown
  revision availability is fail-closed. Test fixtures in `tests/ci`
  exercise docs-only, shared-change, contracts and missing-result cases.
- **Manual**: source-pinned runtime image/wheel attestation and the costly
  full cross-service, browser, infrastructure and real dependency suites.
  Artifact transfer is reserved for evidence-consuming jobs or failed
  security reports; intermediate every-job uploads are eliminated.
- **Security**: preserve digest-verified cosign/Trivy and the base-only
  review boundary. Branch settings must independently enforce review
  and signed release policies; neither is supplied by CI YAML alone.

## Before / after comparison

| Metric | Before | After |
| --- | --- | --- |
| Workflow files | 33 (exact) | 3 (exact, subject to final tree verification) |
| Workflows activated by broad PR | Up to 22 including base-only admission | 2 including base-only admission |
| Jobs on broad PR | Approximately 69 if matrices fully selected (static estimate) | Approximately 20 including admission (static estimate) |
| Jobs on docs-only PR | Approximately 30 (old unfiltered jobs plus skipped-matrix aggregators) | 4 (scope, architecture, required, admission) |
| Duplicate validation jobs | Cross-workflow Python/package, browser, architecture, native and contract repetitions | Separate equivalents removed; affected jobs execute once per logical suite |
| Unnecessary triggers | Numerous redundant `push` + `pull_request` branches and observation pushes | CI on PR and `main` only; expensive qualification manual |
| Obsolete workflow-specific scripts | Outcome checker and old workflow-name source bindings | Outcome checker deleted, source bindings updated |
| Estimated runner-minutes per typical PR | Not responsibly measurable from mostly cancelled runs | Not measured until new workflows run; expect fewer launched jobs, not a guaranteed percentage |
| Required validation coverage | Distributed among old workflows and proposed checks | One aggregate check with source, contract, authority, security and component checks; manual qualification retained |

These are *configuration* metrics, not claims that new hosted runners have passed.
A job may still fail for existing product code or external dependencies. No
workflow-level assertion alone establishes executed native-platform evidence.

## Verification and settings blocker

Run `python3 -m unittest discover -s tests/ci -p 'test_*.py' -v` and
`python scripts/validate_docs.py`, and validate every YAML with
`actionlint`. On GitHub, inspect the first `CI / Required` run for a
docs-only PR, a product-specific PR, a shared contract change and a
failed/selected job. Then dispatch each expensive suite at a controlled
time. Do **not** repeatedly commit full-CI-triggering checkpoints.

The GitHub connection returned an **empty repository ruleset list**, but
`GET /branches/main/protection` returned HTTP 403
(`Resource not accessible by integration`). Therefore actual protection
cannot be certified. In Repository Settings → Branches / Rulesets, an
administrator must inspect and, if required, replace the five historical
checks (`Architecture registry and documentation`, `Foundation checks`,
`Foundation images`, `Foundation contracts`,
`Foundation policy controls`) with `CI / Required` from the official
GitHub Actions application (candidate app ID 15368), **without changing**
review, conversation, security or deployment protections. Verify the check
has succeeded before requiring its new name. The checked-in
`release/branch-protection.candidate.json` is only a proposed setting; it
does not modify GitHub protection.

All historical evidence reports remain evidence about their original
commit, not active source/compatibility CI. No branch merge or production
deployment is part of this cleanup.
