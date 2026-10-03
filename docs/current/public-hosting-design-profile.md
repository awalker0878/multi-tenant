# SOL-M02 — Public service hosting design profile

**Version:** 0.5 · **Status:** Proposed · **Accountable role:** Security and hosting solution architects.

## Scope and authority

A proposed public-extension design profile under the same workload mobility authority model; public exposure remains deferred and is not enabled by the internal fixture.

This is a newly authored maintained Markdown record, not a reconstruction of an unavailable Word original. Its creation date is not an acceptance date. Source basis: [RA §9](../architecture/reference/9-shared-services-ingress-and-controlled-egress.md) · [RA §7](../architecture/reference/7-tenant-environments-and-security-domain-placement.md) · [NET §2](../engineering/fabric/2-isolated-attachment-units-and-bounded-capacity.md).

## Design content

Public exposure is a separate approved service. External reachability terminates at the selected PAZ ingress function and permitted external boundary, with distinct backend permission to OZ and protected data access to RZ. Internal domains do not receive direct external attachments simply to publish an endpoint. Return paths and any address translation must preserve control and attribution.

Choose actual ingress/WAF/load-balancer functions, TLS termination/re-encryption, certificate and DNS ownership, trusted client attribution, health probes, upstream threat capacity and inspection. Each is a design decision requiring a supported implementation, not a default product recommendation. Administrative endpoints are excluded from the consumption path.

Document admission and withdrawal of exposure, backend failure behaviour, certificate/key loss and replacement, inspection capacity under node failure, log dependency loss, and recovery/failback. Egress is separately scoped; an inbound approval does not authorize arbitrary outbound communication.

### Relationship to the workload mobility application

The control application and expanded capability vocabulary do not enable this
proposed public-extension profile. Public ingress, controlled egress, policy
insertion, edge capacity, address families and service exposure require explicit
installed-tuple and route qualification, native construction, independent traffic
observations and adopting authority. Missing evidence remains a blocker.

Apply the same tenant-scoped immutable plans, approvals, worker authority, complete
profile limitations, useful-service postconditions and data/recovery boundaries as
the [current RAD](RAD-adoption.md) and [TAD](TAD-infrastructure.md). Rehearsal must
suppress production side effects and must not publish public DNS or activate a
public route implicitly. Keep this design profile deferred until its own engineering,
implementation and acceptance conditions are demonstrated; it is not inherited from
a successful internal IPv4 fixture.

### No inferred public-edge or service equivalence

The semantic property contract does not enable this deferred public design.
An NSX or Nutanix product name, Neutron core API, or an overlay identifier cannot
supply ingress protection, load-balancing, VPN, route ownership or isolation.
Selected backend, service, rule scope and enforcement state require native
observation and independent positive/negative tests. Gateway protection cannot
silently substitute for a mandatory all-NIC distributed policy.

See [verified research decisions](../engineering/platform-migration-research.md) and
[existing wave-plan delta](../product/enterprise-workload-mobility-execution-plan.md#8-research-driven-acceptance-and-implementation-delta).

### Catalog and discovery correction — 1 October 2026

Availability catalog 18 distinguishes security zones from physical failure domains;
no zone name establishes HA, restart reserves or recovery. Typed requirements now
reject malformed flags/quantities and insufficient workload counts; independent-site
recovery remains unsupported. New catalog digests require regenerated examples and
fresh plan review. All five-request/three-platform examples stay disabled.
OpenStack collector selector 3 preserves bounded native allocation/image/attachment
facts without converting them into qualification. The [current research review](../engineering/platform-capability-review-2026-10-01.md)
records these changes and remaining coverage. No deferred public, encryption, GPU,
whole-VM, provisioning or migration capability is enabled by this correction.

## Engineering and implementation handoff

Produce the actual site LLD and interface agreements before a native implementation. Allocate each required upstream/ingress/backend/data control to its owner. Keep the base internal fixture disabled externally and build an explicitly isolated qualification scope for the extension.

## Acceptance and open work

This replaces no unavailable source by claim. It supplies a new profile for review. The actual public-service solution, components, addresses, tests, risk acceptance and native activation are not completed by it.

Adopting authority and approval evidence: **not recorded**. Link the actual design review and its conditions when they exist; a code merge does not authorize a site or service. Keep sensitive site parameters and private credentials in their approved systems.

[Maintained design register](README.md) · [Decision register](../adr/README.md)
