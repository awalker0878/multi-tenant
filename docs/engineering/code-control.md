# Context boundaries and code control

Owner: architecture and engineering leads; platform/SRE maintains merge and release enforcement. Reviewed: 2026-10-04. Delivery: P00.02, P01.01, P01.03, P01.04 and P10.06. This is the code-control policy for a context-oriented microservices repository. The [context inventory](../../architecture/context-map.yaml) records declared ownership and permitted relationships; the [context code structure](../architecture/context-code-structure.md) defines the source layout and [target architecture](../architecture/target-architecture.md) explains runtime placement.

Code control includes where code belongs, what it may depend on, who reviews a change, which checks admit it, and how its exact artifact reaches an environment. A directory convention alone is insufficient. Repository policy, executable checks and runtime credentials enforce different parts of the boundary and must agree.

## 1. Ownership inventory

Maintain one machine-readable record for every service, bounded context, capability and published contract. A capability belongs to one context; a context has one authoritative deployable owner at a given release. Several capabilities do not imply several containers. The console is a backend for frontend (BFF), responsible for user interaction and presentation; it is not a second owner of governance, catalogue or lifecycle decisions.

The current machine-readable inventory declares service/context source roots, layers, package dependencies and worker ownership. Capability semantics and public API/event ownership are defined in the service and contract specifications; P01 connects their implemented schemas and build identities to the inventory. Declared future paths are not reported as inspected runtime code. The current validator does not prove capability semantics or network-call relationships.

| Inventory information | Required control |
| --- | --- |
| Stable service/context/capability IDs; owned source roots and namespaces | Every first-party source path is assigned; duplicate ownership and unknown paths fail classification |
| Public API/event contract and producing context | One producer; versioned schemas; explicit consumers; generated clients trace to schema and generator revisions |
| Source, package and synchronous/event dependencies | Distinguish static imports, build inputs and network relationships; reject undeclared imports and accidental synchronous cycles |
| Database, migration, outbox/inbox and object-prefix owner | One writer authority; consumer projections remain local and attributable |
| Build/test entrypoints, lockfiles, images and deployable identity | Clean isolated builds; change impact expands to all relevant consumers |
| Accountable engineering role and approved review identities | Path ownership maps to actual authorized accounts; role names alone cannot satisfy a GitHub review |
| Technical shared package and direct/transitive consumers | Immutable package input, bounded API, independent compatibility tests; no shared aggregate or ORM model |
| Boundary exceptions | Exact edge/rule, owner, justification, reviewer, expiry and removal work item; no implicit allow-all |

Change this inventory in the same pull request as a boundary or contract change. A new code root, Composer autoload mapping, Python package, TypeScript alias or generated client must be reviewed as a dependency change. First-party source cannot escape analysis by moving outside an existing glob. Data/event relationships may be bidirectional when explicitly designed; this does not authorize mutual source imports or a distributed transaction.

## 2. Source dependency policy

PHP service code lives under `services/<service>/src/Contexts/<Context>/`. The Laravel host supplies bootstrap, configuration, bindings and process entrypoints. Python service code lives under `services/<service>/src/<service>/` with the corresponding lowercase layers. Use distinct PSR-4 namespace roots and Python package names for each service.

| Layer | May depend on | Must not depend on |
| --- | --- | --- |
| `Domain` / `domain` | Owned entities, values, domain events, pure rules and explicitly approved language-level primitives | Laravel, Eloquent, web/session globals, framework container, ORM, broker, Temporal or provider SDKs; another context's internals |
| `Application` / `application` | Owned Domain, use-case input/output, narrow ports defined by the consuming application | Infrastructure or Interfaces implementations, framework request objects, native provider calls, sibling service code |
| `Infrastructure` / `infrastructure` | Owned Application ports and Domain; approved database, transport, workflow and provider adapters | Another service's private models, direct foreign SQL, undeclared public-client versions |
| `Interfaces` / `interfaces` | Owned Application use cases and input/output; approved HTTP/job/CLI transport types | Direct persistence or native mutation; direct invocation of Infrastructure; a second implementation of business rules |
| Host composition root | Explicitly registers adapters and entrypoints for its service | Business invariants, cross-service aggregate ownership, native actions during bootstrap |

An adapter may use an approved external generated client to implement an application port. The use case consumes its own port and typed results, preserving the owner's vocabulary and error semantics. An HTTP controller, queue listener or console command invokes the same use case after establishing its input and caller context. Infrastructure implements local persistence with Eloquent; Domain entities do not extend Eloquent models. This is the project's chosen boundary, not a claim that Laravel requires this architecture.

Within a service hosting multiple contexts, prohibit direct imports of another context's Domain, Application and Infrastructure internals. Any exceptional in-process public boundary requires an explicit reviewed export and registry edge; colocating contexts is not permission to share aggregates or transactions. Cross-service interaction always uses a versioned API or event contract. Tests may replace an owned port with a test adapter, but cannot normalize forbidden production dependencies.

The console applies equivalent feature boundaries in PHP and TypeScript. Feature modules expose narrow entrypoints; a feature cannot reach into another feature's private state or backend internals. Generated contract types describe transport, not new sources of authorization. The BFF's own session and presentation persistence does not authorize connections to business-service databases.

## 3. Executable boundary checks

The committed [Context policy workflow](../../.github/workflows/architecture-policy.yml) runs the current registry check, architecture fixture tests and documentation checks on this branch and pull requests targeting it. It uses pinned actions, an ephemeral runner and read-only repository permissions. This initial workflow supplies concrete feedback; it is not the full language-aware application gate or proof that repository protection is active. P01.04 must bind required check names and reviewers to verified repository settings, then protect policy changes through the trusted enforcement path described below.

The repository's [architecture validator](../../scripts/validate_architecture.py) validates declared structure and checks the source forms it explicitly supports. Its result is a structural smoke check. P01 must install, configure and verify complete language tools before claiming comprehensive source-boundary enforcement. An absent service is not a successfully analyzed application. Run the current check from the repository root with `python scripts/validate_architecture.py`. It distinguishes registry validation, Python AST import checks where source exists, conservative PHP lexical prechecks and TypeScript source placement. It cannot establish complete PHP/Python dependency analysis, TypeScript import boundaries or application/runtime isolation. Its fixtures in [the architecture control suite](../../tests/documentation/test_architecture_controls.py) validate those limited controls.

| Enforcement surface | P01 implementation and proof | Limits to cover separately |
| --- | --- | --- |
| PHP dependency graph | Pin Deptrac and its parser in owned Composer locks; collect each context/layer and external dependency explicitly; apply the table above; fail unclassified first-party code and forbidden edges [C3] | Dynamic container lookups, string class names, reflection, helper functions and runtime configuration need custom static rules, explicit composition review and integration tests |
| PHP architecture-specific assertions | Use focused Pest architecture assertions or reviewed PHPStan rules where the graph needs additional checks; pin the selected implementation and prove it with violating fixtures | Style/type success does not imply the architecture rules ran; retain an independent architecture result |
| Python dependency graph | Pin Import Linter; combine forbidden, layered and independence contracts for service roots and modules [C4] | Layer order alone can permit unwanted lateral edges; forbid Interfaces-to-Infrastructure and service-to-service imports explicitly; review dynamic import/plugin paths |
| TypeScript/Vue imports | Pin ESLint plus the selected TypeScript/Vue parsers and boundary rules; check feature public entrypoints, path aliases, generated clients and server-only modules | ESLint `no-restricted-imports` covers static imports; dynamic imports and CommonJS forms need corresponding rules or syntax restrictions [C5] |
| Build isolation | Build a service from only its declared service root, contract inputs and versioned technical packages | A successful monorepo-wide build can conceal missing dependencies or sibling source copied into an image |
| Runtime data ownership | Execute denial tests with actual per-service database, object and broker identities | Static import analysis cannot establish database permissions, message ACLs or remote endpoint authorization |

Do not select a linear layer rule that implicitly allows Interfaces to reach Infrastructure. Configure the actual permitted edges. Domain receives a positive list of allowed primitives; allowing all external vendor packages would defeat the framework-independent boundary. Analyzer configuration must cover aliases, fully qualified references, inheritance, traits, attributes and generated entrypoints as supported by the selected parser.

The initial registry excludes generated and technical shared packages from Domain/Application even when their service can use them in adapters. Python standard-library imports are accepted by the initial smoke check; that is not proof that code avoids network, process, filesystem or database effects. Likewise, host-root classification does not prove a file contains only composition. Complete language rules and semantic review must close those gaps before G01 architecture acceptance.

Report scanned roots, files/classes/modules classified, excluded paths, uncovered symbols, rule failures and tool/configuration identities. Generated and vendor exclusions must be narrow, attributable and validated through their own build/contract checks. A renamed namespace, empty source set or missing configuration cannot turn a required check green.

### Negative fixtures required before enforcement is accepted

Maintain a small architecture-tool fixture suite separate from product tests. Each fixture asserts the expected rule identifier, not merely any nonzero exit. Include legal examples so an always-failing tool cannot pass its own verification.

| Fixture | Required rejection |
| --- | --- |
| PHP Domain entity imports an Eloquent model or Laravel facade | Framework dependency in Domain |
| Application use case imports its Infrastructure repository | Reversed dependency instead of an owned port |
| Interfaces controller calls an Infrastructure adapter directly | Entry adapter bypasses the application boundary |
| Catalogue imports governance source, including an aliased/fully qualified reference | Private service import |
| Python use case imports `lifecycle.infrastructure` from planning | Sibling-service import and adapter leak |
| Console feature imports another feature's private state through an alias or re-export | Undeclared frontend dependency |
| An unregistered source root, context or contract consumer appears | Ownership/impact classification incomplete |
| Analyzer configuration drops a source root or adds broad exclusions | Enforcement coverage shrinks without approval |

P01 records real executions of the selected tools against these fixtures. Tests of the lightweight registry validator establish that validator's behavior only; they do not satisfy the PHP, Python or frontend acceptance evidence by themselves.

## 4. Review and merge control

Use short-lived changes against the designated protected integration branch, with release/support branches only where the [release process](../releases/release-process.md) defines them. Keep one intent per review; coordinate a contract expansion, producer update and consumer adoption through compatible commits and releases. A service can release independently within the declared compatibility window.

P01 maps role responsibilities to authorized GitHub identities, creates `.github/CODEOWNERS`, and verifies the effective repository ruleset. Configure actual source, contracts, registry, migrations, dependency locks, pipeline code, signing/promotion policy and CODEOWNERS itself. Test precedence with representative changed paths. GitHub uses the last matching CODEOWNERS pattern and requires valid account access; a malformed or inaccessible owner does not enforce review [C1].

| Change class | Review policy |
| --- | --- |
| Ordinary context implementation | Owning context reviewer other than the author; affected consumer review when observable behavior changes |
| Context boundary, public contract or shared package | Owning producer plus affected consumers; architecture review for an ownership or dependency change |
| Authorization, tenant isolation, evidence integrity or native execution | Owning context plus an independent security or safety reviewer, as appropriate to the risk |
| Migrations, workflow history or recovery behavior | Owning context plus SRE/data/workflow reviewer; assess mixed-version and rollback constraints |
| CI rules, required checks, ownership map, exceptions, signing or promotion | Platform/architecture owner plus independent security review; the change cannot approve its own weakening |

For critical changes, require two distinct qualified reviewers satisfying the roles above. Merely listing two owners on a CODEOWNERS line does **not** require both approvals: GitHub accepts an approval from any listed owner [C1]. Where available, path-specific required-team review can implement the policy; GitHub documents that this feature does not apply to user-owned repositories [C2]. Otherwise use an approved review-policy check over current authorized individuals/roles and the exact reviewed revision, or retain explicit manual admission until that mechanism is implemented and demonstrated. Do not claim that a generic two-review count verifies two distinct reviewer roles.

The target protected-branch policy requires pull requests, current required checks, resolved blocking review findings, stale-approval dismissal or equivalent latest-change review, and blocks deletion/force pushes and ordinary direct updates. Select the precise supported ruleset behavior after checking repository ownership, plan and access. Limit bypass actors, separate emergency authority from normal development and record any actual exception. These are admission requirements; writing this document does not activate GitHub settings [C2].

Prove activation with the effective settings and controlled attempts to merge a failed check, omit an owner, reuse stale approval and submit a critical change without its independent role review. The repository's configured policy must reject the attempt; a screenshot of an intended setting alone is insufficient. Do not run destructive tests against a live protected branch.

## 5. Required checks and change impact

The [testing standard](testing-and-ci.md) owns behavioral suites. Code control supplies a mandatory admission result that aggregates the checks selected from the inventory and actual diff. P01 fixes stable check names and their trusted reporting source. A skipped, missing, cancelled, stale or inconclusive required constituent must prevent admission; an intentionally inapplicable suite needs a recorded classification reason.

| Required result | Admission condition |
| --- | --- |
| Architecture and inventory | Declared ownership, valid dependency edges, all changed source classified, language-boundary checks pass |
| Quality and type safety | Pinned formatting/lint/type analysis passes; no unapproved suppression growth |
| Contract compatibility | Schema diff and actual consumer fixtures confirm the supported old/new combinations; generated output matches source |
| Dependency and build integrity | Manifest/lock consistency, advisory/license policy, tool/image pins and reproducible isolated builds |
| Behavior and security | Impact-selected service/integration tests and mandatory critical suite pass with no hidden skipped safety cases |
| Review policy | Required owner/role approvals apply to the current revision; all scoped exceptions are current and valid |
| Artifact admission | Source/check identities match SBOM, provenance and immutable image digests; selected signer/builder policy satisfied |

Determine impact from both base and proposed inventory so deleting an edge cannot remove the tests it previously required. Expand through contract consumers, shared packages and build inputs, and include renames, deletions, migrations, lockfiles, generated files and infrastructure. Unknown classification runs the full applicable suite and blocks release until ownership is resolved. Authorization, tenancy, workflow/fencing, evidence, shared CI and dependency-policy changes always run the full relevant critical cross-service suite.

Protect the check implementation as code: a PR that changes a workflow or analyzer rule cannot establish its own admission solely by executing that weakened version. Run enforcement from a trusted base or separately governed reusable workflow, assess the proposed configuration with negative fixtures, and require independent approval before adopting it. Keep untrusted PR code and artifacts out of privileged review/release jobs. Where GitHub supports selecting an expected app for a required status, bind it to the approved reporter [C2].

API/schema diff tools detect structural changes, not every semantic break. Human contract review and consumer tests cover changed authorization, error meanings, units, ordering, idempotency and event timing. A schema-compatible authorization regression still blocks merge. Do not alter published historical contracts to make a diff appear compatible.

## 6. Controlled exceptions and baseline drift

Start new contexts without architecture or type suppression baselines. Any necessary exception specifies its exact rule and dependency edge or files, owner, rationale, risk, compensating check, approving reviewer, UTC expiry, removal task and applicable releases. Check it on every affected build and promotion. Reject an expired exception, wildcard expansion, missing reviewer or silent baseline regeneration.

The same discipline applies to dependency/license exceptions, scanner unavailability, flaky-test quarantine and temporary contract compatibility windows. A style exception cannot waive tenant isolation or native-write fencing. Removing a required control is a policy change with independent review, not a normal developer suppression.

Track baseline additions and removals in the change report. Eliminate unmatched/obsolete ignore entries, forbid new unexplained exclusions and test analyzers after tool upgrades. The engineering lead reviews outstanding exceptions during P10.06 support/requalification preparation; their expiry is not postponed automatically by release tagging.

## 7. Release and continuing verification

Each deployable records its source commit, service path, context IDs, public-contract versions, dependency locks, migrations, compatible peer versions and immutable image digest. The product release manifest composes those identities into a tested set. A Git tag identifies a source point; it does not alone establish which services were built or qualified.

Promote the exact verified artifacts. Evaluate independent service upgrades against supported peers and active workflow histories. Changes to a shared technical package trigger all declared transitive consumer checks even when only one service is initially promoted. Rollback and recovery follow the actual data/native-effect boundary, not an assumption that reverting a commit reverses an operation.

P00.02 reviews ownership and dependency direction. P01.01 proves independent source/build boundaries. P01.03 proves published contracts and consumer conformance. P01.04 demonstrates actual analyzer, review and merge/promotion enforcement. P10.06 reviews policy drift, expired exceptions, dependency support and requalification triggers. Store resulting evidence in the canonical delivery register only after the work is executed and reviewed.

## Primary references

Reviewed 2026-10-04. These sources establish tool behavior; source layout, reviewer roles and admission requirements above are project policies.

| Ref | Primary source | Use |
| --- | --- | --- |
| C1 | [GitHub CODEOWNERS](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-code-owners) | Pattern precedence, account access and any-owner approval semantics |
| C2 | [GitHub ruleset rules](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets) | Required checks/reviews, team-review limits, bypass and reporting-source controls |
| C3 | [Deptrac configuration](https://deptrac.github.io/deptrac/configuration/) and [collectors](https://deptrac.github.io/deptrac/collectors/) | Explicit layer collection, allowed edges and covered dependency types |
| C4 | [Import Linter layers](https://import-linter.readthedocs.io/en/stable/contract_types/layers/), [forbidden imports](https://import-linter.readthedocs.io/en/stable/contract_types/forbidden/) and [independence](https://import-linter.readthedocs.io/en/stable/contract_types/independence/) | Complementary Python dependency contracts |
| C5 | [ESLint restricted imports](https://eslint.org/docs/latest/rules/no-restricted-imports) | Static import restriction and its dynamic-import limitation |
