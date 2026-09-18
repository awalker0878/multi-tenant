# Security-edge and ZIP assurance

**Purpose:** close the current evidence-model gap behind backlog I03/I04 without pretending that route resources, quarantine policies or local packet fixtures implement a complete production ZIP.

A ZIP is a controlled interface between exactly two adjacent domains. It is not a workload zone, transit VRF, generic Tier-0, shared external network or permissive routing context. A current assurance record must bind the accepted boundary scope to routing, policy, inspection, logging, management, failure and bypass observations on the actual realization.

## Source obligations

- ZIP-001 requires every inter-zone path to traverse the applicable ZIP/security edge.
- ZIP-002 requires exactly two authorized adjacent endpoints and prohibits a general-purpose third-zone transit path.
- ZIP-003 requires default deny and permits only approved Flow Intentions/Service Bindings.
- ZIP-004 requires management traffic to remain segregated from operational traffic.
- ZIP-005 keeps data-path and management-path ZIP services distinct and requires assurance before shared virtualization is relied upon.
- ZIP-006 requires both zone authorities, joint approval, security functions, management authority, posture, session-revocation behavior and current evidence.
- ZIP-007 requires a distributed/shared realization to prove the same mandatory security outcomes as a dedicated edge; an unsupported mandatory function makes it ineligible.
- RA §8 additionally requires route/return-path correctness, state/HA behavior, inspection/logging, fail-secure behavior and review of connected/distributed bypass paths.
- NET §§3, 5 and 6 require observed forward/reply paths, healthy negative controls, failure behavior, capacity and separate management paths.

## Active assurance index

The active index is `sources/capabilities/security_edge_zip_assurance_index.json` and is intentionally empty today.

A future record binds one stable `boundary_id` to exactly two distinct endpoint references plus:

- both adjacent authority records;
- joint boundary approval;
- service class;
- management authority;
- accepted/review dates.

The two endpoints must be distinct. Their organizational authority references may be the same when one accountable organization legitimately owns both domains; the record still retains each side explicitly.

## Dedicated versus distributed/shared realization

`DEDICATED_EDGE` records represent a dedicated logical/physical security-edge realization.

`DISTRIBUTED_SHARED` records additionally require:

- a sharing-assurance reference;
- evidence that the realization satisfies the same mandatory ZIP outcomes as a dedicated edge.

`unsupported_mandatory_functions` must always be empty for a qualified record. Distributed firewall licensing, a router or a shared gateway label is not enough.

## Mandatory security functions

Every record carries current evidence for:

- route control;
- stateful policy;
- inspection;
- logging;
- session revocation;
- management separation;
- source-identity preservation;
- fail-secure behavior.

This keeps the security-edge definition outcome-based while remaining vendor-neutral.

## Topology and bypass evidence

The topology block requires controlled references for:

- forward path;
- reply path;
- paired attachments;
- native connected/distributed route review;
- bypass-path review;
- management path;
- translation behavior;
- return-path symmetry.

A prepared VPC, Tier-1, Neutron router, static route or local route graph cannot by itself satisfy this evidence.

## Policy evidence

Current policy evidence requires:

- deny baseline;
- approved flow set;
- policy precedence;
- inspection profile;
- logging profile;
- session-revocation behavior.

An emergency DROP object such as the repository's NSX gateway-quarantine candidate is useful restricted-scope implementation evidence, but it neither enables a firewall nor proves complete path traversal, inspection, precedence or HA.

## Failure and capacity evidence

The failure record covers:

- HA mode;
- state synchronization;
- edge-member loss;
- manager unavailability;
- route withdrawal;
- proof that no uninspected fallback path appears.

Capacity evidence remains separately attributable for sessions, throughput, inspection, log export and survivor capacity.

These are service-class evidence references rather than hard-coded universal performance values.

## Path tests

Current path evidence must include:

- one healthy allowed flow;
- cross-tenant denial;
- unsolicited reverse-initiation denial;
- management-transit denial;
- same-host or distributed-bypass negative evidence.

A timeout alone is not accepted as isolation proof; the underlying test campaign must retain healthy controls and actual forwarding/policy evidence.

## States

Supported states are:

- `CURRENT_QUALIFIED` — boundary review, path/failure evidence and residual-gap state are current;
- `REVIEW_DUE` — scope or residual-gap review has expired;
- `FAILURE_TEST_DUE` — scope remains current but path/failure evidence is stale;
- `GAPS_OPEN` — current evidence exists but unresolved ZIP gaps remain;
- `UNCERTAIN` — authoritative edge/routing/policy state requires reconciliation.

## Readiness preflight

`scripts/check_security_edge_zip_readiness.py` checks an exact boundary ID, source endpoint, destination endpoint and service class against the active assurance index.

A successful result is `SECURITY_EDGE_ZIP_CURRENT_NO_MUTATION_AUTHORIZED`.

It does **not** authorize:

- route creation;
- firewall/policy changes;
- domain attachment;
- edge configuration;
- management-access changes;
- infrastructure apply;
- production activation.

Current repository state remains held because no production security-edge realization has supplied current native evidence:

```sh
python scripts/check_security_edge_zip_readiness.py examples/security_edge_zip_readiness_intent.json.example --as-of 2026-09-18T21:45:00Z --expected-status HOLD_NO_CURRENT_SECURITY_EDGE_ZIP_ASSURANCE
```

Actual EC/SE selection, native configuration, joint boundary approval, packet/control-plane observations, failure tests and operating acceptance remain external accountable work.

[RA §8 — Zone interfaces, routing and security-edge topology](../architecture/reference/8-zone-interfaces-routing-and-security-edge-topology.md) · [NET §3 — Worked inter-zone routing and enforcement schedule](fabric/3-worked-inter-zone-routing-and-enforcement-schedule.md) · [ZIP allocation](../implementation/allocation/zip.md)
