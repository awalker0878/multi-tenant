# Network and boundary detailed engineering

[Documentation home](../../README.md) · [Source document](../../../reference/Portable_Hosting_Delivery_Kits_v1_1/02_Engineering/Network_and_Boundary_Detailed_Engineering.docx)

> **Source:** NBD — Delivery-kit v1.1 collection; original document version retained in the front matter. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: 7a86351d7f4be320e48d3112485bbab4b0f5b4a79cd0e420a823c793a708733a -->

## Chapters

- [1. Count and assign the actual isolation units](1-count-and-assign-the-actual-isolation-units.md)
- [2. Walk F14-01 through the forward and reply routes](2-walk-f14-01-through-the-forward-and-reply-routes.md)
- [3. Make service replies choose the originating context](3-make-service-replies-choose-the-originating-context.md)
- [4. Budget address families and encapsulation precisely](4-budget-address-families-and-encapsulation-precisely.md)
- [5. Keep fabric authority separate from tenant routing](5-keep-fabric-authority-separate-from-tenant-routing.md)
- [6. Issue an interface control and handoff record](6-issue-an-interface-control-and-handoff-record.md)
- [7. Release the network design under an explicit failure model](7-release-the-network-design-under-an-explicit-failure-model.md)

## Source front matter
<!-- SOURCE-BLOCK NBD:0 BEGIN -->

DESIGN DEVELOPMENT  /  NBD

<!-- SOURCE-BLOCK NBD:0 END -->

<!-- SOURCE-BLOCK NBD:1 BEGIN -->

## Network, Boundary and Shared-Service Detailed Engineering

<!-- SOURCE-BLOCK NBD:1 END -->

<!-- SOURCE-BLOCK NBD:2 BEGIN -->

*Connect addressing, forwarding, policy, return paths and failure behaviour in one buildable design.*

<!-- SOURCE-BLOCK NBD:2 END -->

<!-- SOURCE-BLOCK NBD:3 BEGIN -->

Kit release v1.1 • 17 September 2026 • Parent architecture v1.4 retained

<!-- SOURCE-BLOCK NBD:3 END -->

<!-- SOURCE-BLOCK NBD:4 BEGIN -->

Proposed engineering development. Reference examples, site decisions, actual observations and approval remain separate.

<!-- SOURCE-BLOCK NBD:4 END -->

<!-- SOURCE-BLOCK NBD:5 BEGIN -->

This supplement develops EK-03, EK-05 and EK-06 using the frozen WD fixture. Addresses remain documentation examples, not allocations for a site. Native resource syntax is deliberately left to the selected supported platform. The worked routes explain what the implementation must realize and observe.

<!-- SOURCE-BLOCK NBD:5 END -->

<!-- SOURCE-BLOCK NBD:6 BEGIN -->

## Section navigation

<!-- SOURCE-BLOCK NBD:6 END -->

<!-- SOURCE-BLOCK NBD:7 BEGIN -->

[1. Count and assign the actual isolation units](1-count-and-assign-the-actual-isolation-units.md#NBD_01)

<!-- SOURCE-BLOCK NBD:7 END -->

<!-- SOURCE-BLOCK NBD:8 BEGIN -->

[2. Walk F14-01 through the forward and reply routes](2-walk-f14-01-through-the-forward-and-reply-routes.md#NBD_02)

<!-- SOURCE-BLOCK NBD:8 END -->

<!-- SOURCE-BLOCK NBD:9 BEGIN -->

[3. Make service replies choose the originating context](3-make-service-replies-choose-the-originating-context.md#NBD_03)

<!-- SOURCE-BLOCK NBD:9 END -->

<!-- SOURCE-BLOCK NBD:10 BEGIN -->

[4. Budget address families and encapsulation precisely](4-budget-address-families-and-encapsulation-precisely.md#NBD_04)

<!-- SOURCE-BLOCK NBD:10 END -->

<!-- SOURCE-BLOCK NBD:11 BEGIN -->

[5. Keep fabric authority separate from tenant routing](5-keep-fabric-authority-separate-from-tenant-routing.md#NBD_05)

<!-- SOURCE-BLOCK NBD:11 END -->

<!-- SOURCE-BLOCK NBD:12 BEGIN -->

[6. Issue an interface control and handoff record](6-issue-an-interface-control-and-handoff-record.md#NBD_06)

<!-- SOURCE-BLOCK NBD:12 END -->

<!-- SOURCE-BLOCK NBD:13 BEGIN -->

[7. Release the network design under an explicit failure model](7-release-the-network-design-under-an-explicit-failure-model.md#NBD_07)

<!-- SOURCE-BLOCK NBD:13 END -->

<!-- SOURCE-BLOCK NBD:14 BEGIN -->

Basis: linked RA/WD and role-kit sections retain their original authority. The elaborations, record formats and calculations in this supplement are local proposals, not new government requirements. D-source references identify freshly checked public mechanisms, not installed compatibility. Exact source locators are in 04\_Shared/development/source\_reviews.csv.

<!-- SOURCE-BLOCK NBD:14 END -->

<!-- SOURCE-BLOCK NBD:15 BEGIN -->

<!-- SOURCE-BLOCK NBD:15 END -->
