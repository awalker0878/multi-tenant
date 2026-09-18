# 1. One reference environment, three native realizations

[Documentation home](../../README.md) · [Source document](../../../reference/Portable_Hosting_Delivery_Kits_v1_1/05_Reference_v1_4/03_Vendor_Stack_Realizations_v1_4.docx) · [Chapter index](README.md)

> **Source:** VND — Draft v1.4. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: 73be32b98783bd7857be8a00928c6894bf16f6bc98c8eb016058d3cf75b9d86b -->
<a id="__RefHeading___Toc4808_865363315"></a>
<a id="VND_s_001"></a>

Additional test capacity: one endpoint in each of four domains does not supply a same-domain endpoint pair. WD §11 adds one authorized disposable probe used sequentially, with peak five endpoints; simultaneous extra probes require separate capacity. Test same-host placement only where that co-residency is permitted.

Parent architecture: [RA §7](../../architecture/reference/7-tenant-environments-and-security-domain-placement.md#RA_s_007)  •  [RA §15](../../architecture/reference/15-cross-vendor-realization-model.md#RA_s_015)  •  [RA §23](../../architecture/reference/23-tenant-domain-and-workload-provisioning-sequence.md#RA_s_023)

The reference environment is a small qualification fixture, not a minimum production bill of materials. It contains two independent tenants, one WSD per tenant, an OZ and RZ domain instance for each WSD, and one disposable processor and data-service endpoint per tenant. The two endpoint roles exist to test hosting, placement, routing, storage and recovery; no business application design is prescribed. Production endpoint counts, quorum and availability are separate service decisions. \[[B2](08-references-parent-basis-and-external-context.md#VND_src_B2) §§7, 15, 23\]


<a id="source-table-28"></a>

| Stable identity | Meaning | Native allocation outcome |
| --- | --- | --- |
| tenant-01 / WSD-01 | First administrative scope and bounded workload environment. | Entitled resource access; no provider-wide management rights. |
| D01O / D01R | Independent OZ and RZ instances; symbolic prefixes P01O/P01R. | Separate routing/policy realization and qualified host-pool eligibility. |
| A01O / A01R; Z01 | Domain attachments and the approved tenant-01 OZ↔RZ boundary. | Isolated handoffs, correct forward/return routing and explicit policy. |
| tenant-02 / WSD-02 | Second administrative scope with no default path to tenant-01. | Same service outcomes but independently owned native resources. |
| D02O / D02R | Second pair of OZ/RZ instances; prefixes P02O/P02R. | No shared routing authority merely because zone labels match. |
| A02O / A02R; Z02 | Second pair of attachments and boundary relationship. | Policy and lifecycle remain independent of Z01. |
| Resolver/time/log/backup/key services | Approved shared consumption interfaces selected for the fixture. | Bindings and service-side entitlement, not broad provider-subnet access. |

The baseline fixture has no public ingress or general Internet egress. REF-DATA-HTTPS permits a processor to initiate TCP/443 to its own data endpoint with endpoint TLS validation. Necessary name, time, protection and initialization flows are separately declared. The same expected outcomes apply when the entire fixture is recreated on each stack; this does not require identical native object names or a shared overlay.


<a id="source-table-31"></a>

| Accounting item | Fixture quantity | Not included by implication |
| --- | --- | --- |
| Tenants / WSDs | 2 / 2 | Independent platform installations per tenant are not implied. |
| Domain instances / native routing scopes | 4 / at least the isolated scopes required by the selected realization | Four routing scopes do not establish four independent physical failure domains. |
| Logical domain attachments | 4 | Redundant links, physical ports and service-side contexts counted separately. |
| OZ↔RZ boundary relationships | 2 | Additional shared-service and management boundaries depend on actual placement. |
| Disposable compute endpoints | 4 | Not a production HA application or sufficient product cluster size. |
| Data/protection objects | Owned per endpoint/WSD as required by the selected test service | Snapshots, replicas, retained backups and keys are additional attributable objects. |

Qualification compares observed service outcomes: correct allocation, placement, intra-domain enforcement, approved inter-zone communication, management denial, data entitlement, service consumption, safe change, isolated restore and clean retirement. A successful VM create on all three platforms is insufficient. The fixture’s symbolic names are translated to actual native resource identifiers and retained in its as-built record.

Related engineering: [Shared path schedule](../fabric/3-worked-inter-zone-routing-and-enforcement-schedule.md#NET_s_003)  •  [Fixture provisioning sequence](../../implementation/provisioning-strategy/4-end-to-end-fixture-provisioning-and-safe-activation.md#PROV_s_004)  •  [Qualification stages](../../assurance/site-qualification/5-qualification-stages-applicability-and-evidence.md#QUAL_s_005)

[Chapter index](README.md) · [Next chapter](2-physical-placement-and-the-sharing-decision.md)

<!-- BEGIN GENERATED DECISION LINKS -->

## Related decision records

- [ADR-0018 — Separate tenant administration, WSD lifecycle and domain realization](../../adr/0018-separate-tenant-administration-wsd-lifecycle-and-domain-realization.md)

<!-- END GENERATED DECISION LINKS -->
