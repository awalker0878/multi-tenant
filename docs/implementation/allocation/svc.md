# SVC — assertion allocation

[Allocation index](../assertion-allocation.md) · [Unchanged requirement catalogue](../../assurance/requirements.md)

These are source-grounded proposed allocations, not native compliance results.

## SVC-001

Consumers SHALL NOT receive broad routing to a shared-services supernet solely because they consume one shared service.


### SVC-001.A01

**Assertion:** Complete source obligation; all applicable clauses must be satisfied: Consumers SHALL NOT receive broad routing to a shared-services supernet solely because they consume one shared service.

**Owner / location:** Service operations / Authoritative IPAM/name registry and explicitly scoped provider service endpoints

**Disposition:** EXTERNAL_AUTHORITATIVE_SERVICE_WITH_CANDIDATE_DNS_INTEGRATION. **Evidence class:** NATIVE_NOT_RUN; related local fixtures/engine checks are narrower evidence, not satisfaction

**Artifact or required operating record:** Accepted service binding, resource entitlement, authoritative allocation/TTL/retention record and native API/transport ACL — specifically: Complete source obligation; all applicable clauses must be satisfied: Consumers SHALL NOT receive broad routing to a shared-services supernet solely because they consume one shared service.

**Available related source:** [tools/dns_change.py](../../../tools/dns_change.py) · [docs/DNS_LIFECYCLE.md](../../DNS_LIFECYCLE.md) · [docs/current/interface-agreements.md](../../current/interface-agreements.md)

**Verification:** Observe exact permitted resource/operation and denied foreign/admin access; verify each origin-specific reply, lifecycle and service-loss behaviour. Baseline procedures: CT-008, CT-037

**Remaining dependency:** The DNS client is not an IPAM allocator or production DNS authority; actual server ACLs, secondary/cache propagation and other service integrations remain required.

**Review state:** PROPOSED_ALLOCATION; actual applicability, named authority and evidence assignment pending

## SVC-002

Where useful, shared services SHOULD expose zone-aligned endpoints so that consumption does not force unnecessary cross-zone routing.


### SVC-002.A01

**Assertion:** Complete source obligation; all applicable clauses must be satisfied: Where useful, shared services SHOULD expose zone-aligned endpoints so that consumption does not force unnecessary cross-zone routing.

**Owner / location:** Service operations / Authoritative IPAM/name registry and explicitly scoped provider service endpoints

**Disposition:** EXTERNAL_AUTHORITATIVE_SERVICE_WITH_CANDIDATE_DNS_INTEGRATION. **Evidence class:** NATIVE_NOT_RUN; related local fixtures/engine checks are narrower evidence, not satisfaction

**Artifact or required operating record:** Accepted service binding, resource entitlement, authoritative allocation/TTL/retention record and native API/transport ACL — specifically: Complete source obligation; all applicable clauses must be satisfied: Where useful, shared services SHOULD expose zone-aligned endpoints so that consumption does not force unnecessary cross-zone routing.

**Available related source:** [tools/dns_change.py](../../../tools/dns_change.py) · [docs/DNS_LIFECYCLE.md](../../DNS_LIFECYCLE.md) · [docs/current/interface-agreements.md](../../current/interface-agreements.md)

**Verification:** Observe exact permitted resource/operation and denied foreign/admin access; verify each origin-specific reply, lifecycle and service-loss behaviour. Baseline procedures: CT-008, CT-025

**Remaining dependency:** The DNS client is not an IPAM allocator or production DNS authority; actual server ACLs, secondary/cache propagation and other service integrations remain required.

**Review state:** PROPOSED_ALLOCATION; actual applicability, named authority and evidence assignment pending

## SVC-003

Each ServiceProfile SHALL define direction, endpoint identity, authentication, allowed scope, availability, failure behavior and management separation; bindings SHALL be revoked when their entitlement or service version expires.


### SVC-003.A01

**Assertion:** Complete source obligation; all applicable clauses must be satisfied: Each ServiceProfile SHALL define direction, endpoint identity, authentication, allowed scope, availability, failure behavior and management separation; bindings SHALL be revoked when their entitlement or service version expires.

**Owner / location:** Service operations / Authoritative IPAM/name registry and explicitly scoped provider service endpoints

**Disposition:** EXTERNAL_AUTHORITATIVE_SERVICE_WITH_CANDIDATE_DNS_INTEGRATION. **Evidence class:** NATIVE_NOT_RUN; related local fixtures/engine checks are narrower evidence, not satisfaction

**Artifact or required operating record:** Accepted service binding, resource entitlement, authoritative allocation/TTL/retention record and native API/transport ACL — specifically: Complete source obligation; all applicable clauses must be satisfied: Each ServiceProfile SHALL define direction, endpoint identity, authentication, allowed scope, availability, failure behavior and management separation; bindings SHALL be revoked when their entitlement or service version expires.

**Available related source:** [tools/dns_change.py](../../../tools/dns_change.py) · [docs/DNS_LIFECYCLE.md](../../DNS_LIFECYCLE.md) · [docs/current/interface-agreements.md](../../current/interface-agreements.md)

**Verification:** Observe exact permitted resource/operation and denied foreign/admin access; verify each origin-specific reply, lifecycle and service-loss behaviour. Baseline procedures: CT-008, CT-028, CT-077

**Remaining dependency:** The DNS client is not an IPAM allocator or production DNS authority; actual server ACLs, secondary/cache propagation and other service integrations remain required.

**Review state:** PROPOSED_ALLOCATION; actual applicability, named authority and evidence assignment pending

### SVC-003.A02

**Assertion:** Each ServiceProfile SHALL define direction, endpoint identity, authentication, allowed scope, availability, failure behavior and management separation

**Owner / location:** Service operations / Authoritative IPAM/name registry and explicitly scoped provider service endpoints

**Disposition:** EXTERNAL_AUTHORITATIVE_SERVICE_WITH_CANDIDATE_DNS_INTEGRATION. **Evidence class:** NATIVE_NOT_RUN; related local fixtures/engine checks are narrower evidence, not satisfaction

**Artifact or required operating record:** Accepted service binding, resource entitlement, authoritative allocation/TTL/retention record and native API/transport ACL — specifically: Each ServiceProfile SHALL define direction, endpoint identity, authentication, allowed scope, availability, failure behavior and management separation

**Available related source:** [tools/dns_change.py](../../../tools/dns_change.py) · [docs/DNS_LIFECYCLE.md](../../DNS_LIFECYCLE.md) · [docs/current/interface-agreements.md](../../current/interface-agreements.md)

**Verification:** Observe exact permitted resource/operation and denied foreign/admin access; verify each origin-specific reply, lifecycle and service-loss behaviour. Baseline procedures: CT-008, CT-028, CT-077

**Remaining dependency:** The DNS client is not an IPAM allocator or production DNS authority; actual server ACLs, secondary/cache propagation and other service integrations remain required.

**Review state:** PROPOSED_ALLOCATION; actual applicability, named authority and evidence assignment pending

### SVC-003.A03

**Assertion:** bindings SHALL be revoked when their entitlement or service version expires.

**Owner / location:** Service operations / Authoritative IPAM/name registry and explicitly scoped provider service endpoints

**Disposition:** EXTERNAL_AUTHORITATIVE_SERVICE_WITH_CANDIDATE_DNS_INTEGRATION. **Evidence class:** NATIVE_NOT_RUN; related local fixtures/engine checks are narrower evidence, not satisfaction

**Artifact or required operating record:** Accepted service binding, resource entitlement, authoritative allocation/TTL/retention record and native API/transport ACL — specifically: bindings SHALL be revoked when their entitlement or service version expires.

**Available related source:** [tools/dns_change.py](../../../tools/dns_change.py) · [docs/DNS_LIFECYCLE.md](../../DNS_LIFECYCLE.md) · [docs/current/interface-agreements.md](../../current/interface-agreements.md)

**Verification:** Observe exact permitted resource/operation and denied foreign/admin access; verify each origin-specific reply, lifecycle and service-loss behaviour. Baseline procedures: CT-008, CT-028, CT-077

**Remaining dependency:** The DNS client is not an IPAM allocator or production DNS authority; actual server ACLs, secondary/cache propagation and other service integrations remain required.

**Review state:** PROPOSED_ALLOCATION; actual applicability, named authority and evidence assignment pending
