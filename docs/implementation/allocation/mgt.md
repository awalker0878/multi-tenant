# MGT — assertion allocation

[Allocation index](../assertion-allocation.md) · [Unchanged requirement catalogue](../../assurance/requirements.md)

These are source-grounded proposed allocations, not native compliance results.

## MGT-001

Tenant workload networks SHALL have no direct route to infrastructure management interfaces.


### MGT-001.A01

**Assertion:** Complete source obligation; all applicable clauses must be satisfied: Tenant workload networks SHALL have no direct route to infrastructure management interfaces.

**Owner / location:** Management operations / Approved management/IAM/key/state service and privileged execution boundaries

**Disposition:** EXTERNAL_SERVICE_AND_OPERATING_CONTROL_REQUIRED. **Evidence class:** NATIVE_NOT_RUN; related local fixtures/engine checks are narrower evidence, not satisfaction

**Artifact or required operating record:** Native role/route/key/backend configuration, owner-approved recovery procedure and independently retained audit records — specifically: Complete source obligation; all applicable clauses must be satisfied: Tenant workload networks SHALL have no direct route to infrastructure management interfaces.

**Available related source:** [docs/current/TAD-infrastructure.md](../../current/TAD-infrastructure.md) · [docs/current/interface-agreements.md](../../current/interface-agreements.md)

**Verification:** Observe both authorized use and denied cross-authority access, then exercise the declared loss/recovery case. Baseline procedures: CT-004, CT-026

**Remaining dependency:** Actual protected management transport, independent recovery, native least privilege and the selected state/key service are not supplied by network readback tools.

**Review state:** PROPOSED_ALLOCATION; actual applicability, named authority and evidence assignment pending

## MGT-002

Administrative access SHALL originate from an authorized management access path and traverse management-specific security controls.


### MGT-002.A01

**Assertion:** Complete source obligation; all applicable clauses must be satisfied: Administrative access SHALL originate from an authorized management access path and traverse management-specific security controls.

**Owner / location:** Management operations / Approved management/IAM/key/state service and privileged execution boundaries

**Disposition:** EXTERNAL_SERVICE_AND_OPERATING_CONTROL_REQUIRED. **Evidence class:** NATIVE_NOT_RUN; related local fixtures/engine checks are narrower evidence, not satisfaction

**Artifact or required operating record:** Native role/route/key/backend configuration, owner-approved recovery procedure and independently retained audit records — specifically: Complete source obligation; all applicable clauses must be satisfied: Administrative access SHALL originate from an authorized management access path and traverse management-specific security controls.

**Available related source:** [docs/current/TAD-infrastructure.md](../../current/TAD-infrastructure.md) · [docs/current/interface-agreements.md](../../current/interface-agreements.md)

**Verification:** Observe both authorized use and denied cross-authority access, then exercise the declared loss/recovery case. Baseline procedures: CT-026, CT-027

**Remaining dependency:** Actual protected management transport, independent recovery, native least privilege and the selected state/key service are not supplied by network readback tools.

**Review state:** PROPOSED_ALLOCATION; actual applicability, named authority and evidence assignment pending

## MGT-003

Automation identities used to manage tenant workloads SHALL be separated from identities able to modify the physical fabric, security edge, or management foundation.


### MGT-003.A01

**Assertion:** Complete source obligation; all applicable clauses must be satisfied: Automation identities used to manage tenant workloads SHALL be separated from identities able to modify the physical fabric, security edge, or management foundation.

**Owner / location:** Automation platform / Approved management/IAM/key/state service and privileged execution boundaries

**Disposition:** EXTERNAL_SERVICE_AND_OPERATING_CONTROL_REQUIRED. **Evidence class:** NATIVE_NOT_RUN; related local fixtures/engine checks are narrower evidence, not satisfaction

**Artifact or required operating record:** Native role/route/key/backend configuration, owner-approved recovery procedure and independently retained audit records — specifically: Complete source obligation; all applicable clauses must be satisfied: Automation identities used to manage tenant workloads SHALL be separated from identities able to modify the physical fabric, security edge, or management foundation.

**Available related source:** [docs/current/TAD-infrastructure.md](../../current/TAD-infrastructure.md) · [docs/current/interface-agreements.md](../../current/interface-agreements.md)

**Verification:** Observe both authorized use and denied cross-authority access, then exercise the declared loss/recovery case. Baseline procedures: CT-019, CT-044

**Remaining dependency:** Actual protected management transport, independent recovery, native least privilege and the selected state/key service are not supplied by network readback tools.

**Review state:** PROPOSED_ALLOCATION; actual applicability, named authority and evidence assignment pending

## MGT-004

Break-glass access SHALL be separately controlled, strongly authenticated, logged, time-bounded where feasible, and periodically tested.


### MGT-004.A01

**Assertion:** Complete source obligation; all applicable clauses must be satisfied: Break-glass access SHALL be separately controlled, strongly authenticated, logged, time-bounded where feasible, and periodically tested.

**Owner / location:** Management operations / Approved management/IAM/key/state service and privileged execution boundaries

**Disposition:** EXTERNAL_SERVICE_AND_OPERATING_CONTROL_REQUIRED. **Evidence class:** NATIVE_NOT_RUN; related local fixtures/engine checks are narrower evidence, not satisfaction

**Artifact or required operating record:** Native role/route/key/backend configuration, owner-approved recovery procedure and independently retained audit records — specifically: Complete source obligation; all applicable clauses must be satisfied: Break-glass access SHALL be separately controlled, strongly authenticated, logged, time-bounded where feasible, and periodically tested.

**Available related source:** [docs/current/TAD-infrastructure.md](../../current/TAD-infrastructure.md) · [docs/current/interface-agreements.md](../../current/interface-agreements.md)

**Verification:** Observe both authorized use and denied cross-authority access, then exercise the declared loss/recovery case. Baseline procedures: CT-027, CT-079

**Remaining dependency:** Actual protected management transport, independent recovery, native least privilege and the selected state/key service are not supplied by network readback tools.

**Review state:** PROPOSED_ALLOCATION; actual applicability, named authority and evidence assignment pending

### MGT-004.A02

**Assertion:** Separate emergency authority

**Owner / location:** Management operations / Approved management/IAM/key/state service and privileged execution boundaries

**Disposition:** EXTERNAL_SERVICE_AND_OPERATING_CONTROL_REQUIRED. **Evidence class:** NATIVE_NOT_RUN; related local fixtures/engine checks are narrower evidence, not satisfaction

**Artifact or required operating record:** Native role/route/key/backend configuration, owner-approved recovery procedure and independently retained audit records — specifically: Separate emergency authority

**Available related source:** [docs/current/TAD-infrastructure.md](../../current/TAD-infrastructure.md) · [docs/current/interface-agreements.md](../../current/interface-agreements.md)

**Verification:** Observe both authorized use and denied cross-authority access, then exercise the declared loss/recovery case. Baseline procedures: CT-027, CT-079

**Remaining dependency:** Actual protected management transport, independent recovery, native least privilege and the selected state/key service are not supplied by network readback tools.

**Review state:** PROPOSED_ALLOCATION; actual applicability, named authority and evidence assignment pending

### MGT-004.A03

**Assertion:** Strong emergency authentication

**Owner / location:** Management operations / Approved management/IAM/key/state service and privileged execution boundaries

**Disposition:** EXTERNAL_SERVICE_AND_OPERATING_CONTROL_REQUIRED. **Evidence class:** NATIVE_NOT_RUN; related local fixtures/engine checks are narrower evidence, not satisfaction

**Artifact or required operating record:** Native role/route/key/backend configuration, owner-approved recovery procedure and independently retained audit records — specifically: Strong emergency authentication

**Available related source:** [docs/current/TAD-infrastructure.md](../../current/TAD-infrastructure.md) · [docs/current/interface-agreements.md](../../current/interface-agreements.md)

**Verification:** Observe both authorized use and denied cross-authority access, then exercise the declared loss/recovery case. Baseline procedures: CT-027, CT-079

**Remaining dependency:** Actual protected management transport, independent recovery, native least privilege and the selected state/key service are not supplied by network readback tools.

**Review state:** PROPOSED_ALLOCATION; actual applicability, named authority and evidence assignment pending

### MGT-004.A04

**Assertion:** Emergency access logging

**Owner / location:** Management operations / Approved management/IAM/key/state service and privileged execution boundaries

**Disposition:** EXTERNAL_SERVICE_AND_OPERATING_CONTROL_REQUIRED. **Evidence class:** NATIVE_NOT_RUN; related local fixtures/engine checks are narrower evidence, not satisfaction

**Artifact or required operating record:** Native role/route/key/backend configuration, owner-approved recovery procedure and independently retained audit records — specifically: Emergency access logging

**Available related source:** [docs/current/TAD-infrastructure.md](../../current/TAD-infrastructure.md) · [docs/current/interface-agreements.md](../../current/interface-agreements.md)

**Verification:** Observe both authorized use and denied cross-authority access, then exercise the declared loss/recovery case. Baseline procedures: CT-027, CT-079

**Remaining dependency:** Actual protected management transport, independent recovery, native least privilege and the selected state/key service are not supplied by network readback tools.

**Review state:** PROPOSED_ALLOCATION; actual applicability, named authority and evidence assignment pending

### MGT-004.A05

**Assertion:** Bounded access where feasible

**Owner / location:** Management operations / Approved management/IAM/key/state service and privileged execution boundaries

**Disposition:** EXTERNAL_SERVICE_AND_OPERATING_CONTROL_REQUIRED. **Evidence class:** NATIVE_NOT_RUN; related local fixtures/engine checks are narrower evidence, not satisfaction

**Artifact or required operating record:** Native role/route/key/backend configuration, owner-approved recovery procedure and independently retained audit records — specifically: Bounded access where feasible

**Available related source:** [docs/current/TAD-infrastructure.md](../../current/TAD-infrastructure.md) · [docs/current/interface-agreements.md](../../current/interface-agreements.md)

**Verification:** Observe both authorized use and denied cross-authority access, then exercise the declared loss/recovery case. Baseline procedures: CT-027, CT-079

**Remaining dependency:** Actual protected management transport, independent recovery, native least privilege and the selected state/key service are not supplied by network readback tools.

**Review state:** PROPOSED_ALLOCATION; actual applicability, named authority and evidence assignment pending

### MGT-004.A06

**Assertion:** Periodic actual recovery exercise

**Owner / location:** Management operations / Approved management/IAM/key/state service and privileged execution boundaries

**Disposition:** EXTERNAL_SERVICE_AND_OPERATING_CONTROL_REQUIRED. **Evidence class:** NATIVE_NOT_RUN; related local fixtures/engine checks are narrower evidence, not satisfaction

**Artifact or required operating record:** Native role/route/key/backend configuration, owner-approved recovery procedure and independently retained audit records — specifically: Periodic actual recovery exercise

**Available related source:** [docs/current/TAD-infrastructure.md](../../current/TAD-infrastructure.md) · [docs/current/interface-agreements.md](../../current/interface-agreements.md)

**Verification:** Observe both authorized use and denied cross-authority access, then exercise the declared loss/recovery case. Baseline procedures: CT-027, CT-079

**Remaining dependency:** Actual protected management transport, independent recovery, native least privilege and the selected state/key service are not supplied by network readback tools.

**Review state:** PROPOSED_ALLOCATION; actual applicability, named authority and evidence assignment pending

## MGT-005

The implementation SHALL document independent MZ semantics, OOB transport dependencies, remote-management boundary and privileged identity controls; tenant-facing APIs SHALL NOT expose infrastructure administration.


### MGT-005.A01

**Assertion:** Complete source obligation; all applicable clauses must be satisfied: The implementation SHALL document independent MZ semantics, OOB transport dependencies, remote-management boundary and privileged identity controls; tenant-facing APIs SHALL NOT expose infrastructure administration.

**Owner / location:** Management operations / Approved management/IAM/key/state service and privileged execution boundaries

**Disposition:** EXTERNAL_SERVICE_AND_OPERATING_CONTROL_REQUIRED. **Evidence class:** NATIVE_NOT_RUN; related local fixtures/engine checks are narrower evidence, not satisfaction

**Artifact or required operating record:** Native role/route/key/backend configuration, owner-approved recovery procedure and independently retained audit records — specifically: Complete source obligation; all applicable clauses must be satisfied: The implementation SHALL document independent MZ semantics, OOB transport dependencies, remote-management boundary and privileged identity controls; tenant-facing APIs SHALL NOT expose infrastructure administration.

**Available related source:** [docs/current/TAD-infrastructure.md](../../current/TAD-infrastructure.md) · [docs/current/interface-agreements.md](../../current/interface-agreements.md)

**Verification:** Observe both authorized use and denied cross-authority access, then exercise the declared loss/recovery case. Baseline procedures: CT-004, CT-026, CT-055

**Remaining dependency:** Actual protected management transport, independent recovery, native least privilege and the selected state/key service are not supplied by network readback tools.

**Review state:** PROPOSED_ALLOCATION; actual applicability, named authority and evidence assignment pending

### MGT-005.A02

**Assertion:** MZ security semantics

**Owner / location:** Management operations / Approved management/IAM/key/state service and privileged execution boundaries

**Disposition:** EXTERNAL_SERVICE_AND_OPERATING_CONTROL_REQUIRED. **Evidence class:** NATIVE_NOT_RUN; related local fixtures/engine checks are narrower evidence, not satisfaction

**Artifact or required operating record:** Native role/route/key/backend configuration, owner-approved recovery procedure and independently retained audit records — specifically: MZ security semantics

**Available related source:** [docs/current/TAD-infrastructure.md](../../current/TAD-infrastructure.md) · [docs/current/interface-agreements.md](../../current/interface-agreements.md)

**Verification:** Observe both authorized use and denied cross-authority access, then exercise the declared loss/recovery case. Baseline procedures: CT-004, CT-026, CT-055

**Remaining dependency:** Actual protected management transport, independent recovery, native least privilege and the selected state/key service are not supplied by network readback tools.

**Review state:** PROPOSED_ALLOCATION; actual applicability, named authority and evidence assignment pending

### MGT-005.A03

**Assertion:** Physical/logical OOB dependencies

**Owner / location:** Management operations / Approved management/IAM/key/state service and privileged execution boundaries

**Disposition:** EXTERNAL_SERVICE_AND_OPERATING_CONTROL_REQUIRED. **Evidence class:** NATIVE_NOT_RUN; related local fixtures/engine checks are narrower evidence, not satisfaction

**Artifact or required operating record:** Native role/route/key/backend configuration, owner-approved recovery procedure and independently retained audit records — specifically: Physical/logical OOB dependencies

**Available related source:** [docs/current/TAD-infrastructure.md](../../current/TAD-infrastructure.md) · [docs/current/interface-agreements.md](../../current/interface-agreements.md)

**Verification:** Observe both authorized use and denied cross-authority access, then exercise the declared loss/recovery case. Baseline procedures: CT-004, CT-026, CT-055

**Remaining dependency:** Actual protected management transport, independent recovery, native least privilege and the selected state/key service are not supplied by network readback tools.

**Review state:** PROPOSED_ALLOCATION; actual applicability, named authority and evidence assignment pending

### MGT-005.A04

**Assertion:** Remote-management boundary

**Owner / location:** Management operations / Approved management/IAM/key/state service and privileged execution boundaries

**Disposition:** EXTERNAL_SERVICE_AND_OPERATING_CONTROL_REQUIRED. **Evidence class:** NATIVE_NOT_RUN; related local fixtures/engine checks are narrower evidence, not satisfaction

**Artifact or required operating record:** Native role/route/key/backend configuration, owner-approved recovery procedure and independently retained audit records — specifically: Remote-management boundary

**Available related source:** [docs/current/TAD-infrastructure.md](../../current/TAD-infrastructure.md) · [docs/current/interface-agreements.md](../../current/interface-agreements.md)

**Verification:** Observe both authorized use and denied cross-authority access, then exercise the declared loss/recovery case. Baseline procedures: CT-004, CT-026, CT-055

**Remaining dependency:** Actual protected management transport, independent recovery, native least privilege and the selected state/key service are not supplied by network readback tools.

**Review state:** PROPOSED_ALLOCATION; actual applicability, named authority and evidence assignment pending

### MGT-005.A05

**Assertion:** Privileged identity control

**Owner / location:** Management operations / Approved management/IAM/key/state service and privileged execution boundaries

**Disposition:** EXTERNAL_SERVICE_AND_OPERATING_CONTROL_REQUIRED. **Evidence class:** NATIVE_NOT_RUN; related local fixtures/engine checks are narrower evidence, not satisfaction

**Artifact or required operating record:** Native role/route/key/backend configuration, owner-approved recovery procedure and independently retained audit records — specifically: Privileged identity control

**Available related source:** [docs/current/TAD-infrastructure.md](../../current/TAD-infrastructure.md) · [docs/current/interface-agreements.md](../../current/interface-agreements.md)

**Verification:** Observe both authorized use and denied cross-authority access, then exercise the declared loss/recovery case. Baseline procedures: CT-004, CT-026, CT-055

**Remaining dependency:** Actual protected management transport, independent recovery, native least privilege and the selected state/key service are not supplied by network readback tools.

**Review state:** PROPOSED_ALLOCATION; actual applicability, named authority and evidence assignment pending

### MGT-005.A06

**Assertion:** Tenant-facing interface excludes infrastructure administration

**Owner / location:** Management operations / Approved management/IAM/key/state service and privileged execution boundaries

**Disposition:** EXTERNAL_SERVICE_AND_OPERATING_CONTROL_REQUIRED. **Evidence class:** NATIVE_NOT_RUN; related local fixtures/engine checks are narrower evidence, not satisfaction

**Artifact or required operating record:** Native role/route/key/backend configuration, owner-approved recovery procedure and independently retained audit records — specifically: Tenant-facing interface excludes infrastructure administration

**Available related source:** [docs/current/TAD-infrastructure.md](../../current/TAD-infrastructure.md) · [docs/current/interface-agreements.md](../../current/interface-agreements.md)

**Verification:** Observe both authorized use and denied cross-authority access, then exercise the declared loss/recovery case. Baseline procedures: CT-004, CT-026, CT-055

**Remaining dependency:** Actual protected management transport, independent recovery, native least privilege and the selected state/key service are not supplied by network readback tools.

**Review state:** PROPOSED_ALLOCATION; actual applicability, named authority and evidence assignment pending
