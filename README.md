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

The ten native Terraform module/root pairs, Ansible source, observation tools, tests and packet fixtures are retained. The completion-audit corrective release fixes documentation fidelity, decision governance and the Terraform verification boundary; it does not change production connectivity. Historical test reports remain historical. Repository updates are recorded in the corrective pull request, and no infrastructure is deployed.

## Local review

```sh
python -m pip install -r requirements-repository.txt
python scripts/check_documentation.py
python scripts/check_repository.py
python tools/check_local.py
```

See [TESTING.md](docs/TESTING.md) for independent Terraform/Ansible and disposable-lab gates. Consult the exact pull-request commit checks for actual engine results; source documentation does not predeclare those checks successful or claim native qualification. See [LOCAL_IMPORT.md](docs/LOCAL_IMPORT.md) before importing into your own checkout.

## Completion-audit corrections

[CA-01–CA-11 response](docs/assurance/completion-audit.md) · [370 assertion allocations](docs/assurance/implementation-allocation.md) · [All verification families](docs/assurance/verification-families.md) · [Historical dispositions](docs/assurance/historical-findings.md)
