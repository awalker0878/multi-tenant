# IPAM — assertion allocation

[Allocation index](../assertion-allocation.md) · [Unchanged requirement catalogue](../../assurance/requirements.md)

These are source-grounded proposed allocations, not native compliance results.

## IPAM-001

Every managed network SHALL have an authoritative IPAM record and owner.


### IPAM-001.A01

**Assertion:** Complete source obligation; all applicable clauses must be satisfied: Every managed network SHALL have an authoritative IPAM record and owner.

**Owner / location:** Network engineering / Authoritative IPAM/name registry and explicitly scoped provider service endpoints

**Disposition:** EXTERNAL_AUTHORITATIVE_SERVICE_WITH_CANDIDATE_DNS_INTEGRATION. **Evidence class:** NATIVE_NOT_RUN; related local fixtures/engine checks are narrower evidence, not satisfaction

**Artifact or required operating record:** Accepted service binding, resource entitlement, authoritative allocation/TTL/retention record and native API/transport ACL — specifically: Complete source obligation; all applicable clauses must be satisfied: Every managed network SHALL have an authoritative IPAM record and owner.

**Available related source:** [tools/dns_change.py](../../../tools/dns_change.py) · [docs/DNS_LIFECYCLE.md](../../DNS_LIFECYCLE.md) · [docs/current/interface-agreements.md](../../current/interface-agreements.md)

**Verification:** Observe exact permitted resource/operation and denied foreign/admin access; verify each origin-specific reply, lifecycle and service-loss behaviour. Baseline procedures: CT-029, CT-030

**Remaining dependency:** The DNS client is not an IPAM allocator or production DNS authority; actual server ACLs, secondary/cache propagation and other service integrations remain required.

**Review state:** PROPOSED_ALLOCATION; actual applicability, named authority and evidence assignment pending

## IPAM-002

Overlapping address space SHALL be an explicit exception or migration pattern, not the standard tenancy model.


### IPAM-002.A01

**Assertion:** Complete source obligation; all applicable clauses must be satisfied: Overlapping address space SHALL be an explicit exception or migration pattern, not the standard tenancy model.

**Owner / location:** Network engineering / Authoritative IPAM/name registry and explicitly scoped provider service endpoints

**Disposition:** EXTERNAL_AUTHORITATIVE_SERVICE_WITH_CANDIDATE_DNS_INTEGRATION. **Evidence class:** NATIVE_NOT_RUN; related local fixtures/engine checks are narrower evidence, not satisfaction

**Artifact or required operating record:** Accepted service binding, resource entitlement, authoritative allocation/TTL/retention record and native API/transport ACL — specifically: Complete source obligation; all applicable clauses must be satisfied: Overlapping address space SHALL be an explicit exception or migration pattern, not the standard tenancy model.

**Available related source:** [tools/dns_change.py](../../../tools/dns_change.py) · [docs/DNS_LIFECYCLE.md](../../DNS_LIFECYCLE.md) · [docs/current/interface-agreements.md](../../current/interface-agreements.md)

**Verification:** Observe exact permitted resource/operation and denied foreign/admin access; verify each origin-specific reply, lifecycle and service-loss behaviour. Baseline procedures: CT-029, CT-061

**Remaining dependency:** The DNS client is not an IPAM allocator or production DNS authority; actual server ACLs, secondary/cache propagation and other service integrations remain required.

**Review state:** PROPOSED_ALLOCATION; actual applicability, named authority and evidence assignment pending

## IPAM-003

Address release SHOULD include quarantine/reuse controls appropriate to DNS, logging, firewall state, and incident-response requirements.


### IPAM-003.A01

**Assertion:** Complete source obligation; all applicable clauses must be satisfied: Address release SHOULD include quarantine/reuse controls appropriate to DNS, logging, firewall state, and incident-response requirements.

**Owner / location:** Network engineering / Authoritative IPAM/name registry and explicitly scoped provider service endpoints

**Disposition:** EXTERNAL_AUTHORITATIVE_SERVICE_WITH_CANDIDATE_DNS_INTEGRATION. **Evidence class:** NATIVE_NOT_RUN; related local fixtures/engine checks are narrower evidence, not satisfaction

**Artifact or required operating record:** Accepted service binding, resource entitlement, authoritative allocation/TTL/retention record and native API/transport ACL — specifically: Complete source obligation; all applicable clauses must be satisfied: Address release SHOULD include quarantine/reuse controls appropriate to DNS, logging, firewall state, and incident-response requirements.

**Available related source:** [tools/dns_change.py](../../../tools/dns_change.py) · [docs/DNS_LIFECYCLE.md](../../DNS_LIFECYCLE.md) · [docs/current/interface-agreements.md](../../current/interface-agreements.md)

**Verification:** Observe exact permitted resource/operation and denied foreign/admin access; verify each origin-specific reply, lifecycle and service-loss behaviour. Baseline procedures: CT-013, CT-030

**Remaining dependency:** The DNS client is not an IPAM allocator or production DNS authority; actual server ACLs, secondary/cache propagation and other service integrations remain required.

**Review state:** PROPOSED_ALLOCATION; actual applicability, named authority and evidence assignment pending

## IPAM-004

Address allocation, DNS/DHCP registration and release SHALL use idempotent operation identities, conflict detection and a dependency-aware quarantine policy; IPAM failure SHALL NOT cause guessed allocations.


### IPAM-004.A01

**Assertion:** Complete source obligation; all applicable clauses must be satisfied: Address allocation, DNS/DHCP registration and release SHALL use idempotent operation identities, conflict detection and a dependency-aware quarantine policy; IPAM failure SHALL NOT cause guessed allocations.

**Owner / location:** Automation platform / Authoritative IPAM/name registry and explicitly scoped provider service endpoints

**Disposition:** EXTERNAL_AUTHORITATIVE_SERVICE_WITH_CANDIDATE_DNS_INTEGRATION. **Evidence class:** NATIVE_NOT_RUN; related local fixtures/engine checks are narrower evidence, not satisfaction

**Artifact or required operating record:** Accepted service binding, resource entitlement, authoritative allocation/TTL/retention record and native API/transport ACL — specifically: Complete source obligation; all applicable clauses must be satisfied: Address allocation, DNS/DHCP registration and release SHALL use idempotent operation identities, conflict detection and a dependency-aware quarantine policy; IPAM failure SHALL NOT cause guessed allocations.

**Available related source:** [tools/dns_change.py](../../../tools/dns_change.py) · [docs/DNS_LIFECYCLE.md](../../DNS_LIFECYCLE.md) · [docs/current/interface-agreements.md](../../current/interface-agreements.md)

**Verification:** Observe exact permitted resource/operation and denied foreign/admin access; verify each origin-specific reply, lifecycle and service-loss behaviour. Baseline procedures: CT-029, CT-030, CT-045, CT-046

**Remaining dependency:** The DNS client is not an IPAM allocator or production DNS authority; actual server ACLs, secondary/cache propagation and other service integrations remain required.

**Review state:** PROPOSED_ALLOCATION; actual applicability, named authority and evidence assignment pending

### IPAM-004.A02

**Assertion:** Allocation authority and delegated scope

**Owner / location:** Automation platform / Authoritative IPAM/name registry and explicitly scoped provider service endpoints

**Disposition:** EXTERNAL_AUTHORITATIVE_SERVICE_WITH_CANDIDATE_DNS_INTEGRATION. **Evidence class:** NATIVE_NOT_RUN; related local fixtures/engine checks are narrower evidence, not satisfaction

**Artifact or required operating record:** Accepted service binding, resource entitlement, authoritative allocation/TTL/retention record and native API/transport ACL — specifically: Allocation authority and delegated scope

**Available related source:** [tools/dns_change.py](../../../tools/dns_change.py) · [docs/DNS_LIFECYCLE.md](../../DNS_LIFECYCLE.md) · [docs/current/interface-agreements.md](../../current/interface-agreements.md)

**Verification:** Observe exact permitted resource/operation and denied foreign/admin access; verify each origin-specific reply, lifecycle and service-loss behaviour. Baseline procedures: CT-029, CT-030, CT-045, CT-046

**Remaining dependency:** The DNS client is not an IPAM allocator or production DNS authority; actual server ACLs, secondary/cache propagation and other service integrations remain required.

**Review state:** PROPOSED_ALLOCATION; actual applicability, named authority and evidence assignment pending

### IPAM-004.A03

**Assertion:** Address lifecycle reconciled with native resource

**Owner / location:** Automation platform / Authoritative IPAM/name registry and explicitly scoped provider service endpoints

**Disposition:** EXTERNAL_AUTHORITATIVE_SERVICE_WITH_CANDIDATE_DNS_INTEGRATION. **Evidence class:** NATIVE_NOT_RUN; related local fixtures/engine checks are narrower evidence, not satisfaction

**Artifact or required operating record:** Accepted service binding, resource entitlement, authoritative allocation/TTL/retention record and native API/transport ACL — specifically: Address lifecycle reconciled with native resource

**Available related source:** [tools/dns_change.py](../../../tools/dns_change.py) · [docs/DNS_LIFECYCLE.md](../../DNS_LIFECYCLE.md) · [docs/current/interface-agreements.md](../../current/interface-agreements.md)

**Verification:** Observe exact permitted resource/operation and denied foreign/admin access; verify each origin-specific reply, lifecycle and service-loss behaviour. Baseline procedures: CT-029, CT-030, CT-045, CT-046

**Remaining dependency:** The DNS client is not an IPAM allocator or production DNS authority; actual server ACLs, secondary/cache propagation and other service integrations remain required.

**Review state:** PROPOSED_ALLOCATION; actual applicability, named authority and evidence assignment pending

### IPAM-004.A04

**Assertion:** DNS and address state reconciled

**Owner / location:** Automation platform / Authoritative IPAM/name registry and explicitly scoped provider service endpoints

**Disposition:** EXTERNAL_AUTHORITATIVE_SERVICE_WITH_CANDIDATE_DNS_INTEGRATION. **Evidence class:** NATIVE_NOT_RUN; related local fixtures/engine checks are narrower evidence, not satisfaction

**Artifact or required operating record:** Accepted service binding, resource entitlement, authoritative allocation/TTL/retention record and native API/transport ACL — specifically: DNS and address state reconciled

**Available related source:** [tools/dns_change.py](../../../tools/dns_change.py) · [docs/DNS_LIFECYCLE.md](../../DNS_LIFECYCLE.md) · [docs/current/interface-agreements.md](../../current/interface-agreements.md)

**Verification:** Observe exact permitted resource/operation and denied foreign/admin access; verify each origin-specific reply, lifecycle and service-loss behaviour. Baseline procedures: CT-029, CT-030, CT-045, CT-046

**Remaining dependency:** The DNS client is not an IPAM allocator or production DNS authority; actual server ACLs, secondary/cache propagation and other service integrations remain required.

**Review state:** PROPOSED_ALLOCATION; actual applicability, named authority and evidence assignment pending

### IPAM-004.A05

**Assertion:** No orphan release or duplicate allocation

**Owner / location:** Automation platform / Authoritative IPAM/name registry and explicitly scoped provider service endpoints

**Disposition:** EXTERNAL_AUTHORITATIVE_SERVICE_WITH_CANDIDATE_DNS_INTEGRATION. **Evidence class:** NATIVE_NOT_RUN; related local fixtures/engine checks are narrower evidence, not satisfaction

**Artifact or required operating record:** Accepted service binding, resource entitlement, authoritative allocation/TTL/retention record and native API/transport ACL — specifically: No orphan release or duplicate allocation

**Available related source:** [tools/dns_change.py](../../../tools/dns_change.py) · [docs/DNS_LIFECYCLE.md](../../DNS_LIFECYCLE.md) · [docs/current/interface-agreements.md](../../current/interface-agreements.md)

**Verification:** Observe exact permitted resource/operation and denied foreign/admin access; verify each origin-specific reply, lifecycle and service-loss behaviour. Baseline procedures: CT-029, CT-030, CT-045, CT-046

**Remaining dependency:** The DNS client is not an IPAM allocator or production DNS authority; actual server ACLs, secondary/cache propagation and other service integrations remain required.

**Review state:** PROPOSED_ALLOCATION; actual applicability, named authority and evidence assignment pending
