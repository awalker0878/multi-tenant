# Requirement catalogue — retained wording

The 194 statements below are transcribed from the retained delivery-kit requirement CSV. Source editions, applicability and execution status are not re-approved here. Requirement-to-code links are traceability, not a claim that every control is implemented.

[Original requirement register](../../reference/Portable_Hosting_Delivery_Kits_v1_1/04_Shared/requirements.csv) · [Test specification register](test-specifications.md)

<a id="ARCH-001"></a>
## ARCH-001

The hosting contract SHALL be vendor neutral and SHALL NOT require consumers to specify vendor-specific identifiers or topology objects.

| Source field | Retained value |
| --- | --- |
| Accountable role | Architecture authority |
| Parent sections | [RA §1](../architecture/reference/1-purpose-scope-and-architectural-authority.md) · [RA §2](../architecture/reference/2-design-drivers-and-selected-reference-pattern.md) · [RA §20](../architecture/reference/20-provisioning-model-and-infrastructure-work-packages.md) |
| Supplement homes | [GM §1](gap-map/1-document-family-scope-and-precedence.md) · [GM §2](gap-map/2-primary-knowledge-homes-and-cross-cutting-changes.md) · [PROV §1](../implementation/provisioning-strategy/1-provisioning-scopes-ownership-and-accepted-handoffs.md) |
| Source IDs | S00 |
| Wording disposition | Unchanged from v1.2 |
| Execution status | Specified, not executed by this release |
| Tests | [CT-016](test-specifications.md#CT-016) · [CT-017](test-specifications.md#CT-017) |

Related ADRs: [ADR-0003](../adr/0003-let-the-infrastructure-architecture-lead-the-tooling.md)

<a id="ARCH-002"></a>
## ARCH-002

Routine tenant and workload lifecycle operations SHOULD NOT require changes to physical leaf or spine configuration.

| Source field | Retained value |
| --- | --- |
| Accountable role | Architecture authority |
| Parent sections | [RA §1](../architecture/reference/1-purpose-scope-and-architectural-authority.md) · [RA §2](../architecture/reference/2-design-drivers-and-selected-reference-pattern.md) · [RA §20](../architecture/reference/20-provisioning-model-and-infrastructure-work-packages.md) |
| Supplement homes | [GM §1](gap-map/1-document-family-scope-and-precedence.md) · [GM §2](gap-map/2-primary-knowledge-homes-and-cross-cutting-changes.md) · [PROV §1](../implementation/provisioning-strategy/1-provisioning-scopes-ownership-and-accepted-handoffs.md) |
| Source IDs | S00 |
| Wording disposition | Unchanged from v1.2 |
| Execution status | Specified, not executed by this release |
| Tests | [CT-071](test-specifications.md#CT-071) · [CT-072](test-specifications.md#CT-072) |

Related ADRs: [ADR-0004](../adr/0004-scale-through-commissioned-hosting-cells-and-capacity-pools.md)

<a id="ARCH-003"></a>
## ARCH-003

All inter-zone paths SHALL be explicit and SHALL traverse the applicable ZIP/security edge.

| Source field | Retained value |
| --- | --- |
| Accountable role | Architecture authority |
| Parent sections | [RA §1](../architecture/reference/1-purpose-scope-and-architectural-authority.md) · [RA §2](../architecture/reference/2-design-drivers-and-selected-reference-pattern.md) · [RA §20](../architecture/reference/20-provisioning-model-and-infrastructure-work-packages.md) |
| Supplement homes | [GM §1](gap-map/1-document-family-scope-and-precedence.md) · [GM §2](gap-map/2-primary-knowledge-homes-and-cross-cutting-changes.md) · [PROV §1](../implementation/provisioning-strategy/1-provisioning-scopes-ownership-and-accepted-handoffs.md) |
| Source IDs | S00; S01; S02 |
| Wording disposition | Unchanged from v1.2 |
| Execution status | Specified, not executed by this release |
| Tests | [CT-003](test-specifications.md#CT-003) · [CT-025](test-specifications.md#CT-025) |

Related ADRs: [ADR-0006](../adr/0006-use-an-explicit-governed-zip-for-inter-domain-trust-transitions.md)

<a id="ARCH-004"></a>
## ARCH-004

Management/OOB traffic SHALL be separated from tenant operational traffic and SHALL have independently controlled access paths.

| Source field | Retained value |
| --- | --- |
| Accountable role | Architecture authority |
| Parent sections | [RA §1](../architecture/reference/1-purpose-scope-and-architectural-authority.md) · [RA §2](../architecture/reference/2-design-drivers-and-selected-reference-pattern.md) · [RA §20](../architecture/reference/20-provisioning-model-and-infrastructure-work-packages.md) |
| Supplement homes | [GM §1](gap-map/1-document-family-scope-and-precedence.md) · [GM §2](gap-map/2-primary-knowledge-homes-and-cross-cutting-changes.md) · [PROV §1](../implementation/provisioning-strategy/1-provisioning-scopes-ownership-and-accepted-handoffs.md) |
| Source IDs | S00; S01; S02 |
| Wording disposition | Unchanged from v1.2 |
| Execution status | Specified, not executed by this release |
| Tests | [CT-004](test-specifications.md#CT-004) · [CT-026](test-specifications.md#CT-026) |

Related ADRs: [ADR-0009](../adr/0009-separate-management-security-platform-control-and-oob-recovery.md)

<a id="SCOPE-001"></a>
## SCOPE-001

Every implementation SHALL publish its offered service classes, supported information categories, excluded capabilities and required qualification evidence before accepting a production request.

| Source field | Retained value |
| --- | --- |
| Accountable role | Architecture authority |
| Parent sections | [RA §1](../architecture/reference/1-purpose-scope-and-architectural-authority.md) · [RA §2](../architecture/reference/2-design-drivers-and-selected-reference-pattern.md) · [RA §20](../architecture/reference/20-provisioning-model-and-infrastructure-work-packages.md) |
| Supplement homes | [GM §1](gap-map/1-document-family-scope-and-precedence.md) · [GM §2](gap-map/2-primary-knowledge-homes-and-cross-cutting-changes.md) · [PROV §1](../implementation/provisioning-strategy/1-provisioning-scopes-ownership-and-accepted-handoffs.md) |
| Source IDs | S00 |
| Wording disposition | Unchanged from v1.2 |
| Execution status | Specified, not executed by this release |
| Tests | [CT-018](test-specifications.md#CT-018) · [CT-062](test-specifications.md#CT-062) |

<a id="INV-001"></a>
## INV-001

Tenant identity, security-zone identity, workload lifecycle, and platform realization are separate concepts.

| Source field | Retained value |
| --- | --- |
| Accountable role | Architecture authority |
| Parent sections | [RA §1](../architecture/reference/1-purpose-scope-and-architectural-authority.md) · [RA §28](../architecture/reference/28-architecture-acceptance-and-verification.md) |
| Supplement homes | [GM §1](gap-map/1-document-family-scope-and-precedence.md) · [QUAL §5](site-qualification/5-qualification-stages-applicability-and-evidence.md) · [QUAL §6](site-qualification/6-control-inheritance-assurance-and-organizational-interfaces.md) |
| Source IDs | S00 |
| Wording disposition | Unchanged from v1.2 |
| Execution status | Specified, not executed by this release |
| Tests | [CT-016](test-specifications.md#CT-016) · [CT-070](test-specifications.md#CT-070) |

Related ADRs: [ADR-0018](../adr/0018-separate-tenant-administration-wsd-lifecycle-and-domain-realization.md)

<a id="INV-002"></a>
## INV-002

A VPC, VRF, Tier-1 gateway, or Neutron router is an implementation mechanism, not the enterprise definition of a security zone.

| Source field | Retained value |
| --- | --- |
| Accountable role | Architecture authority |
| Parent sections | [RA §1](../architecture/reference/1-purpose-scope-and-architectural-authority.md) · [RA §28](../architecture/reference/28-architecture-acceptance-and-verification.md) |
| Supplement homes | [GM §1](gap-map/1-document-family-scope-and-precedence.md) · [QUAL §5](site-qualification/5-qualification-stages-applicability-and-evidence.md) · [QUAL §6](site-qualification/6-control-inheritance-assurance-and-organizational-interfaces.md) |
| Source IDs | S00 |
| Wording disposition | Unchanged from v1.2 |
| Execution status | Specified, not executed by this release |
| Tests | [CT-025](test-specifications.md#CT-025) · [CT-080](test-specifications.md#CT-080) |

<a id="INV-003"></a>
## INV-003

Routes are derived from authorized intent; workload owners do not provide arbitrary route tables, BGP peers, route targets, or prefix imports/exports.

| Source field | Retained value |
| --- | --- |
| Accountable role | Architecture authority |
| Parent sections | [RA §1](../architecture/reference/1-purpose-scope-and-architectural-authority.md) · [RA §28](../architecture/reference/28-architecture-acceptance-and-verification.md) |
| Supplement homes | [GM §1](gap-map/1-document-family-scope-and-precedence.md) · [QUAL §5](site-qualification/5-qualification-stages-applicability-and-evidence.md) · [QUAL §6](site-qualification/6-control-inheritance-assurance-and-organizational-interfaces.md) |
| Source IDs | S00 |
| Wording disposition | Unchanged from v1.2 |
| Execution status | Specified, not executed by this release |
| Tests | [CT-009](test-specifications.md#CT-009) · [CT-033](test-specifications.md#CT-033) |

<a id="INV-004"></a>
## INV-004

Shared services are exposed through explicit service bindings; broad reachability to a common-services supernet is not the default.

| Source field | Retained value |
| --- | --- |
| Accountable role | Architecture authority |
| Parent sections | [RA §1](../architecture/reference/1-purpose-scope-and-architectural-authority.md) · [RA §28](../architecture/reference/28-architecture-acceptance-and-verification.md) |
| Supplement homes | [GM §1](gap-map/1-document-family-scope-and-precedence.md) · [QUAL §5](site-qualification/5-qualification-stages-applicability-and-evidence.md) · [QUAL §6](site-qualification/6-control-inheritance-assurance-and-organizational-interfaces.md) |
| Source IDs | S00 |
| Wording disposition | Unchanged from v1.2 |
| Execution status | Specified, not executed by this release |
| Tests | [CT-008](test-specifications.md#CT-008) |

<a id="INV-005"></a>
## INV-005

Portability means equivalent required outcomes and conformance, not identical topology.

| Source field | Retained value |
| --- | --- |
| Accountable role | Architecture authority |
| Parent sections | [RA §1](../architecture/reference/1-purpose-scope-and-architectural-authority.md) · [RA §28](../architecture/reference/28-architecture-acceptance-and-verification.md) |
| Supplement homes | [GM §1](gap-map/1-document-family-scope-and-precedence.md) · [QUAL §5](site-qualification/5-qualification-stages-applicability-and-evidence.md) · [QUAL §6](site-qualification/6-control-inheritance-assurance-and-organizational-interfaces.md) |
| Source IDs | S00 |
| Wording disposition | Unchanged from v1.2 |
| Execution status | Specified, not executed by this release |
| Tests | [CT-016](test-specifications.md#CT-016) · [CT-060](test-specifications.md#CT-060) |

<a id="INV-006"></a>
## INV-006

A deployment is not Service Ready until realized state and security controls are verified.

| Source field | Retained value |
| --- | --- |
| Accountable role | Architecture authority |
| Parent sections | [RA §1](../architecture/reference/1-purpose-scope-and-architectural-authority.md) · [RA §28](../architecture/reference/28-architecture-acceptance-and-verification.md) |
| Supplement homes | [GM §1](gap-map/1-document-family-scope-and-precedence.md) · [QUAL §5](site-qualification/5-qualification-stages-applicability-and-evidence.md) · [QUAL §6](site-qualification/6-control-inheritance-assurance-and-organizational-interfaces.md) |
| Source IDs | S00 |
| Wording disposition | Unchanged from v1.2 |
| Execution status | Specified, not executed by this release |
| Tests | [CT-049](test-specifications.md#CT-049) · [CT-069](test-specifications.md#CT-069) |

<a id="INV-007"></a>
## INV-007

Failure of an admission or control-plane dependency SHALL fail new changes closed; failure SHALL NOT silently create a security bypass.

| Source field | Retained value |
| --- | --- |
| Accountable role | Architecture authority |
| Parent sections | [RA §1](../architecture/reference/1-purpose-scope-and-architectural-authority.md) · [RA §28](../architecture/reference/28-architecture-acceptance-and-verification.md) |
| Supplement homes | [GM §1](gap-map/1-document-family-scope-and-precedence.md) · [QUAL §5](site-qualification/5-qualification-stages-applicability-and-evidence.md) · [QUAL §6](site-qualification/6-control-inheritance-assurance-and-organizational-interfaces.md) |
| Source IDs | S00 |
| Wording disposition | Unchanged from v1.2 |
| Execution status | Specified, not executed by this release |
| Tests | [CT-011](test-specifications.md#CT-011) · [CT-045](test-specifications.md#CT-045) |

<a id="REF-001"></a>
## REF-001

The service contract SHALL remain stable when a supported platform is replaced, provided the replacement platform passes the required conformance profile.

| Source field | Retained value |
| --- | --- |
| Accountable role | Architecture authority |
| Parent sections | [RA §1](../architecture/reference/1-purpose-scope-and-architectural-authority.md) · [RA §28](../architecture/reference/28-architecture-acceptance-and-verification.md) |
| Supplement homes | [GM §1](gap-map/1-document-family-scope-and-precedence.md) · [QUAL §5](site-qualification/5-qualification-stages-applicability-and-evidence.md) · [QUAL §6](site-qualification/6-control-inheritance-assurance-and-organizational-interfaces.md) |
| Source IDs | S00 |
| Wording disposition | Unchanged from v1.2 |
| Execution status | Specified, not executed by this release |
| Tests | [CT-016](test-specifications.md#CT-016) · [CT-060](test-specifications.md#CT-060) |

<a id="REF-002"></a>
## REF-002

Platform-specific extensions MAY be offered, but they SHALL be declared as capabilities and SHALL NOT redefine the portable core semantics.

| Source field | Retained value |
| --- | --- |
| Accountable role | Architecture authority |
| Parent sections | [RA §1](../architecture/reference/1-purpose-scope-and-architectural-authority.md) · [RA §28](../architecture/reference/28-architecture-acceptance-and-verification.md) |
| Supplement homes | [GM §1](gap-map/1-document-family-scope-and-precedence.md) · [QUAL §5](site-qualification/5-qualification-stages-applicability-and-evidence.md) · [QUAL §6](site-qualification/6-control-inheritance-assurance-and-organizational-interfaces.md) |
| Source IDs | S00 |
| Wording disposition | Unchanged from v1.2 |
| Execution status | Specified, not executed by this release |
| Tests | [CT-016](test-specifications.md#CT-016) · [CT-018](test-specifications.md#CT-018) |

<a id="DOC-001"></a>
## DOC-001

Every normative requirement SHALL have a stable identifier, accountable owner, applicability, source basis, verification procedure and exception policy; generated catalogues SHALL contain every active requirement.

| Source field | Retained value |
| --- | --- |
| Accountable role | Architecture authority |
| Parent sections | [RA §1](../architecture/reference/1-purpose-scope-and-architectural-authority.md) · [RA §28](../architecture/reference/28-architecture-acceptance-and-verification.md) |
| Supplement homes | [GM §1](gap-map/1-document-family-scope-and-precedence.md) · [QUAL §5](site-qualification/5-qualification-stages-applicability-and-evidence.md) · [QUAL §6](site-qualification/6-control-inheritance-assurance-and-organizational-interfaces.md) |
| Source IDs | S00 |
| Wording disposition | Unchanged from v1.2 |
| Execution status | Specified, not executed by this release |
| Tests | [CT-075](test-specifications.md#CT-075) |

<a id="AUTH-001"></a>
## AUTH-001

Technical conformance, service readiness and formal authorization SHALL be recorded as distinct states; an automated test result SHALL NOT create, renew or impersonate an authorization decision.

| Source field | Retained value |
| --- | --- |
| Accountable role | Security authority |
| Parent sections | [RA §1](../architecture/reference/1-purpose-scope-and-architectural-authority.md) · [RA §28](../architecture/reference/28-architecture-acceptance-and-verification.md) |
| Supplement homes | [GM §1](gap-map/1-document-family-scope-and-precedence.md) · [QUAL §5](site-qualification/5-qualification-stages-applicability-and-evidence.md) · [QUAL §6](site-qualification/6-control-inheritance-assurance-and-organizational-interfaces.md) |
| Source IDs | S04; S05 |
| Wording disposition | Unchanged from v1.2 |
| Execution status | Specified, not executed by this release |
| Tests | [CT-049](test-specifications.md#CT-049) · [CT-069](test-specifications.md#CT-069) |

Related ADRs: [ADR-0017](../adr/0017-separate-reference-adoption-technical-qualification-and-authorization.md)

<a id="STD-001"></a>
## STD-001

The standards register SHALL record edition, effective/review date, applicability, owner and supersession relationships; external changes SHALL trigger an impact review of affected profiles and evidence.

| Source field | Retained value |
| --- | --- |
| Accountable role | Security authority |
| Parent sections | [RA §1](../architecture/reference/1-purpose-scope-and-architectural-authority.md) · [RA §28](../architecture/reference/28-architecture-acceptance-and-verification.md) |
| Supplement homes | [GM §1](gap-map/1-document-family-scope-and-precedence.md) · [QUAL §5](site-qualification/5-qualification-stages-applicability-and-evidence.md) · [QUAL §6](site-qualification/6-control-inheritance-assurance-and-organizational-interfaces.md) |
| Source IDs | S01; S02; S05; S10 |
| Wording disposition | Unchanged from v1.2 |
| Execution status | Specified, not executed by this release |
| Tests | [CT-062](test-specifications.md#CT-062) · [CT-075](test-specifications.md#CT-075) |

<a id="STD-002"></a>
## STD-002

Control mappings SHALL preserve source edition and identifier and SHALL distinguish direct source requirements, local translations and design decisions; a family-level crosswalk SHALL NOT be represented as a completed control assessment.

| Source field | Retained value |
| --- | --- |
| Accountable role | Security authority |
| Parent sections | [RA §1](../architecture/reference/1-purpose-scope-and-architectural-authority.md) · [RA §28](../architecture/reference/28-architecture-acceptance-and-verification.md) |
| Supplement homes | [GM §1](gap-map/1-document-family-scope-and-precedence.md) · [QUAL §5](site-qualification/5-qualification-stages-applicability-and-evidence.md) · [QUAL §6](site-qualification/6-control-inheritance-assurance-and-organizational-interfaces.md) |
| Source IDs | S05 |
| Wording disposition | Unchanged from v1.2 |
| Execution status | Specified, not executed by this release |
| Tests | [CT-062](test-specifications.md#CT-062) · [CT-075](test-specifications.md#CT-075) |

<a id="CAT-001"></a>
## CAT-001

Each WSD SHALL record confidentiality, integrity and availability separately and SHALL reference the exact adopted SecurityProfile, AssuranceProfile, AvailabilityProfile, RecoveryProfile and PlacementProfile.

| Source field | Retained value |
| --- | --- |
| Accountable role | Security authority |
| Parent sections | [RA §2](../architecture/reference/2-design-drivers-and-selected-reference-pattern.md) |
| Supplement homes | [GM §2](gap-map/2-primary-knowledge-homes-and-cross-cutting-changes.md) |
| Source IDs | S00; S05; S06 |
| Wording disposition | Unchanged from v1.2 |
| Execution status | Specified, not executed by this release |
| Tests | [CT-017](test-specifications.md#CT-017) · [CT-062](test-specifications.md#CT-062) · [CT-069](test-specifications.md#CT-069) |

Related ADRs: [ADR-0019](../adr/0019-separate-information-impacts-from-service-level-and-recovery-promises.md)

<a id="CAT-002"></a>
## CAT-002

Profile resolution SHALL be immutable and authorized; a consumer SHALL NOT lower mandatory requirements by editing a profile, forging a status field or choosing an unsupported category.

| Source field | Retained value |
| --- | --- |
| Accountable role | Automation platform |
| Parent sections | [RA §2](../architecture/reference/2-design-drivers-and-selected-reference-pattern.md) |
| Supplement homes | [GM §2](gap-map/2-primary-knowledge-homes-and-cross-cutting-changes.md) |
| Source IDs | S00 |
| Wording disposition | Unchanged from v1.2 |
| Execution status | Specified, not executed by this release |
| Tests | [CT-017](test-specifications.md#CT-017) · [CT-018](test-specifications.md#CT-018) |

<a id="THR-001"></a>
## THR-001

Each platform qualification and material WSD change SHALL include a threat/failure analysis that identifies trust boundaries, privileged actors, dependency failures, residual risks and applicable tests.

| Source field | Retained value |
| --- | --- |
| Accountable role | Security authority |
| Parent sections | [RA §2](../architecture/reference/2-design-drivers-and-selected-reference-pattern.md) |
| Supplement homes | [GM §2](gap-map/2-primary-knowledge-homes-and-cross-cutting-changes.md) |
| Source IDs | S03; S05; S08 |
| Wording disposition | Unchanged from v1.2 |
| Execution status | Specified, not executed by this release |
| Tests | [CT-035](test-specifications.md#CT-035) · [CT-062](test-specifications.md#CT-062) · [CT-080](test-specifications.md#CT-080) |

<a id="MODEL-001"></a>
## MODEL-001

Every network SHALL resolve to one Security Domain Instance, one logical domain, one zone class, one address authority and one accountable owner; shared-domain lifecycle SHALL use explicit dependency references.

| Source field | Retained value |
| --- | --- |
| Accountable role | Architecture authority |
| Parent sections | [RA §3](../architecture/reference/3-system-context-and-physical-hosting-topology.md) · [RA §7](../architecture/reference/7-tenant-environments-and-security-domain-placement.md) |
| Supplement homes | [QUAL §2](site-qualification/2-site-low-level-design-and-dependency-schedule.md) · [VND §1](../engineering/platform-realizations/1-one-reference-environment-three-native-realizations.md) · [VND §2](../engineering/platform-realizations/2-physical-placement-and-the-sharing-decision.md) |
| Source IDs | S00 |
| Wording disposition | Unchanged from v1.2 |
| Execution status | Specified, not executed by this release |
| Tests | [CT-017](test-specifications.md#CT-017) · [CT-025](test-specifications.md#CT-025) · [CT-070](test-specifications.md#CT-070) |

Related ADRs: [ADR-0018](../adr/0018-separate-tenant-administration-wsd-lifecycle-and-domain-realization.md)

<a id="MODEL-002"></a>
## MODEL-002

Provider service consumption, platform control, privileged management and OOB transport SHALL be modeled separately; a shared service SHALL NOT create implicit authority over another plane.

| Source field | Retained value |
| --- | --- |
| Accountable role | Architecture authority |
| Parent sections | [RA §3](../architecture/reference/3-system-context-and-physical-hosting-topology.md) · [RA §7](../architecture/reference/7-tenant-environments-and-security-domain-placement.md) |
| Supplement homes | [QUAL §2](site-qualification/2-site-low-level-design-and-dependency-schedule.md) · [VND §1](../engineering/platform-realizations/1-one-reference-environment-three-native-realizations.md) · [VND §2](../engineering/platform-realizations/2-physical-placement-and-the-sharing-decision.md) |
| Source IDs | S00; S01; S02 |
| Wording disposition | Unchanged from v1.2 |
| Execution status | Specified, not executed by this release |
| Tests | [CT-004](test-specifications.md#CT-004) · [CT-008](test-specifications.md#CT-008) · [CT-026](test-specifications.md#CT-026) |

Related ADRs: [ADR-0010](../adr/0010-expose-shared-services-through-scoped-consumption-endpoints.md)

<a id="TEN-001"></a>
## TEN-001

Cross-tenant routing SHALL be denied by default even when two tenants use the same zone class.

| Source field | Retained value |
| --- | --- |
| Accountable role | Automation platform |
| Parent sections | [RA §7](../architecture/reference/7-tenant-environments-and-security-domain-placement.md) |
| Supplement homes | [VND §1](../engineering/platform-realizations/1-one-reference-environment-three-native-realizations.md) · [VND §2](../engineering/platform-realizations/2-physical-placement-and-the-sharing-decision.md) |
| Source IDs | S00 |
| Wording disposition | Unchanged from v1.2 |
| Execution status | Specified, not executed by this release |
| Tests | [CT-001](test-specifications.md#CT-001) · [CT-002](test-specifications.md#CT-002) · [CT-019](test-specifications.md#CT-019) |

Related ADRs: [ADR-0018](../adr/0018-separate-tenant-administration-wsd-lifecycle-and-domain-realization.md)

<a id="TEN-002"></a>
## TEN-002

Tenant administrators SHALL NOT have authority to modify provider management, security-edge infrastructure, physical fabric, or another tenant namespace.

| Source field | Retained value |
| --- | --- |
| Accountable role | Automation platform |
| Parent sections | [RA §7](../architecture/reference/7-tenant-environments-and-security-domain-placement.md) |
| Supplement homes | [VND §1](../engineering/platform-realizations/1-one-reference-environment-three-native-realizations.md) · [VND §2](../engineering/platform-realizations/2-physical-placement-and-the-sharing-decision.md) |
| Source IDs | S00 |
| Wording disposition | Unchanged from v1.2 |
| Execution status | Specified, not executed by this release |
| Tests | [CT-019](test-specifications.md#CT-019) · [CT-026](test-specifications.md#CT-026) |

<a id="TEN-003"></a>
## TEN-003

Tenant ownership, entitlements and role bindings SHALL be versioned and auditable; suspension SHALL specify permitted recovery/containment actions and SHALL NOT imply indiscriminate workload deletion.

| Source field | Retained value |
| --- | --- |
| Accountable role | Service owner |
| Parent sections | [RA §7](../architecture/reference/7-tenant-environments-and-security-domain-placement.md) |
| Supplement homes | [VND §1](../engineering/platform-realizations/1-one-reference-environment-three-native-realizations.md) · [VND §2](../engineering/platform-realizations/2-physical-placement-and-the-sharing-decision.md) |
| Source IDs | S00 |
| Wording disposition | Unchanged from v1.2 |
| Execution status | Specified, not executed by this release |
| Tests | [CT-019](test-specifications.md#CT-019) · [CT-057](test-specifications.md#CT-057) · [CT-070](test-specifications.md#CT-070) |

Related ADRs: [ADR-0016](../adr/0016-assign-one-authoritative-writer-per-native-object-and-sensitive-subresource.md)

<a id="WSD-001"></a>
## WSD-001

Every managed workload SHALL belong to a WSD or an explicitly documented equivalent lifecycle object.

| Source field | Retained value |
| --- | --- |
| Accountable role | Service owner |
| Parent sections | [RA §7](../architecture/reference/7-tenant-environments-and-security-domain-placement.md) |
| Supplement homes | [VND §1](../engineering/platform-realizations/1-one-reference-environment-three-native-realizations.md) · [VND §2](../engineering/platform-realizations/2-physical-placement-and-the-sharing-decision.md) |
| Source IDs | S00 |
| Wording disposition | Unchanged from v1.2 |
| Execution status | Specified, not executed by this release |
| Tests | [CT-017](test-specifications.md#CT-017) · [CT-070](test-specifications.md#CT-070) |

Related ADRs: [ADR-0018](../adr/0018-separate-tenant-administration-wsd-lifecycle-and-domain-realization.md)

<a id="WSD-002"></a>
## WSD-002

The WSD SHALL contain security and connectivity intent; it SHALL NOT contain vendor-specific infrastructure identifiers in the consumer contract.

| Source field | Retained value |
| --- | --- |
| Accountable role | Automation platform |
| Parent sections | [RA §7](../architecture/reference/7-tenant-environments-and-security-domain-placement.md) |
| Supplement homes | [VND §1](../engineering/platform-realizations/1-one-reference-environment-three-native-realizations.md) · [VND §2](../engineering/platform-realizations/2-physical-placement-and-the-sharing-decision.md) |
| Source IDs | S00 |
| Wording disposition | Unchanged from v1.2 |
| Execution status | Specified, not executed by this release |
| Tests | [CT-016](test-specifications.md#CT-016) · [CT-017](test-specifications.md#CT-017) |

<a id="WSD-003"></a>
## WSD-003

A WSD SHALL declare compute, storage, identity, backup, recovery, exposure and evidence dependencies in addition to network intent; unresolved mandatory dependencies SHALL block Service Ready.

| Source field | Retained value |
| --- | --- |
| Accountable role | Service owner |
| Parent sections | [RA §7](../architecture/reference/7-tenant-environments-and-security-domain-placement.md) |
| Supplement homes | [VND §1](../engineering/platform-realizations/1-one-reference-environment-three-native-realizations.md) · [VND §2](../engineering/platform-realizations/2-physical-placement-and-the-sharing-decision.md) |
| Source IDs | S00 |
| Wording disposition | Unchanged from v1.2 |
| Execution status | Specified, not executed by this release |
| Tests | [CT-062](test-specifications.md#CT-062) · [CT-069](test-specifications.md#CT-069) |

<a id="SDI-001"></a>
## SDI-001

A Security Domain Instance SHALL contain only networks authorized to share its routing/security authority.

| Source field | Retained value |
| --- | --- |
| Accountable role | Security authority |
| Parent sections | [RA §7](../architecture/reference/7-tenant-environments-and-security-domain-placement.md) |
| Supplement homes | [VND §1](../engineering/platform-realizations/1-one-reference-environment-three-native-realizations.md) · [VND §2](../engineering/platform-realizations/2-physical-placement-and-the-sharing-decision.md) |
| Source IDs | S00 |
| Wording disposition | Unchanged from v1.2 |
| Execution status | Specified, not executed by this release |
| Tests | [CT-025](test-specifications.md#CT-025) · [CT-035](test-specifications.md#CT-035) |

Related ADRs: [ADR-0018](../adr/0018-separate-tenant-administration-wsd-lifecycle-and-domain-realization.md)

<a id="SDI-002"></a>
## SDI-002

Sharing a zone class SHALL NOT imply reachability between independent Security Domain Instances.

| Source field | Retained value |
| --- | --- |
| Accountable role | Platform engineering |
| Parent sections | [RA §7](../architecture/reference/7-tenant-environments-and-security-domain-placement.md) |
| Supplement homes | [VND §1](../engineering/platform-realizations/1-one-reference-environment-three-native-realizations.md) · [VND §2](../engineering/platform-realizations/2-physical-placement-and-the-sharing-decision.md) |
| Source IDs | S00 |
| Wording disposition | Unchanged from v1.2 |
| Execution status | Specified, not executed by this release |
| Tests | [CT-001](test-specifications.md#CT-001) · [CT-002](test-specifications.md#CT-002) · [CT-021](test-specifications.md#CT-021) |

<a id="SDI-003"></a>
## SDI-003

Dedicated Security Domain Instances SHOULD be available for workloads whose assurance profile or threat model requires stronger isolation than shared logical segmentation.

| Source field | Retained value |
| --- | --- |
| Accountable role | Platform engineering |
| Parent sections | [RA §7](../architecture/reference/7-tenant-environments-and-security-domain-placement.md) |
| Supplement homes | [VND §1](../engineering/platform-realizations/1-one-reference-environment-three-native-realizations.md) · [VND §2](../engineering/platform-realizations/2-physical-placement-and-the-sharing-decision.md) |
| Source IDs | S00 |
| Wording disposition | Unchanged from v1.2 |
| Execution status | Specified, not executed by this release |
| Tests | [CT-018](test-specifications.md#CT-018) · [CT-035](test-specifications.md#CT-035) |

<a id="SDI-004"></a>
## SDI-004

Each Security Domain Instance SHALL reference a logical domain and a qualified site/platform realization; membership and sharing changes SHALL be assessed as security-significant changes.

| Source field | Retained value |
| --- | --- |
| Accountable role | Security authority |
| Parent sections | [RA §7](../architecture/reference/7-tenant-environments-and-security-domain-placement.md) |
| Supplement homes | [VND §1](../engineering/platform-realizations/1-one-reference-environment-three-native-realizations.md) · [VND §2](../engineering/platform-realizations/2-physical-placement-and-the-sharing-decision.md) |
| Source IDs | S00 |
| Wording disposition | Unchanged from v1.2 |
| Execution status | Specified, not executed by this release |
| Tests | [CT-025](test-specifications.md#CT-025) · [CT-035](test-specifications.md#CT-035) · [CT-048](test-specifications.md#CT-048) |

Related ADRs: [ADR-0008](../adr/0008-preserve-zone-aware-host-placement-and-disclose-every-shared-layer.md)

<a id="ZONE-001"></a>
## ZONE-001

Internal instance zoneClass SHALL be limited to PAZ, OZ, RZ, HRZ or provider-controlled MZ; external PZ/REZ relationships SHALL use ExternalDomain with explicit authority and trust metadata.

| Source field | Retained value |
| --- | --- |
| Accountable role | Security authority |
| Parent sections | [RA §8](../architecture/reference/8-zone-interfaces-routing-and-security-edge-topology.md) |
| Supplement homes | [NET §2](../engineering/fabric/2-isolated-attachment-units-and-bounded-capacity.md) · [NET §3](../engineering/fabric/3-worked-inter-zone-routing-and-enforcement-schedule.md) |
| Source IDs | S01; S02 |
| Wording disposition | Unchanged from v1.2 |
| Execution status | Specified, not executed by this release |
| Tests | [CT-017](test-specifications.md#CT-017) · [CT-025](test-specifications.md#CT-025) · [CT-076](test-specifications.md#CT-076) |

<a id="ZONE-002"></a>
## ZONE-002

Every requested adjacency SHALL be evaluated against the versioned zone policy before allocation; being permitted to create a ZIP SHALL NOT grant any traffic by default.

| Source field | Retained value |
| --- | --- |
| Accountable role | Automation platform |
| Parent sections | [RA §8](../architecture/reference/8-zone-interfaces-routing-and-security-edge-topology.md) |
| Supplement homes | [NET §2](../engineering/fabric/2-isolated-attachment-units-and-bounded-capacity.md) · [NET §3](../engineering/fabric/3-worked-inter-zone-routing-and-enforcement-schedule.md) |
| Source IDs | S01; S02 |
| Wording disposition | Unchanged from v1.2 |
| Execution status | Specified, not executed by this release |
| Tests | [CT-025](test-specifications.md#CT-025) · [CT-066](test-specifications.md#CT-066) |

<a id="ZIP-001"></a>
## ZIP-001

All inter-zone network paths SHALL traverse the applicable ZIP/security edge.

| Source field | Retained value |
| --- | --- |
| Accountable role | Security-edge operations |
| Parent sections | [RA §8](../architecture/reference/8-zone-interfaces-routing-and-security-edge-topology.md) |
| Supplement homes | [NET §2](../engineering/fabric/2-isolated-attachment-units-and-bounded-capacity.md) · [NET §3](../engineering/fabric/3-worked-inter-zone-routing-and-enforcement-schedule.md) |
| Source IDs | S00 |
| Wording disposition | Unchanged from v1.2 |
| Execution status | Specified, not executed by this release |
| Tests | [CT-003](test-specifications.md#CT-003) · [CT-080](test-specifications.md#CT-080) |

Related ADRs: [ADR-0006](../adr/0006-use-an-explicit-governed-zip-for-inter-domain-trust-transitions.md)

<a id="ZIP-002"></a>
## ZIP-002

A ZIP SHALL identify exactly two authorized adjacent endpoints, each an internal domain instance or approved external/management domain, and SHALL NOT create a general-purpose third-zone transit path.

| Source field | Retained value |
| --- | --- |
| Accountable role | Security authority |
| Parent sections | [RA §8](../architecture/reference/8-zone-interfaces-routing-and-security-edge-topology.md) |
| Supplement homes | [NET §2](../engineering/fabric/2-isolated-attachment-units-and-bounded-capacity.md) · [NET §3](../engineering/fabric/3-worked-inter-zone-routing-and-enforcement-schedule.md) |
| Source IDs | S00; S01; S02 |
| Wording disposition | Unchanged from v1.2 |
| Execution status | Specified, not executed by this release |
| Tests | [CT-023](test-specifications.md#CT-023) · [CT-025](test-specifications.md#CT-025) |

Related ADRs: [ADR-0006](../adr/0006-use-an-explicit-governed-zip-for-inter-domain-trust-transitions.md) · [ADR-0007](../adr/0007-allocate-isolated-domain-attachments-and-qualify-sharing.md)

<a id="ZIP-003"></a>
## ZIP-003

Default inter-zone policy SHALL be deny; allowed flows SHALL be generated from approved Flow Intentions and Service Bindings.

| Source field | Retained value |
| --- | --- |
| Accountable role | Security-edge operations |
| Parent sections | [RA §8](../architecture/reference/8-zone-interfaces-routing-and-security-edge-topology.md) |
| Supplement homes | [NET §2](../engineering/fabric/2-isolated-attachment-units-and-bounded-capacity.md) · [NET §3](../engineering/fabric/3-worked-inter-zone-routing-and-enforcement-schedule.md) |
| Source IDs | S00 |
| Wording disposition | Unchanged from v1.2 |
| Execution status | Specified, not executed by this release |
| Tests | [CT-007](test-specifications.md#CT-007) · [CT-025](test-specifications.md#CT-025) · [CT-066](test-specifications.md#CT-066) |

Related ADRs: [ADR-0006](../adr/0006-use-an-explicit-governed-zip-for-inter-domain-trust-transitions.md)

<a id="ZIP-004"></a>
## ZIP-004

ZIP management traffic SHALL be segregated from operational traffic.

| Source field | Retained value |
| --- | --- |
| Accountable role | Security-edge operations |
| Parent sections | [RA §8](../architecture/reference/8-zone-interfaces-routing-and-security-edge-topology.md) |
| Supplement homes | [NET §2](../engineering/fabric/2-isolated-attachment-units-and-bounded-capacity.md) · [NET §3](../engineering/fabric/3-worked-inter-zone-routing-and-enforcement-schedule.md) |
| Source IDs | S00 |
| Wording disposition | Unchanged from v1.2 |
| Execution status | Specified, not executed by this release |
| Tests | [CT-004](test-specifications.md#CT-004) · [CT-026](test-specifications.md#CT-026) |

<a id="ZIP-005"></a>
## ZIP-005

Data-path ZIPs and management-path ZIPs SHALL be governed and deployed as distinct security services; shared virtualization SHALL only be used where the applicable assurance analysis supports it.

| Source field | Retained value |
| --- | --- |
| Accountable role | Security authority |
| Parent sections | [RA §8](../architecture/reference/8-zone-interfaces-routing-and-security-edge-topology.md) |
| Supplement homes | [NET §2](../engineering/fabric/2-isolated-attachment-units-and-bounded-capacity.md) · [NET §3](../engineering/fabric/3-worked-inter-zone-routing-and-enforcement-schedule.md) |
| Source IDs | S00 |
| Wording disposition | Unchanged from v1.2 |
| Execution status | Specified, not executed by this release |
| Tests | [CT-026](test-specifications.md#CT-026) · [CT-035](test-specifications.md#CT-035) · [CT-080](test-specifications.md#CT-080) |

<a id="ZIP-006"></a>
## ZIP-006

Each ZIP SHALL record its two zone authorities, joint approval, required security functions, management authority, heightened posture, session-revocation behavior and current evidence.

| Source field | Retained value |
| --- | --- |
| Accountable role | Security authority |
| Parent sections | [RA §8](../architecture/reference/8-zone-interfaces-routing-and-security-edge-topology.md) |
| Supplement homes | [NET §2](../engineering/fabric/2-isolated-attachment-units-and-bounded-capacity.md) · [NET §3](../engineering/fabric/3-worked-inter-zone-routing-and-enforcement-schedule.md) |
| Source IDs | S01; S02 |
| Wording disposition | Unchanged from v1.2 |
| Execution status | Specified, not executed by this release |
| Tests | [CT-067](test-specifications.md#CT-067) · [CT-077](test-specifications.md#CT-077) · [CT-080](test-specifications.md#CT-080) |

Related ADRs: [ADR-0006](../adr/0006-use-an-explicit-governed-zip-for-inter-domain-trust-transitions.md)

<a id="ZIP-007"></a>
## ZIP-007

A distributed or shared-infrastructure ZIP SHALL be qualified against the same required security outcomes as a dedicated edge; any unsupported mandatory function SHALL make that realization ineligible.

| Source field | Retained value |
| --- | --- |
| Accountable role | Platform engineering |
| Parent sections | [RA §8](../architecture/reference/8-zone-interfaces-routing-and-security-edge-topology.md) |
| Supplement homes | [NET §2](../engineering/fabric/2-isolated-attachment-units-and-bounded-capacity.md) · [NET §3](../engineering/fabric/3-worked-inter-zone-routing-and-enforcement-schedule.md) |
| Source IDs | S02 |
| Wording disposition | Unchanged from v1.2 |
| Execution status | Specified, not executed by this release |
| Tests | [CT-003](test-specifications.md#CT-003) · [CT-023](test-specifications.md#CT-023) · [CT-080](test-specifications.md#CT-080) |

Related ADRs: [ADR-0006](../adr/0006-use-an-explicit-governed-zip-for-inter-domain-trust-transitions.md)

<a id="MGT-001"></a>
## MGT-001

Tenant workload networks SHALL have no direct route to infrastructure management interfaces.

| Source field | Retained value |
| --- | --- |
| Accountable role | Management operations |
| Parent sections | [RA §6](../architecture/reference/6-management-platform-control-and-out-of-band-access.md) · [RA §13](../architecture/reference/13-identity-cryptography-and-service-trust.md) |
| Supplement homes | [NET §6](../engineering/fabric/6-management-paths-and-interface-handover.md) · [SVC §3](../architecture/shared-services/3-identity-certificates-keys-and-independent-recovery.md) |
| Source IDs | S00 |
| Wording disposition | Unchanged from v1.2 |
| Execution status | Specified, not executed by this release |
| Tests | [CT-004](test-specifications.md#CT-004) · [CT-026](test-specifications.md#CT-026) |

Related ADRs: [ADR-0009](../adr/0009-separate-management-security-platform-control-and-oob-recovery.md)

<a id="MGT-002"></a>
## MGT-002

Administrative access SHALL originate from an authorized management access path and traverse management-specific security controls.

| Source field | Retained value |
| --- | --- |
| Accountable role | Management operations |
| Parent sections | [RA §6](../architecture/reference/6-management-platform-control-and-out-of-band-access.md) · [RA §13](../architecture/reference/13-identity-cryptography-and-service-trust.md) |
| Supplement homes | [NET §6](../engineering/fabric/6-management-paths-and-interface-handover.md) · [SVC §3](../architecture/shared-services/3-identity-certificates-keys-and-independent-recovery.md) |
| Source IDs | S00 |
| Wording disposition | Unchanged from v1.2 |
| Execution status | Specified, not executed by this release |
| Tests | [CT-026](test-specifications.md#CT-026) · [CT-027](test-specifications.md#CT-027) |

Related ADRs: [ADR-0009](../adr/0009-separate-management-security-platform-control-and-oob-recovery.md)

<a id="MGT-003"></a>
## MGT-003

Automation identities used to manage tenant workloads SHALL be separated from identities able to modify the physical fabric, security edge, or management foundation.

| Source field | Retained value |
| --- | --- |
| Accountable role | Automation platform |
| Parent sections | [RA §6](../architecture/reference/6-management-platform-control-and-out-of-band-access.md) · [RA §13](../architecture/reference/13-identity-cryptography-and-service-trust.md) |
| Supplement homes | [NET §6](../engineering/fabric/6-management-paths-and-interface-handover.md) · [SVC §3](../architecture/shared-services/3-identity-certificates-keys-and-independent-recovery.md) |
| Source IDs | S00 |
| Wording disposition | Unchanged from v1.2 |
| Execution status | Specified, not executed by this release |
| Tests | [CT-019](test-specifications.md#CT-019) · [CT-044](test-specifications.md#CT-044) |

<a id="MGT-004"></a>
## MGT-004

Break-glass access SHALL be separately controlled, strongly authenticated, logged, time-bounded where feasible, and periodically tested.

| Source field | Retained value |
| --- | --- |
| Accountable role | Management operations |
| Parent sections | [RA §6](../architecture/reference/6-management-platform-control-and-out-of-band-access.md) · [RA §13](../architecture/reference/13-identity-cryptography-and-service-trust.md) |
| Supplement homes | [NET §6](../engineering/fabric/6-management-paths-and-interface-handover.md) · [SVC §3](../architecture/shared-services/3-identity-certificates-keys-and-independent-recovery.md) |
| Source IDs | S00 |
| Wording disposition | Unchanged from v1.2 |
| Execution status | Specified, not executed by this release |
| Tests | [CT-027](test-specifications.md#CT-027) · [CT-079](test-specifications.md#CT-079) |

<a id="MGT-005"></a>
## MGT-005

The implementation SHALL document independent MZ semantics, OOB transport dependencies, remote-management boundary and privileged identity controls; tenant-facing APIs SHALL NOT expose infrastructure administration.

| Source field | Retained value |
| --- | --- |
| Accountable role | Management operations |
| Parent sections | [RA §6](../architecture/reference/6-management-platform-control-and-out-of-band-access.md) · [RA §13](../architecture/reference/13-identity-cryptography-and-service-trust.md) |
| Supplement homes | [NET §6](../engineering/fabric/6-management-paths-and-interface-handover.md) · [SVC §3](../architecture/shared-services/3-identity-certificates-keys-and-independent-recovery.md) |
| Source IDs | S01; S02; S07 |
| Wording disposition | Unchanged from v1.2 |
| Execution status | Specified, not executed by this release |
| Tests | [CT-004](test-specifications.md#CT-004) · [CT-026](test-specifications.md#CT-026) · [CT-055](test-specifications.md#CT-055) |

Related ADRs: [ADR-0009](../adr/0009-separate-management-security-platform-control-and-oob-recovery.md) · [ADR-0014](../adr/0014-bootstrap-management-and-trust-before-consuming-native-apis.md)

<a id="OVL-001"></a>
## OVL-001

A platform SHALL provide an isolated routing/policy mechanism capable of realizing the Security Domain semantics required by the applicable conformance profile.

| Source field | Retained value |
| --- | --- |
| Accountable role | Platform engineering |
| Parent sections | [RA §8](../architecture/reference/8-zone-interfaces-routing-and-security-edge-topology.md) |
| Supplement homes | [NET §2](../engineering/fabric/2-isolated-attachment-units-and-bounded-capacity.md) · [NET §3](../engineering/fabric/3-worked-inter-zone-routing-and-enforcement-schedule.md) |
| Source IDs | S00 |
| Wording disposition | Unchanged from v1.2 |
| Execution status | Specified, not executed by this release |
| Tests | [CT-016](test-specifications.md#CT-016) · [CT-018](test-specifications.md#CT-018) · [CT-080](test-specifications.md#CT-080) |

Related ADRs: [ADR-0005](../adr/0005-keep-vendor-overlays-local-and-connect-through-controlled-handoffs.md)

<a id="OVL-002"></a>
## OVL-002

Native routing MAY be used within one authorized Security Domain Instance; communication between independent security domains SHALL follow the approved boundary/ZIP realization and its policy.

| Source field | Retained value |
| --- | --- |
| Accountable role | Platform engineering |
| Parent sections | [RA §8](../architecture/reference/8-zone-interfaces-routing-and-security-edge-topology.md) |
| Supplement homes | [NET §2](../engineering/fabric/2-isolated-attachment-units-and-bounded-capacity.md) · [NET §3](../engineering/fabric/3-worked-inter-zone-routing-and-enforcement-schedule.md) |
| Source IDs | S00; S01; S02 |
| Wording disposition | Unchanged from v1.2 |
| Execution status | Specified, not executed by this release |
| Tests | [CT-003](test-specifications.md#CT-003) · [CT-021](test-specifications.md#CT-021) · [CT-023](test-specifications.md#CT-023) |

<a id="OVL-003"></a>
## OVL-003

Before a workload is attached, the adapter SHALL normalize permissive native defaults and enforce the mandatory baseline on all supported NIC, router, gateway and workload-attachment paths.

| Source field | Retained value |
| --- | --- |
| Accountable role | Platform engineering |
| Parent sections | [RA §8](../architecture/reference/8-zone-interfaces-routing-and-security-edge-topology.md) |
| Supplement homes | [NET §2](../engineering/fabric/2-isolated-attachment-units-and-bounded-capacity.md) · [NET §3](../engineering/fabric/3-worked-inter-zone-routing-and-enforcement-schedule.md) |
| Source IDs | S00 |
| Wording disposition | Unchanged from v1.2 |
| Execution status | Specified, not executed by this release |
| Tests | [CT-022](test-specifications.md#CT-022) · [CT-066](test-specifications.md#CT-066) · [CT-069](test-specifications.md#CT-069) |

<a id="RTE-001"></a>
## RTE-001

Routes, route imports/exports, and BGP adjacencies SHALL be provider-controlled outputs of authorized intent.

| Source field | Retained value |
| --- | --- |
| Accountable role | Network engineering |
| Parent sections | [RA §8](../architecture/reference/8-zone-interfaces-routing-and-security-edge-topology.md) · [RA §10](../architecture/reference/10-addressing-name-services-and-end-to-end-traffic.md) |
| Supplement homes | [NET §2](../engineering/fabric/2-isolated-attachment-units-and-bounded-capacity.md) · [NET §3](../engineering/fabric/3-worked-inter-zone-routing-and-enforcement-schedule.md) · [NET §4](../engineering/fabric/4-address-naming-and-protocol-family-decisions.md) · [SVC §2](../architecture/shared-services/2-name-time-initialization-and-telemetry-profiles.md) |
| Source IDs | S00 |
| Wording disposition | Unchanged from v1.2 |
| Execution status | Specified, not executed by this release |
| Tests | [CT-009](test-specifications.md#CT-009) · [CT-033](test-specifications.md#CT-033) |

<a id="RTE-002"></a>
## RTE-002

A generalized shared transit VRF SHALL NOT be used as a default inter-zone routing mechanism.

| Source field | Retained value |
| --- | --- |
| Accountable role | Network engineering |
| Parent sections | [RA §8](../architecture/reference/8-zone-interfaces-routing-and-security-edge-topology.md) · [RA §10](../architecture/reference/10-addressing-name-services-and-end-to-end-traffic.md) |
| Supplement homes | [NET §2](../engineering/fabric/2-isolated-attachment-units-and-bounded-capacity.md) · [NET §3](../engineering/fabric/3-worked-inter-zone-routing-and-enforcement-schedule.md) · [NET §4](../engineering/fabric/4-address-naming-and-protocol-family-decisions.md) · [SVC §2](../architecture/shared-services/2-name-time-initialization-and-telemetry-profiles.md) |
| Source IDs | S00 |
| Wording disposition | Unchanged from v1.2 |
| Execution status | Specified, not executed by this release |
| Tests | [CT-003](test-specifications.md#CT-003) · [CT-009](test-specifications.md#CT-009) · [CT-023](test-specifications.md#CT-023) |

<a id="RTE-003"></a>
## RTE-003

Temporary migration or transition routes SHALL have explicit scope, approval, expiry, telemetry, and automated teardown.

| Source field | Retained value |
| --- | --- |
| Accountable role | Network engineering |
| Parent sections | [RA §8](../architecture/reference/8-zone-interfaces-routing-and-security-edge-topology.md) · [RA §10](../architecture/reference/10-addressing-name-services-and-end-to-end-traffic.md) |
| Supplement homes | [NET §2](../engineering/fabric/2-isolated-attachment-units-and-bounded-capacity.md) · [NET §3](../engineering/fabric/3-worked-inter-zone-routing-and-enforcement-schedule.md) · [NET §4](../engineering/fabric/4-address-naming-and-protocol-family-decisions.md) · [SVC §2](../architecture/shared-services/2-name-time-initialization-and-telemetry-profiles.md) |
| Source IDs | S00 |
| Wording disposition | Unchanged from v1.2 |
| Execution status | Specified, not executed by this release |
| Tests | [CT-009](test-specifications.md#CT-009) · [CT-058](test-specifications.md#CT-058) · [CT-077](test-specifications.md#CT-077) |

<a id="RTE-004"></a>
## RTE-004

Route compilation SHALL validate connected routes, recursive next hops, summaries, NAT/PBR interactions and all enabled address families; realized forwarding SHALL be compared with the approved graph before exposure.

| Source field | Retained value |
| --- | --- |
| Accountable role | Network engineering |
| Parent sections | [RA §8](../architecture/reference/8-zone-interfaces-routing-and-security-edge-topology.md) · [RA §10](../architecture/reference/10-addressing-name-services-and-end-to-end-traffic.md) |
| Supplement homes | [NET §2](../engineering/fabric/2-isolated-attachment-units-and-bounded-capacity.md) · [NET §3](../engineering/fabric/3-worked-inter-zone-routing-and-enforcement-schedule.md) · [NET §4](../engineering/fabric/4-address-naming-and-protocol-family-decisions.md) · [SVC §2](../architecture/shared-services/2-name-time-initialization-and-telemetry-profiles.md) |
| Source IDs | S00 |
| Wording disposition | Unchanged from v1.2 |
| Execution status | Specified, not executed by this release |
| Tests | [CT-009](test-specifications.md#CT-009) · [CT-023](test-specifications.md#CT-023) · [CT-024](test-specifications.md#CT-024) · [CT-031](test-specifications.md#CT-031) |

Related ADRs: [ADR-0035](../adr/0035-make-shared-service-replies-select-the-originating-security-context.md)

<a id="IPAM-001"></a>
## IPAM-001

Every managed network SHALL have an authoritative IPAM record and owner.

| Source field | Retained value |
| --- | --- |
| Accountable role | Network engineering |
| Parent sections | [RA §10](../architecture/reference/10-addressing-name-services-and-end-to-end-traffic.md) |
| Supplement homes | [NET §3](../engineering/fabric/3-worked-inter-zone-routing-and-enforcement-schedule.md) · [NET §4](../engineering/fabric/4-address-naming-and-protocol-family-decisions.md) · [SVC §2](../architecture/shared-services/2-name-time-initialization-and-telemetry-profiles.md) |
| Source IDs | S00 |
| Wording disposition | Unchanged from v1.2 |
| Execution status | Specified, not executed by this release |
| Tests | [CT-029](test-specifications.md#CT-029) · [CT-030](test-specifications.md#CT-030) |

Related ADRs: [ADR-0020](../adr/0020-use-authoritative-unique-by-default-address-allocation-and-controlled-reuse.md)

<a id="IPAM-002"></a>
## IPAM-002

Overlapping address space SHALL be an explicit exception or migration pattern, not the standard tenancy model.

| Source field | Retained value |
| --- | --- |
| Accountable role | Network engineering |
| Parent sections | [RA §10](../architecture/reference/10-addressing-name-services-and-end-to-end-traffic.md) |
| Supplement homes | [NET §3](../engineering/fabric/3-worked-inter-zone-routing-and-enforcement-schedule.md) · [NET §4](../engineering/fabric/4-address-naming-and-protocol-family-decisions.md) · [SVC §2](../architecture/shared-services/2-name-time-initialization-and-telemetry-profiles.md) |
| Source IDs | S00 |
| Wording disposition | Unchanged from v1.2 |
| Execution status | Specified, not executed by this release |
| Tests | [CT-029](test-specifications.md#CT-029) · [CT-061](test-specifications.md#CT-061) |

Related ADRs: [ADR-0020](../adr/0020-use-authoritative-unique-by-default-address-allocation-and-controlled-reuse.md)

<a id="IPAM-003"></a>
## IPAM-003

Address release SHOULD include quarantine/reuse controls appropriate to DNS, logging, firewall state, and incident-response requirements.

| Source field | Retained value |
| --- | --- |
| Accountable role | Network engineering |
| Parent sections | [RA §10](../architecture/reference/10-addressing-name-services-and-end-to-end-traffic.md) |
| Supplement homes | [NET §3](../engineering/fabric/3-worked-inter-zone-routing-and-enforcement-schedule.md) · [NET §4](../engineering/fabric/4-address-naming-and-protocol-family-decisions.md) · [SVC §2](../architecture/shared-services/2-name-time-initialization-and-telemetry-profiles.md) |
| Source IDs | S00 |
| Wording disposition | Unchanged from v1.2 |
| Execution status | Specified, not executed by this release |
| Tests | [CT-013](test-specifications.md#CT-013) · [CT-030](test-specifications.md#CT-030) |

Related ADRs: [ADR-0020](../adr/0020-use-authoritative-unique-by-default-address-allocation-and-controlled-reuse.md)

<a id="IPAM-004"></a>
## IPAM-004

Address allocation, DNS/DHCP registration and release SHALL use idempotent operation identities, conflict detection and a dependency-aware quarantine policy; IPAM failure SHALL NOT cause guessed allocations.

| Source field | Retained value |
| --- | --- |
| Accountable role | Automation platform |
| Parent sections | [RA §10](../architecture/reference/10-addressing-name-services-and-end-to-end-traffic.md) |
| Supplement homes | [NET §3](../engineering/fabric/3-worked-inter-zone-routing-and-enforcement-schedule.md) · [NET §4](../engineering/fabric/4-address-naming-and-protocol-family-decisions.md) · [SVC §2](../architecture/shared-services/2-name-time-initialization-and-telemetry-profiles.md) |
| Source IDs | S00 |
| Wording disposition | Unchanged from v1.2 |
| Execution status | Specified, not executed by this release |
| Tests | [CT-029](test-specifications.md#CT-029) · [CT-030](test-specifications.md#CT-030) · [CT-045](test-specifications.md#CT-045) · [CT-046](test-specifications.md#CT-046) |

Related ADRs: [ADR-0020](../adr/0020-use-authoritative-unique-by-default-address-allocation-and-controlled-reuse.md)

<a id="IPV6-001"></a>
## IPV6-001

Security semantics SHALL be equivalent across IPv4 and IPv6 unless an explicit, approved protocol-specific exception exists.

| Source field | Retained value |
| --- | --- |
| Accountable role | Network engineering |
| Parent sections | [RA §10](../architecture/reference/10-addressing-name-services-and-end-to-end-traffic.md) |
| Supplement homes | [NET §3](../engineering/fabric/3-worked-inter-zone-routing-and-enforcement-schedule.md) · [NET §4](../engineering/fabric/4-address-naming-and-protocol-family-decisions.md) · [SVC §2](../architecture/shared-services/2-name-time-initialization-and-telemetry-profiles.md) |
| Source IDs | S00 |
| Wording disposition | Unchanged from v1.2 |
| Execution status | Specified, not executed by this release |
| Tests | [CT-002](test-specifications.md#CT-002) · [CT-031](test-specifications.md#CT-031) · [CT-032](test-specifications.md#CT-032) |

Related ADRs: [ADR-0021](../adr/0021-offer-address-families-explicitly-across-the-whole-service-path.md)

<a id="IPV6-002"></a>
## IPV6-002

Conformance testing SHALL include IPv6 negative-path tests before a platform is certified for dual-stack service.

| Source field | Retained value |
| --- | --- |
| Accountable role | Platform engineering |
| Parent sections | [RA §10](../architecture/reference/10-addressing-name-services-and-end-to-end-traffic.md) |
| Supplement homes | [NET §3](../engineering/fabric/3-worked-inter-zone-routing-and-enforcement-schedule.md) · [NET §4](../engineering/fabric/4-address-naming-and-protocol-family-decisions.md) · [SVC §2](../architecture/shared-services/2-name-time-initialization-and-telemetry-profiles.md) |
| Source IDs | S00 |
| Wording disposition | Unchanged from v1.2 |
| Execution status | Specified, not executed by this release |
| Tests | [CT-002](test-specifications.md#CT-002) · [CT-003](test-specifications.md#CT-003) · [CT-031](test-specifications.md#CT-031) |

Related ADRs: [ADR-0021](../adr/0021-offer-address-families-explicitly-across-the-whole-service-path.md)

<a id="IPV6-003"></a>
## IPV6-003

Every offered address-family mode SHALL define local protocol controls, ICMPv6/PMTU treatment, transition-path restrictions and complete service/recovery dependencies; unsupported family combinations SHALL be rejected.

| Source field | Retained value |
| --- | --- |
| Accountable role | Network engineering |
| Parent sections | [RA §10](../architecture/reference/10-addressing-name-services-and-end-to-end-traffic.md) |
| Supplement homes | [NET §3](../engineering/fabric/3-worked-inter-zone-routing-and-enforcement-schedule.md) · [NET §4](../engineering/fabric/4-address-naming-and-protocol-family-decisions.md) · [SVC §2](../architecture/shared-services/2-name-time-initialization-and-telemetry-profiles.md) |
| Source IDs | S23; S24 |
| Wording disposition | Unchanged from v1.2 |
| Execution status | Specified, not executed by this release |
| Tests | [CT-018](test-specifications.md#CT-018) · [CT-031](test-specifications.md#CT-031) · [CT-032](test-specifications.md#CT-032) |

Related ADRs: [ADR-0021](../adr/0021-offer-address-families-explicitly-across-the-whole-service-path.md)

<a id="SVC-001"></a>
## SVC-001

Consumers SHALL NOT receive broad routing to a shared-services supernet solely because they consume one shared service.

| Source field | Retained value |
| --- | --- |
| Accountable role | Service operations |
| Parent sections | [RA §9](../architecture/reference/9-shared-services-ingress-and-controlled-egress.md) |
| Supplement homes | [SVC §1](../architecture/shared-services/1-shared-service-placement-and-consumption-boundaries.md) · [SVC §2](../architecture/shared-services/2-name-time-initialization-and-telemetry-profiles.md) |
| Source IDs | S00 |
| Wording disposition | Unchanged from v1.2 |
| Execution status | Specified, not executed by this release |
| Tests | [CT-008](test-specifications.md#CT-008) · [CT-037](test-specifications.md#CT-037) |

Related ADRs: [ADR-0010](../adr/0010-expose-shared-services-through-scoped-consumption-endpoints.md) · [ADR-0035](../adr/0035-make-shared-service-replies-select-the-originating-security-context.md)

<a id="SVC-002"></a>
## SVC-002

Where useful, shared services SHOULD expose zone-aligned endpoints so that consumption does not force unnecessary cross-zone routing.

| Source field | Retained value |
| --- | --- |
| Accountable role | Service operations |
| Parent sections | [RA §9](../architecture/reference/9-shared-services-ingress-and-controlled-egress.md) |
| Supplement homes | [SVC §1](../architecture/shared-services/1-shared-service-placement-and-consumption-boundaries.md) · [SVC §2](../architecture/shared-services/2-name-time-initialization-and-telemetry-profiles.md) |
| Source IDs | S00 |
| Wording disposition | Unchanged from v1.2 |
| Execution status | Specified, not executed by this release |
| Tests | [CT-008](test-specifications.md#CT-008) · [CT-025](test-specifications.md#CT-025) |

Related ADRs: [ADR-0010](../adr/0010-expose-shared-services-through-scoped-consumption-endpoints.md)

<a id="SVC-003"></a>
## SVC-003

Each ServiceProfile SHALL define direction, endpoint identity, authentication, allowed scope, availability, failure behavior and management separation; bindings SHALL be revoked when their entitlement or service version expires.

| Source field | Retained value |
| --- | --- |
| Accountable role | Service operations |
| Parent sections | [RA §9](../architecture/reference/9-shared-services-ingress-and-controlled-egress.md) |
| Supplement homes | [SVC §1](../architecture/shared-services/1-shared-service-placement-and-consumption-boundaries.md) · [SVC §2](../architecture/shared-services/2-name-time-initialization-and-telemetry-profiles.md) |
| Source IDs | S00 |
| Wording disposition | Unchanged from v1.2 |
| Execution status | Specified, not executed by this release |
| Tests | [CT-008](test-specifications.md#CT-008) · [CT-028](test-specifications.md#CT-028) · [CT-077](test-specifications.md#CT-077) |

Related ADRs: [ADR-0010](../adr/0010-expose-shared-services-through-scoped-consumption-endpoints.md) · [ADR-0035](../adr/0035-make-shared-service-replies-select-the-originating-security-context.md)

<a id="ING-001"></a>
## ING-001

A workload SHALL NOT obtain direct public ingress by attaching its internal Security Domain directly to a public network.

| Source field | Retained value |
| --- | --- |
| Accountable role | Security-edge operations |
| Parent sections | [RA §9](../architecture/reference/9-shared-services-ingress-and-controlled-egress.md) |
| Supplement homes | [SVC §1](../architecture/shared-services/1-shared-service-placement-and-consumption-boundaries.md) · [SVC §2](../architecture/shared-services/2-name-time-initialization-and-telemetry-profiles.md) |
| Source IDs | S00 |
| Wording disposition | Unchanged from v1.2 |
| Execution status | Specified, not executed by this release |
| Tests | [CT-006](test-specifications.md#CT-006) · [CT-025](test-specifications.md#CT-025) |

Related ADRs: [ADR-0022](../adr/0022-treat-public-access-and-egress-as-explicit-service-extensions.md)

<a id="ING-002"></a>
## ING-002

Public exposure SHALL be represented by an Exposure object with owner, protocol, endpoint, certificate/DNS dependencies, logging, security profile, and lifecycle state.

| Source field | Retained value |
| --- | --- |
| Accountable role | Service owner |
| Parent sections | [RA §9](../architecture/reference/9-shared-services-ingress-and-controlled-egress.md) |
| Supplement homes | [SVC §1](../architecture/shared-services/1-shared-service-placement-and-consumption-boundaries.md) · [SVC §2](../architecture/shared-services/2-name-time-initialization-and-telemetry-profiles.md) |
| Source IDs | S00 |
| Wording disposition | Unchanged from v1.2 |
| Execution status | Specified, not executed by this release |
| Tests | [CT-006](test-specifications.md#CT-006) · [CT-063](test-specifications.md#CT-063) |

Related ADRs: [ADR-0022](../adr/0022-treat-public-access-and-egress-as-explicit-service-extensions.md)

<a id="EGR-001"></a>
## EGR-001

Internet egress SHALL be deny-by-default and enabled only through an approved egress profile.

| Source field | Retained value |
| --- | --- |
| Accountable role | Security-edge operations |
| Parent sections | [RA §9](../architecture/reference/9-shared-services-ingress-and-controlled-egress.md) |
| Supplement homes | [SVC §1](../architecture/shared-services/1-shared-service-placement-and-consumption-boundaries.md) · [SVC §2](../architecture/shared-services/2-name-time-initialization-and-telemetry-profiles.md) |
| Source IDs | S00 |
| Wording disposition | Unchanged from v1.2 |
| Execution status | Specified, not executed by this release |
| Tests | [CT-005](test-specifications.md#CT-005) · [CT-064](test-specifications.md#CT-064) |

Related ADRs: [ADR-0022](../adr/0022-treat-public-access-and-egress-as-explicit-service-extensions.md)

<a id="EGR-002"></a>
## EGR-002

Egress telemetry SHALL permit attribution to the originating tenant/WSD and should preserve useful source identity where operationally feasible.

| Source field | Retained value |
| --- | --- |
| Accountable role | Security-edge operations |
| Parent sections | [RA §9](../architecture/reference/9-shared-services-ingress-and-controlled-egress.md) |
| Supplement homes | [SVC §1](../architecture/shared-services/1-shared-service-placement-and-consumption-boundaries.md) · [SVC §2](../architecture/shared-services/2-name-time-initialization-and-telemetry-profiles.md) |
| Source IDs | S00 |
| Wording disposition | Unchanged from v1.2 |
| Execution status | Specified, not executed by this release |
| Tests | [CT-010](test-specifications.md#CT-010) · [CT-064](test-specifications.md#CT-064) |

Related ADRs: [ADR-0022](../adr/0022-treat-public-access-and-egress-as-explicit-service-extensions.md)

<a id="EXP-001"></a>
## EXP-001

Exposure SHALL remain disabled until current-generation boundary, certificate, backend, logging and authorization gates pass; exposure revocation SHALL enforce the approved existing-session policy.

| Source field | Retained value |
| --- | --- |
| Accountable role | Security-edge operations |
| Parent sections | [RA §9](../architecture/reference/9-shared-services-ingress-and-controlled-egress.md) |
| Supplement homes | [SVC §1](../architecture/shared-services/1-shared-service-placement-and-consumption-boundaries.md) · [SVC §2](../architecture/shared-services/2-name-time-initialization-and-telemetry-profiles.md) |
| Source IDs | S00 |
| Wording disposition | Unchanged from v1.2 |
| Execution status | Specified, not executed by this release |
| Tests | [CT-063](test-specifications.md#CT-063) · [CT-069](test-specifications.md#CT-069) · [CT-077](test-specifications.md#CT-077) |

Related ADRs: [ADR-0015](../adr/0015-build-under-deny-and-verify-before-and-after-activation.md) · [ADR-0022](../adr/0022-treat-public-access-and-egress-as-explicit-service-extensions.md)

<a id="MICRO-001"></a>
## MICRO-001

WSD-to-WSD and tier-to-tier communication inside a shared Security Domain Instance SHALL be denied unless an approved policy explicitly permits it.

| Source field | Retained value |
| --- | --- |
| Accountable role | Platform engineering |
| Parent sections | [RA §7](../architecture/reference/7-tenant-environments-and-security-domain-placement.md) · [RA §11](../architecture/reference/11-compute-pools-hypervisors-and-workload-placement.md) |
| Supplement homes | [QUAL §3](site-qualification/3-capacity-service-envelopes-and-growth-triggers.md) · [VND §1](../engineering/platform-realizations/1-one-reference-environment-three-native-realizations.md) · [VND §2](../engineering/platform-realizations/2-physical-placement-and-the-sharing-decision.md) |
| Source IDs | S00 |
| Wording disposition | Unchanged from v1.2 |
| Execution status | Specified, not executed by this release |
| Tests | [CT-021](test-specifications.md#CT-021) · [CT-066](test-specifications.md#CT-066) |

Related ADRs: [ADR-0023](../adr/0023-protect-mandatory-policy-and-identity-selectors-from-tenant-mutation.md)

<a id="MICRO-002"></a>
## MICRO-002

Platform metadata used for security policy SHALL be managed, validated, and protected from unauthorized tenant modification.

| Source field | Retained value |
| --- | --- |
| Accountable role | Platform engineering |
| Parent sections | [RA §7](../architecture/reference/7-tenant-environments-and-security-domain-placement.md) · [RA §11](../architecture/reference/11-compute-pools-hypervisors-and-workload-placement.md) |
| Supplement homes | [QUAL §3](site-qualification/3-capacity-service-envelopes-and-growth-triggers.md) · [VND §1](../engineering/platform-realizations/1-one-reference-environment-three-native-realizations.md) · [VND §2](../engineering/platform-realizations/2-physical-placement-and-the-sharing-decision.md) |
| Source IDs | S00 |
| Wording disposition | Unchanged from v1.2 |
| Execution status | Specified, not executed by this release |
| Tests | [CT-020](test-specifications.md#CT-020) · [CT-066](test-specifications.md#CT-066) |

Related ADRs: [ADR-0023](../adr/0023-protect-mandatory-policy-and-identity-selectors-from-tenant-mutation.md)

<a id="MICRO-003"></a>
## MICRO-003

The platform SHALL prevent unapproved NIC, source-identity, privileged-workload and label changes from bypassing mandatory segmentation; effective policy SHALL be verified for same-host and cross-host traffic.

| Source field | Retained value |
| --- | --- |
| Accountable role | Platform engineering |
| Parent sections | [RA §7](../architecture/reference/7-tenant-environments-and-security-domain-placement.md) · [RA §11](../architecture/reference/11-compute-pools-hypervisors-and-workload-placement.md) |
| Supplement homes | [QUAL §3](site-qualification/3-capacity-service-envelopes-and-growth-triggers.md) · [VND §1](../engineering/platform-realizations/1-one-reference-environment-three-native-realizations.md) · [VND §2](../engineering/platform-realizations/2-physical-placement-and-the-sharing-decision.md) |
| Source IDs | S00 |
| Wording disposition | Unchanged from v1.2 |
| Execution status | Specified, not executed by this release |
| Tests | [CT-020](test-specifications.md#CT-020) · [CT-021](test-specifications.md#CT-021) · [CT-022](test-specifications.md#CT-022) · [CT-065](test-specifications.md#CT-065) |

Related ADRs: [ADR-0023](../adr/0023-protect-mandatory-policy-and-identity-selectors-from-tenant-mutation.md)

<a id="EDGE-001"></a>
## EDGE-001

Every domain-to-boundary attachment SHALL have a provider-owned EdgeAttachment record covering forwarding authority, isolation, MTU, HA, capacity and cleanup; consumers SHALL NOT choose its native topology identifiers.

| Source field | Retained value |
| --- | --- |
| Accountable role | Network engineering |
| Parent sections | [RA §8](../architecture/reference/8-zone-interfaces-routing-and-security-edge-topology.md) · [RA §16](../architecture/reference/16-nutanix-hosting-stack-reference-realization.md) · [RA §17](../architecture/reference/17-vmware-and-nsx-hosting-stack-reference-realization.md) · [RA §18](../architecture/reference/18-openstack-hosting-stack-reference-realization.md) |
| Supplement homes | [NET §2](../engineering/fabric/2-isolated-attachment-units-and-bounded-capacity.md) · [NET §3](../engineering/fabric/3-worked-inter-zone-routing-and-enforcement-schedule.md) · [VND §3](../engineering/platform-realizations/3-nutanix-component-path-and-lifecycle-realization.md) · [VND §4](../engineering/platform-realizations/4-vmware-nsx-isolated-upstream-routing-and-enforcement.md) · [VND §5](../engineering/platform-realizations/5-openstack-selected-services-backend-and-mandatory-policy.md) |
| Source IDs | S00 |
| Wording disposition | Unchanged from v1.2 |
| Execution status | Specified, not executed by this release |
| Tests | [CT-023](test-specifications.md#CT-023) · [CT-024](test-specifications.md#CT-024) · [CT-032](test-specifications.md#CT-032) · [CT-071](test-specifications.md#CT-071) |

Related ADRs: [ADR-0007](../adr/0007-allocate-isolated-domain-attachments-and-qualify-sharing.md)

<a id="EDGE-002"></a>
## EDGE-002

A shared attachment SHALL be prohibited unless direct connected, neighbor, gateway and NAT/PBR paths preserve the required domain isolation and ZIP enforcement in normal and failure states.

| Source field | Retained value |
| --- | --- |
| Accountable role | Security authority |
| Parent sections | [RA §8](../architecture/reference/8-zone-interfaces-routing-and-security-edge-topology.md) · [RA §16](../architecture/reference/16-nutanix-hosting-stack-reference-realization.md) · [RA §17](../architecture/reference/17-vmware-and-nsx-hosting-stack-reference-realization.md) · [RA §18](../architecture/reference/18-openstack-hosting-stack-reference-realization.md) |
| Supplement homes | [NET §2](../engineering/fabric/2-isolated-attachment-units-and-bounded-capacity.md) · [NET §3](../engineering/fabric/3-worked-inter-zone-routing-and-enforcement-schedule.md) · [VND §3](../engineering/platform-realizations/3-nutanix-component-path-and-lifecycle-realization.md) · [VND §4](../engineering/platform-realizations/4-vmware-nsx-isolated-upstream-routing-and-enforcement.md) · [VND §5](../engineering/platform-realizations/5-openstack-selected-services-backend-and-mandatory-policy.md) |
| Source IDs | S00 |
| Wording disposition | Unchanged from v1.2 |
| Execution status | Specified, not executed by this release |
| Tests | [CT-023](test-specifications.md#CT-023) · [CT-024](test-specifications.md#CT-024) · [CT-080](test-specifications.md#CT-080) |

Related ADRs: [ADR-0007](../adr/0007-allocate-isolated-domain-attachments-and-qualify-sharing.md) · [ADR-0035](../adr/0035-make-shared-service-replies-select-the-originating-security-context.md)

<a id="SITE-001"></a>
## SITE-001

Security Domain Instances SHOULD be site-local by default.

| Source field | Retained value |
| --- | --- |
| Accountable role | Platform engineering |
| Parent sections | [RA §14](../architecture/reference/14-availability-multi-site-operation-and-recovery-topology.md) · [RA §27](../architecture/reference/27-recovery-migration-and-retirement.md) |
| Supplement homes | [PROV §6](../implementation/provisioning-strategy/6-brownfield-adoption-growth-and-retirement.md) · [QUAL §4](site-qualification/4-service-parameter-and-requirement-decisions.md) · [SVC §4](../architecture/shared-services/4-storage-copies-and-retained-data-ownership.md) · [SVC §6](../architecture/shared-services/6-failure-recovery-migration-and-failback-topology.md) |
| Source IDs | S00 |
| Wording disposition | Unchanged from v1.2 |
| Execution status | Specified, not executed by this release |
| Tests | [CT-054](test-specifications.md#CT-054) · [CT-055](test-specifications.md#CT-055) |

Related ADRs: [ADR-0011](../adr/0011-default-to-site-local-domains-and-routed-recovery.md)

<a id="SITE-002"></a>
## SITE-002

Layer-2 stretch across sites SHALL require a documented application/availability requirement and failure-domain analysis.

| Source field | Retained value |
| --- | --- |
| Accountable role | Architecture authority |
| Parent sections | [RA §14](../architecture/reference/14-availability-multi-site-operation-and-recovery-topology.md) · [RA §27](../architecture/reference/27-recovery-migration-and-retirement.md) |
| Supplement homes | [PROV §6](../implementation/provisioning-strategy/6-brownfield-adoption-growth-and-retirement.md) · [QUAL §4](site-qualification/4-service-parameter-and-requirement-decisions.md) · [SVC §4](../architecture/shared-services/4-storage-copies-and-retained-data-ownership.md) · [SVC §6](../architecture/shared-services/6-failure-recovery-migration-and-failback-topology.md) |
| Source IDs | S00 |
| Wording disposition | Unchanged from v1.2 |
| Execution status | Specified, not executed by this release |
| Tests | [CT-054](test-specifications.md#CT-054) |

Related ADRs: [ADR-0011](../adr/0011-default-to-site-local-domains-and-routed-recovery.md)

<a id="SITE-003"></a>
## SITE-003

Recovery-site connectivity SHALL be pre-authorized and tested; emergency recovery SHALL NOT depend on ad hoc route leaking.

| Source field | Retained value |
| --- | --- |
| Accountable role | Recovery operations |
| Parent sections | [RA §14](../architecture/reference/14-availability-multi-site-operation-and-recovery-topology.md) · [RA §27](../architecture/reference/27-recovery-migration-and-retirement.md) |
| Supplement homes | [PROV §6](../implementation/provisioning-strategy/6-brownfield-adoption-growth-and-retirement.md) · [QUAL §4](site-qualification/4-service-parameter-and-requirement-decisions.md) · [SVC §4](../architecture/shared-services/4-storage-copies-and-retained-data-ownership.md) · [SVC §6](../architecture/shared-services/6-failure-recovery-migration-and-failback-topology.md) |
| Source IDs | S00 |
| Wording disposition | Unchanged from v1.2 |
| Execution status | Specified, not executed by this release |
| Tests | [CT-052](test-specifications.md#CT-052) · [CT-054](test-specifications.md#CT-054) |

Related ADRs: [ADR-0011](../adr/0011-default-to-site-local-domains-and-routed-recovery.md)

<a id="SITE-004"></a>
## SITE-004

Recovery placement SHALL preserve domain, co-residency, cryptographic, identity and location constraints; writer fencing and failback ownership SHALL be proven before production recovery is offered.

| Source field | Retained value |
| --- | --- |
| Accountable role | Recovery operations |
| Parent sections | [RA §14](../architecture/reference/14-availability-multi-site-operation-and-recovery-topology.md) · [RA §27](../architecture/reference/27-recovery-migration-and-retirement.md) |
| Supplement homes | [PROV §6](../implementation/provisioning-strategy/6-brownfield-adoption-growth-and-retirement.md) · [QUAL §4](site-qualification/4-service-parameter-and-requirement-decisions.md) · [SVC §4](../architecture/shared-services/4-storage-copies-and-retained-data-ownership.md) · [SVC §6](../architecture/shared-services/6-failure-recovery-migration-and-failback-topology.md) |
| Source IDs | S00 |
| Wording disposition | Unchanged from v1.2 |
| Execution status | Specified, not executed by this release |
| Tests | [CT-035](test-specifications.md#CT-035) · [CT-038](test-specifications.md#CT-038) · [CT-054](test-specifications.md#CT-054) · [CT-061](test-specifications.md#CT-061) |

Related ADRs: [ADR-0011](../adr/0011-default-to-site-local-domains-and-routed-recovery.md)

<a id="CMP-001"></a>
## CMP-001

Compute placement, maintenance evacuation, migration and HA restart SHALL enforce the approved tenant/domain/zone co-residency matrix; no scheduler action SHALL silently weaken it.

| Source field | Retained value |
| --- | --- |
| Accountable role | Platform engineering |
| Parent sections | [RA §7](../architecture/reference/7-tenant-environments-and-security-domain-placement.md) · [RA §11](../architecture/reference/11-compute-pools-hypervisors-and-workload-placement.md) |
| Supplement homes | [QUAL §3](site-qualification/3-capacity-service-envelopes-and-growth-triggers.md) · [VND §1](../engineering/platform-realizations/1-one-reference-environment-three-native-realizations.md) · [VND §2](../engineering/platform-realizations/2-physical-placement-and-the-sharing-decision.md) |
| Source IDs | S03 |
| Wording disposition | Unchanged from v1.2 |
| Execution status | Specified, not executed by this release |
| Tests | [CT-035](test-specifications.md#CT-035) · [CT-056](test-specifications.md#CT-056) |

Related ADRs: [ADR-0008](../adr/0008-preserve-zone-aware-host-placement-and-disclose-every-shared-layer.md)

<a id="CMP-002"></a>
## CMP-002

Each compute profile SHALL define supported hardware/software, boot/attestation controls, administrative isolation, resource guarantees, overcommit policy and handling of unsupported devices.

| Source field | Retained value |
| --- | --- |
| Accountable role | Platform engineering |
| Parent sections | [RA §7](../architecture/reference/7-tenant-environments-and-security-domain-placement.md) · [RA §11](../architecture/reference/11-compute-pools-hypervisors-and-workload-placement.md) |
| Supplement homes | [QUAL §3](site-qualification/3-capacity-service-envelopes-and-growth-triggers.md) · [VND §1](../engineering/platform-realizations/1-one-reference-environment-three-native-realizations.md) · [VND §2](../engineering/platform-realizations/2-physical-placement-and-the-sharing-decision.md) |
| Source IDs | S03; S07 |
| Wording disposition | Unchanged from v1.2 |
| Execution status | Specified, not executed by this release |
| Tests | [CT-036](test-specifications.md#CT-036) · [CT-039](test-specifications.md#CT-039) · [CT-073](test-specifications.md#CT-073) |

<a id="CMP-003"></a>
## CMP-003

The meaning of dedicated compute SHALL state its exact physical and administrative scope and disclose any shared storage, network, control, support or recovery dependency.

| Source field | Retained value |
| --- | --- |
| Accountable role | Architecture authority |
| Parent sections | [RA §7](../architecture/reference/7-tenant-environments-and-security-domain-placement.md) · [RA §11](../architecture/reference/11-compute-pools-hypervisors-and-workload-placement.md) |
| Supplement homes | [QUAL §3](site-qualification/3-capacity-service-envelopes-and-growth-triggers.md) · [VND §1](../engineering/platform-realizations/1-one-reference-environment-three-native-realizations.md) · [VND §2](../engineering/platform-realizations/2-physical-placement-and-the-sharing-decision.md) |
| Source IDs | S00 |
| Wording disposition | Unchanged from v1.2 |
| Execution status | Specified, not executed by this release |
| Tests | [CT-035](test-specifications.md#CT-035) · [CT-062](test-specifications.md#CT-062) |

Related ADRs: [ADR-0008](../adr/0008-preserve-zone-aware-host-placement-and-disclose-every-shared-layer.md)

<a id="STO-001"></a>
## STO-001

Every storage resource and derivative copy SHALL carry owner, categorization, access scope, key policy, placement/retention constraints and lineage; cross-scope attachment or export SHALL require explicit authorization.

| Source field | Retained value |
| --- | --- |
| Accountable role | Storage operations |
| Parent sections | [RA §12](../architecture/reference/12-storage-backup-and-data-isolation-architecture.md) |
| Supplement homes | [SVC §4](../architecture/shared-services/4-storage-copies-and-retained-data-ownership.md) · [SVC §5](../architecture/shared-services/5-backup-capture-independent-protection-and-isolated-restore.md) |
| Source IDs | S00 |
| Wording disposition | Unchanged from v1.2 |
| Execution status | Specified, not executed by this release |
| Tests | [CT-037](test-specifications.md#CT-037) · [CT-053](test-specifications.md#CT-053) · [CT-078](test-specifications.md#CT-078) |

Related ADRs: [ADR-0027](../adr/0027-separate-virtual-disk-guest-data-replication-and-administration-paths.md)

<a id="STO-002"></a>
## STO-002

Storage service profiles SHALL define measurable capacity/performance, consistency, replication, snapshot/clone and portability semantics and SHALL be tested under contention and the accepted failure condition.

| Source field | Retained value |
| --- | --- |
| Accountable role | Storage operations |
| Parent sections | [RA §12](../architecture/reference/12-storage-backup-and-data-isolation-architecture.md) |
| Supplement homes | [SVC §4](../architecture/shared-services/4-storage-copies-and-retained-data-ownership.md) · [SVC §5](../architecture/shared-services/5-backup-capture-independent-protection-and-isolated-restore.md) |
| Source IDs | S00 |
| Wording disposition | Unchanged from v1.2 |
| Execution status | Specified, not executed by this release |
| Tests | [CT-039](test-specifications.md#CT-039) · [CT-052](test-specifications.md#CT-052) · [CT-060](test-specifications.md#CT-060) |

Related ADRs: [ADR-0027](../adr/0027-separate-virtual-disk-guest-data-replication-and-administration-paths.md)

<a id="STO-003"></a>
## STO-003

Storage release and reuse SHALL reconcile all known copies and legal/administrative holds, apply an approved sanitization method and retain a receipt describing scope, method, verification and exceptions.

| Source field | Retained value |
| --- | --- |
| Accountable role | Storage operations |
| Parent sections | [RA §12](../architecture/reference/12-storage-backup-and-data-isolation-architecture.md) |
| Supplement homes | [SVC §4](../architecture/shared-services/4-storage-copies-and-retained-data-ownership.md) · [SVC §5](../architecture/shared-services/5-backup-capture-independent-protection-and-isolated-restore.md) |
| Source IDs | S27 |
| Wording disposition | Unchanged from v1.2 |
| Execution status | Specified, not executed by this release |
| Tests | [CT-053](test-specifications.md#CT-053) · [CT-059](test-specifications.md#CT-059) · [CT-078](test-specifications.md#CT-078) |

Related ADRs: [ADR-0027](../adr/0027-separate-virtual-disk-guest-data-replication-and-administration-paths.md) · [ADR-0033](../adr/0033-separate-live-service-retirement-from-retained-data-disposal.md)

<a id="IAM-001"></a>
## IAM-001

Human, workload and automation identities SHALL have separately scoped authorization, credential lifecycle and accountability; no tenant identity SHALL acquire provider foundation authority through role or group inheritance.

| Source field | Retained value |
| --- | --- |
| Accountable role | Identity operations |
| Parent sections | [RA §13](../architecture/reference/13-identity-cryptography-and-service-trust.md) |
| Supplement homes | [SVC §3](../architecture/shared-services/3-identity-certificates-keys-and-independent-recovery.md) |
| Source IDs | S07 |
| Wording disposition | Unchanged from v1.2 |
| Execution status | Specified, not executed by this release |
| Tests | [CT-019](test-specifications.md#CT-019) · [CT-027](test-specifications.md#CT-027) · [CT-028](test-specifications.md#CT-028) |

Related ADRs: [ADR-0029](../adr/0029-keep-recovery-trust-material-independent-of-the-platform-it-unlocks.md)

<a id="IAM-002"></a>
## IAM-002

Privileged access SHALL use the approved hardened path, strong authentication, least privilege and time-bound delegation; emergency and supplier access SHALL be logged, tested and revoked after use.

| Source field | Retained value |
| --- | --- |
| Accountable role | Identity operations |
| Parent sections | [RA §13](../architecture/reference/13-identity-cryptography-and-service-trust.md) |
| Supplement homes | [SVC §3](../architecture/shared-services/3-identity-certificates-keys-and-independent-recovery.md) |
| Source IDs | S07 |
| Wording disposition | Unchanged from v1.2 |
| Execution status | Specified, not executed by this release |
| Tests | [CT-026](test-specifications.md#CT-026) · [CT-027](test-specifications.md#CT-027) · [CT-079](test-specifications.md#CT-079) |

Related ADRs: [ADR-0009](../adr/0009-separate-management-security-platform-control-and-oob-recovery.md) · [ADR-0029](../adr/0029-keep-recovery-trust-material-independent-of-the-platform-it-unlocks.md)

<a id="IAM-003"></a>
## IAM-003

Credential and session revocation SHALL be verified at the consuming service within the approved propagation interval, including cached tokens and delegated grants.

| Source field | Retained value |
| --- | --- |
| Accountable role | Identity operations |
| Parent sections | [RA §13](../architecture/reference/13-identity-cryptography-and-service-trust.md) |
| Supplement homes | [SVC §3](../architecture/shared-services/3-identity-certificates-keys-and-independent-recovery.md) |
| Source IDs | S00 |
| Wording disposition | Unchanged from v1.2 |
| Execution status | Specified, not executed by this release |
| Tests | [CT-028](test-specifications.md#CT-028) · [CT-077](test-specifications.md#CT-077) · [CT-079](test-specifications.md#CT-079) |

<a id="CRY-001"></a>
## CRY-001

Protected data services SHALL enforce their versioned cryptographic profile at rest and in transit; the profile SHALL identify approved algorithms/modes, endpoint identity validation, module/operating-environment evidence and exceptions.

| Source field | Retained value |
| --- | --- |
| Accountable role | Security authority |
| Parent sections | [RA §13](../architecture/reference/13-identity-cryptography-and-service-trust.md) |
| Supplement homes | [SVC §3](../architecture/shared-services/3-identity-certificates-keys-and-independent-recovery.md) |
| Source IDs | S09; S10 |
| Wording disposition | Unchanged from v1.2 |
| Execution status | Specified, not executed by this release |
| Tests | [CT-028](test-specifications.md#CT-028) · [CT-038](test-specifications.md#CT-038) · [CT-063](test-specifications.md#CT-063) |

Related ADRs: [ADR-0029](../adr/0029-keep-recovery-trust-material-independent-of-the-platform-it-unlocks.md)

<a id="CRY-002"></a>
## CRY-002

Key use, administration, recovery and destruction SHALL have explicit separated authority and dependency records; key destruction SHALL NOT invalidate required retained-data recovery without an approved disposition decision.

| Source field | Retained value |
| --- | --- |
| Accountable role | Key-management operations |
| Parent sections | [RA §13](../architecture/reference/13-identity-cryptography-and-service-trust.md) |
| Supplement homes | [SVC §3](../architecture/shared-services/3-identity-certificates-keys-and-independent-recovery.md) |
| Source IDs | S09 |
| Wording disposition | Unchanged from v1.2 |
| Execution status | Specified, not executed by this release |
| Tests | [CT-038](test-specifications.md#CT-038) · [CT-053](test-specifications.md#CT-053) · [CT-059](test-specifications.md#CT-059) |

Related ADRs: [ADR-0029](../adr/0029-keep-recovery-trust-material-independent-of-the-platform-it-unlocks.md)

<a id="CRY-003"></a>
## CRY-003

KMS/trust-service outage behavior SHALL be tested and SHALL NOT enable plaintext fallback; cryptographic inventory, certificate rotation and algorithm-transition plans SHALL be maintained.

| Source field | Retained value |
| --- | --- |
| Accountable role | Key-management operations |
| Parent sections | [RA §13](../architecture/reference/13-identity-cryptography-and-service-trust.md) |
| Supplement homes | [SVC §3](../architecture/shared-services/3-identity-certificates-keys-and-independent-recovery.md) |
| Source IDs | S09; S10 |
| Wording disposition | Unchanged from v1.2 |
| Execution status | Specified, not executed by this release |
| Tests | [CT-028](test-specifications.md#CT-028) · [CT-038](test-specifications.md#CT-038) · [CT-055](test-specifications.md#CT-055) |

Related ADRs: [ADR-0029](../adr/0029-keep-recovery-trust-material-independent-of-the-platform-it-unlocks.md)

<a id="IMG-001"></a>
## IMG-001

Only approved versioned images and baselines SHALL be deployed; each SHALL include provenance, digest, support status, hardening and vulnerability disposition with a retirement/rebuild policy.

| Source field | Retained value |
| --- | --- |
| Accountable role | Platform engineering |
| Parent sections | [RA §11](../architecture/reference/11-compute-pools-hypervisors-and-workload-placement.md) |
| Supplement homes | [QUAL §3](site-qualification/3-capacity-service-envelopes-and-growth-triggers.md) · [VND §2](../engineering/platform-realizations/2-physical-placement-and-the-sharing-decision.md) |
| Source IDs | S07 |
| Wording disposition | Unchanged from v1.2 |
| Execution status | Specified, not executed by this release |
| Tests | [CT-036](test-specifications.md#CT-036) · [CT-040](test-specifications.md#CT-040) · [CT-041](test-specifications.md#CT-041) |

<a id="IMG-002"></a>
## IMG-002

Runtime configuration SHALL be verified against the required baseline after provisioning and material change; unsupported protection agents or disabled mandatory controls SHALL not be silently accepted.

| Source field | Retained value |
| --- | --- |
| Accountable role | Platform engineering |
| Parent sections | [RA §11](../architecture/reference/11-compute-pools-hypervisors-and-workload-placement.md) |
| Supplement homes | [QUAL §3](site-qualification/3-capacity-service-envelopes-and-growth-triggers.md) · [VND §2](../engineering/platform-realizations/2-physical-placement-and-the-sharing-decision.md) |
| Source IDs | S00 |
| Wording disposition | Unchanged from v1.2 |
| Execution status | Specified, not executed by this release |
| Tests | [CT-014](test-specifications.md#CT-014) · [CT-036](test-specifications.md#CT-036) · [CT-040](test-specifications.md#CT-040) |

<a id="BKP-001"></a>
## BKP-001

Backup consumers SHALL NOT receive connectivity to backup management interfaces merely because they consume backup service.

| Source field | Retained value |
| --- | --- |
| Accountable role | Backup operations |
| Parent sections | [RA §12](../architecture/reference/12-storage-backup-and-data-isolation-architecture.md) · [RA §27](../architecture/reference/27-recovery-migration-and-retirement.md) |
| Supplement homes | [PROV §6](../implementation/provisioning-strategy/6-brownfield-adoption-growth-and-retirement.md) · [SVC §4](../architecture/shared-services/4-storage-copies-and-retained-data-ownership.md) · [SVC §5](../architecture/shared-services/5-backup-capture-independent-protection-and-isolated-restore.md) · [SVC §6](../architecture/shared-services/6-failure-recovery-migration-and-failback-topology.md) |
| Source IDs | S00 |
| Wording disposition | Unchanged from v1.2 |
| Execution status | Specified, not executed by this release |
| Tests | [CT-004](test-specifications.md#CT-004) · [CT-051](test-specifications.md#CT-051) |

Related ADRs: [ADR-0028](../adr/0028-protect-backup-administration-and-prove-isolated-usable-restore.md)

<a id="BKP-002"></a>
## BKP-002

Restore workflows SHALL enforce the same tenant, security-zone, identity, and evidence controls as backup ingestion.

| Source field | Retained value |
| --- | --- |
| Accountable role | Backup operations |
| Parent sections | [RA §12](../architecture/reference/12-storage-backup-and-data-isolation-architecture.md) · [RA §27](../architecture/reference/27-recovery-migration-and-retirement.md) |
| Supplement homes | [PROV §6](../implementation/provisioning-strategy/6-brownfield-adoption-growth-and-retirement.md) · [SVC §4](../architecture/shared-services/4-storage-copies-and-retained-data-ownership.md) · [SVC §5](../architecture/shared-services/5-backup-capture-independent-protection-and-isolated-restore.md) · [SVC §6](../architecture/shared-services/6-failure-recovery-migration-and-failback-topology.md) |
| Source IDs | S00 |
| Wording disposition | Unchanged from v1.2 |
| Execution status | Specified, not executed by this release |
| Tests | [CT-052](test-specifications.md#CT-052) · [CT-054](test-specifications.md#CT-054) |

Related ADRs: [ADR-0028](../adr/0028-protect-backup-administration-and-prove-isolated-usable-restore.md)

<a id="BKP-003"></a>
## BKP-003

Every protected production WSD SHALL have a BackupPolicy with consistency, retention, location, key and protected-copy requirements; successful isolated restore SHALL be demonstrated at the policy cadence.

| Source field | Retained value |
| --- | --- |
| Accountable role | Backup operations |
| Parent sections | [RA §12](../architecture/reference/12-storage-backup-and-data-isolation-architecture.md) · [RA §27](../architecture/reference/27-recovery-migration-and-retirement.md) |
| Supplement homes | [PROV §6](../implementation/provisioning-strategy/6-brownfield-adoption-growth-and-retirement.md) · [SVC §4](../architecture/shared-services/4-storage-copies-and-retained-data-ownership.md) · [SVC §5](../architecture/shared-services/5-backup-capture-independent-protection-and-isolated-restore.md) · [SVC §6](../architecture/shared-services/6-failure-recovery-migration-and-failback-topology.md) |
| Source IDs | S00 |
| Wording disposition | Unchanged from v1.2 |
| Execution status | Specified, not executed by this release |
| Tests | [CT-051](test-specifications.md#CT-051) · [CT-052](test-specifications.md#CT-052) · [CT-053](test-specifications.md#CT-053) |

Related ADRs: [ADR-0028](../adr/0028-protect-backup-administration-and-prove-isolated-usable-restore.md)

<a id="BKP-004"></a>
## BKP-004

Production credentials SHALL NOT be able to destroy or reduce the protection of recovery copies designated independent/immutable; retained copies SHALL keep the keys and catalogue required for authorized recovery.

| Source field | Retained value |
| --- | --- |
| Accountable role | Backup operations |
| Parent sections | [RA §12](../architecture/reference/12-storage-backup-and-data-isolation-architecture.md) · [RA §27](../architecture/reference/27-recovery-migration-and-retirement.md) |
| Supplement homes | [PROV §6](../implementation/provisioning-strategy/6-brownfield-adoption-growth-and-retirement.md) · [SVC §4](../architecture/shared-services/4-storage-copies-and-retained-data-ownership.md) · [SVC §5](../architecture/shared-services/5-backup-capture-independent-protection-and-isolated-restore.md) · [SVC §6](../architecture/shared-services/6-failure-recovery-migration-and-failback-topology.md) |
| Source IDs | S00 |
| Wording disposition | Unchanged from v1.2 |
| Execution status | Specified, not executed by this release |
| Tests | [CT-038](test-specifications.md#CT-038) · [CT-051](test-specifications.md#CT-051) · [CT-053](test-specifications.md#CT-053) |

Related ADRs: [ADR-0028](../adr/0028-protect-backup-administration-and-prove-isolated-usable-restore.md)

<a id="REL-001"></a>
## REL-001

Availability and recovery profiles SHALL define measurement scope, SLO, failure tolerance, maintenance treatment, RTO/RPO, consistency, dependencies and test cadence; impact categorization SHALL NOT substitute for these values.

| Source field | Retained value |
| --- | --- |
| Accountable role | Service owner |
| Parent sections | [RA §14](../architecture/reference/14-availability-multi-site-operation-and-recovery-topology.md) · [RA §26](../architecture/reference/26-operating-model-capacity-and-observability.md) |
| Supplement homes | [QUAL §3](site-qualification/3-capacity-service-envelopes-and-growth-triggers.md) · [QUAL §4](site-qualification/4-service-parameter-and-requirement-decisions.md) · [QUAL §7](site-qualification/7-operating-accountability-handover-and-change.md) · [SVC §6](../architecture/shared-services/6-failure-recovery-migration-and-failback-topology.md) |
| Source IDs | S00 |
| Wording disposition | Unchanged from v1.2 |
| Execution status | Specified, not executed by this release |
| Tests | [CT-012](test-specifications.md#CT-012) · [CT-052](test-specifications.md#CT-052) · [CT-054](test-specifications.md#CT-054) · [CT-062](test-specifications.md#CT-062) |

Related ADRs: [ADR-0019](../adr/0019-separate-information-impacts-from-service-level-and-recovery-promises.md) · [ADR-0036](../adr/0036-require-initial-operational-and-recovery-readiness-before-production-activation.md)

<a id="REL-002"></a>
## REL-002

Recovery/HA capabilities SHALL be measured under the approved load and failure scenario before a platform offers the profile; reported SLOs SHALL disclose exclusions and actual breaches.

| Source field | Retained value |
| --- | --- |
| Accountable role | Operations/SRE |
| Parent sections | [RA §14](../architecture/reference/14-availability-multi-site-operation-and-recovery-topology.md) · [RA §26](../architecture/reference/26-operating-model-capacity-and-observability.md) |
| Supplement homes | [QUAL §3](site-qualification/3-capacity-service-envelopes-and-growth-triggers.md) · [QUAL §4](site-qualification/4-service-parameter-and-requirement-decisions.md) · [QUAL §7](site-qualification/7-operating-accountability-handover-and-change.md) · [SVC §6](../architecture/shared-services/6-failure-recovery-migration-and-failback-topology.md) |
| Source IDs | S00 |
| Wording disposition | Unchanged from v1.2 |
| Execution status | Specified, not executed by this release |
| Tests | [CT-012](test-specifications.md#CT-012) · [CT-039](test-specifications.md#CT-039) · [CT-054](test-specifications.md#CT-054) · [CT-056](test-specifications.md#CT-056) |

<a id="PLACE-001"></a>
## PLACE-001

Placement SHALL satisfy all mandatory security, assurance, location, lifecycle, capacity and recovery constraints using a current qualified platform profile; unresolved or conflicting constraints SHALL reject the request.

| Source field | Retained value |
| --- | --- |
| Accountable role | Automation platform |
| Parent sections | [RA §13](../architecture/reference/13-identity-cryptography-and-service-trust.md) · [RA §14](../architecture/reference/14-availability-multi-site-operation-and-recovery-topology.md) |
| Supplement homes | [QUAL §4](site-qualification/4-service-parameter-and-requirement-decisions.md) · [SVC §3](../architecture/shared-services/3-identity-certificates-keys-and-independent-recovery.md) · [SVC §6](../architecture/shared-services/6-failure-recovery-migration-and-failback-topology.md) |
| Source IDs | S00 |
| Wording disposition | Unchanged from v1.2 |
| Execution status | Specified, not executed by this release |
| Tests | [CT-018](test-specifications.md#CT-018) · [CT-035](test-specifications.md#CT-035) · [CT-056](test-specifications.md#CT-056) · [CT-061](test-specifications.md#CT-061) |

<a id="PLACE-002"></a>
## PLACE-002

Data, backup, telemetry, diagnostic, control-plane, administrative-access and key locations/control constraints SHALL be represented separately and enforced through approved profiles and agreements.

| Source field | Retained value |
| --- | --- |
| Accountable role | Service owner |
| Parent sections | [RA §13](../architecture/reference/13-identity-cryptography-and-service-trust.md) · [RA §14](../architecture/reference/14-availability-multi-site-operation-and-recovery-topology.md) |
| Supplement homes | [QUAL §4](site-qualification/4-service-parameter-and-requirement-decisions.md) · [SVC §3](../architecture/shared-services/3-identity-certificates-keys-and-independent-recovery.md) · [SVC §6](../architecture/shared-services/6-failure-recovery-migration-and-failback-topology.md) |
| Source IDs | S00 |
| Wording disposition | Unchanged from v1.2 |
| Execution status | Specified, not executed by this release |
| Tests | [CT-061](test-specifications.md#CT-061) · [CT-079](test-specifications.md#CT-079) |

<a id="PLACE-003"></a>
## PLACE-003

Each portable service class SHALL have a documented exit path, declared proprietary dependencies and representative export/recovery evidence; residency or format support alone SHALL NOT be presented as portability or sovereignty proof.

| Source field | Retained value |
| --- | --- |
| Accountable role | Architecture authority |
| Parent sections | [RA §13](../architecture/reference/13-identity-cryptography-and-service-trust.md) · [RA §14](../architecture/reference/14-availability-multi-site-operation-and-recovery-topology.md) |
| Supplement homes | [QUAL §4](site-qualification/4-service-parameter-and-requirement-decisions.md) · [SVC §3](../architecture/shared-services/3-identity-certificates-keys-and-independent-recovery.md) · [SVC §6](../architecture/shared-services/6-failure-recovery-migration-and-failback-topology.md) |
| Source IDs | S00 |
| Wording disposition | Unchanged from v1.2 |
| Execution status | Specified, not executed by this release |
| Tests | [CT-060](test-specifications.md#CT-060) · [CT-073](test-specifications.md#CT-073) |

<a id="SVCM-001"></a>
## SVCM-001

The service catalogue SHALL publish entitlements, hard quotas, reservation semantics, availability/recovery targets, supported capabilities and lifecycle obligations with stable service identifiers.

| Source field | Retained value |
| --- | --- |
| Accountable role | Service owner |
| Parent sections | [RA §4](../architecture/reference/4-hosting-cells-resource-pools-and-failure-boundaries.md) · [RA §20](../architecture/reference/20-provisioning-model-and-infrastructure-work-packages.md) |
| Supplement homes | [NET §2](../engineering/fabric/2-isolated-attachment-units-and-bounded-capacity.md) · [PROV §1](../implementation/provisioning-strategy/1-provisioning-scopes-ownership-and-accepted-handoffs.md) · [QUAL §2](site-qualification/2-site-low-level-design-and-dependency-schedule.md) · [QUAL §3](site-qualification/3-capacity-service-envelopes-and-growth-triggers.md) |
| Source IDs | S00 |
| Wording disposition | Unchanged from v1.2 |
| Execution status | Specified, not executed by this release |
| Tests | [CT-019](test-specifications.md#CT-019) · [CT-056](test-specifications.md#CT-056) · [CT-062](test-specifications.md#CT-062) |

Related ADRs: [ADR-0030](../adr/0030-admit-demand-against-every-surviving-capacity-bottleneck.md)

<a id="SVCM-002"></a>
## SVCM-002

Capacity inventory SHALL reconcile procured, staged, commissioned, available, reserved and consumed resources and SHALL report unused/stranded capacity, ownership and support-life exposure.

| Source field | Retained value |
| --- | --- |
| Accountable role | Capacity management |
| Parent sections | [RA §4](../architecture/reference/4-hosting-cells-resource-pools-and-failure-boundaries.md) · [RA §20](../architecture/reference/20-provisioning-model-and-infrastructure-work-packages.md) |
| Supplement homes | [NET §2](../engineering/fabric/2-isolated-attachment-units-and-bounded-capacity.md) · [PROV §1](../implementation/provisioning-strategy/1-provisioning-scopes-ownership-and-accepted-handoffs.md) · [QUAL §2](site-qualification/2-site-low-level-design-and-dependency-schedule.md) · [QUAL §3](site-qualification/3-capacity-service-envelopes-and-growth-triggers.md) |
| Source IDs | S00 |
| Wording disposition | Unchanged from v1.2 |
| Execution status | Specified, not executed by this release |
| Tests | [CT-074](test-specifications.md#CT-074) |

Related ADRs: [ADR-0004](../adr/0004-scale-through-commissioned-hosting-cells-and-capacity-pools.md)

<a id="RESP-001"></a>
## RESP-001

Every applicable infrastructure/application control and recovery dependency SHALL have a provider, tenant or shared responsibility assignment and evidence owner; unresolved mandatory responsibilities SHALL block Service Ready.

| Source field | Retained value |
| --- | --- |
| Accountable role | Service owner |
| Parent sections | [RA §23](../architecture/reference/23-tenant-domain-and-workload-provisioning-sequence.md) · [RA §26](../architecture/reference/26-operating-model-capacity-and-observability.md) |
| Supplement homes | [PROV §4](../implementation/provisioning-strategy/4-end-to-end-fixture-provisioning-and-safe-activation.md) · [QUAL §3](site-qualification/3-capacity-service-envelopes-and-growth-triggers.md) · [QUAL §7](site-qualification/7-operating-accountability-handover-and-change.md) · [VND §1](../engineering/platform-realizations/1-one-reference-environment-three-native-realizations.md) |
| Source IDs | S05; S08 |
| Wording disposition | Unchanged from v1.2 |
| Execution status | Specified, not executed by this release |
| Tests | [CT-062](test-specifications.md#CT-062) · [CT-069](test-specifications.md#CT-069) |

<a id="FAB-001"></a>
## FAB-001

Routine create, update and retirement of tenants/WSDs in a precommissioned overlay service class SHALL NOT require leaf/spine configuration changes; foundation growth and fabric-routed service classes SHALL use separately authorized workflows.

| Source field | Retained value |
| --- | --- |
| Accountable role | Network engineering |
| Parent sections | [RA §5](../architecture/reference/5-physical-fabric-and-platform-attachment.md) |
| Supplement homes | [NET §1](../engineering/fabric/1-transport-routing-and-overlay-ownership.md) · [NET §2](../engineering/fabric/2-isolated-attachment-units-and-bounded-capacity.md) · [NET §5](../engineering/fabric/5-mtu-performance-and-failure-engineering.md) |
| Source IDs | S00 |
| Wording disposition | Unchanged from v1.2 |
| Execution status | Specified, not executed by this release |
| Tests | [CT-071](test-specifications.md#CT-071) · [CT-072](test-specifications.md#CT-072) |

Related ADRs: [ADR-0004](../adr/0004-scale-through-commissioned-hosting-cells-and-capacity-pools.md)

<a id="FAB-002"></a>
## FAB-002

A physical VRF SHALL be created only when the physical fabric itself must provide L3 routing for a legitimate routing/security domain.

| Source field | Retained value |
| --- | --- |
| Accountable role | Network engineering |
| Parent sections | [RA §5](../architecture/reference/5-physical-fabric-and-platform-attachment.md) |
| Supplement homes | [NET §1](../engineering/fabric/1-transport-routing-and-overlay-ownership.md) · [NET §2](../engineering/fabric/2-isolated-attachment-units-and-bounded-capacity.md) · [NET §5](../engineering/fabric/5-mtu-performance-and-failure-engineering.md) |
| Source IDs | S00 |
| Wording disposition | Unchanged from v1.2 |
| Execution status | Specified, not executed by this release |
| Tests | [CT-009](test-specifications.md#CT-009) · [CT-072](test-specifications.md#CT-072) |

<a id="FAB-003"></a>
## FAB-003

Function names such as backup, migration, platform, ZIP, or generic transit SHALL NOT by themselves justify a VRF.

| Source field | Retained value |
| --- | --- |
| Accountable role | Architecture authority |
| Parent sections | [RA §5](../architecture/reference/5-physical-fabric-and-platform-attachment.md) |
| Supplement homes | [NET §1](../engineering/fabric/1-transport-routing-and-overlay-ownership.md) · [NET §2](../engineering/fabric/2-isolated-attachment-units-and-bounded-capacity.md) · [NET §5](../engineering/fabric/5-mtu-performance-and-failure-engineering.md) |
| Source IDs | S00 |
| Wording disposition | Unchanged from v1.2 |
| Execution status | Specified, not executed by this release |
| Tests | [CT-025](test-specifications.md#CT-025) · [CT-072](test-specifications.md#CT-072) |

Related ADRs: [ADR-0012](../adr/0012-distinguish-persistent-platform-transports-from-temporary-migration-access.md)

<a id="FAB-004"></a>
## FAB-004

The fabric profile SHALL define addressing/routing authority, control-plane protection, MTU, fault convergence, management isolation, maintenance and measured scale before platform commissioning.

| Source field | Retained value |
| --- | --- |
| Accountable role | Network engineering |
| Parent sections | [RA §5](../architecture/reference/5-physical-fabric-and-platform-attachment.md) |
| Supplement homes | [NET §1](../engineering/fabric/1-transport-routing-and-overlay-ownership.md) · [NET §2](../engineering/fabric/2-isolated-attachment-units-and-bounded-capacity.md) · [NET §5](../engineering/fabric/5-mtu-performance-and-failure-engineering.md) |
| Source IDs | S20; S21; S22 |
| Wording disposition | Unchanged from v1.2 |
| Execution status | Specified, not executed by this release |
| Tests | [CT-026](test-specifications.md#CT-026) · [CT-032](test-specifications.md#CT-032) · [CT-033](test-specifications.md#CT-033) · [CT-034](test-specifications.md#CT-034) |

<a id="EVPN-001"></a>
## EVPN-001

When EVPN is used, RD/RT/VNI, gateway and multihoming policies SHALL be provider-owned, collision-checked and domain-scoped; unapproved route imports SHALL be denied.

| Source field | Retained value |
| --- | --- |
| Accountable role | Network engineering |
| Parent sections | [RA §5](../architecture/reference/5-physical-fabric-and-platform-attachment.md) |
| Supplement homes | [NET §1](../engineering/fabric/1-transport-routing-and-overlay-ownership.md) · [NET §2](../engineering/fabric/2-isolated-attachment-units-and-bounded-capacity.md) · [NET §5](../engineering/fabric/5-mtu-performance-and-failure-engineering.md) |
| Source IDs | S20; S21; S22 |
| Wording disposition | Unchanged from v1.2 |
| Execution status | Specified, not executed by this release |
| Tests | [CT-009](test-specifications.md#CT-009) · [CT-033](test-specifications.md#CT-033) · [CT-072](test-specifications.md#CT-072) |

Related ADRs: [ADR-0005](../adr/0005-keep-vendor-overlays-local-and-connect-through-controlled-handoffs.md)

<a id="EVPN-002"></a>
## EVPN-002

Every multihoming and border interoperability profile SHALL be tested for split-brain, link/peer failure, MTU, route withdrawal and stateful-path behavior; vendor-specific MLAG interoperability SHALL NOT be assumed.

| Source field | Retained value |
| --- | --- |
| Accountable role | Network engineering |
| Parent sections | [RA §5](../architecture/reference/5-physical-fabric-and-platform-attachment.md) |
| Supplement homes | [NET §1](../engineering/fabric/1-transport-routing-and-overlay-ownership.md) · [NET §2](../engineering/fabric/2-isolated-attachment-units-and-bounded-capacity.md) · [NET §5](../engineering/fabric/5-mtu-performance-and-failure-engineering.md) |
| Source IDs | S21; S22 |
| Wording disposition | Unchanged from v1.2 |
| Execution status | Specified, not executed by this release |
| Tests | [CT-024](test-specifications.md#CT-024) · [CT-032](test-specifications.md#CT-032) · [CT-034](test-specifications.md#CT-034) |

Related ADRs: [ADR-0005](../adr/0005-keep-vendor-overlays-local-and-connect-through-controlled-handoffs.md)

<a id="PORT-001"></a>
## PORT-001

Every platform SHALL publish a machine-readable capability profile and a tested implementation profile.

| Source field | Retained value |
| --- | --- |
| Accountable role | Platform engineering |
| Parent sections | [RA §15](../architecture/reference/15-cross-vendor-realization-model.md) · [RA §28](../architecture/reference/28-architecture-acceptance-and-verification.md) |
| Supplement homes | [QUAL §5](site-qualification/5-qualification-stages-applicability-and-evidence.md) · [QUAL §6](site-qualification/6-control-inheritance-assurance-and-organizational-interfaces.md) · [VND §1](../engineering/platform-realizations/1-one-reference-environment-three-native-realizations.md) · [VND §6](../engineering/platform-realizations/6-portable-composite-and-migrated-service-choices.md) · [VND §7](../engineering/platform-realizations/7-implementation-tuple-and-decision-package.md) |
| Source IDs | S00 |
| Wording disposition | Unchanged from v1.2 |
| Execution status | Specified, not executed by this release |
| Tests | [CT-015](test-specifications.md#CT-015) · [CT-018](test-specifications.md#CT-018) · [CT-080](test-specifications.md#CT-080) |

<a id="PORT-002"></a>
## PORT-002

A placement decision SHALL fail rather than silently reduce a requested security or availability capability.

| Source field | Retained value |
| --- | --- |
| Accountable role | Automation platform |
| Parent sections | [RA §15](../architecture/reference/15-cross-vendor-realization-model.md) · [RA §28](../architecture/reference/28-architecture-acceptance-and-verification.md) |
| Supplement homes | [QUAL §5](site-qualification/5-qualification-stages-applicability-and-evidence.md) · [QUAL §6](site-qualification/6-control-inheritance-assurance-and-organizational-interfaces.md) · [VND §1](../engineering/platform-realizations/1-one-reference-environment-three-native-realizations.md) · [VND §6](../engineering/platform-realizations/6-portable-composite-and-migrated-service-choices.md) · [VND §7](../engineering/platform-realizations/7-implementation-tuple-and-decision-package.md) |
| Source IDs | S00 |
| Wording disposition | Unchanged from v1.2 |
| Execution status | Specified, not executed by this release |
| Tests | [CT-018](test-specifications.md#CT-018) · [CT-061](test-specifications.md#CT-061) |

<a id="PORT-003"></a>
## PORT-003

Platform-specific features MAY be exposed as optional extensions provided the WSD declares the dependency and portability impact.

| Source field | Retained value |
| --- | --- |
| Accountable role | Architecture authority |
| Parent sections | [RA §15](../architecture/reference/15-cross-vendor-realization-model.md) · [RA §28](../architecture/reference/28-architecture-acceptance-and-verification.md) |
| Supplement homes | [QUAL §5](site-qualification/5-qualification-stages-applicability-and-evidence.md) · [QUAL §6](site-qualification/6-control-inheritance-assurance-and-organizational-interfaces.md) · [VND §1](../engineering/platform-realizations/1-one-reference-environment-three-native-realizations.md) · [VND §6](../engineering/platform-realizations/6-portable-composite-and-migrated-service-choices.md) · [VND §7](../engineering/platform-realizations/7-implementation-tuple-and-decision-package.md) |
| Source IDs | S00 |
| Wording disposition | Unchanged from v1.2 |
| Execution status | Specified, not executed by this release |
| Tests | [CT-016](test-specifications.md#CT-016) · [CT-060](test-specifications.md#CT-060) · [CT-073](test-specifications.md#CT-073) |

Related ADRs: [ADR-0005](../adr/0005-keep-vendor-overlays-local-and-connect-through-controlled-handoffs.md)

<a id="QUAL-001"></a>
## QUAL-001

Production placement SHALL require a current qualified PlatformProfile containing the exact product/API/provider/hardware tuple, applicable features/licenses, tested limits, evidence and approval; a candidate or documentation snapshot SHALL be ineligible.

| Source field | Retained value |
| --- | --- |
| Accountable role | Security authority |
| Parent sections | [RA §15](../architecture/reference/15-cross-vendor-realization-model.md) · [RA §28](../architecture/reference/28-architecture-acceptance-and-verification.md) |
| Supplement homes | [QUAL §5](site-qualification/5-qualification-stages-applicability-and-evidence.md) · [QUAL §6](site-qualification/6-control-inheritance-assurance-and-organizational-interfaces.md) · [VND §1](../engineering/platform-realizations/1-one-reference-environment-three-native-realizations.md) · [VND §6](../engineering/platform-realizations/6-portable-composite-and-migrated-service-choices.md) · [VND §7](../engineering/platform-realizations/7-implementation-tuple-and-decision-package.md) |
| Source IDs | S00 |
| Wording disposition | Unchanged from v1.2 |
| Execution status | Specified, not executed by this release |
| Tests | [CT-015](test-specifications.md#CT-015) · [CT-018](test-specifications.md#CT-018) · [CT-069](test-specifications.md#CT-069) |

Related ADRs: [ADR-0014](../adr/0014-bootstrap-management-and-trust-before-consuming-native-apis.md)

<a id="NUT-001"></a>
## NUT-001

New Nutanix automation SHOULD use current supported v2/v4-backed provider resources where those resources satisfy the requirement; legacy resources require an explicit compatibility rationale.

| Source field | Retained value |
| --- | --- |
| Accountable role | Platform engineering |
| Parent sections | [RA §16](../architecture/reference/16-nutanix-hosting-stack-reference-realization.md) |
| Supplement homes | [VND §3](../engineering/platform-realizations/3-nutanix-component-path-and-lifecycle-realization.md) |
| Source IDs | S00; S17 |
| Wording disposition | Unchanged from v1.2 |
| Execution status | Specified, not executed by this release |
| Tests | [CT-015](test-specifications.md#CT-015) · [CT-018](test-specifications.md#CT-018) |

Related ADRs: [ADR-0024](../adr/0024-use-independent-nutanix-vpc-domain-realizations-with-qualified-handoffs.md)

<a id="NUT-002"></a>
## NUT-002

Nutanix VPC internal routing SHALL NOT be used to bypass a required inter-zone ZIP.

| Source field | Retained value |
| --- | --- |
| Accountable role | Platform engineering |
| Parent sections | [RA §16](../architecture/reference/16-nutanix-hosting-stack-reference-realization.md) |
| Supplement homes | [VND §3](../engineering/platform-realizations/3-nutanix-component-path-and-lifecycle-realization.md) |
| Source IDs | S00 |
| Wording disposition | Unchanged from v1.2 |
| Execution status | Specified, not executed by this release |
| Tests | [CT-003](test-specifications.md#CT-003) · [CT-023](test-specifications.md#CT-023) · [CT-024](test-specifications.md#CT-024) |

Related ADRs: [ADR-0007](../adr/0007-allocate-isolated-domain-attachments-and-qualify-sharing.md) · [ADR-0024](../adr/0024-use-independent-nutanix-vpc-domain-realizations-with-qualified-handoffs.md)

<a id="NUT-003"></a>
## NUT-003

Provider-managed categories/metadata used for security SHALL be protected from tenant modification.

| Source field | Retained value |
| --- | --- |
| Accountable role | Platform engineering |
| Parent sections | [RA §16](../architecture/reference/16-nutanix-hosting-stack-reference-realization.md) |
| Supplement homes | [VND §3](../engineering/platform-realizations/3-nutanix-component-path-and-lifecycle-realization.md) |
| Source IDs | S00 |
| Wording disposition | Unchanged from v1.2 |
| Execution status | Specified, not executed by this release |
| Tests | [CT-020](test-specifications.md#CT-020) · [CT-066](test-specifications.md#CT-066) |

Related ADRs: [ADR-0023](../adr/0023-protect-mandatory-policy-and-identity-selectors-from-tenant-mutation.md) · [ADR-0024](../adr/0024-use-independent-nutanix-vpc-domain-realizations-with-qualified-handoffs.md)

<a id="NUT-004"></a>
## NUT-004

The Nutanix profile SHALL qualify the actual AOS/Prism/Flow/provider tuple and external-attachment behavior; unresolved licensing, routing, policy precedence or asynchronous realization limitations SHALL block the affected capability.

| Source field | Retained value |
| --- | --- |
| Accountable role | Platform engineering |
| Parent sections | [RA §16](../architecture/reference/16-nutanix-hosting-stack-reference-realization.md) |
| Supplement homes | [VND §3](../engineering/platform-realizations/3-nutanix-component-path-and-lifecycle-realization.md) |
| Source IDs | S17 |
| Wording disposition | Unchanged from v1.2 |
| Execution status | Specified, not executed by this release |
| Tests | [CT-015](test-specifications.md#CT-015) · [CT-023](test-specifications.md#CT-023) · [CT-045](test-specifications.md#CT-045) · [CT-080](test-specifications.md#CT-080) |

Related ADRs: [ADR-0024](../adr/0024-use-independent-nutanix-vpc-domain-realizations-with-qualified-handoffs.md)

<a id="NSX-001"></a>
## NSX-001

An NSX implementation SHALL keep tenant/project policy distinct from provider/global management and security policy.

| Source field | Retained value |
| --- | --- |
| Accountable role | Platform engineering |
| Parent sections | [RA §17](../architecture/reference/17-vmware-and-nsx-hosting-stack-reference-realization.md) |
| Supplement homes | [VND §4](../engineering/platform-realizations/4-vmware-nsx-isolated-upstream-routing-and-enforcement.md) |
| Source IDs | S00 |
| Wording disposition | Unchanged from v1.2 |
| Execution status | Specified, not executed by this release |
| Tests | [CT-019](test-specifications.md#CT-019) · [CT-020](test-specifications.md#CT-020) · [CT-066](test-specifications.md#CT-066) |

Related ADRs: [ADR-0023](../adr/0023-protect-mandatory-policy-and-identity-selectors-from-tenant-mutation.md) · [ADR-0025](../adr/0025-use-isolated-nsx-upstream-routing-rather-than-a-common-unrestricted-table.md)

<a id="NSX-002"></a>
## NSX-002

Gateway policy used for zone transitions SHALL be generated from portable Flow/ZIP intent rather than manually duplicated per workload.

| Source field | Retained value |
| --- | --- |
| Accountable role | Platform engineering |
| Parent sections | [RA §17](../architecture/reference/17-vmware-and-nsx-hosting-stack-reference-realization.md) |
| Supplement homes | [VND §4](../engineering/platform-realizations/4-vmware-nsx-isolated-upstream-routing-and-enforcement.md) |
| Source IDs | S00 |
| Wording disposition | Unchanged from v1.2 |
| Execution status | Specified, not executed by this release |
| Tests | [CT-003](test-specifications.md#CT-003) · [CT-007](test-specifications.md#CT-007) · [CT-009](test-specifications.md#CT-009) |

Related ADRs: [ADR-0025](../adr/0025-use-isolated-nsx-upstream-routing-rather-than-a-common-unrestricted-table.md)

<a id="NSX-003"></a>
## NSX-003

The NSX profile SHALL identify actual routing and enforcement components, global/project authority and policy precedence, and SHALL qualify their behavior on the selected product/provider tuple rather than equating a Tier-1 or project with a ZIP.

| Source field | Retained value |
| --- | --- |
| Accountable role | Platform engineering |
| Parent sections | [RA §17](../architecture/reference/17-vmware-and-nsx-hosting-stack-reference-realization.md) |
| Supplement homes | [VND §4](../engineering/platform-realizations/4-vmware-nsx-isolated-upstream-routing-and-enforcement.md) |
| Source IDs | S18 |
| Wording disposition | Unchanged from v1.2 |
| Execution status | Specified, not executed by this release |
| Tests | [CT-003](test-specifications.md#CT-003) · [CT-015](test-specifications.md#CT-015) · [CT-024](test-specifications.md#CT-024) · [CT-080](test-specifications.md#CT-080) |

Related ADRs: [ADR-0025](../adr/0025-use-isolated-nsx-upstream-routing-rather-than-a-common-unrestricted-table.md)

<a id="OS-001"></a>
## OS-001

Default OpenStack security-group behaviour SHALL be reviewed and normalized to the secure-by-default service baseline.

| Source field | Retained value |
| --- | --- |
| Accountable role | Platform engineering |
| Parent sections | [RA §18](../architecture/reference/18-openstack-hosting-stack-reference-realization.md) |
| Supplement homes | [VND §5](../engineering/platform-realizations/5-openstack-selected-services-backend-and-mandatory-policy.md) |
| Source IDs | S00 |
| Wording disposition | Unchanged from v1.2 |
| Execution status | Specified, not executed by this release |
| Tests | [CT-005](test-specifications.md#CT-005) · [CT-021](test-specifications.md#CT-021) · [CT-066](test-specifications.md#CT-066) |

Related ADRs: [ADR-0023](../adr/0023-protect-mandatory-policy-and-identity-selectors-from-tenant-mutation.md) · [ADR-0026](../adr/0026-choose-and-own-the-actual-openstack-backend-and-domain-boundaries.md)

<a id="OS-002"></a>
## OS-002

Provider networks and external-router capabilities SHALL remain provider controlled and SHALL not become unrestricted tenant escape paths.

| Source field | Retained value |
| --- | --- |
| Accountable role | Platform engineering |
| Parent sections | [RA §18](../architecture/reference/18-openstack-hosting-stack-reference-realization.md) |
| Supplement homes | [VND §5](../engineering/platform-realizations/5-openstack-selected-services-backend-and-mandatory-policy.md) |
| Source IDs | S00 |
| Wording disposition | Unchanged from v1.2 |
| Execution status | Specified, not executed by this release |
| Tests | [CT-019](test-specifications.md#CT-019) · [CT-022](test-specifications.md#CT-022) · [CT-023](test-specifications.md#CT-023) |

Related ADRs: [ADR-0023](../adr/0023-protect-mandatory-policy-and-identity-selectors-from-tenant-mutation.md) · [ADR-0026](../adr/0026-choose-and-own-the-actual-openstack-backend-and-domain-boundaries.md)

<a id="OS-003"></a>
## OS-003

The OpenStack profile SHALL record distribution, service/API versions, Neutron backend/extensions and provider authority over external/port-security operations; native routing or editable security groups SHALL NOT be assumed to satisfy all ZIP functions.

| Source field | Retained value |
| --- | --- |
| Accountable role | Platform engineering |
| Parent sections | [RA §18](../architecture/reference/18-openstack-hosting-stack-reference-realization.md) |
| Supplement homes | [VND §5](../engineering/platform-realizations/5-openstack-selected-services-backend-and-mandatory-policy.md) |
| Source IDs | S19 |
| Wording disposition | Unchanged from v1.2 |
| Execution status | Specified, not executed by this release |
| Tests | [CT-015](test-specifications.md#CT-015) · [CT-018](test-specifications.md#CT-018) · [CT-022](test-specifications.md#CT-022) · [CT-080](test-specifications.md#CT-080) |

Related ADRs: [ADR-0026](../adr/0026-choose-and-own-the-actual-openstack-backend-and-domain-boundaries.md)

<a id="FUT-001"></a>
## FUT-001

A new platform SHALL pass the applicable conformance suite before it is approved for production placement.

| Source field | Retained value |
| --- | --- |
| Accountable role | Platform engineering |
| Parent sections | [RA §19](../architecture/reference/19-physical-workloads-and-future-platform-extensions.md) |
| Supplement homes | [QUAL §8](site-qualification/8-extensions-and-release-maintenance.md) |
| Source IDs | S00 |
| Wording disposition | Unchanged from v1.2 |
| Execution status | Specified, not executed by this release |
| Tests | [CT-015](test-specifications.md#CT-015) · [CT-018](test-specifications.md#CT-018) · [CT-065](test-specifications.md#CT-065) · [CT-080](test-specifications.md#CT-080) |

<a id="FUT-002"></a>
## FUT-002

A platform SHALL declare unsupported capabilities explicitly; unsupported capabilities SHALL NOT be emulated by weakening a mandatory control.

| Source field | Retained value |
| --- | --- |
| Accountable role | Platform engineering |
| Parent sections | [RA §19](../architecture/reference/19-physical-workloads-and-future-platform-extensions.md) |
| Supplement homes | [QUAL §8](site-qualification/8-extensions-and-release-maintenance.md) |
| Source IDs | S00 |
| Wording disposition | Unchanged from v1.2 |
| Execution status | Specified, not executed by this release |
| Tests | [CT-018](test-specifications.md#CT-018) · [CT-065](test-specifications.md#CT-065) |

<a id="FUT-003"></a>
## FUT-003

Bare-metal and container profiles SHALL explicitly qualify host/control-plane, network, storage and lifecycle isolation; namespaces, projects and physical VRFs SHALL NOT alone be accepted as evidence of a complete security boundary.

| Source field | Retained value |
| --- | --- |
| Accountable role | Platform engineering |
| Parent sections | [RA §19](../architecture/reference/19-physical-workloads-and-future-platform-extensions.md) |
| Supplement homes | [QUAL §8](site-qualification/8-extensions-and-release-maintenance.md) |
| Source IDs | S25; S26 |
| Wording disposition | Unchanged from v1.2 |
| Execution status | Specified, not executed by this release |
| Tests | [CT-035](test-specifications.md#CT-035) · [CT-037](test-specifications.md#CT-037) · [CT-059](test-specifications.md#CT-059) · [CT-065](test-specifications.md#CT-065) · [CT-072](test-specifications.md#CT-072) |

<a id="API-001"></a>
## API-001

The portable API SHALL be versioned and backward-compatibility rules SHALL be published.

| Source field | Retained value |
| --- | --- |
| Accountable role | Automation platform |
| Parent sections | [RA §23](../architecture/reference/23-tenant-domain-and-workload-provisioning-sequence.md) · [RA §24](../architecture/reference/24-terraform-across-the-vendor-stacks.md) |
| Supplement homes | [PROV §3](../implementation/provisioning-strategy/3-terraform-native-tools-and-operation-level-support.md) · [PROV §4](../implementation/provisioning-strategy/4-end-to-end-fixture-provisioning-and-safe-activation.md) · [PROV §5](../implementation/provisioning-strategy/5-concurrency-ownership-and-failed-execution.md) · [VND §1](../engineering/platform-realizations/1-one-reference-environment-three-native-realizations.md) |
| Source IDs | S00 |
| Wording disposition | Unchanged from v1.2 |
| Execution status | Specified, not executed by this release |
| Tests | [CT-016](test-specifications.md#CT-016) · [CT-070](test-specifications.md#CT-070) |

<a id="API-002"></a>
## API-002

Vendor identifiers, VLAN/VNI/VRF details, route targets, raw firewall rules and raw next-hop routes SHALL NOT be part of the normal consumer contract.

| Source field | Retained value |
| --- | --- |
| Accountable role | Automation platform |
| Parent sections | [RA §23](../architecture/reference/23-tenant-domain-and-workload-provisioning-sequence.md) · [RA §24](../architecture/reference/24-terraform-across-the-vendor-stacks.md) |
| Supplement homes | [PROV §3](../implementation/provisioning-strategy/3-terraform-native-tools-and-operation-level-support.md) · [PROV §4](../implementation/provisioning-strategy/4-end-to-end-fixture-provisioning-and-safe-activation.md) · [PROV §5](../implementation/provisioning-strategy/5-concurrency-ownership-and-failed-execution.md) · [VND §1](../engineering/platform-realizations/1-one-reference-environment-three-native-realizations.md) |
| Source IDs | S00 |
| Wording disposition | Unchanged from v1.2 |
| Execution status | Specified, not executed by this release |
| Tests | [CT-017](test-specifications.md#CT-017) · [CT-019](test-specifications.md#CT-019) |

<a id="API-003"></a>
## API-003

Where a consumer-facing provisioning API is provided, it SHALL enforce immutable IDs, idempotent create, optimistic concurrency, typed/closed schemas, authorized references and authoritative service-owned status; stale or unauthorized updates SHALL fail before side effects. These controls MAY be implemented by an existing qualified service interface.

| Source field | Retained value |
| --- | --- |
| Accountable role | Automation platform |
| Parent sections | [RA §23](../architecture/reference/23-tenant-domain-and-workload-provisioning-sequence.md) · [RA §24](../architecture/reference/24-terraform-across-the-vendor-stacks.md) |
| Supplement homes | [PROV §3](../implementation/provisioning-strategy/3-terraform-native-tools-and-operation-level-support.md) · [PROV §4](../implementation/provisioning-strategy/4-end-to-end-fixture-provisioning-and-safe-activation.md) · [PROV §5](../implementation/provisioning-strategy/5-concurrency-ownership-and-failed-execution.md) · [VND §1](../engineering/platform-realizations/1-one-reference-environment-three-native-realizations.md) |
| Source IDs | S00 |
| Wording disposition | Unchanged from v1.2 |
| Execution status | Specified, not executed by this release |
| Tests | [CT-017](test-specifications.md#CT-017) · [CT-046](test-specifications.md#CT-046) · [CT-070](test-specifications.md#CT-070) |

Related ADRs: [ADR-0003](../adr/0003-let-the-infrastructure-architecture-lead-the-tooling.md)

<a id="POL-001"></a>
## POL-001

Admission policy SHALL be provider independent wherever the rule expresses an architectural invariant.

| Source field | Retained value |
| --- | --- |
| Accountable role | Automation platform |
| Parent sections | [RA §20](../architecture/reference/20-provisioning-model-and-infrastructure-work-packages.md) · [RA §23](../architecture/reference/23-tenant-domain-and-workload-provisioning-sequence.md) |
| Supplement homes | [PROV §1](../implementation/provisioning-strategy/1-provisioning-scopes-ownership-and-accepted-handoffs.md) · [PROV §4](../implementation/provisioning-strategy/4-end-to-end-fixture-provisioning-and-safe-activation.md) · [VND §1](../engineering/platform-realizations/1-one-reference-environment-three-native-realizations.md) |
| Source IDs | S00 |
| Wording disposition | Unchanged from v1.2 |
| Execution status | Specified, not executed by this release |
| Tests | [CT-017](test-specifications.md#CT-017) · [CT-025](test-specifications.md#CT-025) · [CT-066](test-specifications.md#CT-066) |

<a id="POL-002"></a>
## POL-002

Provider-specific plan checks SHOULD validate that the adapter compiled the intent into the expected native constructs.

| Source field | Retained value |
| --- | --- |
| Accountable role | Automation platform |
| Parent sections | [RA §20](../architecture/reference/20-provisioning-model-and-infrastructure-work-packages.md) · [RA §23](../architecture/reference/23-tenant-domain-and-workload-provisioning-sequence.md) |
| Supplement homes | [PROV §1](../implementation/provisioning-strategy/1-provisioning-scopes-ownership-and-accepted-handoffs.md) · [PROV §4](../implementation/provisioning-strategy/4-end-to-end-fixture-provisioning-and-safe-activation.md) · [VND §1](../engineering/platform-realizations/1-one-reference-environment-three-native-realizations.md) |
| Source IDs | S00 |
| Wording disposition | Unchanged from v1.2 |
| Execution status | Specified, not executed by this release |
| Tests | [CT-009](test-specifications.md#CT-009) · [CT-048](test-specifications.md#CT-048) · [CT-066](test-specifications.md#CT-066) |

<a id="FLOW-001"></a>
## FLOW-001

Flow Intentions SHALL resolve explicit identities, service/profile version, initiation direction, lifetime, purpose and logging; compilation SHALL preserve mandatory policy precedence and enforce approved session-revocation behavior.

| Source field | Retained value |
| --- | --- |
| Accountable role | Security-edge operations |
| Parent sections | [RA §20](../architecture/reference/20-provisioning-model-and-infrastructure-work-packages.md) · [RA §23](../architecture/reference/23-tenant-domain-and-workload-provisioning-sequence.md) |
| Supplement homes | [PROV §1](../implementation/provisioning-strategy/1-provisioning-scopes-ownership-and-accepted-handoffs.md) · [PROV §4](../implementation/provisioning-strategy/4-end-to-end-fixture-provisioning-and-safe-activation.md) · [VND §1](../engineering/platform-realizations/1-one-reference-environment-three-native-realizations.md) |
| Source IDs | S00 |
| Wording disposition | Unchanged from v1.2 |
| Execution status | Specified, not executed by this release |
| Tests | [CT-007](test-specifications.md#CT-007) · [CT-020](test-specifications.md#CT-020) · [CT-066](test-specifications.md#CT-066) · [CT-077](test-specifications.md#CT-077) |

<a id="AUTO-001"></a>
## AUTO-001

If security admission, IPAM, route authority, or mandatory policy validation is unavailable, new provisioning SHALL stop rather than inventing or bypassing required state.

| Source field | Retained value |
| --- | --- |
| Accountable role | Automation platform |
| Parent sections | [RA §23](../architecture/reference/23-tenant-domain-and-workload-provisioning-sequence.md) · [RA §24](../architecture/reference/24-terraform-across-the-vendor-stacks.md) |
| Supplement homes | [PROV §3](../implementation/provisioning-strategy/3-terraform-native-tools-and-operation-level-support.md) · [PROV §4](../implementation/provisioning-strategy/4-end-to-end-fixture-provisioning-and-safe-activation.md) · [PROV §5](../implementation/provisioning-strategy/5-concurrency-ownership-and-failed-execution.md) · [VND §1](../engineering/platform-realizations/1-one-reference-environment-three-native-realizations.md) |
| Source IDs | S00 |
| Wording disposition | Unchanged from v1.2 |
| Execution status | Specified, not executed by this release |
| Tests | [CT-011](test-specifications.md#CT-011) · [CT-029](test-specifications.md#CT-029) · [CT-045](test-specifications.md#CT-045) |

Related ADRs: [ADR-0014](../adr/0014-bootstrap-management-and-trust-before-consuming-native-apis.md)

<a id="AUTO-002"></a>
## AUTO-002

Provisioning SHALL be journaled and idempotent, reserve only eligible capacity/addresses, enforce deny before attachment/exposure, and gate activation on realized current-generation evidence and authorization.

| Source field | Retained value |
| --- | --- |
| Accountable role | Automation platform |
| Parent sections | [RA §23](../architecture/reference/23-tenant-domain-and-workload-provisioning-sequence.md) · [RA §24](../architecture/reference/24-terraform-across-the-vendor-stacks.md) |
| Supplement homes | [PROV §3](../implementation/provisioning-strategy/3-terraform-native-tools-and-operation-level-support.md) · [PROV §4](../implementation/provisioning-strategy/4-end-to-end-fixture-provisioning-and-safe-activation.md) · [PROV §5](../implementation/provisioning-strategy/5-concurrency-ownership-and-failed-execution.md) · [VND §1](../engineering/platform-realizations/1-one-reference-environment-three-native-realizations.md) |
| Source IDs | S00 |
| Wording disposition | Unchanged from v1.2 |
| Execution status | Specified, not executed by this release |
| Tests | [CT-045](test-specifications.md#CT-045) · [CT-046](test-specifications.md#CT-046) · [CT-048](test-specifications.md#CT-048) · [CT-069](test-specifications.md#CT-069) |

Related ADRs: [ADR-0015](../adr/0015-build-under-deny-and-verify-before-and-after-activation.md) · [ADR-0031](../adr/0031-discover-uncertain-native-outcomes-instead-of-blind-replay-or-rollback.md)

<a id="AUTO-003"></a>
## AUTO-003

Retries SHALL distinguish transient, permanent and conflict failures, use bounded backoff/deadlines and preserve resource identity; uncertain outcomes SHALL be discovered and reconciled rather than duplicated.

| Source field | Retained value |
| --- | --- |
| Accountable role | Automation platform |
| Parent sections | [RA §23](../architecture/reference/23-tenant-domain-and-workload-provisioning-sequence.md) · [RA §24](../architecture/reference/24-terraform-across-the-vendor-stacks.md) |
| Supplement homes | [PROV §3](../implementation/provisioning-strategy/3-terraform-native-tools-and-operation-level-support.md) · [PROV §4](../implementation/provisioning-strategy/4-end-to-end-fixture-provisioning-and-safe-activation.md) · [PROV §5](../implementation/provisioning-strategy/5-concurrency-ownership-and-failed-execution.md) · [VND §1](../engineering/platform-realizations/1-one-reference-environment-three-native-realizations.md) |
| Source IDs | S00 |
| Wording disposition | Unchanged from v1.2 |
| Execution status | Specified, not executed by this release |
| Tests | [CT-045](test-specifications.md#CT-045) · [CT-046](test-specifications.md#CT-046) · [CT-047](test-specifications.md#CT-047) |

Related ADRs: [ADR-0031](../adr/0031-discover-uncertain-native-outcomes-instead-of-blind-replay-or-rollback.md)

<a id="TF-001"></a>
## TF-001

Provider configuration SHALL be defined in root modules and passed to child modules; reusable child modules SHOULD NOT embed provider credentials/configuration.

| Source field | Retained value |
| --- | --- |
| Accountable role | Automation platform |
| Parent sections | [RA §24](../architecture/reference/24-terraform-across-the-vendor-stacks.md) |
| Supplement homes | [PROV §3](../implementation/provisioning-strategy/3-terraform-native-tools-and-operation-level-support.md) · [PROV §5](../implementation/provisioning-strategy/5-concurrency-ownership-and-failed-execution.md) |
| Source IDs | S00; S13 |
| Wording disposition | Unchanged from v1.2 |
| Execution status | Specified, not executed by this release |
| Tests | [CT-042](test-specifications.md#CT-042) · [CT-043](test-specifications.md#CT-043) |

Related ADRs: [ADR-0013](../adr/0013-compose-provisioning-across-separate-platform-and-service-authorities.md)

<a id="TF-002"></a>
## TF-002

Provider versions SHALL be constrained and dependency lock files SHALL be committed and reviewed.

| Source field | Retained value |
| --- | --- |
| Accountable role | Automation platform |
| Parent sections | [RA §24](../architecture/reference/24-terraform-across-the-vendor-stacks.md) |
| Supplement homes | [PROV §3](../implementation/provisioning-strategy/3-terraform-native-tools-and-operation-level-support.md) · [PROV §5](../implementation/provisioning-strategy/5-concurrency-ownership-and-failed-execution.md) |
| Source IDs | S00; S14 |
| Wording disposition | Unchanged from v1.2 |
| Execution status | Specified, not executed by this release |
| Tests | [CT-015](test-specifications.md#CT-015) · [CT-042](test-specifications.md#CT-042) · [CT-048](test-specifications.md#CT-048) |

Related ADRs: [ADR-0013](../adr/0013-compose-provisioning-across-separate-platform-and-service-authorities.md)

<a id="TF-003"></a>
## TF-003

The provisioning workflow SHALL select the required hosting-platform and shared-service adapters before execution; adapters SHALL preserve their authority and lifecycle boundaries. A single giant conditional module SHOULD NOT attempt to implement all platforms.

| Source field | Retained value |
| --- | --- |
| Accountable role | Automation platform |
| Parent sections | [RA §24](../architecture/reference/24-terraform-across-the-vendor-stacks.md) |
| Supplement homes | [PROV §3](../implementation/provisioning-strategy/3-terraform-native-tools-and-operation-level-support.md) · [PROV §5](../implementation/provisioning-strategy/5-concurrency-ownership-and-failed-execution.md) |
| Source IDs | S00 |
| Wording disposition | Unchanged from v1.2 |
| Execution status | Specified, not executed by this release |
| Tests | [CT-016](test-specifications.md#CT-016) · [CT-044](test-specifications.md#CT-044) |

Related ADRs: [ADR-0003](../adr/0003-let-the-infrastructure-architecture-lead-the-tooling.md) · [ADR-0013](../adr/0013-compose-provisioning-across-separate-platform-and-service-authorities.md)

<a id="TF-004"></a>
## TF-004

Module interfaces SHOULD be relatively flat and composable; deeply nested modules that obscure lifecycle or ownership boundaries SHOULD be avoided.

| Source field | Retained value |
| --- | --- |
| Accountable role | Automation platform |
| Parent sections | [RA §24](../architecture/reference/24-terraform-across-the-vendor-stacks.md) |
| Supplement homes | [PROV §3](../implementation/provisioning-strategy/3-terraform-native-tools-and-operation-level-support.md) · [PROV §5](../implementation/provisioning-strategy/5-concurrency-ownership-and-failed-execution.md) |
| Source IDs | S00 |
| Wording disposition | Unchanged from v1.2 |
| Execution status | Specified, not executed by this release |
| Tests | [CT-044](test-specifications.md#CT-044) · [CT-070](test-specifications.md#CT-070) |

<a id="TF-005"></a>
## TF-005

Remote module sources and runner images SHALL be pinned to immutable versions/digests separately from provider lockfiles; approved package checksums and provenance SHALL be verified before privileged execution.

| Source field | Retained value |
| --- | --- |
| Accountable role | Automation platform |
| Parent sections | [RA §24](../architecture/reference/24-terraform-across-the-vendor-stacks.md) |
| Supplement homes | [PROV §3](../implementation/provisioning-strategy/3-terraform-native-tools-and-operation-level-support.md) · [PROV §5](../implementation/provisioning-strategy/5-concurrency-ownership-and-failed-execution.md) |
| Source IDs | S14 |
| Wording disposition | Unchanged from v1.2 |
| Execution status | Specified, not executed by this release |
| Tests | [CT-042](test-specifications.md#CT-042) · [CT-048](test-specifications.md#CT-048) |

Related ADRs: [ADR-0013](../adr/0013-compose-provisioning-across-separate-platform-and-service-authorities.md) · [ADR-0038](../adr/0038-govern-images-and-privileged-dependency-provenance-across-their-lifecycle.md)

<a id="STATE-001"></a>
## STATE-001

No single routine tenant automation identity SHALL have authority to modify physical fabric, management foundation, security edge, and tenant workloads simultaneously.

| Source field | Retained value |
| --- | --- |
| Accountable role | Automation platform |
| Parent sections | [RA §24](../architecture/reference/24-terraform-across-the-vendor-stacks.md) |
| Supplement homes | [PROV §3](../implementation/provisioning-strategy/3-terraform-native-tools-and-operation-level-support.md) · [PROV §5](../implementation/provisioning-strategy/5-concurrency-ownership-and-failed-execution.md) |
| Source IDs | S00 |
| Wording disposition | Unchanged from v1.2 |
| Execution status | Specified, not executed by this release |
| Tests | [CT-019](test-specifications.md#CT-019) · [CT-044](test-specifications.md#CT-044) |

Related ADRs: [ADR-0013](../adr/0013-compose-provisioning-across-separate-platform-and-service-authorities.md)

<a id="STATE-002"></a>
## STATE-002

Remote state backends SHALL use encryption, strong authentication, locking, recovery/versioning, access logging, and separation appropriate to the sensitivity of contained data.

| Source field | Retained value |
| --- | --- |
| Accountable role | Automation platform |
| Parent sections | [RA §24](../architecture/reference/24-terraform-across-the-vendor-stacks.md) |
| Supplement homes | [PROV §3](../implementation/provisioning-strategy/3-terraform-native-tools-and-operation-level-support.md) · [PROV §5](../implementation/provisioning-strategy/5-concurrency-ownership-and-failed-execution.md) |
| Source IDs | S00 |
| Wording disposition | Unchanged from v1.2 |
| Execution status | Specified, not executed by this release |
| Tests | [CT-043](test-specifications.md#CT-043) · [CT-044](test-specifications.md#CT-044) · [CT-055](test-specifications.md#CT-055) |

<a id="STATE-003"></a>
## STATE-003

Cross-state/external-service changes SHALL use a journaled dependency workflow with scoped outputs, idempotent stage completion and data-safe compensation; state-file restoration SHALL NOT be represented as infrastructure rollback.

| Source field | Retained value |
| --- | --- |
| Accountable role | Automation platform |
| Parent sections | [RA §24](../architecture/reference/24-terraform-across-the-vendor-stacks.md) |
| Supplement homes | [PROV §3](../implementation/provisioning-strategy/3-terraform-native-tools-and-operation-level-support.md) · [PROV §5](../implementation/provisioning-strategy/5-concurrency-ownership-and-failed-execution.md) |
| Source IDs | S00 |
| Wording disposition | Unchanged from v1.2 |
| Execution status | Specified, not executed by this release |
| Tests | [CT-044](test-specifications.md#CT-044) · [CT-045](test-specifications.md#CT-045) · [CT-070](test-specifications.md#CT-070) |

Related ADRs: [ADR-0013](../adr/0013-compose-provisioning-across-separate-platform-and-service-authorities.md) · [ADR-0016](../adr/0016-assign-one-authoritative-writer-per-native-object-and-sensitive-subresource.md) · [ADR-0031](../adr/0031-discover-uncertain-native-outcomes-instead-of-blind-replay-or-rollback.md)

<a id="CICD-001"></a>
## CICD-001

A change that modifies inter-zone policy, external exposure, route authority, management access, or assurance profile SHALL receive a higher change classification than an ordinary workload scale operation.

| Source field | Retained value |
| --- | --- |
| Accountable role | Change authority |
| Parent sections | [RA §24](../architecture/reference/24-terraform-across-the-vendor-stacks.md) |
| Supplement homes | [PROV §3](../implementation/provisioning-strategy/3-terraform-native-tools-and-operation-level-support.md) · [PROV §5](../implementation/provisioning-strategy/5-concurrency-ownership-and-failed-execution.md) |
| Source IDs | S00 |
| Wording disposition | Unchanged from v1.2 |
| Execution status | Specified, not executed by this release |
| Tests | [CT-048](test-specifications.md#CT-048) · [CT-058](test-specifications.md#CT-058) |

Related ADRs: [ADR-0034](../adr/0034-classify-change-by-architectural-impact-rather-than-file-location.md)

<a id="CICD-002"></a>
## CICD-002

An approval SHALL bind the immutable plan and all security-relevant input/policy/state/dependency digests; stale, changed or expired artifacts SHALL be rejected at apply.

| Source field | Retained value |
| --- | --- |
| Accountable role | Automation platform |
| Parent sections | [RA §24](../architecture/reference/24-terraform-across-the-vendor-stacks.md) |
| Supplement homes | [PROV §3](../implementation/provisioning-strategy/3-terraform-native-tools-and-operation-level-support.md) · [PROV §5](../implementation/provisioning-strategy/5-concurrency-ownership-and-failed-execution.md) |
| Source IDs | S00 |
| Wording disposition | Unchanged from v1.2 |
| Execution status | Specified, not executed by this release |
| Tests | [CT-042](test-specifications.md#CT-042) · [CT-048](test-specifications.md#CT-048) |

Related ADRs: [ADR-0034](../adr/0034-classify-change-by-architectural-impact-rather-than-file-location.md)

<a id="SUP-001"></a>
## SUP-001

Privileged software/provider/module supply chains SHALL use approved sources, integrity verification, revocation and a compromise-response procedure covering already-executed artifacts and credentials.

| Source field | Retained value |
| --- | --- |
| Accountable role | Automation platform |
| Parent sections | [RA §24](../architecture/reference/24-terraform-across-the-vendor-stacks.md) |
| Supplement homes | [PROV §3](../implementation/provisioning-strategy/3-terraform-native-tools-and-operation-level-support.md) · [PROV §5](../implementation/provisioning-strategy/5-concurrency-ownership-and-failed-execution.md) |
| Source IDs | S05; S14 |
| Wording disposition | Unchanged from v1.2 |
| Execution status | Specified, not executed by this release |
| Tests | [CT-041](test-specifications.md#CT-041) · [CT-042](test-specifications.md#CT-042) · [CT-057](test-specifications.md#CT-057) |

Related ADRs: [ADR-0038](../adr/0038-govern-images-and-privileged-dependency-provenance-across-their-lifecycle.md)

<a id="SEC-001"></a>
## SEC-001

Static privileged provider credentials SHALL NOT be embedded in Terraform source code.

| Source field | Retained value |
| --- | --- |
| Accountable role | Automation platform |
| Parent sections | [RA §13](../architecture/reference/13-identity-cryptography-and-service-trust.md) · [RA §24](../architecture/reference/24-terraform-across-the-vendor-stacks.md) |
| Supplement homes | [PROV §3](../implementation/provisioning-strategy/3-terraform-native-tools-and-operation-level-support.md) · [PROV §5](../implementation/provisioning-strategy/5-concurrency-ownership-and-failed-execution.md) · [SVC §3](../architecture/shared-services/3-identity-certificates-keys-and-independent-recovery.md) |
| Source IDs | S00 |
| Wording disposition | Unchanged from v1.2 |
| Execution status | Specified, not executed by this release |
| Tests | [CT-043](test-specifications.md#CT-043) |

<a id="SEC-002"></a>
## SEC-002

Automation identities SHALL use least privilege and separate duties by control domain.

| Source field | Retained value |
| --- | --- |
| Accountable role | Automation platform |
| Parent sections | [RA §13](../architecture/reference/13-identity-cryptography-and-service-trust.md) · [RA §24](../architecture/reference/24-terraform-across-the-vendor-stacks.md) |
| Supplement homes | [PROV §3](../implementation/provisioning-strategy/3-terraform-native-tools-and-operation-level-support.md) · [PROV §5](../implementation/provisioning-strategy/5-concurrency-ownership-and-failed-execution.md) · [SVC §3](../architecture/shared-services/3-identity-certificates-keys-and-independent-recovery.md) |
| Source IDs | S00 |
| Wording disposition | Unchanged from v1.2 |
| Execution status | Specified, not executed by this release |
| Tests | [CT-019](test-specifications.md#CT-019) · [CT-044](test-specifications.md#CT-044) · [CT-079](test-specifications.md#CT-079) |

<a id="SEC-003"></a>
## SEC-003

Credential rotation, revocation, and break-glass recovery SHALL be tested as part of the platform operational profile.

| Source field | Retained value |
| --- | --- |
| Accountable role | Automation platform |
| Parent sections | [RA §13](../architecture/reference/13-identity-cryptography-and-service-trust.md) · [RA §24](../architecture/reference/24-terraform-across-the-vendor-stacks.md) |
| Supplement homes | [PROV §3](../implementation/provisioning-strategy/3-terraform-native-tools-and-operation-level-support.md) · [PROV §5](../implementation/provisioning-strategy/5-concurrency-ownership-and-failed-execution.md) · [SVC §3](../architecture/shared-services/3-identity-certificates-keys-and-independent-recovery.md) |
| Source IDs | S00 |
| Wording disposition | Unchanged from v1.2 |
| Execution status | Specified, not executed by this release |
| Tests | [CT-027](test-specifications.md#CT-027) · [CT-028](test-specifications.md#CT-028) · [CT-043](test-specifications.md#CT-043) |

<a id="SEC-004"></a>
## SEC-004

Where supported and verified, sensitive values SHOULD use ephemeral/write-only mechanisms; all remaining secret-bearing plan/state/log artifacts SHALL be classified, encrypted, access-controlled and tested for unintended disclosure.

| Source field | Retained value |
| --- | --- |
| Accountable role | Automation platform |
| Parent sections | [RA §13](../architecture/reference/13-identity-cryptography-and-service-trust.md) · [RA §24](../architecture/reference/24-terraform-across-the-vendor-stacks.md) |
| Supplement homes | [PROV §3](../implementation/provisioning-strategy/3-terraform-native-tools-and-operation-level-support.md) · [PROV §5](../implementation/provisioning-strategy/5-concurrency-ownership-and-failed-execution.md) · [SVC §3](../architecture/shared-services/3-identity-certificates-keys-and-independent-recovery.md) |
| Source IDs | S15; S16 |
| Wording disposition | Unchanged from v1.2 |
| Execution status | Specified, not executed by this release |
| Tests | [CT-043](test-specifications.md#CT-043) · [CT-044](test-specifications.md#CT-044) |

<a id="DRIFT-001"></a>
## DRIFT-001

Security-significant drift SHALL generate an actionable event and update technical conformance/readiness conditions until resolved or accepted; formal authorization records SHALL remain separately attributable and immutable.

| Source field | Retained value |
| --- | --- |
| Accountable role | Operations/SRE |
| Parent sections | [RA §25](../architecture/reference/25-change-brownfield-adoption-and-configuration-ownership.md) |
| Supplement homes | [PROV §5](../implementation/provisioning-strategy/5-concurrency-ownership-and-failed-execution.md) · [PROV §6](../implementation/provisioning-strategy/6-brownfield-adoption-growth-and-retirement.md) |
| Source IDs | S00; S05 |
| Wording disposition | Unchanged from v1.2 |
| Execution status | Specified, not executed by this release |
| Tests | [CT-014](test-specifications.md#CT-014) · [CT-049](test-specifications.md#CT-049) · [CT-057](test-specifications.md#CT-057) |

Related ADRs: [ADR-0032](../adr/0032-keep-incident-containment-above-routine-reconciliation.md)

<a id="DRIFT-002"></a>
## DRIFT-002

Emergency changes SHALL be reconciled back into the source of truth after the incident or maintenance action.

| Source field | Retained value |
| --- | --- |
| Accountable role | Operations/SRE |
| Parent sections | [RA §25](../architecture/reference/25-change-brownfield-adoption-and-configuration-ownership.md) |
| Supplement homes | [PROV §5](../implementation/provisioning-strategy/5-concurrency-ownership-and-failed-execution.md) · [PROV §6](../implementation/provisioning-strategy/6-brownfield-adoption-growth-and-retirement.md) |
| Source IDs | S00 |
| Wording disposition | Unchanged from v1.2 |
| Execution status | Specified, not executed by this release |
| Tests | [CT-014](test-specifications.md#CT-014) · [CT-057](test-specifications.md#CT-057) |

Related ADRs: [ADR-0032](../adr/0032-keep-incident-containment-above-routine-reconciliation.md)

<a id="DRIFT-003"></a>
## DRIFT-003

Incident containment overrides SHALL take precedence over ordinary reconciliation until explicitly released or handled by their approved expiry policy; automated repair SHALL NOT silently undo containment.

| Source field | Retained value |
| --- | --- |
| Accountable role | Incident response |
| Parent sections | [RA §25](../architecture/reference/25-change-brownfield-adoption-and-configuration-ownership.md) |
| Supplement homes | [PROV §5](../implementation/provisioning-strategy/5-concurrency-ownership-and-failed-execution.md) · [PROV §6](../implementation/provisioning-strategy/6-brownfield-adoption-growth-and-retirement.md) |
| Source IDs | S00 |
| Wording disposition | Unchanged from v1.2 |
| Execution status | Specified, not executed by this release |
| Tests | [CT-057](test-specifications.md#CT-057) · [CT-058](test-specifications.md#CT-058) · [CT-066](test-specifications.md#CT-066) |

Related ADRs: [ADR-0032](../adr/0032-keep-incident-containment-above-routine-reconciliation.md)

<a id="ASSUR-001"></a>
## ASSUR-001

Assurance profile selection SHALL be based on system security requirements and risk analysis rather than tenant preference alone.

| Source field | Retained value |
| --- | --- |
| Accountable role | Security authority |
| Parent sections | [RA §7](../architecture/reference/7-tenant-environments-and-security-domain-placement.md) · [RA §11](../architecture/reference/11-compute-pools-hypervisors-and-workload-placement.md) · [RA §12](../architecture/reference/12-storage-backup-and-data-isolation-architecture.md) · [RA §14](../architecture/reference/14-availability-multi-site-operation-and-recovery-topology.md) |
| Supplement homes | [QUAL §3](site-qualification/3-capacity-service-envelopes-and-growth-triggers.md) · [QUAL §4](site-qualification/4-service-parameter-and-requirement-decisions.md) · [SVC §4](../architecture/shared-services/4-storage-copies-and-retained-data-ownership.md) · [SVC §5](../architecture/shared-services/5-backup-capture-independent-protection-and-isolated-restore.md) · [SVC §6](../architecture/shared-services/6-failure-recovery-migration-and-failback-topology.md) · [VND §1](../engineering/platform-realizations/1-one-reference-environment-three-native-realizations.md) · [VND §2](../engineering/platform-realizations/2-physical-placement-and-the-sharing-decision.md) |
| Source IDs | S00; S03; S05 |
| Wording disposition | Unchanged from v1.2 |
| Execution status | Specified, not executed by this release |
| Tests | [CT-035](test-specifications.md#CT-035) · [CT-062](test-specifications.md#CT-062) |

Related ADRs: [ADR-0008](../adr/0008-preserve-zone-aware-host-placement-and-disclose-every-shared-layer.md)

<a id="ASSUR-002"></a>
## ASSUR-002

Assurance profiles SHALL define explicit isolation for compute, storage, routing, edge, management, backup and keys, with measurable verification and exception rules; “dedicated” SHALL identify its actual resource scope.

| Source field | Retained value |
| --- | --- |
| Accountable role | Security authority |
| Parent sections | [RA §7](../architecture/reference/7-tenant-environments-and-security-domain-placement.md) · [RA §11](../architecture/reference/11-compute-pools-hypervisors-and-workload-placement.md) · [RA §12](../architecture/reference/12-storage-backup-and-data-isolation-architecture.md) · [RA §14](../architecture/reference/14-availability-multi-site-operation-and-recovery-topology.md) |
| Supplement homes | [QUAL §3](site-qualification/3-capacity-service-envelopes-and-growth-triggers.md) · [QUAL §4](site-qualification/4-service-parameter-and-requirement-decisions.md) · [SVC §4](../architecture/shared-services/4-storage-copies-and-retained-data-ownership.md) · [SVC §5](../architecture/shared-services/5-backup-capture-independent-protection-and-isolated-restore.md) · [SVC §6](../architecture/shared-services/6-failure-recovery-migration-and-failback-topology.md) · [VND §1](../engineering/platform-realizations/1-one-reference-environment-three-native-realizations.md) · [VND §2](../engineering/platform-realizations/2-physical-placement-and-the-sharing-decision.md) |
| Source IDs | S03; S05 |
| Wording disposition | Unchanged from v1.2 |
| Execution status | Specified, not executed by this release |
| Tests | [CT-018](test-specifications.md#CT-018) · [CT-035](test-specifications.md#CT-035) · [CT-037](test-specifications.md#CT-037) · [CT-062](test-specifications.md#CT-062) |

Related ADRs: [ADR-0008](../adr/0008-preserve-zone-aware-host-placement-and-disclose-every-shared-layer.md)

<a id="ASSUR-003"></a>
## ASSUR-003

A production profile SHALL have approved parameter values, owners, applicable test sets and evidence freshness limits; incomplete or expired profiles SHALL be ineligible for new production placement.

| Source field | Retained value |
| --- | --- |
| Accountable role | Security authority |
| Parent sections | [RA §7](../architecture/reference/7-tenant-environments-and-security-domain-placement.md) · [RA §11](../architecture/reference/11-compute-pools-hypervisors-and-workload-placement.md) · [RA §12](../architecture/reference/12-storage-backup-and-data-isolation-architecture.md) · [RA §14](../architecture/reference/14-availability-multi-site-operation-and-recovery-topology.md) |
| Supplement homes | [QUAL §3](site-qualification/3-capacity-service-envelopes-and-growth-triggers.md) · [QUAL §4](site-qualification/4-service-parameter-and-requirement-decisions.md) · [SVC §4](../architecture/shared-services/4-storage-copies-and-retained-data-ownership.md) · [SVC §5](../architecture/shared-services/5-backup-capture-independent-protection-and-isolated-restore.md) · [SVC §6](../architecture/shared-services/6-failure-recovery-migration-and-failback-topology.md) · [VND §1](../engineering/platform-realizations/1-one-reference-environment-three-native-realizations.md) · [VND §2](../engineering/platform-realizations/2-physical-placement-and-the-sharing-decision.md) |
| Source IDs | S00 |
| Wording disposition | Unchanged from v1.2 |
| Execution status | Specified, not executed by this release |
| Tests | [CT-018](test-specifications.md#CT-018) · [CT-058](test-specifications.md#CT-058) · [CT-069](test-specifications.md#CT-069) |

<a id="TEST-001"></a>
## TEST-001

Negative tests SHALL be first-class acceptance criteria; proving that an allowed flow works is insufficient.

| Source field | Retained value |
| --- | --- |
| Accountable role | Assurance engineering |
| Parent sections | [RA §28](../architecture/reference/28-architecture-acceptance-and-verification.md) |
| Supplement homes | [QUAL §5](site-qualification/5-qualification-stages-applicability-and-evidence.md) · [QUAL §6](site-qualification/6-control-inheritance-assurance-and-organizational-interfaces.md) |
| Source IDs | S00 |
| Wording disposition | Unchanged from v1.2 |
| Execution status | Specified, not executed by this release |
| Tests | [CT-001](test-specifications.md#CT-001) · [CT-002](test-specifications.md#CT-002) · [CT-003](test-specifications.md#CT-003) · [CT-007](test-specifications.md#CT-007) |

<a id="TEST-002"></a>
## TEST-002

A platform upgrade SHALL trigger an appropriate regression/conformance test set before broad production rollout.

| Source field | Retained value |
| --- | --- |
| Accountable role | Assurance engineering |
| Parent sections | [RA §28](../architecture/reference/28-architecture-acceptance-and-verification.md) |
| Supplement homes | [QUAL §5](site-qualification/5-qualification-stages-applicability-and-evidence.md) · [QUAL §6](site-qualification/6-control-inheritance-assurance-and-organizational-interfaces.md) |
| Source IDs | S00 |
| Wording disposition | Unchanged from v1.2 |
| Execution status | Specified, not executed by this release |
| Tests | [CT-015](test-specifications.md#CT-015) · [CT-018](test-specifications.md#CT-018) |

<a id="TEST-003"></a>
## TEST-003

Every test execution SHALL record target versions, preconditions, healthy control paths, observation, expected outcome and attributable evidence; blocked, not-run or unjustified not-applicable results SHALL NOT satisfy mandatory gates.

| Source field | Retained value |
| --- | --- |
| Accountable role | Assurance engineering |
| Parent sections | [RA §28](../architecture/reference/28-architecture-acceptance-and-verification.md) |
| Supplement homes | [QUAL §5](site-qualification/5-qualification-stages-applicability-and-evidence.md) · [QUAL §6](site-qualification/6-control-inheritance-assurance-and-organizational-interfaces.md) |
| Source IDs | S00 |
| Wording disposition | Unchanged from v1.2 |
| Execution status | Specified, not executed by this release |
| Tests | [CT-049](test-specifications.md#CT-049) · [CT-069](test-specifications.md#CT-069) · [CT-075](test-specifications.md#CT-075) |

Related ADRs: [ADR-0017](../adr/0017-separate-reference-adoption-technical-qualification-and-authorization.md)

<a id="TEST-004"></a>
## TEST-004

Fault-injection and intrusive negative tests SHALL run only within an approved scope, safety envelope and recovery procedure; production testing SHALL protect unrelated tenants.

| Source field | Retained value |
| --- | --- |
| Accountable role | Assurance engineering |
| Parent sections | [RA §28](../architecture/reference/28-architecture-acceptance-and-verification.md) |
| Supplement homes | [QUAL §5](site-qualification/5-qualification-stages-applicability-and-evidence.md) · [QUAL §6](site-qualification/6-control-inheritance-assurance-and-organizational-interfaces.md) |
| Source IDs | S00 |
| Wording disposition | Unchanged from v1.2 |
| Execution status | Specified, not executed by this release |
| Tests | [CT-011](test-specifications.md#CT-011) · [CT-012](test-specifications.md#CT-012) · [CT-034](test-specifications.md#CT-034) · [CT-054](test-specifications.md#CT-054) |

<a id="EVID-001"></a>
## EVID-001

The evidence record SHALL identify the source revision, policy version, provider/module versions, realized security relationships, test results, and active exceptions.

| Source field | Retained value |
| --- | --- |
| Accountable role | Assurance engineering |
| Parent sections | [RA §26](../architecture/reference/26-operating-model-capacity-and-observability.md) · [RA §28](../architecture/reference/28-architecture-acceptance-and-verification.md) |
| Supplement homes | [QUAL §3](site-qualification/3-capacity-service-envelopes-and-growth-triggers.md) · [QUAL §5](site-qualification/5-qualification-stages-applicability-and-evidence.md) · [QUAL §6](site-qualification/6-control-inheritance-assurance-and-organizational-interfaces.md) · [QUAL §7](site-qualification/7-operating-accountability-handover-and-change.md) |
| Source IDs | S00 |
| Wording disposition | Unchanged from v1.2 |
| Execution status | Specified, not executed by this release |
| Tests | [CT-049](test-specifications.md#CT-049) · [CT-069](test-specifications.md#CT-069) · [CT-075](test-specifications.md#CT-075) |

<a id="EVID-002"></a>
## EVID-002

Evidence SHALL bind target generation, source/profile/capability/dependency digests, artifact integrity, collection time, test executions and active exceptions; freshness SHALL be evaluated after material changes.

| Source field | Retained value |
| --- | --- |
| Accountable role | Assurance engineering |
| Parent sections | [RA §26](../architecture/reference/26-operating-model-capacity-and-observability.md) · [RA §28](../architecture/reference/28-architecture-acceptance-and-verification.md) |
| Supplement homes | [QUAL §3](site-qualification/3-capacity-service-envelopes-and-growth-triggers.md) · [QUAL §5](site-qualification/5-qualification-stages-applicability-and-evidence.md) · [QUAL §6](site-qualification/6-control-inheritance-assurance-and-organizational-interfaces.md) · [QUAL §7](site-qualification/7-operating-accountability-handover-and-change.md) |
| Source IDs | S05; S11 |
| Wording disposition | Unchanged from v1.2 |
| Execution status | Specified, not executed by this release |
| Tests | [CT-048](test-specifications.md#CT-048) · [CT-049](test-specifications.md#CT-049) · [CT-069](test-specifications.md#CT-069) |

<a id="EVID-003"></a>
## EVID-003

Formal authorization decisions SHALL be issued by the designated authority and retained separately from technical test status, with scope, validity and operating conditions that the controller can evaluate.

| Source field | Retained value |
| --- | --- |
| Accountable role | Security authority |
| Parent sections | [RA §26](../architecture/reference/26-operating-model-capacity-and-observability.md) · [RA §28](../architecture/reference/28-architecture-acceptance-and-verification.md) |
| Supplement homes | [QUAL §3](site-qualification/3-capacity-service-envelopes-and-growth-triggers.md) · [QUAL §5](site-qualification/5-qualification-stages-applicability-and-evidence.md) · [QUAL §6](site-qualification/6-control-inheritance-assurance-and-organizational-interfaces.md) · [QUAL §7](site-qualification/7-operating-accountability-handover-and-change.md) |
| Source IDs | S04; S05 |
| Wording disposition | Unchanged from v1.2 |
| Execution status | Specified, not executed by this release |
| Tests | [CT-049](test-specifications.md#CT-049) · [CT-058](test-specifications.md#CT-058) · [CT-069](test-specifications.md#CT-069) |

Related ADRs: [ADR-0017](../adr/0017-separate-reference-adoption-technical-qualification-and-authorization.md)

<a id="OBS-001"></a>
## OBS-001

Logs SHALL contain stable identifiers sufficient to correlate tenant, WSD, Security Domain, policy, and deployment evidence.

| Source field | Retained value |
| --- | --- |
| Accountable role | Security operations |
| Parent sections | [RA §26](../architecture/reference/26-operating-model-capacity-and-observability.md) |
| Supplement homes | [QUAL §3](site-qualification/3-capacity-service-envelopes-and-growth-triggers.md) · [QUAL §7](site-qualification/7-operating-accountability-handover-and-change.md) |
| Source IDs | S00 |
| Wording disposition | Unchanged from v1.2 |
| Execution status | Specified, not executed by this release |
| Tests | [CT-010](test-specifications.md#CT-010) · [CT-049](test-specifications.md#CT-049) |

Related ADRs: [ADR-0037](../adr/0037-define-independent-telemetry-and-collection-loss-behaviour.md)

<a id="OBS-002"></a>
## OBS-002

Security control logging SHALL not depend solely on the tenant workload being healthy or cooperative.

| Source field | Retained value |
| --- | --- |
| Accountable role | Security operations |
| Parent sections | [RA §26](../architecture/reference/26-operating-model-capacity-and-observability.md) |
| Supplement homes | [QUAL §3](site-qualification/3-capacity-service-envelopes-and-growth-triggers.md) · [QUAL §7](site-qualification/7-operating-accountability-handover-and-change.md) |
| Source IDs | S00 |
| Wording disposition | Unchanged from v1.2 |
| Execution status | Specified, not executed by this release |
| Tests | [CT-010](test-specifications.md#CT-010) · [CT-050](test-specifications.md#CT-050) |

Related ADRs: [ADR-0037](../adr/0037-define-independent-telemetry-and-collection-loss-behaviour.md)

<a id="OBS-003"></a>
## OBS-003

Logging profiles SHALL define event coverage, attribution, time integrity, minimization, forwarding latency, buffering, loss alerting, retention, access and safe behavior during collection failure.

| Source field | Retained value |
| --- | --- |
| Accountable role | Security operations |
| Parent sections | [RA §26](../architecture/reference/26-operating-model-capacity-and-observability.md) |
| Supplement homes | [QUAL §3](site-qualification/3-capacity-service-envelopes-and-growth-triggers.md) · [QUAL §7](site-qualification/7-operating-accountability-handover-and-change.md) |
| Source IDs | S11 |
| Wording disposition | Unchanged from v1.2 |
| Execution status | Specified, not executed by this release |
| Tests | [CT-010](test-specifications.md#CT-010) · [CT-050](test-specifications.md#CT-050) · [CT-068](test-specifications.md#CT-068) |

Related ADRs: [ADR-0037](../adr/0037-define-independent-telemetry-and-collection-loss-behaviour.md)

<a id="CAP-001"></a>
## CAP-001

Capacity planning SHALL include N+failure headroom so that loss of a security-edge node does not require disabling or bypassing enforcement.

| Source field | Retained value |
| --- | --- |
| Accountable role | Capacity management |
| Parent sections | [RA §4](../architecture/reference/4-hosting-cells-resource-pools-and-failure-boundaries.md) · [RA §26](../architecture/reference/26-operating-model-capacity-and-observability.md) |
| Supplement homes | [NET §2](../engineering/fabric/2-isolated-attachment-units-and-bounded-capacity.md) · [QUAL §2](site-qualification/2-site-low-level-design-and-dependency-schedule.md) · [QUAL §3](site-qualification/3-capacity-service-envelopes-and-growth-triggers.md) · [QUAL §7](site-qualification/7-operating-accountability-handover-and-change.md) |
| Source IDs | S00 |
| Wording disposition | Unchanged from v1.2 |
| Execution status | Specified, not executed by this release |
| Tests | [CT-012](test-specifications.md#CT-012) · [CT-056](test-specifications.md#CT-056) |

Related ADRs: [ADR-0030](../adr/0030-admit-demand-against-every-surviving-capacity-bottleneck.md)

<a id="CAP-002"></a>
## CAP-002

Placement and growth admission SHALL evaluate measured surviving capacity, security-feature overhead, shared dependencies, quotas and operational reserves for the approved failure model.

| Source field | Retained value |
| --- | --- |
| Accountable role | Capacity management |
| Parent sections | [RA §4](../architecture/reference/4-hosting-cells-resource-pools-and-failure-boundaries.md) · [RA §26](../architecture/reference/26-operating-model-capacity-and-observability.md) |
| Supplement homes | [NET §2](../engineering/fabric/2-isolated-attachment-units-and-bounded-capacity.md) · [QUAL §2](site-qualification/2-site-low-level-design-and-dependency-schedule.md) · [QUAL §3](site-qualification/3-capacity-service-envelopes-and-growth-triggers.md) · [QUAL §7](site-qualification/7-operating-accountability-handover-and-change.md) |
| Source IDs | S00 |
| Wording disposition | Unchanged from v1.2 |
| Execution status | Specified, not executed by this release |
| Tests | [CT-039](test-specifications.md#CT-039) · [CT-047](test-specifications.md#CT-047) · [CT-056](test-specifications.md#CT-056) |

Related ADRs: [ADR-0004](../adr/0004-scale-through-commissioned-hosting-cells-and-capacity-pools.md) · [ADR-0030](../adr/0030-admit-demand-against-every-surviving-capacity-bottleneck.md)

<a id="CAP-003"></a>
## CAP-003

Capacity reporting SHALL distinguish procured, received, commissioned, allocated, reserved and consumed capacity and identify unused-capacity age, constraints and accountable remediation.

| Source field | Retained value |
| --- | --- |
| Accountable role | Service management |
| Parent sections | [RA §4](../architecture/reference/4-hosting-cells-resource-pools-and-failure-boundaries.md) · [RA §26](../architecture/reference/26-operating-model-capacity-and-observability.md) |
| Supplement homes | [NET §2](../engineering/fabric/2-isolated-attachment-units-and-bounded-capacity.md) · [QUAL §2](site-qualification/2-site-low-level-design-and-dependency-schedule.md) · [QUAL §3](site-qualification/3-capacity-service-envelopes-and-growth-triggers.md) · [QUAL §7](site-qualification/7-operating-accountability-handover-and-change.md) |
| Source IDs | S28 |
| Wording disposition | Unchanged from v1.2 |
| Execution status | Specified, not executed by this release |
| Tests | [CT-074](test-specifications.md#CT-074) |

Related ADRs: [ADR-0030](../adr/0030-admit-demand-against-every-surviving-capacity-bottleneck.md)

<a id="FAIL-001"></a>
## FAIL-001

Control-plane failure SHALL NOT create an implicit permit path.

| Source field | Retained value |
| --- | --- |
| Accountable role | Platform operations |
| Parent sections | [RA §14](../architecture/reference/14-availability-multi-site-operation-and-recovery-topology.md) · [RA §27](../architecture/reference/27-recovery-migration-and-retirement.md) |
| Supplement homes | [PROV §6](../implementation/provisioning-strategy/6-brownfield-adoption-growth-and-retirement.md) · [QUAL §4](site-qualification/4-service-parameter-and-requirement-decisions.md) · [SVC §4](../architecture/shared-services/4-storage-copies-and-retained-data-ownership.md) · [SVC §6](../architecture/shared-services/6-failure-recovery-migration-and-failback-topology.md) |
| Source IDs | S00 |
| Wording disposition | Unchanged from v1.2 |
| Execution status | Specified, not executed by this release |
| Tests | [CT-011](test-specifications.md#CT-011) · [CT-012](test-specifications.md#CT-012) · [CT-024](test-specifications.md#CT-024) · [CT-052](test-specifications.md#CT-052) |

<a id="FAIL-002"></a>
## FAIL-002

Failover and control-plane-loss scenarios SHALL be included in platform conformance testing.

| Source field | Retained value |
| --- | --- |
| Accountable role | Assurance engineering |
| Parent sections | [RA §14](../architecture/reference/14-availability-multi-site-operation-and-recovery-topology.md) · [RA §27](../architecture/reference/27-recovery-migration-and-retirement.md) |
| Supplement homes | [PROV §6](../implementation/provisioning-strategy/6-brownfield-adoption-growth-and-retirement.md) · [QUAL §4](site-qualification/4-service-parameter-and-requirement-decisions.md) · [SVC §4](../architecture/shared-services/4-storage-copies-and-retained-data-ownership.md) · [SVC §6](../architecture/shared-services/6-failure-recovery-migration-and-failback-topology.md) |
| Source IDs | S00 |
| Wording disposition | Unchanged from v1.2 |
| Execution status | Specified, not executed by this release |
| Tests | [CT-011](test-specifications.md#CT-011) · [CT-012](test-specifications.md#CT-012) · [CT-027](test-specifications.md#CT-027) · [CT-038](test-specifications.md#CT-038) · [CT-050](test-specifications.md#CT-050) · [CT-054](test-specifications.md#CT-054) · [CT-055](test-specifications.md#CT-055) |

<a id="FAIL-003"></a>
## FAIL-003

Every critical dependency SHALL have a qualified loss/partition/recovery behavior, including credential/key continuity, logging loss, state recovery and split-brain prevention; unavailable authority SHALL NOT authorize fallback bypass.

| Source field | Retained value |
| --- | --- |
| Accountable role | Platform operations |
| Parent sections | [RA §14](../architecture/reference/14-availability-multi-site-operation-and-recovery-topology.md) · [RA §27](../architecture/reference/27-recovery-migration-and-retirement.md) |
| Supplement homes | [PROV §6](../implementation/provisioning-strategy/6-brownfield-adoption-growth-and-retirement.md) · [QUAL §4](site-qualification/4-service-parameter-and-requirement-decisions.md) · [SVC §4](../architecture/shared-services/4-storage-copies-and-retained-data-ownership.md) · [SVC §6](../architecture/shared-services/6-failure-recovery-migration-and-failback-topology.md) |
| Source IDs | S00 |
| Wording disposition | Unchanged from v1.2 |
| Execution status | Specified, not executed by this release |
| Tests | [CT-027](test-specifications.md#CT-027) · [CT-038](test-specifications.md#CT-038) · [CT-044](test-specifications.md#CT-044) · [CT-050](test-specifications.md#CT-050) · [CT-054](test-specifications.md#CT-054) · [CT-055](test-specifications.md#CT-055) |

<a id="REC-001"></a>
## REC-001

Recovery procedures SHALL include independent bootstrap access, protected key/state/catalog recovery, dependency ordering, writer fencing, isolated validation and attributable activation authority.

| Source field | Retained value |
| --- | --- |
| Accountable role | Continuity management |
| Parent sections | [RA §21](../architecture/reference/21-day-0-bootstrap-and-physical-commissioning.md) · [RA §27](../architecture/reference/27-recovery-migration-and-retirement.md) |
| Supplement homes | [PROV §2](../implementation/provisioning-strategy/2-day-0-and-steady-state-commissioning-without-circular-dependencies.md) · [PROV §6](../implementation/provisioning-strategy/6-brownfield-adoption-growth-and-retirement.md) · [SVC §4](../architecture/shared-services/4-storage-copies-and-retained-data-ownership.md) · [SVC §6](../architecture/shared-services/6-failure-recovery-migration-and-failback-topology.md) |
| Source IDs | S00 |
| Wording disposition | Unchanged from v1.2 |
| Execution status | Specified, not executed by this release |
| Tests | [CT-052](test-specifications.md#CT-052) · [CT-054](test-specifications.md#CT-054) · [CT-055](test-specifications.md#CT-055) |

Related ADRs: [ADR-0014](../adr/0014-bootstrap-management-and-trust-before-consuming-native-apis.md) · [ADR-0028](../adr/0028-protect-backup-administration-and-prove-isolated-usable-restore.md) · [ADR-0029](../adr/0029-keep-recovery-trust-material-independent-of-the-platform-it-unlocks.md)

<a id="REC-002"></a>
## REC-002

Recovery and failback exercises SHALL measure actual service RTO/RPO, data consistency and security outcomes and SHALL remove temporary routes, grants and exposures after authorized completion.

| Source field | Retained value |
| --- | --- |
| Accountable role | Continuity management |
| Parent sections | [RA §21](../architecture/reference/21-day-0-bootstrap-and-physical-commissioning.md) · [RA §27](../architecture/reference/27-recovery-migration-and-retirement.md) |
| Supplement homes | [PROV §2](../implementation/provisioning-strategy/2-day-0-and-steady-state-commissioning-without-circular-dependencies.md) · [PROV §6](../implementation/provisioning-strategy/6-brownfield-adoption-growth-and-retirement.md) · [SVC §4](../architecture/shared-services/4-storage-copies-and-retained-data-ownership.md) · [SVC §6](../architecture/shared-services/6-failure-recovery-migration-and-failback-topology.md) |
| Source IDs | S00 |
| Wording disposition | Unchanged from v1.2 |
| Execution status | Specified, not executed by this release |
| Tests | [CT-052](test-specifications.md#CT-052) · [CT-054](test-specifications.md#CT-054) · [CT-055](test-specifications.md#CT-055) · [CT-060](test-specifications.md#CT-060) |

Related ADRs: [ADR-0011](../adr/0011-default-to-site-local-domains-and-routed-recovery.md) · [ADR-0019](../adr/0019-separate-information-impacts-from-service-level-and-recovery-promises.md) · [ADR-0036](../adr/0036-require-initial-operational-and-recovery-readiness-before-production-activation.md)

<a id="VULN-001"></a>
## VULN-001

All platform and automation assets SHALL have version/support inventory, vulnerability ownership, risk-based remediation targets, exception handling and retirement decisions.

| Source field | Retained value |
| --- | --- |
| Accountable role | Vulnerability management |
| Parent sections | [RA §25](../architecture/reference/25-change-brownfield-adoption-and-configuration-ownership.md) |
| Supplement homes | [PROV §5](../implementation/provisioning-strategy/5-concurrency-ownership-and-failed-execution.md) · [PROV §6](../implementation/provisioning-strategy/6-brownfield-adoption-growth-and-retirement.md) |
| Source IDs | S05; S07 |
| Wording disposition | Unchanged from v1.2 |
| Execution status | Specified, not executed by this release |
| Tests | [CT-041](test-specifications.md#CT-041) · [CT-042](test-specifications.md#CT-042) · [CT-074](test-specifications.md#CT-074) |

Related ADRs: [ADR-0034](../adr/0034-classify-change-by-architectural-impact-rather-than-file-location.md) · [ADR-0038](../adr/0038-govern-images-and-privileged-dependency-provenance-across-their-lifecycle.md)

<a id="VULN-002"></a>
## VULN-002

Security updates SHALL use trusted artifacts, compatibility/regression evidence, phased promotion and a tested recovery strategy; unsupported or vulnerable templates SHALL be controlled at new-deployment admission.

| Source field | Retained value |
| --- | --- |
| Accountable role | Platform engineering |
| Parent sections | [RA §25](../architecture/reference/25-change-brownfield-adoption-and-configuration-ownership.md) |
| Supplement homes | [PROV §5](../implementation/provisioning-strategy/5-concurrency-ownership-and-failed-execution.md) · [PROV §6](../implementation/provisioning-strategy/6-brownfield-adoption-growth-and-retirement.md) |
| Source IDs | S07 |
| Wording disposition | Unchanged from v1.2 |
| Execution status | Specified, not executed by this release |
| Tests | [CT-015](test-specifications.md#CT-015) · [CT-040](test-specifications.md#CT-040) · [CT-041](test-specifications.md#CT-041) · [CT-042](test-specifications.md#CT-042) |

Related ADRs: [ADR-0034](../adr/0034-classify-change-by-architectural-impact-rather-than-file-location.md) · [ADR-0038](../adr/0038-govern-images-and-privileged-dependency-provenance-across-their-lifecycle.md)

<a id="IR-001"></a>
## IR-001

Emergency containment SHALL be possible without requiring a physical-fabric redesign or broad outage to unrelated tenants.

| Source field | Retained value |
| --- | --- |
| Accountable role | Incident response |
| Parent sections | [RA §25](../architecture/reference/25-change-brownfield-adoption-and-configuration-ownership.md) · [RA §27](../architecture/reference/27-recovery-migration-and-retirement.md) |
| Supplement homes | [PROV §5](../implementation/provisioning-strategy/5-concurrency-ownership-and-failed-execution.md) · [PROV §6](../implementation/provisioning-strategy/6-brownfield-adoption-growth-and-retirement.md) · [SVC §4](../architecture/shared-services/4-storage-copies-and-retained-data-ownership.md) · [SVC §6](../architecture/shared-services/6-failure-recovery-migration-and-failback-topology.md) |
| Source IDs | S00 |
| Wording disposition | Unchanged from v1.2 |
| Execution status | Specified, not executed by this release |
| Tests | [CT-057](test-specifications.md#CT-057) · [CT-067](test-specifications.md#CT-067) |

Related ADRs: [ADR-0032](../adr/0032-keep-incident-containment-above-routine-reconciliation.md)

<a id="IR-002"></a>
## IR-002

Incident procedures SHALL define authority, scoped containment, evidence custody, coordination, recovery acceptance and reconciliation of emergency changes; containment release SHALL be explicit and attributable.

| Source field | Retained value |
| --- | --- |
| Accountable role | Incident response |
| Parent sections | [RA §25](../architecture/reference/25-change-brownfield-adoption-and-configuration-ownership.md) · [RA §27](../architecture/reference/27-recovery-migration-and-retirement.md) |
| Supplement homes | [PROV §5](../implementation/provisioning-strategy/5-concurrency-ownership-and-failed-execution.md) · [PROV §6](../implementation/provisioning-strategy/6-brownfield-adoption-growth-and-retirement.md) · [SVC §4](../architecture/shared-services/4-storage-copies-and-retained-data-ownership.md) · [SVC §6](../architecture/shared-services/6-failure-recovery-migration-and-failback-topology.md) |
| Source IDs | S12 |
| Wording disposition | Unchanged from v1.2 |
| Execution status | Specified, not executed by this release |
| Tests | [CT-049](test-specifications.md#CT-049) · [CT-057](test-specifications.md#CT-057) · [CT-058](test-specifications.md#CT-058) · [CT-066](test-specifications.md#CT-066) |

Related ADRs: [ADR-0032](../adr/0032-keep-incident-containment-above-routine-reconciliation.md)

<a id="LIFE-001"></a>
## LIFE-001

Offboarding SHALL remove obsolete routes and policy objects and SHALL produce evidence of completion.

| Source field | Retained value |
| --- | --- |
| Accountable role | Service management |
| Parent sections | [RA §27](../architecture/reference/27-recovery-migration-and-retirement.md) |
| Supplement homes | [PROV §6](../implementation/provisioning-strategy/6-brownfield-adoption-growth-and-retirement.md) · [SVC §4](../architecture/shared-services/4-storage-copies-and-retained-data-ownership.md) · [SVC §6](../architecture/shared-services/6-failure-recovery-migration-and-failback-topology.md) |
| Source IDs | S00 |
| Wording disposition | Unchanged from v1.2 |
| Execution status | Specified, not executed by this release |
| Tests | [CT-013](test-specifications.md#CT-013) · [CT-059](test-specifications.md#CT-059) · [CT-070](test-specifications.md#CT-070) |

Related ADRs: [ADR-0033](../adr/0033-separate-live-service-retirement-from-retained-data-disposal.md)

<a id="LIFE-002"></a>
## LIFE-002

Retirement SHALL distinguish live-service removal from retained-data obligations and SHALL verify identity, DNS, route, policy, attachment, copy and key lifecycle without deleting shared or held resources.

| Source field | Retained value |
| --- | --- |
| Accountable role | Service management |
| Parent sections | [RA §27](../architecture/reference/27-recovery-migration-and-retirement.md) |
| Supplement homes | [PROV §6](../implementation/provisioning-strategy/6-brownfield-adoption-growth-and-retirement.md) · [SVC §4](../architecture/shared-services/4-storage-copies-and-retained-data-ownership.md) · [SVC §6](../architecture/shared-services/6-failure-recovery-migration-and-failback-topology.md) |
| Source IDs | S27 |
| Wording disposition | Unchanged from v1.2 |
| Execution status | Specified, not executed by this release |
| Tests | [CT-013](test-specifications.md#CT-013) · [CT-053](test-specifications.md#CT-053) · [CT-059](test-specifications.md#CT-059) · [CT-070](test-specifications.md#CT-070) · [CT-078](test-specifications.md#CT-078) |

Related ADRs: [ADR-0016](../adr/0016-assign-one-authoritative-writer-per-native-object-and-sensitive-subresource.md) · [ADR-0033](../adr/0033-separate-live-service-retirement-from-retained-data-disposal.md)

<a id="LIFE-003"></a>
## LIFE-003

Sanitization SHALL use an approved media-appropriate method with copy/key-scope evidence; deletion of a resource record SHALL NOT alone constitute proof of data destruction.

| Source field | Retained value |
| --- | --- |
| Accountable role | Data owner |
| Parent sections | [RA §27](../architecture/reference/27-recovery-migration-and-retirement.md) |
| Supplement homes | [PROV §6](../implementation/provisioning-strategy/6-brownfield-adoption-growth-and-retirement.md) · [SVC §4](../architecture/shared-services/4-storage-copies-and-retained-data-ownership.md) · [SVC §6](../architecture/shared-services/6-failure-recovery-migration-and-failback-topology.md) |
| Source IDs | S27 |
| Wording disposition | Unchanged from v1.2 |
| Execution status | Specified, not executed by this release |
| Tests | [CT-053](test-specifications.md#CT-053) · [CT-059](test-specifications.md#CT-059) |

Related ADRs: [ADR-0033](../adr/0033-separate-live-service-retirement-from-retained-data-disposal.md)

<a id="MIG-001"></a>
## MIG-001

Migration connectivity SHALL be time-bound unless explicitly converted to an approved steady-state connection.

| Source field | Retained value |
| --- | --- |
| Accountable role | Migration owner |
| Parent sections | [RA §27](../architecture/reference/27-recovery-migration-and-retirement.md) |
| Supplement homes | [PROV §6](../implementation/provisioning-strategy/6-brownfield-adoption-growth-and-retirement.md) · [SVC §4](../architecture/shared-services/4-storage-copies-and-retained-data-ownership.md) · [SVC §6](../architecture/shared-services/6-failure-recovery-migration-and-failback-topology.md) |
| Source IDs | S00 |
| Wording disposition | Unchanged from v1.2 |
| Execution status | Specified, not executed by this release |
| Tests | [CT-058](test-specifications.md#CT-058) · [CT-060](test-specifications.md#CT-060) · [CT-076](test-specifications.md#CT-076) |

Related ADRs: [ADR-0012](../adr/0012-distinguish-persistent-platform-transports-from-temporary-migration-access.md)

<a id="MIG-002"></a>
## MIG-002

Migration flows SHALL traverse an approved security edge when they cross security-domain boundaries.

| Source field | Retained value |
| --- | --- |
| Accountable role | Migration owner |
| Parent sections | [RA §27](../architecture/reference/27-recovery-migration-and-retirement.md) |
| Supplement homes | [PROV §6](../implementation/provisioning-strategy/6-brownfield-adoption-growth-and-retirement.md) · [SVC §4](../architecture/shared-services/4-storage-copies-and-retained-data-ownership.md) · [SVC §6](../architecture/shared-services/6-failure-recovery-migration-and-failback-topology.md) |
| Source IDs | S00 |
| Wording disposition | Unchanged from v1.2 |
| Execution status | Specified, not executed by this release |
| Tests | [CT-003](test-specifications.md#CT-003) · [CT-060](test-specifications.md#CT-060) |

Related ADRs: [ADR-0012](../adr/0012-distinguish-persistent-platform-transports-from-temporary-migration-access.md)

<a id="MIG-003"></a>
## MIG-003

Migration and exit rehearsals SHALL validate data/application consistency, identity/key dependencies, equivalent security outcomes, fencing/cutover, rollback feasibility and complete transition teardown.

| Source field | Retained value |
| --- | --- |
| Accountable role | Migration owner |
| Parent sections | [RA §27](../architecture/reference/27-recovery-migration-and-retirement.md) |
| Supplement homes | [PROV §6](../implementation/provisioning-strategy/6-brownfield-adoption-growth-and-retirement.md) · [SVC §4](../architecture/shared-services/4-storage-copies-and-retained-data-ownership.md) · [SVC §6](../architecture/shared-services/6-failure-recovery-migration-and-failback-topology.md) |
| Source IDs | S00 |
| Wording disposition | Unchanged from v1.2 |
| Execution status | Specified, not executed by this release |
| Tests | [CT-054](test-specifications.md#CT-054) · [CT-060](test-specifications.md#CT-060) · [CT-073](test-specifications.md#CT-073) · [CT-078](test-specifications.md#CT-078) |

Related ADRs: [ADR-0012](../adr/0012-distinguish-persistent-platform-transports-from-temporary-migration-access.md)

<a id="OPS-001"></a>
## OPS-001

Each service SHALL publish a provider/tenant/shared control responsibility matrix and accountable decision owners for its complete lifecycle, including inherited controls, support access and data disposal.

| Source field | Retained value |
| --- | --- |
| Accountable role | Service management |
| Parent sections | [RA §20](../architecture/reference/20-provisioning-model-and-infrastructure-work-packages.md) · [RA §26](../architecture/reference/26-operating-model-capacity-and-observability.md) |
| Supplement homes | [PROV §1](../implementation/provisioning-strategy/1-provisioning-scopes-ownership-and-accepted-handoffs.md) · [QUAL §3](site-qualification/3-capacity-service-envelopes-and-growth-triggers.md) · [QUAL §7](site-qualification/7-operating-accountability-handover-and-change.md) |
| Source IDs | S05; S28 |
| Wording disposition | Unchanged from v1.2 |
| Execution status | Specified, not executed by this release |
| Tests | [CT-019](test-specifications.md#CT-019) · [CT-062](test-specifications.md#CT-062) · [CT-079](test-specifications.md#CT-079) |

Related ADRs: [ADR-0034](../adr/0034-classify-change-by-architectural-impact-rather-than-file-location.md)

<a id="OPS-002"></a>
## OPS-002

Production handover SHALL include owner/escalation, dependency, SLO/recovery, capacity, monitoring, runbook, support/version and evidence records; privileged access SHALL be reviewed against the actual authority model.

| Source field | Retained value |
| --- | --- |
| Accountable role | Service management |
| Parent sections | [RA §20](../architecture/reference/20-provisioning-model-and-infrastructure-work-packages.md) · [RA §26](../architecture/reference/26-operating-model-capacity-and-observability.md) |
| Supplement homes | [PROV §1](../implementation/provisioning-strategy/1-provisioning-scopes-ownership-and-accepted-handoffs.md) · [QUAL §3](site-qualification/3-capacity-service-envelopes-and-growth-triggers.md) · [QUAL §7](site-qualification/7-operating-accountability-handover-and-change.md) |
| Source IDs | S00 |
| Wording disposition | Unchanged from v1.2 |
| Execution status | Specified, not executed by this release |
| Tests | [CT-019](test-specifications.md#CT-019) · [CT-062](test-specifications.md#CT-062) · [CT-069](test-specifications.md#CT-069) |

<a id="EXC-001"></a>
## EXC-001

Every exception SHALL have an accountable risk owner and expiry or review date.

| Source field | Retained value |
| --- | --- |
| Accountable role | Risk owner |
| Parent sections | [RA §25](../architecture/reference/25-change-brownfield-adoption-and-configuration-ownership.md) |
| Supplement homes | [PROV §5](../implementation/provisioning-strategy/5-concurrency-ownership-and-failed-execution.md) · [PROV §6](../implementation/provisioning-strategy/6-brownfield-adoption-growth-and-retirement.md) |
| Source IDs | S00 |
| Wording disposition | Unchanged from v1.2 |
| Execution status | Specified, not executed by this release |
| Tests | [CT-058](test-specifications.md#CT-058) · [CT-062](test-specifications.md#CT-062) |

<a id="EXC-002"></a>
## EXC-002

The control plane SHALL surface expired exceptions as non-compliant state rather than allowing them to become permanent undocumented architecture.

| Source field | Retained value |
| --- | --- |
| Accountable role | Risk owner |
| Parent sections | [RA §25](../architecture/reference/25-change-brownfield-adoption-and-configuration-ownership.md) |
| Supplement homes | [PROV §5](../implementation/provisioning-strategy/5-concurrency-ownership-and-failed-execution.md) · [PROV §6](../implementation/provisioning-strategy/6-brownfield-adoption-growth-and-retirement.md) |
| Source IDs | S00 |
| Wording disposition | Unchanged from v1.2 |
| Execution status | Specified, not executed by this release |
| Tests | [CT-058](test-specifications.md#CT-058) · [CT-069](test-specifications.md#CT-069) |

<a id="EXC-003"></a>
## EXC-003

Exceptions SHALL bind requirement IDs, precise scope, effective/expiry times, compensating controls and authorized risk approval; expiry handling SHALL preserve evidence and follow a pre-approved secure continuity/remediation decision.

| Source field | Retained value |
| --- | --- |
| Accountable role | Risk owner |
| Parent sections | [RA §25](../architecture/reference/25-change-brownfield-adoption-and-configuration-ownership.md) |
| Supplement homes | [PROV §5](../implementation/provisioning-strategy/5-concurrency-ownership-and-failed-execution.md) · [PROV §6](../implementation/provisioning-strategy/6-brownfield-adoption-growth-and-retirement.md) |
| Source IDs | S00 |
| Wording disposition | Unchanged from v1.2 |
| Execution status | Specified, not executed by this release |
| Tests | [CT-017](test-specifications.md#CT-017) · [CT-058](test-specifications.md#CT-058) · [CT-069](test-specifications.md#CT-069) |

<a id="ONB-001"></a>
## ONB-001

Onboarding SHALL verify ownership, complete intent/profiles, current qualification/authorization conditions, operational readiness and lifecycle obligations before Service Ready is granted.

| Source field | Retained value |
| --- | --- |
| Accountable role | Service management |
| Parent sections | [RA §23](../architecture/reference/23-tenant-domain-and-workload-provisioning-sequence.md) · [RA §28](../architecture/reference/28-architecture-acceptance-and-verification.md) |
| Supplement homes | [PROV §4](../implementation/provisioning-strategy/4-end-to-end-fixture-provisioning-and-safe-activation.md) · [QUAL §5](site-qualification/5-qualification-stages-applicability-and-evidence.md) · [QUAL §6](site-qualification/6-control-inheritance-assurance-and-organizational-interfaces.md) · [VND §1](../engineering/platform-realizations/1-one-reference-environment-three-native-realizations.md) |
| Source IDs | S00 |
| Wording disposition | Unchanged from v1.2 |
| Execution status | Specified, not executed by this release |
| Tests | [CT-017](test-specifications.md#CT-017) · [CT-018](test-specifications.md#CT-018) · [CT-049](test-specifications.md#CT-049) · [CT-062](test-specifications.md#CT-062) · [CT-069](test-specifications.md#CT-069) |

Related ADRs: [ADR-0015](../adr/0015-build-under-deny-and-verify-before-and-after-activation.md) · [ADR-0036](../adr/0036-require-initial-operational-and-recovery-readiness-before-production-activation.md)

<a id="DEL-001"></a>
## DEL-001

The reference implementation SHALL demonstrate two-tenant isolation, controlled zone transitions, protected management, service bindings, recovery and retirement on a qualified first platform before scale expansion.

| Source field | Retained value |
| --- | --- |
| Accountable role | Delivery owner |
| Parent sections | [RA §22](../architecture/reference/22-vendor-platform-and-shared-service-commissioning.md) · [RA §30](../architecture/reference/30-implementation-handoff-and-delivery-sequence.md) |
| Supplement homes | [GM §3](gap-map/3-detailed-gap-register-and-treatment.md) · [PROV §2](../implementation/provisioning-strategy/2-day-0-and-steady-state-commissioning-without-circular-dependencies.md) · [PROV §3](../implementation/provisioning-strategy/3-terraform-native-tools-and-operation-level-support.md) · [QUAL §1](site-qualification/1-from-proposed-architecture-to-accepted-service.md) · [QUAL §2](site-qualification/2-site-low-level-design-and-dependency-schedule.md) · [SVC §1](../architecture/shared-services/1-shared-service-placement-and-consumption-boundaries.md) |
| Source IDs | S00 |
| Wording disposition | Unchanged from v1.2 |
| Execution status | Specified, not executed by this release |
| Tests | [CT-001](test-specifications.md#CT-001) · [CT-003](test-specifications.md#CT-003) · [CT-004](test-specifications.md#CT-004) · [CT-008](test-specifications.md#CT-008) · [CT-013](test-specifications.md#CT-013) · [CT-052](test-specifications.md#CT-052) · [CT-069](test-specifications.md#CT-069) |

<a id="DEL-002"></a>
## DEL-002

Multi-platform portability claims SHALL be supported by the same intent/core conformance outcomes on at least two qualified implementations and by a representative data/application exit rehearsal.

| Source field | Retained value |
| --- | --- |
| Accountable role | Delivery owner |
| Parent sections | [RA §22](../architecture/reference/22-vendor-platform-and-shared-service-commissioning.md) · [RA §30](../architecture/reference/30-implementation-handoff-and-delivery-sequence.md) |
| Supplement homes | [GM §3](gap-map/3-detailed-gap-register-and-treatment.md) · [PROV §2](../implementation/provisioning-strategy/2-day-0-and-steady-state-commissioning-without-circular-dependencies.md) · [PROV §3](../implementation/provisioning-strategy/3-terraform-native-tools-and-operation-level-support.md) · [QUAL §1](site-qualification/1-from-proposed-architecture-to-accepted-service.md) · [QUAL §2](site-qualification/2-site-low-level-design-and-dependency-schedule.md) · [SVC §1](../architecture/shared-services/1-shared-service-placement-and-consumption-boundaries.md) |
| Source IDs | S00 |
| Wording disposition | Unchanged from v1.2 |
| Execution status | Specified, not executed by this release |
| Tests | [CT-016](test-specifications.md#CT-016) · [CT-060](test-specifications.md#CT-060) · [CT-073](test-specifications.md#CT-073) |

<a id="ACPT-001"></a>
## ACPT-001

Production acceptance SHALL require current evidence for every applicable acceptance criterion, explicit exclusions and risk decisions, operational owner acceptance and a valid separately issued authorization decision.

| Source field | Retained value |
| --- | --- |
| Accountable role | Security authority |
| Parent sections | [RA §28](../architecture/reference/28-architecture-acceptance-and-verification.md) · [RA §30](../architecture/reference/30-implementation-handoff-and-delivery-sequence.md) |
| Supplement homes | [GM §3](gap-map/3-detailed-gap-register-and-treatment.md) · [QUAL §1](site-qualification/1-from-proposed-architecture-to-accepted-service.md) · [QUAL §2](site-qualification/2-site-low-level-design-and-dependency-schedule.md) · [QUAL §5](site-qualification/5-qualification-stages-applicability-and-evidence.md) · [QUAL §6](site-qualification/6-control-inheritance-assurance-and-organizational-interfaces.md) |
| Source IDs | S04; S05 |
| Wording disposition | Unchanged from v1.2 |
| Execution status | Specified, not executed by this release |
| Tests | [CT-018](test-specifications.md#CT-018) · [CT-049](test-specifications.md#CT-049) · [CT-062](test-specifications.md#CT-062) · [CT-069](test-specifications.md#CT-069) |

Related ADRs: [ADR-0015](../adr/0015-build-under-deny-and-verify-before-and-after-activation.md) · [ADR-0017](../adr/0017-separate-reference-adoption-technical-qualification-and-authorization.md) · [ADR-0036](../adr/0036-require-initial-operational-and-recovery-readiness-before-production-activation.md)
