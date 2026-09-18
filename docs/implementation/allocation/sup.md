# SUP — assertion allocation

[Allocation index](../assertion-allocation.md) · [Unchanged requirement catalogue](../../assurance/requirements.md)

These are source-grounded proposed allocations, not native compliance results.

## SUP-001

Privileged software/provider/module supply chains SHALL use approved sources, integrity verification, revocation and a compromise-response procedure covering already-executed artifacts and credentials.


### SUP-001.A01

**Assertion:** Complete source obligation; all applicable clauses must be satisfied: Privileged software/provider/module supply chains SHALL use approved sources, integrity verification, revocation and a compromise-response procedure covering already-executed artifacts and credentials.

**Owner / location:** Automation platform / Actual operational service, independent telemetry, capacity/failure domains and lifecycle authorities

**Disposition:** EXTERNAL_OPERATING_SERVICE_OR_CONTROL_REQUIRED. **Evidence class:** NATIVE_NOT_RUN; related local fixtures/engine checks are narrower evidence, not satisfaction

**Artifact or required operating record:** Owned runbook/service configuration, measured limits, dependency inventory and actual incident/recovery/retention acceptance record — specifically: Complete source obligation; all applicable clauses must be satisfied: Privileged software/provider/module supply chains SHALL use approved sources, integrity verification, revocation and a compromise-response procedure covering already-executed artifacts and credentials.

**Available related source:** [docs/current/transition-and-as-built.md](../../current/transition-and-as-built.md) · [docs/current/TAD-infrastructure.md](../../current/TAD-infrastructure.md) · [sources/implementation_backlog.csv](../../../sources/implementation_backlog.csv)

**Verification:** Perform each documented assertion on the actual approved service using independent observations and measured time/data outcomes; inspect exact versions and residual risks. Baseline procedures: CT-041, CT-042, CT-057

**Remaining dependency:** Reference procedures and local fixtures do not provide the selected operational infrastructure, measured recovery/HA, native supply-chain response or disposition authority.

**Review state:** PROPOSED_ALLOCATION; actual applicability, named authority and evidence assignment pending
