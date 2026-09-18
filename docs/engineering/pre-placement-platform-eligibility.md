# Pre-placement platform-family eligibility

**Purpose:** make the reference architecture's mandatory-capability rejection rule
executable without introducing a placement controller, scheduler, reservation service,
or custom hosting API.

The architecture separates a Workload Security Domain (WSD) from vendor topology. A
WSD carries service-owner, lifecycle, security and recovery requirements; it is not a
mandatory custom API type or necessarily a Terraform state. The provider first checks
the requested hosting outcome, then selects an eligible site/cell/service class, and
only after that allows a native scheduler to choose within an approved pool.

This check implements only the **platform-family capability** part of that sequence.

## Source architecture

The source requires:

- mandatory requirement conflicts to be rejected before resource allocation;
- a required dedicated or zone-specific pool to pause rather than silently become shared;
- portable deployment to preserve the same hosting requirement across eligible stacks;
- mandatory capability gaps to cause explicit rejection or an approved alternative;
- exact site/product/API/hardware/automation versions and qualification evidence to remain separate from the architecture.

Relevant source chapters:

- [Tenant environments and security-domain placement](../architecture/reference/7-tenant-environments-and-security-domain-placement.md)
- [Compute pools, hypervisors and workload placement](../architecture/reference/11-compute-pools-hypervisors-and-workload-placement.md)
- [Cross-vendor realization model](../architecture/reference/15-cross-vendor-realization-model.md)
- [Tenant/domain/workload provisioning sequence](../architecture/reference/23-tenant-domain-and-workload-provisioning-sequence.md)
- [Platform capability registry](platform-capability-registry.md)

The maintained WSD example remains
[the internal two-tenant protected workload solution](../current/internal-hosting-solution.md).

## Input boundary

The example request does **not** attempt to model the entire WSD deployment
specification. It references the reviewed engineering record and extracts only the
portable capabilities needed for a platform-family precheck.

The record contains:

| Field | Meaning |
|---|---|
| \`wsd_engineering_ref\` | Maintained engineering record that owns the actual WSD requirements. |
| \`candidate_platforms\` | Platform families already permitted for this engineering comparison. |
| \`mandatory_capabilities\` | Portable capabilities that cannot be reduced or substituted silently. |
| \`optional_capabilities\` | Capabilities whose absence is disclosed but does not satisfy or weaken a mandatory requirement. |
| \`required_assurance_profile\` | Optional explicit assurance-profile requirement; never inferred from a platform name. |
| \`site_binding\` | Must remain \`UNSELECTED\` in this profile. |
| \`production_authority\` | Must remain \`NOT_ASSESSED\`. |

Only \`SINGLE_PLATFORM_WSD\` is supported by this first profile. A split-platform WSD
is an explicit architecture variation that requires its own latency, failure,
connectivity and recovery analysis; it is not admitted by changing one flag here.

## Eligibility rule

\`scripts/check_platform_family_eligibility.py\` evaluates the request against
\`sources/capabilities/platform_registry.json\`.

A platform family is a capability match only when:

1. every mandatory portable capability is \`NATIVE_QUALIFIED\`;
2. the registry has an exact selected product tuple rather than \`UNSELECTED\`; and
3. any requested assurance profile is explicitly present in that tuple's qualified profile set.

Candidate Terraform source, documentation, provider locks and local fixtures cannot
satisfy these conditions.

Today the expected result is:

    HOLD_NO_NATIVE_QUALIFIED_PLATFORM

That is intentional because the current capability registry has no native-qualified
claims.

## What an eligible result still does not mean

Even a future result of:

    PLATFORM_FAMILY_CAPABILITY_MATCH_SITE_GATES_REMAIN

does not select or reserve anything.

The result always keeps these permissions false:

- \`may_select_site\`
- \`may_reserve_capacity\`
- \`may_allocate\`
- \`may_apply\`
- \`may_activate\`

The remaining architecture gates include requester authority, approved profiles,
site/cell/service-class eligibility, zone-sharing and physical placement policy,
quota and surviving capacity, compute/storage/network/key/recovery compatibility,
address and security-edge capacity, shared-service dependencies, site-specific
native qualification and operational acceptance.

This prevents a future placement implementation from treating "vendor feature exists"
as "this site can safely host this WSD."

## CLI use

Validate the repository's deliberately held example:

    python scripts/check_platform_family_eligibility.py \
      examples/pre_placement_capability_request.json.example \
      --expected-status HOLD_NO_NATIVE_QUALIFIED_PLATFORM

Without \`--expected-status\`, a held request returns nonzero. This makes the default
operational behavior fail closed.

The explicit expected status exists only so CI can assert the repository's current,
deliberate hold. If the capability registry later changes, that assertion must be
reviewed instead of silently turning the example into an eligible placement.

## Relationship to provisioning

This check belongs before architecture step **2 — Place and reserve**. It does not
implement step 1 in full and it does not perform step 2. The complete admission path
still has to validate authority, profiles, quota, zone relationships and declared
dependencies before reservation.

Terraform remains an implementation mechanism after the appropriate owners have
accepted the target and work-package inputs. This precheck does not turn Terraform,
the capability registry, or the WSD into a custom control-plane application.

[Engineering index](README.md) ·
[Capability registry](platform-capability-registry.md) ·
[Commissioning kit](../implementation/native-reference/README.md)
