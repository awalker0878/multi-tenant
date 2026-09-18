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

## Pre-placement platform-family eligibility

Design: [Tenant/WSD placement](../architecture/reference/7-tenant-environments-and-security-domain-placement.md) · [Compute and workload placement](../architecture/reference/11-compute-pools-hypervisors-and-workload-placement.md) · [Provisioning admission sequence](../architecture/reference/23-tenant-domain-and-workload-provisioning-sequence.md)

Implementation: [fail-closed precheck](../../scripts/check_platform_family_eligibility.py) · [held WSD capability example](../../examples/pre_placement_capability_request.json.example) · [engineering boundary](../engineering/pre-placement-platform-eligibility.md)

This precheck evaluates only platform-family capability evidence. It cannot select a site, reserve capacity, allocate resources or authorize activation. The current example intentionally holds because no platform capability is native-qualified.

## Open native work

[The inherited implementation backlog](../../sources/implementation_backlog.csv) remains the source record for installed target selection, effective security edges, authoritative service integration, native IPv6, actual fencing and production readiness. This conversion does not close those items.
