# STATE — assertion allocation

[Allocation index](../assertion-allocation.md) · [Unchanged requirement catalogue](../../assurance/requirements.md)

These are source-grounded proposed allocations, not native compliance results.

## STATE-001

No single routine tenant automation identity SHALL have authority to modify physical fabric, management foundation, security edge, and tenant workloads simultaneously.


### STATE-001.A01

**Assertion:** Complete source obligation; all applicable clauses must be satisfied: No single routine tenant automation identity SHALL have authority to modify physical fabric, management foundation, security edge, and tenant workloads simultaneously.

**Owner / location:** Automation platform / Approved management/IAM/key/state service and privileged execution boundaries

**Disposition:** EXTERNAL_SERVICE_AND_OPERATING_CONTROL_REQUIRED. **Evidence class:** NATIVE_NOT_RUN; related local fixtures/engine checks are narrower evidence, not satisfaction

**Artifact or required operating record:** Native role/route/key/backend configuration, owner-approved recovery procedure and independently retained audit records — specifically: Complete source obligation; all applicable clauses must be satisfied: No single routine tenant automation identity SHALL have authority to modify physical fabric, management foundation, security edge, and tenant workloads simultaneously.

**Available related source:** [docs/current/TAD-infrastructure.md](../../current/TAD-infrastructure.md) · [docs/current/interface-agreements.md](../../current/interface-agreements.md)

**Verification:** Observe both authorized use and denied cross-authority access, then exercise the declared loss/recovery case. Baseline procedures: CT-019, CT-044

**Remaining dependency:** Actual protected management transport, independent recovery, native least privilege and the selected state/key service are not supplied by network readback tools.

**Review state:** PROPOSED_ALLOCATION; actual applicability, named authority and evidence assignment pending

### STATE-001.A02

**Assertion:** Foundation writer isolated from tenant writer

**Owner / location:** Automation platform / Approved management/IAM/key/state service and privileged execution boundaries

**Disposition:** EXTERNAL_SERVICE_AND_OPERATING_CONTROL_REQUIRED. **Evidence class:** NATIVE_NOT_RUN; related local fixtures/engine checks are narrower evidence, not satisfaction

**Artifact or required operating record:** Native role/route/key/backend configuration, owner-approved recovery procedure and independently retained audit records — specifically: Foundation writer isolated from tenant writer

**Available related source:** [docs/current/TAD-infrastructure.md](../../current/TAD-infrastructure.md) · [docs/current/interface-agreements.md](../../current/interface-agreements.md)

**Verification:** Observe both authorized use and denied cross-authority access, then exercise the declared loss/recovery case. Baseline procedures: CT-019, CT-044

**Remaining dependency:** Actual protected management transport, independent recovery, native least privilege and the selected state/key service are not supplied by network readback tools.

**Review state:** PROPOSED_ALLOCATION; actual applicability, named authority and evidence assignment pending

### STATE-001.A03

**Assertion:** Management writer isolated

**Owner / location:** Automation platform / Approved management/IAM/key/state service and privileged execution boundaries

**Disposition:** EXTERNAL_SERVICE_AND_OPERATING_CONTROL_REQUIRED. **Evidence class:** NATIVE_NOT_RUN; related local fixtures/engine checks are narrower evidence, not satisfaction

**Artifact or required operating record:** Native role/route/key/backend configuration, owner-approved recovery procedure and independently retained audit records — specifically: Management writer isolated

**Available related source:** [docs/current/TAD-infrastructure.md](../../current/TAD-infrastructure.md) · [docs/current/interface-agreements.md](../../current/interface-agreements.md)

**Verification:** Observe both authorized use and denied cross-authority access, then exercise the declared loss/recovery case. Baseline procedures: CT-019, CT-044

**Remaining dependency:** Actual protected management transport, independent recovery, native least privilege and the selected state/key service are not supplied by network readback tools.

**Review state:** PROPOSED_ALLOCATION; actual applicability, named authority and evidence assignment pending

### STATE-001.A04

**Assertion:** Security-edge writer isolated

**Owner / location:** Automation platform / Approved management/IAM/key/state service and privileged execution boundaries

**Disposition:** EXTERNAL_SERVICE_AND_OPERATING_CONTROL_REQUIRED. **Evidence class:** NATIVE_NOT_RUN; related local fixtures/engine checks are narrower evidence, not satisfaction

**Artifact or required operating record:** Native role/route/key/backend configuration, owner-approved recovery procedure and independently retained audit records — specifically: Security-edge writer isolated

**Available related source:** [docs/current/TAD-infrastructure.md](../../current/TAD-infrastructure.md) · [docs/current/interface-agreements.md](../../current/interface-agreements.md)

**Verification:** Observe both authorized use and denied cross-authority access, then exercise the declared loss/recovery case. Baseline procedures: CT-019, CT-044

**Remaining dependency:** Actual protected management transport, independent recovery, native least privilege and the selected state/key service are not supplied by network readback tools.

**Review state:** PROPOSED_ALLOCATION; actual applicability, named authority and evidence assignment pending

### STATE-001.A05

**Assertion:** Tenant/workload writer cannot span all authorities

**Owner / location:** Automation platform / Approved management/IAM/key/state service and privileged execution boundaries

**Disposition:** EXTERNAL_SERVICE_AND_OPERATING_CONTROL_REQUIRED. **Evidence class:** NATIVE_NOT_RUN; related local fixtures/engine checks are narrower evidence, not satisfaction

**Artifact or required operating record:** Native role/route/key/backend configuration, owner-approved recovery procedure and independently retained audit records — specifically: Tenant/workload writer cannot span all authorities

**Available related source:** [docs/current/TAD-infrastructure.md](../../current/TAD-infrastructure.md) · [docs/current/interface-agreements.md](../../current/interface-agreements.md)

**Verification:** Observe both authorized use and denied cross-authority access, then exercise the declared loss/recovery case. Baseline procedures: CT-019, CT-044

**Remaining dependency:** Actual protected management transport, independent recovery, native least privilege and the selected state/key service are not supplied by network readback tools.

**Review state:** PROPOSED_ALLOCATION; actual applicability, named authority and evidence assignment pending

## STATE-002

Remote state backends SHALL use encryption, strong authentication, locking, recovery/versioning, access logging, and separation appropriate to the sensitivity of contained data.


### STATE-002.A01

**Assertion:** Complete source obligation; all applicable clauses must be satisfied: Remote state backends SHALL use encryption, strong authentication, locking, recovery/versioning, access logging, and separation appropriate to the sensitivity of contained data.

**Owner / location:** Automation platform / Approved management/IAM/key/state service and privileged execution boundaries

**Disposition:** EXTERNAL_SERVICE_AND_OPERATING_CONTROL_REQUIRED. **Evidence class:** NATIVE_NOT_RUN; related local fixtures/engine checks are narrower evidence, not satisfaction

**Artifact or required operating record:** Native role/route/key/backend configuration, owner-approved recovery procedure and independently retained audit records — specifically: Complete source obligation; all applicable clauses must be satisfied: Remote state backends SHALL use encryption, strong authentication, locking, recovery/versioning, access logging, and separation appropriate to the sensitivity of contained data.

**Available related source:** [docs/current/TAD-infrastructure.md](../../current/TAD-infrastructure.md) · [docs/current/interface-agreements.md](../../current/interface-agreements.md)

**Verification:** Observe both authorized use and denied cross-authority access, then exercise the declared loss/recovery case. Baseline procedures: CT-043, CT-044, CT-055

**Remaining dependency:** Actual protected management transport, independent recovery, native least privilege and the selected state/key service are not supplied by network readback tools.

**Review state:** PROPOSED_ALLOCATION; actual applicability, named authority and evidence assignment pending

### STATE-002.A02

**Assertion:** Backend encryption

**Owner / location:** Automation platform / Approved management/IAM/key/state service and privileged execution boundaries

**Disposition:** EXTERNAL_SERVICE_AND_OPERATING_CONTROL_REQUIRED. **Evidence class:** NATIVE_NOT_RUN; related local fixtures/engine checks are narrower evidence, not satisfaction

**Artifact or required operating record:** Native role/route/key/backend configuration, owner-approved recovery procedure and independently retained audit records — specifically: Backend encryption

**Available related source:** [docs/current/TAD-infrastructure.md](../../current/TAD-infrastructure.md) · [docs/current/interface-agreements.md](../../current/interface-agreements.md)

**Verification:** Observe both authorized use and denied cross-authority access, then exercise the declared loss/recovery case. Baseline procedures: CT-043, CT-044, CT-055

**Remaining dependency:** Actual protected management transport, independent recovery, native least privilege and the selected state/key service are not supplied by network readback tools.

**Review state:** PROPOSED_ALLOCATION; actual applicability, named authority and evidence assignment pending

### STATE-002.A03

**Assertion:** Strong authentication

**Owner / location:** Automation platform / Approved management/IAM/key/state service and privileged execution boundaries

**Disposition:** EXTERNAL_SERVICE_AND_OPERATING_CONTROL_REQUIRED. **Evidence class:** NATIVE_NOT_RUN; related local fixtures/engine checks are narrower evidence, not satisfaction

**Artifact or required operating record:** Native role/route/key/backend configuration, owner-approved recovery procedure and independently retained audit records — specifically: Strong authentication

**Available related source:** [docs/current/TAD-infrastructure.md](../../current/TAD-infrastructure.md) · [docs/current/interface-agreements.md](../../current/interface-agreements.md)

**Verification:** Observe both authorized use and denied cross-authority access, then exercise the declared loss/recovery case. Baseline procedures: CT-043, CT-044, CT-055

**Remaining dependency:** Actual protected management transport, independent recovery, native least privilege and the selected state/key service are not supplied by network readback tools.

**Review state:** PROPOSED_ALLOCATION; actual applicability, named authority and evidence assignment pending

### STATE-002.A04

**Assertion:** Exclusive locking

**Owner / location:** Automation platform / Approved management/IAM/key/state service and privileged execution boundaries

**Disposition:** EXTERNAL_SERVICE_AND_OPERATING_CONTROL_REQUIRED. **Evidence class:** NATIVE_NOT_RUN; related local fixtures/engine checks are narrower evidence, not satisfaction

**Artifact or required operating record:** Native role/route/key/backend configuration, owner-approved recovery procedure and independently retained audit records — specifically: Exclusive locking

**Available related source:** [docs/current/TAD-infrastructure.md](../../current/TAD-infrastructure.md) · [docs/current/interface-agreements.md](../../current/interface-agreements.md)

**Verification:** Observe both authorized use and denied cross-authority access, then exercise the declared loss/recovery case. Baseline procedures: CT-043, CT-044, CT-055

**Remaining dependency:** Actual protected management transport, independent recovery, native least privilege and the selected state/key service are not supplied by network readback tools.

**Review state:** PROPOSED_ALLOCATION; actual applicability, named authority and evidence assignment pending

### STATE-002.A05

**Assertion:** Version/history recovery

**Owner / location:** Automation platform / Approved management/IAM/key/state service and privileged execution boundaries

**Disposition:** EXTERNAL_SERVICE_AND_OPERATING_CONTROL_REQUIRED. **Evidence class:** NATIVE_NOT_RUN; related local fixtures/engine checks are narrower evidence, not satisfaction

**Artifact or required operating record:** Native role/route/key/backend configuration, owner-approved recovery procedure and independently retained audit records — specifically: Version/history recovery

**Available related source:** [docs/current/TAD-infrastructure.md](../../current/TAD-infrastructure.md) · [docs/current/interface-agreements.md](../../current/interface-agreements.md)

**Verification:** Observe both authorized use and denied cross-authority access, then exercise the declared loss/recovery case. Baseline procedures: CT-043, CT-044, CT-055

**Remaining dependency:** Actual protected management transport, independent recovery, native least privilege and the selected state/key service are not supplied by network readback tools.

**Review state:** PROPOSED_ALLOCATION; actual applicability, named authority and evidence assignment pending

### STATE-002.A06

**Assertion:** Access logging

**Owner / location:** Automation platform / Approved management/IAM/key/state service and privileged execution boundaries

**Disposition:** EXTERNAL_SERVICE_AND_OPERATING_CONTROL_REQUIRED. **Evidence class:** NATIVE_NOT_RUN; related local fixtures/engine checks are narrower evidence, not satisfaction

**Artifact or required operating record:** Native role/route/key/backend configuration, owner-approved recovery procedure and independently retained audit records — specifically: Access logging

**Available related source:** [docs/current/TAD-infrastructure.md](../../current/TAD-infrastructure.md) · [docs/current/interface-agreements.md](../../current/interface-agreements.md)

**Verification:** Observe both authorized use and denied cross-authority access, then exercise the declared loss/recovery case. Baseline procedures: CT-043, CT-044, CT-055

**Remaining dependency:** Actual protected management transport, independent recovery, native least privilege and the selected state/key service are not supplied by network readback tools.

**Review state:** PROPOSED_ALLOCATION; actual applicability, named authority and evidence assignment pending

### STATE-002.A07

**Assertion:** Sensitivity-appropriate authority separation

**Owner / location:** Automation platform / Approved management/IAM/key/state service and privileged execution boundaries

**Disposition:** EXTERNAL_SERVICE_AND_OPERATING_CONTROL_REQUIRED. **Evidence class:** NATIVE_NOT_RUN; related local fixtures/engine checks are narrower evidence, not satisfaction

**Artifact or required operating record:** Native role/route/key/backend configuration, owner-approved recovery procedure and independently retained audit records — specifically: Sensitivity-appropriate authority separation

**Available related source:** [docs/current/TAD-infrastructure.md](../../current/TAD-infrastructure.md) · [docs/current/interface-agreements.md](../../current/interface-agreements.md)

**Verification:** Observe both authorized use and denied cross-authority access, then exercise the declared loss/recovery case. Baseline procedures: CT-043, CT-044, CT-055

**Remaining dependency:** Actual protected management transport, independent recovery, native least privilege and the selected state/key service are not supplied by network readback tools.

**Review state:** PROPOSED_ALLOCATION; actual applicability, named authority and evidence assignment pending

## STATE-003

Cross-state/external-service changes SHALL use a journaled dependency workflow with scoped outputs, idempotent stage completion and data-safe compensation; state-file restoration SHALL NOT be represented as infrastructure rollback.


### STATE-003.A01

**Assertion:** Complete source obligation; all applicable clauses must be satisfied: Cross-state/external-service changes SHALL use a journaled dependency workflow with scoped outputs, idempotent stage completion and data-safe compensation; state-file restoration SHALL NOT be represented as infrastructure rollback.

**Owner / location:** Automation platform / Approved management/IAM/key/state service and privileged execution boundaries

**Disposition:** EXTERNAL_SERVICE_AND_OPERATING_CONTROL_REQUIRED. **Evidence class:** NATIVE_NOT_RUN; related local fixtures/engine checks are narrower evidence, not satisfaction

**Artifact or required operating record:** Native role/route/key/backend configuration, owner-approved recovery procedure and independently retained audit records — specifically: Complete source obligation; all applicable clauses must be satisfied: Cross-state/external-service changes SHALL use a journaled dependency workflow with scoped outputs, idempotent stage completion and data-safe compensation; state-file restoration SHALL NOT be represented as infrastructure rollback.

**Available related source:** [docs/current/TAD-infrastructure.md](../../current/TAD-infrastructure.md) · [docs/current/interface-agreements.md](../../current/interface-agreements.md)

**Verification:** Observe both authorized use and denied cross-authority access, then exercise the declared loss/recovery case. Baseline procedures: CT-044, CT-045, CT-070

**Remaining dependency:** Actual protected management transport, independent recovery, native least privilege and the selected state/key service are not supplied by network readback tools.

**Review state:** PROPOSED_ALLOCATION; actual applicability, named authority and evidence assignment pending

### STATE-003.A02

**Assertion:** Journaled dependency workflow

**Owner / location:** Automation platform / Approved management/IAM/key/state service and privileged execution boundaries

**Disposition:** EXTERNAL_SERVICE_AND_OPERATING_CONTROL_REQUIRED. **Evidence class:** NATIVE_NOT_RUN; related local fixtures/engine checks are narrower evidence, not satisfaction

**Artifact or required operating record:** Native role/route/key/backend configuration, owner-approved recovery procedure and independently retained audit records — specifically: Journaled dependency workflow

**Available related source:** [docs/current/TAD-infrastructure.md](../../current/TAD-infrastructure.md) · [docs/current/interface-agreements.md](../../current/interface-agreements.md)

**Verification:** Observe both authorized use and denied cross-authority access, then exercise the declared loss/recovery case. Baseline procedures: CT-044, CT-045, CT-070

**Remaining dependency:** Actual protected management transport, independent recovery, native least privilege and the selected state/key service are not supplied by network readback tools.

**Review state:** PROPOSED_ALLOCATION; actual applicability, named authority and evidence assignment pending

### STATE-003.A03

**Assertion:** Minimal scoped outputs

**Owner / location:** Automation platform / Approved management/IAM/key/state service and privileged execution boundaries

**Disposition:** EXTERNAL_SERVICE_AND_OPERATING_CONTROL_REQUIRED. **Evidence class:** NATIVE_NOT_RUN; related local fixtures/engine checks are narrower evidence, not satisfaction

**Artifact or required operating record:** Native role/route/key/backend configuration, owner-approved recovery procedure and independently retained audit records — specifically: Minimal scoped outputs

**Available related source:** [docs/current/TAD-infrastructure.md](../../current/TAD-infrastructure.md) · [docs/current/interface-agreements.md](../../current/interface-agreements.md)

**Verification:** Observe both authorized use and denied cross-authority access, then exercise the declared loss/recovery case. Baseline procedures: CT-044, CT-045, CT-070

**Remaining dependency:** Actual protected management transport, independent recovery, native least privilege and the selected state/key service are not supplied by network readback tools.

**Review state:** PROPOSED_ALLOCATION; actual applicability, named authority and evidence assignment pending

### STATE-003.A04

**Assertion:** Idempotent stage completion

**Owner / location:** Automation platform / Approved management/IAM/key/state service and privileged execution boundaries

**Disposition:** EXTERNAL_SERVICE_AND_OPERATING_CONTROL_REQUIRED. **Evidence class:** NATIVE_NOT_RUN; related local fixtures/engine checks are narrower evidence, not satisfaction

**Artifact or required operating record:** Native role/route/key/backend configuration, owner-approved recovery procedure and independently retained audit records — specifically: Idempotent stage completion

**Available related source:** [docs/current/TAD-infrastructure.md](../../current/TAD-infrastructure.md) · [docs/current/interface-agreements.md](../../current/interface-agreements.md)

**Verification:** Observe both authorized use and denied cross-authority access, then exercise the declared loss/recovery case. Baseline procedures: CT-044, CT-045, CT-070

**Remaining dependency:** Actual protected management transport, independent recovery, native least privilege and the selected state/key service are not supplied by network readback tools.

**Review state:** PROPOSED_ALLOCATION; actual applicability, named authority and evidence assignment pending

### STATE-003.A05

**Assertion:** Data-safe compensation

**Owner / location:** Automation platform / Approved management/IAM/key/state service and privileged execution boundaries

**Disposition:** EXTERNAL_SERVICE_AND_OPERATING_CONTROL_REQUIRED. **Evidence class:** NATIVE_NOT_RUN; related local fixtures/engine checks are narrower evidence, not satisfaction

**Artifact or required operating record:** Native role/route/key/backend configuration, owner-approved recovery procedure and independently retained audit records — specifically: Data-safe compensation

**Available related source:** [docs/current/TAD-infrastructure.md](../../current/TAD-infrastructure.md) · [docs/current/interface-agreements.md](../../current/interface-agreements.md)

**Verification:** Observe both authorized use and denied cross-authority access, then exercise the declared loss/recovery case. Baseline procedures: CT-044, CT-045, CT-070

**Remaining dependency:** Actual protected management transport, independent recovery, native least privilege and the selected state/key service are not supplied by network readback tools.

**Review state:** PROPOSED_ALLOCATION; actual applicability, named authority and evidence assignment pending

### STATE-003.A06

**Assertion:** State-file restoration is not infrastructure rollback

**Owner / location:** Automation platform / Approved management/IAM/key/state service and privileged execution boundaries

**Disposition:** EXTERNAL_SERVICE_AND_OPERATING_CONTROL_REQUIRED. **Evidence class:** NATIVE_NOT_RUN; related local fixtures/engine checks are narrower evidence, not satisfaction

**Artifact or required operating record:** Native role/route/key/backend configuration, owner-approved recovery procedure and independently retained audit records — specifically: State-file restoration is not infrastructure rollback

**Available related source:** [docs/current/TAD-infrastructure.md](../../current/TAD-infrastructure.md) · [docs/current/interface-agreements.md](../../current/interface-agreements.md)

**Verification:** Observe both authorized use and denied cross-authority access, then exercise the declared loss/recovery case. Baseline procedures: CT-044, CT-045, CT-070

**Remaining dependency:** Actual protected management transport, independent recovery, native least privilege and the selected state/key service are not supplied by network readback tools.

**Review state:** PROPOSED_ALLOCATION; actual applicability, named authority and evidence assignment pending
