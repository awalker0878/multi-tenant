# 1. Provisioning scopes, ownership and accepted handoffs

[Documentation home](../../README.md) · [Source document](../../../reference/Portable_Hosting_Delivery_Kits_v1_1/05_Reference_v1_4/04_Provisioning_and_Commissioning_v1_4.docx) · [Chapter index](README.md)

> **Source:** PROV — Draft v1.4. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: 483df77cff70166fbdfdf711135efa3beeecc8fe1015a58290cbebff5b80bdfd -->
<!-- SOURCE-BLOCK PROV:23 BEGIN -->

<a id="__RefHeading___Toc7812_1525915568"></a>
<a id="PROV_s_001"></a>

<!-- SOURCE-BLOCK PROV:23 END -->

<!-- SOURCE-BLOCK PROV:24 BEGIN -->

WD §§9–10 supplies a connected build-and-receipt schedule. P2 installation and P3 construction can use authorized bootstrap dependencies, but their joint acceptance precedes ordinary service advertising. Gate numbers do not override those dependency conditions.

<!-- SOURCE-BLOCK PROV:24 END -->

<!-- SOURCE-BLOCK PROV:25 BEGIN -->

Parent architecture: [RA §20](../../architecture/reference/20-provisioning-model-and-infrastructure-work-packages.md#RA_s_020)  •  [RA §22](../../architecture/reference/22-vendor-platform-and-shared-service-commissioning.md#RA_s_022)  •  [RA §24](../../architecture/reference/24-terraform-across-the-vendor-stacks.md#RA_s_024)

<!-- SOURCE-BLOCK PROV:25 END -->

<!-- SOURCE-BLOCK PROV:26 BEGIN -->

Provisioning is the execution of an approved infrastructure design. The same delivery may require a platform installer, network configuration tool, Terraform providers, protection tooling and service-owner actions. Tool choice does not transfer authority. The work packages below refine the parent P0–P6 model and describe infrastructure inputs and outputs; they do not prescribe a portal, controller implementation or programming language. \[[B2](07-references-parent-basis-and-external-context.md#PROV_src_B2) §§20–24\]

<!-- SOURCE-BLOCK PROV:26 END -->

<!-- SOURCE-BLOCK PROV:27 BEGIN -->


<a id="source-table-27"></a>

| Package / owner | Accepted inputs | Owned output and dependent consumer |
| --- | --- | --- |
| P0 · foundation/trust owner | Authorized site scope, bootstrap plan, verified installation material and custodians. | Restricted management access and minimum recoverable dependencies; consumed by P1–P3. |
| P1 · network/hardware owner | P0 access, actual physical inventory and approved fabric/OOB design. | Accepted transport and physical attachment capacity; consumed by platform and edge commissioning. |
| P2 · platform owner | P1 transport, trusted installer, required name/time/identity/key access. | Installed and baselined platform, eligible compute/storage/network pools; joint P3 testing before offering them. |
| P3 · security/shared-service owners | Accepted placement/management and required installed platform capability. | Security-edge and common-service endpoints, protected administration and published capacity; consumed by P4/P5. |
| P4 · domain/tenant owner | Approved request plus accepted P2/P3 service envelope and reserved capacity. | Entitled administrative scope, domain networks, denied attachments and mandatory baseline. |
| P5 · workload/service owners | Accepted P4 boundaries and required images/data/protection/service handoffs. | Owned endpoints, current service access, observed tests and controlled activation. |
| P6 · lifecycle owners | As-built inventory, ownership, retained-data obligations and approved change. | Updated, recovered or retired service with reconciled dependencies and evidence. |

<!-- SOURCE-BLOCK PROV:27 END -->

<!-- SOURCE-BLOCK PROV:28 BEGIN -->

<!-- SOURCE-BLOCK PROV:28 END -->

<!-- SOURCE-BLOCK PROV:29 BEGIN -->

Dependencies are not always a single linear chain. A platform installer may need temporary DNS or key access supplied through P0 before the permanent service is hosted in P3. P2 installation can therefore precede full P3 commissioning, while P2 service acceptance and P3 acceptance are jointly gated. The bootstrap record names these temporary dependencies and their transfer. Do not mark a cell available for tenant placement merely because installation completed.

<!-- SOURCE-BLOCK PROV:29 END -->

<!-- SOURCE-BLOCK PROV:30 BEGIN -->


<a id="source-table-30"></a>

| Handoff field | Concrete content | Why it matters |
| --- | --- | --- |
| Identity and version | Actual resource or service identity, owner and configuration/version reference. | Avoid a name pointing to a different gateway or endpoint after replacement. |
| Offered scope | Eligible tenant/domain/zone classes, address families and permitted operations. | A physical attachment or API is not permission for unrestricted use. |
| Capacity | Accepted available/reserved capacity, units, failure basis and expiry of a reservation. | The next package cannot count the same capacity twice. |
| Dependencies | Management, trust, route, storage, naming and recovery prerequisites. | Failure or withdrawal has an accountable affected-consumer list. |
| Readiness evidence | Observed configuration, test scope, unresolved conditions and acceptance authority. | A successful installer or Terraform process is not service acceptance. |
| Lifecycle rules | Who can change/delete, how consumption is withdrawn, and what retained/shared objects survive. | Dependent cleanup cannot destroy the shared service. |

<!-- SOURCE-BLOCK PROV:30 END -->

<!-- SOURCE-BLOCK PROV:31 BEGIN -->

<!-- SOURCE-BLOCK PROV:31 END -->

<!-- SOURCE-BLOCK PROV:32 BEGIN -->

One approved environment is a composition of scoped changes, not one all-powerful state file. For the reference fixture, the platform owner creates the native domain and endpoint resources, the edge owner creates Z01/Z02 and their approved routes/policy, the address/name owner assigns prefixes and records, and the protection/key owners supply their services. Exchange references and accepted readiness records rather than all underlying credentials or state.

<!-- SOURCE-BLOCK PROV:32 END -->

<!-- SOURCE-BLOCK PROV:33 BEGIN -->

Related engineering: [Parent work-package model](../../architecture/reference/20-provisioning-model-and-infrastructure-work-packages.md#RA_s_020)  •  [Two-tenant fixture](../../engineering/platform-realizations/1-one-reference-environment-three-native-realizations.md#VND_s_001)  •  [Decision accountability](../../assurance/site-qualification/7-operating-accountability-handover-and-change.md#QUAL_s_007)

<!-- SOURCE-BLOCK PROV:33 END -->

[Chapter index](README.md) · [Next chapter](2-day-0-and-steady-state-commissioning-without-circular-dependencies.md)

<!-- BEGIN GENERATED DECISION LINKS -->

## Related decision records

- [ADR-0013 — Compose provisioning across separate platform and service authorities](../../adr/0013-compose-provisioning-across-separate-platform-and-service-authorities.md)

<!-- END GENERATED DECISION LINKS -->
