# Portable Multi-Tenant Secure Hosting

Private infrastructure architecture, engineering and implementation workspace.

## Read the architecture and engineering in Git

The Word library is now available as full linked Markdown chapters, tables, diagrams and working templates—not only a list of attachments.

| Area | Start here |
| --- | --- |
| Complete documentation | [Documentation home](docs/README.md) |
| Reference architecture / RAD | [Architecture](docs/architecture/README.md) · [RAD reading view](docs/architecture/RAD.md) |
| Technical architecture / TAD | [Engineering](docs/engineering/README.md) · [TAD reading view](docs/engineering/TAD.md) |
| Solution design | [Service decisions and worked infrastructure](docs/solutions/README.md) |
| Architecture decisions | [Proposed ADR register](docs/adr/README.md) |
| Implementation | [Commissioning and code map](docs/implementation/README.md) |
| Assurance and audit | [Requirements, qualification and source audits](docs/assurance/README.md) |
| Operations and working forms | [Operations](docs/operations/README.md) · [HLD/LLD/MOP templates](docs/templates/README.md) |
| Provenance and original artifacts | [Migration record](docs/DOCUMENTATION_MIGRATION.md) · [Source files and workbooks](docs/ARTIFACT_CATALOG.md) |

## Implementation boundaries

The infrastructure architecture remains authoritative. Terraform and Ansible implement separately owned resource and verification responsibilities; they do not define a new hosting application. Native code remains candidate implementation until its actual supported target and evidence are accepted. The supplied source records distinguish local fixtures, native readback and formal operating authorization.

The ten native Terraform module/root pairs, Ansible source, observation tools, tests and packet fixtures are retained. The integrated audit correction preserves production connectivity and resource semantics. Current source publication is recorded by Git and exact CI results; ZIP-era statements describe their original delivery only. Historical test reports remain historical, and no infrastructure is deployed by this repository review.

## Local review

```sh
python -m pip install -r requirements-repository.txt
python scripts/check_documentation.py
python scripts/check_repository.py
python tools/check_local.py
```

See [TESTING.md](docs/TESTING.md) for independent Terraform/Ansible and disposable-lab gates. Read the exact CI revision for actual engine and local packet results; none of those checks qualifies a native platform. See [LOCAL_IMPORT.md](docs/LOCAL_IMPORT.md) before importing into your own checkout.

## Completion-audit corrections

[Corrective disposition register](docs/assurance/completion-corrections.md) records code-fidelity, semantic-negative, current-integrity, ADR lifecycle, test-family and assertion-allocation work. [Maintained design records](docs/current/README.md) are distinct from immutable Word transcriptions. Actual initial Terraform/Ansible engine results and provider locks are recorded in [engine evidence](evidence/completion-corrections/README.md); final-revision CI and native qualification are separate gates.

## Current main integration follow-up

[Main integration audit](docs/assurance/main-integration-audit.md) records the mixed-correction test failures and their canonical-record resolution. The complete regression suite remains required alongside real Terraform/Ansible checks; no failing tests are skipped and no native acceptance is issued.

## Routed IPv6 implementation work

The [I08 packet extension](docs/implementation/routed-ipv6-lab.md) exercises the existing WD14 topology over real IPv6 sockets in disposable Linux namespaces. Its [engineering profile](docs/engineering/routed-ipv6-qualification.md) distinguishes local path evidence from the still-open native platform and offered-family acceptance. Exact current run results belong to CI artifacts, not historical reports.

## Known native task-tree verification

The [I09 Nutanix task-tree extension](docs/implementation/nutanix-task-tree-readback.md) observes explicitly recorded parent/child work without discovery, cancellation or mutation. Its [engineering profile](docs/engineering/nutanix-task-tree-readback.md) keeps incomplete children, failed tasks, native resource differences and actual fencing obligations separate from a successful parent label.

## Platform capability evidence

The [machine-readable platform capability registry](docs/engineering/platform-capability-registry.md) records candidate implementation coverage separately from native qualification. Current entries fail closed for placement because no installed platform tuple has completed native qualification; local source or fixtures are not promoted to production capability evidence.


## Pre-placement platform-family eligibility

The [platform-family eligibility precheck](docs/engineering/pre-placement-platform-eligibility.md) consumes a reviewed WSD engineering reference plus mandatory/optional portable capabilities and fails closed when no candidate family is natively qualified. It does not choose a site, reserve capacity, allocate infrastructure, run Terraform, or authorize activation. The repository example is intentionally held until native platform qualification exists.
