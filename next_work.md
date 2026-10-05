# Next work — P01 delivery and runtime foundation

Active branch: `greenfield/enterprise-microservices-plan`. The requesting user approved advancement from G00 on 2026-10-04. The [accountable decision](docs/qualification/gate-reviews/g00-user-decision-2026-10-04.md) accepts the product, architecture and development baseline and explicitly carries remaining work to its receiving checkpoints. **P01 is the active phase; G01 is the next exit gate.** The [delivery register](docs/implementation/delivery-register.yaml) owns state; [progress](docs/implementation/progress.md) and [traceability](docs/implementation/traceability.md) are generated views.

## Current handoff

The resumed foundation increment is implemented and measured. Retain the existing local work and the source-bound records below; do not restart P00 or request the recorded G00 approval again. All seven principal applications and both selected workers have independent package/image foundations. Product readiness remains unavailable and workers consume no native tasks.

- **Contracts and messaging:** EV-P01-015 records 35 real PostgreSQL/RabbitMQ checks plus 16 shared PHP/Python event fixtures. Catalogue owns the atomic fact/outbox; Planning owns the atomic inbox/projection. Rollback, uncertain publication, crash/restart, duplicate delivery, tenant/actor binding, revision gaps and revoked publication are measured. The inbox now rejects an outer transaction before it can acknowledge uncommitted work. See [the messaging record](docs/implementation/p01-messaging.md).
- **HTTP contracts:** EV-P01-017 records all 28 PHP/Python fixtures, deterministic PHP/Python/TypeScript generation, model round trips, compilation and actual base/head version freezing. The diagnostic schema also matches 34 retained real responses from all seven applications. Business API conventions remain with their receiving feature packages. See [the HTTP contract record](docs/implementation/p01-http-contracts.md).
- **Console state and recovery:** EV-P01-016 records 149 Compose checks; EV-P01-018 records 166 Kubernetes checks. Encrypted sessions and tenant-scoped cache/locks survive database and application restart, including a replacement Pod. Invalid-key and failed-template recovery preserve the original state. Seven observed outages generate seven actual HTTPS receipts and matching acknowledgements at the synthetic receiver. See [shared state](docs/implementation/p01-console-shared-state.md) and [the operations runbook](docs/operations/runbooks/foundation-operations.md).
- **Earlier recovery evidence remains scoped:** EV-P01-013 retains 79 Permit Desk checks and two complete fresh-destination application/configuration restores. EV-P01-014 retains 40 stateful-dependency checks and 73 probe assertions, including one selected retained object restored to a fresh store with identical bytes and preserved retention. These remain distinct from product messaging and whole-store/operating qualification.

**Resumed P01.04 implementation and evidence are committed.** EV-P01-019–023
now register the actual review-policy, target-base probe, first and corrected
real-image scans, expanded control suite and repository secret scan. The
[artifact record](docs/implementation/p01-artifact-admission.md) and complete
[candidate manifest](release/p01-candidate-set.json) bind all nine components.
The [retention correction](docs/implementation/p01-evidence-retention.md) restored
18 original build logs without changing their recorded hashes; normal CI checks
retained byte integrity. Hosted run 37269433140 passed 59 control tests and scanned
all 9,766 tracked files with zero secret findings.

**The mandatory image admission check is FAILED.** After available fixes, all
nine images remain HELD: 80 blocking package/advisory matches per PHP image and
63 per Python image, with no fixed versions reported for those remaining matches.
The nine real-image campaigns passed their denial controls and unchanged-byte
quarantine transfers. Those successes do not admit a candidate. BL-P01-002 records
the remediation/requalification action; no waiver or scanner exclusion is applied.

**Next concrete actions:**

1. Resolve the exact retained image findings through pinned image remediation or
   a separately authorized, implemented risk-disposition policy; rerun affected
   image/runtime/security checks. Review the selected replacement against existing
   dependency and recovery evidence before reusing it.
2. Supply actual reviewer accounts and the administration/reporting path for
   BL-P01-001. The latest observation still shows `protected: false` and no rulesets.
   Activate the trusted default-branch hook, independently reported exact-PR
   decision, CODEOWNERS and required checks. The policy and prepared protection
   body are implemented candidates; the real enforcement is not installed.
3. Complete [OP01–OP07](release/operating-inputs.json) with actual runtime, registry,
   signer, trust/custody, reviewer, alert-response, recovery and support inputs.
   `python3 scripts/p01/admission/operating_inputs.py --require-complete` currently
   exits 1 with all seven records held. Ordinary schema validation passing does
   not satisfy that readiness check. Use those inputs for the affected operated
   integrations and remaining observability/operational review.
4. Examine [the criterion-by-criterion G01 assessment](docs/qualification/gate-reviews/g01-engineering-assessment-2026-10-05.md)
   and complete the receiving reviews. Preserve the measured synthetic scope,
   alert receiver limitation and remaining signal/resource/operating obligations.

**P01 work remains IN_PROGRESS, its verification roll-up is FAILED, and G01 is
NOT_REVIEWED.** No native effect, accepted RTO/RPO, operated trust, signed product
promotion or approval is inferred. The G00 approval remains accepted; do not ask
for it again or restart completed campaigns merely because this handoff resumed.

## Carried inputs and checkpoint ownership

The user's reviewer identity, G00 approval, baseline decision scope, migration direction/method and later checkpoints are recorded with immutable provenance in the [input record](docs/qualification/feasibility/input-record.md). Do not request that baseline approval again. Remaining unknown integration and native fields describe actual inputs still needed, not a reason to stop independent foundation work.

- Review the completed representative Permit Desk fixture and bounded Compose application/configuration recovery in P01.02/P01.06 before G01. Retain EV-P01-013 and the two original P00 database/attachment recovery boundaries with their distinct measured scopes.
- Review EV-P01-014 against G01.02/G01.05/G01.06 using the [dependency recovery runbook](docs/operations/runbooks/stateful-dependency-recovery.md). Its single-node synthetic probes and one selected object version do not establish product integration, whole-store recovery, HA, retention authority or operational acceptance.
- Obtain actual runtime, registry/signer, trust, network and dependency facts before the affected P01 integration. Local development artifacts do not establish operated deployment or promotion controls.
- Obtain installed VMware/OpenStack facts and permitted discovery scope before G04 work, and exact campaign effects/authority before G07/G08 native tests. Native qualifications remain unrun.
- Retain application outage/data objectives before P08, operating/retained-state obligations at P10/P11, and staffing/dependency dates when supplied. Approval does not invent these facts.

The original P00 task axes continue to show any carried incomplete work; the accountable G00 advancement decision is recorded separately. No unperformed check becomes a pass. Whole-VM conversion stays a separate P09 option; the approved first migration direction uses `application_rebuild_restore`.

Historical `implementation/all-waves` source is pinned at `a2963d8d43e25f08d70fbd99b0e5e19ab5c9828e` for reference. Current documentation, stack and ADR-024 take precedence; no historical implementation, passing result or authority transfers.

## Document each implementation increment

Use the [engineering standards](docs/engineering/README.md) and [coverage map](docs/engineering/coverage.md) when refining P00/P01. P00.03 has measured framework/tool locks, candidate image builds and schema/client tooling. Production adoption, complete service dependencies, managed-browser requirements and the actual mirror/trust path still need operating decisions and evidence. P01 must implement the documented structure, ownership, static analysis, contract and runtime checks before feature expansion; the written standards are not a completed foundation.

Apply the [pragmatic Laravel convention](docs/decisions/adr-024-pragmatic-laravel-domain-convention.md) within the [owning microservice](docs/architecture/context-code-structure.md): capability-based `app/Domain/` and `app/Application/`, Eloquent model behavior, Actions with `handle()`, external adapters in `app/Infrastructure/`, and normal Laravel entrypoints. Capabilities do not automatically become microservices. P00.02 aligns [the context registry](architecture/context-map.yaml) with that accepted convention and settles the remaining service decisions. P00.03 has verified the candidate architecture tools against actual spike locks and intentional violations; P01 must map these rules to the complete registered product source. P01.01/P01.04 implement PHP/Python/frontend dependency checks and actual ownership/review protection. The current registry/fixture workflow has explicit analysis limits; a source-empty pass does not close those packages.

For every coherent change, identify requirement/package IDs and the owning service. Update its behavior/contract specification and any affected ADR; put future API/event schemas in the contract tree, operational procedures under `docs/operations/runbooks/`, and qualification definitions/evidence indexes under `docs/qualification/`. The [documentation guide](docs/documentation-guide.md) defines the complete placement and naming rules.

Record actual source/artifact revisions, environment, positive/negative/recovery results, evidence identity and reviewer in `delivery-register.yaml`. Add a blocker with owner and unblock condition when necessary. Regenerate the progress/traceability views and validate references. Update this file to name the next concrete task, without copying a second status table here.

Use small coherent commits and the established GitHub connector workflow. No historical passing test, approval, credential, native support claim or operational acceptance transfers from the old programme. Scaffolding and design examples cannot be described as completed product behavior.
