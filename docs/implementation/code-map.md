# Architecture, decisions and implementation coverage

This map connects existing source code to the supplied design. It is a documentation integration, not new native functionality or a fresh deployment audit. Read the actual module/tool limitations and collect target-specific evidence before claiming conformance.

## Nutanix domains and staged workloads

Design: [RA §16](../architecture/reference/16-nutanix-hosting-stack-reference-realization.md) · [PBS §2](../engineering/platform-build/2-nutanix-commission-the-hosting-cell.md) · [PBS §3](../engineering/platform-build/3-nutanix-realize-a-tenant-and-its-workload-domains.md)

Decisions: [ADR-0024](../adr/0024-use-independent-nutanix-vpc-domain-realizations-with-qualified-handoffs.md) · [ADR-0008](../adr/0008-preserve-zone-aware-host-placement-and-disclose-every-shared-layer.md)

Implementation: [terraform/modules/nutanix-domain](../../terraform/modules/nutanix-domain) · [terraform/roots/nutanix-domain](../../terraform/roots/nutanix-domain) · [terraform/modules/nutanix-workload](../../terraform/modules/nutanix-workload) · [terraform/roots/nutanix-workload](../../terraform/roots/nutanix-workload)

Candidate native resources; actual Flow, placement, storage and external handoff behaviour requires target qualification.

## VMware/NSX domain, workload, route and quarantine

Design: [RA §17](../architecture/reference/17-vmware-and-nsx-hosting-stack-reference-realization.md) · [PBS §4](../engineering/platform-build/4-vmware-nsx-commission-transport-compute-and-edge-roles.md) · [PBS §5](../engineering/platform-build/5-vmware-nsx-bind-domain-workload-and-policy-lifecycles.md)

Decisions: [ADR-0025](../adr/0025-use-isolated-nsx-upstream-routing-rather-than-a-common-unrestricted-table.md) · [ADR-0015](../adr/0015-build-under-deny-and-verify-before-and-after-activation.md)

Implementation: [terraform/modules/nsx-domain](../../terraform/modules/nsx-domain) · [terraform/modules/vsphere-workload](../../terraform/modules/vsphere-workload) · [terraform/modules/nsx-route](../../terraform/modules/nsx-route) · [terraform/modules/nsx-gateway-quarantine](../../terraform/modules/nsx-gateway-quarantine)

These resource scopes do not supply a complete Tier-0/VRF/Edge construction or qualified end-to-end ZIP.

## OpenStack domain, workload and route

Design: [RA §18](../architecture/reference/18-openstack-hosting-stack-reference-realization.md) · [PBS §6](../engineering/platform-build/6-openstack-commission-a-distribution-not-a-generic-label.md) · [PBS §7](../engineering/platform-build/7-openstack-protect-mandatory-network-mutation.md)

Decisions: [ADR-0026](../adr/0026-choose-and-own-the-actual-openstack-backend-and-domain-boundaries.md) · [ADR-0023](../adr/0023-protect-mandatory-policy-and-identity-selectors-from-tenant-mutation.md)

Implementation: [terraform/modules/openstack-domain](../../terraform/modules/openstack-domain) · [terraform/modules/openstack-workload](../../terraform/modules/openstack-workload) · [terraform/modules/openstack-route](../../terraform/modules/openstack-route)

Backend, port-security authority, scheduler, boot behaviour, storage and effective paths remain native qualification work.

## Exact route engineering and review

Design: [RA §10](../architecture/reference/10-addressing-name-services-and-end-to-end-traffic.md) · [NBD §2](../engineering/network-boundaries/2-walk-f14-01-through-the-forward-and-reply-routes.md) · [WD §6](../solutions/internal-protected-workload/6-worked-forwarding-and-return-route-schedule.md)

Decisions: [ADR-0007](../adr/0007-allocate-isolated-domain-attachments-and-qualify-sharing.md) · [ADR-0035](../adr/0035-make-shared-service-replies-select-the-originating-security-context.md)

Implementation: [tools/route_audit.py](../../tools/route_audit.py) · [tools/route_record_review.py](../../tools/route_record_review.py) · [tools/plan_review.py](../../tools/plan_review.py) · [terraform/modules/nutanix-route](../../terraform/modules/nutanix-route)

Offline graphs and exact-record checks are not observations of a live routing table or approval provenance.

## DNS service-owner lifecycle

Design: [SVC §2](../architecture/shared-services/2-name-time-initialization-and-telemetry-profiles.md) · [RA §10](../architecture/reference/10-addressing-name-services-and-end-to-end-traffic.md)

Decisions: [ADR-0020](../adr/0020-use-authoritative-unique-by-default-address-allocation-and-controlled-reuse.md) · [ADR-0010](../adr/0010-expose-shared-services-through-scoped-consumption-endpoints.md)

Implementation: [tools/dns_change.py](../../tools/dns_change.py) · [docs/DNS_LIFECYCLE.md](../DNS_LIFECYCLE.md) · [lab/run_dns_lab.py](../../lab/run_dns_lab.py)

The candidate RFC2136 client and local fixture do not allocate IPAM addresses, qualify a DNS product or prove cache propagation.

## Native readback and interrupted change

Design: [PROV §5](provisioning-strategy/5-concurrency-ownership-and-failed-execution.md) · [OPS §3](../operations/recovery-transition/3-run-maintenance-and-recover-interrupted-changes.md)

Decisions: [ADR-0031](../adr/0031-discover-uncertain-native-outcomes-instead-of-blind-replay-or-rollback.md) · [ADR-0032](../adr/0032-keep-incident-containment-above-routine-reconciliation.md)

Implementation: [tools/nsx_observe.py](../../tools/nsx_observe.py) · [tools/nutanix_observe.py](../../tools/nutanix_observe.py) · [tools/neutron_observe.py](../../tools/neutron_observe.py) · [tools/recovery_review.py](../../tools/recovery_review.py)

Selected reads and offline recovery checks do not perform true writer fencing, platform repair or authorization.

## Service identity and packet fixture

Design: [RA §13](../architecture/reference/13-identity-cryptography-and-service-trust.md) · [QCP §4](../assurance/qualification-campaign/4-observe-identity-storage-and-protocol-completeness.md)

Decisions: [ADR-0029](../adr/0029-keep-recovery-trust-material-independent-of-the-platform-it-unlocks.md) · [ADR-0017](../adr/0017-separate-reference-adoption-technical-qualification-and-authorization.md)

Implementation: [lab/run_namespace_lab.py](../../lab/run_namespace_lab.py) · [lab/mtls_fixture.py](../../lab/mtls_fixture.py)

Local IPv4 mutual-TLS and resource-grant observations do not qualify enterprise PKI, KMS, backup, native IPv6 or vendor HA.

## Local Ansible staging and expectation validation

Design: [PROV §1](provisioning-strategy/1-provisioning-scopes-ownership-and-accepted-handoffs.md) · [PROV §3](provisioning-strategy/3-terraform-native-tools-and-operation-level-support.md)

Decisions: [ADR-0013](../adr/0013-compose-provisioning-across-separate-platform-and-service-authorities.md) · [ADR-0016](../adr/0016-assign-one-authoritative-writer-per-native-object-and-sensitive-subresource.md)

Implementation: [ansible/roles](../../ansible/roles) · [ansible/playbooks](../../ansible/playbooks) · [scripts/verify_ansible.py](../../scripts/verify_ansible.py)

New candidate localhost-only roles; not native switch, hypervisor or firewall configuration.

## Source checks and engine gates

Design: [QUAL §5](../assurance/site-qualification/5-qualification-stages-applicability-and-evidence.md) · [QCP §6](../assurance/qualification-campaign/6-build-an-evidence-packet-a-reviewer-can-challenge.md)

Decisions: [ADR-0017](../adr/0017-separate-reference-adoption-technical-qualification-and-authorization.md)

Implementation: [tools/check_local.py](../../tools/check_local.py) · [scripts/check_repository.py](../../scripts/check_repository.py) · [tools/verify_terraform.py](../../tools/verify_terraform.py) · [.github/workflows/validate.yml](../../.github/workflows/validate.yml)

Current documentation checks are separate from native engine/CI or platform runs. Historical results retain their exact scope.

## Platform capability registry

Design: [Cross-vendor realization model](../architecture/reference/15-cross-vendor-realization-model.md) · [Site qualification and evidence](../assurance/site-qualification/5-qualification-stages-applicability-and-evidence.md)

Implementation: [machine-readable registry](../../sources/capabilities/platform_registry.json) · [registry checker](../../scripts/check_platform_capabilities.py) · [engineering evidence boundary](../engineering/platform-capability-registry.md)

The registry distinguishes candidate source and local fixtures from native qualification. It currently makes no platform production-eligible and does not perform placement.

## Native PlatformProfile qualification dossier

Design: [Site qualification and evidence](../assurance/site-qualification/5-qualification-stages-applicability-and-evidence.md) · [QUAL-001 / ASSUR-003 requirements](../assurance/requirements.md#QUAL-001)

Implementation: [active qualification index](../../sources/capabilities/qualification_index.json) · [dossier validator](../../scripts/check_platform_qualification.py) · [engineering boundary](../engineering/platform-native-qualification.md)

A native-qualified registry claim must be backed by a current exact-tuple dossier with tested limits, evidence freshness, owners and an independent approval reference. The active index is intentionally empty and grants no placement or activation authority.

## Pre-placement platform-family eligibility

Design: [Tenant/WSD placement](../architecture/reference/7-tenant-environments-and-security-domain-placement.md) · [Compute and workload placement](../architecture/reference/11-compute-pools-hypervisors-and-workload-placement.md) · [Provisioning admission sequence](../architecture/reference/23-tenant-domain-and-workload-provisioning-sequence.md)

Implementation: [fail-closed precheck](../../scripts/check_platform_family_eligibility.py) · [held WSD capability example](../../examples/pre_placement_capability_request.json.example) · [engineering boundary](../engineering/pre-placement-platform-eligibility.md)

This precheck evaluates only platform-family capability evidence. It cannot select a site, reserve capacity, allocate resources or authorize activation. The current example intentionally holds because no platform capability is native-qualified.

## Site, cell and service-class capacity eligibility

Design: [Hosting cells and failure boundaries](../architecture/reference/4-hosting-cells-resource-pools-and-failure-boundaries.md) · [Capacity and service envelopes](../assurance/site-qualification/3-capacity-service-envelopes-and-growth-triggers.md) · [Place and reserve sequence](../architecture/reference/23-tenant-domain-and-workload-provisioning-sequence.md)

Implementation: [active capacity inventory](../../sources/capabilities/site_service_capacity_index.json) · [capacity-envelope validator](../../scripts/check_site_service_capacity.py) · [read-only site/service precheck](../../scripts/check_site_service_eligibility.py) · [engineering boundary](../engineering/site-service-capacity-eligibility.md)

The current inventory is intentionally empty. Matching envelopes never create a reservation, select a site, allocate an address or authorize activation; one failed capacity/profile/quota dimension rejects the envelope.

## Reservation preflight and reconciliation evidence

Design: [Place and reserve sequence](../architecture/reference/23-tenant-domain-and-workload-provisioning-sequence.md) · [Reservation recovery](provisioning-strategy/4-end-to-end-fixture-provisioning-and-safe-activation.md) · [Concurrency and failed execution](provisioning-strategy/5-concurrency-ownership-and-failed-execution.md)

Implementation: [exported reservation evidence index](../../sources/capabilities/reservation_record_index.json) · [record validator](../../scripts/check_reservation_records.py) · [immutable intent preflight](../../scripts/check_reservation_preflight.py) · [engineering boundary](../engineering/reservation-preflight-and-reconciliation.md)

The authoritative reservation system remains external. Stable reservation/operation identity, generation, exact demand binding, owner/expiry and conflict/uncertain-outcome handling are validated, but CI never creates or releases a reservation or allocates an address.

## Authoritative IPAM allocation handoff

Design: [Addressing and authoritative IPAM](../architecture/reference/10-addressing-name-services-and-end-to-end-traffic.md) · [ADR-0020](../adr/0020-use-authoritative-unique-by-default-address-allocation-and-controlled-reuse.md) · [Reserve/confirm/release lifecycle](provisioning-strategy/4-end-to-end-fixture-provisioning-and-safe-activation.md)

Implementation: [exported IPAM evidence index](../../sources/capabilities/ipam_allocation_index.json) · [lifecycle evidence validator](../../scripts/check_ipam_allocation_records.py) · [no-guess allocation preflight](../../scripts/check_ipam_allocation_preflight.py) · [engineering boundary](../engineering/authoritative-ipam-allocation-handoff.md)

Actual allocation values remain in authoritative IPAM. Stable operation identity, explicit ownership, unique-by-default policy, uncertain-outcome holds, dependent cleanup and reuse quarantine are validated without reserving/releasing an address or writing DNS.

## Authoritative DNS registration handoff

Design: [Name/time/initialization service profiles](../architecture/shared-services/2-name-time-initialization-and-telemetry-profiles.md) · [Address/name lifecycle](../architecture/reference/10-addressing-name-services-and-end-to-end-traffic.md) · [Scoped DNS lifecycle](../DNS_LIFECYCLE.md)

Implementation: [exported DNS evidence index](../../sources/capabilities/dns_registration_index.json) · [registration evidence validator](../../scripts/check_dns_registration_records.py) · [no-guess DNS preflight](../../scripts/check_dns_registration_preflight.py) · [engineering boundary](../engineering/authoritative-dns-registration-handoff.md)

Actual DNS names and A/AAAA/PTR values remain outside Git. REGISTERED state requires CONFIRMED IPAM evidence and every declared required observation; uncertain outcomes block retries and CI never invokes the RFC2136 writer.

## Backup protection and isolated-restore assurance

Design: [Backup capture and isolated restore](../architecture/shared-services/5-backup-capture-independent-protection-and-isolated-restore.md) · [Storage and backup architecture](../architecture/reference/12-storage-backup-and-data-isolation-architecture.md) · [Recovery qualification evidence](../assurance/site-qualification/5-qualification-stages-applicability-and-evidence.md)

Implementation: [exported backup/restore assurance index](../../sources/capabilities/backup_restore_assurance_index.json) · [assurance evidence validator](../../scripts/check_backup_restore_assurance.py) · [readiness preflight](../../scripts/check_backup_restore_readiness.py) · [engineering boundary](../engineering/backup-isolated-restore-assurance.md)

A successful backup task is insufficient. Current assurance requires protected-copy/catalogue/key evidence, destructive-authority separation and a current isolated useful-data restore witness; CI performs no backup, restore, key or reconnect mutation.

## Control inheritance and external-dependency assurance

Design: [G30 control inheritance gap](../assurance/gap-map/3-detailed-gap-register-and-treatment.md#gap_G30) · [Control inheritance and organizational interfaces](../assurance/site-qualification/6-control-inheritance-assurance-and-organizational-interfaces.md) · [Architecture acceptance and verification](../architecture/reference/28-architecture-acceptance-and-verification.md)

Implementation: [exported control inheritance assurance index](../../sources/capabilities/control_inheritance_assurance_index.json) · [assurance evidence validator](../../scripts/check_control_inheritance_assurance.py) · [readiness preflight](../../scripts/check_control_inheritance_readiness.py) · [engineering boundary](../engineering/control-inheritance-and-external-dependency-assurance.md)

Current assurance requires exact scope, per-control responsibility/evidence, all six external organizational interfaces and no OPEN residual gaps. CI does not select controls, accept inheritance or residual risk, issue authorization, apply infrastructure or activate production.

## Operational handover and incident-readiness assurance

Design: [G31 operating ownership and incident behaviour](../assurance/gap-map/3-detailed-gap-register-and-treatment.md#gap_G31) · [Operating accountability, handover and change](../assurance/site-qualification/7-operating-accountability-handover-and-change.md) · [Operational responsibility acceptance](../operations/recovery-transition/8-accept-operational-responsibility-for-the-delivered-scope.md)

Implementation: [exported operational handover assurance index](../../sources/capabilities/operational_handover_assurance_index.json) · [assurance evidence validator](../../scripts/check_operational_handover_assurance.py) · [readiness preflight](../../scripts/check_operational_handover_readiness.py) · [engineering boundary](../engineering/operational-handover-and-incident-readiness-assurance.md)

Current assurance requires named operating decision owners, accepted as-built/support/recovery scope, current privileged-access and monitoring review, explicit containment release and a current scoped incident exercise. CI performs no live access, incident, recovery, change, apply or activation action.

## Version, source provenance and lifecycle assurance

Design: [G32 version and source provenance](../assurance/gap-map/3-detailed-gap-register-and-treatment.md#gap_G32) · [Implementation tuple and decision package](../engineering/platform-realizations/7-implementation-tuple-and-decision-package.md) · [Support tuple evidence checklist](../engineering/vendor-cards/7-support-tuple-variations-and-evidence-checklist.md)

Implementation: [active version/source provenance index](../../sources/capabilities/version_source_provenance_index.json) · [provenance/lifecycle validator](../../scripts/check_version_source_provenance.py) · [readiness preflight](../../scripts/check_version_source_readiness.py) · [native qualification dependency](../../scripts/check_platform_qualification.py) · [engineering boundary](../engineering/version-source-provenance-and-lifecycle-assurance.md)

A current native qualification now requires the same exact product/API/provider/hardware/licence tuple to have CURRENT_SUPPORTED provenance. Source review, installed compatibility and native qualification remain separate evidence states; none grants placement or activation authority.

## Open native work

[The inherited implementation backlog](../../sources/implementation_backlog.csv) remains the source record for installed target selection, effective security edges, authoritative service integration, native IPv6, actual fencing and production readiness. This conversion does not close those items.
