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

Laravel services use their own standard `app/` tree and local `App\` namespace, following [ADR-024](../decisions/adr-024-pragmatic-laravel-domain-convention.md). `app/Domain/<Capability>` and `app/Application/<Capability>` organize business behavior within the service's bounded context; `app/Infrastructure` holds integrations. Controllers, commands, jobs, listeners, policies and providers retain Laravel's normal locations. The selected convention is documented by its author [C6]. Reusing `App\` in independently built services is expected: namespace resolution is relative to the owning Composer application, never a global shared namespace.

| PHP area | Permitted responsibility/dependencies | Forbidden coupling |
| --- | --- | --- |
| `App\Domain\<Capability>` | Owned Eloquent models and business transitions, value objects, rules, exceptions and events; Laravel facilities appropriate to those responsibilities | Application, Infrastructure or delivery classes; transport request/response objects; another service's private source/data |
| `App\Application\<Capability>` | Domain capabilities, Actions with public `handle()`, Laravel authorization, direct Eloquent persistence and local transactions; consumer-owned contracts for external behavior | Concrete Infrastructure or delivery classes; HTTP request/response objects as use-case input/output; native provider SDK calls |
| `App\Infrastructure` | External SDK/client adapters, specialized persistence and implementations of owned contracts; approved generated transport clients and technical integration packages | Private foreign models/SQL, undeclared client versions or taking ownership of another context's business rules |
| Standard Laravel entrypoints | Validated transport input, caller context, Action invocation and response presentation; simple authorized/scoped reads may query owned models | Business mutation workflows duplicated outside Actions, foreign database access or direct native mutation |
| Policies and providers | Policies express resource/action authorization; providers register bindings and framework integration | Business state transitions hidden in authorization or bootstrap; cross-service aggregate ownership |

Domain/Application may use Laravel. Dependency checks prohibit upward first-party dependencies and transport coupling; they do not reject Eloquent or a framework facade merely because it is a vendor class. Using `Gate` to evaluate a registered policy is normal Action behavior. Container lookups, custom facades and string class references must not conceal an otherwise forbidden Infrastructure/delivery dependency. Actions coordinate durable publication through the owning service's outbox protocol; asynchronous reactions do not authorize direct job-class imports into the use-case layer.

Capabilities in the same bounded context can collaborate directly, including owned model relationships. Do not require a repository or Data class for every operation. An external service/provider boundary requires an explicit owned contract and adapter; an ordinary local Eloquent query does not. The initial six business contexts each have their own service. If one service later hosts another bounded context, that topology needs an ownership decision and explicit public boundary before private code is shared. Cross-service interaction continues to use versioned API/event contracts, never shared Eloquent models or a combined autoloader.

Python retains `services/<service>/src/<service>/` and distinct package names:

| Python layer | May depend on | Must not depend on |
| --- | --- | --- |
| `domain` | Owned entities, values, events, pure rules and approved language primitives | Application/infrastructure/interfaces, ORM, web/broker/Temporal/provider SDKs or foreign service internals |
| `application` | Owned domain, use-case types and consuming application ports | Concrete infrastructure/interfaces, transport request objects, native provider SDKs or sibling service code |
| `infrastructure` | Owned application/domain and approved adapters | Foreign private source/SQL or undeclared clients |
| `interfaces` | Owned application and transport types | Infrastructure implementation calls, direct persistence/native mutation or duplicated invariants |
| Bootstrap | Binding the service's adapters and entrypoints | Business invariants or native actions during startup |

The console applies equivalent feature boundaries in PHP and TypeScript. Feature modules expose narrow entrypoints; a feature cannot reach into another feature's private state or backend internals. Generated contract types describe transport, not new sources of authorization. The BFF's own session and presentation persistence does not authorize connections to business-service databases.

## 3. Executable boundary checks

The P00.03 experiment under `spikes/compatibility/` is a deliberately isolated non-product source root, alongside documentation tooling. It has its own recorded commands and results. The product architecture validator excludes only that exact spike root; other unregistered spike/source roots still fail. Experimental dependencies, locks and successful probes do not satisfy service build or G01 acceptance. Promotion requires a newly registered service/package and its normal checks.

The committed [Context policy workflow](../../.github/workflows/architecture-policy.yml) runs the current registry check, architecture fixture tests and documentation checks on this branch and pull requests targeting it. It uses pinned actions, an ephemeral runner and read-only repository permissions. This initial workflow supplies concrete feedback; it is not the full language-aware application gate or proof that repository protection is active. P01.04 must bind required check names and reviewers to verified repository settings, then protect policy changes through the trusted enforcement path described below.

The repository's [architecture validator](../../scripts/validate_architecture.py) validates declared structure and checks the source forms it explicitly supports. Its result is a structural smoke check. P01 must install, configure and verify complete language tools before claiming comprehensive source-boundary enforcement. An absent service is not a successfully analyzed application. Run the current check from the repository root with `python scripts/validate_architecture.py`. It distinguishes registry validation, Python AST import checks where source exists, conservative PHP lexical prechecks and TypeScript source placement. It cannot establish complete PHP/Python dependency analysis, TypeScript import boundaries or application/runtime isolation. Its fixtures in [the architecture control suite](../../tests/documentation/test_architecture_controls.py) validate those limited controls.

| Enforcement surface | P01 implementation and proof | Limits to cover separately |
| --- | --- | --- |
| PHP dependency graph | Pin Deptrac and its parser in each application lock; collect the local `App\` layers and normal delivery directories, allow Laravel as specified above, and fail unclassified first-party code and forbidden edges [C3] | Dynamic container lookups, string class names, reflection, helper functions and runtime configuration need custom static rules, explicit composition review and integration tests |
| PHP architecture-specific assertions | Require Pest architecture checks for the adopted namespaces, Action `handle()` presence and any selected Data naming convention; add reflection/PHPStan assertions for public visibility and project-specific gaps | Method-presence assertions do not prove public visibility, authorization, transactions, outbox durability or every dynamic dependency; test those separately |
| Python dependency graph | Pin Import Linter; combine forbidden, layered and independence contracts for service roots and modules [C4] | Layer order alone can permit unwanted lateral edges; forbid Interfaces-to-Infrastructure and service-to-service imports explicitly; review dynamic import/plugin paths |
| TypeScript/Vue imports | Pin ESLint plus the selected TypeScript/Vue parsers and boundary rules; check feature public entrypoints, path aliases, generated clients and server-only modules | ESLint `no-restricted-imports` covers static imports; dynamic imports and CommonJS forms need corresponding rules or syntax restrictions [C5] |
| Build isolation | Build a service from only its declared service root, contract inputs and versioned technical packages | A successful monorepo-wide build can conceal missing dependencies or sibling source copied into an image |
| Runtime data ownership | Execute denial tests with actual per-service database, object and broker identities | Static import analysis cannot establish database permissions, message ACLs or remote endpoint authorization |

Configure the permitted edges for each language rather than applying one linear layer rule to both. PHP permits Laravel within Domain/Application while forbidding upward application dependencies; Python retains its framework-independent core and explicit Interfaces-to-Infrastructure prohibition. External provider SDKs and generated transport clients remain infrastructure concerns. Analyzer configuration must cover aliases, fully qualified references, inheritance, traits, attributes and generated entrypoints as supported by the selected parser.

The project registry keeps generated transport clients and shared technical integration packages out of Domain/Application even when the service may use them in adapters. This project-specific boundary does not ban Laravel itself. Python standard-library imports are accepted by the initial smoke check; that does not prove freedom from I/O. PHP host-root classification likewise does not establish correct policy or Action delegation. Complete language rules and behavioral review must close those gaps before G01 architecture acceptance.

Report scanned roots, files/classes/modules classified, excluded paths, uncovered symbols, rule failures and tool/configuration identities. Generated and vendor exclusions must be narrow, attributable and validated through their own build/contract checks. A renamed namespace, empty source set or missing configuration cannot turn a required check green.

### Negative fixtures required before enforcement is accepted

Maintain a small architecture-tool fixture suite separate from product tests. Each fixture asserts the expected rule identifier, not merely any nonzero exit. Include legal examples so an always-failing tool cannot pass its own verification.

| Fixture | Required rejection |
| --- | --- |
| PHP Domain model imports an Application Action, Infrastructure adapter or HTTP request | Upward first-party dependency or transport coupling |
| Application use case imports its Infrastructure repository | Reversed dependency instead of an owned port |
| Application Action imports an `App\Http` controller, `App\Jobs` class or concrete Infrastructure adapter | Use case depends on delivery or integration implementation |
| Catalogue imports governance source, including an aliased/fully qualified reference | Private service import |
| Python use case imports `lifecycle.infrastructure` from planning | Sibling-service import and adapter leak |
| Console feature imports another feature's private state through an alias or re-export | Undeclared frontend dependency |
| An unregistered source root, context or contract consumer appears | Ownership/impact classification incomplete |
| Analyzer configuration drops a source root or adds broad exclusions | Enforcement coverage shrinks without approval |

Legal PHP fixtures must include an Eloquent Domain model, an Action using `Gate` and `DB`, ordinary Laravel controllers, and two isolated services each using `App\`. A simple authorized read and collaboration between capabilities in one context must pass. Foreign Composer source mappings and sibling service build inputs must still fail even when their namespaces look identical.

P01 records real executions of the selected tools against these fixtures. Tests of the lightweight registry validator establish that validator's behavior only; they do not satisfy the PHP, Python or frontend acceptance evidence by themselves. A skipped namespace check cannot satisfy G01 for a required service whose implementation or adopted namespace is missing.

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
| C6 | [Pragmatic Domain-Driven Design in Laravel](https://dev.to/maiobarbero/pragmatic-domain-driven-design-in-laravel-with-laravel-boost-3bcm) | Author's Laravel convention; no package or assistant program is adopted |
