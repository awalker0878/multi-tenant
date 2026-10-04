# Configuration and environment bill of materials

Owners: SRE and delivery for environment/release records; each context owner for its settings; security for trust and custody. Scope: R02/R08/R29–R32/R34/R35; P01.02/P01.04–P01.06 and P10. The [deployment model](deployment-model.md) owns placement and logical network flows.

## Record boundaries

Keep three records linked by immutable references: a release manifest identifies deployable artifacts; an environment BOM identifies what is installed; domain records describe tenant intent and authority through owner APIs. Deployment values must not become a second database of grants, approvals, workloads or qualification decisions.

Repository configuration contains schemas, non-sensitive defaults and synthetic examples. Restricted environment records contain real endpoints, identities, network approvals, recovery locations and permitted secret references. Secrets and live Terraform state are not repository configuration. Separate a non-secret configuration digest from secret version/reference attestations so secret material is never hashed into published evidence accidentally.

## Minimum release and environment records

| Record | Required fields | Validation rule |
| --- | --- | --- |
| Release identity | Source revision; release-manifest revision/digest; build provenance; signature and verifier policy | Every image/package resolves to immutable bytes from the recorded source/build |
| Component | Context/pool/dependency ID, owner, runtime/product version, image/package digest, SBOM reference, dependencies | No floating version/tag as installed identity; dependency closure resolves in target network mode |
| Environment | Environment ID, trust/residency boundary, runtime/failure domains, topology revision, permitted operating mode | Development/integration/native qualification/production authorities remain distinct |
| Persistence | Context owner, DB/object/state/workflow store, runtime/migrator identities, encryption/key references, backup/recovery group | No shared cross-context runtime owner; recovery dependencies and keys available |
| Service deployment | Artifact/configuration revisions, resource limits, replicas/placement policy, health/readiness checks, API compatibility | Required settings validated before readiness; deployed digest matches manifest |
| Worker pool | Site/pool identity, artifact/SDK/adapter revisions, allowed endpoints/actions, queues, secret refs and limits | Queue membership never substitutes for admitted operation scope |
| Network flow | Initiator, receiver, exact protocol/port, identity, permitted data, trust root, timeout, budget, owner and evidence | Deny unused flows; exercise allowed and denied paths on the selected runtime |
| Native tuple | Platform/API/backend/feature/entitlement versions; network/storage/guest profiles; site revision and owners | Compare against the exact support claim; a vendor label is insufficient |
| Operations | Telemetry/alert routes, retention, maintenance mode, backup checkpoints, recovery and escalation owners | Routing, restore and safe restart exercised against this configuration |

Represent references as stable identifiers with revisions, for example `environment-integration-a`, `site-lab-a` and `config-revision-17` in synthetic fixtures. Actual IDs are recorded by implementation schemas; these examples prescribe no executable API payload.

## Configuration ownership and precedence

1. Service schemas define required names, types, bounds and secure defaults. Reject unknown mandatory-option combinations and contradictory modes.
2. Reviewed environment values select topology, budgets, dependencies and permitted operations. Record the exact rendered non-secret revision before deployment.
3. Approved secret/key references resolve through the selected custody system at runtime. Missing/expired material fails readiness or the affected privileged action; no fallback administrator secret.
4. Tenant intent and grants resolve from owning services under authorization. A manifest cannot override them.
5. Record the effective configuration identity in health/diagnostic output without returning secrets. Detect unmanaged drift against that identity.

Choose one precedence order in implementation and test it for local, integration and operated deployments. Never let an undocumented environment variable silently override an approved endpoint, trust root or native-enable switch.

## Component decisions and compatibility

Use [ADR-003/006–012/016/017/019/020](../decisions/decision-register.md) to select runtime patches, persistence/workflow/broker versions, trust, runtime/CNI, IaC backend and deployment modes. Directed frontend majors remain constraints; accepted exact locks and build evidence establish a usable combination. Record minimum/maximum supported dependency and mixed-service/worker versions in each release.

The BOM also includes operating dependencies: DNS/time/PKI, registry/mirrors, backup and recovery tools, provider plugins, guest images, conversion utilities and any required native/service API entitlement. A connected installation's incidental package cache is not a reproducible restricted-network supply.

## Change procedure

| Step | Owner action | Required outcome |
| --- | --- | --- |
| 1. Describe | Component owner identifies changed values, affected boundaries, consumers and rollback limits | Traceable requirement/package and decision impact |
| 2. Assess | Security/SRE/lifecycle assess authorization, state, native tuple and qualification impact | Explicit affected claims and required tests; no blanket evidence carry-over |
| 3. Build and validate | Delivery produces signed artifacts and schema-valid rendered config; compares manifest/BOM | Deterministic diff free of secrets and unrelated scope |
| 4. Exercise | Independent operator uses applicable install/upgrade/recovery procedure in target-like environment | Actual observations tied to old/new revisions and limits |
| 5. Apply and observe | Authorized operator applies the reviewed change with admission/worker controls | Running identities/digests match; health, denials and durable work behave correctly |
| 6. Record | SRE records as-built revision and evidence; owners review remaining holds | Current BOM and operational record agree |

Do not automatically repair drift affecting native ownership, identity, or a running migration. First determine whether the difference reflects an authorized external change and reconcile the authoritative owner.

## Restore and retirement

Back up non-secret configuration, manifest/signature policy and protected secret/key references with their dependency order. Preserve decryption material under the custody plan for the whole required data-retention period. Restoring configuration does not restore current approval or resurrect valid execution leases.

Before removing a component, enumerate active workflows, object/data retention, replay consumers, identity/key dependencies and recovery obligations. Remove obsolete secret references and flows only after dependent work is completed or safely migrated. Record independent observations of retired access and retained recovery material.

Gate evidence comprises installed BOM export, rendered configuration digest, trust/role/network negative checks, artifact verification, measured sizing and restore results. File presence or a successful schema parse establishes none of these operating outcomes.
