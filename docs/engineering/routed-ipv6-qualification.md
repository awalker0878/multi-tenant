# Routed IPv6 reference-path qualification

**Work package:** I08 local packet extension. **State:** implemented laboratory profile;
only an actual successful exact-revision run establishes its stated local observations.
Native platform, site and production-service qualification remain unissued.

## Architecture and source authority

This work continues the existing two-tenant WD14 design, not a new hosting API or an
alternative security-zone model. The native gateway, EC and SE labels are the existing
reference roles; Linux namespaces and nftables are test instruments standing in for
those roles, not a selected production firewall or platform.

The unchanged [WD14 source](../../examples/wd14-routing.json) already declares both
address families. Its [connected design](../solutions/README.md),
[fabric address-family decisions](fabric/4-address-naming-and-protocol-family-decisions.md),
[MTU and failure engineering](fabric/5-mtu-performance-and-failure-engineering.md),
and [ADR-0021](../adr/0021-offer-address-families-explicitly-across-the-whole-service-path.md)
remain the architectural basis. The historical [I08 backlog entry](../../sources/implementation_backlog.csv)
identified real endpoint/AAAA observations but no routed IPv6 packet campaign.

IPV6-001, IPV6-002 and IPV6-003 require equivalent security outcomes for offered
families, negative tests before a dual-stack offer, and explicit local protocols,
PMTU, transition and service/recovery dependencies. The original requirement wording
is preserved in the [source register](../../reference/Portable_Hosting_Delivery_Kits_v1_1/04_Shared/requirements.csv).
This laboratory implements a bounded subset of that verification, not full closure of
those requirements. The original handbook likewise separated IPv6 negative-path proof
from simply selecting an IPv6 option; its earlier topology and controller framing are
historical and are not reintroduced here.

## Physical and logical realization of the experiment

The controller creates one empty master network namespace and sixteen node namespaces.
A private bridge and veth pair realize each existing reference segment. There is no
uplink, external host interface, management API, arbitrary inventory or user-supplied
address. No routable IPv4 address is assigned in the IPv6 run. IPv4 is independently
re-executed by the retained campaign, not used as an invisible fallback.

| Existing reference role | IPv6 laboratory responsibility | Deliberate limitation |
|---|---|---|
| Four workload endpoints | IPv6-only challenge clients/listeners; configured /64s | Not guest hardening or application qualification |
| Four native gateways | Existing connected networks and exact declared static routes | Not a Nutanix, NSX or Neutron implementation |
| EC-01 / EC-02 | Distinct stateful inter-domain forwarding, quarantine and containment | Not inspection throughput, appliance HA or complete ZIP equivalence |
| SE-01 / SE-02 | Permitted service path and tenant-specific return path | Not independent service-plane failover |
| Resolver | Bounded DNS over real IPv6 UDP/TCP sockets | Scripted answer/truncation, not authoritative DNS product qualification |
| Time, logs, repository | Reachable local challenge targets for negative controls | No invented NTP, log-ingestion or repository service protocol |

The four workload prefixes remain `2001:db8:100:1::/64` through
`2001:db8:100:4::/64`. The attachment segments remain in `2001:db8:200::/48` and the
service reference segment in `2001:db8:300:1::/64`. Exact addresses, memberships and
next hops come from the hash-bound source, not from duplicated configuration defaults.

The application path is processor to its own data endpoint through the native/EC/native
chain on TCP 443. Only the source-declared DNS TCP/UDP 53 bindings are added to the
forwarding permits. A challenge listener on port 443 or 444 is not an approved flow;
its purpose is to distinguish effective denial from a nonexistent service.

## IPv6 local-protocol profile

This is an explicitly **static-address** experiment. Router advertisements, automatic
address configuration and redirects are disabled within each owned worker namespace.
The input policy separately drops router advertisements and redirects. Duplicate
address detection remains enabled; readiness requires every expected global address
and the absence of tentative or DAD-failed state. An empty read is not success.

Neighbour Solicitation and Advertisement are permitted with hop limit 255. The small
lab admits the necessary scoped MLD messages but disables bridge multicast snooping
for the test topology. It does not claim multicast-snooping interoperability or
source-identity enforcement against a malicious neighbour. A single unwanted RA is
sent on one fixed private link, and rejection is observed with a counter and unchanged
endpoint routes. That observation is not a comprehensive RA-Guard qualification.

ICMPv6 errors are not globally disabled. The edge and endpoint policies admit the
related error classes used by the permitted session; the MTU experiment specifically
observes Packet Too Big. No broad routed echo-request permit is introduced. Actual
products may require a different supported local-protocol implementation; the
security outcome and accepted scope must be checked rather than copying these lab rules.

These explicit experimental choices are informed by [RFC 4861](https://www.rfc-editor.org/rfc/rfc4861.html),
[RFC 4890](https://www.rfc-editor.org/rfc/rfc4890.html), [RFC 8201](https://www.rfc-editor.org/rfc/rfc8201.html),
the [Linux IPv6 sysctl documentation](https://docs.kernel.org/networking/ip-sysctl.html)
and the [nftables packet-header reference](https://wiki.nftables.org/wiki-nftables/index.php/Matching_packet_headers).
They are external protocol/kernel references, not revisions of the original
architecture or evidence that an installed native tuple is supported.

## Quarantine, return paths and safe failure

Every EC/SE forwarding chain starts with default drop. Only after that policy exists
are router forwarding and the permitted fixture flows enabled. The policy has named
counters so a denied request can be attributed to the intended edge. Successful
application tests also inspect forward counters in their declared native/EC/native
chain. The host input/output model is deliberately simpler than a production guest
policy; the tested inter-domain restrictions reside at the explicit edge.

Cross-tenant probes require healthy targets and inspect the source gateway for an
absent matching route. This is a no-route observation, not a fabricated firewall drop.
Wrong ports and unauthorized service attempts require actual edge-drop counters. The
resolver's first-tenant reply route is removed, the second tenant is checked concurrently,
and the exact route is restored. Missing replies cannot count as working isolation.

Containment rules precede established-session acceptance and cover both directions.
An existing session and a new attempt must fail while the other tenant still works.
The experiment later removes its own temporary containment; this is not an operational
authority to lift an actual incident restriction. An edge link is separately taken down
and restored to verify absence of an alternate permit path and explicit address/DAD/route
recovery. A link becoming operational is not proof that its prior IPv6 address and
connected next hop survived.
There is no redundant appliance pair, so this is failure/recovery testing, not an HA promise.

## MTU and TLS observations

A middle IPv6 link is reduced to 1280 bytes while endpoint links remain larger. The
experiment first suppresses Packet Too Big at one fixed source-side router: a large
challenge should fail while a small exchange remains healthy. Restoring related error
forwarding must recover the large transfer and expose a 1280-byte socket path MTU.
This measures the Linux path and cannot qualify VXLAN/Geneve, encryption overhead,
fragment/extension-header policy, or the native fabric's full packet/frame budget.

The existing ephemeral TLS 1.3 fixture then runs over the same routed IPv6 application
path. It verifies the server name, certificate trust and client resource grant,
including another trusted tenant, expired/untrusted/missing credentials, plaintext
rejection and withdrawal of an existing client's grant. The modified fixture accepts
IPv6 documentation addresses as well as its existing loopback/IPv4 test scope. It is
not a production PKI, KMS, revocation service or backup implementation.

## Native engineering release still required

| Native realization | Evidence required before offering the family |
|---|---|
| Nutanix | Accepted AOS/Prism/Flow/API/provider combination; supported IPv6 VPC/subnet/edge semantics, immutable selectors, actual same-host and routed enforcement, source/neighbor controls and recovery |
| VMware / NSX | Supported IPv6 segment/Tier-1/isolated upstream realization, Edge/distributed paths, mandatory-policy precedence, neighbour/RA controls, address/source validation, return routes and failure handling |
| OpenStack | Actual distribution/Neutron backend and API-role limits, router advertisements/address mode, port-security and mandatory-policy ownership, provider attachments, distributed paths and recovery |
| Shared service/security edge | Actual endpoint family, protocol and authentication; origin-specific replies; ICMPv6/PMTU; management exclusion; logs; surviving capacity; isolated restore and controlled re-exposure |

The existing Terraform module profiles remain IPv4-only where declared. Do not add an
IPv6 flag to an unsupported native resource or use this lab result as permission to
change the offered family. Select the actual tuple and accepted engineering records,
then qualify the complete path with the applicable CT/RA/W14/Q11 assertions. General
ND spoofing, fragment/extension-header handling, SLAAC/DHCPv6, NAT/PBR/BGP, native
management exclusion, overlay MTU, HA and backup recovery remain explicitly outside
this local experiment.

The [native IPv6/address-family assurance gate](native-ipv6-address-family-assurance.md)
sits above this laboratory. Before an IPv6-only or dual-stack service is treated as current,
the selected site/platform/security-edge scope must separately prove supported addressing
modes, local protocol behavior, route/security parity, native MTU/PMTU, required shared
services, failure/recovery and operational acceptance. The active native assurance index
is intentionally empty.

[Run procedure](../implementation/routed-ipv6-lab.md) · [Implementation work record](../../sources/implementation/routed_ipv6.json)
