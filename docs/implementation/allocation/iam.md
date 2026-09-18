# IAM — assertion allocation

[Allocation index](../assertion-allocation.md) · [Unchanged requirement catalogue](../../assurance/requirements.md)

These are source-grounded proposed allocations, not native compliance results.

## IAM-001

Human, workload and automation identities SHALL have separately scoped authorization, credential lifecycle and accountability; no tenant identity SHALL acquire provider foundation authority through role or group inheritance.


### IAM-001.A01

**Assertion:** Complete source obligation; all applicable clauses must be satisfied: Human, workload and automation identities SHALL have separately scoped authorization, credential lifecycle and accountability; no tenant identity SHALL acquire provider foundation authority through role or group inheritance.

**Owner / location:** Identity operations / Approved management/IAM/key/state service and privileged execution boundaries

**Disposition:** EXTERNAL_SERVICE_AND_OPERATING_CONTROL_REQUIRED. **Evidence class:** NATIVE_NOT_RUN; related local fixtures/engine checks are narrower evidence, not satisfaction

**Artifact or required operating record:** Native role/route/key/backend configuration, owner-approved recovery procedure and independently retained audit records — specifically: Complete source obligation; all applicable clauses must be satisfied: Human, workload and automation identities SHALL have separately scoped authorization, credential lifecycle and accountability; no tenant identity SHALL acquire provider foundation authority through role or group inheritance.

**Available related source:** [docs/current/TAD-infrastructure.md](../../current/TAD-infrastructure.md) · [docs/current/interface-agreements.md](../../current/interface-agreements.md)

**Verification:** Observe both authorized use and denied cross-authority access, then exercise the declared loss/recovery case. Baseline procedures: CT-019, CT-027, CT-028

**Remaining dependency:** Actual protected management transport, independent recovery, native least privilege and the selected state/key service are not supplied by network readback tools.

**Review state:** PROPOSED_ALLOCATION; actual applicability, named authority and evidence assignment pending

### IAM-001.A02

**Assertion:** Human, workload and automation identities SHALL have separately scoped authorization, credential lifecycle and accountability

**Owner / location:** Identity operations / Approved management/IAM/key/state service and privileged execution boundaries

**Disposition:** EXTERNAL_SERVICE_AND_OPERATING_CONTROL_REQUIRED. **Evidence class:** NATIVE_NOT_RUN; related local fixtures/engine checks are narrower evidence, not satisfaction

**Artifact or required operating record:** Native role/route/key/backend configuration, owner-approved recovery procedure and independently retained audit records — specifically: Human, workload and automation identities SHALL have separately scoped authorization, credential lifecycle and accountability

**Available related source:** [docs/current/TAD-infrastructure.md](../../current/TAD-infrastructure.md) · [docs/current/interface-agreements.md](../../current/interface-agreements.md)

**Verification:** Observe both authorized use and denied cross-authority access, then exercise the declared loss/recovery case. Baseline procedures: CT-019, CT-027, CT-028

**Remaining dependency:** Actual protected management transport, independent recovery, native least privilege and the selected state/key service are not supplied by network readback tools.

**Review state:** PROPOSED_ALLOCATION; actual applicability, named authority and evidence assignment pending

### IAM-001.A03

**Assertion:** no tenant identity SHALL acquire provider foundation authority through role or group inheritance.

**Owner / location:** Identity operations / Approved management/IAM/key/state service and privileged execution boundaries

**Disposition:** EXTERNAL_SERVICE_AND_OPERATING_CONTROL_REQUIRED. **Evidence class:** NATIVE_NOT_RUN; related local fixtures/engine checks are narrower evidence, not satisfaction

**Artifact or required operating record:** Native role/route/key/backend configuration, owner-approved recovery procedure and independently retained audit records — specifically: no tenant identity SHALL acquire provider foundation authority through role or group inheritance.

**Available related source:** [docs/current/TAD-infrastructure.md](../../current/TAD-infrastructure.md) · [docs/current/interface-agreements.md](../../current/interface-agreements.md)

**Verification:** Observe both authorized use and denied cross-authority access, then exercise the declared loss/recovery case. Baseline procedures: CT-019, CT-027, CT-028

**Remaining dependency:** Actual protected management transport, independent recovery, native least privilege and the selected state/key service are not supplied by network readback tools.

**Review state:** PROPOSED_ALLOCATION; actual applicability, named authority and evidence assignment pending

## IAM-002

Privileged access SHALL use the approved hardened path, strong authentication, least privilege and time-bound delegation; emergency and supplier access SHALL be logged, tested and revoked after use.


### IAM-002.A01

**Assertion:** Complete source obligation; all applicable clauses must be satisfied: Privileged access SHALL use the approved hardened path, strong authentication, least privilege and time-bound delegation; emergency and supplier access SHALL be logged, tested and revoked after use.

**Owner / location:** Identity operations / Approved management/IAM/key/state service and privileged execution boundaries

**Disposition:** EXTERNAL_SERVICE_AND_OPERATING_CONTROL_REQUIRED. **Evidence class:** NATIVE_NOT_RUN; related local fixtures/engine checks are narrower evidence, not satisfaction

**Artifact or required operating record:** Native role/route/key/backend configuration, owner-approved recovery procedure and independently retained audit records — specifically: Complete source obligation; all applicable clauses must be satisfied: Privileged access SHALL use the approved hardened path, strong authentication, least privilege and time-bound delegation; emergency and supplier access SHALL be logged, tested and revoked after use.

**Available related source:** [docs/current/TAD-infrastructure.md](../../current/TAD-infrastructure.md) · [docs/current/interface-agreements.md](../../current/interface-agreements.md)

**Verification:** Observe both authorized use and denied cross-authority access, then exercise the declared loss/recovery case. Baseline procedures: CT-026, CT-027, CT-079

**Remaining dependency:** Actual protected management transport, independent recovery, native least privilege and the selected state/key service are not supplied by network readback tools.

**Review state:** PROPOSED_ALLOCATION; actual applicability, named authority and evidence assignment pending

### IAM-002.A02

**Assertion:** Privileged access SHALL use the approved hardened path, strong authentication, least privilege and time-bound delegation

**Owner / location:** Identity operations / Approved management/IAM/key/state service and privileged execution boundaries

**Disposition:** EXTERNAL_SERVICE_AND_OPERATING_CONTROL_REQUIRED. **Evidence class:** NATIVE_NOT_RUN; related local fixtures/engine checks are narrower evidence, not satisfaction

**Artifact or required operating record:** Native role/route/key/backend configuration, owner-approved recovery procedure and independently retained audit records — specifically: Privileged access SHALL use the approved hardened path, strong authentication, least privilege and time-bound delegation

**Available related source:** [docs/current/TAD-infrastructure.md](../../current/TAD-infrastructure.md) · [docs/current/interface-agreements.md](../../current/interface-agreements.md)

**Verification:** Observe both authorized use and denied cross-authority access, then exercise the declared loss/recovery case. Baseline procedures: CT-026, CT-027, CT-079

**Remaining dependency:** Actual protected management transport, independent recovery, native least privilege and the selected state/key service are not supplied by network readback tools.

**Review state:** PROPOSED_ALLOCATION; actual applicability, named authority and evidence assignment pending

### IAM-002.A03

**Assertion:** emergency and supplier access SHALL be logged, tested and revoked after use.

**Owner / location:** Identity operations / Approved management/IAM/key/state service and privileged execution boundaries

**Disposition:** EXTERNAL_SERVICE_AND_OPERATING_CONTROL_REQUIRED. **Evidence class:** NATIVE_NOT_RUN; related local fixtures/engine checks are narrower evidence, not satisfaction

**Artifact or required operating record:** Native role/route/key/backend configuration, owner-approved recovery procedure and independently retained audit records — specifically: emergency and supplier access SHALL be logged, tested and revoked after use.

**Available related source:** [docs/current/TAD-infrastructure.md](../../current/TAD-infrastructure.md) · [docs/current/interface-agreements.md](../../current/interface-agreements.md)

**Verification:** Observe both authorized use and denied cross-authority access, then exercise the declared loss/recovery case. Baseline procedures: CT-026, CT-027, CT-079

**Remaining dependency:** Actual protected management transport, independent recovery, native least privilege and the selected state/key service are not supplied by network readback tools.

**Review state:** PROPOSED_ALLOCATION; actual applicability, named authority and evidence assignment pending

## IAM-003

Credential and session revocation SHALL be verified at the consuming service within the approved propagation interval, including cached tokens and delegated grants.


### IAM-003.A01

**Assertion:** Complete source obligation; all applicable clauses must be satisfied: Credential and session revocation SHALL be verified at the consuming service within the approved propagation interval, including cached tokens and delegated grants.

**Owner / location:** Identity operations / Approved management/IAM/key/state service and privileged execution boundaries

**Disposition:** EXTERNAL_SERVICE_AND_OPERATING_CONTROL_REQUIRED. **Evidence class:** NATIVE_NOT_RUN; related local fixtures/engine checks are narrower evidence, not satisfaction

**Artifact or required operating record:** Native role/route/key/backend configuration, owner-approved recovery procedure and independently retained audit records — specifically: Complete source obligation; all applicable clauses must be satisfied: Credential and session revocation SHALL be verified at the consuming service within the approved propagation interval, including cached tokens and delegated grants.

**Available related source:** [docs/current/TAD-infrastructure.md](../../current/TAD-infrastructure.md) · [docs/current/interface-agreements.md](../../current/interface-agreements.md)

**Verification:** Observe both authorized use and denied cross-authority access, then exercise the declared loss/recovery case. Baseline procedures: CT-028, CT-077, CT-079

**Remaining dependency:** Actual protected management transport, independent recovery, native least privilege and the selected state/key service are not supplied by network readback tools.

**Review state:** PROPOSED_ALLOCATION; actual applicability, named authority and evidence assignment pending
