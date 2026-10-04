# Release manifest contract

Owner: delivery lead. Consumers: deployment automation, service operators, assurance and support. Related decisions: ADR-003, ADR-005, ADR-012, ADR-022 and ADR-023.

The manifest identifies a reproducible product release and its evaluated scope. Its human release name is a label; immutable artifact and configuration identities are the binding references.

| Field family | Required content |
| --- | --- |
| Identity | Unique release/candidate ID, repository revision, build provenance, manifest digest and signature identity |
| Services | Console and six domain-service image digests, configuration schema versions and required runtime dependencies |
| Context and code controls | Context-map revision/digest, service source paths and context IDs, language-analysis/configuration identities and coverage, required-check/review evidence and scoped unexpired exception references |
| Workers | Workflow, discovery, infrastructure, guest, shared-service and data-mover artifact identities; permitted routing/version combinations |
| Automation | Terraform/provider/module and Ansible/role identities, schema/input versions and approved ownership model |
| Contracts | HTTP/event/schema versions, client compatibility and canonicalization/digest version |
| Persistence | Service migration versions, compatible previous state, expand/contract stages and downgrade limits |
| Deployment | Dependency/BOM identities, environment profile, configuration digests, network/trust assumptions and artifact-mirror requirements |
| Security | SBOM/provenance references, signature verification policy, security review reference and unresolved accepted limitations |
| Qualification | Exact support-record IDs, affected campaign/evidence references, expiry/revocation and reuse review |
| Operations | Install/upgrade/recovery runbook revisions, accepted objectives, support ownership and readiness references |
| Acceptance | G10/G11 review references, pilot scope/outcomes and publication authority |

Do not include private keys, passwords, tokens, live inventory or sensitive evidence bytes. Refer to environment secrets and protected records through scoped identities. Configuration needed for reproducibility must be distinguished from secret values.

## Validation rules

Every referenced artifact must exist, match its digest and satisfy signature/provenance policy. The dependency closure includes offline installation dependencies when that mode is in scope. Schemas, migrations and mixed worker/API versions must be compatible under the documented upgrade sequence.

Reconcile each service image with the owning context and its declared source/package build inputs. The [code-control review](../engineering/code-control.md) must apply to that exact source/configuration revision. A passed structural smoke check cannot stand in for required PHP/Python/frontend analysis or verified merge/release policy; missing analysis and expired exceptions remain blocking findings.

Each advertised support row must refer to the actual candidate artifacts and applicable qualification evidence or an explicit unaffected-evidence review. Expired or revoked support cannot be restored by publishing the same artifact under a new release name.

The manifest is immutable after acceptance. Any change to an artifact, compatibility promise, support scope or accepted assumption creates a new candidate or controlled superseding record. Retain links to predecessors and the scope of their supersession.
