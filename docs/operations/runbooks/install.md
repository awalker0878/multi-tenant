# Install an environment

Procedure ID: OPS-INSTALL. Owner: SRE; contributors: IAM/security, context owners, delivery and inventory. Requirements: R02–R04/R08/R29–R32/R35. Delivery: P01.02/P01.05/P01.06, P10.05; campaign Q09. Applies to a clean environment using one approved release manifest and environment BOM.

## Inputs and prerequisites

- Record environment/trust boundary, installation/change reference, release manifest/digest, configuration revision, installation operator and dependency owners.
- Resolve runtime, component versions, network flows, identity/key custody and restricted-network mode through the [decision register](../../decisions/decision-register.md). Use the [BOM](../configuration-and-bom.md) for exact values and secret references.
- Confirm required infrastructure, failure domains, capacity, DNS/time/PKI, registry/mirrors, durable storage, backup targets and independent recovery access. The installation must not depend on broad native platform credentials.
- Supply release-specific deployment bindings and health checks that were exercised with the selected runtime. They must identify the operation, artifact, identity and expected output; do not translate these steps into guessed commands.
- Establish an installation evidence destination independent of components that are not yet running. Reconcile it into assurance once the service is available.

Keep new native admission disabled and mutating worker pools isolated throughout D01–D07. Readiness includes denied paths and safe failure, not just a successful connection.

## Installation sequence

| Stage | Operator action | Expected observation and hold condition |
| --- | --- | --- |
| D01 Infrastructure | Verify selected runtime/failure domains, DNS/time, trust roots, registries, storage and allowed management/egress flows | Exact owners/versions/capacity recorded; required reachable paths and denied unauthorized paths observed. Stop on trust, residency, time or resource mismatch |
| D02 Persistence | Install pinned context-owned databases, workflow persistence/server, broker and protected evidence storage with separate runtime/migrator roles | Dependency health and durable storage confirmed; cross-context/runtime-admin attempts denied. Stop on missing encryption/key, role boundary or recovery dependency |
| D02 Recovery check | Back up and restore synthetic dependency records and evidence bytes in isolation using the selected mechanism | Identity/count/digest comparisons and key access succeed. Backup creation alone does not pass this step |
| D03 Services | Run controlled migrations under the dedicated change identity; deploy governance, catalogue, inventory, planning, lifecycle, assurance and console using dependency/readiness order | Running digests match manifest; service auth and compatible contracts work; unavailable mandatory dependencies fail readiness or affected operations safely |
| D04 Telemetry | Bind logs/metrics/traces/audit and alert routing; exercise a synthetic journey and test alert | Correlated redacted records reach permitted sinks; alert is delivered and acknowledged; missing collection is observable |
| D05 Site trust | Register approved site/read-only pool identity and endpoint constraints through [commissioning](commissioning.md) | Handshake, trust denial, revocation and read-only scope demonstrated; registration alone enables no mutation |
| D06 Initial records | Bootstrap explicitly verified administrator, disable/restrict bootstrap path, load reviewed profiles/policies and create authorized fixture/first-tenant records | Attributable grants and revisions; separate author/reviewer/operator behavior; no baked-in password or automatic qualified capability |
| D07 Read-only acceptance | Discover permitted endpoints; inspect coverage/freshness; exercise application intent, assessment and plan review with required authority | Unknown or stale facts remain visible; denied tenant/native paths stay denied; no native mutation is dispatched |

D03 service deployment order follows the selected readiness dependencies rather than a fabricated startup sequence. Services may start without downstream readiness, but no deployment may report an operable journey until its actual required dependencies pass. Domain operations still enforce their own failure rules.

## Laravel service acceptance at D03

Apply the [Laravel runtime contract](../deployment-model.md) and [data/messaging standard](../../engineering/data-and-messaging.md). The release-specific binding must provide the selected commands and process manager settings for these checks; the framework commands referenced by those standards are not a complete installation script.

1. Verify each service's runtime and PHP extensions against its dependency lock/BOM. Confirm separate runtime/migration credentials and deny cross-context data access.
2. Provision its persistent application encryption key through the approved secret mechanism. All replicas use the correct service/environment key reference; restarts do not generate new keys. Check recovery custody without copying key values into evidence.
3. Supply deployment configuration before generating the protected configuration cache. Inspect the effective non-secret settings, ingress document root, production debug behavior and permitted writable paths. Confirm the image/build artifacts contain no environment secrets or resolved configuration cache.
4. Run one controlled migration job and verify the expected schema/migration state independently of exit code. Check that application replicas lack migration privileges and do not migrate concurrently at startup.
5. Verify startup, liveness and readiness as separate signals. An unavailable shared dependency must produce the documented traffic/admission hold without a fleet-wide restart loop. A successful default health response is insufficient for this step.
6. Start only the selected context-local queues and scheduler owner. Confirm queue/worker deadline ordering, retry/failed-job policy, durable outbox recovery and named scheduled task ownership. Keep these mechanisms separate from Temporal/native mutation authority.
7. Execute synthetic jobs for alternating tenants in the same worker, including a failure, and verify context cleanup. Exercise controlled process replacement and ensure only the intended scheduler remains active.

Attach actual observations to D03/D04 evidence with secret values redacted. A missing setting, unexplained duplicate execution, key mismatch or tenant context leak holds service acceptance.

## Native qualification and pilot boundary

After D07, record installation acceptance scope separately from native support. D08 requires P06 safety controls, commissioned isolated endpoints, explicit campaign authority, compatible artifacts, recovery/evidence readiness and the appropriate qualification lane. Ordinary operational use additionally requires current exact-tuple support and plan-specific authority. A successful installation cannot supply those decisions.

D09 pilot activation follows qualified supported scope, approved tenant plan/change conditions and receiving application/security/service-owner validation. Use lifecycle to admit the exact plan; the installer must not bypass workflow authority to demonstrate an effect manually.

## Failure and safe recovery

| Failure | Required response |
| --- | --- |
| Artifact/configuration mismatch | Halt stage; preserve manifest and observed digest; revalidate via [promotion](promote-release.md) before replacing anything |
| Missing identity/key/dependency | Keep readiness/admission held; correct the owner-controlled prerequisite; never inject a broad administrator credential |
| Partial migration/schema change | Capture actual schema/migration journal; follow its forward/rollback compatibility instructions; do not rerun destructive steps blindly |
| Dependency restore mismatch | Preserve failed restore evidence and original backup; use [dependency recovery](dependency-recovery.md); do not bootstrap fresh empty state over it |
| Worker unexpectedly gains native write access | Isolate/fence affected path, notify security/platform owner and reconcile any dispatched effect before continuing |
| D07 discovery incomplete | Record unknown/stale scope and collector coverage; correct access/budget or limit accepted scope explicitly |

If initial bootstrap partially succeeds, observe whether the intended administrative grant exists and whether the bootstrap mechanism remains usable. Reconcile the recorded operation; do not create a second unrestricted administrator simply because the response was lost.

## Verification and handover

An independent operator verifies component/BOM identities, allowed and denied API/database/network access, fixture tenant isolation, evidence object integrity, safe restart and alert receipt. Check that native admission remains disabled unless separately enabled under D08 authority. Verify protected backup and trust recovery access from the intended recovery location.

Record elapsed install/recovery times, configuration/secret reference revisions, migration receipts, dependency restore results, synthetic journey/alert evidence, remaining limitations and the exact stage achieved. Save actual commands/API bindings and redacted outputs with the exercise record. Do not report native provisioning, application migration or production readiness from these installation checks.
