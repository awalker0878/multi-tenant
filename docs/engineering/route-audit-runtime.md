# Package-owned offline route-audit model

Reviewed 3 October 2026. This B05 continuation follows the
[enterprise workload mobility execution plan](../product/enterprise-workload-mobility-execution-plan.md).
It moves the offline routed-topology model from `provisioner/execution/route_audit.py` to
`provisioner.execution.route_audit`. The old tools path is retired without an alias.

The model remains offline and deterministic. It validates the explicit version-1
fixture, unique segment/address ownership, directly connected next hops, restricted
route shapes, tenant/path ownership and approved stateful flow intent. It simulates
longest-prefix forwarding for the documented IPv4/IPv6 reference topology only. NAT,
ECMP, PBR, implicit vendor policy, ARP/ND enforcement and real firewall state remain
outside the model and are never inferred from a passing audit.

Planning/input-review/local-test callers use the package owner directly. Historical
import evidence retains its original path as provenance. Installed-distribution tests
require the package module, absence of the retired tools module and operation without
legacy `tools`/`scripts` imports. The existing route-model suite continues to exercise
positive, negative, cross-tenant, return-path and malformed-input behavior.

This move changes no route, address, provider input, policy or native contact path. A
passing result remains `MODEL_CHECKS_ONLY`, not native qualification, production
routing approval or execution authority. Direct operator/native observer ownership,
installed service composition and retained-state conversion keep B05 open.
