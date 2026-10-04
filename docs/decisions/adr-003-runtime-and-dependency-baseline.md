# ADR-003 — Runtime and dependency baseline

Owner role: Engineering lead. Related phases: P00, P01. Record date: 2026-10-04.

Origin: `DESIGN`. Disposition: `PROPOSED` as recorded in the [decision register](decision-register.md).

This record develops the existing baseline for review and records bounded experiments below. No accountable-owner acceptance or native qualification is claimed; the register disposition is unchanged.

## Context

The requested frontend stack now has measured dependency candidates from isolated compatibility experiments. Laravel 13 and PHP 8.5 remain candidates in the register, and the full production bill of materials is not accepted. Reproducible builds and upgrade responsibility require one reviewed set of runtime, package and image identifiers for actual deployables.

## Decision and scope

Laravel 13/PHP 8.5 remain candidates. Measured Node/Python/runtime and dependency versions are recorded in the P00 compatibility reports; production runtime/image selection, complete service dependencies and accountable update ownership remain unresolved.

Initial checkpoint: NOW: P00.03 / G00.03 before P01.01.

Refinement and validation: Exact lock/image resolution, update policy and support lifecycle before G01.

## Options and trade-offs

| Option | Assessment |
| --- | --- |
| Validate the proposed Laravel/PHP candidates | Keeps the proposed baseline while requiring dependency resolution, build and execution evidence. |
| Select another compatible supported backend version set | Can resolve a candidate incompatibility, but must still satisfy ADR-002 and document support and upgrade implications. |
| Allow each service to choose versions independently | Reduces coordination initially but enlarges the maintenance, compatibility and image qualification matrix. |

## Consequences

- Each deployable needs lockfiles, image digests and an accountable dependency update owner.
- A common initial runtime family limits the qualification matrix; exceptions must identify the service and reason.

## Unresolved details and evidence needed

- Review the measured PHP, Laravel, Python, Node and package-manager candidates; resolve remaining service dependencies and immutable operating-system image identities.
- Document compatibility sources, vulnerability/update policy, mirror availability and support lifecycle boundaries.

## Acceptance and validation

- Build all initial deployables from clean lockfiles and captured image inputs before G01.
- Run cross-language schema and integration checks using the exact selected runtimes.
- Demonstrate a repeatable dependency update and rollback decision on a non-production branch.

Record actual reviewer identity, decision date and evidence references when review occurs. Record delivery and gate outcomes in the delivery register; updating this ADR does not complete a work package.

## Revisit conditions

A dependency reaches its accepted support boundary, an unresolved vulnerability changes acceptability, or a required integration invalidates the runtime combination.

## Related records

- [Decision register](decision-register.md) — authority for disposition, origin and blocking checkpoint.
- [Phased implementation plan](../implementation/phased-plan.md) — package and gate sequence.
- [ADR authoring template](../templates/adr.md) — required decision-record fields.

## P00 compatibility execution

The [P00.03 results](../implementation/p00-compatibility-results.md) record the actual resolved versions, successful probes, failed attempts and remaining runtime limits. Candidate selection now follows those measurements; upstream support tables alone do not close this decision. The spike remains separate from product service code, and this ADR remains proposed until the complete bill of materials and operating owner are reviewed.

The [Python tooling continuation](../implementation/p00-python-tooling-results.md) measured CPython 3.12.14 and uv 0.12.19 with Ruff 0.16.10, mypy 2.4.0, pytest 9.1.1, Import Linter 2.15/Grimp 3.17 and pip-audit 2.10.1. A fresh locked installation passed lint/format, strict typing over 26 files, four synthetic behavior tests, three dependency contracts and seven intended negative boundary cases. Strict advisory lookup returned no known advisories for the 49 audited packages at execution time. These are feasible tool candidates, not adopted production versions or evidence that business services are implemented.

Adoption requires an accountable engineering/SRE decision, update and support ownership, actual service locks and images, and P01 executions against the registered service, worker and shared-package roots. The Python probe forbids only its included HTTPX/Pydantic transport libraries in core layers; actual service rules must cover their complete approved dependency set. The measured spike does not qualify restricted-network mirrors, runtime isolation, native workflows or production security.

The [complete PHP/browser replay](../implementation/p00-integration-results.md) also passed with PHP 8.5.11, Composer 2.10.3, Laravel 13.34.0, Inertia Laravel 3.5.1, Pint 1.32.1, Larastan 3.12.2/PHPStan 2.2.16, Deptrac 4.7.2 and Pest 4.7.8/Laravel plugin 4.1.0. Chromium 153.0.8010.12 ran through Playwright 1.63.0 with Node 24.19.0/npm 11.17.0. This supports adopting a measured candidate, subject to production image, extension, mirror, browser-policy and accountable update decisions. Neither a tool pass nor an advisory lookup changes this ADR's disposition.


## Candidate image execution

The [image experiment](../implementation/p00-image-results.md) now provides an executed Debian Bookworm `linux/amd64` candidate with separately built PHP/Python quality and runtime stages. Its captured input lock fixes upstream index and platform manifest digests for PHP, Python, Node, Composer and uv; Debian additions use a fixed authenticated snapshot. Normal CI pushes replay that lock rather than resolving mutable tags. Runtime extension lists, installed OS/language packages, local image identities, build logs and positive/negative runtime observations are retained with source bindings.

The candidates run as UID/GID 10001 with no added capabilities and test read-only roots plus explicitly writable temporary mounts. This establishes the recorded fixture behavior and candidate BOM. It does not establish byte-identical rebuilt images, signed publication, an installed environment BOM, OS vulnerability qualification, production FPM/ingress behavior or an approved enterprise mirror path. Complete service images and their operational controls remain P01 obligations. Review the exact inventories and limitations before adopting the family; any changed source, lock, OS snapshot or extension selection requires a new measured result.

The [decision and input packet](../implementation/p00-decision-and-input-review.md) consolidates DC04–DC08 and IP02, including runtime/update ownership, dependencies, trust/custody and managed-browser/network decisions. These actual operating choices remain required; the executable image and contract experiments are no longer missing engineering work.
