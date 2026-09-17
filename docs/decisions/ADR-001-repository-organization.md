# ADR-001: infrastructure-first repository and non-deploying verification

Status: proposed repository implementation, 17 September 2026.

The reference architecture defines infrastructure and boundaries. Engineering translates those decisions into supported native combinations. Terraform and Ansible implement or verify selected responsibilities; this repository is not a custom hosting-controller application.

## Organization

- `docs/architecture`, `docs/engineering`, `docs/implementation`: navigation, active decisions and procedures.
- `reference/`: versioned document families; preserve intra-family relative links and distinguish historical material from current source.
- `terraform/modules` and `terraform/roots`: separate native resource scopes, retaining Increment 04 paths to avoid needless source/test changes.
- `ansible`: separately owned roles, safe inventories and playbooks. Initial role is localhost-only manifest validation, not native provisioning.
- `tools`, `tests`, `lab`, `examples`: implementation utilities, automated observations and inert fixtures.
- `sources`: import lineage, artifact catalogue and unresolved implementation work.
- `evidence/baseline`: historical authoring results, not CI success for a changed commit.
- `build`: ignored current execution output, uploaded as short-retention private Actions artifacts.

## Verification boundaries

Regular CI has repository-read permission and no infrastructure credentials. Terraform initializes plugins with backend disabled, validates actual schemas and uses only mocked plan tests. Ansible contacts localhost only. No apply, destroy, native DNS update, target observation or activation is a CI operation.

A one-time import workflow temporarily has contents-write permission only in its source-import job to decode checksum-bound source into normal reviewable files. Test jobs retain read-only permission. The transport is not a production dependency and will be removed after import.

Original Office artifact publication is tracked separately from text/source import. An inventory or a successful test must not be used to claim that a missing binary was uploaded. Source checksums establish byte lineage, not authenticity or architecture approval.
