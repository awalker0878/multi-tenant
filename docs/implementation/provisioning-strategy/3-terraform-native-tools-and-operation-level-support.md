# 3. Terraform, native tools and operation-level support

[Documentation home](../../README.md) · [Source document](../../../reference/Portable_Hosting_Delivery_Kits_v1_1/05_Reference_v1_4/04_Provisioning_and_Commissioning_v1_4.docx) · [Chapter index](README.md)

> **Source:** PROV — Draft v1.4. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: 483df77cff70166fbdfdf711135efa3beeecc8fe1015a58290cbebff5b80bdfd -->
<!-- SOURCE-BLOCK PROV:43 BEGIN -->

<a id="__RefHeading___Toc7816_1525915568"></a>
<a id="PROV_s_003"></a>

<!-- SOURCE-BLOCK PROV:43 END -->

<!-- SOURCE-BLOCK PROV:44 BEGIN -->

Parent architecture: [RA §16](../../architecture/reference/16-nutanix-hosting-stack-reference-realization.md#RA_s_016)  •  [RA §17](../../architecture/reference/17-vmware-and-nsx-hosting-stack-reference-realization.md#RA_s_017)  •  [RA §18](../../architecture/reference/18-openstack-hosting-stack-reference-realization.md#RA_s_018)  •  [RA §22](../../architecture/reference/22-vendor-platform-and-shared-service-commissioning.md#RA_s_022)  •  [RA §24](../../architecture/reference/24-terraform-across-the-vendor-stacks.md#RA_s_024)

<!-- SOURCE-BLOCK PROV:44 END -->

<!-- SOURCE-BLOCK PROV:45 BEGIN -->

Select execution mechanisms at the resource-operation boundary. Terraform is appropriate where the qualified provider exposes the required lifecycle through supported management interfaces. A platform or distribution installer remains authoritative for installation and upgrades it owns. Shared services remain under their own management tools and credentials. A command embedded in Terraform does not gain declarative observation, update or deletion support merely from being invoked during an apply. \[[B2](07-references-parent-basis-and-external-context.md#PROV_src_B2) §§21, 24\]

<!-- SOURCE-BLOCK PROV:45 END -->

<!-- SOURCE-BLOCK PROV:46 BEGIN -->


<a id="source-table-46"></a>

| Resource family | Candidate execution owner/mechanism | Required lifecycle evidence |
| --- | --- | --- |
| Physical switches, OOB and attachment pools | Foundation configuration tooling or a specifically qualified network provider. | Read current config; safe changes; rollback/recovery; drift and withdrawal. |
| Nutanix domain, subnet, VM and policy | Qualified Nutanix API/provider for the selected AOS/Prism/Flow combination. | Per-resource create/read/update/adopt/delete, asynchronous task and failure behaviour. |
| VMware compute/storage and NSX networking | Separately scoped vSphere and NSX integrations; selected platform lifecycle tools. | Placement and disk changes; gateway/policy support; destructive replacement and release compatibility. |
| OpenStack tenant/instance/volume/network | Selected distribution lifecycle tools plus qualified service API/provider resources. | Tenant scope, backend-dependent policy, eventual consistency, cleanup and import limitations. |
| ZIP and external service policy | Security-owner-approved management/provider integration. | Context, routes, rules, sessions, HA state and safe revocation. |
| IPAM/DNS, keys, identity and protection | Authoritative service integrations, not recreated by every hosting adapter. | Reservations, ownership, entitlement, version/expiry and compensating cleanup. |

<!-- SOURCE-BLOCK PROV:46 END -->

<!-- SOURCE-BLOCK PROV:47 BEGIN -->

<!-- SOURCE-BLOCK PROV:47 END -->

<!-- SOURCE-BLOCK PROV:48 BEGIN -->

The operation-coverage register accompanies this release. Its rows begin as unqualified, because no target environment was supplied. For each exact native resource, mark every operation as supported and verified, supported but not tested, unsupported, not applicable with rationale, or owned externally with an accepted handoff. Attach the actual provider/API and release evidence; do not fill a whole row from a provider’s product name.

<!-- SOURCE-BLOCK PROV:48 END -->

<!-- SOURCE-BLOCK PROV:49 BEGIN -->


<a id="source-table-49"></a>

| Operation | Question to resolve | Disqualifying ambiguity |
| --- | --- | --- |
| Observe | Can the owner find actual resource/config/task state after losing a response? | Only create is possible; no reliable reconciliation. |
| Create | Is baseline policy present before the new endpoint becomes reachable? | Native default connectivity exists until a later best-effort script. |
| Update / replace | Which changes are in-place, disruptive or destructive? | A resize/policy change unexpectedly recreates a live disk or gateway. |
| Adopt / import | Can existing identity and ownership be preserved without replacement? | Import is treated as permission to change every dependent live resource. |
| Delete | Are routes, ports, sessions, addresses and shared/retained dependencies reconciled? | A process reports success while active authority or owned resources remain. |
| Recover uncertain outcome | Can an interrupted operation be safely resumed or compensated? | Retry duplicates allocation or destroys data written after the first attempt. |

<!-- SOURCE-BLOCK PROV:49 END -->

<!-- SOURCE-BLOCK PROV:50 BEGIN -->

<!-- SOURCE-BLOCK PROV:50 END -->

<!-- SOURCE-BLOCK PROV:51 BEGIN -->

Root Terraform configurations supply provider configuration to focused modules; provider requirements and aliases are handled explicitly. Protect plan/state artifacts and keep execution authority aligned with the work package. Provider dependency lockfiles record provider selections and checksums, not remote module versions; pin module and executor artifacts independently. These tool rules implement, rather than determine, the architectural ownership model. \[[S13](07-references-parent-basis-and-external-context.md#PROV_src_S13); [S14](07-references-parent-basis-and-external-context.md#PROV_src_S14)\]

<!-- SOURCE-BLOCK PROV:51 END -->

<!-- SOURCE-BLOCK PROV:52 BEGIN -->

No particular firewall, IPAM, backup or key vendor is selected by this reference. Their integration owners must fill the missing operation rows before automation is offered. A supported external operation with a controlled handoff can be legitimate; an undocumented manual step or non-observable shell side effect cannot be reported as complete zero-touch coverage.

<!-- SOURCE-BLOCK PROV:52 END -->

<!-- SOURCE-BLOCK PROV:53 BEGIN -->

Related engineering: [Version and compatibility record](../../engineering/platform-realizations/7-implementation-tuple-and-decision-package.md#VND_s_007)  •  [Lifecycle qualification](../../assurance/site-qualification/5-qualification-stages-applicability-and-evidence.md#QUAL_s_005)

<!-- SOURCE-BLOCK PROV:53 END -->

[Previous chapter](2-day-0-and-steady-state-commissioning-without-circular-dependencies.md) · [Chapter index](README.md) · [Next chapter](4-end-to-end-fixture-provisioning-and-safe-activation.md)

<!-- BEGIN GENERATED DECISION LINKS -->

## Related decision records

- [ADR-0013 — Compose provisioning across separate platform and service authorities](../../adr/0013-compose-provisioning-across-separate-platform-and-service-authorities.md)

<!-- END GENERATED DECISION LINKS -->
