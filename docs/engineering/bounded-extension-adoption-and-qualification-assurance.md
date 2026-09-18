# Bounded extension adoption and qualification assurance

**Purpose:** make G33 executable by keeping optional infrastructure/service extensions outside the portable base service until their own scope, topology, ownership, lifecycle and applicable qualification are complete.

Bare metal, containers, special devices, L2 stretch/cross-stack patterns, higher-assurance designs and future platforms are not automatically admitted because they reuse WSD terminology or resemble an existing platform object. They remain separately governed extension service classes.

## Source obligations

- G33 requires approved extension scope and complete applicable extension qualification.
- REF-002 allows platform-specific extensions only when they are declared and do not redefine the portable core.
- FUT-001 requires a new platform to pass its applicable conformance suite before production placement.
- FUT-002 requires unsupported capabilities to remain explicit and forbids weakening mandatory controls to imitate support.
- FUT-003 requires bare-metal and container profiles to explicitly qualify host/control-plane, network, storage and lifecycle isolation; namespaces, projects and physical VRFs are not complete security-boundary evidence.
- RA §19 requires separate component topology and provisioning profiles before an extension is offered.
- QUAL §8 requires extension-specific topology, trust/failure boundaries, supported stack, provisioning ownership, service parameters and applicable qualification.

## Active extension assurance index

The active index is `sources/capabilities/extension_adoption_assurance_index.json` and is intentionally empty today.

Every future record is hard-bound to:

- an extension kind and stable extension ID;
- an extension profile and extension-specific service class;
- an attributable adoption decision and extension owner;
- an explicit portability-impact record;
- `base_service_status = EXTENSION_ONLY`.

The validator rejects any record that attempts to mark the extension as part of the base offered service.

## Complete design boundary

Every extension must carry controlled references for:

- component topology;
- trust boundaries;
- failure model;
- management;
- network;
- storage;
- identity;
- provisioning;
- recovery;
- retirement.

These are evidence references rather than implementation payloads. The repository does not become the physical-fabric controller, Kubernetes API, device manager or other extension owner.

## Kind-specific evidence

Each extension kind has a closed required evidence set.

### Bare metal

- authenticated BMC/boot/firmware path;
- port/gateway authority;
- data attachment;
- media sanitization before reuse.

A physical VRF by itself cannot satisfy this set.

### Container hosting

- control-plane/node sharing decision;
- workload admission;
- actual network-policy enforcement;
- privileged/host-network workload restrictions;
- secrets and storage;
- cluster recovery.

A namespace or project plus a NetworkPolicy declaration is not sufficient evidence of a hostile-tenant boundary.

### Special devices and accelerators

- device tenancy;
- host compatibility;
- reset/data handling;
- mobility limits.

### L2 stretch or cross-stack composite

- gateway/partition behavior;
- writer fencing;
- latency/failure coupling;
- cross-scope ownership.

### Higher assurance

- source applicability;
- dedication scope;
- infrastructure-control scope;
- explicit approval.

### Future platform

- supported stack;
- portable-interface equivalence;
- conformance scope;
- exit and recovery path.

## Qualification dimensions

All extension records require evidence across seven dimensions:

- topology;
- management;
- host/control-plane;
- network;
- storage;
- lifecycle;
- recovery.

The qualification record also carries applicable test sets, a qualification decision, accountable role and validity period.

Unsupported capabilities remain explicit. `mandatory_control_weakening` is hard-locked to `DENIED`.

## States

Supported states are:

- `CURRENT_ADOPTED` — scope review and qualification are current and no OPEN residual gaps remain;
- `REVIEW_DUE` — extension scope or residual-gap review is stale;
- `QUALIFICATION_DUE` — scope remains current but applicable extension qualification has expired;
- `GAPS_OPEN` — current evidence exists but unresolved extension gaps remain;
- `UNCERTAIN` — authoritative extension state requires reconciliation.

None of these states can make the extension part of the base service.

## Readiness preflight

`scripts/check_extension_adoption_readiness.py` compares a requested extension kind/profile/service-class scope to the active adoption index.

A successful result is `EXTENSION_ADOPTION_CURRENT_EXTENSION_ONLY_NO_PROVISIONING_AUTHORIZED`.

It does **not** authorize:

- promotion into the portable base service;
- bare-metal or physical-fabric changes;
- cluster creation;
- device assignment;
- extension provisioning;
- infrastructure apply;
- production activation.

Current repository state remains held because the active extension index is empty:

```sh
python scripts/check_extension_adoption_readiness.py examples/extension_adoption_readiness_intent.json.example --as-of 2026-09-18T21:00:00Z --expected-status HOLD_NO_CURRENT_EXTENSION_ADOPTION
```

Actual extension low-level designs, native implementation, qualification campaigns, recovery/exit evidence and authorization remain extension-owner work.

[G33 — Bounded extensions](../assurance/gap-map/3-detailed-gap-register-and-treatment.md#gap_G33) · [RA §19 — Physical workloads and future platform extensions](../architecture/reference/19-physical-workloads-and-future-platform-extensions.md) · [QUAL §8 — Extensions and release maintenance](../assurance/site-qualification/8-extensions-and-release-maintenance.md)
