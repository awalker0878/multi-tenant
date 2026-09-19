# Test strategy and actual evidence levels

The active reference describes the infrastructure; the tests evaluate specific code
and observations, not organizational authorization. [Terraform guidance](../terraform/README.md)
and [Ansible boundaries](../ansible/README.md) describe the two execution surfaces.

## Toolchain and commands

Use Python 3.13 for parity with the authoring environment. Install dependencies from
an approved source using `requirements-repository.txt` for local checks or
`requirements-dev.txt` for the Ansible engine. CI selects Terraform **1.13.5** and
Ansible Core **2.19.7** as explicit candidate bootstrap versions, not as a statement
that they are the newest releases or the approved production combination.

```sh
python -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements-dev.txt
python scripts/check_repository.py
python tools/check_local.py
python scripts/verify_ansible.py
python tools/verify_terraform.py --mock-tests
```

| Gate | What actually executes | What a pass does not establish |
|---|---|---|
| Repository | Source shapes, common-secret patterns, links, frozen bytes, mock-test guard, YAML structure | Engine parsing, exhaustive security review, native compatibility |
| Local regressions | Python functions and disposable loopback HTTPS/DNS/TLS fixtures; route-model cases | Native product behaviour, routed IPv6 or full ZIP qualification |
| Ansible engine | Actual syntax checks, local template/file tasks, second-run zero-change, check-mode non-mutation and negative fixtures | Remote host configuration, switch support, native contacts |
| Terraform engine | Backend-disabled init/validate, real plugin schemas and plan-only provider mocks on ten module/root pairs | Live provider API support, infrastructure conformance, safe production apply |
| Routed-family laboratory | Separate fixed IPv4 and IPv6 namespace packet/TLS campaigns, plus exact-source report completeness | Native IPv6, vendor HA, production DNS/PKI or authorization |
| Other manual labs | Additional fixed disposable protocol campaigns | Native product qualification or authorization |
| Native qualification | Separate approved target and engineering procedure | Not executed or automated by repository CI |

`make test` means the first two gates only. `make test-all` additionally requires both
engines and fails if either is unavailable. Missing tools never return a passing engine
result. YAML parsing and pure Jinja rendering must not be reported as Ansible syntax
or idempotence tests. Terraform test mocks still require real installed provider
schemas; Python source checks do not replace them. [R1; R2]

## Terraform trust and isolation

Initialization downloads and executes provider packages. Use trusted mirrors,
reviewed version pins and real generated checksums. The verifier removes ambient
platform credentials, copies the source to a temporary directory, disables backend
initialization and never invokes a native apply or a live plan. Module tests must
explicitly mock all required providers and use `command = plan`; real-provider blocks,
provider remapping and alternate module sources are refused by the guard.

The guard is lexical, not a full HCL parser or a sandbox for malicious source.
Review all resources, providers and tests before execution. Engine/schema diagnostics
are required before changing the candidate status. Generated locks and schema exports
are captured under `build/reports/`; locks must be reviewed and committed to their
corresponding module/root locations through a separate change. Do not invent them.

## Ansible ownership

No Ansible source existed in the imported increment. These new roles use only core
modules. The staging role writes two reference files in a caller-marked local directory;
it cannot create a native VM, route or firewall policy. The other role invokes only the
fixed native reader's input-validation mode, without contact flags. Defaults opt out.

The engine verifier executes first-run staging, repeat staging, check-mode drift
simulation, disabled and foreign-owner rejection and no-contact reader validation.
Check mode is a simulation; the verifier additionally compares staged bytes before and
afterwards. Unsupported/skipped actions are not real observations. [R2; R3]

## CI and cost/safety boundaries

The regular workflow has independent repository, Terraform and Ansible jobs, using
GitHub-hosted Ubuntu 24.04. The routed-family laboratory runs on pull requests, `main` pushes and manual dispatch.
Other retained laboratory workflows keep their separate manual-dispatch scope.
All actions are pinned to observed full commit IDs, repository permissions are read-only,
checkout credentials are not persisted and no native secrets or deploy job are used.
The original import did not execute the workflows. Subsequent runs and the current
change are tracked by their exact Git revision and Actions artifacts, not by treating
that historical delivery note as current status.
Jobs may consume your private repository's Actions allowance when pushed or dispatched.

Do not run unreviewed pull-request code on privileged self-hosted infrastructure.
No job is allowed to use `pull_request_target`, native credentials or an environment
with access to production systems. Package trust and dependency updates still require
review; direct version pins are not a complete transitive supply-chain lock. [R4]

## Reports and preservation

Current reruns write to ignored `build/reports/`. Imported `quality/` reports remain
historical, including their original failures and earlier test counts. The sanitized
repository-release snapshot is under [evidence/repository-import](../evidence/repository-import/README.md).
No current check relabels a frozen Word document or old report as newly approved.
Reference Word/Excel bytes are preserved, not edited, re-rendered or recalculated.

## Primary implementation references

- R1: [Terraform provider mocks](https://developer.hashicorp.com/terraform/language/tests/mocking).
- R2: [Ansible check and diff mode](https://docs.ansible.com/projects/ansible/latest/playbook_guide/playbooks_checkmode.html).
- R3: [Ansible template module](https://docs.ansible.com/projects/ansible/latest/collections/ansible/builtin/template_module.html).
- R4: [GitHub secure workflow guidance](https://docs.github.com/en/actions/reference/security/secure-use).

Reviewed for repository design; exact installed component qualification remains separate.


## Documentation migration gate

Run `python scripts/check_documentation.py` to verify full source conversion, table and field retention, diagram bytes, local Markdown anchors and source-backed ADRs. This does not rewrite documents, fetch sources, execute Terraform/Ansible, contact a target, or issue architecture acceptance. Reports are written only below `build/reports/`.


## Completion-corrective release verification

`python tools/check_release.py` checks a clean current Git checkout, not the historical file list. Exported releases require their explicit snapshot manifest. `python scripts/check_documentation.py` adds independently parsed code/tab/break fidelity, ordered table cells, exact ADR rendering/lifecycle, maintained design records and complete test/allocation indexes. `tools/verify_terraform.py --mock-tests` exports schemas from backend-free modules only, validates roots with `-backend=false`, and validates committed locks read-only. Passing that job does not contact native services. Ansible negative checks require genuine failed local assertions, not timeouts. Current CI source hashes and run identity are recorded in reports.

## Routed IPv6 local packet extension

[Run the fixed IPv6 campaign](implementation/routed-ipv6-lab.md) after the [engineering scope](engineering/routed-ipv6-qualification.md) is understood. `python lab/run_ipv6_lab.py --execute` requires nftables and authorized namespace/sysctl capabilities and produces a new private `build/reports/local_ipv6_packet_lab.json`. The hosted disposable lab job supplies explicit privilege; it does not disable host security settings. The ordinary unit suite covers its message/guard/source logic separately. A blocked runtime is nonzero, not a skipped pass, and native IPv6 remains unqualified.

## Known-task-tree readback campaign

`python lab/run_task_tree_lab.py --execute` runs 18 fixed loopback-HTTPS readback/recovery cases, including the actual CLI and private report handling. `tests/test_nutanix_task_tree.py` adds the overlapping unit and negative cases. Task/resource bodies and external control records are scripted; no native target, task submission/cancellation or real writer fencing is involved. See the [candidate profile and limits](engineering/nutanix-task-tree-readback.md). The repository CI job executes this campaign and uploads its exact-source report alongside other local results.

## Platform capability registry

`python scripts/check_platform_capabilities.py` validates the machine-readable engineering registry without contacting a platform or performing placement. Repository code, provider locks, documentation and local fixtures may support `CANDIDATE_SOURCE` or `LOCAL_FIXTURE_ONLY` states, but only a selected installed tuple with separately controlled native evidence can become `NATIVE_QUALIFIED`. The current registry intentionally has zero production-eligible platforms.


## Pre-placement platform-family eligibility

`python scripts/check_platform_family_eligibility.py examples/pre_placement_capability_request.json.example --expected-status HOLD_NO_NATIVE_QUALIFIED_PLATFORM` verifies that the current WSD capability precheck remains fail-closed because no platform capability is natively qualified. Without `--expected-status`, a held request exits nonzero. This check does not validate requester authority, site/cell/pool selection, quota, surviving capacity, storage/key/recovery compatibility, native placement or production activation.


## Native PlatformProfile qualification dossier

`python scripts/check_platform_qualification.py` validates the active exact-tuple qualification index, including owners, applicable tests, tested limits, evidence hashes/freshness and approval validity. The current index is intentionally empty. `scripts/check_platform_capabilities.py` then refuses any future `NATIVE_QUALIFIED` claim that lacks a current matching dossier for the same tuple/capability/evidence scope. Neither check contacts a platform, selects a site, reserves capacity, applies infrastructure or issues production authorization.


## Site/service-class capacity eligibility

`python scripts/check_site_service_capacity.py` validates current commissioned site/cell/service-class envelopes against exact-tuple qualification records, approved profile references, failure-model evidence, owners and time-bounded multi-resource capacity. `python scripts/check_site_service_eligibility.py examples/site_service_capacity_request.json.example --expected-status HOLD_NO_ELIGIBLE_SITE_SERVICE_ENVELOPE` confirms the current empty inventory remains fail-closed. The checker compares surviving capacity, operational reserve, existing commitments, unavailable capacity and supplied quota headroom, but never creates a reservation or contacts IPAM/native platforms.


## Reservation preflight and exported records

`python scripts/check_reservation_records.py --as-of 2026-09-18T18:00:00Z` validates exported reservation evidence without becoming the authoritative reservation database. `python scripts/check_reservation_preflight.py examples/reservation_intent.json.example --as-of 2026-09-18T18:00:00Z --expected-status HOLD_ENVELOPE_NOT_CURRENTLY_ELIGIBLE` confirms the current example remains held. The preflight checks immutable reservation/operation IDs, generation, exact capacity-demand binding, owner/expiry, dependency operation identities and existing conflict/uncertain outcomes. It cannot create, extend, consume or release reservations, allocate addresses, apply infrastructure or activate service.


## Authoritative IPAM allocation handoff

`python scripts/check_ipam_allocation_records.py --as-of 2026-09-18T18:00:00Z` validates exported authoritative-IPAM lifecycle evidence without storing actual allocation values. `python scripts/check_ipam_allocation_preflight.py examples/ipam_allocation_intent.json.example --as-of 2026-09-18T18:00:00Z --expected-status HOLD_PARENT_RESERVATION_NOT_HELD` asserts the current fail-closed handoff. Tests cover stable operation identity, conflicts, uncertain outcomes, confirmation after realization, release cleanup, reuse quarantine, overlap-exception references and rejection of caller-supplied address fields. Neither check reserves/releases addresses or writes DNS.


## Authoritative DNS registration handoff

`python scripts/check_dns_registration_records.py --as-of 2026-09-18T18:00:00Z` validates exported DNS registration lifecycle evidence without storing actual names or record values. `python scripts/check_dns_registration_preflight.py examples/dns_registration_intent.json.example --as-of 2026-09-18T18:00:00Z --expected-status HOLD_IPAM_ALLOCATION_NOT_CONFIRMED` verifies that DNS remains held until authoritative IPAM is confirmed. These checks do not invoke `tools/dns_change.py`, contact DNS, broaden update ACLs or establish recursive/secondary propagation unless independently evidenced.


## Backup protection and isolated-restore assurance

`python scripts/check_backup_restore_assurance.py --as-of 2026-09-18T19:00:00Z` validates exported BackupPolicy/protected-copy/isolated-restore evidence without contacting backup, storage or key services. `python scripts/check_backup_restore_readiness.py examples/backup_restore_readiness_intent.json.example --as-of 2026-09-18T19:00:00Z --expected-status HOLD_NO_CURRENT_BACKUP_ASSURANCE` verifies the current empty assurance index remains fail-closed. A backup job alone is never accepted as restore assurance, and all backup/restore/key/reconnect/apply/activation authority flags remain false.

## Control inheritance and external-dependency assurance

`python scripts/check_control_inheritance_assurance.py --as-of 2026-09-18T20:00:00Z` validates exported per-control allocation, inherited-service applicability, external-interface evidence and residual-gap decisions. `python scripts/check_control_inheritance_readiness.py examples/control_inheritance_readiness_intent.json.example --as-of 2026-09-18T20:00:00Z --expected-status HOLD_NO_CURRENT_CONTROL_ALLOCATION` verifies the current empty assurance index remains fail-closed. Tests require all six QUAL §6 interfaces, current evidence, explicit inherited-service references, and attributable decisions for accepted gaps while all control-selection/risk-acceptance/authorization/apply/activation authority flags remain false.

## Operational handover and incident-readiness assurance

`python scripts/check_operational_handover_assurance.py --as-of 2026-09-18T21:00:00Z` validates exported handover ownership, decision authority, privileged-access review, monitoring evidence, residual obligations and scoped incident-exercise evidence. `python scripts/check_operational_handover_readiness.py examples/operational_handover_readiness_intent.json.example --as-of 2026-09-18T21:00:00Z --expected-status HOLD_NO_CURRENT_OPERATIONAL_HANDOVER` verifies the current empty assurance index remains fail-closed. Tests require explicit containment release, emergency-change reconciliation and no unresolved stale privileged grants while all live operations/apply/activation authority flags remain false.

## Version, source provenance and lifecycle assurance

`python scripts/check_version_source_provenance.py --as-of 2026-09-18T22:00:00Z` validates exact product/API/provider/hardware/licence tuples, mandatory current source-review kinds, compatibility evidence and support lifecycle. `python scripts/check_version_source_readiness.py examples/version_source_readiness_intent.json.example --as-of 2026-09-18T22:00:00Z --expected-status HOLD_NO_CURRENT_VERSION_SOURCE_PROVENANCE` verifies the current empty provenance index remains fail-closed. Native qualification tests also prove that a CURRENT_APPROVED dossier is rejected unless the same exact tuple has one matching CURRENT_SUPPORTED provenance record.

## Bounded extension adoption and qualification assurance

`python scripts/check_extension_adoption_assurance.py --as-of 2026-09-18T21:00:00Z` validates extension-only scope, complete topology/lifecycle design, all seven qualification dimensions, extension-kind-specific evidence, unsupported-capability disclosure and residual-gap state. `python scripts/check_extension_adoption_readiness.py examples/extension_adoption_readiness_intent.json.example --as-of 2026-09-18T21:00:00Z --expected-status HOLD_NO_CURRENT_EXTENSION_ADOPTION` verifies the empty extension index remains fail-closed. Tests prove namespace-only and physical-VRF-only evidence is insufficient and that no result grants base-service, cluster, device, physical-fabric, apply or activation authority.

## Knowledge maintenance and release-integrity assurance

`python scripts/check_knowledge_maintenance_assurance.py --as-of 2026-09-18T21:05:00Z` validates the complete eight-topic primary-home map, stable parent/home anchors and any exported release-maintenance record. `python scripts/check_knowledge_maintenance_readiness.py examples/knowledge_maintenance_readiness_intent.json.example --as-of 2026-09-18T21:05:00Z --expected-status HOLD_NO_CURRENT_RELEASE_MAINTENANCE` verifies the current empty maintenance index remains fail-closed. Tests cover duplicate primary homes, bad anchors, incomplete version sets, stale cadence/validation, open drift conflicts, affected-topic ripple review and exact revision matching while all publication/change/architecture/apply/activation authority flags remain false.

## Security-edge and ZIP assurance

`python scripts/check_security_edge_zip_assurance.py --as-of 2026-09-18T21:45:00Z` validates exact pairwise boundary scope, dedicated versus distributed/shared realization, mandatory security functions, native path/bypass/policy evidence, failure behavior, capacity and residual gaps. `python scripts/check_security_edge_zip_readiness.py examples/security_edge_zip_readiness_intent.json.example --as-of 2026-09-18T21:45:00Z --expected-status HOLD_NO_CURRENT_SECURITY_EDGE_ZIP_ASSURANCE` verifies the active empty ZIP index remains fail-closed. Tests prove a route/quarantine object is insufficient, distributed/shared realizations require equivalent-outcome evidence, unsupported mandatory functions are ineligible, and every mutation/apply/activation authority flag remains false.

## Native readback, writer-fencing and reconciliation assurance

`python scripts/check_native_reconciliation_assurance.py --as-of 2026-09-18T22:05:00Z` validates exact installed-interface applicability, readback digests/outcomes, stable samples, scoped writer fencing, containment state, operation generation and attributable reconciliation decisions. `python scripts/check_native_reconciliation_readiness.py examples/native_reconciliation_readiness_intent.json.example --as-of 2026-09-18T22:05:00Z --expected-status HOLD_NO_CURRENT_NATIVE_RECONCILIATION` verifies the active empty reconciliation index remains fail-closed. Tests cover matched readback without fencing, stale observations, active containment, pending/failed native outcomes, stale decision chronology, generation mismatch and open gaps while task-list/cancel, containment-release, state-import, repair/delete/apply/activation authority flags remain false.

## Native IPv6 and address-family assurance

`python scripts/check_native_ipv6_assurance.py --as-of 2026-09-18T22:05:00Z` validates exact native family scope, supported addressing modes, local IPv6 protocols, routing/security parity, PMTU/MTU, shared-service dependencies, failure/recovery and current native qualification. `python scripts/check_native_ipv6_readiness.py examples/native_ipv6_readiness_intent.json.example --as-of 2026-09-18T22:05:00Z --expected-status HOLD_NO_CURRENT_NATIVE_IPV6_ASSURANCE` verifies the active empty native-family index remains fail-closed. Tests distinguish IPv6-only from dual-stack, require no hidden IPv4 fallback or an independent IPv4 campaign respectively, and keep service-offer/address/route/policy/MTU/apply/activation authority flags false.

## Production activation and initial-readiness assurance

`python scripts/check_production_activation_assurance.py --as-of 2026-09-18T22:05:00Z` validates exact activation scope, G0/G1/G2 prerequisite references, applicable initial G4 readiness, operating-authority validity, reversible exposure/withdrawal preparation and post-activation evidence. `python scripts/check_production_activation_readiness.py examples/production_activation_readiness_intent.json.example --as-of 2026-09-18T22:05:00Z --expected-status HOLD_NO_CURRENT_PRODUCTION_ACTIVATION_ASSURANCE` verifies the active empty activation index remains fail-closed. Tests distinguish pre-activation readiness from current activated state, require post-activation observations after the activation receipt, and force failed/unknown live verification into withdrawal-required while all exposure/apply/activation authority flags remain false.

## Identity, certificate and cryptographic trust assurance

`python scripts/check_identity_crypto_assurance.py --as-of 2026-09-18T23:00:00Z` validates identity scope, privileged/emergency access, revocation, certificate lifecycle, separated key authorities, retained-data-aware destruction, KMS/trust outage behavior, independent recovery and crypto-agility evidence. `python scripts/check_identity_crypto_readiness.py examples/identity_crypto_readiness_intent.json.example --as-of 2026-09-18T23:00:00Z --expected-status HOLD_NO_CURRENT_IDENTITY_CRYPTO_ASSURANCE` verifies the active empty trust index remains fail-closed. Tests reject collapsed key authorities, missing cached-token revocation proof, missing retained-data dependency, missing no-plaintext-fallback evidence, stale trust/outage evidence and open gaps while every credential/certificate/key/recovery/apply/activation authority flag remains false.
