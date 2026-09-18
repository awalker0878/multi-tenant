# FAIL — assertion allocation

[Allocation index](../assertion-allocation.md) · [Unchanged requirement catalogue](../../assurance/requirements.md)

These are source-grounded proposed allocations, not native compliance results.

## FAIL-001

Control-plane failure SHALL NOT create an implicit permit path.


### FAIL-001.A01

**Assertion:** Complete source obligation; all applicable clauses must be satisfied: Control-plane failure SHALL NOT create an implicit permit path.

**Owner / location:** Platform operations / Actual operational service, independent telemetry, capacity/failure domains and lifecycle authorities

**Disposition:** EXTERNAL_OPERATING_SERVICE_OR_CONTROL_REQUIRED. **Evidence class:** NATIVE_NOT_RUN; related local fixtures/engine checks are narrower evidence, not satisfaction

**Artifact or required operating record:** Owned runbook/service configuration, measured limits, dependency inventory and actual incident/recovery/retention acceptance record — specifically: Complete source obligation; all applicable clauses must be satisfied: Control-plane failure SHALL NOT create an implicit permit path.

**Available related source:** [docs/current/transition-and-as-built.md](../../current/transition-and-as-built.md) · [docs/current/TAD-infrastructure.md](../../current/TAD-infrastructure.md) · [sources/implementation_backlog.csv](../../../sources/implementation_backlog.csv)

**Verification:** Perform each documented assertion on the actual approved service using independent observations and measured time/data outcomes; inspect exact versions and residual risks. Baseline procedures: CT-011, CT-012, CT-024, CT-052

**Remaining dependency:** Reference procedures and local fixtures do not provide the selected operational infrastructure, measured recovery/HA, native supply-chain response or disposition authority.

**Review state:** PROPOSED_ALLOCATION; actual applicability, named authority and evidence assignment pending

## FAIL-002

Failover and control-plane-loss scenarios SHALL be included in platform conformance testing.


### FAIL-002.A01

**Assertion:** Complete source obligation; all applicable clauses must be satisfied: Failover and control-plane-loss scenarios SHALL be included in platform conformance testing.

**Owner / location:** Assurance engineering / Actual operational service, independent telemetry, capacity/failure domains and lifecycle authorities

**Disposition:** EXTERNAL_OPERATING_SERVICE_OR_CONTROL_REQUIRED. **Evidence class:** NATIVE_NOT_RUN; related local fixtures/engine checks are narrower evidence, not satisfaction

**Artifact or required operating record:** Owned runbook/service configuration, measured limits, dependency inventory and actual incident/recovery/retention acceptance record — specifically: Complete source obligation; all applicable clauses must be satisfied: Failover and control-plane-loss scenarios SHALL be included in platform conformance testing.

**Available related source:** [docs/current/transition-and-as-built.md](../../current/transition-and-as-built.md) · [docs/current/TAD-infrastructure.md](../../current/TAD-infrastructure.md) · [sources/implementation_backlog.csv](../../../sources/implementation_backlog.csv)

**Verification:** Perform each documented assertion on the actual approved service using independent observations and measured time/data outcomes; inspect exact versions and residual risks. Baseline procedures: CT-011, CT-012, CT-027, CT-038, CT-050, CT-054, CT-055

**Remaining dependency:** Reference procedures and local fixtures do not provide the selected operational infrastructure, measured recovery/HA, native supply-chain response or disposition authority.

**Review state:** PROPOSED_ALLOCATION; actual applicability, named authority and evidence assignment pending

## FAIL-003

Every critical dependency SHALL have a qualified loss/partition/recovery behavior, including credential/key continuity, logging loss, state recovery and split-brain prevention; unavailable authority SHALL NOT authorize fallback bypass.


### FAIL-003.A01

**Assertion:** Complete source obligation; all applicable clauses must be satisfied: Every critical dependency SHALL have a qualified loss/partition/recovery behavior, including credential/key continuity, logging loss, state recovery and split-brain prevention; unavailable authority SHALL NOT authorize fallback bypass.

**Owner / location:** Platform operations / Actual operational service, independent telemetry, capacity/failure domains and lifecycle authorities

**Disposition:** EXTERNAL_OPERATING_SERVICE_OR_CONTROL_REQUIRED. **Evidence class:** NATIVE_NOT_RUN; related local fixtures/engine checks are narrower evidence, not satisfaction

**Artifact or required operating record:** Owned runbook/service configuration, measured limits, dependency inventory and actual incident/recovery/retention acceptance record — specifically: Complete source obligation; all applicable clauses must be satisfied: Every critical dependency SHALL have a qualified loss/partition/recovery behavior, including credential/key continuity, logging loss, state recovery and split-brain prevention; unavailable authority SHALL NOT authorize fallback bypass.

**Available related source:** [docs/current/transition-and-as-built.md](../../current/transition-and-as-built.md) · [docs/current/TAD-infrastructure.md](../../current/TAD-infrastructure.md) · [sources/implementation_backlog.csv](../../../sources/implementation_backlog.csv)

**Verification:** Perform each documented assertion on the actual approved service using independent observations and measured time/data outcomes; inspect exact versions and residual risks. Baseline procedures: CT-027, CT-038, CT-044, CT-050, CT-054, CT-055

**Remaining dependency:** Reference procedures and local fixtures do not provide the selected operational infrastructure, measured recovery/HA, native supply-chain response or disposition authority.

**Review state:** PROPOSED_ALLOCATION; actual applicability, named authority and evidence assignment pending

### FAIL-003.A02

**Assertion:** Loss/partition behaviour of each critical dependency

**Owner / location:** Platform operations / Actual operational service, independent telemetry, capacity/failure domains and lifecycle authorities

**Disposition:** EXTERNAL_OPERATING_SERVICE_OR_CONTROL_REQUIRED. **Evidence class:** NATIVE_NOT_RUN; related local fixtures/engine checks are narrower evidence, not satisfaction

**Artifact or required operating record:** Owned runbook/service configuration, measured limits, dependency inventory and actual incident/recovery/retention acceptance record — specifically: Loss/partition behaviour of each critical dependency

**Available related source:** [docs/current/transition-and-as-built.md](../../current/transition-and-as-built.md) · [docs/current/TAD-infrastructure.md](../../current/TAD-infrastructure.md) · [sources/implementation_backlog.csv](../../../sources/implementation_backlog.csv)

**Verification:** Perform each documented assertion on the actual approved service using independent observations and measured time/data outcomes; inspect exact versions and residual risks. Baseline procedures: CT-027, CT-038, CT-044, CT-050, CT-054, CT-055

**Remaining dependency:** Reference procedures and local fixtures do not provide the selected operational infrastructure, measured recovery/HA, native supply-chain response or disposition authority.

**Review state:** PROPOSED_ALLOCATION; actual applicability, named authority and evidence assignment pending

### FAIL-003.A03

**Assertion:** Credential and key continuity

**Owner / location:** Platform operations / Actual operational service, independent telemetry, capacity/failure domains and lifecycle authorities

**Disposition:** EXTERNAL_OPERATING_SERVICE_OR_CONTROL_REQUIRED. **Evidence class:** NATIVE_NOT_RUN; related local fixtures/engine checks are narrower evidence, not satisfaction

**Artifact or required operating record:** Owned runbook/service configuration, measured limits, dependency inventory and actual incident/recovery/retention acceptance record — specifically: Credential and key continuity

**Available related source:** [docs/current/transition-and-as-built.md](../../current/transition-and-as-built.md) · [docs/current/TAD-infrastructure.md](../../current/TAD-infrastructure.md) · [sources/implementation_backlog.csv](../../../sources/implementation_backlog.csv)

**Verification:** Perform each documented assertion on the actual approved service using independent observations and measured time/data outcomes; inspect exact versions and residual risks. Baseline procedures: CT-027, CT-038, CT-044, CT-050, CT-054, CT-055

**Remaining dependency:** Reference procedures and local fixtures do not provide the selected operational infrastructure, measured recovery/HA, native supply-chain response or disposition authority.

**Review state:** PROPOSED_ALLOCATION; actual applicability, named authority and evidence assignment pending

### FAIL-003.A04

**Assertion:** Logging loss response

**Owner / location:** Platform operations / Actual operational service, independent telemetry, capacity/failure domains and lifecycle authorities

**Disposition:** EXTERNAL_OPERATING_SERVICE_OR_CONTROL_REQUIRED. **Evidence class:** NATIVE_NOT_RUN; related local fixtures/engine checks are narrower evidence, not satisfaction

**Artifact or required operating record:** Owned runbook/service configuration, measured limits, dependency inventory and actual incident/recovery/retention acceptance record — specifically: Logging loss response

**Available related source:** [docs/current/transition-and-as-built.md](../../current/transition-and-as-built.md) · [docs/current/TAD-infrastructure.md](../../current/TAD-infrastructure.md) · [sources/implementation_backlog.csv](../../../sources/implementation_backlog.csv)

**Verification:** Perform each documented assertion on the actual approved service using independent observations and measured time/data outcomes; inspect exact versions and residual risks. Baseline procedures: CT-027, CT-038, CT-044, CT-050, CT-054, CT-055

**Remaining dependency:** Reference procedures and local fixtures do not provide the selected operational infrastructure, measured recovery/HA, native supply-chain response or disposition authority.

**Review state:** PROPOSED_ALLOCATION; actual applicability, named authority and evidence assignment pending

### FAIL-003.A05

**Assertion:** State recovery

**Owner / location:** Platform operations / Actual operational service, independent telemetry, capacity/failure domains and lifecycle authorities

**Disposition:** EXTERNAL_OPERATING_SERVICE_OR_CONTROL_REQUIRED. **Evidence class:** NATIVE_NOT_RUN; related local fixtures/engine checks are narrower evidence, not satisfaction

**Artifact or required operating record:** Owned runbook/service configuration, measured limits, dependency inventory and actual incident/recovery/retention acceptance record — specifically: State recovery

**Available related source:** [docs/current/transition-and-as-built.md](../../current/transition-and-as-built.md) · [docs/current/TAD-infrastructure.md](../../current/TAD-infrastructure.md) · [sources/implementation_backlog.csv](../../../sources/implementation_backlog.csv)

**Verification:** Perform each documented assertion on the actual approved service using independent observations and measured time/data outcomes; inspect exact versions and residual risks. Baseline procedures: CT-027, CT-038, CT-044, CT-050, CT-054, CT-055

**Remaining dependency:** Reference procedures and local fixtures do not provide the selected operational infrastructure, measured recovery/HA, native supply-chain response or disposition authority.

**Review state:** PROPOSED_ALLOCATION; actual applicability, named authority and evidence assignment pending

### FAIL-003.A06

**Assertion:** Split-brain prevention

**Owner / location:** Platform operations / Actual operational service, independent telemetry, capacity/failure domains and lifecycle authorities

**Disposition:** EXTERNAL_OPERATING_SERVICE_OR_CONTROL_REQUIRED. **Evidence class:** NATIVE_NOT_RUN; related local fixtures/engine checks are narrower evidence, not satisfaction

**Artifact or required operating record:** Owned runbook/service configuration, measured limits, dependency inventory and actual incident/recovery/retention acceptance record — specifically: Split-brain prevention

**Available related source:** [docs/current/transition-and-as-built.md](../../current/transition-and-as-built.md) · [docs/current/TAD-infrastructure.md](../../current/TAD-infrastructure.md) · [sources/implementation_backlog.csv](../../../sources/implementation_backlog.csv)

**Verification:** Perform each documented assertion on the actual approved service using independent observations and measured time/data outcomes; inspect exact versions and residual risks. Baseline procedures: CT-027, CT-038, CT-044, CT-050, CT-054, CT-055

**Remaining dependency:** Reference procedures and local fixtures do not provide the selected operational infrastructure, measured recovery/HA, native supply-chain response or disposition authority.

**Review state:** PROPOSED_ALLOCATION; actual applicability, named authority and evidence assignment pending

### FAIL-003.A07

**Assertion:** Unavailable authority does not permit bypass

**Owner / location:** Platform operations / Actual operational service, independent telemetry, capacity/failure domains and lifecycle authorities

**Disposition:** EXTERNAL_OPERATING_SERVICE_OR_CONTROL_REQUIRED. **Evidence class:** NATIVE_NOT_RUN; related local fixtures/engine checks are narrower evidence, not satisfaction

**Artifact or required operating record:** Owned runbook/service configuration, measured limits, dependency inventory and actual incident/recovery/retention acceptance record — specifically: Unavailable authority does not permit bypass

**Available related source:** [docs/current/transition-and-as-built.md](../../current/transition-and-as-built.md) · [docs/current/TAD-infrastructure.md](../../current/TAD-infrastructure.md) · [sources/implementation_backlog.csv](../../../sources/implementation_backlog.csv)

**Verification:** Perform each documented assertion on the actual approved service using independent observations and measured time/data outcomes; inspect exact versions and residual risks. Baseline procedures: CT-027, CT-038, CT-044, CT-050, CT-054, CT-055

**Remaining dependency:** Reference procedures and local fixtures do not provide the selected operational infrastructure, measured recovery/HA, native supply-chain response or disposition authority.

**Review state:** PROPOSED_ALLOCATION; actual applicability, named authority and evidence assignment pending
