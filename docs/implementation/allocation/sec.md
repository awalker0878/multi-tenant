# SEC — assertion allocation

[Allocation index](../assertion-allocation.md) · [Unchanged requirement catalogue](../../assurance/requirements.md)

These are source-grounded proposed allocations, not native compliance results.

## SEC-001

Static privileged provider credentials SHALL NOT be embedded in Terraform source code.


### SEC-001.A01

**Assertion:** Complete source obligation; all applicable clauses must be satisfied: Static privileged provider credentials SHALL NOT be embedded in Terraform source code.

**Owner / location:** Automation platform / Approved management/IAM/key/state service and privileged execution boundaries

**Disposition:** EXTERNAL_SERVICE_AND_OPERATING_CONTROL_REQUIRED. **Evidence class:** NATIVE_NOT_RUN; related local fixtures/engine checks are narrower evidence, not satisfaction

**Artifact or required operating record:** Native role/route/key/backend configuration, owner-approved recovery procedure and independently retained audit records — specifically: Complete source obligation; all applicable clauses must be satisfied: Static privileged provider credentials SHALL NOT be embedded in Terraform source code.

**Available related source:** [docs/current/TAD-infrastructure.md](../../current/TAD-infrastructure.md) · [docs/current/interface-agreements.md](../../current/interface-agreements.md)

**Verification:** Observe both authorized use and denied cross-authority access, then exercise the declared loss/recovery case. Baseline procedures: CT-043

**Remaining dependency:** Actual protected management transport, independent recovery, native least privilege and the selected state/key service are not supplied by network readback tools.

**Review state:** PROPOSED_ALLOCATION; actual applicability, named authority and evidence assignment pending

## SEC-002

Automation identities SHALL use least privilege and separate duties by control domain.


### SEC-002.A01

**Assertion:** Complete source obligation; all applicable clauses must be satisfied: Automation identities SHALL use least privilege and separate duties by control domain.

**Owner / location:** Automation platform / Approved management/IAM/key/state service and privileged execution boundaries

**Disposition:** EXTERNAL_SERVICE_AND_OPERATING_CONTROL_REQUIRED. **Evidence class:** NATIVE_NOT_RUN; related local fixtures/engine checks are narrower evidence, not satisfaction

**Artifact or required operating record:** Native role/route/key/backend configuration, owner-approved recovery procedure and independently retained audit records — specifically: Complete source obligation; all applicable clauses must be satisfied: Automation identities SHALL use least privilege and separate duties by control domain.

**Available related source:** [docs/current/TAD-infrastructure.md](../../current/TAD-infrastructure.md) · [docs/current/interface-agreements.md](../../current/interface-agreements.md)

**Verification:** Observe both authorized use and denied cross-authority access, then exercise the declared loss/recovery case. Baseline procedures: CT-019, CT-044, CT-079

**Remaining dependency:** Actual protected management transport, independent recovery, native least privilege and the selected state/key service are not supplied by network readback tools.

**Review state:** PROPOSED_ALLOCATION; actual applicability, named authority and evidence assignment pending

## SEC-003

Credential rotation, revocation, and break-glass recovery SHALL be tested as part of the platform operational profile.


### SEC-003.A01

**Assertion:** Complete source obligation; all applicable clauses must be satisfied: Credential rotation, revocation, and break-glass recovery SHALL be tested as part of the platform operational profile.

**Owner / location:** Automation platform / Approved management/IAM/key/state service and privileged execution boundaries

**Disposition:** EXTERNAL_SERVICE_AND_OPERATING_CONTROL_REQUIRED. **Evidence class:** NATIVE_NOT_RUN; related local fixtures/engine checks are narrower evidence, not satisfaction

**Artifact or required operating record:** Native role/route/key/backend configuration, owner-approved recovery procedure and independently retained audit records — specifically: Complete source obligation; all applicable clauses must be satisfied: Credential rotation, revocation, and break-glass recovery SHALL be tested as part of the platform operational profile.

**Available related source:** [docs/current/TAD-infrastructure.md](../../current/TAD-infrastructure.md) · [docs/current/interface-agreements.md](../../current/interface-agreements.md)

**Verification:** Observe both authorized use and denied cross-authority access, then exercise the declared loss/recovery case. Baseline procedures: CT-027, CT-028, CT-043

**Remaining dependency:** Actual protected management transport, independent recovery, native least privilege and the selected state/key service are not supplied by network readback tools.

**Review state:** PROPOSED_ALLOCATION; actual applicability, named authority and evidence assignment pending

### SEC-003.A02

**Assertion:** Actual credential rotation

**Owner / location:** Automation platform / Approved management/IAM/key/state service and privileged execution boundaries

**Disposition:** EXTERNAL_SERVICE_AND_OPERATING_CONTROL_REQUIRED. **Evidence class:** NATIVE_NOT_RUN; related local fixtures/engine checks are narrower evidence, not satisfaction

**Artifact or required operating record:** Native role/route/key/backend configuration, owner-approved recovery procedure and independently retained audit records — specifically: Actual credential rotation

**Available related source:** [docs/current/TAD-infrastructure.md](../../current/TAD-infrastructure.md) · [docs/current/interface-agreements.md](../../current/interface-agreements.md)

**Verification:** Observe both authorized use and denied cross-authority access, then exercise the declared loss/recovery case. Baseline procedures: CT-027, CT-028, CT-043

**Remaining dependency:** Actual protected management transport, independent recovery, native least privilege and the selected state/key service are not supplied by network readback tools.

**Review state:** PROPOSED_ALLOCATION; actual applicability, named authority and evidence assignment pending

### SEC-003.A03

**Assertion:** Revocation

**Owner / location:** Automation platform / Approved management/IAM/key/state service and privileged execution boundaries

**Disposition:** EXTERNAL_SERVICE_AND_OPERATING_CONTROL_REQUIRED. **Evidence class:** NATIVE_NOT_RUN; related local fixtures/engine checks are narrower evidence, not satisfaction

**Artifact or required operating record:** Native role/route/key/backend configuration, owner-approved recovery procedure and independently retained audit records — specifically: Revocation

**Available related source:** [docs/current/TAD-infrastructure.md](../../current/TAD-infrastructure.md) · [docs/current/interface-agreements.md](../../current/interface-agreements.md)

**Verification:** Observe both authorized use and denied cross-authority access, then exercise the declared loss/recovery case. Baseline procedures: CT-027, CT-028, CT-043

**Remaining dependency:** Actual protected management transport, independent recovery, native least privilege and the selected state/key service are not supplied by network readback tools.

**Review state:** PROPOSED_ALLOCATION; actual applicability, named authority and evidence assignment pending

### SEC-003.A04

**Assertion:** Break-glass recovery exercise

**Owner / location:** Automation platform / Approved management/IAM/key/state service and privileged execution boundaries

**Disposition:** EXTERNAL_SERVICE_AND_OPERATING_CONTROL_REQUIRED. **Evidence class:** NATIVE_NOT_RUN; related local fixtures/engine checks are narrower evidence, not satisfaction

**Artifact or required operating record:** Native role/route/key/backend configuration, owner-approved recovery procedure and independently retained audit records — specifically: Break-glass recovery exercise

**Available related source:** [docs/current/TAD-infrastructure.md](../../current/TAD-infrastructure.md) · [docs/current/interface-agreements.md](../../current/interface-agreements.md)

**Verification:** Observe both authorized use and denied cross-authority access, then exercise the declared loss/recovery case. Baseline procedures: CT-027, CT-028, CT-043

**Remaining dependency:** Actual protected management transport, independent recovery, native least privilege and the selected state/key service are not supplied by network readback tools.

**Review state:** PROPOSED_ALLOCATION; actual applicability, named authority and evidence assignment pending

## SEC-004

Where supported and verified, sensitive values SHOULD use ephemeral/write-only mechanisms; all remaining secret-bearing plan/state/log artifacts SHALL be classified, encrypted, access-controlled and tested for unintended disclosure.


### SEC-004.A01

**Assertion:** Complete source obligation; all applicable clauses must be satisfied: Where supported and verified, sensitive values SHOULD use ephemeral/write-only mechanisms; all remaining secret-bearing plan/state/log artifacts SHALL be classified, encrypted, access-controlled and tested for unintended disclosure.

**Owner / location:** Automation platform / Approved management/IAM/key/state service and privileged execution boundaries

**Disposition:** EXTERNAL_SERVICE_AND_OPERATING_CONTROL_REQUIRED. **Evidence class:** NATIVE_NOT_RUN; related local fixtures/engine checks are narrower evidence, not satisfaction

**Artifact or required operating record:** Native role/route/key/backend configuration, owner-approved recovery procedure and independently retained audit records — specifically: Complete source obligation; all applicable clauses must be satisfied: Where supported and verified, sensitive values SHOULD use ephemeral/write-only mechanisms; all remaining secret-bearing plan/state/log artifacts SHALL be classified, encrypted, access-controlled and tested for unintended disclosure.

**Available related source:** [docs/current/TAD-infrastructure.md](../../current/TAD-infrastructure.md) · [docs/current/interface-agreements.md](../../current/interface-agreements.md)

**Verification:** Observe both authorized use and denied cross-authority access, then exercise the declared loss/recovery case. Baseline procedures: CT-043, CT-044

**Remaining dependency:** Actual protected management transport, independent recovery, native least privilege and the selected state/key service are not supplied by network readback tools.

**Review state:** PROPOSED_ALLOCATION; actual applicability, named authority and evidence assignment pending

### SEC-004.A02

**Assertion:** Where supported and verified, sensitive values SHOULD use ephemeral/write-only mechanisms

**Owner / location:** Automation platform / Approved management/IAM/key/state service and privileged execution boundaries

**Disposition:** EXTERNAL_SERVICE_AND_OPERATING_CONTROL_REQUIRED. **Evidence class:** NATIVE_NOT_RUN; related local fixtures/engine checks are narrower evidence, not satisfaction

**Artifact or required operating record:** Native role/route/key/backend configuration, owner-approved recovery procedure and independently retained audit records — specifically: Where supported and verified, sensitive values SHOULD use ephemeral/write-only mechanisms

**Available related source:** [docs/current/TAD-infrastructure.md](../../current/TAD-infrastructure.md) · [docs/current/interface-agreements.md](../../current/interface-agreements.md)

**Verification:** Observe both authorized use and denied cross-authority access, then exercise the declared loss/recovery case. Baseline procedures: CT-043, CT-044

**Remaining dependency:** Actual protected management transport, independent recovery, native least privilege and the selected state/key service are not supplied by network readback tools.

**Review state:** PROPOSED_ALLOCATION; actual applicability, named authority and evidence assignment pending

### SEC-004.A03

**Assertion:** all remaining secret-bearing plan/state/log artifacts SHALL be classified, encrypted, access-controlled and tested for unintended disclosure.

**Owner / location:** Automation platform / Approved management/IAM/key/state service and privileged execution boundaries

**Disposition:** EXTERNAL_SERVICE_AND_OPERATING_CONTROL_REQUIRED. **Evidence class:** NATIVE_NOT_RUN; related local fixtures/engine checks are narrower evidence, not satisfaction

**Artifact or required operating record:** Native role/route/key/backend configuration, owner-approved recovery procedure and independently retained audit records — specifically: all remaining secret-bearing plan/state/log artifacts SHALL be classified, encrypted, access-controlled and tested for unintended disclosure.

**Available related source:** [docs/current/TAD-infrastructure.md](../../current/TAD-infrastructure.md) · [docs/current/interface-agreements.md](../../current/interface-agreements.md)

**Verification:** Observe both authorized use and denied cross-authority access, then exercise the declared loss/recovery case. Baseline procedures: CT-043, CT-044

**Remaining dependency:** Actual protected management transport, independent recovery, native least privilege and the selected state/key service are not supplied by network readback tools.

**Review state:** PROPOSED_ALLOCATION; actual applicability, named authority and evidence assignment pending
