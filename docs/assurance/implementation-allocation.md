# Proposed assertion-level implementation allocation

**State: proposed engineering allocation. No native requirement is marked satisfied.** Each original requirement is retained verbatim and compound obligations are separated into exact source-focus spans. A span inherits its complete requirement; this is not a new normative rewrite or a claim that every possible interpretation is exhausted.

The allocation distinguishes concrete enforcement locations, responsible source roles, partial candidate code, external services, manual/governance decisions and unimplemented work. Every focus needs a site-specific configuration record and actual evidence. Unresolved mandatory responsibility blocks Service Ready.

[Editable allocation CSV](../../sources/assurance/implementation_allocation.csv) · [Canonical records](../../sources/assurance/implementation_allocation.json) · [Verification families](verification-families.md)

Coverage: 194 original requirements; 370 proposed assertion focuses. These are allocation records, not counts of implemented controls or tests.

## Requirement navigation

[ARCH-001](#ARCH-001) · [ARCH-002](#ARCH-002) · [ARCH-003](#ARCH-003) · [ARCH-004](#ARCH-004) · [SCOPE-001](#SCOPE-001) · [INV-001](#INV-001) · [INV-002](#INV-002) · [INV-003](#INV-003) · [INV-004](#INV-004) · [INV-005](#INV-005) · [INV-006](#INV-006) · [INV-007](#INV-007) · [REF-001](#REF-001) · [REF-002](#REF-002) · [DOC-001](#DOC-001) · [AUTH-001](#AUTH-001) · [STD-001](#STD-001) · [STD-002](#STD-002) · [CAT-001](#CAT-001) · [CAT-002](#CAT-002) · [THR-001](#THR-001) · [MODEL-001](#MODEL-001) · [MODEL-002](#MODEL-002) · [TEN-001](#TEN-001) · [TEN-002](#TEN-002) · [TEN-003](#TEN-003) · [WSD-001](#WSD-001) · [WSD-002](#WSD-002) · [WSD-003](#WSD-003) · [SDI-001](#SDI-001) · [SDI-002](#SDI-002) · [SDI-003](#SDI-003) · [SDI-004](#SDI-004) · [ZONE-001](#ZONE-001) · [ZONE-002](#ZONE-002) · [ZIP-001](#ZIP-001) · [ZIP-002](#ZIP-002) · [ZIP-003](#ZIP-003) · [ZIP-004](#ZIP-004) · [ZIP-005](#ZIP-005) · [ZIP-006](#ZIP-006) · [ZIP-007](#ZIP-007) · [MGT-001](#MGT-001) · [MGT-002](#MGT-002) · [MGT-003](#MGT-003) · [MGT-004](#MGT-004) · [MGT-005](#MGT-005) · [OVL-001](#OVL-001) · [OVL-002](#OVL-002) · [OVL-003](#OVL-003) · [RTE-001](#RTE-001) · [RTE-002](#RTE-002) · [RTE-003](#RTE-003) · [RTE-004](#RTE-004) · [IPAM-001](#IPAM-001) · [IPAM-002](#IPAM-002) · [IPAM-003](#IPAM-003) · [IPAM-004](#IPAM-004) · [IPV6-001](#IPV6-001) · [IPV6-002](#IPV6-002) · [IPV6-003](#IPV6-003) · [SVC-001](#SVC-001) · [SVC-002](#SVC-002) · [SVC-003](#SVC-003) · [ING-001](#ING-001) · [ING-002](#ING-002) · [EGR-001](#EGR-001) · [EGR-002](#EGR-002) · [EXP-001](#EXP-001) · [MICRO-001](#MICRO-001) · [MICRO-002](#MICRO-002) · [MICRO-003](#MICRO-003) · [EDGE-001](#EDGE-001) · [EDGE-002](#EDGE-002) · [SITE-001](#SITE-001) · [SITE-002](#SITE-002) · [SITE-003](#SITE-003) · [SITE-004](#SITE-004) · [CMP-001](#CMP-001) · [CMP-002](#CMP-002) · [CMP-003](#CMP-003) · [STO-001](#STO-001) · [STO-002](#STO-002) · [STO-003](#STO-003) · [IAM-001](#IAM-001) · [IAM-002](#IAM-002) · [IAM-003](#IAM-003) · [CRY-001](#CRY-001) · [CRY-002](#CRY-002) · [CRY-003](#CRY-003) · [IMG-001](#IMG-001) · [IMG-002](#IMG-002) · [BKP-001](#BKP-001) · [BKP-002](#BKP-002) · [BKP-003](#BKP-003) · [BKP-004](#BKP-004) · [REL-001](#REL-001) · [REL-002](#REL-002) · [PLACE-001](#PLACE-001) · [PLACE-002](#PLACE-002) · [PLACE-003](#PLACE-003) · [SVCM-001](#SVCM-001) · [SVCM-002](#SVCM-002) · [RESP-001](#RESP-001) · [FAB-001](#FAB-001) · [FAB-002](#FAB-002) · [FAB-003](#FAB-003) · [FAB-004](#FAB-004) · [EVPN-001](#EVPN-001) · [EVPN-002](#EVPN-002) · [PORT-001](#PORT-001) · [PORT-002](#PORT-002) · [PORT-003](#PORT-003) · [QUAL-001](#QUAL-001) · [NUT-001](#NUT-001) · [NUT-002](#NUT-002) · [NUT-003](#NUT-003) · [NUT-004](#NUT-004) · [NSX-001](#NSX-001) · [NSX-002](#NSX-002) · [NSX-003](#NSX-003) · [OS-001](#OS-001) · [OS-002](#OS-002) · [OS-003](#OS-003) · [FUT-001](#FUT-001) · [FUT-002](#FUT-002) · [FUT-003](#FUT-003) · [API-001](#API-001) · [API-002](#API-002) · [API-003](#API-003) · [POL-001](#POL-001) · [POL-002](#POL-002) · [FLOW-001](#FLOW-001) · [AUTO-001](#AUTO-001) · [AUTO-002](#AUTO-002) · [AUTO-003](#AUTO-003) · [TF-001](#TF-001) · [TF-002](#TF-002) · [TF-003](#TF-003) · [TF-004](#TF-004) · [TF-005](#TF-005) · [STATE-001](#STATE-001) · [STATE-002](#STATE-002) · [STATE-003](#STATE-003) · [CICD-001](#CICD-001) · [CICD-002](#CICD-002) · [SUP-001](#SUP-001) · [SEC-001](#SEC-001) · [SEC-002](#SEC-002) · [SEC-003](#SEC-003) · [SEC-004](#SEC-004) · [DRIFT-001](#DRIFT-001) · [DRIFT-002](#DRIFT-002) · [DRIFT-003](#DRIFT-003) · [ASSUR-001](#ASSUR-001) · [ASSUR-002](#ASSUR-002) · [ASSUR-003](#ASSUR-003) · [TEST-001](#TEST-001) · [TEST-002](#TEST-002) · [TEST-003](#TEST-003) · [TEST-004](#TEST-004) · [EVID-001](#EVID-001) · [EVID-002](#EVID-002) · [EVID-003](#EVID-003) · [OBS-001](#OBS-001) · [OBS-002](#OBS-002) · [OBS-003](#OBS-003) · [CAP-001](#CAP-001) · [CAP-002](#CAP-002) · [CAP-003](#CAP-003) · [FAIL-001](#FAIL-001) · [FAIL-002](#FAIL-002) · [FAIL-003](#FAIL-003) · [REC-001](#REC-001) · [REC-002](#REC-002) · [VULN-001](#VULN-001) · [VULN-002](#VULN-002) · [IR-001](#IR-001) · [IR-002](#IR-002) · [LIFE-001](#LIFE-001) · [LIFE-002](#LIFE-002) · [LIFE-003](#LIFE-003) · [MIG-001](#MIG-001) · [MIG-002](#MIG-002) · [MIG-003](#MIG-003) · [OPS-001](#OPS-001) · [OPS-002](#OPS-002) · [EXC-001](#EXC-001) · [EXC-002](#EXC-002) · [EXC-003](#EXC-003) · [ONB-001](#ONB-001) · [DEL-001](#DEL-001) · [DEL-002](#DEL-002) · [ACPT-001](#ACPT-001)

<a id="ARCH-001"></a>
## ARCH-001

The hosting contract SHALL be vendor neutral and SHALL NOT require consumers to specify vendor-specific identifiers or topology objects.

**Source role:** Architecture authority. **Original design references:** RA §1; RA §2; RA §20.

**Enforcement location:** Accepted service/profile and topology records; native domain/identity boundaries implement selected constraints.

**Delivery disposition:** `PARTIAL_DESIGN_AND_CANDIDATE`.

**Related code/procedure:** [docs/architecture/RAD.md](../architecture/RAD.md) · [docs/engineering/TAD.md](../engineering/TAD.md) · [tools/input_review.py](../../tools/input_review.py). These artifacts do not individually or collectively establish the entire requirement.

**Current evidence limit:** SOURCE_AND_LOCAL_FIXTURE_ONLY_OR_NOT_IMPLEMENTED; NOT_NATIVE_QUALIFIED. Actual native evidence is not supplied.

**Outstanding dependency:** No complete authoritative service/profile registry, tenant role enforcement or actual placement/edge evidence is supplied. Input screening covers only its enumerated examples and cannot accept the complete service.

| Assertion | Exact source focus | Required site-specific completion |
| --- | --- | --- |
| ARCH-001/A01 | The hosting contract SHALL be vendor neutral and SHALL NOT require consumers to specify vendor-specific identifiers or topology objects. | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |

**Verification:** [CT-016](test-specifications.md#CT-016) · [CT-017](test-specifications.md#CT-017). Apply the referenced procedure to the actual enforcement location and this focus; include effective negative/failure observations where the original criterion requires them.

**Applicability and acceptance:** TO_BE_DECIDED_FOR_ACTUAL_SERVICE; NOT_AUTO_NA. The accountable project role records applicability, configuration and evidence; this reusable allocation does not invent those decisions.

<a id="ARCH-002"></a>
## ARCH-002

Routine tenant and workload lifecycle operations SHOULD NOT require changes to physical leaf or spine configuration.

**Source role:** Architecture authority. **Original design references:** RA §1; RA §2; RA §20.

**Enforcement location:** Accepted service/profile and topology records; native domain/identity boundaries implement selected constraints.

**Delivery disposition:** `PARTIAL_DESIGN_AND_CANDIDATE`.

**Related code/procedure:** [docs/architecture/RAD.md](../architecture/RAD.md) · [docs/engineering/TAD.md](../engineering/TAD.md) · [tools/input_review.py](../../tools/input_review.py). These artifacts do not individually or collectively establish the entire requirement.

**Current evidence limit:** SOURCE_AND_LOCAL_FIXTURE_ONLY_OR_NOT_IMPLEMENTED; NOT_NATIVE_QUALIFIED. Actual native evidence is not supplied.

**Outstanding dependency:** No complete authoritative service/profile registry, tenant role enforcement or actual placement/edge evidence is supplied. Input screening covers only its enumerated examples and cannot accept the complete service.

| Assertion | Exact source focus | Required site-specific completion |
| --- | --- | --- |
| ARCH-002/A01 | Routine tenant and workload lifecycle operations SHOULD NOT require changes to physical leaf or spine configuration. | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |

**Verification:** [CT-071](test-specifications.md#CT-071) · [CT-072](test-specifications.md#CT-072). Apply the referenced procedure to the actual enforcement location and this focus; include effective negative/failure observations where the original criterion requires them.

**Applicability and acceptance:** TO_BE_DECIDED_FOR_ACTUAL_SERVICE; NOT_AUTO_NA. The accountable project role records applicability, configuration and evidence; this reusable allocation does not invent those decisions.

<a id="ARCH-003"></a>
## ARCH-003

All inter-zone paths SHALL be explicit and SHALL traverse the applicable ZIP/security edge.

**Source role:** Architecture authority. **Original design references:** RA §1; RA §2; RA §20.

**Enforcement location:** Accepted service/profile and topology records; native domain/identity boundaries implement selected constraints.

**Delivery disposition:** `PARTIAL_DESIGN_AND_CANDIDATE`.

**Related code/procedure:** [docs/architecture/RAD.md](../architecture/RAD.md) · [docs/engineering/TAD.md](../engineering/TAD.md) · [tools/input_review.py](../../tools/input_review.py). These artifacts do not individually or collectively establish the entire requirement.

**Current evidence limit:** SOURCE_AND_LOCAL_FIXTURE_ONLY_OR_NOT_IMPLEMENTED; NOT_NATIVE_QUALIFIED. Actual native evidence is not supplied.

**Outstanding dependency:** No complete authoritative service/profile registry, tenant role enforcement or actual placement/edge evidence is supplied. Input screening covers only its enumerated examples and cannot accept the complete service.

| Assertion | Exact source focus | Required site-specific completion |
| --- | --- | --- |
| ARCH-003/A01 | All inter-zone paths SHALL be explicit and SHALL traverse the applicable ZIP/security edge. | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |

**Verification:** [CT-003](test-specifications.md#CT-003) · [CT-025](test-specifications.md#CT-025). Apply the referenced procedure to the actual enforcement location and this focus; include effective negative/failure observations where the original criterion requires them.

**Applicability and acceptance:** TO_BE_DECIDED_FOR_ACTUAL_SERVICE; NOT_AUTO_NA. The accountable project role records applicability, configuration and evidence; this reusable allocation does not invent those decisions.

<a id="ARCH-004"></a>
## ARCH-004

Management/OOB traffic SHALL be separated from tenant operational traffic and SHALL have independently controlled access paths.

**Source role:** Architecture authority. **Original design references:** RA §1; RA §2; RA §20.

**Enforcement location:** Accepted service/profile and topology records; native domain/identity boundaries implement selected constraints.

**Delivery disposition:** `PARTIAL_DESIGN_AND_CANDIDATE`.

**Related code/procedure:** [docs/architecture/RAD.md](../architecture/RAD.md) · [docs/engineering/TAD.md](../engineering/TAD.md) · [tools/input_review.py](../../tools/input_review.py). These artifacts do not individually or collectively establish the entire requirement.

**Current evidence limit:** SOURCE_AND_LOCAL_FIXTURE_ONLY_OR_NOT_IMPLEMENTED; NOT_NATIVE_QUALIFIED. Actual native evidence is not supplied.

**Outstanding dependency:** No complete authoritative service/profile registry, tenant role enforcement or actual placement/edge evidence is supplied. Input screening covers only its enumerated examples and cannot accept the complete service.

| Assertion | Exact source focus | Required site-specific completion |
| --- | --- | --- |
| ARCH-004/A01 | Management/OOB traffic SHALL be separated from tenant operational traffic and SHALL have independently controlled access paths. | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |

**Verification:** [CT-004](test-specifications.md#CT-004) · [CT-026](test-specifications.md#CT-026). Apply the referenced procedure to the actual enforcement location and this focus; include effective negative/failure observations where the original criterion requires them.

**Applicability and acceptance:** TO_BE_DECIDED_FOR_ACTUAL_SERVICE; NOT_AUTO_NA. The accountable project role records applicability, configuration and evidence; this reusable allocation does not invent those decisions.

<a id="SCOPE-001"></a>
## SCOPE-001

Every implementation SHALL publish its offered service classes, supported information categories, excluded capabilities and required qualification evidence before accepting a production request.

**Source role:** Architecture authority. **Original design references:** RA §1; RA §2; RA §20.

**Enforcement location:** Accepted service/profile and topology records; native domain/identity boundaries implement selected constraints.

**Delivery disposition:** `PARTIAL_DESIGN_AND_CANDIDATE`.

**Related code/procedure:** [docs/architecture/RAD.md](../architecture/RAD.md) · [docs/engineering/TAD.md](../engineering/TAD.md) · [tools/input_review.py](../../tools/input_review.py). These artifacts do not individually or collectively establish the entire requirement.

**Current evidence limit:** SOURCE_AND_LOCAL_FIXTURE_ONLY_OR_NOT_IMPLEMENTED; NOT_NATIVE_QUALIFIED. Actual native evidence is not supplied.

**Outstanding dependency:** No complete authoritative service/profile registry, tenant role enforcement or actual placement/edge evidence is supplied. Input screening covers only its enumerated examples and cannot accept the complete service.

| Assertion | Exact source focus | Required site-specific completion |
| --- | --- | --- |
| SCOPE-001/A01 | Every implementation SHALL publish its offered service classes, supported information categories, excluded capabilities and required qualification evidence before accepting a production request. | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |

**Verification:** [CT-018](test-specifications.md#CT-018) · [CT-062](test-specifications.md#CT-062). Apply the referenced procedure to the actual enforcement location and this focus; include effective negative/failure observations where the original criterion requires them.

**Applicability and acceptance:** TO_BE_DECIDED_FOR_ACTUAL_SERVICE; NOT_AUTO_NA. The accountable project role records applicability, configuration and evidence; this reusable allocation does not invent those decisions.

<a id="INV-001"></a>
## INV-001

Tenant identity, security-zone identity, workload lifecycle, and platform realization are separate concepts.

**Source role:** Architecture authority. **Original design references:** RA §1; RA §28.

**Enforcement location:** Accepted service/profile and topology records; native domain/identity boundaries implement selected constraints.

**Delivery disposition:** `PARTIAL_DESIGN_AND_CANDIDATE`.

**Related code/procedure:** [docs/architecture/RAD.md](../architecture/RAD.md) · [docs/engineering/TAD.md](../engineering/TAD.md) · [tools/input_review.py](../../tools/input_review.py). These artifacts do not individually or collectively establish the entire requirement.

**Current evidence limit:** SOURCE_AND_LOCAL_FIXTURE_ONLY_OR_NOT_IMPLEMENTED; NOT_NATIVE_QUALIFIED. Actual native evidence is not supplied.

**Outstanding dependency:** No complete authoritative service/profile registry, tenant role enforcement or actual placement/edge evidence is supplied. Input screening covers only its enumerated examples and cannot accept the complete service.

| Assertion | Exact source focus | Required site-specific completion |
| --- | --- | --- |
| INV-001/A01 | Tenant identity, security-zone identity, workload lifecycle, and platform realization are separate concepts. | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |

**Verification:** [CT-016](test-specifications.md#CT-016) · [CT-070](test-specifications.md#CT-070). Apply the referenced procedure to the actual enforcement location and this focus; include effective negative/failure observations where the original criterion requires them.

**Applicability and acceptance:** TO_BE_DECIDED_FOR_ACTUAL_SERVICE; NOT_AUTO_NA. The accountable project role records applicability, configuration and evidence; this reusable allocation does not invent those decisions.

<a id="INV-002"></a>
## INV-002

A VPC, VRF, Tier-1 gateway, or Neutron router is an implementation mechanism, not the enterprise definition of a security zone.

**Source role:** Architecture authority. **Original design references:** RA §1; RA §28.

**Enforcement location:** Accepted service/profile and topology records; native domain/identity boundaries implement selected constraints.

**Delivery disposition:** `PARTIAL_DESIGN_AND_CANDIDATE`.

**Related code/procedure:** [docs/architecture/RAD.md](../architecture/RAD.md) · [docs/engineering/TAD.md](../engineering/TAD.md) · [tools/input_review.py](../../tools/input_review.py). These artifacts do not individually or collectively establish the entire requirement.

**Current evidence limit:** SOURCE_AND_LOCAL_FIXTURE_ONLY_OR_NOT_IMPLEMENTED; NOT_NATIVE_QUALIFIED. Actual native evidence is not supplied.

**Outstanding dependency:** No complete authoritative service/profile registry, tenant role enforcement or actual placement/edge evidence is supplied. Input screening covers only its enumerated examples and cannot accept the complete service.

| Assertion | Exact source focus | Required site-specific completion |
| --- | --- | --- |
| INV-002/A01 | A VPC, VRF, Tier-1 gateway, or Neutron router is an implementation mechanism, not the enterprise definition of a security zone. | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |

**Verification:** [CT-025](test-specifications.md#CT-025) · [CT-080](test-specifications.md#CT-080). Apply the referenced procedure to the actual enforcement location and this focus; include effective negative/failure observations where the original criterion requires them.

**Applicability and acceptance:** TO_BE_DECIDED_FOR_ACTUAL_SERVICE; NOT_AUTO_NA. The accountable project role records applicability, configuration and evidence; this reusable allocation does not invent those decisions.

<a id="INV-003"></a>
## INV-003

Routes are derived from authorized intent; workload owners do not provide arbitrary route tables, BGP peers, route targets, or prefix imports/exports.

**Source role:** Architecture authority. **Original design references:** RA §1; RA §28.

**Enforcement location:** Accepted service/profile and topology records; native domain/identity boundaries implement selected constraints.

**Delivery disposition:** `PARTIAL_DESIGN_AND_CANDIDATE`.

**Related code/procedure:** [docs/architecture/RAD.md](../architecture/RAD.md) · [docs/engineering/TAD.md](../engineering/TAD.md) · [tools/input_review.py](../../tools/input_review.py). These artifacts do not individually or collectively establish the entire requirement.

**Current evidence limit:** SOURCE_AND_LOCAL_FIXTURE_ONLY_OR_NOT_IMPLEMENTED; NOT_NATIVE_QUALIFIED. Actual native evidence is not supplied.

**Outstanding dependency:** No complete authoritative service/profile registry, tenant role enforcement or actual placement/edge evidence is supplied. Input screening covers only its enumerated examples and cannot accept the complete service.

| Assertion | Exact source focus | Required site-specific completion |
| --- | --- | --- |
| INV-003/A01 | Routes are derived from authorized intent | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |
| INV-003/A02 | workload owners do not provide arbitrary route tables, BGP peers, route targets, or prefix imports/exports. | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |

**Verification:** [CT-009](test-specifications.md#CT-009) · [CT-033](test-specifications.md#CT-033). Apply the referenced procedure to the actual enforcement location and this focus; include effective negative/failure observations where the original criterion requires them.

**Applicability and acceptance:** TO_BE_DECIDED_FOR_ACTUAL_SERVICE; NOT_AUTO_NA. The accountable project role records applicability, configuration and evidence; this reusable allocation does not invent those decisions.

<a id="INV-004"></a>
## INV-004

Shared services are exposed through explicit service bindings; broad reachability to a common-services supernet is not the default.

**Source role:** Architecture authority. **Original design references:** RA §1; RA §28.

**Enforcement location:** Accepted service/profile and topology records; native domain/identity boundaries implement selected constraints.

**Delivery disposition:** `PARTIAL_DESIGN_AND_CANDIDATE`.

**Related code/procedure:** [docs/architecture/RAD.md](../architecture/RAD.md) · [docs/engineering/TAD.md](../engineering/TAD.md) · [tools/input_review.py](../../tools/input_review.py). These artifacts do not individually or collectively establish the entire requirement.

**Current evidence limit:** SOURCE_AND_LOCAL_FIXTURE_ONLY_OR_NOT_IMPLEMENTED; NOT_NATIVE_QUALIFIED. Actual native evidence is not supplied.

**Outstanding dependency:** No complete authoritative service/profile registry, tenant role enforcement or actual placement/edge evidence is supplied. Input screening covers only its enumerated examples and cannot accept the complete service.

| Assertion | Exact source focus | Required site-specific completion |
| --- | --- | --- |
| INV-004/A01 | Shared services are exposed through explicit service bindings | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |
| INV-004/A02 | broad reachability to a common-services supernet is not the default. | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |

**Verification:** [CT-008](test-specifications.md#CT-008). Apply the referenced procedure to the actual enforcement location and this focus; include effective negative/failure observations where the original criterion requires them.

**Applicability and acceptance:** TO_BE_DECIDED_FOR_ACTUAL_SERVICE; NOT_AUTO_NA. The accountable project role records applicability, configuration and evidence; this reusable allocation does not invent those decisions.

<a id="INV-005"></a>
## INV-005

Portability means equivalent required outcomes and conformance, not identical topology.

**Source role:** Architecture authority. **Original design references:** RA §1; RA §28.

**Enforcement location:** Accepted service/profile and topology records; native domain/identity boundaries implement selected constraints.

**Delivery disposition:** `PARTIAL_DESIGN_AND_CANDIDATE`.

**Related code/procedure:** [docs/architecture/RAD.md](../architecture/RAD.md) · [docs/engineering/TAD.md](../engineering/TAD.md) · [tools/input_review.py](../../tools/input_review.py). These artifacts do not individually or collectively establish the entire requirement.

**Current evidence limit:** SOURCE_AND_LOCAL_FIXTURE_ONLY_OR_NOT_IMPLEMENTED; NOT_NATIVE_QUALIFIED. Actual native evidence is not supplied.

**Outstanding dependency:** No complete authoritative service/profile registry, tenant role enforcement or actual placement/edge evidence is supplied. Input screening covers only its enumerated examples and cannot accept the complete service.

| Assertion | Exact source focus | Required site-specific completion |
| --- | --- | --- |
| INV-005/A01 | Portability means equivalent required outcomes and conformance, not identical topology. | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |

**Verification:** [CT-016](test-specifications.md#CT-016) · [CT-060](test-specifications.md#CT-060). Apply the referenced procedure to the actual enforcement location and this focus; include effective negative/failure observations where the original criterion requires them.

**Applicability and acceptance:** TO_BE_DECIDED_FOR_ACTUAL_SERVICE; NOT_AUTO_NA. The accountable project role records applicability, configuration and evidence; this reusable allocation does not invent those decisions.

<a id="INV-006"></a>
## INV-006

A deployment is not Service Ready until realized state and security controls are verified.

**Source role:** Architecture authority. **Original design references:** RA §1; RA §28.

**Enforcement location:** Accepted service/profile and topology records; native domain/identity boundaries implement selected constraints.

**Delivery disposition:** `PARTIAL_DESIGN_AND_CANDIDATE`.

**Related code/procedure:** [docs/architecture/RAD.md](../architecture/RAD.md) · [docs/engineering/TAD.md](../engineering/TAD.md) · [tools/input_review.py](../../tools/input_review.py). These artifacts do not individually or collectively establish the entire requirement.

**Current evidence limit:** SOURCE_AND_LOCAL_FIXTURE_ONLY_OR_NOT_IMPLEMENTED; NOT_NATIVE_QUALIFIED. Actual native evidence is not supplied.

**Outstanding dependency:** No complete authoritative service/profile registry, tenant role enforcement or actual placement/edge evidence is supplied. Input screening covers only its enumerated examples and cannot accept the complete service.

| Assertion | Exact source focus | Required site-specific completion |
| --- | --- | --- |
| INV-006/A01 | A deployment is not Service Ready until realized state and security controls are verified. | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |

**Verification:** [CT-049](test-specifications.md#CT-049) · [CT-069](test-specifications.md#CT-069). Apply the referenced procedure to the actual enforcement location and this focus; include effective negative/failure observations where the original criterion requires them.

**Applicability and acceptance:** TO_BE_DECIDED_FOR_ACTUAL_SERVICE; NOT_AUTO_NA. The accountable project role records applicability, configuration and evidence; this reusable allocation does not invent those decisions.

<a id="INV-007"></a>
## INV-007

Failure of an admission or control-plane dependency SHALL fail new changes closed; failure SHALL NOT silently create a security bypass.

**Source role:** Architecture authority. **Original design references:** RA §1; RA §28.

**Enforcement location:** Accepted service/profile and topology records; native domain/identity boundaries implement selected constraints.

**Delivery disposition:** `PARTIAL_DESIGN_AND_CANDIDATE`.

**Related code/procedure:** [docs/architecture/RAD.md](../architecture/RAD.md) · [docs/engineering/TAD.md](../engineering/TAD.md) · [tools/input_review.py](../../tools/input_review.py). These artifacts do not individually or collectively establish the entire requirement.

**Current evidence limit:** SOURCE_AND_LOCAL_FIXTURE_ONLY_OR_NOT_IMPLEMENTED; NOT_NATIVE_QUALIFIED. Actual native evidence is not supplied.

**Outstanding dependency:** No complete authoritative service/profile registry, tenant role enforcement or actual placement/edge evidence is supplied. Input screening covers only its enumerated examples and cannot accept the complete service.

| Assertion | Exact source focus | Required site-specific completion |
| --- | --- | --- |
| INV-007/A01 | Failure of an admission or control-plane dependency SHALL fail new changes closed | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |
| INV-007/A02 | failure SHALL NOT silently create a security bypass. | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |

**Verification:** [CT-011](test-specifications.md#CT-011) · [CT-045](test-specifications.md#CT-045). Apply the referenced procedure to the actual enforcement location and this focus; include effective negative/failure observations where the original criterion requires them.

**Applicability and acceptance:** TO_BE_DECIDED_FOR_ACTUAL_SERVICE; NOT_AUTO_NA. The accountable project role records applicability, configuration and evidence; this reusable allocation does not invent those decisions.

<a id="REF-001"></a>
## REF-001

The service contract SHALL remain stable when a supported platform is replaced, provided the replacement platform passes the required conformance profile.

**Source role:** Architecture authority. **Original design references:** RA §1; RA §28.

**Enforcement location:** Accepted service/profile and topology records; native domain/identity boundaries implement selected constraints.

**Delivery disposition:** `PARTIAL_DESIGN_AND_CANDIDATE`.

**Related code/procedure:** [docs/architecture/RAD.md](../architecture/RAD.md) · [docs/engineering/TAD.md](../engineering/TAD.md) · [tools/input_review.py](../../tools/input_review.py). These artifacts do not individually or collectively establish the entire requirement.

**Current evidence limit:** SOURCE_AND_LOCAL_FIXTURE_ONLY_OR_NOT_IMPLEMENTED; NOT_NATIVE_QUALIFIED. Actual native evidence is not supplied.

**Outstanding dependency:** No complete authoritative service/profile registry, tenant role enforcement or actual placement/edge evidence is supplied. Input screening covers only its enumerated examples and cannot accept the complete service.

| Assertion | Exact source focus | Required site-specific completion |
| --- | --- | --- |
| REF-001/A01 | The service contract SHALL remain stable when a supported platform is replaced, provided the replacement platform passes the required conformance profile. | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |

**Verification:** [CT-016](test-specifications.md#CT-016) · [CT-060](test-specifications.md#CT-060). Apply the referenced procedure to the actual enforcement location and this focus; include effective negative/failure observations where the original criterion requires them.

**Applicability and acceptance:** TO_BE_DECIDED_FOR_ACTUAL_SERVICE; NOT_AUTO_NA. The accountable project role records applicability, configuration and evidence; this reusable allocation does not invent those decisions.

<a id="REF-002"></a>
## REF-002

Platform-specific extensions MAY be offered, but they SHALL be declared as capabilities and SHALL NOT redefine the portable core semantics.

**Source role:** Architecture authority. **Original design references:** RA §1; RA §28.

**Enforcement location:** Accepted service/profile and topology records; native domain/identity boundaries implement selected constraints.

**Delivery disposition:** `PARTIAL_DESIGN_AND_CANDIDATE`.

**Related code/procedure:** [docs/architecture/RAD.md](../architecture/RAD.md) · [docs/engineering/TAD.md](../engineering/TAD.md) · [tools/input_review.py](../../tools/input_review.py). These artifacts do not individually or collectively establish the entire requirement.

**Current evidence limit:** SOURCE_AND_LOCAL_FIXTURE_ONLY_OR_NOT_IMPLEMENTED; NOT_NATIVE_QUALIFIED. Actual native evidence is not supplied.

**Outstanding dependency:** No complete authoritative service/profile registry, tenant role enforcement or actual placement/edge evidence is supplied. Input screening covers only its enumerated examples and cannot accept the complete service.

| Assertion | Exact source focus | Required site-specific completion |
| --- | --- | --- |
| REF-002/A01 | Platform-specific extensions MAY be offered, but they SHALL be declared as capabilities and SHALL NOT redefine the portable core semantics. | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |

**Verification:** [CT-016](test-specifications.md#CT-016) · [CT-018](test-specifications.md#CT-018). Apply the referenced procedure to the actual enforcement location and this focus; include effective negative/failure observations where the original criterion requires them.

**Applicability and acceptance:** TO_BE_DECIDED_FOR_ACTUAL_SERVICE; NOT_AUTO_NA. The accountable project role records applicability, configuration and evidence; this reusable allocation does not invent those decisions.

<a id="DOC-001"></a>
## DOC-001

Every normative requirement SHALL have a stable identifier, accountable owner, applicability, source basis, verification procedure and exception policy; generated catalogues SHALL contain every active requirement.

**Source role:** Architecture authority. **Original design references:** RA §1; RA §28.

**Enforcement location:** Architecture/security/service-owner review and controlled evidence/exception record systems.

**Delivery disposition:** `EXTERNAL_GOVERNANCE_OR_MANUAL_CONTROL`.

**Related code/procedure:** [docs/DOCUMENTATION_MIGRATION.md](../DOCUMENTATION_MIGRATION.md) · [docs/assurance/requirements.md](requirements.md). These artifacts do not individually or collectively establish the entire requirement.

**Current evidence limit:** SOURCE_AND_LOCAL_FIXTURE_ONLY_OR_NOT_IMPLEMENTED; NOT_NATIVE_QUALIFIED. Actual native evidence is not supplied.

**Outstanding dependency:** Actual deciding authority, jurisdiction, applicability, issued approval, operating evidence and exception expiry handling must be supplied by the service owner; Git labels and test passes cannot issue them.

| Assertion | Exact source focus | Required site-specific completion |
| --- | --- | --- |
| DOC-001/A01 | stable identifier | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |
| DOC-001/A02 | accountable owner | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |
| DOC-001/A03 | applicability | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |
| DOC-001/A04 | source basis | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |
| DOC-001/A05 | verification procedure | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |
| DOC-001/A06 | exception policy | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |

**Verification:** [CT-075](test-specifications.md#CT-075). Apply the referenced procedure to the actual enforcement location and this focus; include effective negative/failure observations where the original criterion requires them.

**Applicability and acceptance:** TO_BE_DECIDED_FOR_ACTUAL_SERVICE; NOT_AUTO_NA. The accountable project role records applicability, configuration and evidence; this reusable allocation does not invent those decisions.

<a id="AUTH-001"></a>
## AUTH-001

Technical conformance, service readiness and formal authorization SHALL be recorded as distinct states; an automated test result SHALL NOT create, renew or impersonate an authorization decision.

**Source role:** Security authority. **Original design references:** RA §1; RA §28.

**Enforcement location:** Architecture/security/service-owner review and controlled evidence/exception record systems.

**Delivery disposition:** `EXTERNAL_GOVERNANCE_OR_MANUAL_CONTROL`.

**Related code/procedure:** [docs/DOCUMENTATION_MIGRATION.md](../DOCUMENTATION_MIGRATION.md) · [docs/assurance/requirements.md](requirements.md). These artifacts do not individually or collectively establish the entire requirement.

**Current evidence limit:** SOURCE_AND_LOCAL_FIXTURE_ONLY_OR_NOT_IMPLEMENTED; NOT_NATIVE_QUALIFIED. Actual native evidence is not supplied.

**Outstanding dependency:** Actual deciding authority, jurisdiction, applicability, issued approval, operating evidence and exception expiry handling must be supplied by the service owner; Git labels and test passes cannot issue them.

| Assertion | Exact source focus | Required site-specific completion |
| --- | --- | --- |
| AUTH-001/A01 | Technical conformance, service readiness and formal authorization SHALL be recorded as distinct states | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |
| AUTH-001/A02 | an automated test result SHALL NOT create, renew or impersonate an authorization decision. | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |

**Verification:** [CT-049](test-specifications.md#CT-049) · [CT-069](test-specifications.md#CT-069). Apply the referenced procedure to the actual enforcement location and this focus; include effective negative/failure observations where the original criterion requires them.

**Applicability and acceptance:** TO_BE_DECIDED_FOR_ACTUAL_SERVICE; NOT_AUTO_NA. The accountable project role records applicability, configuration and evidence; this reusable allocation does not invent those decisions.

<a id="STD-001"></a>
## STD-001

The standards register SHALL record edition, effective/review date, applicability, owner and supersession relationships; external changes SHALL trigger an impact review of affected profiles and evidence.

**Source role:** Security authority. **Original design references:** RA §1; RA §28.

**Enforcement location:** Architecture/security/service-owner review and controlled evidence/exception record systems.

**Delivery disposition:** `EXTERNAL_GOVERNANCE_OR_MANUAL_CONTROL`.

**Related code/procedure:** [docs/DOCUMENTATION_MIGRATION.md](../DOCUMENTATION_MIGRATION.md) · [docs/assurance/requirements.md](requirements.md). These artifacts do not individually or collectively establish the entire requirement.

**Current evidence limit:** SOURCE_AND_LOCAL_FIXTURE_ONLY_OR_NOT_IMPLEMENTED; NOT_NATIVE_QUALIFIED. Actual native evidence is not supplied.

**Outstanding dependency:** Actual deciding authority, jurisdiction, applicability, issued approval, operating evidence and exception expiry handling must be supplied by the service owner; Git labels and test passes cannot issue them.

| Assertion | Exact source focus | Required site-specific completion |
| --- | --- | --- |
| STD-001/A01 | The standards register SHALL record edition, effective/review date, applicability, owner and supersession relationships | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |
| STD-001/A02 | external changes SHALL trigger an impact review of affected profiles and evidence. | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |

**Verification:** [CT-062](test-specifications.md#CT-062) · [CT-075](test-specifications.md#CT-075). Apply the referenced procedure to the actual enforcement location and this focus; include effective negative/failure observations where the original criterion requires them.

**Applicability and acceptance:** TO_BE_DECIDED_FOR_ACTUAL_SERVICE; NOT_AUTO_NA. The accountable project role records applicability, configuration and evidence; this reusable allocation does not invent those decisions.

<a id="STD-002"></a>
## STD-002

Control mappings SHALL preserve source edition and identifier and SHALL distinguish direct source requirements, local translations and design decisions; a family-level crosswalk SHALL NOT be represented as a completed control assessment.

**Source role:** Security authority. **Original design references:** RA §1; RA §28.

**Enforcement location:** Architecture/security/service-owner review and controlled evidence/exception record systems.

**Delivery disposition:** `EXTERNAL_GOVERNANCE_OR_MANUAL_CONTROL`.

**Related code/procedure:** [docs/DOCUMENTATION_MIGRATION.md](../DOCUMENTATION_MIGRATION.md) · [docs/assurance/requirements.md](requirements.md). These artifacts do not individually or collectively establish the entire requirement.

**Current evidence limit:** SOURCE_AND_LOCAL_FIXTURE_ONLY_OR_NOT_IMPLEMENTED; NOT_NATIVE_QUALIFIED. Actual native evidence is not supplied.

**Outstanding dependency:** Actual deciding authority, jurisdiction, applicability, issued approval, operating evidence and exception expiry handling must be supplied by the service owner; Git labels and test passes cannot issue them.

| Assertion | Exact source focus | Required site-specific completion |
| --- | --- | --- |
| STD-002/A01 | Control mappings SHALL preserve source edition and identifier and SHALL distinguish direct source requirements, local translations and design decisions | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |
| STD-002/A02 | a family-level crosswalk SHALL NOT be represented as a completed control assessment. | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |

**Verification:** [CT-062](test-specifications.md#CT-062) · [CT-075](test-specifications.md#CT-075). Apply the referenced procedure to the actual enforcement location and this focus; include effective negative/failure observations where the original criterion requires them.

**Applicability and acceptance:** TO_BE_DECIDED_FOR_ACTUAL_SERVICE; NOT_AUTO_NA. The accountable project role records applicability, configuration and evidence; this reusable allocation does not invent those decisions.

<a id="CAT-001"></a>
## CAT-001

Each WSD SHALL record confidentiality, integrity and availability separately and SHALL reference the exact adopted SecurityProfile, AssuranceProfile, AvailabilityProfile, RecoveryProfile and PlacementProfile.

**Source role:** Security authority. **Original design references:** RA §2.

**Enforcement location:** Accepted service/profile and topology records; native domain/identity boundaries implement selected constraints.

**Delivery disposition:** `PARTIAL_DESIGN_AND_CANDIDATE`.

**Related code/procedure:** [docs/architecture/RAD.md](../architecture/RAD.md) · [docs/engineering/TAD.md](../engineering/TAD.md) · [tools/input_review.py](../../tools/input_review.py). These artifacts do not individually or collectively establish the entire requirement.

**Current evidence limit:** SOURCE_AND_LOCAL_FIXTURE_ONLY_OR_NOT_IMPLEMENTED; NOT_NATIVE_QUALIFIED. Actual native evidence is not supplied.

**Outstanding dependency:** No complete authoritative service/profile registry, tenant role enforcement or actual placement/edge evidence is supplied. Input screening covers only its enumerated examples and cannot accept the complete service.

| Assertion | Exact source focus | Required site-specific completion |
| --- | --- | --- |
| CAT-001/A01 | Each WSD SHALL record confidentiality, integrity and availability separately and SHALL reference the exact adopted SecurityProfile, AssuranceProfile, AvailabilityProfile, RecoveryProfile and PlacementProfile. | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |

**Verification:** [CT-017](test-specifications.md#CT-017) · [CT-062](test-specifications.md#CT-062) · [CT-069](test-specifications.md#CT-069). Apply the referenced procedure to the actual enforcement location and this focus; include effective negative/failure observations where the original criterion requires them.

**Applicability and acceptance:** TO_BE_DECIDED_FOR_ACTUAL_SERVICE; NOT_AUTO_NA. The accountable project role records applicability, configuration and evidence; this reusable allocation does not invent those decisions.

<a id="CAT-002"></a>
## CAT-002

Profile resolution SHALL be immutable and authorized; a consumer SHALL NOT lower mandatory requirements by editing a profile, forging a status field or choosing an unsupported category.

**Source role:** Automation platform. **Original design references:** RA §2.

**Enforcement location:** Accepted service/profile and topology records; native domain/identity boundaries implement selected constraints.

**Delivery disposition:** `PARTIAL_DESIGN_AND_CANDIDATE`.

**Related code/procedure:** [docs/architecture/RAD.md](../architecture/RAD.md) · [docs/engineering/TAD.md](../engineering/TAD.md) · [tools/input_review.py](../../tools/input_review.py). These artifacts do not individually or collectively establish the entire requirement.

**Current evidence limit:** SOURCE_AND_LOCAL_FIXTURE_ONLY_OR_NOT_IMPLEMENTED; NOT_NATIVE_QUALIFIED. Actual native evidence is not supplied.

**Outstanding dependency:** No complete authoritative service/profile registry, tenant role enforcement or actual placement/edge evidence is supplied. Input screening covers only its enumerated examples and cannot accept the complete service.

| Assertion | Exact source focus | Required site-specific completion |
| --- | --- | --- |
| CAT-002/A01 | Profile resolution SHALL be immutable and authorized | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |
| CAT-002/A02 | a consumer SHALL NOT lower mandatory requirements by editing a profile, forging a status field or choosing an unsupported category. | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |

**Verification:** [CT-017](test-specifications.md#CT-017) · [CT-018](test-specifications.md#CT-018). Apply the referenced procedure to the actual enforcement location and this focus; include effective negative/failure observations where the original criterion requires them.

**Applicability and acceptance:** TO_BE_DECIDED_FOR_ACTUAL_SERVICE; NOT_AUTO_NA. The accountable project role records applicability, configuration and evidence; this reusable allocation does not invent those decisions.

<a id="THR-001"></a>
## THR-001

Each platform qualification and material WSD change SHALL include a threat/failure analysis that identifies trust boundaries, privileged actors, dependency failures, residual risks and applicable tests.

**Source role:** Security authority. **Original design references:** RA §2.

**Enforcement location:** Accepted service/profile and topology records; native domain/identity boundaries implement selected constraints.

**Delivery disposition:** `PARTIAL_DESIGN_AND_CANDIDATE`.

**Related code/procedure:** [docs/architecture/RAD.md](../architecture/RAD.md) · [docs/engineering/TAD.md](../engineering/TAD.md) · [tools/input_review.py](../../tools/input_review.py). These artifacts do not individually or collectively establish the entire requirement.

**Current evidence limit:** SOURCE_AND_LOCAL_FIXTURE_ONLY_OR_NOT_IMPLEMENTED; NOT_NATIVE_QUALIFIED. Actual native evidence is not supplied.

**Outstanding dependency:** No complete authoritative service/profile registry, tenant role enforcement or actual placement/edge evidence is supplied. Input screening covers only its enumerated examples and cannot accept the complete service.

| Assertion | Exact source focus | Required site-specific completion |
| --- | --- | --- |
| THR-001/A01 | Each platform qualification and material WSD change SHALL include a threat/failure analysis that identifies trust boundaries, privileged actors, dependency failures, residual risks and applicable tests. | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |

**Verification:** [CT-035](test-specifications.md#CT-035) · [CT-062](test-specifications.md#CT-062) · [CT-080](test-specifications.md#CT-080). Apply the referenced procedure to the actual enforcement location and this focus; include effective negative/failure observations where the original criterion requires them.

**Applicability and acceptance:** TO_BE_DECIDED_FOR_ACTUAL_SERVICE; NOT_AUTO_NA. The accountable project role records applicability, configuration and evidence; this reusable allocation does not invent those decisions.

<a id="MODEL-001"></a>
## MODEL-001

Every network SHALL resolve to one Security Domain Instance, one logical domain, one zone class, one address authority and one accountable owner; shared-domain lifecycle SHALL use explicit dependency references.

**Source role:** Architecture authority. **Original design references:** RA §3; RA §7.

**Enforcement location:** Accepted service/profile and topology records; native domain/identity boundaries implement selected constraints.

**Delivery disposition:** `PARTIAL_DESIGN_AND_CANDIDATE`.

**Related code/procedure:** [docs/architecture/RAD.md](../architecture/RAD.md) · [docs/engineering/TAD.md](../engineering/TAD.md) · [tools/input_review.py](../../tools/input_review.py). These artifacts do not individually or collectively establish the entire requirement.

**Current evidence limit:** SOURCE_AND_LOCAL_FIXTURE_ONLY_OR_NOT_IMPLEMENTED; NOT_NATIVE_QUALIFIED. Actual native evidence is not supplied.

**Outstanding dependency:** No complete authoritative service/profile registry, tenant role enforcement or actual placement/edge evidence is supplied. Input screening covers only its enumerated examples and cannot accept the complete service.

| Assertion | Exact source focus | Required site-specific completion |
| --- | --- | --- |
| MODEL-001/A01 | Every network SHALL resolve to one Security Domain Instance, one logical domain, one zone class, one address authority and one accountable owner | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |
| MODEL-001/A02 | shared-domain lifecycle SHALL use explicit dependency references. | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |

**Verification:** [CT-017](test-specifications.md#CT-017) · [CT-025](test-specifications.md#CT-025) · [CT-070](test-specifications.md#CT-070). Apply the referenced procedure to the actual enforcement location and this focus; include effective negative/failure observations where the original criterion requires them.

**Applicability and acceptance:** TO_BE_DECIDED_FOR_ACTUAL_SERVICE; NOT_AUTO_NA. The accountable project role records applicability, configuration and evidence; this reusable allocation does not invent those decisions.

<a id="MODEL-002"></a>
## MODEL-002

Provider service consumption, platform control, privileged management and OOB transport SHALL be modeled separately; a shared service SHALL NOT create implicit authority over another plane.

**Source role:** Architecture authority. **Original design references:** RA §3; RA §7.

**Enforcement location:** Accepted service/profile and topology records; native domain/identity boundaries implement selected constraints.

**Delivery disposition:** `PARTIAL_DESIGN_AND_CANDIDATE`.

**Related code/procedure:** [docs/architecture/RAD.md](../architecture/RAD.md) · [docs/engineering/TAD.md](../engineering/TAD.md) · [tools/input_review.py](../../tools/input_review.py). These artifacts do not individually or collectively establish the entire requirement.

**Current evidence limit:** SOURCE_AND_LOCAL_FIXTURE_ONLY_OR_NOT_IMPLEMENTED; NOT_NATIVE_QUALIFIED. Actual native evidence is not supplied.

**Outstanding dependency:** No complete authoritative service/profile registry, tenant role enforcement or actual placement/edge evidence is supplied. Input screening covers only its enumerated examples and cannot accept the complete service.

| Assertion | Exact source focus | Required site-specific completion |
| --- | --- | --- |
| MODEL-002/A01 | Provider service consumption, platform control, privileged management and OOB transport SHALL be modeled separately | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |
| MODEL-002/A02 | a shared service SHALL NOT create implicit authority over another plane. | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |

**Verification:** [CT-004](test-specifications.md#CT-004) · [CT-008](test-specifications.md#CT-008) · [CT-026](test-specifications.md#CT-026). Apply the referenced procedure to the actual enforcement location and this focus; include effective negative/failure observations where the original criterion requires them.

**Applicability and acceptance:** TO_BE_DECIDED_FOR_ACTUAL_SERVICE; NOT_AUTO_NA. The accountable project role records applicability, configuration and evidence; this reusable allocation does not invent those decisions.

<a id="TEN-001"></a>
## TEN-001

Cross-tenant routing SHALL be denied by default even when two tenants use the same zone class.

**Source role:** Automation platform. **Original design references:** RA §7.

**Enforcement location:** Accepted service/profile and topology records; native domain/identity boundaries implement selected constraints.

**Delivery disposition:** `PARTIAL_DESIGN_AND_CANDIDATE`.

**Related code/procedure:** [docs/architecture/RAD.md](../architecture/RAD.md) · [docs/engineering/TAD.md](../engineering/TAD.md) · [tools/input_review.py](../../tools/input_review.py). These artifacts do not individually or collectively establish the entire requirement.

**Current evidence limit:** SOURCE_AND_LOCAL_FIXTURE_ONLY_OR_NOT_IMPLEMENTED; NOT_NATIVE_QUALIFIED. Actual native evidence is not supplied.

**Outstanding dependency:** No complete authoritative service/profile registry, tenant role enforcement or actual placement/edge evidence is supplied. Input screening covers only its enumerated examples and cannot accept the complete service.

| Assertion | Exact source focus | Required site-specific completion |
| --- | --- | --- |
| TEN-001/A01 | Cross-tenant routing SHALL be denied by default even when two tenants use the same zone class. | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |

**Verification:** [CT-001](test-specifications.md#CT-001) · [CT-002](test-specifications.md#CT-002) · [CT-019](test-specifications.md#CT-019). Apply the referenced procedure to the actual enforcement location and this focus; include effective negative/failure observations where the original criterion requires them.

**Applicability and acceptance:** TO_BE_DECIDED_FOR_ACTUAL_SERVICE; NOT_AUTO_NA. The accountable project role records applicability, configuration and evidence; this reusable allocation does not invent those decisions.

<a id="TEN-002"></a>
## TEN-002

Tenant administrators SHALL NOT have authority to modify provider management, security-edge infrastructure, physical fabric, or another tenant namespace.

**Source role:** Automation platform. **Original design references:** RA §7.

**Enforcement location:** Accepted service/profile and topology records; native domain/identity boundaries implement selected constraints.

**Delivery disposition:** `PARTIAL_DESIGN_AND_CANDIDATE`.

**Related code/procedure:** [docs/architecture/RAD.md](../architecture/RAD.md) · [docs/engineering/TAD.md](../engineering/TAD.md) · [tools/input_review.py](../../tools/input_review.py). These artifacts do not individually or collectively establish the entire requirement.

**Current evidence limit:** SOURCE_AND_LOCAL_FIXTURE_ONLY_OR_NOT_IMPLEMENTED; NOT_NATIVE_QUALIFIED. Actual native evidence is not supplied.

**Outstanding dependency:** No complete authoritative service/profile registry, tenant role enforcement or actual placement/edge evidence is supplied. Input screening covers only its enumerated examples and cannot accept the complete service.

| Assertion | Exact source focus | Required site-specific completion |
| --- | --- | --- |
| TEN-002/A01 | Tenant administrators SHALL NOT have authority to modify provider management, security-edge infrastructure, physical fabric, or another tenant namespace. | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |

**Verification:** [CT-019](test-specifications.md#CT-019) · [CT-026](test-specifications.md#CT-026). Apply the referenced procedure to the actual enforcement location and this focus; include effective negative/failure observations where the original criterion requires them.

**Applicability and acceptance:** TO_BE_DECIDED_FOR_ACTUAL_SERVICE; NOT_AUTO_NA. The accountable project role records applicability, configuration and evidence; this reusable allocation does not invent those decisions.

<a id="TEN-003"></a>
## TEN-003

Tenant ownership, entitlements and role bindings SHALL be versioned and auditable; suspension SHALL specify permitted recovery/containment actions and SHALL NOT imply indiscriminate workload deletion.

**Source role:** Service owner. **Original design references:** RA §7.

**Enforcement location:** Accepted service/profile and topology records; native domain/identity boundaries implement selected constraints.

**Delivery disposition:** `PARTIAL_DESIGN_AND_CANDIDATE`.

**Related code/procedure:** [docs/architecture/RAD.md](../architecture/RAD.md) · [docs/engineering/TAD.md](../engineering/TAD.md) · [tools/input_review.py](../../tools/input_review.py). These artifacts do not individually or collectively establish the entire requirement.

**Current evidence limit:** SOURCE_AND_LOCAL_FIXTURE_ONLY_OR_NOT_IMPLEMENTED; NOT_NATIVE_QUALIFIED. Actual native evidence is not supplied.

**Outstanding dependency:** No complete authoritative service/profile registry, tenant role enforcement or actual placement/edge evidence is supplied. Input screening covers only its enumerated examples and cannot accept the complete service.

| Assertion | Exact source focus | Required site-specific completion |
| --- | --- | --- |
| TEN-003/A01 | Tenant ownership, entitlements and role bindings SHALL be versioned and auditable | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |
| TEN-003/A02 | suspension SHALL specify permitted recovery/containment actions and SHALL NOT imply indiscriminate workload deletion. | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |

**Verification:** [CT-019](test-specifications.md#CT-019) · [CT-057](test-specifications.md#CT-057) · [CT-070](test-specifications.md#CT-070). Apply the referenced procedure to the actual enforcement location and this focus; include effective negative/failure observations where the original criterion requires them.

**Applicability and acceptance:** TO_BE_DECIDED_FOR_ACTUAL_SERVICE; NOT_AUTO_NA. The accountable project role records applicability, configuration and evidence; this reusable allocation does not invent those decisions.

<a id="WSD-001"></a>
## WSD-001

Every managed workload SHALL belong to a WSD or an explicitly documented equivalent lifecycle object.

**Source role:** Service owner. **Original design references:** RA §7.

**Enforcement location:** Accepted service/profile and topology records; native domain/identity boundaries implement selected constraints.

**Delivery disposition:** `PARTIAL_DESIGN_AND_CANDIDATE`.

**Related code/procedure:** [docs/architecture/RAD.md](../architecture/RAD.md) · [docs/engineering/TAD.md](../engineering/TAD.md) · [tools/input_review.py](../../tools/input_review.py). These artifacts do not individually or collectively establish the entire requirement.

**Current evidence limit:** SOURCE_AND_LOCAL_FIXTURE_ONLY_OR_NOT_IMPLEMENTED; NOT_NATIVE_QUALIFIED. Actual native evidence is not supplied.

**Outstanding dependency:** No complete authoritative service/profile registry, tenant role enforcement or actual placement/edge evidence is supplied. Input screening covers only its enumerated examples and cannot accept the complete service.

| Assertion | Exact source focus | Required site-specific completion |
| --- | --- | --- |
| WSD-001/A01 | Every managed workload SHALL belong to a WSD or an explicitly documented equivalent lifecycle object. | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |

**Verification:** [CT-017](test-specifications.md#CT-017) · [CT-070](test-specifications.md#CT-070). Apply the referenced procedure to the actual enforcement location and this focus; include effective negative/failure observations where the original criterion requires them.

**Applicability and acceptance:** TO_BE_DECIDED_FOR_ACTUAL_SERVICE; NOT_AUTO_NA. The accountable project role records applicability, configuration and evidence; this reusable allocation does not invent those decisions.

<a id="WSD-002"></a>
## WSD-002

The WSD SHALL contain security and connectivity intent; it SHALL NOT contain vendor-specific infrastructure identifiers in the consumer contract.

**Source role:** Automation platform. **Original design references:** RA §7.

**Enforcement location:** Accepted service/profile and topology records; native domain/identity boundaries implement selected constraints.

**Delivery disposition:** `PARTIAL_DESIGN_AND_CANDIDATE`.

**Related code/procedure:** [docs/architecture/RAD.md](../architecture/RAD.md) · [docs/engineering/TAD.md](../engineering/TAD.md) · [tools/input_review.py](../../tools/input_review.py). These artifacts do not individually or collectively establish the entire requirement.

**Current evidence limit:** SOURCE_AND_LOCAL_FIXTURE_ONLY_OR_NOT_IMPLEMENTED; NOT_NATIVE_QUALIFIED. Actual native evidence is not supplied.

**Outstanding dependency:** No complete authoritative service/profile registry, tenant role enforcement or actual placement/edge evidence is supplied. Input screening covers only its enumerated examples and cannot accept the complete service.

| Assertion | Exact source focus | Required site-specific completion |
| --- | --- | --- |
| WSD-002/A01 | The WSD SHALL contain security and connectivity intent | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |
| WSD-002/A02 | it SHALL NOT contain vendor-specific infrastructure identifiers in the consumer contract. | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |

**Verification:** [CT-016](test-specifications.md#CT-016) · [CT-017](test-specifications.md#CT-017). Apply the referenced procedure to the actual enforcement location and this focus; include effective negative/failure observations where the original criterion requires them.

**Applicability and acceptance:** TO_BE_DECIDED_FOR_ACTUAL_SERVICE; NOT_AUTO_NA. The accountable project role records applicability, configuration and evidence; this reusable allocation does not invent those decisions.

<a id="WSD-003"></a>
## WSD-003

A WSD SHALL declare compute, storage, identity, backup, recovery, exposure and evidence dependencies in addition to network intent; unresolved mandatory dependencies SHALL block Service Ready.

**Source role:** Service owner. **Original design references:** RA §7.

**Enforcement location:** Accepted service/profile and topology records; native domain/identity boundaries implement selected constraints.

**Delivery disposition:** `PARTIAL_DESIGN_AND_CANDIDATE`.

**Related code/procedure:** [docs/architecture/RAD.md](../architecture/RAD.md) · [docs/engineering/TAD.md](../engineering/TAD.md) · [tools/input_review.py](../../tools/input_review.py). These artifacts do not individually or collectively establish the entire requirement.

**Current evidence limit:** SOURCE_AND_LOCAL_FIXTURE_ONLY_OR_NOT_IMPLEMENTED; NOT_NATIVE_QUALIFIED. Actual native evidence is not supplied.

**Outstanding dependency:** No complete authoritative service/profile registry, tenant role enforcement or actual placement/edge evidence is supplied. Input screening covers only its enumerated examples and cannot accept the complete service.

| Assertion | Exact source focus | Required site-specific completion |
| --- | --- | --- |
| WSD-003/A01 | A WSD SHALL declare compute, storage, identity, backup, recovery, exposure and evidence dependencies in addition to network intent | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |
| WSD-003/A02 | unresolved mandatory dependencies SHALL block Service Ready. | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |

**Verification:** [CT-062](test-specifications.md#CT-062) · [CT-069](test-specifications.md#CT-069). Apply the referenced procedure to the actual enforcement location and this focus; include effective negative/failure observations where the original criterion requires them.

**Applicability and acceptance:** TO_BE_DECIDED_FOR_ACTUAL_SERVICE; NOT_AUTO_NA. The accountable project role records applicability, configuration and evidence; this reusable allocation does not invent those decisions.

<a id="SDI-001"></a>
## SDI-001

A Security Domain Instance SHALL contain only networks authorized to share its routing/security authority.

**Source role:** Security authority. **Original design references:** RA §7.

**Enforcement location:** Accepted service/profile and topology records; native domain/identity boundaries implement selected constraints.

**Delivery disposition:** `PARTIAL_DESIGN_AND_CANDIDATE`.

**Related code/procedure:** [docs/architecture/RAD.md](../architecture/RAD.md) · [docs/engineering/TAD.md](../engineering/TAD.md) · [tools/input_review.py](../../tools/input_review.py). These artifacts do not individually or collectively establish the entire requirement.

**Current evidence limit:** SOURCE_AND_LOCAL_FIXTURE_ONLY_OR_NOT_IMPLEMENTED; NOT_NATIVE_QUALIFIED. Actual native evidence is not supplied.

**Outstanding dependency:** No complete authoritative service/profile registry, tenant role enforcement or actual placement/edge evidence is supplied. Input screening covers only its enumerated examples and cannot accept the complete service.

| Assertion | Exact source focus | Required site-specific completion |
| --- | --- | --- |
| SDI-001/A01 | A Security Domain Instance SHALL contain only networks authorized to share its routing/security authority. | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |

**Verification:** [CT-025](test-specifications.md#CT-025) · [CT-035](test-specifications.md#CT-035). Apply the referenced procedure to the actual enforcement location and this focus; include effective negative/failure observations where the original criterion requires them.

**Applicability and acceptance:** TO_BE_DECIDED_FOR_ACTUAL_SERVICE; NOT_AUTO_NA. The accountable project role records applicability, configuration and evidence; this reusable allocation does not invent those decisions.

<a id="SDI-002"></a>
## SDI-002

Sharing a zone class SHALL NOT imply reachability between independent Security Domain Instances.

**Source role:** Platform engineering. **Original design references:** RA §7.

**Enforcement location:** Accepted service/profile and topology records; native domain/identity boundaries implement selected constraints.

**Delivery disposition:** `PARTIAL_DESIGN_AND_CANDIDATE`.

**Related code/procedure:** [docs/architecture/RAD.md](../architecture/RAD.md) · [docs/engineering/TAD.md](../engineering/TAD.md) · [tools/input_review.py](../../tools/input_review.py). These artifacts do not individually or collectively establish the entire requirement.

**Current evidence limit:** SOURCE_AND_LOCAL_FIXTURE_ONLY_OR_NOT_IMPLEMENTED; NOT_NATIVE_QUALIFIED. Actual native evidence is not supplied.

**Outstanding dependency:** No complete authoritative service/profile registry, tenant role enforcement or actual placement/edge evidence is supplied. Input screening covers only its enumerated examples and cannot accept the complete service.

| Assertion | Exact source focus | Required site-specific completion |
| --- | --- | --- |
| SDI-002/A01 | Sharing a zone class SHALL NOT imply reachability between independent Security Domain Instances. | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |

**Verification:** [CT-001](test-specifications.md#CT-001) · [CT-002](test-specifications.md#CT-002) · [CT-021](test-specifications.md#CT-021). Apply the referenced procedure to the actual enforcement location and this focus; include effective negative/failure observations where the original criterion requires them.

**Applicability and acceptance:** TO_BE_DECIDED_FOR_ACTUAL_SERVICE; NOT_AUTO_NA. The accountable project role records applicability, configuration and evidence; this reusable allocation does not invent those decisions.

<a id="SDI-003"></a>
## SDI-003

Dedicated Security Domain Instances SHOULD be available for workloads whose assurance profile or threat model requires stronger isolation than shared logical segmentation.

**Source role:** Platform engineering. **Original design references:** RA §7.

**Enforcement location:** Accepted service/profile and topology records; native domain/identity boundaries implement selected constraints.

**Delivery disposition:** `PARTIAL_DESIGN_AND_CANDIDATE`.

**Related code/procedure:** [docs/architecture/RAD.md](../architecture/RAD.md) · [docs/engineering/TAD.md](../engineering/TAD.md) · [tools/input_review.py](../../tools/input_review.py). These artifacts do not individually or collectively establish the entire requirement.

**Current evidence limit:** SOURCE_AND_LOCAL_FIXTURE_ONLY_OR_NOT_IMPLEMENTED; NOT_NATIVE_QUALIFIED. Actual native evidence is not supplied.

**Outstanding dependency:** No complete authoritative service/profile registry, tenant role enforcement or actual placement/edge evidence is supplied. Input screening covers only its enumerated examples and cannot accept the complete service.

| Assertion | Exact source focus | Required site-specific completion |
| --- | --- | --- |
| SDI-003/A01 | Dedicated Security Domain Instances SHOULD be available for workloads whose assurance profile or threat model requires stronger isolation than shared logical segmentation. | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |

**Verification:** [CT-018](test-specifications.md#CT-018) · [CT-035](test-specifications.md#CT-035). Apply the referenced procedure to the actual enforcement location and this focus; include effective negative/failure observations where the original criterion requires them.

**Applicability and acceptance:** TO_BE_DECIDED_FOR_ACTUAL_SERVICE; NOT_AUTO_NA. The accountable project role records applicability, configuration and evidence; this reusable allocation does not invent those decisions.

<a id="SDI-004"></a>
## SDI-004

Each Security Domain Instance SHALL reference a logical domain and a qualified site/platform realization; membership and sharing changes SHALL be assessed as security-significant changes.

**Source role:** Security authority. **Original design references:** RA §7.

**Enforcement location:** Accepted service/profile and topology records; native domain/identity boundaries implement selected constraints.

**Delivery disposition:** `PARTIAL_DESIGN_AND_CANDIDATE`.

**Related code/procedure:** [docs/architecture/RAD.md](../architecture/RAD.md) · [docs/engineering/TAD.md](../engineering/TAD.md) · [tools/input_review.py](../../tools/input_review.py). These artifacts do not individually or collectively establish the entire requirement.

**Current evidence limit:** SOURCE_AND_LOCAL_FIXTURE_ONLY_OR_NOT_IMPLEMENTED; NOT_NATIVE_QUALIFIED. Actual native evidence is not supplied.

**Outstanding dependency:** No complete authoritative service/profile registry, tenant role enforcement or actual placement/edge evidence is supplied. Input screening covers only its enumerated examples and cannot accept the complete service.

| Assertion | Exact source focus | Required site-specific completion |
| --- | --- | --- |
| SDI-004/A01 | Each Security Domain Instance SHALL reference a logical domain and a qualified site/platform realization | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |
| SDI-004/A02 | membership and sharing changes SHALL be assessed as security-significant changes. | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |

**Verification:** [CT-025](test-specifications.md#CT-025) · [CT-035](test-specifications.md#CT-035) · [CT-048](test-specifications.md#CT-048). Apply the referenced procedure to the actual enforcement location and this focus; include effective negative/failure observations where the original criterion requires them.

**Applicability and acceptance:** TO_BE_DECIDED_FOR_ACTUAL_SERVICE; NOT_AUTO_NA. The accountable project role records applicability, configuration and evidence; this reusable allocation does not invent those decisions.

<a id="ZONE-001"></a>
## ZONE-001

Internal instance zoneClass SHALL be limited to PAZ, OZ, RZ, HRZ or provider-controlled MZ; external PZ/REZ relationships SHALL use ExternalDomain with explicit authority and trust metadata.

**Source role:** Security authority. **Original design references:** RA §8.

**Enforcement location:** Accepted service/profile and topology records; native domain/identity boundaries implement selected constraints.

**Delivery disposition:** `PARTIAL_DESIGN_AND_CANDIDATE`.

**Related code/procedure:** [docs/architecture/RAD.md](../architecture/RAD.md) · [docs/engineering/TAD.md](../engineering/TAD.md) · [tools/input_review.py](../../tools/input_review.py). These artifacts do not individually or collectively establish the entire requirement.

**Current evidence limit:** SOURCE_AND_LOCAL_FIXTURE_ONLY_OR_NOT_IMPLEMENTED; NOT_NATIVE_QUALIFIED. Actual native evidence is not supplied.

**Outstanding dependency:** No complete authoritative service/profile registry, tenant role enforcement or actual placement/edge evidence is supplied. Input screening covers only its enumerated examples and cannot accept the complete service.

| Assertion | Exact source focus | Required site-specific completion |
| --- | --- | --- |
| ZONE-001/A01 | Internal instance zoneClass SHALL be limited to PAZ, OZ, RZ, HRZ or provider-controlled MZ | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |
| ZONE-001/A02 | external PZ/REZ relationships SHALL use ExternalDomain with explicit authority and trust metadata. | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |

**Verification:** [CT-017](test-specifications.md#CT-017) · [CT-025](test-specifications.md#CT-025) · [CT-076](test-specifications.md#CT-076). Apply the referenced procedure to the actual enforcement location and this focus; include effective negative/failure observations where the original criterion requires them.

**Applicability and acceptance:** TO_BE_DECIDED_FOR_ACTUAL_SERVICE; NOT_AUTO_NA. The accountable project role records applicability, configuration and evidence; this reusable allocation does not invent those decisions.

<a id="ZONE-002"></a>
## ZONE-002

Every requested adjacency SHALL be evaluated against the versioned zone policy before allocation; being permitted to create a ZIP SHALL NOT grant any traffic by default.

**Source role:** Automation platform. **Original design references:** RA §8.

**Enforcement location:** Accepted service/profile and topology records; native domain/identity boundaries implement selected constraints.

**Delivery disposition:** `PARTIAL_DESIGN_AND_CANDIDATE`.

**Related code/procedure:** [docs/architecture/RAD.md](../architecture/RAD.md) · [docs/engineering/TAD.md](../engineering/TAD.md) · [tools/input_review.py](../../tools/input_review.py). These artifacts do not individually or collectively establish the entire requirement.

**Current evidence limit:** SOURCE_AND_LOCAL_FIXTURE_ONLY_OR_NOT_IMPLEMENTED; NOT_NATIVE_QUALIFIED. Actual native evidence is not supplied.

**Outstanding dependency:** No complete authoritative service/profile registry, tenant role enforcement or actual placement/edge evidence is supplied. Input screening covers only its enumerated examples and cannot accept the complete service.

| Assertion | Exact source focus | Required site-specific completion |
| --- | --- | --- |
| ZONE-002/A01 | Every requested adjacency SHALL be evaluated against the versioned zone policy before allocation | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |
| ZONE-002/A02 | being permitted to create a ZIP SHALL NOT grant any traffic by default. | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |

**Verification:** [CT-025](test-specifications.md#CT-025) · [CT-066](test-specifications.md#CT-066). Apply the referenced procedure to the actual enforcement location and this focus; include effective negative/failure observations where the original criterion requires them.

**Applicability and acceptance:** TO_BE_DECIDED_FOR_ACTUAL_SERVICE; NOT_AUTO_NA. The accountable project role records applicability, configuration and evidence; this reusable allocation does not invent those decisions.

<a id="ZIP-001"></a>
## ZIP-001

All inter-zone network paths SHALL traverse the applicable ZIP/security edge.

**Source role:** Security-edge operations. **Original design references:** RA §8.

**Enforcement location:** Actual two-sided boundary forwarding, stateful policy, inspection and management plane at EC/SE contexts.

**Delivery disposition:** `PARTIAL_CANDIDATE_NATIVE_SOURCE`.

**Related code/procedure:** [terraform/modules/nsx-gateway-quarantine/main.tf.json](../../terraform/modules/nsx-gateway-quarantine/main.tf.json) · [tools/route_record_review.py](../../tools/route_record_review.py). These artifacts do not individually or collectively establish the entire requirement.

**Current evidence limit:** SOURCE_AND_LOCAL_FIXTURE_ONLY_OR_NOT_IMPLEMENTED; NOT_NATIVE_QUALIFIED. Actual native evidence is not supplied.

**Outstanding dependency:** Only candidate scoped NSX gateway DROP and route checks exist. A selected firewall/ZIP, required inspection, isolated native attachments, tenant administration and HA capacity remain unimplemented or unqualified.

| Assertion | Exact source focus | Required site-specific completion |
| --- | --- | --- |
| ZIP-001/A01 | All inter-zone network paths SHALL traverse the applicable ZIP/security edge. | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |

**Verification:** [CT-003](test-specifications.md#CT-003) · [CT-080](test-specifications.md#CT-080). Apply the referenced procedure to the actual enforcement location and this focus; include effective negative/failure observations where the original criterion requires them.

**Applicability and acceptance:** TO_BE_DECIDED_FOR_ACTUAL_SERVICE; NOT_AUTO_NA. The accountable project role records applicability, configuration and evidence; this reusable allocation does not invent those decisions.

<a id="ZIP-002"></a>
## ZIP-002

A ZIP SHALL identify exactly two authorized adjacent endpoints, each an internal domain instance or approved external/management domain, and SHALL NOT create a general-purpose third-zone transit path.

**Source role:** Security authority. **Original design references:** RA §8.

**Enforcement location:** Actual two-sided boundary forwarding, stateful policy, inspection and management plane at EC/SE contexts.

**Delivery disposition:** `PARTIAL_CANDIDATE_NATIVE_SOURCE`.

**Related code/procedure:** [terraform/modules/nsx-gateway-quarantine/main.tf.json](../../terraform/modules/nsx-gateway-quarantine/main.tf.json) · [tools/route_record_review.py](../../tools/route_record_review.py). These artifacts do not individually or collectively establish the entire requirement.

**Current evidence limit:** SOURCE_AND_LOCAL_FIXTURE_ONLY_OR_NOT_IMPLEMENTED; NOT_NATIVE_QUALIFIED. Actual native evidence is not supplied.

**Outstanding dependency:** Only candidate scoped NSX gateway DROP and route checks exist. A selected firewall/ZIP, required inspection, isolated native attachments, tenant administration and HA capacity remain unimplemented or unqualified.

| Assertion | Exact source focus | Required site-specific completion |
| --- | --- | --- |
| ZIP-002/A01 | A ZIP SHALL identify exactly two authorized adjacent endpoints, each an internal domain instance or approved external/management domain, and SHALL NOT create a general-purpose third-zone transit path. | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |

**Verification:** [CT-023](test-specifications.md#CT-023) · [CT-025](test-specifications.md#CT-025). Apply the referenced procedure to the actual enforcement location and this focus; include effective negative/failure observations where the original criterion requires them.

**Applicability and acceptance:** TO_BE_DECIDED_FOR_ACTUAL_SERVICE; NOT_AUTO_NA. The accountable project role records applicability, configuration and evidence; this reusable allocation does not invent those decisions.

<a id="ZIP-003"></a>
## ZIP-003

Default inter-zone policy SHALL be deny; allowed flows SHALL be generated from approved Flow Intentions and Service Bindings.

**Source role:** Security-edge operations. **Original design references:** RA §8.

**Enforcement location:** Actual two-sided boundary forwarding, stateful policy, inspection and management plane at EC/SE contexts.

**Delivery disposition:** `PARTIAL_CANDIDATE_NATIVE_SOURCE`.

**Related code/procedure:** [terraform/modules/nsx-gateway-quarantine/main.tf.json](../../terraform/modules/nsx-gateway-quarantine/main.tf.json) · [tools/route_record_review.py](../../tools/route_record_review.py). These artifacts do not individually or collectively establish the entire requirement.

**Current evidence limit:** SOURCE_AND_LOCAL_FIXTURE_ONLY_OR_NOT_IMPLEMENTED; NOT_NATIVE_QUALIFIED. Actual native evidence is not supplied.

**Outstanding dependency:** Only candidate scoped NSX gateway DROP and route checks exist. A selected firewall/ZIP, required inspection, isolated native attachments, tenant administration and HA capacity remain unimplemented or unqualified.

| Assertion | Exact source focus | Required site-specific completion |
| --- | --- | --- |
| ZIP-003/A01 | Default inter-zone policy SHALL be deny | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |
| ZIP-003/A02 | allowed flows SHALL be generated from approved Flow Intentions and Service Bindings. | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |

**Verification:** [CT-007](test-specifications.md#CT-007) · [CT-025](test-specifications.md#CT-025) · [CT-066](test-specifications.md#CT-066). Apply the referenced procedure to the actual enforcement location and this focus; include effective negative/failure observations where the original criterion requires them.

**Applicability and acceptance:** TO_BE_DECIDED_FOR_ACTUAL_SERVICE; NOT_AUTO_NA. The accountable project role records applicability, configuration and evidence; this reusable allocation does not invent those decisions.

<a id="ZIP-004"></a>
## ZIP-004

ZIP management traffic SHALL be segregated from operational traffic.

**Source role:** Security-edge operations. **Original design references:** RA §8.

**Enforcement location:** Actual two-sided boundary forwarding, stateful policy, inspection and management plane at EC/SE contexts.

**Delivery disposition:** `PARTIAL_CANDIDATE_NATIVE_SOURCE`.

**Related code/procedure:** [terraform/modules/nsx-gateway-quarantine/main.tf.json](../../terraform/modules/nsx-gateway-quarantine/main.tf.json) · [tools/route_record_review.py](../../tools/route_record_review.py). These artifacts do not individually or collectively establish the entire requirement.

**Current evidence limit:** SOURCE_AND_LOCAL_FIXTURE_ONLY_OR_NOT_IMPLEMENTED; NOT_NATIVE_QUALIFIED. Actual native evidence is not supplied.

**Outstanding dependency:** Only candidate scoped NSX gateway DROP and route checks exist. A selected firewall/ZIP, required inspection, isolated native attachments, tenant administration and HA capacity remain unimplemented or unqualified.

| Assertion | Exact source focus | Required site-specific completion |
| --- | --- | --- |
| ZIP-004/A01 | ZIP management traffic SHALL be segregated from operational traffic. | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |

**Verification:** [CT-004](test-specifications.md#CT-004) · [CT-026](test-specifications.md#CT-026). Apply the referenced procedure to the actual enforcement location and this focus; include effective negative/failure observations where the original criterion requires them.

**Applicability and acceptance:** TO_BE_DECIDED_FOR_ACTUAL_SERVICE; NOT_AUTO_NA. The accountable project role records applicability, configuration and evidence; this reusable allocation does not invent those decisions.

<a id="ZIP-005"></a>
## ZIP-005

Data-path ZIPs and management-path ZIPs SHALL be governed and deployed as distinct security services; shared virtualization SHALL only be used where the applicable assurance analysis supports it.

**Source role:** Security authority. **Original design references:** RA §8.

**Enforcement location:** Actual two-sided boundary forwarding, stateful policy, inspection and management plane at EC/SE contexts.

**Delivery disposition:** `PARTIAL_CANDIDATE_NATIVE_SOURCE`.

**Related code/procedure:** [terraform/modules/nsx-gateway-quarantine/main.tf.json](../../terraform/modules/nsx-gateway-quarantine/main.tf.json) · [tools/route_record_review.py](../../tools/route_record_review.py). These artifacts do not individually or collectively establish the entire requirement.

**Current evidence limit:** SOURCE_AND_LOCAL_FIXTURE_ONLY_OR_NOT_IMPLEMENTED; NOT_NATIVE_QUALIFIED. Actual native evidence is not supplied.

**Outstanding dependency:** Only candidate scoped NSX gateway DROP and route checks exist. A selected firewall/ZIP, required inspection, isolated native attachments, tenant administration and HA capacity remain unimplemented or unqualified.

| Assertion | Exact source focus | Required site-specific completion |
| --- | --- | --- |
| ZIP-005/A01 | Data-path ZIPs and management-path ZIPs SHALL be governed and deployed as distinct security services | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |
| ZIP-005/A02 | shared virtualization SHALL only be used where the applicable assurance analysis supports it. | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |

**Verification:** [CT-026](test-specifications.md#CT-026) · [CT-035](test-specifications.md#CT-035) · [CT-080](test-specifications.md#CT-080). Apply the referenced procedure to the actual enforcement location and this focus; include effective negative/failure observations where the original criterion requires them.

**Applicability and acceptance:** TO_BE_DECIDED_FOR_ACTUAL_SERVICE; NOT_AUTO_NA. The accountable project role records applicability, configuration and evidence; this reusable allocation does not invent those decisions.

<a id="ZIP-006"></a>
## ZIP-006

Each ZIP SHALL record its two zone authorities, joint approval, required security functions, management authority, heightened posture, session-revocation behavior and current evidence.

**Source role:** Security authority. **Original design references:** RA §8.

**Enforcement location:** Actual two-sided boundary forwarding, stateful policy, inspection and management plane at EC/SE contexts.

**Delivery disposition:** `PARTIAL_CANDIDATE_NATIVE_SOURCE`.

**Related code/procedure:** [terraform/modules/nsx-gateway-quarantine/main.tf.json](../../terraform/modules/nsx-gateway-quarantine/main.tf.json) · [tools/route_record_review.py](../../tools/route_record_review.py). These artifacts do not individually or collectively establish the entire requirement.

**Current evidence limit:** SOURCE_AND_LOCAL_FIXTURE_ONLY_OR_NOT_IMPLEMENTED; NOT_NATIVE_QUALIFIED. Actual native evidence is not supplied.

**Outstanding dependency:** Only candidate scoped NSX gateway DROP and route checks exist. A selected firewall/ZIP, required inspection, isolated native attachments, tenant administration and HA capacity remain unimplemented or unqualified.

| Assertion | Exact source focus | Required site-specific completion |
| --- | --- | --- |
| ZIP-006/A01 | two zone authorities | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |
| ZIP-006/A02 | joint approval | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |
| ZIP-006/A03 | required security functions | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |
| ZIP-006/A04 | management authority | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |
| ZIP-006/A05 | heightened posture | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |
| ZIP-006/A06 | session-revocation behavior | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |
| ZIP-006/A07 | current evidence | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |

**Verification:** [CT-067](test-specifications.md#CT-067) · [CT-077](test-specifications.md#CT-077) · [CT-080](test-specifications.md#CT-080). Apply the referenced procedure to the actual enforcement location and this focus; include effective negative/failure observations where the original criterion requires them.

**Applicability and acceptance:** TO_BE_DECIDED_FOR_ACTUAL_SERVICE; NOT_AUTO_NA. The accountable project role records applicability, configuration and evidence; this reusable allocation does not invent those decisions.

<a id="ZIP-007"></a>
## ZIP-007

A distributed or shared-infrastructure ZIP SHALL be qualified against the same required security outcomes as a dedicated edge; any unsupported mandatory function SHALL make that realization ineligible.

**Source role:** Platform engineering. **Original design references:** RA §8.

**Enforcement location:** Actual two-sided boundary forwarding, stateful policy, inspection and management plane at EC/SE contexts.

**Delivery disposition:** `PARTIAL_CANDIDATE_NATIVE_SOURCE`.

**Related code/procedure:** [terraform/modules/nsx-gateway-quarantine/main.tf.json](../../terraform/modules/nsx-gateway-quarantine/main.tf.json) · [tools/route_record_review.py](../../tools/route_record_review.py). These artifacts do not individually or collectively establish the entire requirement.

**Current evidence limit:** SOURCE_AND_LOCAL_FIXTURE_ONLY_OR_NOT_IMPLEMENTED; NOT_NATIVE_QUALIFIED. Actual native evidence is not supplied.

**Outstanding dependency:** Only candidate scoped NSX gateway DROP and route checks exist. A selected firewall/ZIP, required inspection, isolated native attachments, tenant administration and HA capacity remain unimplemented or unqualified.

| Assertion | Exact source focus | Required site-specific completion |
| --- | --- | --- |
| ZIP-007/A01 | A distributed or shared-infrastructure ZIP SHALL be qualified against the same required security outcomes as a dedicated edge | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |
| ZIP-007/A02 | any unsupported mandatory function SHALL make that realization ineligible. | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |

**Verification:** [CT-003](test-specifications.md#CT-003) · [CT-023](test-specifications.md#CT-023) · [CT-080](test-specifications.md#CT-080). Apply the referenced procedure to the actual enforcement location and this focus; include effective negative/failure observations where the original criterion requires them.

**Applicability and acceptance:** TO_BE_DECIDED_FOR_ACTUAL_SERVICE; NOT_AUTO_NA. The accountable project role records applicability, configuration and evidence; this reusable allocation does not invent those decisions.

<a id="MGT-001"></a>
## MGT-001

Tenant workload networks SHALL have no direct route to infrastructure management interfaces.

**Source role:** Management operations. **Original design references:** RA §6; RA §13.

**Enforcement location:** Physical/OOB interfaces, management routes, remote-access boundary and privileged identity service.

**Delivery disposition:** `EXTERNAL_NATIVE_FOUNDATION_REQUIRED`.

**Related code/procedure:** [docs/engineering/TAD.md](../engineering/TAD.md) · [tools/nsx_observe.py](../../tools/nsx_observe.py) · [tools/nutanix_observe.py](../../tools/nutanix_observe.py). These artifacts do not individually or collectively establish the entire requirement.

**Current evidence limit:** SOURCE_AND_LOCAL_FIXTURE_ONLY_OR_NOT_IMPLEMENTED; NOT_NATIVE_QUALIFIED. Actual native evidence is not supplied.

**Outstanding dependency:** Readback tools do not construct management separation, hardened admin paths, supplier access, hardware OOB or independently recoverable identity. Native foundation implementation and path/role tests are absent.

| Assertion | Exact source focus | Required site-specific completion |
| --- | --- | --- |
| MGT-001/A01 | Tenant workload networks SHALL have no direct route to infrastructure management interfaces. | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |

**Verification:** [CT-004](test-specifications.md#CT-004) · [CT-026](test-specifications.md#CT-026). Apply the referenced procedure to the actual enforcement location and this focus; include effective negative/failure observations where the original criterion requires them.

**Applicability and acceptance:** TO_BE_DECIDED_FOR_ACTUAL_SERVICE; NOT_AUTO_NA. The accountable project role records applicability, configuration and evidence; this reusable allocation does not invent those decisions.

<a id="MGT-002"></a>
## MGT-002

Administrative access SHALL originate from an authorized management access path and traverse management-specific security controls.

**Source role:** Management operations. **Original design references:** RA §6; RA §13.

**Enforcement location:** Physical/OOB interfaces, management routes, remote-access boundary and privileged identity service.

**Delivery disposition:** `EXTERNAL_NATIVE_FOUNDATION_REQUIRED`.

**Related code/procedure:** [docs/engineering/TAD.md](../engineering/TAD.md) · [tools/nsx_observe.py](../../tools/nsx_observe.py) · [tools/nutanix_observe.py](../../tools/nutanix_observe.py). These artifacts do not individually or collectively establish the entire requirement.

**Current evidence limit:** SOURCE_AND_LOCAL_FIXTURE_ONLY_OR_NOT_IMPLEMENTED; NOT_NATIVE_QUALIFIED. Actual native evidence is not supplied.

**Outstanding dependency:** Readback tools do not construct management separation, hardened admin paths, supplier access, hardware OOB or independently recoverable identity. Native foundation implementation and path/role tests are absent.

| Assertion | Exact source focus | Required site-specific completion |
| --- | --- | --- |
| MGT-002/A01 | Administrative access SHALL originate from an authorized management access path and traverse management-specific security controls. | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |

**Verification:** [CT-026](test-specifications.md#CT-026) · [CT-027](test-specifications.md#CT-027). Apply the referenced procedure to the actual enforcement location and this focus; include effective negative/failure observations where the original criterion requires them.

**Applicability and acceptance:** TO_BE_DECIDED_FOR_ACTUAL_SERVICE; NOT_AUTO_NA. The accountable project role records applicability, configuration and evidence; this reusable allocation does not invent those decisions.

<a id="MGT-003"></a>
## MGT-003

Automation identities used to manage tenant workloads SHALL be separated from identities able to modify the physical fabric, security edge, or management foundation.

**Source role:** Automation platform. **Original design references:** RA §6; RA §13.

**Enforcement location:** Physical/OOB interfaces, management routes, remote-access boundary and privileged identity service.

**Delivery disposition:** `EXTERNAL_NATIVE_FOUNDATION_REQUIRED`.

**Related code/procedure:** [docs/engineering/TAD.md](../engineering/TAD.md) · [tools/nsx_observe.py](../../tools/nsx_observe.py) · [tools/nutanix_observe.py](../../tools/nutanix_observe.py). These artifacts do not individually or collectively establish the entire requirement.

**Current evidence limit:** SOURCE_AND_LOCAL_FIXTURE_ONLY_OR_NOT_IMPLEMENTED; NOT_NATIVE_QUALIFIED. Actual native evidence is not supplied.

**Outstanding dependency:** Readback tools do not construct management separation, hardened admin paths, supplier access, hardware OOB or independently recoverable identity. Native foundation implementation and path/role tests are absent.

| Assertion | Exact source focus | Required site-specific completion |
| --- | --- | --- |
| MGT-003/A01 | Automation identities used to manage tenant workloads SHALL be separated from identities able to modify the physical fabric, security edge, or management foundation. | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |

**Verification:** [CT-019](test-specifications.md#CT-019) · [CT-044](test-specifications.md#CT-044). Apply the referenced procedure to the actual enforcement location and this focus; include effective negative/failure observations where the original criterion requires them.

**Applicability and acceptance:** TO_BE_DECIDED_FOR_ACTUAL_SERVICE; NOT_AUTO_NA. The accountable project role records applicability, configuration and evidence; this reusable allocation does not invent those decisions.

<a id="MGT-004"></a>
## MGT-004

Break-glass access SHALL be separately controlled, strongly authenticated, logged, time-bounded where feasible, and periodically tested.

**Source role:** Management operations. **Original design references:** RA §6; RA §13.

**Enforcement location:** Physical/OOB interfaces, management routes, remote-access boundary and privileged identity service.

**Delivery disposition:** `EXTERNAL_NATIVE_FOUNDATION_REQUIRED`.

**Related code/procedure:** [docs/engineering/TAD.md](../engineering/TAD.md) · [tools/nsx_observe.py](../../tools/nsx_observe.py) · [tools/nutanix_observe.py](../../tools/nutanix_observe.py). These artifacts do not individually or collectively establish the entire requirement.

**Current evidence limit:** SOURCE_AND_LOCAL_FIXTURE_ONLY_OR_NOT_IMPLEMENTED; NOT_NATIVE_QUALIFIED. Actual native evidence is not supplied.

**Outstanding dependency:** Readback tools do not construct management separation, hardened admin paths, supplier access, hardware OOB or independently recoverable identity. Native foundation implementation and path/role tests are absent.

| Assertion | Exact source focus | Required site-specific completion |
| --- | --- | --- |
| MGT-004/A01 | controlled | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |
| MGT-004/A02 | strongly authenticated | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |
| MGT-004/A03 | logged | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |
| MGT-004/A04 | time-bounded | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |
| MGT-004/A05 | tested | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |

**Verification:** [CT-027](test-specifications.md#CT-027) · [CT-079](test-specifications.md#CT-079). Apply the referenced procedure to the actual enforcement location and this focus; include effective negative/failure observations where the original criterion requires them.

**Applicability and acceptance:** TO_BE_DECIDED_FOR_ACTUAL_SERVICE; NOT_AUTO_NA. The accountable project role records applicability, configuration and evidence; this reusable allocation does not invent those decisions.

<a id="MGT-005"></a>
## MGT-005

The implementation SHALL document independent MZ semantics, OOB transport dependencies, remote-management boundary and privileged identity controls; tenant-facing APIs SHALL NOT expose infrastructure administration.

**Source role:** Management operations. **Original design references:** RA §6; RA §13.

**Enforcement location:** Physical/OOB interfaces, management routes, remote-access boundary and privileged identity service.

**Delivery disposition:** `EXTERNAL_NATIVE_FOUNDATION_REQUIRED`.

**Related code/procedure:** [docs/engineering/TAD.md](../engineering/TAD.md) · [tools/nsx_observe.py](../../tools/nsx_observe.py) · [tools/nutanix_observe.py](../../tools/nutanix_observe.py). These artifacts do not individually or collectively establish the entire requirement.

**Current evidence limit:** SOURCE_AND_LOCAL_FIXTURE_ONLY_OR_NOT_IMPLEMENTED; NOT_NATIVE_QUALIFIED. Actual native evidence is not supplied.

**Outstanding dependency:** Readback tools do not construct management separation, hardened admin paths, supplier access, hardware OOB or independently recoverable identity. Native foundation implementation and path/role tests are absent.

| Assertion | Exact source focus | Required site-specific completion |
| --- | --- | --- |
| MGT-005/A01 | The implementation SHALL document independent MZ semantics, OOB transport dependencies, remote-management boundary and privileged identity controls | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |
| MGT-005/A02 | tenant-facing APIs SHALL NOT expose infrastructure administration. | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |

**Verification:** [CT-004](test-specifications.md#CT-004) · [CT-026](test-specifications.md#CT-026) · [CT-055](test-specifications.md#CT-055). Apply the referenced procedure to the actual enforcement location and this focus; include effective negative/failure observations where the original criterion requires them.

**Applicability and acceptance:** TO_BE_DECIDED_FOR_ACTUAL_SERVICE; NOT_AUTO_NA. The accountable project role records applicability, configuration and evidence; this reusable allocation does not invent those decisions.

<a id="OVL-001"></a>
## OVL-001

A platform SHALL provide an isolated routing/policy mechanism capable of realizing the Security Domain semantics required by the applicable conformance profile.

**Source role:** Platform engineering. **Original design references:** RA §8.

**Enforcement location:** Native guest NIC/port policy, provider-owned selectors and domain routing, including same-host paths.

**Delivery disposition:** `PARTIAL_CANDIDATE_NATIVE_SOURCE`.

**Related code/procedure:** [terraform/modules/nutanix-domain/main.tf.json](../../terraform/modules/nutanix-domain/main.tf.json) · [terraform/modules/nsx-domain/main.tf.json](../../terraform/modules/nsx-domain/main.tf.json) · [terraform/modules/openstack-domain/main.tf.json](../../terraform/modules/openstack-domain/main.tf.json). These artifacts do not individually or collectively establish the entire requirement.

**Current evidence limit:** SOURCE_AND_LOCAL_FIXTURE_ONLY_OR_NOT_IMPLEMENTED; NOT_NATIVE_QUALIFIED. Actual native evidence is not supplied.

**Outstanding dependency:** Selected denied-domain source is present. Actual native policy precedence, delegated mutation role, arbitrary NIC/selector bypass and effective same-host/cross-host enforcement are not qualified.

| Assertion | Exact source focus | Required site-specific completion |
| --- | --- | --- |
| OVL-001/A01 | A platform SHALL provide an isolated routing/policy mechanism capable of realizing the Security Domain semantics required by the applicable conformance profile. | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |

**Verification:** [CT-016](test-specifications.md#CT-016) · [CT-018](test-specifications.md#CT-018) · [CT-080](test-specifications.md#CT-080). Apply the referenced procedure to the actual enforcement location and this focus; include effective negative/failure observations where the original criterion requires them.

**Applicability and acceptance:** TO_BE_DECIDED_FOR_ACTUAL_SERVICE; NOT_AUTO_NA. The accountable project role records applicability, configuration and evidence; this reusable allocation does not invent those decisions.

<a id="OVL-002"></a>
## OVL-002

Native routing MAY be used within one authorized Security Domain Instance; communication between independent security domains SHALL follow the approved boundary/ZIP realization and its policy.

**Source role:** Platform engineering. **Original design references:** RA §8.

**Enforcement location:** Native guest NIC/port policy, provider-owned selectors and domain routing, including same-host paths.

**Delivery disposition:** `PARTIAL_CANDIDATE_NATIVE_SOURCE`.

**Related code/procedure:** [terraform/modules/nutanix-domain/main.tf.json](../../terraform/modules/nutanix-domain/main.tf.json) · [terraform/modules/nsx-domain/main.tf.json](../../terraform/modules/nsx-domain/main.tf.json) · [terraform/modules/openstack-domain/main.tf.json](../../terraform/modules/openstack-domain/main.tf.json). These artifacts do not individually or collectively establish the entire requirement.

**Current evidence limit:** SOURCE_AND_LOCAL_FIXTURE_ONLY_OR_NOT_IMPLEMENTED; NOT_NATIVE_QUALIFIED. Actual native evidence is not supplied.

**Outstanding dependency:** Selected denied-domain source is present. Actual native policy precedence, delegated mutation role, arbitrary NIC/selector bypass and effective same-host/cross-host enforcement are not qualified.

| Assertion | Exact source focus | Required site-specific completion |
| --- | --- | --- |
| OVL-002/A01 | Native routing MAY be used within one authorized Security Domain Instance | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |
| OVL-002/A02 | communication between independent security domains SHALL follow the approved boundary/ZIP realization and its policy. | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |

**Verification:** [CT-003](test-specifications.md#CT-003) · [CT-021](test-specifications.md#CT-021) · [CT-023](test-specifications.md#CT-023). Apply the referenced procedure to the actual enforcement location and this focus; include effective negative/failure observations where the original criterion requires them.

**Applicability and acceptance:** TO_BE_DECIDED_FOR_ACTUAL_SERVICE; NOT_AUTO_NA. The accountable project role records applicability, configuration and evidence; this reusable allocation does not invent those decisions.

<a id="OVL-003"></a>
## OVL-003

Before a workload is attached, the adapter SHALL normalize permissive native defaults and enforce the mandatory baseline on all supported NIC, router, gateway and workload-attachment paths.

**Source role:** Platform engineering. **Original design references:** RA §8.

**Enforcement location:** Native guest NIC/port policy, provider-owned selectors and domain routing, including same-host paths.

**Delivery disposition:** `PARTIAL_CANDIDATE_NATIVE_SOURCE`.

**Related code/procedure:** [terraform/modules/nutanix-domain/main.tf.json](../../terraform/modules/nutanix-domain/main.tf.json) · [terraform/modules/nsx-domain/main.tf.json](../../terraform/modules/nsx-domain/main.tf.json) · [terraform/modules/openstack-domain/main.tf.json](../../terraform/modules/openstack-domain/main.tf.json). These artifacts do not individually or collectively establish the entire requirement.

**Current evidence limit:** SOURCE_AND_LOCAL_FIXTURE_ONLY_OR_NOT_IMPLEMENTED; NOT_NATIVE_QUALIFIED. Actual native evidence is not supplied.

**Outstanding dependency:** Selected denied-domain source is present. Actual native policy precedence, delegated mutation role, arbitrary NIC/selector bypass and effective same-host/cross-host enforcement are not qualified.

| Assertion | Exact source focus | Required site-specific completion |
| --- | --- | --- |
| OVL-003/A01 | Before a workload is attached, the adapter SHALL normalize permissive native defaults and enforce the mandatory baseline on all supported NIC, router, gateway and workload-attachment paths. | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |

**Verification:** [CT-022](test-specifications.md#CT-022) · [CT-066](test-specifications.md#CT-066) · [CT-069](test-specifications.md#CT-069). Apply the referenced procedure to the actual enforcement location and this focus; include effective negative/failure observations where the original criterion requires them.

**Applicability and acceptance:** TO_BE_DECIDED_FOR_ACTUAL_SERVICE; NOT_AUTO_NA. The accountable project role records applicability, configuration and evidence; this reusable allocation does not invent those decisions.

<a id="RTE-001"></a>
## RTE-001

Routes, route imports/exports, and BGP adjacencies SHALL be provider-controlled outputs of authorized intent.

**Source role:** Network engineering. **Original design references:** RA §8; RA §10.

**Enforcement location:** Authorized route/flow design plus native RIB/FIB, edge session policy and lifecycle writer.

**Delivery disposition:** `PARTIAL_CANDIDATE_NATIVE_SOURCE`.

**Related code/procedure:** [tools/route_audit.py](../../tools/route_audit.py) · [tools/route_record_review.py](../../tools/route_record_review.py) · [terraform/modules/nsx-route/main.tf.json](../../terraform/modules/nsx-route/main.tf.json) · [terraform/modules/nutanix-route/main.tf.json](../../terraform/modules/nutanix-route/main.tf.json) · [terraform/modules/openstack-route/main.tf.json](../../terraform/modules/openstack-route/main.tf.json). These artifacts do not individually or collectively establish the entire requirement.

**Current evidence limit:** SOURCE_AND_LOCAL_FIXTURE_ONLY_OR_NOT_IMPLEMENTED; NOT_NATIVE_QUALIFIED. Actual native evidence is not supplied.

**Outstanding dependency:** Route models and exact native static-route resources do not implement a complete route authority, full flow compiler, expiration/teardown service, BGP ownership or effective NAT/PBR/session-revocation policy.

| Assertion | Exact source focus | Required site-specific completion |
| --- | --- | --- |
| RTE-001/A01 | Routes, route imports/exports, and BGP adjacencies SHALL be provider-controlled outputs of authorized intent. | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |

**Verification:** [CT-009](test-specifications.md#CT-009) · [CT-033](test-specifications.md#CT-033). Apply the referenced procedure to the actual enforcement location and this focus; include effective negative/failure observations where the original criterion requires them.

**Applicability and acceptance:** TO_BE_DECIDED_FOR_ACTUAL_SERVICE; NOT_AUTO_NA. The accountable project role records applicability, configuration and evidence; this reusable allocation does not invent those decisions.

<a id="RTE-002"></a>
## RTE-002

A generalized shared transit VRF SHALL NOT be used as a default inter-zone routing mechanism.

**Source role:** Network engineering. **Original design references:** RA §8; RA §10.

**Enforcement location:** Authorized route/flow design plus native RIB/FIB, edge session policy and lifecycle writer.

**Delivery disposition:** `PARTIAL_CANDIDATE_NATIVE_SOURCE`.

**Related code/procedure:** [tools/route_audit.py](../../tools/route_audit.py) · [tools/route_record_review.py](../../tools/route_record_review.py) · [terraform/modules/nsx-route/main.tf.json](../../terraform/modules/nsx-route/main.tf.json) · [terraform/modules/nutanix-route/main.tf.json](../../terraform/modules/nutanix-route/main.tf.json) · [terraform/modules/openstack-route/main.tf.json](../../terraform/modules/openstack-route/main.tf.json). These artifacts do not individually or collectively establish the entire requirement.

**Current evidence limit:** SOURCE_AND_LOCAL_FIXTURE_ONLY_OR_NOT_IMPLEMENTED; NOT_NATIVE_QUALIFIED. Actual native evidence is not supplied.

**Outstanding dependency:** Route models and exact native static-route resources do not implement a complete route authority, full flow compiler, expiration/teardown service, BGP ownership or effective NAT/PBR/session-revocation policy.

| Assertion | Exact source focus | Required site-specific completion |
| --- | --- | --- |
| RTE-002/A01 | A generalized shared transit VRF SHALL NOT be used as a default inter-zone routing mechanism. | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |

**Verification:** [CT-003](test-specifications.md#CT-003) · [CT-009](test-specifications.md#CT-009) · [CT-023](test-specifications.md#CT-023). Apply the referenced procedure to the actual enforcement location and this focus; include effective negative/failure observations where the original criterion requires them.

**Applicability and acceptance:** TO_BE_DECIDED_FOR_ACTUAL_SERVICE; NOT_AUTO_NA. The accountable project role records applicability, configuration and evidence; this reusable allocation does not invent those decisions.

<a id="RTE-003"></a>
## RTE-003

Temporary migration or transition routes SHALL have explicit scope, approval, expiry, telemetry, and automated teardown.

**Source role:** Network engineering. **Original design references:** RA §8; RA §10.

**Enforcement location:** Authorized route/flow design plus native RIB/FIB, edge session policy and lifecycle writer.

**Delivery disposition:** `PARTIAL_CANDIDATE_NATIVE_SOURCE`.

**Related code/procedure:** [tools/route_audit.py](../../tools/route_audit.py) · [tools/route_record_review.py](../../tools/route_record_review.py) · [terraform/modules/nsx-route/main.tf.json](../../terraform/modules/nsx-route/main.tf.json) · [terraform/modules/nutanix-route/main.tf.json](../../terraform/modules/nutanix-route/main.tf.json) · [terraform/modules/openstack-route/main.tf.json](../../terraform/modules/openstack-route/main.tf.json). These artifacts do not individually or collectively establish the entire requirement.

**Current evidence limit:** SOURCE_AND_LOCAL_FIXTURE_ONLY_OR_NOT_IMPLEMENTED; NOT_NATIVE_QUALIFIED. Actual native evidence is not supplied.

**Outstanding dependency:** Route models and exact native static-route resources do not implement a complete route authority, full flow compiler, expiration/teardown service, BGP ownership or effective NAT/PBR/session-revocation policy.

| Assertion | Exact source focus | Required site-specific completion |
| --- | --- | --- |
| RTE-003/A01 | Temporary migration or transition routes SHALL have explicit scope, approval, expiry, telemetry, and automated teardown. | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |

**Verification:** [CT-009](test-specifications.md#CT-009) · [CT-058](test-specifications.md#CT-058) · [CT-077](test-specifications.md#CT-077). Apply the referenced procedure to the actual enforcement location and this focus; include effective negative/failure observations where the original criterion requires them.

**Applicability and acceptance:** TO_BE_DECIDED_FOR_ACTUAL_SERVICE; NOT_AUTO_NA. The accountable project role records applicability, configuration and evidence; this reusable allocation does not invent those decisions.

<a id="RTE-004"></a>
## RTE-004

Route compilation SHALL validate connected routes, recursive next hops, summaries, NAT/PBR interactions and all enabled address families; realized forwarding SHALL be compared with the approved graph before exposure.

**Source role:** Network engineering. **Original design references:** RA §8; RA §10.

**Enforcement location:** Authorized route/flow design plus native RIB/FIB, edge session policy and lifecycle writer.

**Delivery disposition:** `PARTIAL_CANDIDATE_NATIVE_SOURCE`.

**Related code/procedure:** [tools/route_audit.py](../../tools/route_audit.py) · [tools/route_record_review.py](../../tools/route_record_review.py) · [terraform/modules/nsx-route/main.tf.json](../../terraform/modules/nsx-route/main.tf.json) · [terraform/modules/nutanix-route/main.tf.json](../../terraform/modules/nutanix-route/main.tf.json) · [terraform/modules/openstack-route/main.tf.json](../../terraform/modules/openstack-route/main.tf.json). These artifacts do not individually or collectively establish the entire requirement.

**Current evidence limit:** SOURCE_AND_LOCAL_FIXTURE_ONLY_OR_NOT_IMPLEMENTED; NOT_NATIVE_QUALIFIED. Actual native evidence is not supplied.

**Outstanding dependency:** Route models and exact native static-route resources do not implement a complete route authority, full flow compiler, expiration/teardown service, BGP ownership or effective NAT/PBR/session-revocation policy.

| Assertion | Exact source focus | Required site-specific completion |
| --- | --- | --- |
| RTE-004/A01 | connected routes | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |
| RTE-004/A02 | recursive next hops | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |
| RTE-004/A03 | summaries | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |
| RTE-004/A04 | NAT/PBR interactions | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |
| RTE-004/A05 | all enabled address families | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |
| RTE-004/A06 | realized forwarding | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |

**Verification:** [CT-009](test-specifications.md#CT-009) · [CT-023](test-specifications.md#CT-023) · [CT-024](test-specifications.md#CT-024) · [CT-031](test-specifications.md#CT-031). Apply the referenced procedure to the actual enforcement location and this focus; include effective negative/failure observations where the original criterion requires them.

**Applicability and acceptance:** TO_BE_DECIDED_FOR_ACTUAL_SERVICE; NOT_AUTO_NA. The accountable project role records applicability, configuration and evidence; this reusable allocation does not invent those decisions.

<a id="IPAM-001"></a>
## IPAM-001

Every managed network SHALL have an authoritative IPAM record and owner.

**Source role:** Network engineering. **Original design references:** RA §10.

**Enforcement location:** Authoritative address/name allocation and native DNS/DHCP lifecycle services.

**Delivery disposition:** `PARTIAL_DNS_EXTERNAL_IPAM_REQUIRED`.

**Related code/procedure:** [tools/dns_change.py](../../tools/dns_change.py) · [docs/DNS_LIFECYCLE.md](../DNS_LIFECYCLE.md). These artifacts do not individually or collectively establish the entire requirement.

**Current evidence limit:** SOURCE_AND_LOCAL_FIXTURE_ONLY_OR_NOT_IMPLEMENTED; NOT_NATIVE_QUALIFIED. Actual native evidence is not supplied.

**Outstanding dependency:** The DNS client writes only exact accepted records. It does not allocate addresses, implement authoritative IPAM/DHCP, approve overlap, qualify server ACLs/propagation or release reuse tombstones.

| Assertion | Exact source focus | Required site-specific completion |
| --- | --- | --- |
| IPAM-001/A01 | Every managed network SHALL have an authoritative IPAM record and owner. | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |

**Verification:** [CT-029](test-specifications.md#CT-029) · [CT-030](test-specifications.md#CT-030). Apply the referenced procedure to the actual enforcement location and this focus; include effective negative/failure observations where the original criterion requires them.

**Applicability and acceptance:** TO_BE_DECIDED_FOR_ACTUAL_SERVICE; NOT_AUTO_NA. The accountable project role records applicability, configuration and evidence; this reusable allocation does not invent those decisions.

<a id="IPAM-002"></a>
## IPAM-002

Overlapping address space SHALL be an explicit exception or migration pattern, not the standard tenancy model.

**Source role:** Network engineering. **Original design references:** RA §10.

**Enforcement location:** Authoritative address/name allocation and native DNS/DHCP lifecycle services.

**Delivery disposition:** `PARTIAL_DNS_EXTERNAL_IPAM_REQUIRED`.

**Related code/procedure:** [tools/dns_change.py](../../tools/dns_change.py) · [docs/DNS_LIFECYCLE.md](../DNS_LIFECYCLE.md). These artifacts do not individually or collectively establish the entire requirement.

**Current evidence limit:** SOURCE_AND_LOCAL_FIXTURE_ONLY_OR_NOT_IMPLEMENTED; NOT_NATIVE_QUALIFIED. Actual native evidence is not supplied.

**Outstanding dependency:** The DNS client writes only exact accepted records. It does not allocate addresses, implement authoritative IPAM/DHCP, approve overlap, qualify server ACLs/propagation or release reuse tombstones.

| Assertion | Exact source focus | Required site-specific completion |
| --- | --- | --- |
| IPAM-002/A01 | Overlapping address space SHALL be an explicit exception or migration pattern, not the standard tenancy model. | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |

**Verification:** [CT-029](test-specifications.md#CT-029) · [CT-061](test-specifications.md#CT-061). Apply the referenced procedure to the actual enforcement location and this focus; include effective negative/failure observations where the original criterion requires them.

**Applicability and acceptance:** TO_BE_DECIDED_FOR_ACTUAL_SERVICE; NOT_AUTO_NA. The accountable project role records applicability, configuration and evidence; this reusable allocation does not invent those decisions.

<a id="IPAM-003"></a>
## IPAM-003

Address release SHOULD include quarantine/reuse controls appropriate to DNS, logging, firewall state, and incident-response requirements.

**Source role:** Network engineering. **Original design references:** RA §10.

**Enforcement location:** Authoritative address/name allocation and native DNS/DHCP lifecycle services.

**Delivery disposition:** `PARTIAL_DNS_EXTERNAL_IPAM_REQUIRED`.

**Related code/procedure:** [tools/dns_change.py](../../tools/dns_change.py) · [docs/DNS_LIFECYCLE.md](../DNS_LIFECYCLE.md). These artifacts do not individually or collectively establish the entire requirement.

**Current evidence limit:** SOURCE_AND_LOCAL_FIXTURE_ONLY_OR_NOT_IMPLEMENTED; NOT_NATIVE_QUALIFIED. Actual native evidence is not supplied.

**Outstanding dependency:** The DNS client writes only exact accepted records. It does not allocate addresses, implement authoritative IPAM/DHCP, approve overlap, qualify server ACLs/propagation or release reuse tombstones.

| Assertion | Exact source focus | Required site-specific completion |
| --- | --- | --- |
| IPAM-003/A01 | Address release SHOULD include quarantine/reuse controls appropriate to DNS, logging, firewall state, and incident-response requirements. | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |

**Verification:** [CT-013](test-specifications.md#CT-013) · [CT-030](test-specifications.md#CT-030). Apply the referenced procedure to the actual enforcement location and this focus; include effective negative/failure observations where the original criterion requires them.

**Applicability and acceptance:** TO_BE_DECIDED_FOR_ACTUAL_SERVICE; NOT_AUTO_NA. The accountable project role records applicability, configuration and evidence; this reusable allocation does not invent those decisions.

<a id="IPAM-004"></a>
## IPAM-004

Address allocation, DNS/DHCP registration and release SHALL use idempotent operation identities, conflict detection and a dependency-aware quarantine policy; IPAM failure SHALL NOT cause guessed allocations.

**Source role:** Automation platform. **Original design references:** RA §10.

**Enforcement location:** Authoritative address/name allocation and native DNS/DHCP lifecycle services.

**Delivery disposition:** `PARTIAL_DNS_EXTERNAL_IPAM_REQUIRED`.

**Related code/procedure:** [tools/dns_change.py](../../tools/dns_change.py) · [docs/DNS_LIFECYCLE.md](../DNS_LIFECYCLE.md). These artifacts do not individually or collectively establish the entire requirement.

**Current evidence limit:** SOURCE_AND_LOCAL_FIXTURE_ONLY_OR_NOT_IMPLEMENTED; NOT_NATIVE_QUALIFIED. Actual native evidence is not supplied.

**Outstanding dependency:** The DNS client writes only exact accepted records. It does not allocate addresses, implement authoritative IPAM/DHCP, approve overlap, qualify server ACLs/propagation or release reuse tombstones.

| Assertion | Exact source focus | Required site-specific completion |
| --- | --- | --- |
| IPAM-004/A01 | Address allocation, DNS/DHCP registration and release SHALL use idempotent operation identities, conflict detection and a dependency-aware quarantine policy | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |
| IPAM-004/A02 | IPAM failure SHALL NOT cause guessed allocations. | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |

**Verification:** [CT-029](test-specifications.md#CT-029) · [CT-030](test-specifications.md#CT-030) · [CT-045](test-specifications.md#CT-045) · [CT-046](test-specifications.md#CT-046). Apply the referenced procedure to the actual enforcement location and this focus; include effective negative/failure observations where the original criterion requires them.

**Applicability and acceptance:** TO_BE_DECIDED_FOR_ACTUAL_SERVICE; NOT_AUTO_NA. The accountable project role records applicability, configuration and evidence; this reusable allocation does not invent those decisions.

<a id="IPV6-001"></a>
## IPV6-001

Security semantics SHALL be equivalent across IPv4 and IPv6 unless an explicit, approved protocol-specific exception exists.

**Source role:** Network engineering. **Original design references:** RA §10.

**Enforcement location:** Every offered native domain/edge/service/recovery path and local neighbour/control protocols.

**Delivery disposition:** `NATIVE_IMPLEMENTATION_AND_QUALIFICATION_OPEN`.

**Related code/procedure:** [tools/route_audit.py](../../tools/route_audit.py) · [lab/run_namespace_lab.py](../../lab/run_namespace_lab.py). These artifacts do not individually or collectively establish the entire requirement.

**Current evidence limit:** SOURCE_AND_LOCAL_FIXTURE_ONLY_OR_NOT_IMPLEMENTED; NOT_NATIVE_QUALIFIED. Actual native evidence is not supplied.

**Outstanding dependency:** Offline IPv6 and loopback/AAAA tests are not native dual-stack. The packet fixture and native staging are IPv4; full IPv6 routing, local controls, PMTU and service/recovery dependencies remain unqualified.

| Assertion | Exact source focus | Required site-specific completion |
| --- | --- | --- |
| IPV6-001/A01 | Security semantics SHALL be equivalent across IPv4 and IPv6 unless an explicit, approved protocol-specific exception exists. | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |

**Verification:** [CT-002](test-specifications.md#CT-002) · [CT-031](test-specifications.md#CT-031) · [CT-032](test-specifications.md#CT-032). Apply the referenced procedure to the actual enforcement location and this focus; include effective negative/failure observations where the original criterion requires them.

**Applicability and acceptance:** TO_BE_DECIDED_FOR_ACTUAL_SERVICE; NOT_AUTO_NA. The accountable project role records applicability, configuration and evidence; this reusable allocation does not invent those decisions.

<a id="IPV6-002"></a>
## IPV6-002

Conformance testing SHALL include IPv6 negative-path tests before a platform is certified for dual-stack service.

**Source role:** Platform engineering. **Original design references:** RA §10.

**Enforcement location:** Every offered native domain/edge/service/recovery path and local neighbour/control protocols.

**Delivery disposition:** `NATIVE_IMPLEMENTATION_AND_QUALIFICATION_OPEN`.

**Related code/procedure:** [tools/route_audit.py](../../tools/route_audit.py) · [lab/run_namespace_lab.py](../../lab/run_namespace_lab.py). These artifacts do not individually or collectively establish the entire requirement.

**Current evidence limit:** SOURCE_AND_LOCAL_FIXTURE_ONLY_OR_NOT_IMPLEMENTED; NOT_NATIVE_QUALIFIED. Actual native evidence is not supplied.

**Outstanding dependency:** Offline IPv6 and loopback/AAAA tests are not native dual-stack. The packet fixture and native staging are IPv4; full IPv6 routing, local controls, PMTU and service/recovery dependencies remain unqualified.

| Assertion | Exact source focus | Required site-specific completion |
| --- | --- | --- |
| IPV6-002/A01 | Conformance testing SHALL include IPv6 negative-path tests before a platform is certified for dual-stack service. | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |

**Verification:** [CT-002](test-specifications.md#CT-002) · [CT-003](test-specifications.md#CT-003) · [CT-031](test-specifications.md#CT-031). Apply the referenced procedure to the actual enforcement location and this focus; include effective negative/failure observations where the original criterion requires them.

**Applicability and acceptance:** TO_BE_DECIDED_FOR_ACTUAL_SERVICE; NOT_AUTO_NA. The accountable project role records applicability, configuration and evidence; this reusable allocation does not invent those decisions.

<a id="IPV6-003"></a>
## IPV6-003

Every offered address-family mode SHALL define local protocol controls, ICMPv6/PMTU treatment, transition-path restrictions and complete service/recovery dependencies; unsupported family combinations SHALL be rejected.

**Source role:** Network engineering. **Original design references:** RA §10.

**Enforcement location:** Every offered native domain/edge/service/recovery path and local neighbour/control protocols.

**Delivery disposition:** `NATIVE_IMPLEMENTATION_AND_QUALIFICATION_OPEN`.

**Related code/procedure:** [tools/route_audit.py](../../tools/route_audit.py) · [lab/run_namespace_lab.py](../../lab/run_namespace_lab.py). These artifacts do not individually or collectively establish the entire requirement.

**Current evidence limit:** SOURCE_AND_LOCAL_FIXTURE_ONLY_OR_NOT_IMPLEMENTED; NOT_NATIVE_QUALIFIED. Actual native evidence is not supplied.

**Outstanding dependency:** Offline IPv6 and loopback/AAAA tests are not native dual-stack. The packet fixture and native staging are IPv4; full IPv6 routing, local controls, PMTU and service/recovery dependencies remain unqualified.

| Assertion | Exact source focus | Required site-specific completion |
| --- | --- | --- |
| IPV6-003/A01 | Every offered address-family mode SHALL define local protocol controls, ICMPv6/PMTU treatment, transition-path restrictions and complete service/recovery dependencies | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |
| IPV6-003/A02 | unsupported family combinations SHALL be rejected. | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |

**Verification:** [CT-018](test-specifications.md#CT-018) · [CT-031](test-specifications.md#CT-031) · [CT-032](test-specifications.md#CT-032). Apply the referenced procedure to the actual enforcement location and this focus; include effective negative/failure observations where the original criterion requires them.

**Applicability and acceptance:** TO_BE_DECIDED_FOR_ACTUAL_SERVICE; NOT_AUTO_NA. The accountable project role records applicability, configuration and evidence; this reusable allocation does not invent those decisions.

<a id="SVC-001"></a>
## SVC-001

Consumers SHALL NOT receive broad routing to a shared-services supernet solely because they consume one shared service.

**Source role:** Service operations. **Original design references:** RA §9.

**Enforcement location:** Service-facing endpoint, tenant-specific forward/reply boundary, ingress/egress owner and service resource authority.

**Delivery disposition:** `PARTIAL_FIXTURE_EXTERNAL_SERVICE_REQUIRED`.

**Related code/procedure:** [docs/engineering/TAD.md](../engineering/TAD.md) · [lab/run_namespace_lab.py](../../lab/run_namespace_lab.py) · [tools/dns_change.py](../../tools/dns_change.py). These artifacts do not individually or collectively establish the entire requirement.

**Current evidence limit:** SOURCE_AND_LOCAL_FIXTURE_ONLY_OR_NOT_IMPLEMENTED; NOT_NATIVE_QUALIFIED. Actual native evidence is not supplied.

**Outstanding dependency:** The local model demonstrates selected TCP/DNS paths, not a production ingress/egress, shared-service entitlement, revocation/expiry, TLS inspection, logging or permitted-return deployment.

| Assertion | Exact source focus | Required site-specific completion |
| --- | --- | --- |
| SVC-001/A01 | Consumers SHALL NOT receive broad routing to a shared-services supernet solely because they consume one shared service. | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |

**Verification:** [CT-008](test-specifications.md#CT-008) · [CT-037](test-specifications.md#CT-037). Apply the referenced procedure to the actual enforcement location and this focus; include effective negative/failure observations where the original criterion requires them.

**Applicability and acceptance:** TO_BE_DECIDED_FOR_ACTUAL_SERVICE; NOT_AUTO_NA. The accountable project role records applicability, configuration and evidence; this reusable allocation does not invent those decisions.

<a id="SVC-002"></a>
## SVC-002

Where useful, shared services SHOULD expose zone-aligned endpoints so that consumption does not force unnecessary cross-zone routing.

**Source role:** Service operations. **Original design references:** RA §9.

**Enforcement location:** Service-facing endpoint, tenant-specific forward/reply boundary, ingress/egress owner and service resource authority.

**Delivery disposition:** `PARTIAL_FIXTURE_EXTERNAL_SERVICE_REQUIRED`.

**Related code/procedure:** [docs/engineering/TAD.md](../engineering/TAD.md) · [lab/run_namespace_lab.py](../../lab/run_namespace_lab.py) · [tools/dns_change.py](../../tools/dns_change.py). These artifacts do not individually or collectively establish the entire requirement.

**Current evidence limit:** SOURCE_AND_LOCAL_FIXTURE_ONLY_OR_NOT_IMPLEMENTED; NOT_NATIVE_QUALIFIED. Actual native evidence is not supplied.

**Outstanding dependency:** The local model demonstrates selected TCP/DNS paths, not a production ingress/egress, shared-service entitlement, revocation/expiry, TLS inspection, logging or permitted-return deployment.

| Assertion | Exact source focus | Required site-specific completion |
| --- | --- | --- |
| SVC-002/A01 | Where useful, shared services SHOULD expose zone-aligned endpoints so that consumption does not force unnecessary cross-zone routing. | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |

**Verification:** [CT-008](test-specifications.md#CT-008) · [CT-025](test-specifications.md#CT-025). Apply the referenced procedure to the actual enforcement location and this focus; include effective negative/failure observations where the original criterion requires them.

**Applicability and acceptance:** TO_BE_DECIDED_FOR_ACTUAL_SERVICE; NOT_AUTO_NA. The accountable project role records applicability, configuration and evidence; this reusable allocation does not invent those decisions.

<a id="SVC-003"></a>
## SVC-003

Each ServiceProfile SHALL define direction, endpoint identity, authentication, allowed scope, availability, failure behavior and management separation; bindings SHALL be revoked when their entitlement or service version expires.

**Source role:** Service operations. **Original design references:** RA §9.

**Enforcement location:** Service-facing endpoint, tenant-specific forward/reply boundary, ingress/egress owner and service resource authority.

**Delivery disposition:** `PARTIAL_FIXTURE_EXTERNAL_SERVICE_REQUIRED`.

**Related code/procedure:** [docs/engineering/TAD.md](../engineering/TAD.md) · [lab/run_namespace_lab.py](../../lab/run_namespace_lab.py) · [tools/dns_change.py](../../tools/dns_change.py). These artifacts do not individually or collectively establish the entire requirement.

**Current evidence limit:** SOURCE_AND_LOCAL_FIXTURE_ONLY_OR_NOT_IMPLEMENTED; NOT_NATIVE_QUALIFIED. Actual native evidence is not supplied.

**Outstanding dependency:** The local model demonstrates selected TCP/DNS paths, not a production ingress/egress, shared-service entitlement, revocation/expiry, TLS inspection, logging or permitted-return deployment.

| Assertion | Exact source focus | Required site-specific completion |
| --- | --- | --- |
| SVC-003/A01 | direction | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |
| SVC-003/A02 | endpoint identity | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |
| SVC-003/A03 | authentication | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |
| SVC-003/A04 | allowed scope | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |
| SVC-003/A05 | availability | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |
| SVC-003/A06 | failure behavior | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |
| SVC-003/A07 | management separation | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |
| SVC-003/A08 | revoked | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |

**Verification:** [CT-008](test-specifications.md#CT-008) · [CT-028](test-specifications.md#CT-028) · [CT-077](test-specifications.md#CT-077). Apply the referenced procedure to the actual enforcement location and this focus; include effective negative/failure observations where the original criterion requires them.

**Applicability and acceptance:** TO_BE_DECIDED_FOR_ACTUAL_SERVICE; NOT_AUTO_NA. The accountable project role records applicability, configuration and evidence; this reusable allocation does not invent those decisions.

<a id="ING-001"></a>
## ING-001

A workload SHALL NOT obtain direct public ingress by attaching its internal Security Domain directly to a public network.

**Source role:** Security-edge operations. **Original design references:** RA §9.

**Enforcement location:** Service-facing endpoint, tenant-specific forward/reply boundary, ingress/egress owner and service resource authority.

**Delivery disposition:** `PARTIAL_FIXTURE_EXTERNAL_SERVICE_REQUIRED`.

**Related code/procedure:** [docs/engineering/TAD.md](../engineering/TAD.md) · [lab/run_namespace_lab.py](../../lab/run_namespace_lab.py) · [tools/dns_change.py](../../tools/dns_change.py). These artifacts do not individually or collectively establish the entire requirement.

**Current evidence limit:** SOURCE_AND_LOCAL_FIXTURE_ONLY_OR_NOT_IMPLEMENTED; NOT_NATIVE_QUALIFIED. Actual native evidence is not supplied.

**Outstanding dependency:** The local model demonstrates selected TCP/DNS paths, not a production ingress/egress, shared-service entitlement, revocation/expiry, TLS inspection, logging or permitted-return deployment.

| Assertion | Exact source focus | Required site-specific completion |
| --- | --- | --- |
| ING-001/A01 | A workload SHALL NOT obtain direct public ingress by attaching its internal Security Domain directly to a public network. | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |

**Verification:** [CT-006](test-specifications.md#CT-006) · [CT-025](test-specifications.md#CT-025). Apply the referenced procedure to the actual enforcement location and this focus; include effective negative/failure observations where the original criterion requires them.

**Applicability and acceptance:** TO_BE_DECIDED_FOR_ACTUAL_SERVICE; NOT_AUTO_NA. The accountable project role records applicability, configuration and evidence; this reusable allocation does not invent those decisions.

<a id="ING-002"></a>
## ING-002

Public exposure SHALL be represented by an Exposure object with owner, protocol, endpoint, certificate/DNS dependencies, logging, security profile, and lifecycle state.

**Source role:** Service owner. **Original design references:** RA §9.

**Enforcement location:** Service-facing endpoint, tenant-specific forward/reply boundary, ingress/egress owner and service resource authority.

**Delivery disposition:** `PARTIAL_FIXTURE_EXTERNAL_SERVICE_REQUIRED`.

**Related code/procedure:** [docs/engineering/TAD.md](../engineering/TAD.md) · [lab/run_namespace_lab.py](../../lab/run_namespace_lab.py) · [tools/dns_change.py](../../tools/dns_change.py). These artifacts do not individually or collectively establish the entire requirement.

**Current evidence limit:** SOURCE_AND_LOCAL_FIXTURE_ONLY_OR_NOT_IMPLEMENTED; NOT_NATIVE_QUALIFIED. Actual native evidence is not supplied.

**Outstanding dependency:** The local model demonstrates selected TCP/DNS paths, not a production ingress/egress, shared-service entitlement, revocation/expiry, TLS inspection, logging or permitted-return deployment.

| Assertion | Exact source focus | Required site-specific completion |
| --- | --- | --- |
| ING-002/A01 | Public exposure SHALL be represented by an Exposure object with owner, protocol, endpoint, certificate/DNS dependencies, logging, security profile, and lifecycle state. | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |

**Verification:** [CT-006](test-specifications.md#CT-006) · [CT-063](test-specifications.md#CT-063). Apply the referenced procedure to the actual enforcement location and this focus; include effective negative/failure observations where the original criterion requires them.

**Applicability and acceptance:** TO_BE_DECIDED_FOR_ACTUAL_SERVICE; NOT_AUTO_NA. The accountable project role records applicability, configuration and evidence; this reusable allocation does not invent those decisions.

<a id="EGR-001"></a>
## EGR-001

Internet egress SHALL be deny-by-default and enabled only through an approved egress profile.

**Source role:** Security-edge operations. **Original design references:** RA §9.

**Enforcement location:** Service-facing endpoint, tenant-specific forward/reply boundary, ingress/egress owner and service resource authority.

**Delivery disposition:** `PARTIAL_FIXTURE_EXTERNAL_SERVICE_REQUIRED`.

**Related code/procedure:** [docs/engineering/TAD.md](../engineering/TAD.md) · [lab/run_namespace_lab.py](../../lab/run_namespace_lab.py) · [tools/dns_change.py](../../tools/dns_change.py). These artifacts do not individually or collectively establish the entire requirement.

**Current evidence limit:** SOURCE_AND_LOCAL_FIXTURE_ONLY_OR_NOT_IMPLEMENTED; NOT_NATIVE_QUALIFIED. Actual native evidence is not supplied.

**Outstanding dependency:** The local model demonstrates selected TCP/DNS paths, not a production ingress/egress, shared-service entitlement, revocation/expiry, TLS inspection, logging or permitted-return deployment.

| Assertion | Exact source focus | Required site-specific completion |
| --- | --- | --- |
| EGR-001/A01 | Internet egress SHALL be deny-by-default and enabled only through an approved egress profile. | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |

**Verification:** [CT-005](test-specifications.md#CT-005) · [CT-064](test-specifications.md#CT-064). Apply the referenced procedure to the actual enforcement location and this focus; include effective negative/failure observations where the original criterion requires them.

**Applicability and acceptance:** TO_BE_DECIDED_FOR_ACTUAL_SERVICE; NOT_AUTO_NA. The accountable project role records applicability, configuration and evidence; this reusable allocation does not invent those decisions.

<a id="EGR-002"></a>
## EGR-002

Egress telemetry SHALL permit attribution to the originating tenant/WSD and should preserve useful source identity where operationally feasible.

**Source role:** Security-edge operations. **Original design references:** RA §9.

**Enforcement location:** Service-facing endpoint, tenant-specific forward/reply boundary, ingress/egress owner and service resource authority.

**Delivery disposition:** `PARTIAL_FIXTURE_EXTERNAL_SERVICE_REQUIRED`.

**Related code/procedure:** [docs/engineering/TAD.md](../engineering/TAD.md) · [lab/run_namespace_lab.py](../../lab/run_namespace_lab.py) · [tools/dns_change.py](../../tools/dns_change.py). These artifacts do not individually or collectively establish the entire requirement.

**Current evidence limit:** SOURCE_AND_LOCAL_FIXTURE_ONLY_OR_NOT_IMPLEMENTED; NOT_NATIVE_QUALIFIED. Actual native evidence is not supplied.

**Outstanding dependency:** The local model demonstrates selected TCP/DNS paths, not a production ingress/egress, shared-service entitlement, revocation/expiry, TLS inspection, logging or permitted-return deployment.

| Assertion | Exact source focus | Required site-specific completion |
| --- | --- | --- |
| EGR-002/A01 | Egress telemetry SHALL permit attribution to the originating tenant/WSD and should preserve useful source identity where operationally feasible. | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |

**Verification:** [CT-010](test-specifications.md#CT-010) · [CT-064](test-specifications.md#CT-064). Apply the referenced procedure to the actual enforcement location and this focus; include effective negative/failure observations where the original criterion requires them.

**Applicability and acceptance:** TO_BE_DECIDED_FOR_ACTUAL_SERVICE; NOT_AUTO_NA. The accountable project role records applicability, configuration and evidence; this reusable allocation does not invent those decisions.

<a id="EXP-001"></a>
## EXP-001

Exposure SHALL remain disabled until current-generation boundary, certificate, backend, logging and authorization gates pass; exposure revocation SHALL enforce the approved existing-session policy.

**Source role:** Security-edge operations. **Original design references:** RA §9.

**Enforcement location:** Service-facing endpoint, tenant-specific forward/reply boundary, ingress/egress owner and service resource authority.

**Delivery disposition:** `PARTIAL_FIXTURE_EXTERNAL_SERVICE_REQUIRED`.

**Related code/procedure:** [docs/engineering/TAD.md](../engineering/TAD.md) · [lab/run_namespace_lab.py](../../lab/run_namespace_lab.py) · [tools/dns_change.py](../../tools/dns_change.py). These artifacts do not individually or collectively establish the entire requirement.

**Current evidence limit:** SOURCE_AND_LOCAL_FIXTURE_ONLY_OR_NOT_IMPLEMENTED; NOT_NATIVE_QUALIFIED. Actual native evidence is not supplied.

**Outstanding dependency:** The local model demonstrates selected TCP/DNS paths, not a production ingress/egress, shared-service entitlement, revocation/expiry, TLS inspection, logging or permitted-return deployment.

| Assertion | Exact source focus | Required site-specific completion |
| --- | --- | --- |
| EXP-001/A01 | Exposure SHALL remain disabled until current-generation boundary, certificate, backend, logging and authorization gates pass | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |
| EXP-001/A02 | exposure revocation SHALL enforce the approved existing-session policy. | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |

**Verification:** [CT-063](test-specifications.md#CT-063) · [CT-069](test-specifications.md#CT-069) · [CT-077](test-specifications.md#CT-077). Apply the referenced procedure to the actual enforcement location and this focus; include effective negative/failure observations where the original criterion requires them.

**Applicability and acceptance:** TO_BE_DECIDED_FOR_ACTUAL_SERVICE; NOT_AUTO_NA. The accountable project role records applicability, configuration and evidence; this reusable allocation does not invent those decisions.

<a id="MICRO-001"></a>
## MICRO-001

WSD-to-WSD and tier-to-tier communication inside a shared Security Domain Instance SHALL be denied unless an approved policy explicitly permits it.

**Source role:** Platform engineering. **Original design references:** RA §7; RA §11.

**Enforcement location:** Native guest NIC/port policy, provider-owned selectors and domain routing, including same-host paths.

**Delivery disposition:** `PARTIAL_CANDIDATE_NATIVE_SOURCE`.

**Related code/procedure:** [terraform/modules/nutanix-domain/main.tf.json](../../terraform/modules/nutanix-domain/main.tf.json) · [terraform/modules/nsx-domain/main.tf.json](../../terraform/modules/nsx-domain/main.tf.json) · [terraform/modules/openstack-domain/main.tf.json](../../terraform/modules/openstack-domain/main.tf.json). These artifacts do not individually or collectively establish the entire requirement.

**Current evidence limit:** SOURCE_AND_LOCAL_FIXTURE_ONLY_OR_NOT_IMPLEMENTED; NOT_NATIVE_QUALIFIED. Actual native evidence is not supplied.

**Outstanding dependency:** Selected denied-domain source is present. Actual native policy precedence, delegated mutation role, arbitrary NIC/selector bypass and effective same-host/cross-host enforcement are not qualified.

| Assertion | Exact source focus | Required site-specific completion |
| --- | --- | --- |
| MICRO-001/A01 | WSD-to-WSD and tier-to-tier communication inside a shared Security Domain Instance SHALL be denied unless an approved policy explicitly permits it. | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |

**Verification:** [CT-021](test-specifications.md#CT-021) · [CT-066](test-specifications.md#CT-066). Apply the referenced procedure to the actual enforcement location and this focus; include effective negative/failure observations where the original criterion requires them.

**Applicability and acceptance:** TO_BE_DECIDED_FOR_ACTUAL_SERVICE; NOT_AUTO_NA. The accountable project role records applicability, configuration and evidence; this reusable allocation does not invent those decisions.

<a id="MICRO-002"></a>
## MICRO-002

Platform metadata used for security policy SHALL be managed, validated, and protected from unauthorized tenant modification.

**Source role:** Platform engineering. **Original design references:** RA §7; RA §11.

**Enforcement location:** Native guest NIC/port policy, provider-owned selectors and domain routing, including same-host paths.

**Delivery disposition:** `PARTIAL_CANDIDATE_NATIVE_SOURCE`.

**Related code/procedure:** [terraform/modules/nutanix-domain/main.tf.json](../../terraform/modules/nutanix-domain/main.tf.json) · [terraform/modules/nsx-domain/main.tf.json](../../terraform/modules/nsx-domain/main.tf.json) · [terraform/modules/openstack-domain/main.tf.json](../../terraform/modules/openstack-domain/main.tf.json). These artifacts do not individually or collectively establish the entire requirement.

**Current evidence limit:** SOURCE_AND_LOCAL_FIXTURE_ONLY_OR_NOT_IMPLEMENTED; NOT_NATIVE_QUALIFIED. Actual native evidence is not supplied.

**Outstanding dependency:** Selected denied-domain source is present. Actual native policy precedence, delegated mutation role, arbitrary NIC/selector bypass and effective same-host/cross-host enforcement are not qualified.

| Assertion | Exact source focus | Required site-specific completion |
| --- | --- | --- |
| MICRO-002/A01 | Platform metadata used for security policy SHALL be managed, validated, and protected from unauthorized tenant modification. | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |

**Verification:** [CT-020](test-specifications.md#CT-020) · [CT-066](test-specifications.md#CT-066). Apply the referenced procedure to the actual enforcement location and this focus; include effective negative/failure observations where the original criterion requires them.

**Applicability and acceptance:** TO_BE_DECIDED_FOR_ACTUAL_SERVICE; NOT_AUTO_NA. The accountable project role records applicability, configuration and evidence; this reusable allocation does not invent those decisions.

<a id="MICRO-003"></a>
## MICRO-003

The platform SHALL prevent unapproved NIC, source-identity, privileged-workload and label changes from bypassing mandatory segmentation; effective policy SHALL be verified for same-host and cross-host traffic.

**Source role:** Platform engineering. **Original design references:** RA §7; RA §11.

**Enforcement location:** Native guest NIC/port policy, provider-owned selectors and domain routing, including same-host paths.

**Delivery disposition:** `PARTIAL_CANDIDATE_NATIVE_SOURCE`.

**Related code/procedure:** [terraform/modules/nutanix-domain/main.tf.json](../../terraform/modules/nutanix-domain/main.tf.json) · [terraform/modules/nsx-domain/main.tf.json](../../terraform/modules/nsx-domain/main.tf.json) · [terraform/modules/openstack-domain/main.tf.json](../../terraform/modules/openstack-domain/main.tf.json). These artifacts do not individually or collectively establish the entire requirement.

**Current evidence limit:** SOURCE_AND_LOCAL_FIXTURE_ONLY_OR_NOT_IMPLEMENTED; NOT_NATIVE_QUALIFIED. Actual native evidence is not supplied.

**Outstanding dependency:** Selected denied-domain source is present. Actual native policy precedence, delegated mutation role, arbitrary NIC/selector bypass and effective same-host/cross-host enforcement are not qualified.

| Assertion | Exact source focus | Required site-specific completion |
| --- | --- | --- |
| MICRO-003/A01 | The platform SHALL prevent unapproved NIC, source-identity, privileged-workload and label changes from bypassing mandatory segmentation | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |
| MICRO-003/A02 | effective policy SHALL be verified for same-host and cross-host traffic. | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |

**Verification:** [CT-020](test-specifications.md#CT-020) · [CT-021](test-specifications.md#CT-021) · [CT-022](test-specifications.md#CT-022) · [CT-065](test-specifications.md#CT-065). Apply the referenced procedure to the actual enforcement location and this focus; include effective negative/failure observations where the original criterion requires them.

**Applicability and acceptance:** TO_BE_DECIDED_FOR_ACTUAL_SERVICE; NOT_AUTO_NA. The accountable project role records applicability, configuration and evidence; this reusable allocation does not invent those decisions.

<a id="EDGE-001"></a>
## EDGE-001

Every domain-to-boundary attachment SHALL have a provider-owned EdgeAttachment record covering forwarding authority, isolation, MTU, HA, capacity and cleanup; consumers SHALL NOT choose its native topology identifiers.

**Source role:** Network engineering. **Original design references:** RA §8; RA §16; RA §17; RA §18.

**Enforcement location:** Actual two-sided boundary forwarding, stateful policy, inspection and management plane at EC/SE contexts.

**Delivery disposition:** `PARTIAL_CANDIDATE_NATIVE_SOURCE`.

**Related code/procedure:** [terraform/modules/nsx-gateway-quarantine/main.tf.json](../../terraform/modules/nsx-gateway-quarantine/main.tf.json) · [tools/route_record_review.py](../../tools/route_record_review.py). These artifacts do not individually or collectively establish the entire requirement.

**Current evidence limit:** SOURCE_AND_LOCAL_FIXTURE_ONLY_OR_NOT_IMPLEMENTED; NOT_NATIVE_QUALIFIED. Actual native evidence is not supplied.

**Outstanding dependency:** Only candidate scoped NSX gateway DROP and route checks exist. A selected firewall/ZIP, required inspection, isolated native attachments, tenant administration and HA capacity remain unimplemented or unqualified.

| Assertion | Exact source focus | Required site-specific completion |
| --- | --- | --- |
| EDGE-001/A01 | Every domain-to-boundary attachment SHALL have a provider-owned EdgeAttachment record covering forwarding authority, isolation, MTU, HA, capacity and cleanup | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |
| EDGE-001/A02 | consumers SHALL NOT choose its native topology identifiers. | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |

**Verification:** [CT-023](test-specifications.md#CT-023) · [CT-024](test-specifications.md#CT-024) · [CT-032](test-specifications.md#CT-032) · [CT-071](test-specifications.md#CT-071). Apply the referenced procedure to the actual enforcement location and this focus; include effective negative/failure observations where the original criterion requires them.

**Applicability and acceptance:** TO_BE_DECIDED_FOR_ACTUAL_SERVICE; NOT_AUTO_NA. The accountable project role records applicability, configuration and evidence; this reusable allocation does not invent those decisions.

<a id="EDGE-002"></a>
## EDGE-002

A shared attachment SHALL be prohibited unless direct connected, neighbor, gateway and NAT/PBR paths preserve the required domain isolation and ZIP enforcement in normal and failure states.

**Source role:** Security authority. **Original design references:** RA §8; RA §16; RA §17; RA §18.

**Enforcement location:** Actual two-sided boundary forwarding, stateful policy, inspection and management plane at EC/SE contexts.

**Delivery disposition:** `PARTIAL_CANDIDATE_NATIVE_SOURCE`.

**Related code/procedure:** [terraform/modules/nsx-gateway-quarantine/main.tf.json](../../terraform/modules/nsx-gateway-quarantine/main.tf.json) · [tools/route_record_review.py](../../tools/route_record_review.py). These artifacts do not individually or collectively establish the entire requirement.

**Current evidence limit:** SOURCE_AND_LOCAL_FIXTURE_ONLY_OR_NOT_IMPLEMENTED; NOT_NATIVE_QUALIFIED. Actual native evidence is not supplied.

**Outstanding dependency:** Only candidate scoped NSX gateway DROP and route checks exist. A selected firewall/ZIP, required inspection, isolated native attachments, tenant administration and HA capacity remain unimplemented or unqualified.

| Assertion | Exact source focus | Required site-specific completion |
| --- | --- | --- |
| EDGE-002/A01 | A shared attachment SHALL be prohibited unless direct connected, neighbor, gateway and NAT/PBR paths preserve the required domain isolation and ZIP enforcement in normal and failure states. | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |

**Verification:** [CT-023](test-specifications.md#CT-023) · [CT-024](test-specifications.md#CT-024) · [CT-080](test-specifications.md#CT-080). Apply the referenced procedure to the actual enforcement location and this focus; include effective negative/failure observations where the original criterion requires them.

**Applicability and acceptance:** TO_BE_DECIDED_FOR_ACTUAL_SERVICE; NOT_AUTO_NA. The accountable project role records applicability, configuration and evidence; this reusable allocation does not invent those decisions.

<a id="SITE-001"></a>
## SITE-001

Security Domain Instances SHOULD be site-local by default.

**Source role:** Platform engineering. **Original design references:** RA §14; RA §27.

**Enforcement location:** Native scheduler eligibility, eligible host pools, HA admission and recovery target/data-location constraints.

**Delivery disposition:** `PARTIAL_VM_PREPARATION_ONLY`.

**Related code/procedure:** [terraform/modules/nutanix-workload/main.tf.json](../../terraform/modules/nutanix-workload/main.tf.json) · [terraform/modules/vsphere-workload/main.tf.json](../../terraform/modules/vsphere-workload/main.tf.json) · [terraform/modules/openstack-workload/main.tf.json](../../terraform/modules/openstack-workload/main.tf.json). These artifacts do not individually or collectively establish the entire requirement.

**Current evidence limit:** SOURCE_AND_LOCAL_FIXTURE_ONLY_OR_NOT_IMPLEMENTED; NOT_NATIVE_QUALIFIED. Actual native evidence is not supplied.

**Outstanding dependency:** VM preparation consumes accepted placement resources; it does not create/qualify host co-residency policy, evacuation/HA restrictions, independent sites, location agreements, guarantees or capacity under failure.

| Assertion | Exact source focus | Required site-specific completion |
| --- | --- | --- |
| SITE-001/A01 | Security Domain Instances SHOULD be site-local by default. | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |

**Verification:** [CT-054](test-specifications.md#CT-054) · [CT-055](test-specifications.md#CT-055). Apply the referenced procedure to the actual enforcement location and this focus; include effective negative/failure observations where the original criterion requires them.

**Applicability and acceptance:** TO_BE_DECIDED_FOR_ACTUAL_SERVICE; NOT_AUTO_NA. The accountable project role records applicability, configuration and evidence; this reusable allocation does not invent those decisions.

<a id="SITE-002"></a>
## SITE-002

Layer-2 stretch across sites SHALL require a documented application/availability requirement and failure-domain analysis.

**Source role:** Architecture authority. **Original design references:** RA §14; RA §27.

**Enforcement location:** Native scheduler eligibility, eligible host pools, HA admission and recovery target/data-location constraints.

**Delivery disposition:** `PARTIAL_VM_PREPARATION_ONLY`.

**Related code/procedure:** [terraform/modules/nutanix-workload/main.tf.json](../../terraform/modules/nutanix-workload/main.tf.json) · [terraform/modules/vsphere-workload/main.tf.json](../../terraform/modules/vsphere-workload/main.tf.json) · [terraform/modules/openstack-workload/main.tf.json](../../terraform/modules/openstack-workload/main.tf.json). These artifacts do not individually or collectively establish the entire requirement.

**Current evidence limit:** SOURCE_AND_LOCAL_FIXTURE_ONLY_OR_NOT_IMPLEMENTED; NOT_NATIVE_QUALIFIED. Actual native evidence is not supplied.

**Outstanding dependency:** VM preparation consumes accepted placement resources; it does not create/qualify host co-residency policy, evacuation/HA restrictions, independent sites, location agreements, guarantees or capacity under failure.

| Assertion | Exact source focus | Required site-specific completion |
| --- | --- | --- |
| SITE-002/A01 | Layer-2 stretch across sites SHALL require a documented application/availability requirement and failure-domain analysis. | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |

**Verification:** [CT-054](test-specifications.md#CT-054). Apply the referenced procedure to the actual enforcement location and this focus; include effective negative/failure observations where the original criterion requires them.

**Applicability and acceptance:** TO_BE_DECIDED_FOR_ACTUAL_SERVICE; NOT_AUTO_NA. The accountable project role records applicability, configuration and evidence; this reusable allocation does not invent those decisions.

<a id="SITE-003"></a>
## SITE-003

Recovery-site connectivity SHALL be pre-authorized and tested; emergency recovery SHALL NOT depend on ad hoc route leaking.

**Source role:** Recovery operations. **Original design references:** RA §14; RA §27.

**Enforcement location:** Native scheduler eligibility, eligible host pools, HA admission and recovery target/data-location constraints.

**Delivery disposition:** `PARTIAL_VM_PREPARATION_ONLY`.

**Related code/procedure:** [terraform/modules/nutanix-workload/main.tf.json](../../terraform/modules/nutanix-workload/main.tf.json) · [terraform/modules/vsphere-workload/main.tf.json](../../terraform/modules/vsphere-workload/main.tf.json) · [terraform/modules/openstack-workload/main.tf.json](../../terraform/modules/openstack-workload/main.tf.json). These artifacts do not individually or collectively establish the entire requirement.

**Current evidence limit:** SOURCE_AND_LOCAL_FIXTURE_ONLY_OR_NOT_IMPLEMENTED; NOT_NATIVE_QUALIFIED. Actual native evidence is not supplied.

**Outstanding dependency:** VM preparation consumes accepted placement resources; it does not create/qualify host co-residency policy, evacuation/HA restrictions, independent sites, location agreements, guarantees or capacity under failure.

| Assertion | Exact source focus | Required site-specific completion |
| --- | --- | --- |
| SITE-003/A01 | Recovery-site connectivity SHALL be pre-authorized and tested | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |
| SITE-003/A02 | emergency recovery SHALL NOT depend on ad hoc route leaking. | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |

**Verification:** [CT-052](test-specifications.md#CT-052) · [CT-054](test-specifications.md#CT-054). Apply the referenced procedure to the actual enforcement location and this focus; include effective negative/failure observations where the original criterion requires them.

**Applicability and acceptance:** TO_BE_DECIDED_FOR_ACTUAL_SERVICE; NOT_AUTO_NA. The accountable project role records applicability, configuration and evidence; this reusable allocation does not invent those decisions.

<a id="SITE-004"></a>
## SITE-004

Recovery placement SHALL preserve domain, co-residency, cryptographic, identity and location constraints; writer fencing and failback ownership SHALL be proven before production recovery is offered.

**Source role:** Recovery operations. **Original design references:** RA §14; RA §27.

**Enforcement location:** Native scheduler eligibility, eligible host pools, HA admission and recovery target/data-location constraints.

**Delivery disposition:** `PARTIAL_VM_PREPARATION_ONLY`.

**Related code/procedure:** [terraform/modules/nutanix-workload/main.tf.json](../../terraform/modules/nutanix-workload/main.tf.json) · [terraform/modules/vsphere-workload/main.tf.json](../../terraform/modules/vsphere-workload/main.tf.json) · [terraform/modules/openstack-workload/main.tf.json](../../terraform/modules/openstack-workload/main.tf.json). These artifacts do not individually or collectively establish the entire requirement.

**Current evidence limit:** SOURCE_AND_LOCAL_FIXTURE_ONLY_OR_NOT_IMPLEMENTED; NOT_NATIVE_QUALIFIED. Actual native evidence is not supplied.

**Outstanding dependency:** VM preparation consumes accepted placement resources; it does not create/qualify host co-residency policy, evacuation/HA restrictions, independent sites, location agreements, guarantees or capacity under failure.

| Assertion | Exact source focus | Required site-specific completion |
| --- | --- | --- |
| SITE-004/A01 | Recovery placement SHALL preserve domain, co-residency, cryptographic, identity and location constraints | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |
| SITE-004/A02 | writer fencing and failback ownership SHALL be proven before production recovery is offered. | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |

**Verification:** [CT-035](test-specifications.md#CT-035) · [CT-038](test-specifications.md#CT-038) · [CT-054](test-specifications.md#CT-054) · [CT-061](test-specifications.md#CT-061). Apply the referenced procedure to the actual enforcement location and this focus; include effective negative/failure observations where the original criterion requires them.

**Applicability and acceptance:** TO_BE_DECIDED_FOR_ACTUAL_SERVICE; NOT_AUTO_NA. The accountable project role records applicability, configuration and evidence; this reusable allocation does not invent those decisions.

<a id="CMP-001"></a>
## CMP-001

Compute placement, maintenance evacuation, migration and HA restart SHALL enforce the approved tenant/domain/zone co-residency matrix; no scheduler action SHALL silently weaken it.

**Source role:** Platform engineering. **Original design references:** RA §7; RA §11.

**Enforcement location:** Native scheduler eligibility, eligible host pools, HA admission and recovery target/data-location constraints.

**Delivery disposition:** `PARTIAL_VM_PREPARATION_ONLY`.

**Related code/procedure:** [terraform/modules/nutanix-workload/main.tf.json](../../terraform/modules/nutanix-workload/main.tf.json) · [terraform/modules/vsphere-workload/main.tf.json](../../terraform/modules/vsphere-workload/main.tf.json) · [terraform/modules/openstack-workload/main.tf.json](../../terraform/modules/openstack-workload/main.tf.json). These artifacts do not individually or collectively establish the entire requirement.

**Current evidence limit:** SOURCE_AND_LOCAL_FIXTURE_ONLY_OR_NOT_IMPLEMENTED; NOT_NATIVE_QUALIFIED. Actual native evidence is not supplied.

**Outstanding dependency:** VM preparation consumes accepted placement resources; it does not create/qualify host co-residency policy, evacuation/HA restrictions, independent sites, location agreements, guarantees or capacity under failure.

| Assertion | Exact source focus | Required site-specific completion |
| --- | --- | --- |
| CMP-001/A01 | Compute placement | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |
| CMP-001/A02 | maintenance evacuation | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |
| CMP-001/A03 | migration | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |
| CMP-001/A04 | HA restart | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |
| CMP-001/A05 | co-residency matrix | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |

**Verification:** [CT-035](test-specifications.md#CT-035) · [CT-056](test-specifications.md#CT-056). Apply the referenced procedure to the actual enforcement location and this focus; include effective negative/failure observations where the original criterion requires them.

**Applicability and acceptance:** TO_BE_DECIDED_FOR_ACTUAL_SERVICE; NOT_AUTO_NA. The accountable project role records applicability, configuration and evidence; this reusable allocation does not invent those decisions.

<a id="CMP-002"></a>
## CMP-002

Each compute profile SHALL define supported hardware/software, boot/attestation controls, administrative isolation, resource guarantees, overcommit policy and handling of unsupported devices.

**Source role:** Platform engineering. **Original design references:** RA §7; RA §11.

**Enforcement location:** Native scheduler eligibility, eligible host pools, HA admission and recovery target/data-location constraints.

**Delivery disposition:** `PARTIAL_VM_PREPARATION_ONLY`.

**Related code/procedure:** [terraform/modules/nutanix-workload/main.tf.json](../../terraform/modules/nutanix-workload/main.tf.json) · [terraform/modules/vsphere-workload/main.tf.json](../../terraform/modules/vsphere-workload/main.tf.json) · [terraform/modules/openstack-workload/main.tf.json](../../terraform/modules/openstack-workload/main.tf.json). These artifacts do not individually or collectively establish the entire requirement.

**Current evidence limit:** SOURCE_AND_LOCAL_FIXTURE_ONLY_OR_NOT_IMPLEMENTED; NOT_NATIVE_QUALIFIED. Actual native evidence is not supplied.

**Outstanding dependency:** VM preparation consumes accepted placement resources; it does not create/qualify host co-residency policy, evacuation/HA restrictions, independent sites, location agreements, guarantees or capacity under failure.

| Assertion | Exact source focus | Required site-specific completion |
| --- | --- | --- |
| CMP-002/A01 | Each compute profile SHALL define supported hardware/software, boot/attestation controls, administrative isolation, resource guarantees, overcommit policy and handling of unsupported devices. | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |

**Verification:** [CT-036](test-specifications.md#CT-036) · [CT-039](test-specifications.md#CT-039) · [CT-073](test-specifications.md#CT-073). Apply the referenced procedure to the actual enforcement location and this focus; include effective negative/failure observations where the original criterion requires them.

**Applicability and acceptance:** TO_BE_DECIDED_FOR_ACTUAL_SERVICE; NOT_AUTO_NA. The accountable project role records applicability, configuration and evidence; this reusable allocation does not invent those decisions.

<a id="CMP-003"></a>
## CMP-003

The meaning of dedicated compute SHALL state its exact physical and administrative scope and disclose any shared storage, network, control, support or recovery dependency.

**Source role:** Architecture authority. **Original design references:** RA §7; RA §11.

**Enforcement location:** Native scheduler eligibility, eligible host pools, HA admission and recovery target/data-location constraints.

**Delivery disposition:** `PARTIAL_VM_PREPARATION_ONLY`.

**Related code/procedure:** [terraform/modules/nutanix-workload/main.tf.json](../../terraform/modules/nutanix-workload/main.tf.json) · [terraform/modules/vsphere-workload/main.tf.json](../../terraform/modules/vsphere-workload/main.tf.json) · [terraform/modules/openstack-workload/main.tf.json](../../terraform/modules/openstack-workload/main.tf.json). These artifacts do not individually or collectively establish the entire requirement.

**Current evidence limit:** SOURCE_AND_LOCAL_FIXTURE_ONLY_OR_NOT_IMPLEMENTED; NOT_NATIVE_QUALIFIED. Actual native evidence is not supplied.

**Outstanding dependency:** VM preparation consumes accepted placement resources; it does not create/qualify host co-residency policy, evacuation/HA restrictions, independent sites, location agreements, guarantees or capacity under failure.

| Assertion | Exact source focus | Required site-specific completion |
| --- | --- | --- |
| CMP-003/A01 | The meaning of dedicated compute SHALL state its exact physical and administrative scope and disclose any shared storage, network, control, support or recovery dependency. | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |

**Verification:** [CT-035](test-specifications.md#CT-035) · [CT-062](test-specifications.md#CT-062). Apply the referenced procedure to the actual enforcement location and this focus; include effective negative/failure observations where the original criterion requires them.

**Applicability and acceptance:** TO_BE_DECIDED_FOR_ACTUAL_SERVICE; NOT_AUTO_NA. The accountable project role records applicability, configuration and evidence; this reusable allocation does not invent those decisions.

<a id="STO-001"></a>
## STO-001

Every storage resource and derivative copy SHALL carry owner, categorization, access scope, key policy, placement/retention constraints and lineage; cross-scope attachment or export SHALL require explicit authorization.

**Source role:** Storage operations. **Original design references:** RA §12.

**Enforcement location:** Storage/controller authorization, snapshot/clone/export lineage, retained copies, keys and media sanitization services.

**Delivery disposition:** `PARTIAL_RESOURCE_CREATION_EXTERNAL_LIFECYCLE`.

**Related code/procedure:** [terraform/modules/nutanix-workload/main.tf.json](../../terraform/modules/nutanix-workload/main.tf.json) · [terraform/modules/openstack-workload/main.tf.json](../../terraform/modules/openstack-workload/main.tf.json) · [docs/DNS_LIFECYCLE.md](../DNS_LIFECYCLE.md). These artifacts do not individually or collectively establish the entire requirement.

**Current evidence limit:** SOURCE_AND_LOCAL_FIXTURE_ONLY_OR_NOT_IMPLEMENTED; NOT_NATIVE_QUALIFIED. Actual native evidence is not supplied.

**Outstanding dependency:** Boot/data volume references and DNS retirement do not implement complete copy inventory, cross-owner export authorization, retention/hold policy, sanitization, receipt or safe shared-resource deletion.

| Assertion | Exact source focus | Required site-specific completion |
| --- | --- | --- |
| STO-001/A01 | owner | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |
| STO-001/A02 | categorization | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |
| STO-001/A03 | access scope | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |
| STO-001/A04 | key policy | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |
| STO-001/A05 | placement/retention constraints | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |
| STO-001/A06 | lineage | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |
| STO-001/A07 | cross-scope attachment or export | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |

**Verification:** [CT-037](test-specifications.md#CT-037) · [CT-053](test-specifications.md#CT-053) · [CT-078](test-specifications.md#CT-078). Apply the referenced procedure to the actual enforcement location and this focus; include effective negative/failure observations where the original criterion requires them.

**Applicability and acceptance:** TO_BE_DECIDED_FOR_ACTUAL_SERVICE; NOT_AUTO_NA. The accountable project role records applicability, configuration and evidence; this reusable allocation does not invent those decisions.

<a id="STO-002"></a>
## STO-002

Storage service profiles SHALL define measurable capacity/performance, consistency, replication, snapshot/clone and portability semantics and SHALL be tested under contention and the accepted failure condition.

**Source role:** Storage operations. **Original design references:** RA §12.

**Enforcement location:** Storage/controller authorization, snapshot/clone/export lineage, retained copies, keys and media sanitization services.

**Delivery disposition:** `PARTIAL_RESOURCE_CREATION_EXTERNAL_LIFECYCLE`.

**Related code/procedure:** [terraform/modules/nutanix-workload/main.tf.json](../../terraform/modules/nutanix-workload/main.tf.json) · [terraform/modules/openstack-workload/main.tf.json](../../terraform/modules/openstack-workload/main.tf.json) · [docs/DNS_LIFECYCLE.md](../DNS_LIFECYCLE.md). These artifacts do not individually or collectively establish the entire requirement.

**Current evidence limit:** SOURCE_AND_LOCAL_FIXTURE_ONLY_OR_NOT_IMPLEMENTED; NOT_NATIVE_QUALIFIED. Actual native evidence is not supplied.

**Outstanding dependency:** Boot/data volume references and DNS retirement do not implement complete copy inventory, cross-owner export authorization, retention/hold policy, sanitization, receipt or safe shared-resource deletion.

| Assertion | Exact source focus | Required site-specific completion |
| --- | --- | --- |
| STO-002/A01 | Storage service profiles SHALL define measurable capacity/performance, consistency, replication, snapshot/clone and portability semantics and SHALL be tested under contention and the accepted failure condition. | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |

**Verification:** [CT-039](test-specifications.md#CT-039) · [CT-052](test-specifications.md#CT-052) · [CT-060](test-specifications.md#CT-060). Apply the referenced procedure to the actual enforcement location and this focus; include effective negative/failure observations where the original criterion requires them.

**Applicability and acceptance:** TO_BE_DECIDED_FOR_ACTUAL_SERVICE; NOT_AUTO_NA. The accountable project role records applicability, configuration and evidence; this reusable allocation does not invent those decisions.

<a id="STO-003"></a>
## STO-003

Storage release and reuse SHALL reconcile all known copies and legal/administrative holds, apply an approved sanitization method and retain a receipt describing scope, method, verification and exceptions.

**Source role:** Storage operations. **Original design references:** RA §12.

**Enforcement location:** Storage/controller authorization, snapshot/clone/export lineage, retained copies, keys and media sanitization services.

**Delivery disposition:** `PARTIAL_RESOURCE_CREATION_EXTERNAL_LIFECYCLE`.

**Related code/procedure:** [terraform/modules/nutanix-workload/main.tf.json](../../terraform/modules/nutanix-workload/main.tf.json) · [terraform/modules/openstack-workload/main.tf.json](../../terraform/modules/openstack-workload/main.tf.json) · [docs/DNS_LIFECYCLE.md](../DNS_LIFECYCLE.md). These artifacts do not individually or collectively establish the entire requirement.

**Current evidence limit:** SOURCE_AND_LOCAL_FIXTURE_ONLY_OR_NOT_IMPLEMENTED; NOT_NATIVE_QUALIFIED. Actual native evidence is not supplied.

**Outstanding dependency:** Boot/data volume references and DNS retirement do not implement complete copy inventory, cross-owner export authorization, retention/hold policy, sanitization, receipt or safe shared-resource deletion.

| Assertion | Exact source focus | Required site-specific completion |
| --- | --- | --- |
| STO-003/A01 | Storage release and reuse SHALL reconcile all known copies and legal/administrative holds, apply an approved sanitization method and retain a receipt describing scope, method, verification and exceptions. | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |

**Verification:** [CT-053](test-specifications.md#CT-053) · [CT-059](test-specifications.md#CT-059) · [CT-078](test-specifications.md#CT-078). Apply the referenced procedure to the actual enforcement location and this focus; include effective negative/failure observations where the original criterion requires them.

**Applicability and acceptance:** TO_BE_DECIDED_FOR_ACTUAL_SERVICE; NOT_AUTO_NA. The accountable project role records applicability, configuration and evidence; this reusable allocation does not invent those decisions.

<a id="IAM-001"></a>
## IAM-001

Human, workload and automation identities SHALL have separately scoped authorization, credential lifecycle and accountability; no tenant identity SHALL acquire provider foundation authority through role or group inheritance.

**Source role:** Identity operations. **Original design references:** RA §13.

**Enforcement location:** Enterprise IAM/PKI/KMS, consuming endpoint policy, session caches and independently controlled recovery custody.

**Delivery disposition:** `EXTERNAL_SECURITY_SERVICE_REQUIRED`.

**Related code/procedure:** [lab/mtls_fixture.py](../../lab/mtls_fixture.py) · [docs/SERVICE_IDENTITY.md](../SERVICE_IDENTITY.md) · [tools/nsx_observe.py](../../tools/nsx_observe.py). These artifacts do not individually or collectively establish the entire requirement.

**Current evidence limit:** SOURCE_AND_LOCAL_FIXTURE_ONLY_OR_NOT_IMPLEMENTED; NOT_NATIVE_QUALIFIED. Actual native evidence is not supplied.

**Outstanding dependency:** Temporary mTLS fixtures and verified client HTTPS are not enterprise authentication/authorization, revocation, FIPS/module approval, at-rest encryption, key custody, algorithm transition or native KMS outage qualification.

| Assertion | Exact source focus | Required site-specific completion |
| --- | --- | --- |
| IAM-001/A01 | Human | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |
| IAM-001/A02 | workload | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |
| IAM-001/A03 | automation identities | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |
| IAM-001/A04 | role or group inheritance | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |

**Verification:** [CT-019](test-specifications.md#CT-019) · [CT-027](test-specifications.md#CT-027) · [CT-028](test-specifications.md#CT-028). Apply the referenced procedure to the actual enforcement location and this focus; include effective negative/failure observations where the original criterion requires them.

**Applicability and acceptance:** TO_BE_DECIDED_FOR_ACTUAL_SERVICE; NOT_AUTO_NA. The accountable project role records applicability, configuration and evidence; this reusable allocation does not invent those decisions.

<a id="IAM-002"></a>
## IAM-002

Privileged access SHALL use the approved hardened path, strong authentication, least privilege and time-bound delegation; emergency and supplier access SHALL be logged, tested and revoked after use.

**Source role:** Identity operations. **Original design references:** RA §13.

**Enforcement location:** Enterprise IAM/PKI/KMS, consuming endpoint policy, session caches and independently controlled recovery custody.

**Delivery disposition:** `EXTERNAL_SECURITY_SERVICE_REQUIRED`.

**Related code/procedure:** [lab/mtls_fixture.py](../../lab/mtls_fixture.py) · [docs/SERVICE_IDENTITY.md](../SERVICE_IDENTITY.md) · [tools/nsx_observe.py](../../tools/nsx_observe.py). These artifacts do not individually or collectively establish the entire requirement.

**Current evidence limit:** SOURCE_AND_LOCAL_FIXTURE_ONLY_OR_NOT_IMPLEMENTED; NOT_NATIVE_QUALIFIED. Actual native evidence is not supplied.

**Outstanding dependency:** Temporary mTLS fixtures and verified client HTTPS are not enterprise authentication/authorization, revocation, FIPS/module approval, at-rest encryption, key custody, algorithm transition or native KMS outage qualification.

| Assertion | Exact source focus | Required site-specific completion |
| --- | --- | --- |
| IAM-002/A01 | Privileged access SHALL use the approved hardened path, strong authentication, least privilege and time-bound delegation | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |
| IAM-002/A02 | emergency and supplier access SHALL be logged, tested and revoked after use. | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |

**Verification:** [CT-026](test-specifications.md#CT-026) · [CT-027](test-specifications.md#CT-027) · [CT-079](test-specifications.md#CT-079). Apply the referenced procedure to the actual enforcement location and this focus; include effective negative/failure observations where the original criterion requires them.

**Applicability and acceptance:** TO_BE_DECIDED_FOR_ACTUAL_SERVICE; NOT_AUTO_NA. The accountable project role records applicability, configuration and evidence; this reusable allocation does not invent those decisions.

<a id="IAM-003"></a>
## IAM-003

Credential and session revocation SHALL be verified at the consuming service within the approved propagation interval, including cached tokens and delegated grants.

**Source role:** Identity operations. **Original design references:** RA §13.

**Enforcement location:** Enterprise IAM/PKI/KMS, consuming endpoint policy, session caches and independently controlled recovery custody.

**Delivery disposition:** `EXTERNAL_SECURITY_SERVICE_REQUIRED`.

**Related code/procedure:** [lab/mtls_fixture.py](../../lab/mtls_fixture.py) · [docs/SERVICE_IDENTITY.md](../SERVICE_IDENTITY.md) · [tools/nsx_observe.py](../../tools/nsx_observe.py). These artifacts do not individually or collectively establish the entire requirement.

**Current evidence limit:** SOURCE_AND_LOCAL_FIXTURE_ONLY_OR_NOT_IMPLEMENTED; NOT_NATIVE_QUALIFIED. Actual native evidence is not supplied.

**Outstanding dependency:** Temporary mTLS fixtures and verified client HTTPS are not enterprise authentication/authorization, revocation, FIPS/module approval, at-rest encryption, key custody, algorithm transition or native KMS outage qualification.

| Assertion | Exact source focus | Required site-specific completion |
| --- | --- | --- |
| IAM-003/A01 | Credential and session revocation SHALL be verified at the consuming service within the approved propagation interval, including cached tokens and delegated grants. | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |

**Verification:** [CT-028](test-specifications.md#CT-028) · [CT-077](test-specifications.md#CT-077) · [CT-079](test-specifications.md#CT-079). Apply the referenced procedure to the actual enforcement location and this focus; include effective negative/failure observations where the original criterion requires them.

**Applicability and acceptance:** TO_BE_DECIDED_FOR_ACTUAL_SERVICE; NOT_AUTO_NA. The accountable project role records applicability, configuration and evidence; this reusable allocation does not invent those decisions.

<a id="CRY-001"></a>
## CRY-001

Protected data services SHALL enforce their versioned cryptographic profile at rest and in transit; the profile SHALL identify approved algorithms/modes, endpoint identity validation, module/operating-environment evidence and exceptions.

**Source role:** Security authority. **Original design references:** RA §13.

**Enforcement location:** Enterprise IAM/PKI/KMS, consuming endpoint policy, session caches and independently controlled recovery custody.

**Delivery disposition:** `EXTERNAL_SECURITY_SERVICE_REQUIRED`.

**Related code/procedure:** [lab/mtls_fixture.py](../../lab/mtls_fixture.py) · [docs/SERVICE_IDENTITY.md](../SERVICE_IDENTITY.md) · [tools/nsx_observe.py](../../tools/nsx_observe.py). These artifacts do not individually or collectively establish the entire requirement.

**Current evidence limit:** SOURCE_AND_LOCAL_FIXTURE_ONLY_OR_NOT_IMPLEMENTED; NOT_NATIVE_QUALIFIED. Actual native evidence is not supplied.

**Outstanding dependency:** Temporary mTLS fixtures and verified client HTTPS are not enterprise authentication/authorization, revocation, FIPS/module approval, at-rest encryption, key custody, algorithm transition or native KMS outage qualification.

| Assertion | Exact source focus | Required site-specific completion |
| --- | --- | --- |
| CRY-001/A01 | at rest | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |
| CRY-001/A02 | in transit | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |
| CRY-001/A03 | algorithms/modes | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |
| CRY-001/A04 | endpoint identity validation | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |
| CRY-001/A05 | module/operating-environment evidence | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |
| CRY-001/A06 | exceptions | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |

**Verification:** [CT-028](test-specifications.md#CT-028) · [CT-038](test-specifications.md#CT-038) · [CT-063](test-specifications.md#CT-063). Apply the referenced procedure to the actual enforcement location and this focus; include effective negative/failure observations where the original criterion requires them.

**Applicability and acceptance:** TO_BE_DECIDED_FOR_ACTUAL_SERVICE; NOT_AUTO_NA. The accountable project role records applicability, configuration and evidence; this reusable allocation does not invent those decisions.

<a id="CRY-002"></a>
## CRY-002

Key use, administration, recovery and destruction SHALL have explicit separated authority and dependency records; key destruction SHALL NOT invalidate required retained-data recovery without an approved disposition decision.

**Source role:** Key-management operations. **Original design references:** RA §13.

**Enforcement location:** Enterprise IAM/PKI/KMS, consuming endpoint policy, session caches and independently controlled recovery custody.

**Delivery disposition:** `EXTERNAL_SECURITY_SERVICE_REQUIRED`.

**Related code/procedure:** [lab/mtls_fixture.py](../../lab/mtls_fixture.py) · [docs/SERVICE_IDENTITY.md](../SERVICE_IDENTITY.md) · [tools/nsx_observe.py](../../tools/nsx_observe.py). These artifacts do not individually or collectively establish the entire requirement.

**Current evidence limit:** SOURCE_AND_LOCAL_FIXTURE_ONLY_OR_NOT_IMPLEMENTED; NOT_NATIVE_QUALIFIED. Actual native evidence is not supplied.

**Outstanding dependency:** Temporary mTLS fixtures and verified client HTTPS are not enterprise authentication/authorization, revocation, FIPS/module approval, at-rest encryption, key custody, algorithm transition or native KMS outage qualification.

| Assertion | Exact source focus | Required site-specific completion |
| --- | --- | --- |
| CRY-002/A01 | Key use | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |
| CRY-002/A02 | administration | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |
| CRY-002/A03 | recovery | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |
| CRY-002/A04 | destruction | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |
| CRY-002/A05 | retained-data recovery | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |

**Verification:** [CT-038](test-specifications.md#CT-038) · [CT-053](test-specifications.md#CT-053) · [CT-059](test-specifications.md#CT-059). Apply the referenced procedure to the actual enforcement location and this focus; include effective negative/failure observations where the original criterion requires them.

**Applicability and acceptance:** TO_BE_DECIDED_FOR_ACTUAL_SERVICE; NOT_AUTO_NA. The accountable project role records applicability, configuration and evidence; this reusable allocation does not invent those decisions.

<a id="CRY-003"></a>
## CRY-003

KMS/trust-service outage behavior SHALL be tested and SHALL NOT enable plaintext fallback; cryptographic inventory, certificate rotation and algorithm-transition plans SHALL be maintained.

**Source role:** Key-management operations. **Original design references:** RA §13.

**Enforcement location:** Enterprise IAM/PKI/KMS, consuming endpoint policy, session caches and independently controlled recovery custody.

**Delivery disposition:** `EXTERNAL_SECURITY_SERVICE_REQUIRED`.

**Related code/procedure:** [lab/mtls_fixture.py](../../lab/mtls_fixture.py) · [docs/SERVICE_IDENTITY.md](../SERVICE_IDENTITY.md) · [tools/nsx_observe.py](../../tools/nsx_observe.py). These artifacts do not individually or collectively establish the entire requirement.

**Current evidence limit:** SOURCE_AND_LOCAL_FIXTURE_ONLY_OR_NOT_IMPLEMENTED; NOT_NATIVE_QUALIFIED. Actual native evidence is not supplied.

**Outstanding dependency:** Temporary mTLS fixtures and verified client HTTPS are not enterprise authentication/authorization, revocation, FIPS/module approval, at-rest encryption, key custody, algorithm transition or native KMS outage qualification.

| Assertion | Exact source focus | Required site-specific completion |
| --- | --- | --- |
| CRY-003/A01 | KMS/trust-service outage behavior SHALL be tested and SHALL NOT enable plaintext fallback | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |
| CRY-003/A02 | cryptographic inventory, certificate rotation and algorithm-transition plans SHALL be maintained. | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |

**Verification:** [CT-028](test-specifications.md#CT-028) · [CT-038](test-specifications.md#CT-038) · [CT-055](test-specifications.md#CT-055). Apply the referenced procedure to the actual enforcement location and this focus; include effective negative/failure observations where the original criterion requires them.

**Applicability and acceptance:** TO_BE_DECIDED_FOR_ACTUAL_SERVICE; NOT_AUTO_NA. The accountable project role records applicability, configuration and evidence; this reusable allocation does not invent those decisions.

<a id="IMG-001"></a>
## IMG-001

Only approved versioned images and baselines SHALL be deployed; each SHALL include provenance, digest, support status, hardening and vulnerability disposition with a retirement/rebuild policy.

**Source role:** Platform engineering. **Original design references:** RA §11.

**Enforcement location:** Approved image registry, artifact signature/digest policy and native guest/platform hardening configuration.

**Delivery disposition:** `EXTERNAL_IMAGE_AND_BASELINE_SERVICE_REQUIRED`.

**Related code/procedure:** [terraform/modules/nutanix-workload/main.tf.json](../../terraform/modules/nutanix-workload/main.tf.json) · [terraform/modules/vsphere-workload/main.tf.json](../../terraform/modules/vsphere-workload/main.tf.json) · [terraform/modules/openstack-workload/main.tf.json](../../terraform/modules/openstack-workload/main.tf.json). These artifacts do not individually or collectively establish the entire requirement.

**Current evidence limit:** SOURCE_AND_LOCAL_FIXTURE_ONLY_OR_NOT_IMPLEMENTED; NOT_NATIVE_QUALIFIED. Actual native evidence is not supplied.

**Outstanding dependency:** Modules consume image/template references; a governed image catalogue, provenance/revocation/hardening agents, vulnerability disposition and runtime guest compliance are not implemented.

| Assertion | Exact source focus | Required site-specific completion |
| --- | --- | --- |
| IMG-001/A01 | Only approved versioned images and baselines SHALL be deployed | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |
| IMG-001/A02 | each SHALL include provenance, digest, support status, hardening and vulnerability disposition with a retirement/rebuild policy. | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |

**Verification:** [CT-036](test-specifications.md#CT-036) · [CT-040](test-specifications.md#CT-040) · [CT-041](test-specifications.md#CT-041). Apply the referenced procedure to the actual enforcement location and this focus; include effective negative/failure observations where the original criterion requires them.

**Applicability and acceptance:** TO_BE_DECIDED_FOR_ACTUAL_SERVICE; NOT_AUTO_NA. The accountable project role records applicability, configuration and evidence; this reusable allocation does not invent those decisions.

<a id="IMG-002"></a>
## IMG-002

Runtime configuration SHALL be verified against the required baseline after provisioning and material change; unsupported protection agents or disabled mandatory controls SHALL not be silently accepted.

**Source role:** Platform engineering. **Original design references:** RA §11.

**Enforcement location:** Approved image registry, artifact signature/digest policy and native guest/platform hardening configuration.

**Delivery disposition:** `EXTERNAL_IMAGE_AND_BASELINE_SERVICE_REQUIRED`.

**Related code/procedure:** [terraform/modules/nutanix-workload/main.tf.json](../../terraform/modules/nutanix-workload/main.tf.json) · [terraform/modules/vsphere-workload/main.tf.json](../../terraform/modules/vsphere-workload/main.tf.json) · [terraform/modules/openstack-workload/main.tf.json](../../terraform/modules/openstack-workload/main.tf.json). These artifacts do not individually or collectively establish the entire requirement.

**Current evidence limit:** SOURCE_AND_LOCAL_FIXTURE_ONLY_OR_NOT_IMPLEMENTED; NOT_NATIVE_QUALIFIED. Actual native evidence is not supplied.

**Outstanding dependency:** Modules consume image/template references; a governed image catalogue, provenance/revocation/hardening agents, vulnerability disposition and runtime guest compliance are not implemented.

| Assertion | Exact source focus | Required site-specific completion |
| --- | --- | --- |
| IMG-002/A01 | Runtime configuration SHALL be verified against the required baseline after provisioning and material change | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |
| IMG-002/A02 | unsupported protection agents or disabled mandatory controls SHALL not be silently accepted. | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |

**Verification:** [CT-014](test-specifications.md#CT-014) · [CT-036](test-specifications.md#CT-036) · [CT-040](test-specifications.md#CT-040). Apply the referenced procedure to the actual enforcement location and this focus; include effective negative/failure observations where the original criterion requires them.

**Applicability and acceptance:** TO_BE_DECIDED_FOR_ACTUAL_SERVICE; NOT_AUTO_NA. The accountable project role records applicability, configuration and evidence; this reusable allocation does not invent those decisions.

<a id="BKP-001"></a>
## BKP-001

Backup consumers SHALL NOT receive connectivity to backup management interfaces merely because they consume backup service.

**Source role:** Backup operations. **Original design references:** RA §12; RA §27.

**Enforcement location:** Backup management and data endpoints, protected-copy authority, catalogues/keys and isolated restore target.

**Delivery disposition:** `EXTERNAL_PROTECTION_SERVICE_REQUIRED`.

**Related code/procedure:** [docs/operations/README.md](../operations/README.md) · [sources/implementation_backlog.csv](../../sources/implementation_backlog.csv). These artifacts do not individually or collectively establish the entire requirement.

**Current evidence limit:** SOURCE_AND_LOCAL_FIXTURE_ONLY_OR_NOT_IMPLEMENTED; NOT_NATIVE_QUALIFIED. Actual native evidence is not supplied.

**Outstanding dependency:** No complete native backup/KMS/catalogue integration, independent deletion control, measured application-consistent restore or retention-aware release is supplied.

| Assertion | Exact source focus | Required site-specific completion |
| --- | --- | --- |
| BKP-001/A01 | Backup consumers SHALL NOT receive connectivity to backup management interfaces merely because they consume backup service. | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |

**Verification:** [CT-004](test-specifications.md#CT-004) · [CT-051](test-specifications.md#CT-051). Apply the referenced procedure to the actual enforcement location and this focus; include effective negative/failure observations where the original criterion requires them.

**Applicability and acceptance:** TO_BE_DECIDED_FOR_ACTUAL_SERVICE; NOT_AUTO_NA. The accountable project role records applicability, configuration and evidence; this reusable allocation does not invent those decisions.

<a id="BKP-002"></a>
## BKP-002

Restore workflows SHALL enforce the same tenant, security-zone, identity, and evidence controls as backup ingestion.

**Source role:** Backup operations. **Original design references:** RA §12; RA §27.

**Enforcement location:** Backup management and data endpoints, protected-copy authority, catalogues/keys and isolated restore target.

**Delivery disposition:** `EXTERNAL_PROTECTION_SERVICE_REQUIRED`.

**Related code/procedure:** [docs/operations/README.md](../operations/README.md) · [sources/implementation_backlog.csv](../../sources/implementation_backlog.csv). These artifacts do not individually or collectively establish the entire requirement.

**Current evidence limit:** SOURCE_AND_LOCAL_FIXTURE_ONLY_OR_NOT_IMPLEMENTED; NOT_NATIVE_QUALIFIED. Actual native evidence is not supplied.

**Outstanding dependency:** No complete native backup/KMS/catalogue integration, independent deletion control, measured application-consistent restore or retention-aware release is supplied.

| Assertion | Exact source focus | Required site-specific completion |
| --- | --- | --- |
| BKP-002/A01 | Restore workflows SHALL enforce the same tenant, security-zone, identity, and evidence controls as backup ingestion. | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |

**Verification:** [CT-052](test-specifications.md#CT-052) · [CT-054](test-specifications.md#CT-054). Apply the referenced procedure to the actual enforcement location and this focus; include effective negative/failure observations where the original criterion requires them.

**Applicability and acceptance:** TO_BE_DECIDED_FOR_ACTUAL_SERVICE; NOT_AUTO_NA. The accountable project role records applicability, configuration and evidence; this reusable allocation does not invent those decisions.

<a id="BKP-003"></a>
## BKP-003

Every protected production WSD SHALL have a BackupPolicy with consistency, retention, location, key and protected-copy requirements; successful isolated restore SHALL be demonstrated at the policy cadence.

**Source role:** Backup operations. **Original design references:** RA §12; RA §27.

**Enforcement location:** Backup management and data endpoints, protected-copy authority, catalogues/keys and isolated restore target.

**Delivery disposition:** `EXTERNAL_PROTECTION_SERVICE_REQUIRED`.

**Related code/procedure:** [docs/operations/README.md](../operations/README.md) · [sources/implementation_backlog.csv](../../sources/implementation_backlog.csv). These artifacts do not individually or collectively establish the entire requirement.

**Current evidence limit:** SOURCE_AND_LOCAL_FIXTURE_ONLY_OR_NOT_IMPLEMENTED; NOT_NATIVE_QUALIFIED. Actual native evidence is not supplied.

**Outstanding dependency:** No complete native backup/KMS/catalogue integration, independent deletion control, measured application-consistent restore or retention-aware release is supplied.

| Assertion | Exact source focus | Required site-specific completion |
| --- | --- | --- |
| BKP-003/A01 | consistency | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |
| BKP-003/A02 | retention | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |
| BKP-003/A03 | location | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |
| BKP-003/A04 | key | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |
| BKP-003/A05 | protected-copy requirements | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |
| BKP-003/A06 | successful isolated restore | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |

**Verification:** [CT-051](test-specifications.md#CT-051) · [CT-052](test-specifications.md#CT-052) · [CT-053](test-specifications.md#CT-053). Apply the referenced procedure to the actual enforcement location and this focus; include effective negative/failure observations where the original criterion requires them.

**Applicability and acceptance:** TO_BE_DECIDED_FOR_ACTUAL_SERVICE; NOT_AUTO_NA. The accountable project role records applicability, configuration and evidence; this reusable allocation does not invent those decisions.

<a id="BKP-004"></a>
## BKP-004

Production credentials SHALL NOT be able to destroy or reduce the protection of recovery copies designated independent/immutable; retained copies SHALL keep the keys and catalogue required for authorized recovery.

**Source role:** Backup operations. **Original design references:** RA §12; RA §27.

**Enforcement location:** Backup management and data endpoints, protected-copy authority, catalogues/keys and isolated restore target.

**Delivery disposition:** `EXTERNAL_PROTECTION_SERVICE_REQUIRED`.

**Related code/procedure:** [docs/operations/README.md](../operations/README.md) · [sources/implementation_backlog.csv](../../sources/implementation_backlog.csv). These artifacts do not individually or collectively establish the entire requirement.

**Current evidence limit:** SOURCE_AND_LOCAL_FIXTURE_ONLY_OR_NOT_IMPLEMENTED; NOT_NATIVE_QUALIFIED. Actual native evidence is not supplied.

**Outstanding dependency:** No complete native backup/KMS/catalogue integration, independent deletion control, measured application-consistent restore or retention-aware release is supplied.

| Assertion | Exact source focus | Required site-specific completion |
| --- | --- | --- |
| BKP-004/A01 | Production credentials | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |
| BKP-004/A02 | independent/immutable | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |
| BKP-004/A03 | keys and catalogue | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |

**Verification:** [CT-038](test-specifications.md#CT-038) · [CT-051](test-specifications.md#CT-051) · [CT-053](test-specifications.md#CT-053). Apply the referenced procedure to the actual enforcement location and this focus; include effective negative/failure observations where the original criterion requires them.

**Applicability and acceptance:** TO_BE_DECIDED_FOR_ACTUAL_SERVICE; NOT_AUTO_NA. The accountable project role records applicability, configuration and evidence; this reusable allocation does not invent those decisions.

<a id="REL-001"></a>
## REL-001

Availability and recovery profiles SHALL define measurement scope, SLO, failure tolerance, maintenance treatment, RTO/RPO, consistency, dependencies and test cadence; impact categorization SHALL NOT substitute for these values.

**Source role:** Service owner. **Original design references:** RA §14; RA §26.

**Enforcement location:** Service catalogue, measured surviving resource pools, security-edge and dependency failure/maintenance behaviour.

**Delivery disposition:** `EXTERNAL_CAPACITY_AND_QUALIFICATION_REQUIRED`.

**Related code/procedure:** [docs/engineering/TAD.md](../engineering/TAD.md) · [lab/run_namespace_lab.py](../../lab/run_namespace_lab.py). These artifacts do not individually or collectively establish the entire requirement.

**Current evidence limit:** SOURCE_AND_LOCAL_FIXTURE_ONLY_OR_NOT_IMPLEMENTED; NOT_NATIVE_QUALIFIED. Actual native evidence is not supplied.

**Outstanding dependency:** Illustrative capacity schedules and local link-failure fixtures do not establish measured production SLO/RTO/RPO, qualified limits, complete reservations or procured-to-available inventory.

| Assertion | Exact source focus | Required site-specific completion |
| --- | --- | --- |
| REL-001/A01 | measurement scope | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |
| REL-001/A02 | SLO | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |
| REL-001/A03 | failure tolerance | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |
| REL-001/A04 | maintenance treatment | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |
| REL-001/A05 | RTO/RPO | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |
| REL-001/A06 | consistency | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |
| REL-001/A07 | dependencies | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |
| REL-001/A08 | test cadence | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |

**Verification:** [CT-012](test-specifications.md#CT-012) · [CT-052](test-specifications.md#CT-052) · [CT-054](test-specifications.md#CT-054) · [CT-062](test-specifications.md#CT-062). Apply the referenced procedure to the actual enforcement location and this focus; include effective negative/failure observations where the original criterion requires them.

**Applicability and acceptance:** TO_BE_DECIDED_FOR_ACTUAL_SERVICE; NOT_AUTO_NA. The accountable project role records applicability, configuration and evidence; this reusable allocation does not invent those decisions.

<a id="REL-002"></a>
## REL-002

Recovery/HA capabilities SHALL be measured under the approved load and failure scenario before a platform offers the profile; reported SLOs SHALL disclose exclusions and actual breaches.

**Source role:** Operations/SRE. **Original design references:** RA §14; RA §26.

**Enforcement location:** Service catalogue, measured surviving resource pools, security-edge and dependency failure/maintenance behaviour.

**Delivery disposition:** `EXTERNAL_CAPACITY_AND_QUALIFICATION_REQUIRED`.

**Related code/procedure:** [docs/engineering/TAD.md](../engineering/TAD.md) · [lab/run_namespace_lab.py](../../lab/run_namespace_lab.py). These artifacts do not individually or collectively establish the entire requirement.

**Current evidence limit:** SOURCE_AND_LOCAL_FIXTURE_ONLY_OR_NOT_IMPLEMENTED; NOT_NATIVE_QUALIFIED. Actual native evidence is not supplied.

**Outstanding dependency:** Illustrative capacity schedules and local link-failure fixtures do not establish measured production SLO/RTO/RPO, qualified limits, complete reservations or procured-to-available inventory.

| Assertion | Exact source focus | Required site-specific completion |
| --- | --- | --- |
| REL-002/A01 | Recovery/HA capabilities SHALL be measured under the approved load and failure scenario before a platform offers the profile | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |
| REL-002/A02 | reported SLOs SHALL disclose exclusions and actual breaches. | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |

**Verification:** [CT-012](test-specifications.md#CT-012) · [CT-039](test-specifications.md#CT-039) · [CT-054](test-specifications.md#CT-054) · [CT-056](test-specifications.md#CT-056). Apply the referenced procedure to the actual enforcement location and this focus; include effective negative/failure observations where the original criterion requires them.

**Applicability and acceptance:** TO_BE_DECIDED_FOR_ACTUAL_SERVICE; NOT_AUTO_NA. The accountable project role records applicability, configuration and evidence; this reusable allocation does not invent those decisions.

<a id="PLACE-001"></a>
## PLACE-001

Placement SHALL satisfy all mandatory security, assurance, location, lifecycle, capacity and recovery constraints using a current qualified platform profile; unresolved or conflicting constraints SHALL reject the request.

**Source role:** Automation platform. **Original design references:** RA §13; RA §14.

**Enforcement location:** Native scheduler eligibility, eligible host pools, HA admission and recovery target/data-location constraints.

**Delivery disposition:** `PARTIAL_VM_PREPARATION_ONLY`.

**Related code/procedure:** [terraform/modules/nutanix-workload/main.tf.json](../../terraform/modules/nutanix-workload/main.tf.json) · [terraform/modules/vsphere-workload/main.tf.json](../../terraform/modules/vsphere-workload/main.tf.json) · [terraform/modules/openstack-workload/main.tf.json](../../terraform/modules/openstack-workload/main.tf.json). These artifacts do not individually or collectively establish the entire requirement.

**Current evidence limit:** SOURCE_AND_LOCAL_FIXTURE_ONLY_OR_NOT_IMPLEMENTED; NOT_NATIVE_QUALIFIED. Actual native evidence is not supplied.

**Outstanding dependency:** VM preparation consumes accepted placement resources; it does not create/qualify host co-residency policy, evacuation/HA restrictions, independent sites, location agreements, guarantees or capacity under failure.

| Assertion | Exact source focus | Required site-specific completion |
| --- | --- | --- |
| PLACE-001/A01 | Placement SHALL satisfy all mandatory security, assurance, location, lifecycle, capacity and recovery constraints using a current qualified platform profile | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |
| PLACE-001/A02 | unresolved or conflicting constraints SHALL reject the request. | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |

**Verification:** [CT-018](test-specifications.md#CT-018) · [CT-035](test-specifications.md#CT-035) · [CT-056](test-specifications.md#CT-056) · [CT-061](test-specifications.md#CT-061). Apply the referenced procedure to the actual enforcement location and this focus; include effective negative/failure observations where the original criterion requires them.

**Applicability and acceptance:** TO_BE_DECIDED_FOR_ACTUAL_SERVICE; NOT_AUTO_NA. The accountable project role records applicability, configuration and evidence; this reusable allocation does not invent those decisions.

<a id="PLACE-002"></a>
## PLACE-002

Data, backup, telemetry, diagnostic, control-plane, administrative-access and key locations/control constraints SHALL be represented separately and enforced through approved profiles and agreements.

**Source role:** Service owner. **Original design references:** RA §13; RA §14.

**Enforcement location:** Native scheduler eligibility, eligible host pools, HA admission and recovery target/data-location constraints.

**Delivery disposition:** `PARTIAL_VM_PREPARATION_ONLY`.

**Related code/procedure:** [terraform/modules/nutanix-workload/main.tf.json](../../terraform/modules/nutanix-workload/main.tf.json) · [terraform/modules/vsphere-workload/main.tf.json](../../terraform/modules/vsphere-workload/main.tf.json) · [terraform/modules/openstack-workload/main.tf.json](../../terraform/modules/openstack-workload/main.tf.json). These artifacts do not individually or collectively establish the entire requirement.

**Current evidence limit:** SOURCE_AND_LOCAL_FIXTURE_ONLY_OR_NOT_IMPLEMENTED; NOT_NATIVE_QUALIFIED. Actual native evidence is not supplied.

**Outstanding dependency:** VM preparation consumes accepted placement resources; it does not create/qualify host co-residency policy, evacuation/HA restrictions, independent sites, location agreements, guarantees or capacity under failure.

| Assertion | Exact source focus | Required site-specific completion |
| --- | --- | --- |
| PLACE-002/A01 | Data | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |
| PLACE-002/A02 | backup | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |
| PLACE-002/A03 | telemetry | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |
| PLACE-002/A04 | diagnostic | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |
| PLACE-002/A05 | control-plane | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |
| PLACE-002/A06 | administrative-access | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |
| PLACE-002/A07 | key locations/control constraints | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |

**Verification:** [CT-061](test-specifications.md#CT-061) · [CT-079](test-specifications.md#CT-079). Apply the referenced procedure to the actual enforcement location and this focus; include effective negative/failure observations where the original criterion requires them.

**Applicability and acceptance:** TO_BE_DECIDED_FOR_ACTUAL_SERVICE; NOT_AUTO_NA. The accountable project role records applicability, configuration and evidence; this reusable allocation does not invent those decisions.

<a id="PLACE-003"></a>
## PLACE-003

Each portable service class SHALL have a documented exit path, declared proprietary dependencies and representative export/recovery evidence; residency or format support alone SHALL NOT be presented as portability or sovereignty proof.

**Source role:** Architecture authority. **Original design references:** RA §13; RA §14.

**Enforcement location:** Native scheduler eligibility, eligible host pools, HA admission and recovery target/data-location constraints.

**Delivery disposition:** `PARTIAL_VM_PREPARATION_ONLY`.

**Related code/procedure:** [terraform/modules/nutanix-workload/main.tf.json](../../terraform/modules/nutanix-workload/main.tf.json) · [terraform/modules/vsphere-workload/main.tf.json](../../terraform/modules/vsphere-workload/main.tf.json) · [terraform/modules/openstack-workload/main.tf.json](../../terraform/modules/openstack-workload/main.tf.json). These artifacts do not individually or collectively establish the entire requirement.

**Current evidence limit:** SOURCE_AND_LOCAL_FIXTURE_ONLY_OR_NOT_IMPLEMENTED; NOT_NATIVE_QUALIFIED. Actual native evidence is not supplied.

**Outstanding dependency:** VM preparation consumes accepted placement resources; it does not create/qualify host co-residency policy, evacuation/HA restrictions, independent sites, location agreements, guarantees or capacity under failure.

| Assertion | Exact source focus | Required site-specific completion |
| --- | --- | --- |
| PLACE-003/A01 | Each portable service class SHALL have a documented exit path, declared proprietary dependencies and representative export/recovery evidence | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |
| PLACE-003/A02 | residency or format support alone SHALL NOT be presented as portability or sovereignty proof. | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |

**Verification:** [CT-060](test-specifications.md#CT-060) · [CT-073](test-specifications.md#CT-073). Apply the referenced procedure to the actual enforcement location and this focus; include effective negative/failure observations where the original criterion requires them.

**Applicability and acceptance:** TO_BE_DECIDED_FOR_ACTUAL_SERVICE; NOT_AUTO_NA. The accountable project role records applicability, configuration and evidence; this reusable allocation does not invent those decisions.

<a id="SVCM-001"></a>
## SVCM-001

The service catalogue SHALL publish entitlements, hard quotas, reservation semantics, availability/recovery targets, supported capabilities and lifecycle obligations with stable service identifiers.

**Source role:** Service owner. **Original design references:** RA §4; RA §20.

**Enforcement location:** Service catalogue, measured surviving resource pools, security-edge and dependency failure/maintenance behaviour.

**Delivery disposition:** `EXTERNAL_CAPACITY_AND_QUALIFICATION_REQUIRED`.

**Related code/procedure:** [docs/engineering/TAD.md](../engineering/TAD.md) · [lab/run_namespace_lab.py](../../lab/run_namespace_lab.py). These artifacts do not individually or collectively establish the entire requirement.

**Current evidence limit:** SOURCE_AND_LOCAL_FIXTURE_ONLY_OR_NOT_IMPLEMENTED; NOT_NATIVE_QUALIFIED. Actual native evidence is not supplied.

**Outstanding dependency:** Illustrative capacity schedules and local link-failure fixtures do not establish measured production SLO/RTO/RPO, qualified limits, complete reservations or procured-to-available inventory.

| Assertion | Exact source focus | Required site-specific completion |
| --- | --- | --- |
| SVCM-001/A01 | The service catalogue SHALL publish entitlements, hard quotas, reservation semantics, availability/recovery targets, supported capabilities and lifecycle obligations with stable service identifiers. | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |

**Verification:** [CT-019](test-specifications.md#CT-019) · [CT-056](test-specifications.md#CT-056) · [CT-062](test-specifications.md#CT-062). Apply the referenced procedure to the actual enforcement location and this focus; include effective negative/failure observations where the original criterion requires them.

**Applicability and acceptance:** TO_BE_DECIDED_FOR_ACTUAL_SERVICE; NOT_AUTO_NA. The accountable project role records applicability, configuration and evidence; this reusable allocation does not invent those decisions.

<a id="SVCM-002"></a>
## SVCM-002

Capacity inventory SHALL reconcile procured, staged, commissioned, available, reserved and consumed resources and SHALL report unused/stranded capacity, ownership and support-life exposure.

**Source role:** Capacity management. **Original design references:** RA §4; RA §20.

**Enforcement location:** Service catalogue, measured surviving resource pools, security-edge and dependency failure/maintenance behaviour.

**Delivery disposition:** `EXTERNAL_CAPACITY_AND_QUALIFICATION_REQUIRED`.

**Related code/procedure:** [docs/engineering/TAD.md](../engineering/TAD.md) · [lab/run_namespace_lab.py](../../lab/run_namespace_lab.py). These artifacts do not individually or collectively establish the entire requirement.

**Current evidence limit:** SOURCE_AND_LOCAL_FIXTURE_ONLY_OR_NOT_IMPLEMENTED; NOT_NATIVE_QUALIFIED. Actual native evidence is not supplied.

**Outstanding dependency:** Illustrative capacity schedules and local link-failure fixtures do not establish measured production SLO/RTO/RPO, qualified limits, complete reservations or procured-to-available inventory.

| Assertion | Exact source focus | Required site-specific completion |
| --- | --- | --- |
| SVCM-002/A01 | Capacity inventory SHALL reconcile procured, staged, commissioned, available, reserved and consumed resources and SHALL report unused/stranded capacity, ownership and support-life exposure. | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |

**Verification:** [CT-074](test-specifications.md#CT-074). Apply the referenced procedure to the actual enforcement location and this focus; include effective negative/failure observations where the original criterion requires them.

**Applicability and acceptance:** TO_BE_DECIDED_FOR_ACTUAL_SERVICE; NOT_AUTO_NA. The accountable project role records applicability, configuration and evidence; this reusable allocation does not invent those decisions.

<a id="RESP-001"></a>
## RESP-001

Every applicable infrastructure/application control and recovery dependency SHALL have a provider, tenant or shared responsibility assignment and evidence owner; unresolved mandatory responsibilities SHALL block Service Ready.

**Source role:** Service owner. **Original design references:** RA §23; RA §26.

**Enforcement location:** Accepted service/profile and topology records; native domain/identity boundaries implement selected constraints.

**Delivery disposition:** `PARTIAL_DESIGN_AND_CANDIDATE`.

**Related code/procedure:** [docs/architecture/RAD.md](../architecture/RAD.md) · [docs/engineering/TAD.md](../engineering/TAD.md) · [tools/input_review.py](../../tools/input_review.py). These artifacts do not individually or collectively establish the entire requirement.

**Current evidence limit:** SOURCE_AND_LOCAL_FIXTURE_ONLY_OR_NOT_IMPLEMENTED; NOT_NATIVE_QUALIFIED. Actual native evidence is not supplied.

**Outstanding dependency:** No complete authoritative service/profile registry, tenant role enforcement or actual placement/edge evidence is supplied. Input screening covers only its enumerated examples and cannot accept the complete service.

| Assertion | Exact source focus | Required site-specific completion |
| --- | --- | --- |
| RESP-001/A01 | Every applicable infrastructure/application control and recovery dependency SHALL have a provider, tenant or shared responsibility assignment and evidence owner | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |
| RESP-001/A02 | unresolved mandatory responsibilities SHALL block Service Ready. | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |

**Verification:** [CT-062](test-specifications.md#CT-062) · [CT-069](test-specifications.md#CT-069). Apply the referenced procedure to the actual enforcement location and this focus; include effective negative/failure observations where the original criterion requires them.

**Applicability and acceptance:** TO_BE_DECIDED_FOR_ACTUAL_SERVICE; NOT_AUTO_NA. The accountable project role records applicability, configuration and evidence; this reusable allocation does not invent those decisions.

<a id="FAB-001"></a>
## FAB-001

Routine create, update and retirement of tenants/WSDs in a precommissioned overlay service class SHALL NOT require leaf/spine configuration changes; foundation growth and fabric-routed service classes SHALL use separately authorized workflows.

**Source role:** Network engineering. **Original design references:** RA §5.

**Enforcement location:** Physical leaf/spine/border configuration, provider route import/export, VTEP and multihoming control.

**Delivery disposition:** `NOT_IMPLEMENTED_IN_NATIVE_FABRIC_CODE`.

**Related code/procedure:** [docs/engineering/TAD.md](../engineering/TAD.md) · [sources/implementation_backlog.csv](../../sources/implementation_backlog.csv). These artifacts do not individually or collectively establish the entire requirement.

**Current evidence limit:** SOURCE_AND_LOCAL_FIXTURE_ONLY_OR_NOT_IMPLEMENTED; NOT_NATIVE_QUALIFIED. Actual native evidence is not supplied.

**Outstanding dependency:** No accepted switch/EVPN/MLAG/border implementation is part of these modules. Underlay addressing, management, measured interoperability, MTU and failures require the actual fabric engineering/build.

| Assertion | Exact source focus | Required site-specific completion |
| --- | --- | --- |
| FAB-001/A01 | Routine create, update and retirement of tenants/WSDs in a precommissioned overlay service class SHALL NOT require leaf/spine configuration changes | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |
| FAB-001/A02 | foundation growth and fabric-routed service classes SHALL use separately authorized workflows. | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |

**Verification:** [CT-071](test-specifications.md#CT-071) · [CT-072](test-specifications.md#CT-072). Apply the referenced procedure to the actual enforcement location and this focus; include effective negative/failure observations where the original criterion requires them.

**Applicability and acceptance:** TO_BE_DECIDED_FOR_ACTUAL_SERVICE; NOT_AUTO_NA. The accountable project role records applicability, configuration and evidence; this reusable allocation does not invent those decisions.

<a id="FAB-002"></a>
## FAB-002

A physical VRF SHALL be created only when the physical fabric itself must provide L3 routing for a legitimate routing/security domain.

**Source role:** Network engineering. **Original design references:** RA §5.

**Enforcement location:** Physical leaf/spine/border configuration, provider route import/export, VTEP and multihoming control.

**Delivery disposition:** `NOT_IMPLEMENTED_IN_NATIVE_FABRIC_CODE`.

**Related code/procedure:** [docs/engineering/TAD.md](../engineering/TAD.md) · [sources/implementation_backlog.csv](../../sources/implementation_backlog.csv). These artifacts do not individually or collectively establish the entire requirement.

**Current evidence limit:** SOURCE_AND_LOCAL_FIXTURE_ONLY_OR_NOT_IMPLEMENTED; NOT_NATIVE_QUALIFIED. Actual native evidence is not supplied.

**Outstanding dependency:** No accepted switch/EVPN/MLAG/border implementation is part of these modules. Underlay addressing, management, measured interoperability, MTU and failures require the actual fabric engineering/build.

| Assertion | Exact source focus | Required site-specific completion |
| --- | --- | --- |
| FAB-002/A01 | A physical VRF SHALL be created only when the physical fabric itself must provide L3 routing for a legitimate routing/security domain. | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |

**Verification:** [CT-009](test-specifications.md#CT-009) · [CT-072](test-specifications.md#CT-072). Apply the referenced procedure to the actual enforcement location and this focus; include effective negative/failure observations where the original criterion requires them.

**Applicability and acceptance:** TO_BE_DECIDED_FOR_ACTUAL_SERVICE; NOT_AUTO_NA. The accountable project role records applicability, configuration and evidence; this reusable allocation does not invent those decisions.

<a id="FAB-003"></a>
## FAB-003

Function names such as backup, migration, platform, ZIP, or generic transit SHALL NOT by themselves justify a VRF.

**Source role:** Architecture authority. **Original design references:** RA §5.

**Enforcement location:** Physical leaf/spine/border configuration, provider route import/export, VTEP and multihoming control.

**Delivery disposition:** `NOT_IMPLEMENTED_IN_NATIVE_FABRIC_CODE`.

**Related code/procedure:** [docs/engineering/TAD.md](../engineering/TAD.md) · [sources/implementation_backlog.csv](../../sources/implementation_backlog.csv). These artifacts do not individually or collectively establish the entire requirement.

**Current evidence limit:** SOURCE_AND_LOCAL_FIXTURE_ONLY_OR_NOT_IMPLEMENTED; NOT_NATIVE_QUALIFIED. Actual native evidence is not supplied.

**Outstanding dependency:** No accepted switch/EVPN/MLAG/border implementation is part of these modules. Underlay addressing, management, measured interoperability, MTU and failures require the actual fabric engineering/build.

| Assertion | Exact source focus | Required site-specific completion |
| --- | --- | --- |
| FAB-003/A01 | Function names such as backup, migration, platform, ZIP, or generic transit SHALL NOT by themselves justify a VRF. | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |

**Verification:** [CT-025](test-specifications.md#CT-025) · [CT-072](test-specifications.md#CT-072). Apply the referenced procedure to the actual enforcement location and this focus; include effective negative/failure observations where the original criterion requires them.

**Applicability and acceptance:** TO_BE_DECIDED_FOR_ACTUAL_SERVICE; NOT_AUTO_NA. The accountable project role records applicability, configuration and evidence; this reusable allocation does not invent those decisions.

<a id="FAB-004"></a>
## FAB-004

The fabric profile SHALL define addressing/routing authority, control-plane protection, MTU, fault convergence, management isolation, maintenance and measured scale before platform commissioning.

**Source role:** Network engineering. **Original design references:** RA §5.

**Enforcement location:** Physical leaf/spine/border configuration, provider route import/export, VTEP and multihoming control.

**Delivery disposition:** `NOT_IMPLEMENTED_IN_NATIVE_FABRIC_CODE`.

**Related code/procedure:** [docs/engineering/TAD.md](../engineering/TAD.md) · [sources/implementation_backlog.csv](../../sources/implementation_backlog.csv). These artifacts do not individually or collectively establish the entire requirement.

**Current evidence limit:** SOURCE_AND_LOCAL_FIXTURE_ONLY_OR_NOT_IMPLEMENTED; NOT_NATIVE_QUALIFIED. Actual native evidence is not supplied.

**Outstanding dependency:** No accepted switch/EVPN/MLAG/border implementation is part of these modules. Underlay addressing, management, measured interoperability, MTU and failures require the actual fabric engineering/build.

| Assertion | Exact source focus | Required site-specific completion |
| --- | --- | --- |
| FAB-004/A01 | addressing/routing authority | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |
| FAB-004/A02 | control-plane protection | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |
| FAB-004/A03 | MTU | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |
| FAB-004/A04 | fault convergence | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |
| FAB-004/A05 | management isolation | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |
| FAB-004/A06 | maintenance | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |
| FAB-004/A07 | measured scale | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |

**Verification:** [CT-026](test-specifications.md#CT-026) · [CT-032](test-specifications.md#CT-032) · [CT-033](test-specifications.md#CT-033) · [CT-034](test-specifications.md#CT-034). Apply the referenced procedure to the actual enforcement location and this focus; include effective negative/failure observations where the original criterion requires them.

**Applicability and acceptance:** TO_BE_DECIDED_FOR_ACTUAL_SERVICE; NOT_AUTO_NA. The accountable project role records applicability, configuration and evidence; this reusable allocation does not invent those decisions.

<a id="EVPN-001"></a>
## EVPN-001

When EVPN is used, RD/RT/VNI, gateway and multihoming policies SHALL be provider-owned, collision-checked and domain-scoped; unapproved route imports SHALL be denied.

**Source role:** Network engineering. **Original design references:** RA §5.

**Enforcement location:** Physical leaf/spine/border configuration, provider route import/export, VTEP and multihoming control.

**Delivery disposition:** `NOT_IMPLEMENTED_IN_NATIVE_FABRIC_CODE`.

**Related code/procedure:** [docs/engineering/TAD.md](../engineering/TAD.md) · [sources/implementation_backlog.csv](../../sources/implementation_backlog.csv). These artifacts do not individually or collectively establish the entire requirement.

**Current evidence limit:** SOURCE_AND_LOCAL_FIXTURE_ONLY_OR_NOT_IMPLEMENTED; NOT_NATIVE_QUALIFIED. Actual native evidence is not supplied.

**Outstanding dependency:** No accepted switch/EVPN/MLAG/border implementation is part of these modules. Underlay addressing, management, measured interoperability, MTU and failures require the actual fabric engineering/build.

| Assertion | Exact source focus | Required site-specific completion |
| --- | --- | --- |
| EVPN-001/A01 | When EVPN is used, RD/RT/VNI, gateway and multihoming policies SHALL be provider-owned, collision-checked and domain-scoped | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |
| EVPN-001/A02 | unapproved route imports SHALL be denied. | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |

**Verification:** [CT-009](test-specifications.md#CT-009) · [CT-033](test-specifications.md#CT-033) · [CT-072](test-specifications.md#CT-072). Apply the referenced procedure to the actual enforcement location and this focus; include effective negative/failure observations where the original criterion requires them.

**Applicability and acceptance:** TO_BE_DECIDED_FOR_ACTUAL_SERVICE; NOT_AUTO_NA. The accountable project role records applicability, configuration and evidence; this reusable allocation does not invent those decisions.

<a id="EVPN-002"></a>
## EVPN-002

Every multihoming and border interoperability profile SHALL be tested for split-brain, link/peer failure, MTU, route withdrawal and stateful-path behavior; vendor-specific MLAG interoperability SHALL NOT be assumed.

**Source role:** Network engineering. **Original design references:** RA §5.

**Enforcement location:** Physical leaf/spine/border configuration, provider route import/export, VTEP and multihoming control.

**Delivery disposition:** `NOT_IMPLEMENTED_IN_NATIVE_FABRIC_CODE`.

**Related code/procedure:** [docs/engineering/TAD.md](../engineering/TAD.md) · [sources/implementation_backlog.csv](../../sources/implementation_backlog.csv). These artifacts do not individually or collectively establish the entire requirement.

**Current evidence limit:** SOURCE_AND_LOCAL_FIXTURE_ONLY_OR_NOT_IMPLEMENTED; NOT_NATIVE_QUALIFIED. Actual native evidence is not supplied.

**Outstanding dependency:** No accepted switch/EVPN/MLAG/border implementation is part of these modules. Underlay addressing, management, measured interoperability, MTU and failures require the actual fabric engineering/build.

| Assertion | Exact source focus | Required site-specific completion |
| --- | --- | --- |
| EVPN-002/A01 | split-brain | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |
| EVPN-002/A02 | link/peer failure | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |
| EVPN-002/A03 | MTU | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |
| EVPN-002/A04 | route withdrawal | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |
| EVPN-002/A05 | stateful-path behavior | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |

**Verification:** [CT-024](test-specifications.md#CT-024) · [CT-032](test-specifications.md#CT-032) · [CT-034](test-specifications.md#CT-034). Apply the referenced procedure to the actual enforcement location and this focus; include effective negative/failure observations where the original criterion requires them.

**Applicability and acceptance:** TO_BE_DECIDED_FOR_ACTUAL_SERVICE; NOT_AUTO_NA. The accountable project role records applicability, configuration and evidence; this reusable allocation does not invent those decisions.

<a id="PORT-001"></a>
## PORT-001

Every platform SHALL publish a machine-readable capability profile and a tested implementation profile.

**Source role:** Platform engineering. **Original design references:** RA §15; RA §28.

**Enforcement location:** Qualified platform capability/eligibility record and representative native service/exit campaigns.

**Delivery disposition:** `DOCUMENTED_QUALIFICATION_NOT_EXECUTED`.

**Related code/procedure:** [docs/assurance/test-specifications.md](test-specifications.md) · [sources/implementation_backlog.csv](../../sources/implementation_backlog.csv). These artifacts do not individually or collectively establish the entire requirement.

**Current evidence limit:** SOURCE_AND_LOCAL_FIXTURE_ONLY_OR_NOT_IMPLEMENTED; NOT_NATIVE_QUALIFIED. Actual native evidence is not supplied.

**Outstanding dependency:** No active authoritative qualified-platform record, bare-metal/container implementation or complete first/second-platform and exit evidence is supplied; unsupported capability must stay ineligible.

| Assertion | Exact source focus | Required site-specific completion |
| --- | --- | --- |
| PORT-001/A01 | Every platform SHALL publish a machine-readable capability profile and a tested implementation profile. | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |

**Verification:** [CT-015](test-specifications.md#CT-015) · [CT-018](test-specifications.md#CT-018) · [CT-080](test-specifications.md#CT-080). Apply the referenced procedure to the actual enforcement location and this focus; include effective negative/failure observations where the original criterion requires them.

**Applicability and acceptance:** TO_BE_DECIDED_FOR_ACTUAL_SERVICE; NOT_AUTO_NA. The accountable project role records applicability, configuration and evidence; this reusable allocation does not invent those decisions.

<a id="PORT-002"></a>
## PORT-002

A placement decision SHALL fail rather than silently reduce a requested security or availability capability.

**Source role:** Automation platform. **Original design references:** RA §15; RA §28.

**Enforcement location:** Qualified platform capability/eligibility record and representative native service/exit campaigns.

**Delivery disposition:** `DOCUMENTED_QUALIFICATION_NOT_EXECUTED`.

**Related code/procedure:** [docs/assurance/test-specifications.md](test-specifications.md) · [sources/implementation_backlog.csv](../../sources/implementation_backlog.csv). These artifacts do not individually or collectively establish the entire requirement.

**Current evidence limit:** SOURCE_AND_LOCAL_FIXTURE_ONLY_OR_NOT_IMPLEMENTED; NOT_NATIVE_QUALIFIED. Actual native evidence is not supplied.

**Outstanding dependency:** No active authoritative qualified-platform record, bare-metal/container implementation or complete first/second-platform and exit evidence is supplied; unsupported capability must stay ineligible.

| Assertion | Exact source focus | Required site-specific completion |
| --- | --- | --- |
| PORT-002/A01 | A placement decision SHALL fail rather than silently reduce a requested security or availability capability. | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |

**Verification:** [CT-018](test-specifications.md#CT-018) · [CT-061](test-specifications.md#CT-061). Apply the referenced procedure to the actual enforcement location and this focus; include effective negative/failure observations where the original criterion requires them.

**Applicability and acceptance:** TO_BE_DECIDED_FOR_ACTUAL_SERVICE; NOT_AUTO_NA. The accountable project role records applicability, configuration and evidence; this reusable allocation does not invent those decisions.

<a id="PORT-003"></a>
## PORT-003

Platform-specific features MAY be exposed as optional extensions provided the WSD declares the dependency and portability impact.

**Source role:** Architecture authority. **Original design references:** RA §15; RA §28.

**Enforcement location:** Qualified platform capability/eligibility record and representative native service/exit campaigns.

**Delivery disposition:** `DOCUMENTED_QUALIFICATION_NOT_EXECUTED`.

**Related code/procedure:** [docs/assurance/test-specifications.md](test-specifications.md) · [sources/implementation_backlog.csv](../../sources/implementation_backlog.csv). These artifacts do not individually or collectively establish the entire requirement.

**Current evidence limit:** SOURCE_AND_LOCAL_FIXTURE_ONLY_OR_NOT_IMPLEMENTED; NOT_NATIVE_QUALIFIED. Actual native evidence is not supplied.

**Outstanding dependency:** No active authoritative qualified-platform record, bare-metal/container implementation or complete first/second-platform and exit evidence is supplied; unsupported capability must stay ineligible.

| Assertion | Exact source focus | Required site-specific completion |
| --- | --- | --- |
| PORT-003/A01 | Platform-specific features MAY be exposed as optional extensions provided the WSD declares the dependency and portability impact. | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |

**Verification:** [CT-016](test-specifications.md#CT-016) · [CT-060](test-specifications.md#CT-060) · [CT-073](test-specifications.md#CT-073). Apply the referenced procedure to the actual enforcement location and this focus; include effective negative/failure observations where the original criterion requires them.

**Applicability and acceptance:** TO_BE_DECIDED_FOR_ACTUAL_SERVICE; NOT_AUTO_NA. The accountable project role records applicability, configuration and evidence; this reusable allocation does not invent those decisions.

<a id="QUAL-001"></a>
## QUAL-001

Production placement SHALL require a current qualified PlatformProfile containing the exact product/API/provider/hardware tuple, applicable features/licenses, tested limits, evidence and approval; a candidate or documentation snapshot SHALL be ineligible.

**Source role:** Security authority. **Original design references:** RA §15; RA §28.

**Enforcement location:** Qualified platform capability/eligibility record and representative native service/exit campaigns.

**Delivery disposition:** `DOCUMENTED_QUALIFICATION_NOT_EXECUTED`.

**Related code/procedure:** [docs/assurance/test-specifications.md](test-specifications.md) · [sources/implementation_backlog.csv](../../sources/implementation_backlog.csv). These artifacts do not individually or collectively establish the entire requirement.

**Current evidence limit:** SOURCE_AND_LOCAL_FIXTURE_ONLY_OR_NOT_IMPLEMENTED; NOT_NATIVE_QUALIFIED. Actual native evidence is not supplied.

**Outstanding dependency:** No active authoritative qualified-platform record, bare-metal/container implementation or complete first/second-platform and exit evidence is supplied; unsupported capability must stay ineligible.

| Assertion | Exact source focus | Required site-specific completion |
| --- | --- | --- |
| QUAL-001/A01 | product/API/provider/hardware tuple | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |
| QUAL-001/A02 | features/licenses | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |
| QUAL-001/A03 | tested limits | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |
| QUAL-001/A04 | evidence | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |
| QUAL-001/A05 | approval | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |

**Verification:** [CT-015](test-specifications.md#CT-015) · [CT-018](test-specifications.md#CT-018) · [CT-069](test-specifications.md#CT-069). Apply the referenced procedure to the actual enforcement location and this focus; include effective negative/failure observations where the original criterion requires them.

**Applicability and acceptance:** TO_BE_DECIDED_FOR_ACTUAL_SERVICE; NOT_AUTO_NA. The accountable project role records applicability, configuration and evidence; this reusable allocation does not invent those decisions.

<a id="NUT-001"></a>
## NUT-001

New Nutanix automation SHOULD use current supported v2/v4-backed provider resources where those resources satisfy the requirement; legacy resources require an explicit compatibility rationale.

**Source role:** Platform engineering. **Original design references:** RA §16.

**Enforcement location:** Nutanix Prism/AOS/Flow native VPC, external attachment and mandatory category authority.

**Delivery disposition:** `PARTIAL_NATIVE_CANDIDATE_NOT_QUALIFIED`.

**Related code/procedure:** [terraform/modules/nutanix-domain/main.tf.json](../../terraform/modules/nutanix-domain/main.tf.json) · [terraform/modules/nutanix-route/main.tf.json](../../terraform/modules/nutanix-route/main.tf.json) · [tools/nutanix_observe.py](../../tools/nutanix_observe.py). These artifacts do not individually or collectively establish the entire requirement.

**Current evidence limit:** SOURCE_AND_LOCAL_FIXTURE_ONLY_OR_NOT_IMPLEMENTED; NOT_NATIVE_QUALIFIED. Actual native evidence is not supplied.

**Outstanding dependency:** Exact installed AOS/Prism/Flow/API/provider/entitlement and route/selector/asynchronous behaviour remain unqualified; selected resources do not prove a complete ZIP or protected category authority.

| Assertion | Exact source focus | Required site-specific completion |
| --- | --- | --- |
| NUT-001/A01 | New Nutanix automation SHOULD use current supported v2/v4-backed provider resources where those resources satisfy the requirement | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |
| NUT-001/A02 | legacy resources require an explicit compatibility rationale. | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |

**Verification:** [CT-015](test-specifications.md#CT-015) · [CT-018](test-specifications.md#CT-018). Apply the referenced procedure to the actual enforcement location and this focus; include effective negative/failure observations where the original criterion requires them.

**Applicability and acceptance:** TO_BE_DECIDED_FOR_ACTUAL_SERVICE; NOT_AUTO_NA. The accountable project role records applicability, configuration and evidence; this reusable allocation does not invent those decisions.

<a id="NUT-002"></a>
## NUT-002

Nutanix VPC internal routing SHALL NOT be used to bypass a required inter-zone ZIP.

**Source role:** Platform engineering. **Original design references:** RA §16.

**Enforcement location:** Nutanix Prism/AOS/Flow native VPC, external attachment and mandatory category authority.

**Delivery disposition:** `PARTIAL_NATIVE_CANDIDATE_NOT_QUALIFIED`.

**Related code/procedure:** [terraform/modules/nutanix-domain/main.tf.json](../../terraform/modules/nutanix-domain/main.tf.json) · [terraform/modules/nutanix-route/main.tf.json](../../terraform/modules/nutanix-route/main.tf.json) · [tools/nutanix_observe.py](../../tools/nutanix_observe.py). These artifacts do not individually or collectively establish the entire requirement.

**Current evidence limit:** SOURCE_AND_LOCAL_FIXTURE_ONLY_OR_NOT_IMPLEMENTED; NOT_NATIVE_QUALIFIED. Actual native evidence is not supplied.

**Outstanding dependency:** Exact installed AOS/Prism/Flow/API/provider/entitlement and route/selector/asynchronous behaviour remain unqualified; selected resources do not prove a complete ZIP or protected category authority.

| Assertion | Exact source focus | Required site-specific completion |
| --- | --- | --- |
| NUT-002/A01 | Nutanix VPC internal routing SHALL NOT be used to bypass a required inter-zone ZIP. | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |

**Verification:** [CT-003](test-specifications.md#CT-003) · [CT-023](test-specifications.md#CT-023) · [CT-024](test-specifications.md#CT-024). Apply the referenced procedure to the actual enforcement location and this focus; include effective negative/failure observations where the original criterion requires them.

**Applicability and acceptance:** TO_BE_DECIDED_FOR_ACTUAL_SERVICE; NOT_AUTO_NA. The accountable project role records applicability, configuration and evidence; this reusable allocation does not invent those decisions.

<a id="NUT-003"></a>
## NUT-003

Provider-managed categories/metadata used for security SHALL be protected from tenant modification.

**Source role:** Platform engineering. **Original design references:** RA §16.

**Enforcement location:** Nutanix Prism/AOS/Flow native VPC, external attachment and mandatory category authority.

**Delivery disposition:** `PARTIAL_NATIVE_CANDIDATE_NOT_QUALIFIED`.

**Related code/procedure:** [terraform/modules/nutanix-domain/main.tf.json](../../terraform/modules/nutanix-domain/main.tf.json) · [terraform/modules/nutanix-route/main.tf.json](../../terraform/modules/nutanix-route/main.tf.json) · [tools/nutanix_observe.py](../../tools/nutanix_observe.py). These artifacts do not individually or collectively establish the entire requirement.

**Current evidence limit:** SOURCE_AND_LOCAL_FIXTURE_ONLY_OR_NOT_IMPLEMENTED; NOT_NATIVE_QUALIFIED. Actual native evidence is not supplied.

**Outstanding dependency:** Exact installed AOS/Prism/Flow/API/provider/entitlement and route/selector/asynchronous behaviour remain unqualified; selected resources do not prove a complete ZIP or protected category authority.

| Assertion | Exact source focus | Required site-specific completion |
| --- | --- | --- |
| NUT-003/A01 | Provider-managed categories/metadata used for security SHALL be protected from tenant modification. | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |

**Verification:** [CT-020](test-specifications.md#CT-020) · [CT-066](test-specifications.md#CT-066). Apply the referenced procedure to the actual enforcement location and this focus; include effective negative/failure observations where the original criterion requires them.

**Applicability and acceptance:** TO_BE_DECIDED_FOR_ACTUAL_SERVICE; NOT_AUTO_NA. The accountable project role records applicability, configuration and evidence; this reusable allocation does not invent those decisions.

<a id="NUT-004"></a>
## NUT-004

The Nutanix profile SHALL qualify the actual AOS/Prism/Flow/provider tuple and external-attachment behavior; unresolved licensing, routing, policy precedence or asynchronous realization limitations SHALL block the affected capability.

**Source role:** Platform engineering. **Original design references:** RA §16.

**Enforcement location:** Nutanix Prism/AOS/Flow native VPC, external attachment and mandatory category authority.

**Delivery disposition:** `PARTIAL_NATIVE_CANDIDATE_NOT_QUALIFIED`.

**Related code/procedure:** [terraform/modules/nutanix-domain/main.tf.json](../../terraform/modules/nutanix-domain/main.tf.json) · [terraform/modules/nutanix-route/main.tf.json](../../terraform/modules/nutanix-route/main.tf.json) · [tools/nutanix_observe.py](../../tools/nutanix_observe.py). These artifacts do not individually or collectively establish the entire requirement.

**Current evidence limit:** SOURCE_AND_LOCAL_FIXTURE_ONLY_OR_NOT_IMPLEMENTED; NOT_NATIVE_QUALIFIED. Actual native evidence is not supplied.

**Outstanding dependency:** Exact installed AOS/Prism/Flow/API/provider/entitlement and route/selector/asynchronous behaviour remain unqualified; selected resources do not prove a complete ZIP or protected category authority.

| Assertion | Exact source focus | Required site-specific completion |
| --- | --- | --- |
| NUT-004/A01 | The Nutanix profile SHALL qualify the actual AOS/Prism/Flow/provider tuple and external-attachment behavior | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |
| NUT-004/A02 | unresolved licensing, routing, policy precedence or asynchronous realization limitations SHALL block the affected capability. | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |

**Verification:** [CT-015](test-specifications.md#CT-015) · [CT-023](test-specifications.md#CT-023) · [CT-045](test-specifications.md#CT-045) · [CT-080](test-specifications.md#CT-080). Apply the referenced procedure to the actual enforcement location and this focus; include effective negative/failure observations where the original criterion requires them.

**Applicability and acceptance:** TO_BE_DECIDED_FOR_ACTUAL_SERVICE; NOT_AUTO_NA. The accountable project role records applicability, configuration and evidence; this reusable allocation does not invent those decisions.

<a id="NSX-001"></a>
## NSX-001

An NSX implementation SHALL keep tenant/project policy distinct from provider/global management and security policy.

**Source role:** Platform engineering. **Original design references:** RA §17.

**Enforcement location:** NSX manager/global-domain permissions, distributed and gateway rules, Tier-1/Tier-0/VRF and Edge forwarding.

**Delivery disposition:** `PARTIAL_NATIVE_CANDIDATE_NOT_QUALIFIED`.

**Related code/procedure:** [terraform/modules/nsx-domain/main.tf.json](../../terraform/modules/nsx-domain/main.tf.json) · [terraform/modules/nsx-gateway-quarantine/main.tf.json](../../terraform/modules/nsx-gateway-quarantine/main.tf.json) · [tools/nsx_observe.py](../../tools/nsx_observe.py). These artifacts do not individually or collectively establish the entire requirement.

**Current evidence limit:** SOURCE_AND_LOCAL_FIXTURE_ONLY_OR_NOT_IMPLEMENTED; NOT_NATIVE_QUALIFIED. Actual native evidence is not supplied.

**Outstanding dependency:** No complete Tier-0/VRF/Edge foundation or applicable global/tenant rule inventory is deployed; aggregate realization is not effective policy, same-host isolation or native HA evidence.

| Assertion | Exact source focus | Required site-specific completion |
| --- | --- | --- |
| NSX-001/A01 | An NSX implementation SHALL keep tenant/project policy distinct from provider/global management and security policy. | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |

**Verification:** [CT-019](test-specifications.md#CT-019) · [CT-020](test-specifications.md#CT-020) · [CT-066](test-specifications.md#CT-066). Apply the referenced procedure to the actual enforcement location and this focus; include effective negative/failure observations where the original criterion requires them.

**Applicability and acceptance:** TO_BE_DECIDED_FOR_ACTUAL_SERVICE; NOT_AUTO_NA. The accountable project role records applicability, configuration and evidence; this reusable allocation does not invent those decisions.

<a id="NSX-002"></a>
## NSX-002

Gateway policy used for zone transitions SHALL be generated from portable Flow/ZIP intent rather than manually duplicated per workload.

**Source role:** Platform engineering. **Original design references:** RA §17.

**Enforcement location:** NSX manager/global-domain permissions, distributed and gateway rules, Tier-1/Tier-0/VRF and Edge forwarding.

**Delivery disposition:** `PARTIAL_NATIVE_CANDIDATE_NOT_QUALIFIED`.

**Related code/procedure:** [terraform/modules/nsx-domain/main.tf.json](../../terraform/modules/nsx-domain/main.tf.json) · [terraform/modules/nsx-gateway-quarantine/main.tf.json](../../terraform/modules/nsx-gateway-quarantine/main.tf.json) · [tools/nsx_observe.py](../../tools/nsx_observe.py). These artifacts do not individually or collectively establish the entire requirement.

**Current evidence limit:** SOURCE_AND_LOCAL_FIXTURE_ONLY_OR_NOT_IMPLEMENTED; NOT_NATIVE_QUALIFIED. Actual native evidence is not supplied.

**Outstanding dependency:** No complete Tier-0/VRF/Edge foundation or applicable global/tenant rule inventory is deployed; aggregate realization is not effective policy, same-host isolation or native HA evidence.

| Assertion | Exact source focus | Required site-specific completion |
| --- | --- | --- |
| NSX-002/A01 | Gateway policy used for zone transitions SHALL be generated from portable Flow/ZIP intent rather than manually duplicated per workload. | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |

**Verification:** [CT-003](test-specifications.md#CT-003) · [CT-007](test-specifications.md#CT-007) · [CT-009](test-specifications.md#CT-009). Apply the referenced procedure to the actual enforcement location and this focus; include effective negative/failure observations where the original criterion requires them.

**Applicability and acceptance:** TO_BE_DECIDED_FOR_ACTUAL_SERVICE; NOT_AUTO_NA. The accountable project role records applicability, configuration and evidence; this reusable allocation does not invent those decisions.

<a id="NSX-003"></a>
## NSX-003

The NSX profile SHALL identify actual routing and enforcement components, global/project authority and policy precedence, and SHALL qualify their behavior on the selected product/provider tuple rather than equating a Tier-1 or project with a ZIP.

**Source role:** Platform engineering. **Original design references:** RA §17.

**Enforcement location:** NSX manager/global-domain permissions, distributed and gateway rules, Tier-1/Tier-0/VRF and Edge forwarding.

**Delivery disposition:** `PARTIAL_NATIVE_CANDIDATE_NOT_QUALIFIED`.

**Related code/procedure:** [terraform/modules/nsx-domain/main.tf.json](../../terraform/modules/nsx-domain/main.tf.json) · [terraform/modules/nsx-gateway-quarantine/main.tf.json](../../terraform/modules/nsx-gateway-quarantine/main.tf.json) · [tools/nsx_observe.py](../../tools/nsx_observe.py). These artifacts do not individually or collectively establish the entire requirement.

**Current evidence limit:** SOURCE_AND_LOCAL_FIXTURE_ONLY_OR_NOT_IMPLEMENTED; NOT_NATIVE_QUALIFIED. Actual native evidence is not supplied.

**Outstanding dependency:** No complete Tier-0/VRF/Edge foundation or applicable global/tenant rule inventory is deployed; aggregate realization is not effective policy, same-host isolation or native HA evidence.

| Assertion | Exact source focus | Required site-specific completion |
| --- | --- | --- |
| NSX-003/A01 | The NSX profile SHALL identify actual routing and enforcement components, global/project authority and policy precedence, and SHALL qualify their behavior on the selected product/provider tuple rather than equating a Tier-1 or project with a ZIP. | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |

**Verification:** [CT-003](test-specifications.md#CT-003) · [CT-015](test-specifications.md#CT-015) · [CT-024](test-specifications.md#CT-024) · [CT-080](test-specifications.md#CT-080). Apply the referenced procedure to the actual enforcement location and this focus; include effective negative/failure observations where the original criterion requires them.

**Applicability and acceptance:** TO_BE_DECIDED_FOR_ACTUAL_SERVICE; NOT_AUTO_NA. The accountable project role records applicability, configuration and evidence; this reusable allocation does not invent those decisions.

<a id="OS-001"></a>
## OS-001

Default OpenStack security-group behaviour SHALL be reviewed and normalized to the secure-by-default service baseline.

**Source role:** Platform engineering. **Original design references:** RA §18.

**Enforcement location:** OpenStack Keystone API policy, Neutron backend domain/router/ports and external-network authority.

**Delivery disposition:** `PARTIAL_NATIVE_CANDIDATE_NOT_QUALIFIED`.

**Related code/procedure:** [terraform/modules/openstack-domain/main.tf.json](../../terraform/modules/openstack-domain/main.tf.json) · [terraform/modules/openstack-workload/main.tf.json](../../terraform/modules/openstack-workload/main.tf.json) · [tools/neutron_observe.py](../../tools/neutron_observe.py). These artifacts do not individually or collectively establish the entire requirement.

**Current evidence limit:** SOURCE_AND_LOCAL_FIXTURE_ONLY_OR_NOT_IMPLEMENTED; NOT_NATIVE_QUALIFIED. Actual native evidence is not supplied.

**Outstanding dependency:** Disabled ports/router and empty-group source is not the actual delegated-role proof, backend qualification, supported distribution/extensions or full stateful ZIP implementation.

| Assertion | Exact source focus | Required site-specific completion |
| --- | --- | --- |
| OS-001/A01 | Default OpenStack security-group behaviour SHALL be reviewed and normalized to the secure-by-default service baseline. | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |

**Verification:** [CT-005](test-specifications.md#CT-005) · [CT-021](test-specifications.md#CT-021) · [CT-066](test-specifications.md#CT-066). Apply the referenced procedure to the actual enforcement location and this focus; include effective negative/failure observations where the original criterion requires them.

**Applicability and acceptance:** TO_BE_DECIDED_FOR_ACTUAL_SERVICE; NOT_AUTO_NA. The accountable project role records applicability, configuration and evidence; this reusable allocation does not invent those decisions.

<a id="OS-002"></a>
## OS-002

Provider networks and external-router capabilities SHALL remain provider controlled and SHALL not become unrestricted tenant escape paths.

**Source role:** Platform engineering. **Original design references:** RA §18.

**Enforcement location:** OpenStack Keystone API policy, Neutron backend domain/router/ports and external-network authority.

**Delivery disposition:** `PARTIAL_NATIVE_CANDIDATE_NOT_QUALIFIED`.

**Related code/procedure:** [terraform/modules/openstack-domain/main.tf.json](../../terraform/modules/openstack-domain/main.tf.json) · [terraform/modules/openstack-workload/main.tf.json](../../terraform/modules/openstack-workload/main.tf.json) · [tools/neutron_observe.py](../../tools/neutron_observe.py). These artifacts do not individually or collectively establish the entire requirement.

**Current evidence limit:** SOURCE_AND_LOCAL_FIXTURE_ONLY_OR_NOT_IMPLEMENTED; NOT_NATIVE_QUALIFIED. Actual native evidence is not supplied.

**Outstanding dependency:** Disabled ports/router and empty-group source is not the actual delegated-role proof, backend qualification, supported distribution/extensions or full stateful ZIP implementation.

| Assertion | Exact source focus | Required site-specific completion |
| --- | --- | --- |
| OS-002/A01 | Provider networks and external-router capabilities SHALL remain provider controlled and SHALL not become unrestricted tenant escape paths. | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |

**Verification:** [CT-019](test-specifications.md#CT-019) · [CT-022](test-specifications.md#CT-022) · [CT-023](test-specifications.md#CT-023). Apply the referenced procedure to the actual enforcement location and this focus; include effective negative/failure observations where the original criterion requires them.

**Applicability and acceptance:** TO_BE_DECIDED_FOR_ACTUAL_SERVICE; NOT_AUTO_NA. The accountable project role records applicability, configuration and evidence; this reusable allocation does not invent those decisions.

<a id="OS-003"></a>
## OS-003

The OpenStack profile SHALL record distribution, service/API versions, Neutron backend/extensions and provider authority over external/port-security operations; native routing or editable security groups SHALL NOT be assumed to satisfy all ZIP functions.

**Source role:** Platform engineering. **Original design references:** RA §18.

**Enforcement location:** OpenStack Keystone API policy, Neutron backend domain/router/ports and external-network authority.

**Delivery disposition:** `PARTIAL_NATIVE_CANDIDATE_NOT_QUALIFIED`.

**Related code/procedure:** [terraform/modules/openstack-domain/main.tf.json](../../terraform/modules/openstack-domain/main.tf.json) · [terraform/modules/openstack-workload/main.tf.json](../../terraform/modules/openstack-workload/main.tf.json) · [tools/neutron_observe.py](../../tools/neutron_observe.py). These artifacts do not individually or collectively establish the entire requirement.

**Current evidence limit:** SOURCE_AND_LOCAL_FIXTURE_ONLY_OR_NOT_IMPLEMENTED; NOT_NATIVE_QUALIFIED. Actual native evidence is not supplied.

**Outstanding dependency:** Disabled ports/router and empty-group source is not the actual delegated-role proof, backend qualification, supported distribution/extensions or full stateful ZIP implementation.

| Assertion | Exact source focus | Required site-specific completion |
| --- | --- | --- |
| OS-003/A01 | The OpenStack profile SHALL record distribution, service/API versions, Neutron backend/extensions and provider authority over external/port-security operations | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |
| OS-003/A02 | native routing or editable security groups SHALL NOT be assumed to satisfy all ZIP functions. | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |

**Verification:** [CT-015](test-specifications.md#CT-015) · [CT-018](test-specifications.md#CT-018) · [CT-022](test-specifications.md#CT-022) · [CT-080](test-specifications.md#CT-080). Apply the referenced procedure to the actual enforcement location and this focus; include effective negative/failure observations where the original criterion requires them.

**Applicability and acceptance:** TO_BE_DECIDED_FOR_ACTUAL_SERVICE; NOT_AUTO_NA. The accountable project role records applicability, configuration and evidence; this reusable allocation does not invent those decisions.

<a id="FUT-001"></a>
## FUT-001

A new platform SHALL pass the applicable conformance suite before it is approved for production placement.

**Source role:** Platform engineering. **Original design references:** RA §19.

**Enforcement location:** Qualified platform capability/eligibility record and representative native service/exit campaigns.

**Delivery disposition:** `DOCUMENTED_QUALIFICATION_NOT_EXECUTED`.

**Related code/procedure:** [docs/assurance/test-specifications.md](test-specifications.md) · [sources/implementation_backlog.csv](../../sources/implementation_backlog.csv). These artifacts do not individually or collectively establish the entire requirement.

**Current evidence limit:** SOURCE_AND_LOCAL_FIXTURE_ONLY_OR_NOT_IMPLEMENTED; NOT_NATIVE_QUALIFIED. Actual native evidence is not supplied.

**Outstanding dependency:** No active authoritative qualified-platform record, bare-metal/container implementation or complete first/second-platform and exit evidence is supplied; unsupported capability must stay ineligible.

| Assertion | Exact source focus | Required site-specific completion |
| --- | --- | --- |
| FUT-001/A01 | A new platform SHALL pass the applicable conformance suite before it is approved for production placement. | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |

**Verification:** [CT-015](test-specifications.md#CT-015) · [CT-018](test-specifications.md#CT-018) · [CT-065](test-specifications.md#CT-065) · [CT-080](test-specifications.md#CT-080). Apply the referenced procedure to the actual enforcement location and this focus; include effective negative/failure observations where the original criterion requires them.

**Applicability and acceptance:** TO_BE_DECIDED_FOR_ACTUAL_SERVICE; NOT_AUTO_NA. The accountable project role records applicability, configuration and evidence; this reusable allocation does not invent those decisions.

<a id="FUT-002"></a>
## FUT-002

A platform SHALL declare unsupported capabilities explicitly; unsupported capabilities SHALL NOT be emulated by weakening a mandatory control.

**Source role:** Platform engineering. **Original design references:** RA §19.

**Enforcement location:** Qualified platform capability/eligibility record and representative native service/exit campaigns.

**Delivery disposition:** `DOCUMENTED_QUALIFICATION_NOT_EXECUTED`.

**Related code/procedure:** [docs/assurance/test-specifications.md](test-specifications.md) · [sources/implementation_backlog.csv](../../sources/implementation_backlog.csv). These artifacts do not individually or collectively establish the entire requirement.

**Current evidence limit:** SOURCE_AND_LOCAL_FIXTURE_ONLY_OR_NOT_IMPLEMENTED; NOT_NATIVE_QUALIFIED. Actual native evidence is not supplied.

**Outstanding dependency:** No active authoritative qualified-platform record, bare-metal/container implementation or complete first/second-platform and exit evidence is supplied; unsupported capability must stay ineligible.

| Assertion | Exact source focus | Required site-specific completion |
| --- | --- | --- |
| FUT-002/A01 | A platform SHALL declare unsupported capabilities explicitly | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |
| FUT-002/A02 | unsupported capabilities SHALL NOT be emulated by weakening a mandatory control. | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |

**Verification:** [CT-018](test-specifications.md#CT-018) · [CT-065](test-specifications.md#CT-065). Apply the referenced procedure to the actual enforcement location and this focus; include effective negative/failure observations where the original criterion requires them.

**Applicability and acceptance:** TO_BE_DECIDED_FOR_ACTUAL_SERVICE; NOT_AUTO_NA. The accountable project role records applicability, configuration and evidence; this reusable allocation does not invent those decisions.

<a id="FUT-003"></a>
## FUT-003

Bare-metal and container profiles SHALL explicitly qualify host/control-plane, network, storage and lifecycle isolation; namespaces, projects and physical VRFs SHALL NOT alone be accepted as evidence of a complete security boundary.

**Source role:** Platform engineering. **Original design references:** RA §19.

**Enforcement location:** Qualified platform capability/eligibility record and representative native service/exit campaigns.

**Delivery disposition:** `DOCUMENTED_QUALIFICATION_NOT_EXECUTED`.

**Related code/procedure:** [docs/assurance/test-specifications.md](test-specifications.md) · [sources/implementation_backlog.csv](../../sources/implementation_backlog.csv). These artifacts do not individually or collectively establish the entire requirement.

**Current evidence limit:** SOURCE_AND_LOCAL_FIXTURE_ONLY_OR_NOT_IMPLEMENTED; NOT_NATIVE_QUALIFIED. Actual native evidence is not supplied.

**Outstanding dependency:** No active authoritative qualified-platform record, bare-metal/container implementation or complete first/second-platform and exit evidence is supplied; unsupported capability must stay ineligible.

| Assertion | Exact source focus | Required site-specific completion |
| --- | --- | --- |
| FUT-003/A01 | Bare-metal and container profiles SHALL explicitly qualify host/control-plane, network, storage and lifecycle isolation | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |
| FUT-003/A02 | namespaces, projects and physical VRFs SHALL NOT alone be accepted as evidence of a complete security boundary. | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |

**Verification:** [CT-035](test-specifications.md#CT-035) · [CT-037](test-specifications.md#CT-037) · [CT-059](test-specifications.md#CT-059) · [CT-065](test-specifications.md#CT-065) · [CT-072](test-specifications.md#CT-072). Apply the referenced procedure to the actual enforcement location and this focus; include effective negative/failure observations where the original criterion requires them.

**Applicability and acceptance:** TO_BE_DECIDED_FOR_ACTUAL_SERVICE; NOT_AUTO_NA. The accountable project role records applicability, configuration and evidence; this reusable allocation does not invent those decisions.

<a id="API-001"></a>
## API-001

The portable API SHALL be versioned and backward-compatibility rules SHALL be published.

**Source role:** Automation platform. **Original design references:** RA §23; RA §24.

**Enforcement location:** Existing authorized service interface and scoped execution workflow before native side effects; native plan/readback layer.

**Delivery disposition:** `PARTIAL_OFFLINE_AND_SERVICE_CLIENT_CHECKS`.

**Related code/procedure:** [tools/input_review.py](../../tools/input_review.py) · [tools/plan_review.py](../../tools/plan_review.py) · [tools/dns_change.py](../../tools/dns_change.py) · [tools/recovery_review.py](../../tools/recovery_review.py). These artifacts do not individually or collectively establish the entire requirement.

**Current evidence limit:** SOURCE_AND_LOCAL_FIXTURE_ONLY_OR_NOT_IMPLEMENTED; NOT_NATIVE_QUALIFIED. Actual native evidence is not supplied.

**Outstanding dependency:** These independent tools do not implement a complete catalogue/API, authoritative immutable status, quota/reservation, admission workflow or actual writer fencing. No bespoke controller is assumed necessary; an accepted existing interface can own those controls.

| Assertion | Exact source focus | Required site-specific completion |
| --- | --- | --- |
| API-001/A01 | The portable API SHALL be versioned and backward-compatibility rules SHALL be published. | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |

**Verification:** [CT-016](test-specifications.md#CT-016) · [CT-070](test-specifications.md#CT-070). Apply the referenced procedure to the actual enforcement location and this focus; include effective negative/failure observations where the original criterion requires them.

**Applicability and acceptance:** TO_BE_DECIDED_FOR_ACTUAL_SERVICE; NOT_AUTO_NA. The accountable project role records applicability, configuration and evidence; this reusable allocation does not invent those decisions.

<a id="API-002"></a>
## API-002

Vendor identifiers, VLAN/VNI/VRF details, route targets, raw firewall rules and raw next-hop routes SHALL NOT be part of the normal consumer contract.

**Source role:** Automation platform. **Original design references:** RA §23; RA §24.

**Enforcement location:** Existing authorized service interface and scoped execution workflow before native side effects; native plan/readback layer.

**Delivery disposition:** `PARTIAL_OFFLINE_AND_SERVICE_CLIENT_CHECKS`.

**Related code/procedure:** [tools/input_review.py](../../tools/input_review.py) · [tools/plan_review.py](../../tools/plan_review.py) · [tools/dns_change.py](../../tools/dns_change.py) · [tools/recovery_review.py](../../tools/recovery_review.py). These artifacts do not individually or collectively establish the entire requirement.

**Current evidence limit:** SOURCE_AND_LOCAL_FIXTURE_ONLY_OR_NOT_IMPLEMENTED; NOT_NATIVE_QUALIFIED. Actual native evidence is not supplied.

**Outstanding dependency:** These independent tools do not implement a complete catalogue/API, authoritative immutable status, quota/reservation, admission workflow or actual writer fencing. No bespoke controller is assumed necessary; an accepted existing interface can own those controls.

| Assertion | Exact source focus | Required site-specific completion |
| --- | --- | --- |
| API-002/A01 | Vendor identifiers, VLAN/VNI/VRF details, route targets, raw firewall rules and raw next-hop routes SHALL NOT be part of the normal consumer contract. | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |

**Verification:** [CT-017](test-specifications.md#CT-017) · [CT-019](test-specifications.md#CT-019). Apply the referenced procedure to the actual enforcement location and this focus; include effective negative/failure observations where the original criterion requires them.

**Applicability and acceptance:** TO_BE_DECIDED_FOR_ACTUAL_SERVICE; NOT_AUTO_NA. The accountable project role records applicability, configuration and evidence; this reusable allocation does not invent those decisions.

<a id="API-003"></a>
## API-003

Where a consumer-facing provisioning API is provided, it SHALL enforce immutable IDs, idempotent create, optimistic concurrency, typed/closed schemas, authorized references and authoritative service-owned status; stale or unauthorized updates SHALL fail before side effects. These controls MAY be implemented by an existing qualified service interface.

**Source role:** Automation platform. **Original design references:** RA §23; RA §24.

**Enforcement location:** Existing authorized service interface and scoped execution workflow before native side effects; native plan/readback layer.

**Delivery disposition:** `PARTIAL_OFFLINE_AND_SERVICE_CLIENT_CHECKS`.

**Related code/procedure:** [tools/input_review.py](../../tools/input_review.py) · [tools/plan_review.py](../../tools/plan_review.py) · [tools/dns_change.py](../../tools/dns_change.py) · [tools/recovery_review.py](../../tools/recovery_review.py). These artifacts do not individually or collectively establish the entire requirement.

**Current evidence limit:** SOURCE_AND_LOCAL_FIXTURE_ONLY_OR_NOT_IMPLEMENTED; NOT_NATIVE_QUALIFIED. Actual native evidence is not supplied.

**Outstanding dependency:** These independent tools do not implement a complete catalogue/API, authoritative immutable status, quota/reservation, admission workflow or actual writer fencing. No bespoke controller is assumed necessary; an accepted existing interface can own those controls.

| Assertion | Exact source focus | Required site-specific completion |
| --- | --- | --- |
| API-003/A01 | immutable IDs | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |
| API-003/A02 | idempotent create | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |
| API-003/A03 | optimistic concurrency | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |
| API-003/A04 | typed/closed schemas | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |
| API-003/A05 | authorized references | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |
| API-003/A06 | authoritative service-owned status | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |

**Verification:** [CT-017](test-specifications.md#CT-017) · [CT-046](test-specifications.md#CT-046) · [CT-070](test-specifications.md#CT-070). Apply the referenced procedure to the actual enforcement location and this focus; include effective negative/failure observations where the original criterion requires them.

**Applicability and acceptance:** TO_BE_DECIDED_FOR_ACTUAL_SERVICE; NOT_AUTO_NA. The accountable project role records applicability, configuration and evidence; this reusable allocation does not invent those decisions.

<a id="POL-001"></a>
## POL-001

Admission policy SHALL be provider independent wherever the rule expresses an architectural invariant.

**Source role:** Automation platform. **Original design references:** RA §20; RA §23.

**Enforcement location:** Existing authorized service interface and scoped execution workflow before native side effects; native plan/readback layer.

**Delivery disposition:** `PARTIAL_OFFLINE_AND_SERVICE_CLIENT_CHECKS`.

**Related code/procedure:** [tools/input_review.py](../../tools/input_review.py) · [tools/plan_review.py](../../tools/plan_review.py) · [tools/dns_change.py](../../tools/dns_change.py) · [tools/recovery_review.py](../../tools/recovery_review.py). These artifacts do not individually or collectively establish the entire requirement.

**Current evidence limit:** SOURCE_AND_LOCAL_FIXTURE_ONLY_OR_NOT_IMPLEMENTED; NOT_NATIVE_QUALIFIED. Actual native evidence is not supplied.

**Outstanding dependency:** These independent tools do not implement a complete catalogue/API, authoritative immutable status, quota/reservation, admission workflow or actual writer fencing. No bespoke controller is assumed necessary; an accepted existing interface can own those controls.

| Assertion | Exact source focus | Required site-specific completion |
| --- | --- | --- |
| POL-001/A01 | Admission policy SHALL be provider independent wherever the rule expresses an architectural invariant. | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |

**Verification:** [CT-017](test-specifications.md#CT-017) · [CT-025](test-specifications.md#CT-025) · [CT-066](test-specifications.md#CT-066). Apply the referenced procedure to the actual enforcement location and this focus; include effective negative/failure observations where the original criterion requires them.

**Applicability and acceptance:** TO_BE_DECIDED_FOR_ACTUAL_SERVICE; NOT_AUTO_NA. The accountable project role records applicability, configuration and evidence; this reusable allocation does not invent those decisions.

<a id="POL-002"></a>
## POL-002

Provider-specific plan checks SHOULD validate that the adapter compiled the intent into the expected native constructs.

**Source role:** Automation platform. **Original design references:** RA §20; RA §23.

**Enforcement location:** Existing authorized service interface and scoped execution workflow before native side effects; native plan/readback layer.

**Delivery disposition:** `PARTIAL_OFFLINE_AND_SERVICE_CLIENT_CHECKS`.

**Related code/procedure:** [tools/input_review.py](../../tools/input_review.py) · [tools/plan_review.py](../../tools/plan_review.py) · [tools/dns_change.py](../../tools/dns_change.py) · [tools/recovery_review.py](../../tools/recovery_review.py). These artifacts do not individually or collectively establish the entire requirement.

**Current evidence limit:** SOURCE_AND_LOCAL_FIXTURE_ONLY_OR_NOT_IMPLEMENTED; NOT_NATIVE_QUALIFIED. Actual native evidence is not supplied.

**Outstanding dependency:** These independent tools do not implement a complete catalogue/API, authoritative immutable status, quota/reservation, admission workflow or actual writer fencing. No bespoke controller is assumed necessary; an accepted existing interface can own those controls.

| Assertion | Exact source focus | Required site-specific completion |
| --- | --- | --- |
| POL-002/A01 | Provider-specific plan checks SHOULD validate that the adapter compiled the intent into the expected native constructs. | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |

**Verification:** [CT-009](test-specifications.md#CT-009) · [CT-048](test-specifications.md#CT-048) · [CT-066](test-specifications.md#CT-066). Apply the referenced procedure to the actual enforcement location and this focus; include effective negative/failure observations where the original criterion requires them.

**Applicability and acceptance:** TO_BE_DECIDED_FOR_ACTUAL_SERVICE; NOT_AUTO_NA. The accountable project role records applicability, configuration and evidence; this reusable allocation does not invent those decisions.

<a id="FLOW-001"></a>
## FLOW-001

Flow Intentions SHALL resolve explicit identities, service/profile version, initiation direction, lifetime, purpose and logging; compilation SHALL preserve mandatory policy precedence and enforce approved session-revocation behavior.

**Source role:** Security-edge operations. **Original design references:** RA §20; RA §23.

**Enforcement location:** Authorized route/flow design plus native RIB/FIB, edge session policy and lifecycle writer.

**Delivery disposition:** `PARTIAL_CANDIDATE_NATIVE_SOURCE`.

**Related code/procedure:** [tools/route_audit.py](../../tools/route_audit.py) · [tools/route_record_review.py](../../tools/route_record_review.py) · [terraform/modules/nsx-route/main.tf.json](../../terraform/modules/nsx-route/main.tf.json) · [terraform/modules/nutanix-route/main.tf.json](../../terraform/modules/nutanix-route/main.tf.json) · [terraform/modules/openstack-route/main.tf.json](../../terraform/modules/openstack-route/main.tf.json). These artifacts do not individually or collectively establish the entire requirement.

**Current evidence limit:** SOURCE_AND_LOCAL_FIXTURE_ONLY_OR_NOT_IMPLEMENTED; NOT_NATIVE_QUALIFIED. Actual native evidence is not supplied.

**Outstanding dependency:** Route models and exact native static-route resources do not implement a complete route authority, full flow compiler, expiration/teardown service, BGP ownership or effective NAT/PBR/session-revocation policy.

| Assertion | Exact source focus | Required site-specific completion |
| --- | --- | --- |
| FLOW-001/A01 | Flow Intentions SHALL resolve explicit identities, service/profile version, initiation direction, lifetime, purpose and logging | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |
| FLOW-001/A02 | compilation SHALL preserve mandatory policy precedence and enforce approved session-revocation behavior. | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |

**Verification:** [CT-007](test-specifications.md#CT-007) · [CT-020](test-specifications.md#CT-020) · [CT-066](test-specifications.md#CT-066) · [CT-077](test-specifications.md#CT-077). Apply the referenced procedure to the actual enforcement location and this focus; include effective negative/failure observations where the original criterion requires them.

**Applicability and acceptance:** TO_BE_DECIDED_FOR_ACTUAL_SERVICE; NOT_AUTO_NA. The accountable project role records applicability, configuration and evidence; this reusable allocation does not invent those decisions.

<a id="AUTO-001"></a>
## AUTO-001

If security admission, IPAM, route authority, or mandatory policy validation is unavailable, new provisioning SHALL stop rather than inventing or bypassing required state.

**Source role:** Automation platform. **Original design references:** RA §23; RA §24.

**Enforcement location:** Existing authorized service interface and scoped execution workflow before native side effects; native plan/readback layer.

**Delivery disposition:** `PARTIAL_OFFLINE_AND_SERVICE_CLIENT_CHECKS`.

**Related code/procedure:** [tools/input_review.py](../../tools/input_review.py) · [tools/plan_review.py](../../tools/plan_review.py) · [tools/dns_change.py](../../tools/dns_change.py) · [tools/recovery_review.py](../../tools/recovery_review.py). These artifacts do not individually or collectively establish the entire requirement.

**Current evidence limit:** SOURCE_AND_LOCAL_FIXTURE_ONLY_OR_NOT_IMPLEMENTED; NOT_NATIVE_QUALIFIED. Actual native evidence is not supplied.

**Outstanding dependency:** These independent tools do not implement a complete catalogue/API, authoritative immutable status, quota/reservation, admission workflow or actual writer fencing. No bespoke controller is assumed necessary; an accepted existing interface can own those controls.

| Assertion | Exact source focus | Required site-specific completion |
| --- | --- | --- |
| AUTO-001/A01 | If security admission, IPAM, route authority, or mandatory policy validation is unavailable, new provisioning SHALL stop rather than inventing or bypassing required state. | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |

**Verification:** [CT-011](test-specifications.md#CT-011) · [CT-029](test-specifications.md#CT-029) · [CT-045](test-specifications.md#CT-045). Apply the referenced procedure to the actual enforcement location and this focus; include effective negative/failure observations where the original criterion requires them.

**Applicability and acceptance:** TO_BE_DECIDED_FOR_ACTUAL_SERVICE; NOT_AUTO_NA. The accountable project role records applicability, configuration and evidence; this reusable allocation does not invent those decisions.

<a id="AUTO-002"></a>
## AUTO-002

Provisioning SHALL be journaled and idempotent, reserve only eligible capacity/addresses, enforce deny before attachment/exposure, and gate activation on realized current-generation evidence and authorization.

**Source role:** Automation platform. **Original design references:** RA §23; RA §24.

**Enforcement location:** Existing authorized service interface and scoped execution workflow before native side effects; native plan/readback layer.

**Delivery disposition:** `PARTIAL_OFFLINE_AND_SERVICE_CLIENT_CHECKS`.

**Related code/procedure:** [tools/input_review.py](../../tools/input_review.py) · [tools/plan_review.py](../../tools/plan_review.py) · [tools/dns_change.py](../../tools/dns_change.py) · [tools/recovery_review.py](../../tools/recovery_review.py). These artifacts do not individually or collectively establish the entire requirement.

**Current evidence limit:** SOURCE_AND_LOCAL_FIXTURE_ONLY_OR_NOT_IMPLEMENTED; NOT_NATIVE_QUALIFIED. Actual native evidence is not supplied.

**Outstanding dependency:** These independent tools do not implement a complete catalogue/API, authoritative immutable status, quota/reservation, admission workflow or actual writer fencing. No bespoke controller is assumed necessary; an accepted existing interface can own those controls.

| Assertion | Exact source focus | Required site-specific completion |
| --- | --- | --- |
| AUTO-002/A01 | journaled | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |
| AUTO-002/A02 | idempotent | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |
| AUTO-002/A03 | eligible capacity/addresses | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |
| AUTO-002/A04 | deny before attachment/exposure | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |
| AUTO-002/A05 | current-generation evidence | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |
| AUTO-002/A06 | authorization | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |

**Verification:** [CT-045](test-specifications.md#CT-045) · [CT-046](test-specifications.md#CT-046) · [CT-048](test-specifications.md#CT-048) · [CT-069](test-specifications.md#CT-069). Apply the referenced procedure to the actual enforcement location and this focus; include effective negative/failure observations where the original criterion requires them.

**Applicability and acceptance:** TO_BE_DECIDED_FOR_ACTUAL_SERVICE; NOT_AUTO_NA. The accountable project role records applicability, configuration and evidence; this reusable allocation does not invent those decisions.

<a id="AUTO-003"></a>
## AUTO-003

Retries SHALL distinguish transient, permanent and conflict failures, use bounded backoff/deadlines and preserve resource identity; uncertain outcomes SHALL be discovered and reconciled rather than duplicated.

**Source role:** Automation platform. **Original design references:** RA §23; RA §24.

**Enforcement location:** Existing authorized service interface and scoped execution workflow before native side effects; native plan/readback layer.

**Delivery disposition:** `PARTIAL_OFFLINE_AND_SERVICE_CLIENT_CHECKS`.

**Related code/procedure:** [tools/input_review.py](../../tools/input_review.py) · [tools/plan_review.py](../../tools/plan_review.py) · [tools/dns_change.py](../../tools/dns_change.py) · [tools/recovery_review.py](../../tools/recovery_review.py). These artifacts do not individually or collectively establish the entire requirement.

**Current evidence limit:** SOURCE_AND_LOCAL_FIXTURE_ONLY_OR_NOT_IMPLEMENTED; NOT_NATIVE_QUALIFIED. Actual native evidence is not supplied.

**Outstanding dependency:** These independent tools do not implement a complete catalogue/API, authoritative immutable status, quota/reservation, admission workflow or actual writer fencing. No bespoke controller is assumed necessary; an accepted existing interface can own those controls.

| Assertion | Exact source focus | Required site-specific completion |
| --- | --- | --- |
| AUTO-003/A01 | Retries SHALL distinguish transient, permanent and conflict failures, use bounded backoff/deadlines and preserve resource identity | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |
| AUTO-003/A02 | uncertain outcomes SHALL be discovered and reconciled rather than duplicated. | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |

**Verification:** [CT-045](test-specifications.md#CT-045) · [CT-046](test-specifications.md#CT-046) · [CT-047](test-specifications.md#CT-047). Apply the referenced procedure to the actual enforcement location and this focus; include effective negative/failure observations where the original criterion requires them.

**Applicability and acceptance:** TO_BE_DECIDED_FOR_ACTUAL_SERVICE; NOT_AUTO_NA. The accountable project role records applicability, configuration and evidence; this reusable allocation does not invent those decisions.

<a id="TF-001"></a>
## TF-001

Provider configuration SHALL be defined in root modules and passed to child modules; reusable child modules SHOULD NOT embed provider credentials/configuration.

**Source role:** Automation platform. **Original design references:** RA §24.

**Enforcement location:** Terraform root/module source, plugin selection/locks and scoped backend use.

**Delivery disposition:** `CANDIDATE_CODE_ENGINE_GATE_REQUIRED`.

**Related code/procedure:** [tools/verify_terraform.py](../../tools/verify_terraform.py) · [terraform/modules/nsx-domain/main.tf.json](../../terraform/modules/nsx-domain/main.tf.json) · [terraform/roots/nsx-domain/main.tf.json](../../terraform/roots/nsx-domain/main.tf.json). These artifacts do not individually or collectively establish the entire requirement.

**Current evidence limit:** SOURCE_AND_LOCAL_FIXTURE_ONLY_OR_NOT_IMPLEMENTED; NOT_NATIVE_QUALIFIED. Actual native evidence is not supplied.

**Outstanding dependency:** Source pattern and mocked plans do not prove native capabilities. Actual engine validation and reviewed dependency locks are required; credentials, modules/images and state backend have distinct trust boundaries.

| Assertion | Exact source focus | Required site-specific completion |
| --- | --- | --- |
| TF-001/A01 | Provider configuration SHALL be defined in root modules and passed to child modules | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |
| TF-001/A02 | reusable child modules SHOULD NOT embed provider credentials/configuration. | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |

**Verification:** [CT-042](test-specifications.md#CT-042) · [CT-043](test-specifications.md#CT-043). Apply the referenced procedure to the actual enforcement location and this focus; include effective negative/failure observations where the original criterion requires them.

**Applicability and acceptance:** TO_BE_DECIDED_FOR_ACTUAL_SERVICE; NOT_AUTO_NA. The accountable project role records applicability, configuration and evidence; this reusable allocation does not invent those decisions.

<a id="TF-002"></a>
## TF-002

Provider versions SHALL be constrained and dependency lock files SHALL be committed and reviewed.

**Source role:** Automation platform. **Original design references:** RA §24.

**Enforcement location:** Terraform root/module source, plugin selection/locks and scoped backend use.

**Delivery disposition:** `CANDIDATE_CODE_ENGINE_GATE_REQUIRED`.

**Related code/procedure:** [tools/verify_terraform.py](../../tools/verify_terraform.py) · [terraform/modules/nsx-domain/main.tf.json](../../terraform/modules/nsx-domain/main.tf.json) · [terraform/roots/nsx-domain/main.tf.json](../../terraform/roots/nsx-domain/main.tf.json). These artifacts do not individually or collectively establish the entire requirement.

**Current evidence limit:** SOURCE_AND_LOCAL_FIXTURE_ONLY_OR_NOT_IMPLEMENTED; NOT_NATIVE_QUALIFIED. Actual native evidence is not supplied.

**Outstanding dependency:** Source pattern and mocked plans do not prove native capabilities. Actual engine validation and reviewed dependency locks are required; credentials, modules/images and state backend have distinct trust boundaries.

| Assertion | Exact source focus | Required site-specific completion |
| --- | --- | --- |
| TF-002/A01 | Provider versions SHALL be constrained and dependency lock files SHALL be committed and reviewed. | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |

**Verification:** [CT-015](test-specifications.md#CT-015) · [CT-042](test-specifications.md#CT-042) · [CT-048](test-specifications.md#CT-048). Apply the referenced procedure to the actual enforcement location and this focus; include effective negative/failure observations where the original criterion requires them.

**Applicability and acceptance:** TO_BE_DECIDED_FOR_ACTUAL_SERVICE; NOT_AUTO_NA. The accountable project role records applicability, configuration and evidence; this reusable allocation does not invent those decisions.

<a id="TF-003"></a>
## TF-003

The provisioning workflow SHALL select the required hosting-platform and shared-service adapters before execution; adapters SHALL preserve their authority and lifecycle boundaries. A single giant conditional module SHOULD NOT attempt to implement all platforms.

**Source role:** Automation platform. **Original design references:** RA §24.

**Enforcement location:** Terraform root/module source, plugin selection/locks and scoped backend use.

**Delivery disposition:** `CANDIDATE_CODE_ENGINE_GATE_REQUIRED`.

**Related code/procedure:** [tools/verify_terraform.py](../../tools/verify_terraform.py) · [terraform/modules/nsx-domain/main.tf.json](../../terraform/modules/nsx-domain/main.tf.json) · [terraform/roots/nsx-domain/main.tf.json](../../terraform/roots/nsx-domain/main.tf.json). These artifacts do not individually or collectively establish the entire requirement.

**Current evidence limit:** SOURCE_AND_LOCAL_FIXTURE_ONLY_OR_NOT_IMPLEMENTED; NOT_NATIVE_QUALIFIED. Actual native evidence is not supplied.

**Outstanding dependency:** Source pattern and mocked plans do not prove native capabilities. Actual engine validation and reviewed dependency locks are required; credentials, modules/images and state backend have distinct trust boundaries.

| Assertion | Exact source focus | Required site-specific completion |
| --- | --- | --- |
| TF-003/A01 | The provisioning workflow SHALL select the required hosting-platform and shared-service adapters before execution | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |
| TF-003/A02 | adapters SHALL preserve their authority and lifecycle boundaries. A single giant conditional module SHOULD NOT attempt to implement all platforms. | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |

**Verification:** [CT-016](test-specifications.md#CT-016) · [CT-044](test-specifications.md#CT-044). Apply the referenced procedure to the actual enforcement location and this focus; include effective negative/failure observations where the original criterion requires them.

**Applicability and acceptance:** TO_BE_DECIDED_FOR_ACTUAL_SERVICE; NOT_AUTO_NA. The accountable project role records applicability, configuration and evidence; this reusable allocation does not invent those decisions.

<a id="TF-004"></a>
## TF-004

Module interfaces SHOULD be relatively flat and composable; deeply nested modules that obscure lifecycle or ownership boundaries SHOULD be avoided.

**Source role:** Automation platform. **Original design references:** RA §24.

**Enforcement location:** Terraform root/module source, plugin selection/locks and scoped backend use.

**Delivery disposition:** `CANDIDATE_CODE_ENGINE_GATE_REQUIRED`.

**Related code/procedure:** [tools/verify_terraform.py](../../tools/verify_terraform.py) · [terraform/modules/nsx-domain/main.tf.json](../../terraform/modules/nsx-domain/main.tf.json) · [terraform/roots/nsx-domain/main.tf.json](../../terraform/roots/nsx-domain/main.tf.json). These artifacts do not individually or collectively establish the entire requirement.

**Current evidence limit:** SOURCE_AND_LOCAL_FIXTURE_ONLY_OR_NOT_IMPLEMENTED; NOT_NATIVE_QUALIFIED. Actual native evidence is not supplied.

**Outstanding dependency:** Source pattern and mocked plans do not prove native capabilities. Actual engine validation and reviewed dependency locks are required; credentials, modules/images and state backend have distinct trust boundaries.

| Assertion | Exact source focus | Required site-specific completion |
| --- | --- | --- |
| TF-004/A01 | Module interfaces SHOULD be relatively flat and composable | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |
| TF-004/A02 | deeply nested modules that obscure lifecycle or ownership boundaries SHOULD be avoided. | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |

**Verification:** [CT-044](test-specifications.md#CT-044) · [CT-070](test-specifications.md#CT-070). Apply the referenced procedure to the actual enforcement location and this focus; include effective negative/failure observations where the original criterion requires them.

**Applicability and acceptance:** TO_BE_DECIDED_FOR_ACTUAL_SERVICE; NOT_AUTO_NA. The accountable project role records applicability, configuration and evidence; this reusable allocation does not invent those decisions.

<a id="TF-005"></a>
## TF-005

Remote module sources and runner images SHALL be pinned to immutable versions/digests separately from provider lockfiles; approved package checksums and provenance SHALL be verified before privileged execution.

**Source role:** Automation platform. **Original design references:** RA §24.

**Enforcement location:** Terraform root/module source, plugin selection/locks and scoped backend use.

**Delivery disposition:** `CANDIDATE_CODE_ENGINE_GATE_REQUIRED`.

**Related code/procedure:** [tools/verify_terraform.py](../../tools/verify_terraform.py) · [terraform/modules/nsx-domain/main.tf.json](../../terraform/modules/nsx-domain/main.tf.json) · [terraform/roots/nsx-domain/main.tf.json](../../terraform/roots/nsx-domain/main.tf.json). These artifacts do not individually or collectively establish the entire requirement.

**Current evidence limit:** SOURCE_AND_LOCAL_FIXTURE_ONLY_OR_NOT_IMPLEMENTED; NOT_NATIVE_QUALIFIED. Actual native evidence is not supplied.

**Outstanding dependency:** Source pattern and mocked plans do not prove native capabilities. Actual engine validation and reviewed dependency locks are required; credentials, modules/images and state backend have distinct trust boundaries.

| Assertion | Exact source focus | Required site-specific completion |
| --- | --- | --- |
| TF-005/A01 | Remote module sources and runner images SHALL be pinned to immutable versions/digests separately from provider lockfiles | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |
| TF-005/A02 | approved package checksums and provenance SHALL be verified before privileged execution. | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |

**Verification:** [CT-042](test-specifications.md#CT-042) · [CT-048](test-specifications.md#CT-048). Apply the referenced procedure to the actual enforcement location and this focus; include effective negative/failure observations where the original criterion requires them.

**Applicability and acceptance:** TO_BE_DECIDED_FOR_ACTUAL_SERVICE; NOT_AUTO_NA. The accountable project role records applicability, configuration and evidence; this reusable allocation does not invent those decisions.

<a id="STATE-001"></a>
## STATE-001

No single routine tenant automation identity SHALL have authority to modify physical fabric, management foundation, security edge, and tenant workloads simultaneously.

**Source role:** Automation platform. **Original design references:** RA §24.

**Enforcement location:** External remote-state backend, scoped execution identities and ownership handoffs.

**Delivery disposition:** `EXTERNAL_BACKEND_CONTROLS_REQUIRED`.

**Related code/procedure:** [terraform/roots/nsx-domain/main.tf.json](../../terraform/roots/nsx-domain/main.tf.json) · [docs/INTERRUPTED_CHANGE_RECOVERY.md](../INTERRUPTED_CHANGE_RECOVERY.md). These artifacts do not individually or collectively establish the entire requirement.

**Current evidence limit:** SOURCE_AND_LOCAL_FIXTURE_ONLY_OR_NOT_IMPLEMENTED; NOT_NATIVE_QUALIFIED. Actual native evidence is not supplied.

**Outstanding dependency:** HTTP backend declarations do not implement encryption, access control, locking, versioned recovery or audit logs. Those backend controls and cross-owner grants must be configured and tested outside the source root.

| Assertion | Exact source focus | Required site-specific completion |
| --- | --- | --- |
| STATE-001/A01 | No single routine tenant automation identity SHALL have authority to modify physical fabric, management foundation, security edge, and tenant workloads simultaneously. | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |

**Verification:** [CT-019](test-specifications.md#CT-019) · [CT-044](test-specifications.md#CT-044). Apply the referenced procedure to the actual enforcement location and this focus; include effective negative/failure observations where the original criterion requires them.

**Applicability and acceptance:** TO_BE_DECIDED_FOR_ACTUAL_SERVICE; NOT_AUTO_NA. The accountable project role records applicability, configuration and evidence; this reusable allocation does not invent those decisions.

<a id="STATE-002"></a>
## STATE-002

Remote state backends SHALL use encryption, strong authentication, locking, recovery/versioning, access logging, and separation appropriate to the sensitivity of contained data.

**Source role:** Automation platform. **Original design references:** RA §24.

**Enforcement location:** External remote-state backend, scoped execution identities and ownership handoffs.

**Delivery disposition:** `EXTERNAL_BACKEND_CONTROLS_REQUIRED`.

**Related code/procedure:** [terraform/roots/nsx-domain/main.tf.json](../../terraform/roots/nsx-domain/main.tf.json) · [docs/INTERRUPTED_CHANGE_RECOVERY.md](../INTERRUPTED_CHANGE_RECOVERY.md). These artifacts do not individually or collectively establish the entire requirement.

**Current evidence limit:** SOURCE_AND_LOCAL_FIXTURE_ONLY_OR_NOT_IMPLEMENTED; NOT_NATIVE_QUALIFIED. Actual native evidence is not supplied.

**Outstanding dependency:** HTTP backend declarations do not implement encryption, access control, locking, versioned recovery or audit logs. Those backend controls and cross-owner grants must be configured and tested outside the source root.

| Assertion | Exact source focus | Required site-specific completion |
| --- | --- | --- |
| STATE-002/A01 | encryption | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |
| STATE-002/A02 | strong authentication | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |
| STATE-002/A03 | locking | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |
| STATE-002/A04 | recovery/versioning | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |
| STATE-002/A05 | access logging | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |
| STATE-002/A06 | separation | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |

**Verification:** [CT-043](test-specifications.md#CT-043) · [CT-044](test-specifications.md#CT-044) · [CT-055](test-specifications.md#CT-055). Apply the referenced procedure to the actual enforcement location and this focus; include effective negative/failure observations where the original criterion requires them.

**Applicability and acceptance:** TO_BE_DECIDED_FOR_ACTUAL_SERVICE; NOT_AUTO_NA. The accountable project role records applicability, configuration and evidence; this reusable allocation does not invent those decisions.

<a id="STATE-003"></a>
## STATE-003

Cross-state/external-service changes SHALL use a journaled dependency workflow with scoped outputs, idempotent stage completion and data-safe compensation; state-file restoration SHALL NOT be represented as infrastructure rollback.

**Source role:** Automation platform. **Original design references:** RA §24.

**Enforcement location:** External remote-state backend, scoped execution identities and ownership handoffs.

**Delivery disposition:** `EXTERNAL_BACKEND_CONTROLS_REQUIRED`.

**Related code/procedure:** [terraform/roots/nsx-domain/main.tf.json](../../terraform/roots/nsx-domain/main.tf.json) · [docs/INTERRUPTED_CHANGE_RECOVERY.md](../INTERRUPTED_CHANGE_RECOVERY.md). These artifacts do not individually or collectively establish the entire requirement.

**Current evidence limit:** SOURCE_AND_LOCAL_FIXTURE_ONLY_OR_NOT_IMPLEMENTED; NOT_NATIVE_QUALIFIED. Actual native evidence is not supplied.

**Outstanding dependency:** HTTP backend declarations do not implement encryption, access control, locking, versioned recovery or audit logs. Those backend controls and cross-owner grants must be configured and tested outside the source root.

| Assertion | Exact source focus | Required site-specific completion |
| --- | --- | --- |
| STATE-003/A01 | Cross-state/external-service changes SHALL use a journaled dependency workflow with scoped outputs, idempotent stage completion and data-safe compensation | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |
| STATE-003/A02 | state-file restoration SHALL NOT be represented as infrastructure rollback. | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |

**Verification:** [CT-044](test-specifications.md#CT-044) · [CT-045](test-specifications.md#CT-045) · [CT-070](test-specifications.md#CT-070). Apply the referenced procedure to the actual enforcement location and this focus; include effective negative/failure observations where the original criterion requires them.

**Applicability and acceptance:** TO_BE_DECIDED_FOR_ACTUAL_SERVICE; NOT_AUTO_NA. The accountable project role records applicability, configuration and evidence; this reusable allocation does not invent those decisions.

<a id="CICD-001"></a>
## CICD-001

A change that modifies inter-zone policy, external exposure, route authority, management access, or assurance profile SHALL receive a higher change classification than an ordinary workload scale operation.

**Source role:** Change authority. **Original design references:** RA §24.

**Enforcement location:** Protected Git review, dependency provenance, isolated runner, scoped apply approval and evidence capture.

**Delivery disposition:** `PARTIAL_REPOSITORY_WORKFLOW`.

**Related code/procedure:** [.github/workflows/validate.yml](../../.github/workflows/validate.yml) · [tools/plan_review.py](../../tools/plan_review.py). These artifacts do not individually or collectively establish the entire requirement.

**Current evidence limit:** SOURCE_AND_LOCAL_FIXTURE_ONLY_OR_NOT_IMPLEMENTED; NOT_NATIVE_QUALIFIED. Actual native evidence is not supplied.

**Outstanding dependency:** A read-only validation workflow is not an approved production runner, actual approval or native apply service. Action pins, dependency review, build images and signed source trust require ongoing ownership.

| Assertion | Exact source focus | Required site-specific completion |
| --- | --- | --- |
| CICD-001/A01 | A change that modifies inter-zone policy, external exposure, route authority, management access, or assurance profile SHALL receive a higher change classification than an ordinary workload scale operation. | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |

**Verification:** [CT-048](test-specifications.md#CT-048) · [CT-058](test-specifications.md#CT-058). Apply the referenced procedure to the actual enforcement location and this focus; include effective negative/failure observations where the original criterion requires them.

**Applicability and acceptance:** TO_BE_DECIDED_FOR_ACTUAL_SERVICE; NOT_AUTO_NA. The accountable project role records applicability, configuration and evidence; this reusable allocation does not invent those decisions.

<a id="CICD-002"></a>
## CICD-002

An approval SHALL bind the immutable plan and all security-relevant input/policy/state/dependency digests; stale, changed or expired artifacts SHALL be rejected at apply.

**Source role:** Automation platform. **Original design references:** RA §24.

**Enforcement location:** Protected Git review, dependency provenance, isolated runner, scoped apply approval and evidence capture.

**Delivery disposition:** `PARTIAL_REPOSITORY_WORKFLOW`.

**Related code/procedure:** [.github/workflows/validate.yml](../../.github/workflows/validate.yml) · [tools/plan_review.py](../../tools/plan_review.py). These artifacts do not individually or collectively establish the entire requirement.

**Current evidence limit:** SOURCE_AND_LOCAL_FIXTURE_ONLY_OR_NOT_IMPLEMENTED; NOT_NATIVE_QUALIFIED. Actual native evidence is not supplied.

**Outstanding dependency:** A read-only validation workflow is not an approved production runner, actual approval or native apply service. Action pins, dependency review, build images and signed source trust require ongoing ownership.

| Assertion | Exact source focus | Required site-specific completion |
| --- | --- | --- |
| CICD-002/A01 | An approval SHALL bind the immutable plan and all security-relevant input/policy/state/dependency digests | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |
| CICD-002/A02 | stale, changed or expired artifacts SHALL be rejected at apply. | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |

**Verification:** [CT-042](test-specifications.md#CT-042) · [CT-048](test-specifications.md#CT-048). Apply the referenced procedure to the actual enforcement location and this focus; include effective negative/failure observations where the original criterion requires them.

**Applicability and acceptance:** TO_BE_DECIDED_FOR_ACTUAL_SERVICE; NOT_AUTO_NA. The accountable project role records applicability, configuration and evidence; this reusable allocation does not invent those decisions.

<a id="SUP-001"></a>
## SUP-001

Privileged software/provider/module supply chains SHALL use approved sources, integrity verification, revocation and a compromise-response procedure covering already-executed artifacts and credentials.

**Source role:** Automation platform. **Original design references:** RA §24.

**Enforcement location:** Protected Git review, dependency provenance, isolated runner, scoped apply approval and evidence capture.

**Delivery disposition:** `PARTIAL_REPOSITORY_WORKFLOW`.

**Related code/procedure:** [.github/workflows/validate.yml](../../.github/workflows/validate.yml) · [tools/plan_review.py](../../tools/plan_review.py). These artifacts do not individually or collectively establish the entire requirement.

**Current evidence limit:** SOURCE_AND_LOCAL_FIXTURE_ONLY_OR_NOT_IMPLEMENTED; NOT_NATIVE_QUALIFIED. Actual native evidence is not supplied.

**Outstanding dependency:** A read-only validation workflow is not an approved production runner, actual approval or native apply service. Action pins, dependency review, build images and signed source trust require ongoing ownership.

| Assertion | Exact source focus | Required site-specific completion |
| --- | --- | --- |
| SUP-001/A01 | Privileged software/provider/module supply chains SHALL use approved sources, integrity verification, revocation and a compromise-response procedure covering already-executed artifacts and credentials. | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |

**Verification:** [CT-041](test-specifications.md#CT-041) · [CT-042](test-specifications.md#CT-042) · [CT-057](test-specifications.md#CT-057). Apply the referenced procedure to the actual enforcement location and this focus; include effective negative/failure observations where the original criterion requires them.

**Applicability and acceptance:** TO_BE_DECIDED_FOR_ACTUAL_SERVICE; NOT_AUTO_NA. The accountable project role records applicability, configuration and evidence; this reusable allocation does not invent those decisions.

<a id="SEC-001"></a>
## SEC-001

Static privileged provider credentials SHALL NOT be embedded in Terraform source code.

**Source role:** Automation platform. **Original design references:** RA §13; RA §24.

**Enforcement location:** Enterprise IAM/PKI/KMS, consuming endpoint policy, session caches and independently controlled recovery custody.

**Delivery disposition:** `EXTERNAL_SECURITY_SERVICE_REQUIRED`.

**Related code/procedure:** [lab/mtls_fixture.py](../../lab/mtls_fixture.py) · [docs/SERVICE_IDENTITY.md](../SERVICE_IDENTITY.md) · [tools/nsx_observe.py](../../tools/nsx_observe.py). These artifacts do not individually or collectively establish the entire requirement.

**Current evidence limit:** SOURCE_AND_LOCAL_FIXTURE_ONLY_OR_NOT_IMPLEMENTED; NOT_NATIVE_QUALIFIED. Actual native evidence is not supplied.

**Outstanding dependency:** Temporary mTLS fixtures and verified client HTTPS are not enterprise authentication/authorization, revocation, FIPS/module approval, at-rest encryption, key custody, algorithm transition or native KMS outage qualification.

| Assertion | Exact source focus | Required site-specific completion |
| --- | --- | --- |
| SEC-001/A01 | Static privileged provider credentials SHALL NOT be embedded in Terraform source code. | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |

**Verification:** [CT-043](test-specifications.md#CT-043). Apply the referenced procedure to the actual enforcement location and this focus; include effective negative/failure observations where the original criterion requires them.

**Applicability and acceptance:** TO_BE_DECIDED_FOR_ACTUAL_SERVICE; NOT_AUTO_NA. The accountable project role records applicability, configuration and evidence; this reusable allocation does not invent those decisions.

<a id="SEC-002"></a>
## SEC-002

Automation identities SHALL use least privilege and separate duties by control domain.

**Source role:** Automation platform. **Original design references:** RA §13; RA §24.

**Enforcement location:** Enterprise IAM/PKI/KMS, consuming endpoint policy, session caches and independently controlled recovery custody.

**Delivery disposition:** `EXTERNAL_SECURITY_SERVICE_REQUIRED`.

**Related code/procedure:** [lab/mtls_fixture.py](../../lab/mtls_fixture.py) · [docs/SERVICE_IDENTITY.md](../SERVICE_IDENTITY.md) · [tools/nsx_observe.py](../../tools/nsx_observe.py). These artifacts do not individually or collectively establish the entire requirement.

**Current evidence limit:** SOURCE_AND_LOCAL_FIXTURE_ONLY_OR_NOT_IMPLEMENTED; NOT_NATIVE_QUALIFIED. Actual native evidence is not supplied.

**Outstanding dependency:** Temporary mTLS fixtures and verified client HTTPS are not enterprise authentication/authorization, revocation, FIPS/module approval, at-rest encryption, key custody, algorithm transition or native KMS outage qualification.

| Assertion | Exact source focus | Required site-specific completion |
| --- | --- | --- |
| SEC-002/A01 | Automation identities SHALL use least privilege and separate duties by control domain. | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |

**Verification:** [CT-019](test-specifications.md#CT-019) · [CT-044](test-specifications.md#CT-044) · [CT-079](test-specifications.md#CT-079). Apply the referenced procedure to the actual enforcement location and this focus; include effective negative/failure observations where the original criterion requires them.

**Applicability and acceptance:** TO_BE_DECIDED_FOR_ACTUAL_SERVICE; NOT_AUTO_NA. The accountable project role records applicability, configuration and evidence; this reusable allocation does not invent those decisions.

<a id="SEC-003"></a>
## SEC-003

Credential rotation, revocation, and break-glass recovery SHALL be tested as part of the platform operational profile.

**Source role:** Automation platform. **Original design references:** RA §13; RA §24.

**Enforcement location:** Enterprise IAM/PKI/KMS, consuming endpoint policy, session caches and independently controlled recovery custody.

**Delivery disposition:** `EXTERNAL_SECURITY_SERVICE_REQUIRED`.

**Related code/procedure:** [lab/mtls_fixture.py](../../lab/mtls_fixture.py) · [docs/SERVICE_IDENTITY.md](../SERVICE_IDENTITY.md) · [tools/nsx_observe.py](../../tools/nsx_observe.py). These artifacts do not individually or collectively establish the entire requirement.

**Current evidence limit:** SOURCE_AND_LOCAL_FIXTURE_ONLY_OR_NOT_IMPLEMENTED; NOT_NATIVE_QUALIFIED. Actual native evidence is not supplied.

**Outstanding dependency:** Temporary mTLS fixtures and verified client HTTPS are not enterprise authentication/authorization, revocation, FIPS/module approval, at-rest encryption, key custody, algorithm transition or native KMS outage qualification.

| Assertion | Exact source focus | Required site-specific completion |
| --- | --- | --- |
| SEC-003/A01 | Credential rotation, revocation, and break-glass recovery SHALL be tested as part of the platform operational profile. | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |

**Verification:** [CT-027](test-specifications.md#CT-027) · [CT-028](test-specifications.md#CT-028) · [CT-043](test-specifications.md#CT-043). Apply the referenced procedure to the actual enforcement location and this focus; include effective negative/failure observations where the original criterion requires them.

**Applicability and acceptance:** TO_BE_DECIDED_FOR_ACTUAL_SERVICE; NOT_AUTO_NA. The accountable project role records applicability, configuration and evidence; this reusable allocation does not invent those decisions.

<a id="SEC-004"></a>
## SEC-004

Where supported and verified, sensitive values SHOULD use ephemeral/write-only mechanisms; all remaining secret-bearing plan/state/log artifacts SHALL be classified, encrypted, access-controlled and tested for unintended disclosure.

**Source role:** Automation platform. **Original design references:** RA §13; RA §24.

**Enforcement location:** Enterprise IAM/PKI/KMS, consuming endpoint policy, session caches and independently controlled recovery custody.

**Delivery disposition:** `EXTERNAL_SECURITY_SERVICE_REQUIRED`.

**Related code/procedure:** [lab/mtls_fixture.py](../../lab/mtls_fixture.py) · [docs/SERVICE_IDENTITY.md](../SERVICE_IDENTITY.md) · [tools/nsx_observe.py](../../tools/nsx_observe.py). These artifacts do not individually or collectively establish the entire requirement.

**Current evidence limit:** SOURCE_AND_LOCAL_FIXTURE_ONLY_OR_NOT_IMPLEMENTED; NOT_NATIVE_QUALIFIED. Actual native evidence is not supplied.

**Outstanding dependency:** Temporary mTLS fixtures and verified client HTTPS are not enterprise authentication/authorization, revocation, FIPS/module approval, at-rest encryption, key custody, algorithm transition or native KMS outage qualification.

| Assertion | Exact source focus | Required site-specific completion |
| --- | --- | --- |
| SEC-004/A01 | Where supported and verified, sensitive values SHOULD use ephemeral/write-only mechanisms | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |
| SEC-004/A02 | all remaining secret-bearing plan/state/log artifacts SHALL be classified, encrypted, access-controlled and tested for unintended disclosure. | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |

**Verification:** [CT-043](test-specifications.md#CT-043) · [CT-044](test-specifications.md#CT-044). Apply the referenced procedure to the actual enforcement location and this focus; include effective negative/failure observations where the original criterion requires them.

**Applicability and acceptance:** TO_BE_DECIDED_FOR_ACTUAL_SERVICE; NOT_AUTO_NA. The accountable project role records applicability, configuration and evidence; this reusable allocation does not invent those decisions.

<a id="DRIFT-001"></a>
## DRIFT-001

Security-significant drift SHALL generate an actionable event and update technical conformance/readiness conditions until resolved or accepted; formal authorization records SHALL remain separately attributable and immutable.

**Source role:** Operations/SRE. **Original design references:** RA §25.

**Enforcement location:** Effective native runtime, incident owner and separately authorized current-generation recovery/repair process.

**Delivery disposition:** `PARTIAL_READBACK_REVIEW_NO_REPAIR`.

**Related code/procedure:** [tools/recovery_review.py](../../tools/recovery_review.py) · [tools/nsx_observe.py](../../tools/nsx_observe.py) · [tools/nutanix_observe.py](../../tools/nutanix_observe.py) · [tools/neutron_observe.py](../../tools/neutron_observe.py). These artifacts do not individually or collectively establish the entire requirement.

**Current evidence limit:** SOURCE_AND_LOCAL_FIXTURE_ONLY_OR_NOT_IMPLEMENTED; NOT_NATIVE_QUALIFIED. Actual native evidence is not supplied.

**Outstanding dependency:** Exact-resource reads and offline decisions do not cover complete platform inventory, continuously detect all drift, authenticate incident authority, enforce real fencing or carry out safe native containment/repair.

| Assertion | Exact source focus | Required site-specific completion |
| --- | --- | --- |
| DRIFT-001/A01 | Security-significant drift SHALL generate an actionable event and update technical conformance/readiness conditions until resolved or accepted | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |
| DRIFT-001/A02 | formal authorization records SHALL remain separately attributable and immutable. | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |

**Verification:** [CT-014](test-specifications.md#CT-014) · [CT-049](test-specifications.md#CT-049) · [CT-057](test-specifications.md#CT-057). Apply the referenced procedure to the actual enforcement location and this focus; include effective negative/failure observations where the original criterion requires them.

**Applicability and acceptance:** TO_BE_DECIDED_FOR_ACTUAL_SERVICE; NOT_AUTO_NA. The accountable project role records applicability, configuration and evidence; this reusable allocation does not invent those decisions.

<a id="DRIFT-002"></a>
## DRIFT-002

Emergency changes SHALL be reconciled back into the source of truth after the incident or maintenance action.

**Source role:** Operations/SRE. **Original design references:** RA §25.

**Enforcement location:** Effective native runtime, incident owner and separately authorized current-generation recovery/repair process.

**Delivery disposition:** `PARTIAL_READBACK_REVIEW_NO_REPAIR`.

**Related code/procedure:** [tools/recovery_review.py](../../tools/recovery_review.py) · [tools/nsx_observe.py](../../tools/nsx_observe.py) · [tools/nutanix_observe.py](../../tools/nutanix_observe.py) · [tools/neutron_observe.py](../../tools/neutron_observe.py). These artifacts do not individually or collectively establish the entire requirement.

**Current evidence limit:** SOURCE_AND_LOCAL_FIXTURE_ONLY_OR_NOT_IMPLEMENTED; NOT_NATIVE_QUALIFIED. Actual native evidence is not supplied.

**Outstanding dependency:** Exact-resource reads and offline decisions do not cover complete platform inventory, continuously detect all drift, authenticate incident authority, enforce real fencing or carry out safe native containment/repair.

| Assertion | Exact source focus | Required site-specific completion |
| --- | --- | --- |
| DRIFT-002/A01 | Emergency changes SHALL be reconciled back into the source of truth after the incident or maintenance action. | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |

**Verification:** [CT-014](test-specifications.md#CT-014) · [CT-057](test-specifications.md#CT-057). Apply the referenced procedure to the actual enforcement location and this focus; include effective negative/failure observations where the original criterion requires them.

**Applicability and acceptance:** TO_BE_DECIDED_FOR_ACTUAL_SERVICE; NOT_AUTO_NA. The accountable project role records applicability, configuration and evidence; this reusable allocation does not invent those decisions.

<a id="DRIFT-003"></a>
## DRIFT-003

Incident containment overrides SHALL take precedence over ordinary reconciliation until explicitly released or handled by their approved expiry policy; automated repair SHALL NOT silently undo containment.

**Source role:** Incident response. **Original design references:** RA §25.

**Enforcement location:** Effective native runtime, incident owner and separately authorized current-generation recovery/repair process.

**Delivery disposition:** `PARTIAL_READBACK_REVIEW_NO_REPAIR`.

**Related code/procedure:** [tools/recovery_review.py](../../tools/recovery_review.py) · [tools/nsx_observe.py](../../tools/nsx_observe.py) · [tools/nutanix_observe.py](../../tools/nutanix_observe.py) · [tools/neutron_observe.py](../../tools/neutron_observe.py). These artifacts do not individually or collectively establish the entire requirement.

**Current evidence limit:** SOURCE_AND_LOCAL_FIXTURE_ONLY_OR_NOT_IMPLEMENTED; NOT_NATIVE_QUALIFIED. Actual native evidence is not supplied.

**Outstanding dependency:** Exact-resource reads and offline decisions do not cover complete platform inventory, continuously detect all drift, authenticate incident authority, enforce real fencing or carry out safe native containment/repair.

| Assertion | Exact source focus | Required site-specific completion |
| --- | --- | --- |
| DRIFT-003/A01 | Incident containment overrides SHALL take precedence over ordinary reconciliation until explicitly released or handled by their approved expiry policy | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |
| DRIFT-003/A02 | automated repair SHALL NOT silently undo containment. | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |

**Verification:** [CT-057](test-specifications.md#CT-057) · [CT-058](test-specifications.md#CT-058) · [CT-066](test-specifications.md#CT-066). Apply the referenced procedure to the actual enforcement location and this focus; include effective negative/failure observations where the original criterion requires them.

**Applicability and acceptance:** TO_BE_DECIDED_FOR_ACTUAL_SERVICE; NOT_AUTO_NA. The accountable project role records applicability, configuration and evidence; this reusable allocation does not invent those decisions.

<a id="ASSUR-001"></a>
## ASSUR-001

Assurance profile selection SHALL be based on system security requirements and risk analysis rather than tenant preference alone.

**Source role:** Security authority. **Original design references:** RA §7; RA §11; RA §12; RA §14.

**Enforcement location:** Accepted service/profile and topology records; native domain/identity boundaries implement selected constraints.

**Delivery disposition:** `PARTIAL_DESIGN_AND_CANDIDATE`.

**Related code/procedure:** [docs/architecture/RAD.md](../architecture/RAD.md) · [docs/engineering/TAD.md](../engineering/TAD.md) · [tools/input_review.py](../../tools/input_review.py). These artifacts do not individually or collectively establish the entire requirement.

**Current evidence limit:** SOURCE_AND_LOCAL_FIXTURE_ONLY_OR_NOT_IMPLEMENTED; NOT_NATIVE_QUALIFIED. Actual native evidence is not supplied.

**Outstanding dependency:** No complete authoritative service/profile registry, tenant role enforcement or actual placement/edge evidence is supplied. Input screening covers only its enumerated examples and cannot accept the complete service.

| Assertion | Exact source focus | Required site-specific completion |
| --- | --- | --- |
| ASSUR-001/A01 | Assurance profile selection SHALL be based on system security requirements and risk analysis rather than tenant preference alone. | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |

**Verification:** [CT-035](test-specifications.md#CT-035) · [CT-062](test-specifications.md#CT-062). Apply the referenced procedure to the actual enforcement location and this focus; include effective negative/failure observations where the original criterion requires them.

**Applicability and acceptance:** TO_BE_DECIDED_FOR_ACTUAL_SERVICE; NOT_AUTO_NA. The accountable project role records applicability, configuration and evidence; this reusable allocation does not invent those decisions.

<a id="ASSUR-002"></a>
## ASSUR-002

Assurance profiles SHALL define explicit isolation for compute, storage, routing, edge, management, backup and keys, with measurable verification and exception rules; “dedicated” SHALL identify its actual resource scope.

**Source role:** Security authority. **Original design references:** RA §7; RA §11; RA §12; RA §14.

**Enforcement location:** Accepted service/profile and topology records; native domain/identity boundaries implement selected constraints.

**Delivery disposition:** `PARTIAL_DESIGN_AND_CANDIDATE`.

**Related code/procedure:** [docs/architecture/RAD.md](../architecture/RAD.md) · [docs/engineering/TAD.md](../engineering/TAD.md) · [tools/input_review.py](../../tools/input_review.py). These artifacts do not individually or collectively establish the entire requirement.

**Current evidence limit:** SOURCE_AND_LOCAL_FIXTURE_ONLY_OR_NOT_IMPLEMENTED; NOT_NATIVE_QUALIFIED. Actual native evidence is not supplied.

**Outstanding dependency:** No complete authoritative service/profile registry, tenant role enforcement or actual placement/edge evidence is supplied. Input screening covers only its enumerated examples and cannot accept the complete service.

| Assertion | Exact source focus | Required site-specific completion |
| --- | --- | --- |
| ASSUR-002/A01 | Assurance profiles SHALL define explicit isolation for compute, storage, routing, edge, management, backup and keys, with measurable verification and exception rules | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |
| ASSUR-002/A02 | “dedicated” SHALL identify its actual resource scope. | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |

**Verification:** [CT-018](test-specifications.md#CT-018) · [CT-035](test-specifications.md#CT-035) · [CT-037](test-specifications.md#CT-037) · [CT-062](test-specifications.md#CT-062). Apply the referenced procedure to the actual enforcement location and this focus; include effective negative/failure observations where the original criterion requires them.

**Applicability and acceptance:** TO_BE_DECIDED_FOR_ACTUAL_SERVICE; NOT_AUTO_NA. The accountable project role records applicability, configuration and evidence; this reusable allocation does not invent those decisions.

<a id="ASSUR-003"></a>
## ASSUR-003

A production profile SHALL have approved parameter values, owners, applicable test sets and evidence freshness limits; incomplete or expired profiles SHALL be ineligible for new production placement.

**Source role:** Security authority. **Original design references:** RA §7; RA §11; RA §12; RA §14.

**Enforcement location:** Accepted service/profile and topology records; native domain/identity boundaries implement selected constraints.

**Delivery disposition:** `PARTIAL_DESIGN_AND_CANDIDATE`.

**Related code/procedure:** [docs/architecture/RAD.md](../architecture/RAD.md) · [docs/engineering/TAD.md](../engineering/TAD.md) · [tools/input_review.py](../../tools/input_review.py). These artifacts do not individually or collectively establish the entire requirement.

**Current evidence limit:** SOURCE_AND_LOCAL_FIXTURE_ONLY_OR_NOT_IMPLEMENTED; NOT_NATIVE_QUALIFIED. Actual native evidence is not supplied.

**Outstanding dependency:** No complete authoritative service/profile registry, tenant role enforcement or actual placement/edge evidence is supplied. Input screening covers only its enumerated examples and cannot accept the complete service.

| Assertion | Exact source focus | Required site-specific completion |
| --- | --- | --- |
| ASSUR-003/A01 | A production profile SHALL have approved parameter values, owners, applicable test sets and evidence freshness limits | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |
| ASSUR-003/A02 | incomplete or expired profiles SHALL be ineligible for new production placement. | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |

**Verification:** [CT-018](test-specifications.md#CT-018) · [CT-058](test-specifications.md#CT-058) · [CT-069](test-specifications.md#CT-069). Apply the referenced procedure to the actual enforcement location and this focus; include effective negative/failure observations where the original criterion requires them.

**Applicability and acceptance:** TO_BE_DECIDED_FOR_ACTUAL_SERVICE; NOT_AUTO_NA. The accountable project role records applicability, configuration and evidence; this reusable allocation does not invent those decisions.

<a id="TEST-001"></a>
## TEST-001

Negative tests SHALL be first-class acceptance criteria; proving that an allowed flow works is insufficient.

**Source role:** Assurance engineering. **Original design references:** RA §28.

**Enforcement location:** Approved qualification campaign, independent observation and evidence store at declared versions/topology.

**Delivery disposition:** `LOCAL_FIXTURES_NOT_NATIVE_QUALIFICATION`.

**Related code/procedure:** [docs/assurance/test-specifications.md](test-specifications.md) · [lab/run_readback_lab.py](../../lab/run_readback_lab.py) · [lab/run_namespace_lab.py](../../lab/run_namespace_lab.py). These artifacts do not individually or collectively establish the entire requirement.

**Current evidence limit:** SOURCE_AND_LOCAL_FIXTURE_ONLY_OR_NOT_IMPLEMENTED; NOT_NATIVE_QUALIFIED. Actual native evidence is not supplied.

**Outstanding dependency:** Reference procedures, local fixtures and hashes do not create native evidence, immutable evidence custody, complete assertion coverage, platform qualification or authorization.

| Assertion | Exact source focus | Required site-specific completion |
| --- | --- | --- |
| TEST-001/A01 | Negative tests SHALL be first-class acceptance criteria | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |
| TEST-001/A02 | proving that an allowed flow works is insufficient. | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |

**Verification:** [CT-001](test-specifications.md#CT-001) · [CT-002](test-specifications.md#CT-002) · [CT-003](test-specifications.md#CT-003) · [CT-007](test-specifications.md#CT-007). Apply the referenced procedure to the actual enforcement location and this focus; include effective negative/failure observations where the original criterion requires them.

**Applicability and acceptance:** TO_BE_DECIDED_FOR_ACTUAL_SERVICE; NOT_AUTO_NA. The accountable project role records applicability, configuration and evidence; this reusable allocation does not invent those decisions.

<a id="TEST-002"></a>
## TEST-002

A platform upgrade SHALL trigger an appropriate regression/conformance test set before broad production rollout.

**Source role:** Assurance engineering. **Original design references:** RA §28.

**Enforcement location:** Approved qualification campaign, independent observation and evidence store at declared versions/topology.

**Delivery disposition:** `LOCAL_FIXTURES_NOT_NATIVE_QUALIFICATION`.

**Related code/procedure:** [docs/assurance/test-specifications.md](test-specifications.md) · [lab/run_readback_lab.py](../../lab/run_readback_lab.py) · [lab/run_namespace_lab.py](../../lab/run_namespace_lab.py). These artifacts do not individually or collectively establish the entire requirement.

**Current evidence limit:** SOURCE_AND_LOCAL_FIXTURE_ONLY_OR_NOT_IMPLEMENTED; NOT_NATIVE_QUALIFIED. Actual native evidence is not supplied.

**Outstanding dependency:** Reference procedures, local fixtures and hashes do not create native evidence, immutable evidence custody, complete assertion coverage, platform qualification or authorization.

| Assertion | Exact source focus | Required site-specific completion |
| --- | --- | --- |
| TEST-002/A01 | A platform upgrade SHALL trigger an appropriate regression/conformance test set before broad production rollout. | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |

**Verification:** [CT-015](test-specifications.md#CT-015) · [CT-018](test-specifications.md#CT-018). Apply the referenced procedure to the actual enforcement location and this focus; include effective negative/failure observations where the original criterion requires them.

**Applicability and acceptance:** TO_BE_DECIDED_FOR_ACTUAL_SERVICE; NOT_AUTO_NA. The accountable project role records applicability, configuration and evidence; this reusable allocation does not invent those decisions.

<a id="TEST-003"></a>
## TEST-003

Every test execution SHALL record target versions, preconditions, healthy control paths, observation, expected outcome and attributable evidence; blocked, not-run or unjustified not-applicable results SHALL NOT satisfy mandatory gates.

**Source role:** Assurance engineering. **Original design references:** RA §28.

**Enforcement location:** Approved qualification campaign, independent observation and evidence store at declared versions/topology.

**Delivery disposition:** `LOCAL_FIXTURES_NOT_NATIVE_QUALIFICATION`.

**Related code/procedure:** [docs/assurance/test-specifications.md](test-specifications.md) · [lab/run_readback_lab.py](../../lab/run_readback_lab.py) · [lab/run_namespace_lab.py](../../lab/run_namespace_lab.py). These artifacts do not individually or collectively establish the entire requirement.

**Current evidence limit:** SOURCE_AND_LOCAL_FIXTURE_ONLY_OR_NOT_IMPLEMENTED; NOT_NATIVE_QUALIFIED. Actual native evidence is not supplied.

**Outstanding dependency:** Reference procedures, local fixtures and hashes do not create native evidence, immutable evidence custody, complete assertion coverage, platform qualification or authorization.

| Assertion | Exact source focus | Required site-specific completion |
| --- | --- | --- |
| TEST-003/A01 | Every test execution SHALL record target versions, preconditions, healthy control paths, observation, expected outcome and attributable evidence | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |
| TEST-003/A02 | blocked, not-run or unjustified not-applicable results SHALL NOT satisfy mandatory gates. | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |

**Verification:** [CT-049](test-specifications.md#CT-049) · [CT-069](test-specifications.md#CT-069) · [CT-075](test-specifications.md#CT-075). Apply the referenced procedure to the actual enforcement location and this focus; include effective negative/failure observations where the original criterion requires them.

**Applicability and acceptance:** TO_BE_DECIDED_FOR_ACTUAL_SERVICE; NOT_AUTO_NA. The accountable project role records applicability, configuration and evidence; this reusable allocation does not invent those decisions.

<a id="TEST-004"></a>
## TEST-004

Fault-injection and intrusive negative tests SHALL run only within an approved scope, safety envelope and recovery procedure; production testing SHALL protect unrelated tenants.

**Source role:** Assurance engineering. **Original design references:** RA §28.

**Enforcement location:** Approved qualification campaign, independent observation and evidence store at declared versions/topology.

**Delivery disposition:** `LOCAL_FIXTURES_NOT_NATIVE_QUALIFICATION`.

**Related code/procedure:** [docs/assurance/test-specifications.md](test-specifications.md) · [lab/run_readback_lab.py](../../lab/run_readback_lab.py) · [lab/run_namespace_lab.py](../../lab/run_namespace_lab.py). These artifacts do not individually or collectively establish the entire requirement.

**Current evidence limit:** SOURCE_AND_LOCAL_FIXTURE_ONLY_OR_NOT_IMPLEMENTED; NOT_NATIVE_QUALIFIED. Actual native evidence is not supplied.

**Outstanding dependency:** Reference procedures, local fixtures and hashes do not create native evidence, immutable evidence custody, complete assertion coverage, platform qualification or authorization.

| Assertion | Exact source focus | Required site-specific completion |
| --- | --- | --- |
| TEST-004/A01 | Fault-injection and intrusive negative tests SHALL run only within an approved scope, safety envelope and recovery procedure | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |
| TEST-004/A02 | production testing SHALL protect unrelated tenants. | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |

**Verification:** [CT-011](test-specifications.md#CT-011) · [CT-012](test-specifications.md#CT-012) · [CT-034](test-specifications.md#CT-034) · [CT-054](test-specifications.md#CT-054). Apply the referenced procedure to the actual enforcement location and this focus; include effective negative/failure observations where the original criterion requires them.

**Applicability and acceptance:** TO_BE_DECIDED_FOR_ACTUAL_SERVICE; NOT_AUTO_NA. The accountable project role records applicability, configuration and evidence; this reusable allocation does not invent those decisions.

<a id="EVID-001"></a>
## EVID-001

The evidence record SHALL identify the source revision, policy version, provider/module versions, realized security relationships, test results, and active exceptions.

**Source role:** Assurance engineering. **Original design references:** RA §26; RA §28.

**Enforcement location:** Approved qualification campaign, independent observation and evidence store at declared versions/topology.

**Delivery disposition:** `LOCAL_FIXTURES_NOT_NATIVE_QUALIFICATION`.

**Related code/procedure:** [docs/assurance/test-specifications.md](test-specifications.md) · [lab/run_readback_lab.py](../../lab/run_readback_lab.py) · [lab/run_namespace_lab.py](../../lab/run_namespace_lab.py). These artifacts do not individually or collectively establish the entire requirement.

**Current evidence limit:** SOURCE_AND_LOCAL_FIXTURE_ONLY_OR_NOT_IMPLEMENTED; NOT_NATIVE_QUALIFIED. Actual native evidence is not supplied.

**Outstanding dependency:** Reference procedures, local fixtures and hashes do not create native evidence, immutable evidence custody, complete assertion coverage, platform qualification or authorization.

| Assertion | Exact source focus | Required site-specific completion |
| --- | --- | --- |
| EVID-001/A01 | The evidence record SHALL identify the source revision, policy version, provider/module versions, realized security relationships, test results, and active exceptions. | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |

**Verification:** [CT-049](test-specifications.md#CT-049) · [CT-069](test-specifications.md#CT-069) · [CT-075](test-specifications.md#CT-075). Apply the referenced procedure to the actual enforcement location and this focus; include effective negative/failure observations where the original criterion requires them.

**Applicability and acceptance:** TO_BE_DECIDED_FOR_ACTUAL_SERVICE; NOT_AUTO_NA. The accountable project role records applicability, configuration and evidence; this reusable allocation does not invent those decisions.

<a id="EVID-002"></a>
## EVID-002

Evidence SHALL bind target generation, source/profile/capability/dependency digests, artifact integrity, collection time, test executions and active exceptions; freshness SHALL be evaluated after material changes.

**Source role:** Assurance engineering. **Original design references:** RA §26; RA §28.

**Enforcement location:** Approved qualification campaign, independent observation and evidence store at declared versions/topology.

**Delivery disposition:** `LOCAL_FIXTURES_NOT_NATIVE_QUALIFICATION`.

**Related code/procedure:** [docs/assurance/test-specifications.md](test-specifications.md) · [lab/run_readback_lab.py](../../lab/run_readback_lab.py) · [lab/run_namespace_lab.py](../../lab/run_namespace_lab.py). These artifacts do not individually or collectively establish the entire requirement.

**Current evidence limit:** SOURCE_AND_LOCAL_FIXTURE_ONLY_OR_NOT_IMPLEMENTED; NOT_NATIVE_QUALIFIED. Actual native evidence is not supplied.

**Outstanding dependency:** Reference procedures, local fixtures and hashes do not create native evidence, immutable evidence custody, complete assertion coverage, platform qualification or authorization.

| Assertion | Exact source focus | Required site-specific completion |
| --- | --- | --- |
| EVID-002/A01 | Evidence SHALL bind target generation, source/profile/capability/dependency digests, artifact integrity, collection time, test executions and active exceptions | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |
| EVID-002/A02 | freshness SHALL be evaluated after material changes. | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |

**Verification:** [CT-048](test-specifications.md#CT-048) · [CT-049](test-specifications.md#CT-049) · [CT-069](test-specifications.md#CT-069). Apply the referenced procedure to the actual enforcement location and this focus; include effective negative/failure observations where the original criterion requires them.

**Applicability and acceptance:** TO_BE_DECIDED_FOR_ACTUAL_SERVICE; NOT_AUTO_NA. The accountable project role records applicability, configuration and evidence; this reusable allocation does not invent those decisions.

<a id="EVID-003"></a>
## EVID-003

Formal authorization decisions SHALL be issued by the designated authority and retained separately from technical test status, with scope, validity and operating conditions that the controller can evaluate.

**Source role:** Security authority. **Original design references:** RA §26; RA §28.

**Enforcement location:** Approved qualification campaign, independent observation and evidence store at declared versions/topology.

**Delivery disposition:** `LOCAL_FIXTURES_NOT_NATIVE_QUALIFICATION`.

**Related code/procedure:** [docs/assurance/test-specifications.md](test-specifications.md) · [lab/run_readback_lab.py](../../lab/run_readback_lab.py) · [lab/run_namespace_lab.py](../../lab/run_namespace_lab.py). These artifacts do not individually or collectively establish the entire requirement.

**Current evidence limit:** SOURCE_AND_LOCAL_FIXTURE_ONLY_OR_NOT_IMPLEMENTED; NOT_NATIVE_QUALIFIED. Actual native evidence is not supplied.

**Outstanding dependency:** Reference procedures, local fixtures and hashes do not create native evidence, immutable evidence custody, complete assertion coverage, platform qualification or authorization.

| Assertion | Exact source focus | Required site-specific completion |
| --- | --- | --- |
| EVID-003/A01 | Formal authorization decisions SHALL be issued by the designated authority and retained separately from technical test status, with scope, validity and operating conditions that the controller can evaluate. | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |

**Verification:** [CT-049](test-specifications.md#CT-049) · [CT-058](test-specifications.md#CT-058) · [CT-069](test-specifications.md#CT-069). Apply the referenced procedure to the actual enforcement location and this focus; include effective negative/failure observations where the original criterion requires them.

**Applicability and acceptance:** TO_BE_DECIDED_FOR_ACTUAL_SERVICE; NOT_AUTO_NA. The accountable project role records applicability, configuration and evidence; this reusable allocation does not invent those decisions.

<a id="OBS-001"></a>
## OBS-001

Logs SHALL contain stable identifiers sufficient to correlate tenant, WSD, Security Domain, policy, and deployment evidence.

**Source role:** Security operations. **Original design references:** RA §26.

**Enforcement location:** Independent collectors and audit paths at platforms, ZIPs, execution, identity and address authorities.

**Delivery disposition:** `EXTERNAL_TELEMETRY_SERVICE_REQUIRED`.

**Related code/procedure:** [docs/operations/README.md](../operations/README.md) · [lab/run_namespace_lab.py](../../lab/run_namespace_lab.py). These artifacts do not individually or collectively establish the entire requirement.

**Current evidence limit:** SOURCE_AND_LOCAL_FIXTURE_ONLY_OR_NOT_IMPLEMENTED; NOT_NATIVE_QUALIFIED. Actual native evidence is not supplied.

**Outstanding dependency:** Fixture counters are not production telemetry. Stable event identifiers, collector independence, buffering/loss detection, storage retention/access and outage restrictions require native services and observations.

| Assertion | Exact source focus | Required site-specific completion |
| --- | --- | --- |
| OBS-001/A01 | Logs SHALL contain stable identifiers sufficient to correlate tenant, WSD, Security Domain, policy, and deployment evidence. | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |

**Verification:** [CT-010](test-specifications.md#CT-010) · [CT-049](test-specifications.md#CT-049). Apply the referenced procedure to the actual enforcement location and this focus; include effective negative/failure observations where the original criterion requires them.

**Applicability and acceptance:** TO_BE_DECIDED_FOR_ACTUAL_SERVICE; NOT_AUTO_NA. The accountable project role records applicability, configuration and evidence; this reusable allocation does not invent those decisions.

<a id="OBS-002"></a>
## OBS-002

Security control logging SHALL not depend solely on the tenant workload being healthy or cooperative.

**Source role:** Security operations. **Original design references:** RA §26.

**Enforcement location:** Independent collectors and audit paths at platforms, ZIPs, execution, identity and address authorities.

**Delivery disposition:** `EXTERNAL_TELEMETRY_SERVICE_REQUIRED`.

**Related code/procedure:** [docs/operations/README.md](../operations/README.md) · [lab/run_namespace_lab.py](../../lab/run_namespace_lab.py). These artifacts do not individually or collectively establish the entire requirement.

**Current evidence limit:** SOURCE_AND_LOCAL_FIXTURE_ONLY_OR_NOT_IMPLEMENTED; NOT_NATIVE_QUALIFIED. Actual native evidence is not supplied.

**Outstanding dependency:** Fixture counters are not production telemetry. Stable event identifiers, collector independence, buffering/loss detection, storage retention/access and outage restrictions require native services and observations.

| Assertion | Exact source focus | Required site-specific completion |
| --- | --- | --- |
| OBS-002/A01 | Security control logging SHALL not depend solely on the tenant workload being healthy or cooperative. | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |

**Verification:** [CT-010](test-specifications.md#CT-010) · [CT-050](test-specifications.md#CT-050). Apply the referenced procedure to the actual enforcement location and this focus; include effective negative/failure observations where the original criterion requires them.

**Applicability and acceptance:** TO_BE_DECIDED_FOR_ACTUAL_SERVICE; NOT_AUTO_NA. The accountable project role records applicability, configuration and evidence; this reusable allocation does not invent those decisions.

<a id="OBS-003"></a>
## OBS-003

Logging profiles SHALL define event coverage, attribution, time integrity, minimization, forwarding latency, buffering, loss alerting, retention, access and safe behavior during collection failure.

**Source role:** Security operations. **Original design references:** RA §26.

**Enforcement location:** Independent collectors and audit paths at platforms, ZIPs, execution, identity and address authorities.

**Delivery disposition:** `EXTERNAL_TELEMETRY_SERVICE_REQUIRED`.

**Related code/procedure:** [docs/operations/README.md](../operations/README.md) · [lab/run_namespace_lab.py](../../lab/run_namespace_lab.py). These artifacts do not individually or collectively establish the entire requirement.

**Current evidence limit:** SOURCE_AND_LOCAL_FIXTURE_ONLY_OR_NOT_IMPLEMENTED; NOT_NATIVE_QUALIFIED. Actual native evidence is not supplied.

**Outstanding dependency:** Fixture counters are not production telemetry. Stable event identifiers, collector independence, buffering/loss detection, storage retention/access and outage restrictions require native services and observations.

| Assertion | Exact source focus | Required site-specific completion |
| --- | --- | --- |
| OBS-003/A01 | Logging profiles SHALL define event coverage, attribution, time integrity, minimization, forwarding latency, buffering, loss alerting, retention, access and safe behavior during collection failure. | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |

**Verification:** [CT-010](test-specifications.md#CT-010) · [CT-050](test-specifications.md#CT-050) · [CT-068](test-specifications.md#CT-068). Apply the referenced procedure to the actual enforcement location and this focus; include effective negative/failure observations where the original criterion requires them.

**Applicability and acceptance:** TO_BE_DECIDED_FOR_ACTUAL_SERVICE; NOT_AUTO_NA. The accountable project role records applicability, configuration and evidence; this reusable allocation does not invent those decisions.

<a id="CAP-001"></a>
## CAP-001

Capacity planning SHALL include N+failure headroom so that loss of a security-edge node does not require disabling or bypassing enforcement.

**Source role:** Capacity management. **Original design references:** RA §4; RA §26.

**Enforcement location:** Service catalogue, measured surviving resource pools, security-edge and dependency failure/maintenance behaviour.

**Delivery disposition:** `EXTERNAL_CAPACITY_AND_QUALIFICATION_REQUIRED`.

**Related code/procedure:** [docs/engineering/TAD.md](../engineering/TAD.md) · [lab/run_namespace_lab.py](../../lab/run_namespace_lab.py). These artifacts do not individually or collectively establish the entire requirement.

**Current evidence limit:** SOURCE_AND_LOCAL_FIXTURE_ONLY_OR_NOT_IMPLEMENTED; NOT_NATIVE_QUALIFIED. Actual native evidence is not supplied.

**Outstanding dependency:** Illustrative capacity schedules and local link-failure fixtures do not establish measured production SLO/RTO/RPO, qualified limits, complete reservations or procured-to-available inventory.

| Assertion | Exact source focus | Required site-specific completion |
| --- | --- | --- |
| CAP-001/A01 | Capacity planning SHALL include N+failure headroom so that loss of a security-edge node does not require disabling or bypassing enforcement. | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |

**Verification:** [CT-012](test-specifications.md#CT-012) · [CT-056](test-specifications.md#CT-056). Apply the referenced procedure to the actual enforcement location and this focus; include effective negative/failure observations where the original criterion requires them.

**Applicability and acceptance:** TO_BE_DECIDED_FOR_ACTUAL_SERVICE; NOT_AUTO_NA. The accountable project role records applicability, configuration and evidence; this reusable allocation does not invent those decisions.

<a id="CAP-002"></a>
## CAP-002

Placement and growth admission SHALL evaluate measured surviving capacity, security-feature overhead, shared dependencies, quotas and operational reserves for the approved failure model.

**Source role:** Capacity management. **Original design references:** RA §4; RA §26.

**Enforcement location:** Service catalogue, measured surviving resource pools, security-edge and dependency failure/maintenance behaviour.

**Delivery disposition:** `EXTERNAL_CAPACITY_AND_QUALIFICATION_REQUIRED`.

**Related code/procedure:** [docs/engineering/TAD.md](../engineering/TAD.md) · [lab/run_namespace_lab.py](../../lab/run_namespace_lab.py). These artifacts do not individually or collectively establish the entire requirement.

**Current evidence limit:** SOURCE_AND_LOCAL_FIXTURE_ONLY_OR_NOT_IMPLEMENTED; NOT_NATIVE_QUALIFIED. Actual native evidence is not supplied.

**Outstanding dependency:** Illustrative capacity schedules and local link-failure fixtures do not establish measured production SLO/RTO/RPO, qualified limits, complete reservations or procured-to-available inventory.

| Assertion | Exact source focus | Required site-specific completion |
| --- | --- | --- |
| CAP-002/A01 | Placement and growth admission SHALL evaluate measured surviving capacity, security-feature overhead, shared dependencies, quotas and operational reserves for the approved failure model. | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |

**Verification:** [CT-039](test-specifications.md#CT-039) · [CT-047](test-specifications.md#CT-047) · [CT-056](test-specifications.md#CT-056). Apply the referenced procedure to the actual enforcement location and this focus; include effective negative/failure observations where the original criterion requires them.

**Applicability and acceptance:** TO_BE_DECIDED_FOR_ACTUAL_SERVICE; NOT_AUTO_NA. The accountable project role records applicability, configuration and evidence; this reusable allocation does not invent those decisions.

<a id="CAP-003"></a>
## CAP-003

Capacity reporting SHALL distinguish procured, received, commissioned, allocated, reserved and consumed capacity and identify unused-capacity age, constraints and accountable remediation.

**Source role:** Service management. **Original design references:** RA §4; RA §26.

**Enforcement location:** Service catalogue, measured surviving resource pools, security-edge and dependency failure/maintenance behaviour.

**Delivery disposition:** `EXTERNAL_CAPACITY_AND_QUALIFICATION_REQUIRED`.

**Related code/procedure:** [docs/engineering/TAD.md](../engineering/TAD.md) · [lab/run_namespace_lab.py](../../lab/run_namespace_lab.py). These artifacts do not individually or collectively establish the entire requirement.

**Current evidence limit:** SOURCE_AND_LOCAL_FIXTURE_ONLY_OR_NOT_IMPLEMENTED; NOT_NATIVE_QUALIFIED. Actual native evidence is not supplied.

**Outstanding dependency:** Illustrative capacity schedules and local link-failure fixtures do not establish measured production SLO/RTO/RPO, qualified limits, complete reservations or procured-to-available inventory.

| Assertion | Exact source focus | Required site-specific completion |
| --- | --- | --- |
| CAP-003/A01 | Capacity reporting SHALL distinguish procured, received, commissioned, allocated, reserved and consumed capacity and identify unused-capacity age, constraints and accountable remediation. | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |

**Verification:** [CT-074](test-specifications.md#CT-074). Apply the referenced procedure to the actual enforcement location and this focus; include effective negative/failure observations where the original criterion requires them.

**Applicability and acceptance:** TO_BE_DECIDED_FOR_ACTUAL_SERVICE; NOT_AUTO_NA. The accountable project role records applicability, configuration and evidence; this reusable allocation does not invent those decisions.

<a id="FAIL-001"></a>
## FAIL-001

Control-plane failure SHALL NOT create an implicit permit path.

**Source role:** Platform operations. **Original design references:** RA §14; RA §27.

**Enforcement location:** Service catalogue, measured surviving resource pools, security-edge and dependency failure/maintenance behaviour.

**Delivery disposition:** `EXTERNAL_CAPACITY_AND_QUALIFICATION_REQUIRED`.

**Related code/procedure:** [docs/engineering/TAD.md](../engineering/TAD.md) · [lab/run_namespace_lab.py](../../lab/run_namespace_lab.py). These artifacts do not individually or collectively establish the entire requirement.

**Current evidence limit:** SOURCE_AND_LOCAL_FIXTURE_ONLY_OR_NOT_IMPLEMENTED; NOT_NATIVE_QUALIFIED. Actual native evidence is not supplied.

**Outstanding dependency:** Illustrative capacity schedules and local link-failure fixtures do not establish measured production SLO/RTO/RPO, qualified limits, complete reservations or procured-to-available inventory.

| Assertion | Exact source focus | Required site-specific completion |
| --- | --- | --- |
| FAIL-001/A01 | Control-plane failure SHALL NOT create an implicit permit path. | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |

**Verification:** [CT-011](test-specifications.md#CT-011) · [CT-012](test-specifications.md#CT-012) · [CT-024](test-specifications.md#CT-024) · [CT-052](test-specifications.md#CT-052). Apply the referenced procedure to the actual enforcement location and this focus; include effective negative/failure observations where the original criterion requires them.

**Applicability and acceptance:** TO_BE_DECIDED_FOR_ACTUAL_SERVICE; NOT_AUTO_NA. The accountable project role records applicability, configuration and evidence; this reusable allocation does not invent those decisions.

<a id="FAIL-002"></a>
## FAIL-002

Failover and control-plane-loss scenarios SHALL be included in platform conformance testing.

**Source role:** Assurance engineering. **Original design references:** RA §14; RA §27.

**Enforcement location:** Service catalogue, measured surviving resource pools, security-edge and dependency failure/maintenance behaviour.

**Delivery disposition:** `EXTERNAL_CAPACITY_AND_QUALIFICATION_REQUIRED`.

**Related code/procedure:** [docs/engineering/TAD.md](../engineering/TAD.md) · [lab/run_namespace_lab.py](../../lab/run_namespace_lab.py). These artifacts do not individually or collectively establish the entire requirement.

**Current evidence limit:** SOURCE_AND_LOCAL_FIXTURE_ONLY_OR_NOT_IMPLEMENTED; NOT_NATIVE_QUALIFIED. Actual native evidence is not supplied.

**Outstanding dependency:** Illustrative capacity schedules and local link-failure fixtures do not establish measured production SLO/RTO/RPO, qualified limits, complete reservations or procured-to-available inventory.

| Assertion | Exact source focus | Required site-specific completion |
| --- | --- | --- |
| FAIL-002/A01 | Failover and control-plane-loss scenarios SHALL be included in platform conformance testing. | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |

**Verification:** [CT-011](test-specifications.md#CT-011) · [CT-012](test-specifications.md#CT-012) · [CT-027](test-specifications.md#CT-027) · [CT-038](test-specifications.md#CT-038) · [CT-050](test-specifications.md#CT-050) · [CT-054](test-specifications.md#CT-054) · [CT-055](test-specifications.md#CT-055). Apply the referenced procedure to the actual enforcement location and this focus; include effective negative/failure observations where the original criterion requires them.

**Applicability and acceptance:** TO_BE_DECIDED_FOR_ACTUAL_SERVICE; NOT_AUTO_NA. The accountable project role records applicability, configuration and evidence; this reusable allocation does not invent those decisions.

<a id="FAIL-003"></a>
## FAIL-003

Every critical dependency SHALL have a qualified loss/partition/recovery behavior, including credential/key continuity, logging loss, state recovery and split-brain prevention; unavailable authority SHALL NOT authorize fallback bypass.

**Source role:** Platform operations. **Original design references:** RA §14; RA §27.

**Enforcement location:** Service catalogue, measured surviving resource pools, security-edge and dependency failure/maintenance behaviour.

**Delivery disposition:** `EXTERNAL_CAPACITY_AND_QUALIFICATION_REQUIRED`.

**Related code/procedure:** [docs/engineering/TAD.md](../engineering/TAD.md) · [lab/run_namespace_lab.py](../../lab/run_namespace_lab.py). These artifacts do not individually or collectively establish the entire requirement.

**Current evidence limit:** SOURCE_AND_LOCAL_FIXTURE_ONLY_OR_NOT_IMPLEMENTED; NOT_NATIVE_QUALIFIED. Actual native evidence is not supplied.

**Outstanding dependency:** Illustrative capacity schedules and local link-failure fixtures do not establish measured production SLO/RTO/RPO, qualified limits, complete reservations or procured-to-available inventory.

| Assertion | Exact source focus | Required site-specific completion |
| --- | --- | --- |
| FAIL-003/A01 | Every critical dependency SHALL have a qualified loss/partition/recovery behavior, including credential/key continuity, logging loss, state recovery and split-brain prevention | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |
| FAIL-003/A02 | unavailable authority SHALL NOT authorize fallback bypass. | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |

**Verification:** [CT-027](test-specifications.md#CT-027) · [CT-038](test-specifications.md#CT-038) · [CT-044](test-specifications.md#CT-044) · [CT-050](test-specifications.md#CT-050) · [CT-054](test-specifications.md#CT-054) · [CT-055](test-specifications.md#CT-055). Apply the referenced procedure to the actual enforcement location and this focus; include effective negative/failure observations where the original criterion requires them.

**Applicability and acceptance:** TO_BE_DECIDED_FOR_ACTUAL_SERVICE; NOT_AUTO_NA. The accountable project role records applicability, configuration and evidence; this reusable allocation does not invent those decisions.

<a id="REC-001"></a>
## REC-001

Recovery procedures SHALL include independent bootstrap access, protected key/state/catalog recovery, dependency ordering, writer fencing, isolated validation and attributable activation authority.

**Source role:** Continuity management. **Original design references:** RA §21; RA §27.

**Enforcement location:** Backup management and data endpoints, protected-copy authority, catalogues/keys and isolated restore target.

**Delivery disposition:** `EXTERNAL_PROTECTION_SERVICE_REQUIRED`.

**Related code/procedure:** [docs/operations/README.md](../operations/README.md) · [sources/implementation_backlog.csv](../../sources/implementation_backlog.csv). These artifacts do not individually or collectively establish the entire requirement.

**Current evidence limit:** SOURCE_AND_LOCAL_FIXTURE_ONLY_OR_NOT_IMPLEMENTED; NOT_NATIVE_QUALIFIED. Actual native evidence is not supplied.

**Outstanding dependency:** No complete native backup/KMS/catalogue integration, independent deletion control, measured application-consistent restore or retention-aware release is supplied.

| Assertion | Exact source focus | Required site-specific completion |
| --- | --- | --- |
| REC-001/A01 | Recovery procedures SHALL include independent bootstrap access, protected key/state/catalog recovery, dependency ordering, writer fencing, isolated validation and attributable activation authority. | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |

**Verification:** [CT-052](test-specifications.md#CT-052) · [CT-054](test-specifications.md#CT-054) · [CT-055](test-specifications.md#CT-055). Apply the referenced procedure to the actual enforcement location and this focus; include effective negative/failure observations where the original criterion requires them.

**Applicability and acceptance:** TO_BE_DECIDED_FOR_ACTUAL_SERVICE; NOT_AUTO_NA. The accountable project role records applicability, configuration and evidence; this reusable allocation does not invent those decisions.

<a id="REC-002"></a>
## REC-002

Recovery and failback exercises SHALL measure actual service RTO/RPO, data consistency and security outcomes and SHALL remove temporary routes, grants and exposures after authorized completion.

**Source role:** Continuity management. **Original design references:** RA §21; RA §27.

**Enforcement location:** Backup management and data endpoints, protected-copy authority, catalogues/keys and isolated restore target.

**Delivery disposition:** `EXTERNAL_PROTECTION_SERVICE_REQUIRED`.

**Related code/procedure:** [docs/operations/README.md](../operations/README.md) · [sources/implementation_backlog.csv](../../sources/implementation_backlog.csv). These artifacts do not individually or collectively establish the entire requirement.

**Current evidence limit:** SOURCE_AND_LOCAL_FIXTURE_ONLY_OR_NOT_IMPLEMENTED; NOT_NATIVE_QUALIFIED. Actual native evidence is not supplied.

**Outstanding dependency:** No complete native backup/KMS/catalogue integration, independent deletion control, measured application-consistent restore or retention-aware release is supplied.

| Assertion | Exact source focus | Required site-specific completion |
| --- | --- | --- |
| REC-002/A01 | Recovery and failback exercises SHALL measure actual service RTO/RPO, data consistency and security outcomes and SHALL remove temporary routes, grants and exposures after authorized completion. | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |

**Verification:** [CT-052](test-specifications.md#CT-052) · [CT-054](test-specifications.md#CT-054) · [CT-055](test-specifications.md#CT-055) · [CT-060](test-specifications.md#CT-060). Apply the referenced procedure to the actual enforcement location and this focus; include effective negative/failure observations where the original criterion requires them.

**Applicability and acceptance:** TO_BE_DECIDED_FOR_ACTUAL_SERVICE; NOT_AUTO_NA. The accountable project role records applicability, configuration and evidence; this reusable allocation does not invent those decisions.

<a id="VULN-001"></a>
## VULN-001

All platform and automation assets SHALL have version/support inventory, vulnerability ownership, risk-based remediation targets, exception handling and retirement decisions.

**Source role:** Vulnerability management. **Original design references:** RA §25.

**Enforcement location:** Approved image registry, artifact signature/digest policy and native guest/platform hardening configuration.

**Delivery disposition:** `EXTERNAL_IMAGE_AND_BASELINE_SERVICE_REQUIRED`.

**Related code/procedure:** [terraform/modules/nutanix-workload/main.tf.json](../../terraform/modules/nutanix-workload/main.tf.json) · [terraform/modules/vsphere-workload/main.tf.json](../../terraform/modules/vsphere-workload/main.tf.json) · [terraform/modules/openstack-workload/main.tf.json](../../terraform/modules/openstack-workload/main.tf.json). These artifacts do not individually or collectively establish the entire requirement.

**Current evidence limit:** SOURCE_AND_LOCAL_FIXTURE_ONLY_OR_NOT_IMPLEMENTED; NOT_NATIVE_QUALIFIED. Actual native evidence is not supplied.

**Outstanding dependency:** Modules consume image/template references; a governed image catalogue, provenance/revocation/hardening agents, vulnerability disposition and runtime guest compliance are not implemented.

| Assertion | Exact source focus | Required site-specific completion |
| --- | --- | --- |
| VULN-001/A01 | All platform and automation assets SHALL have version/support inventory, vulnerability ownership, risk-based remediation targets, exception handling and retirement decisions. | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |

**Verification:** [CT-041](test-specifications.md#CT-041) · [CT-042](test-specifications.md#CT-042) · [CT-074](test-specifications.md#CT-074). Apply the referenced procedure to the actual enforcement location and this focus; include effective negative/failure observations where the original criterion requires them.

**Applicability and acceptance:** TO_BE_DECIDED_FOR_ACTUAL_SERVICE; NOT_AUTO_NA. The accountable project role records applicability, configuration and evidence; this reusable allocation does not invent those decisions.

<a id="VULN-002"></a>
## VULN-002

Security updates SHALL use trusted artifacts, compatibility/regression evidence, phased promotion and a tested recovery strategy; unsupported or vulnerable templates SHALL be controlled at new-deployment admission.

**Source role:** Platform engineering. **Original design references:** RA §25.

**Enforcement location:** Approved image registry, artifact signature/digest policy and native guest/platform hardening configuration.

**Delivery disposition:** `EXTERNAL_IMAGE_AND_BASELINE_SERVICE_REQUIRED`.

**Related code/procedure:** [terraform/modules/nutanix-workload/main.tf.json](../../terraform/modules/nutanix-workload/main.tf.json) · [terraform/modules/vsphere-workload/main.tf.json](../../terraform/modules/vsphere-workload/main.tf.json) · [terraform/modules/openstack-workload/main.tf.json](../../terraform/modules/openstack-workload/main.tf.json). These artifacts do not individually or collectively establish the entire requirement.

**Current evidence limit:** SOURCE_AND_LOCAL_FIXTURE_ONLY_OR_NOT_IMPLEMENTED; NOT_NATIVE_QUALIFIED. Actual native evidence is not supplied.

**Outstanding dependency:** Modules consume image/template references; a governed image catalogue, provenance/revocation/hardening agents, vulnerability disposition and runtime guest compliance are not implemented.

| Assertion | Exact source focus | Required site-specific completion |
| --- | --- | --- |
| VULN-002/A01 | Security updates SHALL use trusted artifacts, compatibility/regression evidence, phased promotion and a tested recovery strategy | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |
| VULN-002/A02 | unsupported or vulnerable templates SHALL be controlled at new-deployment admission. | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |

**Verification:** [CT-015](test-specifications.md#CT-015) · [CT-040](test-specifications.md#CT-040) · [CT-041](test-specifications.md#CT-041) · [CT-042](test-specifications.md#CT-042). Apply the referenced procedure to the actual enforcement location and this focus; include effective negative/failure observations where the original criterion requires them.

**Applicability and acceptance:** TO_BE_DECIDED_FOR_ACTUAL_SERVICE; NOT_AUTO_NA. The accountable project role records applicability, configuration and evidence; this reusable allocation does not invent those decisions.

<a id="IR-001"></a>
## IR-001

Emergency containment SHALL be possible without requiring a physical-fabric redesign or broad outage to unrelated tenants.

**Source role:** Incident response. **Original design references:** RA §25; RA §27.

**Enforcement location:** Effective native runtime, incident owner and separately authorized current-generation recovery/repair process.

**Delivery disposition:** `PARTIAL_READBACK_REVIEW_NO_REPAIR`.

**Related code/procedure:** [tools/recovery_review.py](../../tools/recovery_review.py) · [tools/nsx_observe.py](../../tools/nsx_observe.py) · [tools/nutanix_observe.py](../../tools/nutanix_observe.py) · [tools/neutron_observe.py](../../tools/neutron_observe.py). These artifacts do not individually or collectively establish the entire requirement.

**Current evidence limit:** SOURCE_AND_LOCAL_FIXTURE_ONLY_OR_NOT_IMPLEMENTED; NOT_NATIVE_QUALIFIED. Actual native evidence is not supplied.

**Outstanding dependency:** Exact-resource reads and offline decisions do not cover complete platform inventory, continuously detect all drift, authenticate incident authority, enforce real fencing or carry out safe native containment/repair.

| Assertion | Exact source focus | Required site-specific completion |
| --- | --- | --- |
| IR-001/A01 | Emergency containment SHALL be possible without requiring a physical-fabric redesign or broad outage to unrelated tenants. | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |

**Verification:** [CT-057](test-specifications.md#CT-057) · [CT-067](test-specifications.md#CT-067). Apply the referenced procedure to the actual enforcement location and this focus; include effective negative/failure observations where the original criterion requires them.

**Applicability and acceptance:** TO_BE_DECIDED_FOR_ACTUAL_SERVICE; NOT_AUTO_NA. The accountable project role records applicability, configuration and evidence; this reusable allocation does not invent those decisions.

<a id="IR-002"></a>
## IR-002

Incident procedures SHALL define authority, scoped containment, evidence custody, coordination, recovery acceptance and reconciliation of emergency changes; containment release SHALL be explicit and attributable.

**Source role:** Incident response. **Original design references:** RA §25; RA §27.

**Enforcement location:** Effective native runtime, incident owner and separately authorized current-generation recovery/repair process.

**Delivery disposition:** `PARTIAL_READBACK_REVIEW_NO_REPAIR`.

**Related code/procedure:** [tools/recovery_review.py](../../tools/recovery_review.py) · [tools/nsx_observe.py](../../tools/nsx_observe.py) · [tools/nutanix_observe.py](../../tools/nutanix_observe.py) · [tools/neutron_observe.py](../../tools/neutron_observe.py). These artifacts do not individually or collectively establish the entire requirement.

**Current evidence limit:** SOURCE_AND_LOCAL_FIXTURE_ONLY_OR_NOT_IMPLEMENTED; NOT_NATIVE_QUALIFIED. Actual native evidence is not supplied.

**Outstanding dependency:** Exact-resource reads and offline decisions do not cover complete platform inventory, continuously detect all drift, authenticate incident authority, enforce real fencing or carry out safe native containment/repair.

| Assertion | Exact source focus | Required site-specific completion |
| --- | --- | --- |
| IR-002/A01 | Incident procedures SHALL define authority, scoped containment, evidence custody, coordination, recovery acceptance and reconciliation of emergency changes | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |
| IR-002/A02 | containment release SHALL be explicit and attributable. | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |

**Verification:** [CT-049](test-specifications.md#CT-049) · [CT-057](test-specifications.md#CT-057) · [CT-058](test-specifications.md#CT-058) · [CT-066](test-specifications.md#CT-066). Apply the referenced procedure to the actual enforcement location and this focus; include effective negative/failure observations where the original criterion requires them.

**Applicability and acceptance:** TO_BE_DECIDED_FOR_ACTUAL_SERVICE; NOT_AUTO_NA. The accountable project role records applicability, configuration and evidence; this reusable allocation does not invent those decisions.

<a id="LIFE-001"></a>
## LIFE-001

Offboarding SHALL remove obsolete routes and policy objects and SHALL produce evidence of completion.

**Source role:** Service management. **Original design references:** RA §27.

**Enforcement location:** Storage/controller authorization, snapshot/clone/export lineage, retained copies, keys and media sanitization services.

**Delivery disposition:** `PARTIAL_RESOURCE_CREATION_EXTERNAL_LIFECYCLE`.

**Related code/procedure:** [terraform/modules/nutanix-workload/main.tf.json](../../terraform/modules/nutanix-workload/main.tf.json) · [terraform/modules/openstack-workload/main.tf.json](../../terraform/modules/openstack-workload/main.tf.json) · [docs/DNS_LIFECYCLE.md](../DNS_LIFECYCLE.md). These artifacts do not individually or collectively establish the entire requirement.

**Current evidence limit:** SOURCE_AND_LOCAL_FIXTURE_ONLY_OR_NOT_IMPLEMENTED; NOT_NATIVE_QUALIFIED. Actual native evidence is not supplied.

**Outstanding dependency:** Boot/data volume references and DNS retirement do not implement complete copy inventory, cross-owner export authorization, retention/hold policy, sanitization, receipt or safe shared-resource deletion.

| Assertion | Exact source focus | Required site-specific completion |
| --- | --- | --- |
| LIFE-001/A01 | Offboarding SHALL remove obsolete routes and policy objects and SHALL produce evidence of completion. | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |

**Verification:** [CT-013](test-specifications.md#CT-013) · [CT-059](test-specifications.md#CT-059) · [CT-070](test-specifications.md#CT-070). Apply the referenced procedure to the actual enforcement location and this focus; include effective negative/failure observations where the original criterion requires them.

**Applicability and acceptance:** TO_BE_DECIDED_FOR_ACTUAL_SERVICE; NOT_AUTO_NA. The accountable project role records applicability, configuration and evidence; this reusable allocation does not invent those decisions.

<a id="LIFE-002"></a>
## LIFE-002

Retirement SHALL distinguish live-service removal from retained-data obligations and SHALL verify identity, DNS, route, policy, attachment, copy and key lifecycle without deleting shared or held resources.

**Source role:** Service management. **Original design references:** RA §27.

**Enforcement location:** Storage/controller authorization, snapshot/clone/export lineage, retained copies, keys and media sanitization services.

**Delivery disposition:** `PARTIAL_RESOURCE_CREATION_EXTERNAL_LIFECYCLE`.

**Related code/procedure:** [terraform/modules/nutanix-workload/main.tf.json](../../terraform/modules/nutanix-workload/main.tf.json) · [terraform/modules/openstack-workload/main.tf.json](../../terraform/modules/openstack-workload/main.tf.json) · [docs/DNS_LIFECYCLE.md](../DNS_LIFECYCLE.md). These artifacts do not individually or collectively establish the entire requirement.

**Current evidence limit:** SOURCE_AND_LOCAL_FIXTURE_ONLY_OR_NOT_IMPLEMENTED; NOT_NATIVE_QUALIFIED. Actual native evidence is not supplied.

**Outstanding dependency:** Boot/data volume references and DNS retirement do not implement complete copy inventory, cross-owner export authorization, retention/hold policy, sanitization, receipt or safe shared-resource deletion.

| Assertion | Exact source focus | Required site-specific completion |
| --- | --- | --- |
| LIFE-002/A01 | live-service removal | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |
| LIFE-002/A02 | retained-data obligations | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |
| LIFE-002/A03 | identity | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |
| LIFE-002/A04 | DNS | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |
| LIFE-002/A05 | route | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |
| LIFE-002/A06 | policy | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |
| LIFE-002/A07 | attachment | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |
| LIFE-002/A08 | copy | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |
| LIFE-002/A09 | key lifecycle | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |

**Verification:** [CT-013](test-specifications.md#CT-013) · [CT-053](test-specifications.md#CT-053) · [CT-059](test-specifications.md#CT-059) · [CT-070](test-specifications.md#CT-070) · [CT-078](test-specifications.md#CT-078). Apply the referenced procedure to the actual enforcement location and this focus; include effective negative/failure observations where the original criterion requires them.

**Applicability and acceptance:** TO_BE_DECIDED_FOR_ACTUAL_SERVICE; NOT_AUTO_NA. The accountable project role records applicability, configuration and evidence; this reusable allocation does not invent those decisions.

<a id="LIFE-003"></a>
## LIFE-003

Sanitization SHALL use an approved media-appropriate method with copy/key-scope evidence; deletion of a resource record SHALL NOT alone constitute proof of data destruction.

**Source role:** Data owner. **Original design references:** RA §27.

**Enforcement location:** Storage/controller authorization, snapshot/clone/export lineage, retained copies, keys and media sanitization services.

**Delivery disposition:** `PARTIAL_RESOURCE_CREATION_EXTERNAL_LIFECYCLE`.

**Related code/procedure:** [terraform/modules/nutanix-workload/main.tf.json](../../terraform/modules/nutanix-workload/main.tf.json) · [terraform/modules/openstack-workload/main.tf.json](../../terraform/modules/openstack-workload/main.tf.json) · [docs/DNS_LIFECYCLE.md](../DNS_LIFECYCLE.md). These artifacts do not individually or collectively establish the entire requirement.

**Current evidence limit:** SOURCE_AND_LOCAL_FIXTURE_ONLY_OR_NOT_IMPLEMENTED; NOT_NATIVE_QUALIFIED. Actual native evidence is not supplied.

**Outstanding dependency:** Boot/data volume references and DNS retirement do not implement complete copy inventory, cross-owner export authorization, retention/hold policy, sanitization, receipt or safe shared-resource deletion.

| Assertion | Exact source focus | Required site-specific completion |
| --- | --- | --- |
| LIFE-003/A01 | Sanitization SHALL use an approved media-appropriate method with copy/key-scope evidence | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |
| LIFE-003/A02 | deletion of a resource record SHALL NOT alone constitute proof of data destruction. | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |

**Verification:** [CT-053](test-specifications.md#CT-053) · [CT-059](test-specifications.md#CT-059). Apply the referenced procedure to the actual enforcement location and this focus; include effective negative/failure observations where the original criterion requires them.

**Applicability and acceptance:** TO_BE_DECIDED_FOR_ACTUAL_SERVICE; NOT_AUTO_NA. The accountable project role records applicability, configuration and evidence; this reusable allocation does not invent those decisions.

<a id="MIG-001"></a>
## MIG-001

Migration connectivity SHALL be time-bound unless explicitly converted to an approved steady-state connection.

**Source role:** Migration owner. **Original design references:** RA §27.

**Enforcement location:** Accepted temporary transfer interfaces, data-consistency/writer fencing and identity/DNS/route cutover.

**Delivery disposition:** `DOCUMENTED_TRANSITION_NATIVE_EXECUTION_OPEN`.

**Related code/procedure:** [tools/recovery_review.py](../../tools/recovery_review.py) · [docs/DNS_LIFECYCLE.md](../DNS_LIFECYCLE.md). These artifacts do not individually or collectively establish the entire requirement.

**Current evidence limit:** SOURCE_AND_LOCAL_FIXTURE_ONLY_OR_NOT_IMPLEMENTED; NOT_NATIVE_QUALIFIED. Actual native evidence is not supplied.

**Outstanding dependency:** Neither DNS changes nor readback performs complete cross-platform state transfer, native writer fencing, application consistency, reverse synchronization or transition teardown.

| Assertion | Exact source focus | Required site-specific completion |
| --- | --- | --- |
| MIG-001/A01 | Migration connectivity SHALL be time-bound unless explicitly converted to an approved steady-state connection. | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |

**Verification:** [CT-058](test-specifications.md#CT-058) · [CT-060](test-specifications.md#CT-060) · [CT-076](test-specifications.md#CT-076). Apply the referenced procedure to the actual enforcement location and this focus; include effective negative/failure observations where the original criterion requires them.

**Applicability and acceptance:** TO_BE_DECIDED_FOR_ACTUAL_SERVICE; NOT_AUTO_NA. The accountable project role records applicability, configuration and evidence; this reusable allocation does not invent those decisions.

<a id="MIG-002"></a>
## MIG-002

Migration flows SHALL traverse an approved security edge when they cross security-domain boundaries.

**Source role:** Migration owner. **Original design references:** RA §27.

**Enforcement location:** Accepted temporary transfer interfaces, data-consistency/writer fencing and identity/DNS/route cutover.

**Delivery disposition:** `DOCUMENTED_TRANSITION_NATIVE_EXECUTION_OPEN`.

**Related code/procedure:** [tools/recovery_review.py](../../tools/recovery_review.py) · [docs/DNS_LIFECYCLE.md](../DNS_LIFECYCLE.md). These artifacts do not individually or collectively establish the entire requirement.

**Current evidence limit:** SOURCE_AND_LOCAL_FIXTURE_ONLY_OR_NOT_IMPLEMENTED; NOT_NATIVE_QUALIFIED. Actual native evidence is not supplied.

**Outstanding dependency:** Neither DNS changes nor readback performs complete cross-platform state transfer, native writer fencing, application consistency, reverse synchronization or transition teardown.

| Assertion | Exact source focus | Required site-specific completion |
| --- | --- | --- |
| MIG-002/A01 | Migration flows SHALL traverse an approved security edge when they cross security-domain boundaries. | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |

**Verification:** [CT-003](test-specifications.md#CT-003) · [CT-060](test-specifications.md#CT-060). Apply the referenced procedure to the actual enforcement location and this focus; include effective negative/failure observations where the original criterion requires them.

**Applicability and acceptance:** TO_BE_DECIDED_FOR_ACTUAL_SERVICE; NOT_AUTO_NA. The accountable project role records applicability, configuration and evidence; this reusable allocation does not invent those decisions.

<a id="MIG-003"></a>
## MIG-003

Migration and exit rehearsals SHALL validate data/application consistency, identity/key dependencies, equivalent security outcomes, fencing/cutover, rollback feasibility and complete transition teardown.

**Source role:** Migration owner. **Original design references:** RA §27.

**Enforcement location:** Accepted temporary transfer interfaces, data-consistency/writer fencing and identity/DNS/route cutover.

**Delivery disposition:** `DOCUMENTED_TRANSITION_NATIVE_EXECUTION_OPEN`.

**Related code/procedure:** [tools/recovery_review.py](../../tools/recovery_review.py) · [docs/DNS_LIFECYCLE.md](../DNS_LIFECYCLE.md). These artifacts do not individually or collectively establish the entire requirement.

**Current evidence limit:** SOURCE_AND_LOCAL_FIXTURE_ONLY_OR_NOT_IMPLEMENTED; NOT_NATIVE_QUALIFIED. Actual native evidence is not supplied.

**Outstanding dependency:** Neither DNS changes nor readback performs complete cross-platform state transfer, native writer fencing, application consistency, reverse synchronization or transition teardown.

| Assertion | Exact source focus | Required site-specific completion |
| --- | --- | --- |
| MIG-003/A01 | data/application consistency | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |
| MIG-003/A02 | identity/key dependencies | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |
| MIG-003/A03 | equivalent security outcomes | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |
| MIG-003/A04 | fencing/cutover | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |
| MIG-003/A05 | rollback feasibility | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |
| MIG-003/A06 | transition teardown | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |

**Verification:** [CT-054](test-specifications.md#CT-054) · [CT-060](test-specifications.md#CT-060) · [CT-073](test-specifications.md#CT-073) · [CT-078](test-specifications.md#CT-078). Apply the referenced procedure to the actual enforcement location and this focus; include effective negative/failure observations where the original criterion requires them.

**Applicability and acceptance:** TO_BE_DECIDED_FOR_ACTUAL_SERVICE; NOT_AUTO_NA. The accountable project role records applicability, configuration and evidence; this reusable allocation does not invent those decisions.

<a id="OPS-001"></a>
## OPS-001

Each service SHALL publish a provider/tenant/shared control responsibility matrix and accountable decision owners for its complete lifecycle, including inherited controls, support access and data disposal.

**Source role:** Service management. **Original design references:** RA §20; RA §26.

**Enforcement location:** Architecture/security/service-owner review and controlled evidence/exception record systems.

**Delivery disposition:** `EXTERNAL_GOVERNANCE_OR_MANUAL_CONTROL`.

**Related code/procedure:** [docs/DOCUMENTATION_MIGRATION.md](../DOCUMENTATION_MIGRATION.md) · [docs/assurance/requirements.md](requirements.md). These artifacts do not individually or collectively establish the entire requirement.

**Current evidence limit:** SOURCE_AND_LOCAL_FIXTURE_ONLY_OR_NOT_IMPLEMENTED; NOT_NATIVE_QUALIFIED. Actual native evidence is not supplied.

**Outstanding dependency:** Actual deciding authority, jurisdiction, applicability, issued approval, operating evidence and exception expiry handling must be supplied by the service owner; Git labels and test passes cannot issue them.

| Assertion | Exact source focus | Required site-specific completion |
| --- | --- | --- |
| OPS-001/A01 | Each service SHALL publish a provider/tenant/shared control responsibility matrix and accountable decision owners for its complete lifecycle, including inherited controls, support access and data disposal. | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |

**Verification:** [CT-019](test-specifications.md#CT-019) · [CT-062](test-specifications.md#CT-062) · [CT-079](test-specifications.md#CT-079). Apply the referenced procedure to the actual enforcement location and this focus; include effective negative/failure observations where the original criterion requires them.

**Applicability and acceptance:** TO_BE_DECIDED_FOR_ACTUAL_SERVICE; NOT_AUTO_NA. The accountable project role records applicability, configuration and evidence; this reusable allocation does not invent those decisions.

<a id="OPS-002"></a>
## OPS-002

Production handover SHALL include owner/escalation, dependency, SLO/recovery, capacity, monitoring, runbook, support/version and evidence records; privileged access SHALL be reviewed against the actual authority model.

**Source role:** Service management. **Original design references:** RA §20; RA §26.

**Enforcement location:** Architecture/security/service-owner review and controlled evidence/exception record systems.

**Delivery disposition:** `EXTERNAL_GOVERNANCE_OR_MANUAL_CONTROL`.

**Related code/procedure:** [docs/DOCUMENTATION_MIGRATION.md](../DOCUMENTATION_MIGRATION.md) · [docs/assurance/requirements.md](requirements.md). These artifacts do not individually or collectively establish the entire requirement.

**Current evidence limit:** SOURCE_AND_LOCAL_FIXTURE_ONLY_OR_NOT_IMPLEMENTED; NOT_NATIVE_QUALIFIED. Actual native evidence is not supplied.

**Outstanding dependency:** Actual deciding authority, jurisdiction, applicability, issued approval, operating evidence and exception expiry handling must be supplied by the service owner; Git labels and test passes cannot issue them.

| Assertion | Exact source focus | Required site-specific completion |
| --- | --- | --- |
| OPS-002/A01 | Production handover SHALL include owner/escalation, dependency, SLO/recovery, capacity, monitoring, runbook, support/version and evidence records | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |
| OPS-002/A02 | privileged access SHALL be reviewed against the actual authority model. | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |

**Verification:** [CT-019](test-specifications.md#CT-019) · [CT-062](test-specifications.md#CT-062) · [CT-069](test-specifications.md#CT-069). Apply the referenced procedure to the actual enforcement location and this focus; include effective negative/failure observations where the original criterion requires them.

**Applicability and acceptance:** TO_BE_DECIDED_FOR_ACTUAL_SERVICE; NOT_AUTO_NA. The accountable project role records applicability, configuration and evidence; this reusable allocation does not invent those decisions.

<a id="EXC-001"></a>
## EXC-001

Every exception SHALL have an accountable risk owner and expiry or review date.

**Source role:** Risk owner. **Original design references:** RA §25.

**Enforcement location:** Architecture/security/service-owner review and controlled evidence/exception record systems.

**Delivery disposition:** `EXTERNAL_GOVERNANCE_OR_MANUAL_CONTROL`.

**Related code/procedure:** [docs/DOCUMENTATION_MIGRATION.md](../DOCUMENTATION_MIGRATION.md) · [docs/assurance/requirements.md](requirements.md). These artifacts do not individually or collectively establish the entire requirement.

**Current evidence limit:** SOURCE_AND_LOCAL_FIXTURE_ONLY_OR_NOT_IMPLEMENTED; NOT_NATIVE_QUALIFIED. Actual native evidence is not supplied.

**Outstanding dependency:** Actual deciding authority, jurisdiction, applicability, issued approval, operating evidence and exception expiry handling must be supplied by the service owner; Git labels and test passes cannot issue them.

| Assertion | Exact source focus | Required site-specific completion |
| --- | --- | --- |
| EXC-001/A01 | Every exception SHALL have an accountable risk owner and expiry or review date. | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |

**Verification:** [CT-058](test-specifications.md#CT-058) · [CT-062](test-specifications.md#CT-062). Apply the referenced procedure to the actual enforcement location and this focus; include effective negative/failure observations where the original criterion requires them.

**Applicability and acceptance:** TO_BE_DECIDED_FOR_ACTUAL_SERVICE; NOT_AUTO_NA. The accountable project role records applicability, configuration and evidence; this reusable allocation does not invent those decisions.

<a id="EXC-002"></a>
## EXC-002

The control plane SHALL surface expired exceptions as non-compliant state rather than allowing them to become permanent undocumented architecture.

**Source role:** Risk owner. **Original design references:** RA §25.

**Enforcement location:** Architecture/security/service-owner review and controlled evidence/exception record systems.

**Delivery disposition:** `EXTERNAL_GOVERNANCE_OR_MANUAL_CONTROL`.

**Related code/procedure:** [docs/DOCUMENTATION_MIGRATION.md](../DOCUMENTATION_MIGRATION.md) · [docs/assurance/requirements.md](requirements.md). These artifacts do not individually or collectively establish the entire requirement.

**Current evidence limit:** SOURCE_AND_LOCAL_FIXTURE_ONLY_OR_NOT_IMPLEMENTED; NOT_NATIVE_QUALIFIED. Actual native evidence is not supplied.

**Outstanding dependency:** Actual deciding authority, jurisdiction, applicability, issued approval, operating evidence and exception expiry handling must be supplied by the service owner; Git labels and test passes cannot issue them.

| Assertion | Exact source focus | Required site-specific completion |
| --- | --- | --- |
| EXC-002/A01 | The control plane SHALL surface expired exceptions as non-compliant state rather than allowing them to become permanent undocumented architecture. | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |

**Verification:** [CT-058](test-specifications.md#CT-058) · [CT-069](test-specifications.md#CT-069). Apply the referenced procedure to the actual enforcement location and this focus; include effective negative/failure observations where the original criterion requires them.

**Applicability and acceptance:** TO_BE_DECIDED_FOR_ACTUAL_SERVICE; NOT_AUTO_NA. The accountable project role records applicability, configuration and evidence; this reusable allocation does not invent those decisions.

<a id="EXC-003"></a>
## EXC-003

Exceptions SHALL bind requirement IDs, precise scope, effective/expiry times, compensating controls and authorized risk approval; expiry handling SHALL preserve evidence and follow a pre-approved secure continuity/remediation decision.

**Source role:** Risk owner. **Original design references:** RA §25.

**Enforcement location:** Architecture/security/service-owner review and controlled evidence/exception record systems.

**Delivery disposition:** `EXTERNAL_GOVERNANCE_OR_MANUAL_CONTROL`.

**Related code/procedure:** [docs/DOCUMENTATION_MIGRATION.md](../DOCUMENTATION_MIGRATION.md) · [docs/assurance/requirements.md](requirements.md). These artifacts do not individually or collectively establish the entire requirement.

**Current evidence limit:** SOURCE_AND_LOCAL_FIXTURE_ONLY_OR_NOT_IMPLEMENTED; NOT_NATIVE_QUALIFIED. Actual native evidence is not supplied.

**Outstanding dependency:** Actual deciding authority, jurisdiction, applicability, issued approval, operating evidence and exception expiry handling must be supplied by the service owner; Git labels and test passes cannot issue them.

| Assertion | Exact source focus | Required site-specific completion |
| --- | --- | --- |
| EXC-003/A01 | Exceptions SHALL bind requirement IDs, precise scope, effective/expiry times, compensating controls and authorized risk approval | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |
| EXC-003/A02 | expiry handling SHALL preserve evidence and follow a pre-approved secure continuity/remediation decision. | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |

**Verification:** [CT-017](test-specifications.md#CT-017) · [CT-058](test-specifications.md#CT-058) · [CT-069](test-specifications.md#CT-069). Apply the referenced procedure to the actual enforcement location and this focus; include effective negative/failure observations where the original criterion requires them.

**Applicability and acceptance:** TO_BE_DECIDED_FOR_ACTUAL_SERVICE; NOT_AUTO_NA. The accountable project role records applicability, configuration and evidence; this reusable allocation does not invent those decisions.

<a id="ONB-001"></a>
## ONB-001

Onboarding SHALL verify ownership, complete intent/profiles, current qualification/authorization conditions, operational readiness and lifecycle obligations before Service Ready is granted.

**Source role:** Service management. **Original design references:** RA §23; RA §28.

**Enforcement location:** Architecture/security/service-owner review and controlled evidence/exception record systems.

**Delivery disposition:** `EXTERNAL_GOVERNANCE_OR_MANUAL_CONTROL`.

**Related code/procedure:** [docs/DOCUMENTATION_MIGRATION.md](../DOCUMENTATION_MIGRATION.md) · [docs/assurance/requirements.md](requirements.md). These artifacts do not individually or collectively establish the entire requirement.

**Current evidence limit:** SOURCE_AND_LOCAL_FIXTURE_ONLY_OR_NOT_IMPLEMENTED; NOT_NATIVE_QUALIFIED. Actual native evidence is not supplied.

**Outstanding dependency:** Actual deciding authority, jurisdiction, applicability, issued approval, operating evidence and exception expiry handling must be supplied by the service owner; Git labels and test passes cannot issue them.

| Assertion | Exact source focus | Required site-specific completion |
| --- | --- | --- |
| ONB-001/A01 | Onboarding SHALL verify ownership, complete intent/profiles, current qualification/authorization conditions, operational readiness and lifecycle obligations before Service Ready is granted. | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |

**Verification:** [CT-017](test-specifications.md#CT-017) · [CT-018](test-specifications.md#CT-018) · [CT-049](test-specifications.md#CT-049) · [CT-062](test-specifications.md#CT-062) · [CT-069](test-specifications.md#CT-069). Apply the referenced procedure to the actual enforcement location and this focus; include effective negative/failure observations where the original criterion requires them.

**Applicability and acceptance:** TO_BE_DECIDED_FOR_ACTUAL_SERVICE; NOT_AUTO_NA. The accountable project role records applicability, configuration and evidence; this reusable allocation does not invent those decisions.

<a id="DEL-001"></a>
## DEL-001

The reference implementation SHALL demonstrate two-tenant isolation, controlled zone transitions, protected management, service bindings, recovery and retirement on a qualified first platform before scale expansion.

**Source role:** Delivery owner. **Original design references:** RA §22; RA §30.

**Enforcement location:** Approved qualification campaign, independent observation and evidence store at declared versions/topology.

**Delivery disposition:** `LOCAL_FIXTURES_NOT_NATIVE_QUALIFICATION`.

**Related code/procedure:** [docs/assurance/test-specifications.md](test-specifications.md) · [lab/run_readback_lab.py](../../lab/run_readback_lab.py) · [lab/run_namespace_lab.py](../../lab/run_namespace_lab.py). These artifacts do not individually or collectively establish the entire requirement.

**Current evidence limit:** SOURCE_AND_LOCAL_FIXTURE_ONLY_OR_NOT_IMPLEMENTED; NOT_NATIVE_QUALIFIED. Actual native evidence is not supplied.

**Outstanding dependency:** Reference procedures, local fixtures and hashes do not create native evidence, immutable evidence custody, complete assertion coverage, platform qualification or authorization.

| Assertion | Exact source focus | Required site-specific completion |
| --- | --- | --- |
| DEL-001/A01 | The reference implementation SHALL demonstrate two-tenant isolation, controlled zone transitions, protected management, service bindings, recovery and retirement on a qualified first platform before scale expansion. | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |

**Verification:** [CT-001](test-specifications.md#CT-001) · [CT-003](test-specifications.md#CT-003) · [CT-004](test-specifications.md#CT-004) · [CT-008](test-specifications.md#CT-008) · [CT-013](test-specifications.md#CT-013) · [CT-052](test-specifications.md#CT-052) · [CT-069](test-specifications.md#CT-069). Apply the referenced procedure to the actual enforcement location and this focus; include effective negative/failure observations where the original criterion requires them.

**Applicability and acceptance:** TO_BE_DECIDED_FOR_ACTUAL_SERVICE; NOT_AUTO_NA. The accountable project role records applicability, configuration and evidence; this reusable allocation does not invent those decisions.

<a id="DEL-002"></a>
## DEL-002

Multi-platform portability claims SHALL be supported by the same intent/core conformance outcomes on at least two qualified implementations and by a representative data/application exit rehearsal.

**Source role:** Delivery owner. **Original design references:** RA §22; RA §30.

**Enforcement location:** Approved qualification campaign, independent observation and evidence store at declared versions/topology.

**Delivery disposition:** `LOCAL_FIXTURES_NOT_NATIVE_QUALIFICATION`.

**Related code/procedure:** [docs/assurance/test-specifications.md](test-specifications.md) · [lab/run_readback_lab.py](../../lab/run_readback_lab.py) · [lab/run_namespace_lab.py](../../lab/run_namespace_lab.py). These artifacts do not individually or collectively establish the entire requirement.

**Current evidence limit:** SOURCE_AND_LOCAL_FIXTURE_ONLY_OR_NOT_IMPLEMENTED; NOT_NATIVE_QUALIFIED. Actual native evidence is not supplied.

**Outstanding dependency:** Reference procedures, local fixtures and hashes do not create native evidence, immutable evidence custody, complete assertion coverage, platform qualification or authorization.

| Assertion | Exact source focus | Required site-specific completion |
| --- | --- | --- |
| DEL-002/A01 | Multi-platform portability claims SHALL be supported by the same intent/core conformance outcomes on at least two qualified implementations and by a representative data/application exit rehearsal. | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |

**Verification:** [CT-016](test-specifications.md#CT-016) · [CT-060](test-specifications.md#CT-060) · [CT-073](test-specifications.md#CT-073). Apply the referenced procedure to the actual enforcement location and this focus; include effective negative/failure observations where the original criterion requires them.

**Applicability and acceptance:** TO_BE_DECIDED_FOR_ACTUAL_SERVICE; NOT_AUTO_NA. The accountable project role records applicability, configuration and evidence; this reusable allocation does not invent those decisions.

<a id="ACPT-001"></a>
## ACPT-001

Production acceptance SHALL require current evidence for every applicable acceptance criterion, explicit exclusions and risk decisions, operational owner acceptance and a valid separately issued authorization decision.

**Source role:** Security authority. **Original design references:** RA §28; RA §30.

**Enforcement location:** Architecture/security/service-owner review and controlled evidence/exception record systems.

**Delivery disposition:** `EXTERNAL_GOVERNANCE_OR_MANUAL_CONTROL`.

**Related code/procedure:** [docs/DOCUMENTATION_MIGRATION.md](../DOCUMENTATION_MIGRATION.md) · [docs/assurance/requirements.md](requirements.md). These artifacts do not individually or collectively establish the entire requirement.

**Current evidence limit:** SOURCE_AND_LOCAL_FIXTURE_ONLY_OR_NOT_IMPLEMENTED; NOT_NATIVE_QUALIFIED. Actual native evidence is not supplied.

**Outstanding dependency:** Actual deciding authority, jurisdiction, applicability, issued approval, operating evidence and exception expiry handling must be supplied by the service owner; Git labels and test passes cannot issue them.

| Assertion | Exact source focus | Required site-specific completion |
| --- | --- | --- |
| ACPT-001/A01 | Production acceptance SHALL require current evidence for every applicable acceptance criterion, explicit exclusions and risk decisions, operational owner acceptance and a valid separately issued authorization decision. | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |

**Verification:** [CT-018](test-specifications.md#CT-018) · [CT-049](test-specifications.md#CT-049) · [CT-062](test-specifications.md#CT-062) · [CT-069](test-specifications.md#CT-069). Apply the referenced procedure to the actual enforcement location and this focus; include effective negative/failure observations where the original criterion requires them.

**Applicability and acceptance:** TO_BE_DECIDED_FOR_ACTUAL_SERVICE; NOT_AUTO_NA. The accountable project role records applicability, configuration and evidence; this reusable allocation does not invent those decisions.
