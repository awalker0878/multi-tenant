# Contributing to the greenfield product

Start with the [product overview](README.md), [next work](next_work.md) and [documentation guide](docs/documentation-guide.md). Follow the [developer workflow](docs/engineering/developer-workflow.md), [Laravel conventions](docs/engineering/laravel-conventions.md), [security and tenancy rules](docs/engineering/security-and-tenancy.md) and [testing/CI standard](docs/engineering/testing-and-ci.md) for implementation changes. This branch contains implementation design and delivery controls; runnable product setup instructions will be added in P01 when they can be verified.

## Prepare a change

1. Identify the owning service, requirement IDs and work package. Read its design and prerequisite decisions.
2. Refine acceptance checks, including denied, conflicting and interrupted cases relevant to the change. Select checks by risk and the declared service/contract dependency graph; authorization and shared dependency changes require the wider critical suites.
3. Change code/contracts/configuration and their documentation together. Keep changes coherent and reviewable.
4. Record verification actually performed, its revision/environment and limitations. Real evidence references belong in the delivery register; examples stay synthetic.
5. Review compatibility, deployment, support and recovery impact with the owning reviewers. Update the next-work queue when work can advance.

Use the GitHub connector to publish branch changes in this workflow. Do not commit operational secrets, native data, credentials or sensitive evidence bytes. Refer to approved evidence locations through non-sensitive identifiers.

Each deployable owns its dependency locks, tests and build configuration. Install from reviewed locks; make dependency resolution intentional and reviewable. Use the pinned formatter and static analyzer configuration, with no unreviewed suppressions or baseline growth. P01 will establish CODEOWNERS and enforced review/status checks; its required outputs are described in the developer workflow.

## Documentation checks

Install the pinned documentation dependency in your chosen Python environment, then run from the repository root:

```sh
python -m pip install -r requirements-docs.txt
python scripts/render_delivery_views.py
python scripts/validate_docs.py
```

The scripts require Python 3.10 or newer and the pinned PyYAML dependency. They generate progress/traceability views and check links, IDs, statuses and register references. The scripts themselves do not install packages or contact external systems. Use `python scripts/render_delivery_views.py --check` to detect stale views without modifying them. These checks do not run application tests or native campaigns.

## Change description

Explain the user/operator problem, changed behavior/design, affected requirement/package/ADR IDs, verification performed, compatibility and operating impact, and remaining blockers. Separate proposed behavior from observed results. Do not mark a phase or qualification complete because its documentation or scaffold was committed.
