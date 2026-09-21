You are working in the current repository. Your objective is to **scan the entire repository documentation, identify every unfinished implementation item, and implement the work to completion**.

Treat `/docs` and all documentation beneath it as the primary source of truth for the intended architecture, engineering decisions, implementation requirements, acceptance criteria, and remaining work.

## Primary objective

Systematically inspect the repository and complete **all unfinished work described or implied by the documentation**.

Do not stop after identifying gaps.
Do not simply create another TODO list.
Do not produce a report instead of implementing the work.

Your job is to **find → understand → implement → test → document → commit** each remaining piece of work.

Continue until the repository has no reasonably implementable unfinished work remaining from the documentation.

## 1. Scan the entire documentation set

Recursively inspect:

* `/docs/**`
* architecture documents
* reference architecture
* technical architecture / TAD material
* RAD material
* engineering designs
* solution designs
* implementation guides
* ADRs
* runbooks
* deployment documentation
* Terraform documentation
* Ansible documentation
* testing/validation documentation
* security documentation
* operations documentation
* migration/commissioning documentation
* README files throughout the repository
* any `1.0`, roadmap, backlog, gap-analysis, readiness, or implementation-plan material still present

Also search the repository for indicators of unfinished work such as:

* TODO
* FIXME
* XXX
* TBD
* incomplete
* unfinished
* future work
* remaining work
* not implemented
* placeholder
* stub
* mock
* follow-up
* deferred
* planned
* gap
* pending
* manual step
* unsupported
* not production ready
* acceptance criteria that have not been satisfied

Do not assume a task is complete merely because documentation says it exists. Verify the corresponding implementation.

## 2. Build an internal implementation inventory

Before modifying code, derive an internal dependency-ordered inventory of the unfinished work.

Cross-reference documentation against the actual repository:

* Terraform modules
* Terraform environments/stacks
* providers
* variables and outputs
* Ansible roles
* playbooks
* inventories
* templates
* schemas
* controllers/orchestration
* scripts
* validation tooling
* policy-as-code
* CI/CD
* tests
* examples
* deployment workflows
* security controls
* lifecycle operations
* reconciliation
* commissioning
* backup/recovery
* HA
* observability
* documentation

Use this inventory to guide execution, but **do not stop merely to present the inventory**.

Immediately begin implementing it.

## 3. Use the documented architecture as authoritative

Preserve the architecture and design intent already established in the repository.

In particular:

* Infrastructure/reference architecture comes first.
* Terraform and Ansible are implementation mechanisms for that architecture, not substitutes for it.
* Preserve the Tenant → WSD → environment/security/placement model where documented.
* Preserve secure-by-default multi-tenancy.
* Preserve government security-zone and workload-isolation concepts.
* Preserve vendor-neutral abstractions where the architecture requires them.
* Maintain separate realizations for Nutanix, VMware, OpenStack, and other documented platforms rather than collapsing them into inappropriate common-denominator implementations.
* Maintain clear platform, tenant, workload, shared-services, management, backup, migration, transit, and security boundaries where required by the architecture.
* Follow existing ADRs unless implementation evidence shows that an ADR must be updated.
* Do not silently contradict documented architectural decisions.

If multiple documents overlap, reconcile them based on the newest and most specific architectural decision.

## 4. Implement real functionality

Do not satisfy requirements with superficial artifacts.

Avoid:

* empty modules
* empty roles
* placeholder functions
* TODO comments replacing implementation
* mock implementations presented as production implementations
* fake success paths
* hard-coded test-only values in production code
* scripts that only print what they would do
* documentation claiming functionality that does not exist
* compatibility shims solely to avoid fixing the real implementation
* dead configuration
* duplicated architectures
* abandoned parallel implementations

Where functionality can reasonably be implemented without access to live infrastructure, implement it completely.

Where live credentials, endpoints, hardware, or external systems are genuinely required, implement everything up to that boundary:

* schema
* configuration
* providers
* interfaces
* validation
* orchestration
* safety controls
* dry-run support where appropriate
* tests
* documentation
* operator workflow
* explicit runtime prerequisites

Do not use lack of live infrastructure as an excuse to leave the surrounding implementation unfinished.

## 5. Work in dependency order

Prefer foundational work first.

Typical order:

1. architecture/schema corrections
2. shared contracts and data models
3. reusable Terraform modules
4. environment-specific Terraform compositions
5. Ansible roles
6. orchestration/playbooks
7. platform integrations
8. policy/security controls
9. lifecycle operations
10. reconciliation
11. commissioning/decommissioning
12. HA/recovery
13. observability
14. validation/testing
15. CI/CD
16. examples
17. operator documentation
18. cleanup of superseded material

Adjust this order when repository dependencies indicate a better sequence.

## 6. Make small atomic commits continuously

**Commit frequently as you work.**

Do not accumulate the entire implementation into one huge commit.

Each commit should represent one coherent piece of completed work.

Good examples:

* `feat(terraform): add WSD network composition`
* `feat(ansible): implement Nutanix tenant foundation role`
* `feat(vmware): add workload-domain reconciliation`
* `feat(openstack): implement tenant security baseline`
* `test(terraform): add environment validation coverage`
* `feat(lifecycle): add guarded decommission workflow`
* `docs: document WSD commissioning process`
* `refactor: remove superseded tenant deployment path`

Aim for commits that are:

* small
* understandable
* independently reviewable
* internally consistent
* tested before commit

Do not create meaningless commits for individual lines.

Do not wait until the end to commit.

After each logical unit:

1. implement it
2. run relevant validation/tests
3. fix failures
4. update documentation if required
5. inspect the diff
6. commit it
7. continue immediately with the next unit

## 7. Keep documentation synchronized

When implementation changes architectural or operational reality, update the corresponding documentation in the same logical change.

When work described in an implementation plan is completed:

* update the authoritative documentation
* remove stale TODO language
* migrate useful design information into its permanent documentation location
* remove or archive obsolete planning material where appropriate
* repair internal documentation links
* update examples
* update status/readiness statements

Do not leave completed work described as unfinished.

Do not leave obsolete architecture beside the current architecture without clearly marking or removing it.

## 8. Validate continuously

Run the strongest locally available checks throughout implementation.

Where applicable:

### Terraform

* `terraform fmt -recursive`
* `terraform init -backend=false`
* `terraform validate`
* module tests
* stack/environment validation
* linting if configured
* policy validation

### Ansible

* syntax checks
* linting
* role tests if present
* inventory validation
* playbook parsing
* molecule or equivalent tests where available

### Application/code

* unit tests
* integration tests
* type checks
* static analysis
* linting
* formatting
* builds

### Repository

* documentation/link validation
* schema validation
* generated-file consistency
* CI configuration validation
* security checks already supported by the repository

Fix failures rather than merely documenting them.

## 9. Test architecture-level behavior

Do not limit testing to syntax.

Add or improve tests for important architectural guarantees such as:

* tenant isolation
* WSD isolation
* environment separation
* secure defaults
* network-policy defaults
* invalid configuration rejection
* required security controls
* naming/addressing validation
* deterministic composition
* provider-specific constraints
* dependency ordering
* lifecycle state transitions
* idempotency
* reconciliation
* failure handling
* rollback/recovery behavior where applicable
* backup/recovery configuration
* HA configuration
* configuration drift detection

Use fixtures/examples representing realistic environments.

## 10. Reconcile documentation against implementation repeatedly

After major implementation groups, rescan `/docs`.

Ask:

* Is anything still described as unimplemented?
* Is there an acceptance criterion without implementation?
* Is there a documented module/role/workflow that does not exist?
* Is functionality implemented but not wired into an environment?
* Is an environment missing from Terraform or Ansible?
* Is there code that cannot actually be reached?
* Are examples using obsolete interfaces?
* Do docs and code disagree?
* Did implementation expose another missing dependency?

If so, continue implementing.

## 11. Follow unfinished work transitively

A task is not complete merely because the immediate code exists.

For example:

Terraform module
→ environment composition
→ inputs
→ validation
→ outputs
→ orchestration
→ Ansible integration
→ security controls
→ tests
→ CI
→ operational docs

Follow these dependencies until the feature is usable as part of the complete repository workflow.

Do not stop at isolated modules.

## 12. Make reasonable engineering decisions

When documentation leaves a minor implementation decision unspecified:

* inspect surrounding architecture
* inspect ADRs
* inspect existing patterns
* choose the design most consistent with the repository
* implement it
* document the decision when architecturally significant

Do not stop for unnecessary human confirmation.

Use sound engineering judgment to fill ordinary implementation gaps.

Only treat something as externally blocked when it genuinely requires information that cannot be derived from the repository, such as:

* real credentials
* actual production endpoints
* site-specific secrets
* unavailable hardware
* organizational approval
* externally assigned identifiers that cannot safely be invented

Even then, complete all repository-side work possible around that dependency.

## 13. Remove technical debt exposed by the implementation

As you encounter:

* duplicate modules
* dead code
* abandoned implementation paths
* inconsistent naming
* stale schemas
* outdated examples
* obsolete compatibility layers
* unused variables
* duplicate documentation
* contradictory architecture
* test-only hacks in production paths

clean them up when doing so is safe and directly related to the implementation.

Use separate small commits for substantial cleanup.

## 14. Do not stop prematurely

Do **not** stop after:

* scanning the documentation
* creating a gap list
* implementing one subsystem
* fixing the easiest TODOs
* writing tests without implementations
* implementing Terraform but ignoring Ansible
* implementing modules without wiring environments
* updating docs without code
* generating a summary of remaining work

Continue through the remaining items.

When you believe the repository is complete, perform another full repository scan before concluding.

## 15. Final completion audit

Before declaring completion:

1. Rescan all documentation.
2. Search again for unfinished-work markers.
3. Compare documented capabilities against code.
4. Inspect Terraform environment coverage.
5. Inspect Ansible environment/platform coverage.
6. Inspect orchestration and lifecycle workflows.
7. Inspect security controls.
8. Inspect reconciliation and idempotency.
9. Inspect commissioning/decommissioning.
10. Inspect HA and recovery.
11. Inspect tests.
12. Inspect CI/CD.
13. Inspect operator/runbook documentation.
14. Run all practical repository validation.
15. Run `git status`.
16. Ensure intentional changes are committed.
17. Ensure no accidental generated files or secrets are present.
18. Ensure documentation accurately reflects the resulting implementation.

If the audit exposes additional implementable work, **continue implementing it rather than ending the task**.

## 16. Completion report

Only after implementation and validation are exhausted, provide a concise final report containing:

* major capabilities completed
* tests/validation executed
* significant architectural decisions made
* the sequence of commits created
* any items genuinely blocked by external infrastructure or credentials
* exact reason each external blocker cannot be completed from the repository alone

Do not classify something as externally blocked if repository-side implementation can still be completed.

## Operating rule

**Keep moving forward.**

Use the repository and `/docs` to resolve questions whenever possible. Make reasonable engineering decisions where documentation leaves implementation details open.

Implement in small increments, validate each increment, make small atomic commits as you go, and continue until the documented unfinished work has been exhausted.
