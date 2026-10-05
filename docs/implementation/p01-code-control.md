# P01 code-control implementation record

Scope: P01.01 and P01.04; partial evidence for G01.01 and G01.04. Author/examiner: Codex. Examination date: 2026-10-04. The [code-control policy](../engineering/code-control.md) remains the required outcome. The mechanisms below supply executable source, build and CI checks. They do not establish enforced repository admission or artifact promotion.

## Implemented selection and stable check results

The [foundation candidate registry](../../scripts/p01/candidates.json) identifies seven principal applications and the two selected worker packages. [The selector](../../scripts/p01/select_components.py) computes changed paths using full commit IDs. Pushes compare before/after revisions; pull requests use the merge base and proposed head. Git reports deletions and both sides of renames because rename detection is disabled. Invalid absolute/traversal paths are rejected. A missing usable diff, branch creation or manual run selects every candidate.

| Change | Implemented build selection |
| --- | --- |
| One owning application/service path | That component; its private package quality and registered image |
| Inventory or Lifecycle service | Owning service plus its corresponding site-worker package/image |
| One worker path | That worker; no automatic selection of unrelated services |
| Public contracts, shared build scripts, image inputs, architecture declarations or workflow definitions | All registered components |
| An unregistered product root or shared-package path | All registered components; ownership still needs correction through the architecture check |
| Documentation-only paths | No package/image matrix; stable aggregate checks still report a result |

Image selection intersects affected component IDs with [the image registry](../../deploy/build/components.json). An unknown image component fails selection. Each build receives only copied inputs from the owning component root, rather than access to sibling source. The [build procedure](../../deploy/build/README.md) documents image pins, runtime constraints and the distinction between process probes and operating readiness. The first five Python image builds and isolation probes passed in [run 37238148501](https://github.com/awalker0878/multi-tenant/actions/runs/37238148501) at source `ba6acd71513c7d999cf51249d70d9c2be50967d9`; that execution does not establish a PHP image result or G01 acceptance.

| Workflow | Stable check name | Result rule |
| --- | --- | --- |
| [Context policy](../../.github/workflows/architecture-policy.yml) | `Architecture registry and documentation` | Registry, supported source checks, architecture/documentation tests and document/status validation must complete successfully |
| [Foundation packages](../../.github/workflows/p01-foundations.yml) | `Foundation checks` | Selection must succeed; every selected language matrix must succeed; a matrix may be skipped only when its selection is empty |
| [Foundation images](../../.github/workflows/p01-images.yml) | `Foundation images` | Selection must succeed; the selected image matrix must succeed; a skipped matrix is accepted only for an empty selection |
| [Foundation contracts](../../.github/workflows/p01-contracts.yml) | `Foundation contracts` | Existing base-version artifacts remain unchanged; locked generation, cross-language fixtures and compilation succeed |

The hosted check-runs response for source `7aced8f2cba673a500c060116eb431627f727aeb` confirmed the exact names `Foundation checks` and `Architecture registry and documentation`, both successful, reported by GitHub Actions (`app.id=15368`, slug `github-actions`). [Package run 37238841029](https://github.com/awalker0878/multi-tenant/actions/runs/37238841029) selected no package work and accepted the intentionally skipped Python/PHP matrices through the stable aggregate. This proves the documentation-only result path, not a fresh execution of the skipped package suites. The nine-image aggregate correctly failed run `37239193485` when Console failed. The Console-only correction in run `37239487917` passed its selected image and aggregate at source `d0a7cefb23352ffc112638178bb225d20bf12368`; see the [image evidence](p01-laravel-images.md).

Both foundation workflows run on every push to, and pull request targeting, the active branch. Their final jobs use `always()` and [the outcome validator](../../scripts/p01/check_jobs.py). Missing, failed, cancelled or incorrectly skipped selected work cannot produce an accepted aggregate result. Invalid selection output, unknown or duplicate component IDs and wrong-language selection are rejected. The aggregate relies on GitHub's matrix outcome and the reviewed matrix definition; it is not a separate proof against malicious workflow replacement.

The workflows use commit-pinned actions, ephemeral hosted runners, `contents: read` and checkout with credential persistence disabled. Build jobs do not publish images or obtain signing authority. The observed branch has not been configured to require these check names. A successful job currently supplies feedback and evidence; it does not prevent an ordinary direct update.

## Local verification and coverage limits

The following checks were executed during this examination against the local implementation:

| Command | Observed result |
| --- | --- |
| `python3 -m unittest discover -s scripts/p01 -p 'test_*.py' -q` | 17 tests passed: ten selection cases, four aggregate-result cases and three execution-recorder cases |
| `python3 -m unittest discover -s tests/documentation -p 'test_architecture_controls.py' -q` | 69 architecture-control tests passed |
| `python3 -m unittest discover -s tests/documentation -p 'test_*.py' -q` | 89 tests passed, including the same 69 architecture tests and 20 P00 input-record tests |

The recovered package archives exposed a classification error: their copied dependency
manifests were treated as live unregistered services. Commit `46dd6823504a7d6856588aa4c1c7b31306710e7c`
classifies only direct manifest snapshots at registered P01 package-run locations,
with matching report identity and source/artifact hashes. It continues to traverse
the evidence tree and reject runtime source, tampered or misplaced manifests,
symlinks and prohibited live dependencies. The local check observed 10 live
manifests, 20 evidence snapshots and 107 source files. This is evidence classification,
not a blanket source exclusion or proof of evidence authenticity.

The architecture tests exercise the repository's stated structural/Python-AST/PHP-precheck mechanisms; their count does not establish complete language analysis or runtime isolation. Service-owned PHP analyzers, Python quality, frontend checks and image executions have their own source-bound results. The recorded counts above must not be added as disjoint suites because the documentation total includes the architecture suite.

The [artifact/admission increment](p01-artifact-admission.md) now unions base/head ownership and implemented consumer edges, including removed edges. Unknown ownership selects broadly and denies admission. Trusted-base review and bounded exception predicates have executable negative fixtures. Published contract versions remain immutable under the [HTTP contract checks](p01-http-contracts.md). This implemented foundation graph does not infer unseen future public-contract, network, shared-package or native-effect dependencies; semantic changes still require affected-owner review.

The check implementation executes from the checked-out change. No trusted-base or separately governed enforcement workflow has yet been demonstrated. A change to the selector, analyzer or workflow therefore requires independent policy review; running the changed workflow cannot prove that its own weakening was authorized. There is no implemented account/role review-policy evaluator, latest-reviewed-revision validation, CODEOWNERS enforcement or signed artifact admission in this increment.

## Observed repository settings

Read-only GitHub connector retrievals started at `2026-10-04T22:09:59.756Z`. The table gives the locally recorded completion time for each retrieval. These observations describe the API responses available to this connected session at that time; they are not a continuing settings monitor.

| API source | Completed at (UTC) | Actual observation |
| --- | --- | --- |
| [Repository branch collection](https://api.github.com/repos/awalker0878/multi-tenant/branches?per_page=100) | `2026-10-04T22:10:00.125Z` | The `greenfield/enterprise-microservices-plan` entry reported `protected: false`; its head was `7aced8f2cba673a500c060116eb431627f727aeb` |
| [Repository rulesets](https://api.github.com/repos/awalker0878/multi-tenant/rulesets) | `2026-10-04T22:10:00.108Z` | The returned ruleset list was `[]` |
| [Repository metadata](https://api.github.com/repos/awalker0878/multi-tenant) | `2026-10-04T22:10:00.127Z` | `owner.type` was `User`; connector-reported permission flags `admin`, `maintain`, `push`, `triage` and `pull` were all `true` |

The connector exposed read-only settings retrieval and normal repository/PR operations, but no callable branch-protection or ruleset mutation operation in this session. This is a tool-capability limit, not evidence that the connected account lacks administrator rights: the permission response explicitly reported `admin: true`. No repository settings were changed, no administration credentials were requested and no substitute browser or undocumented mutation endpoint was used.

No `.github/CODEOWNERS` file or validated reviewer-account mapping has been implemented in this foundation. The requesting user's recorded G00 reviewer acceptance establishes that gate decision; it does not automatically assign every context, independent security, platform or operating review role. Existing role names in the architecture registry remain role declarations. No GitHub review identity has been invented to make ownership appear complete.

## Remaining administrative and engineering controls

Complete these P01.04 actions through an available repository administration path, with accountable role mapping and recorded verification:

1. Establish the intended integration/release branch rules and verify supported behavior for this user-owned repository. Require pull requests, current checks, resolved blocking findings and review of the latest change; block branch deletion, force pushes and ordinary direct updates. Record the effective configuration and any explicitly authorized bypass identities and scope.
2. Bind the stable `Architecture registry and documentation`, `Foundation checks` and `Foundation images` results to the approved reporting application where supported. Demonstrate that a missing, failed, stale, cancelled or incorrectly skipped required result blocks admission. Verify actual check names from hosted check runs rather than relying only on workflow labels.
3. Map context, consumer, architecture, security and platform roles to actual authorized GitHub accounts. Implement CODEOWNERS for product roots, contracts, registries, migrations, dependency locks, workflows, policy code and CODEOWNERS itself. Verify account access and last-match precedence using representative changed paths.
4. Enforce the distinct-role review requirements in the policy. Listing multiple owners alone does not require every listed owner to approve. Select a mechanism supported by this repository, or retain explicit manual admission until an exact-revision review-policy check is implemented and proven. Record the actual reviewing identities and separation from the author where required.
5. Protect admission controls from self-modification: execute the trusted enforcement definition from an approved base or separately governed workflow, test proposed rule/exclusion changes with negative fixtures and require independent policy review before adoption. Keep untrusted source and artifacts outside privileged signing/promotion jobs.
6. Complete base/head dependency and contract-consumer impact analysis, exclusion/exception controls, secret/dependency/image checking, SBOMs, signed immutable artifacts and release-manifest verification. Demonstrate rejection of unsigned, altered or mismatched artifacts before claiming G01.04 promotion control.

Record the effective settings, source revisions and successful denial tests in the G01 evidence register after they are actually observed. Until then, P01.04 remains in progress and this record makes no enforced-merge, protected-branch, trusted-release or complete source-analysis claim.

## Follow-up settings observation — 2026-10-05

After source `72188a2dcf973ceee09eed05dfb79a6c53122ae2`, the connector's branch
collection still reported `protected: false` and its ruleset collection still
returned `[]`. Hosted run `37260680627` confirmed successful check name
`Foundation contracts`; EV-P01-017 retains its generation and base/head evidence.
No settings were changed. BL-P01-001 records the unavailable settings-mutation
capability and missing actual reviewer-account mapping with its owner and unblock
condition. The carried registry/signer/trust inputs remain under BL-P00-001.
SBOM/provenance production, scanning, verified promotion and trusted-base policy
execution are still engineering work; ordinary successful CI is not admission.
