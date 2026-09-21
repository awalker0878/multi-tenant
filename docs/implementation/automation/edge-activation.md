# Scoped Linux edge activation and withdrawal

Use the [startup denial guard](edge-startup.md) to establish owned drops before
the accepted network manager starts. It restores no active leases and preserves
unresolved owner history; actual reboot and HA qualification remain site tests.

The reference adapter `tools/nft_edge.py` targets a provider-owned Linux/nftables
IPv4 security edge with already commissioned interfaces and routing. This is an
adoption path for an explicitly selected edge, not a replacement for Nutanix Flow,
NSX distributed enforcement or OpenStack provider-owned mandatory policy. The
tenant must have no administrative access to the edge, its namespace or its native
attachments. The [architecture activation sequence](../provisioning-strategy/4-end-to-end-fixture-provisioning-and-safe-activation.md)
still governs production exposure.

The [delegated incident handler](incident-containment.md) supplies a separate
withdrawal-only authority and native drop-rule readback, including automatic
failure handling for selected delivery stages. It retains the same edge owner
ledger and does not authorize reactivation.

## Foundation requirements

Assign dedicated WSD domain interfaces, explicit service/transit interfaces,
forward/reply route ownership, independent management and native platform
anti-spoofing/no-bypass enforcement. The same boundary may be realized behind any
of the three stacks; its actual installed image, attachment paths, throughput and
failure behavior require qualification. No HA, NAT, IPv6, public ingress, dynamic
routing or hypervisor installation is supplied by this adapter.

Boot and recovery must load the scoped deny boundary before forwarding or native
attachments become usable. Preserve the drop-only policy in the foundation's
owned boot configuration; never persist an active lease as a permanent allow.
Exercise that ordering on the actual image. Runtime lease expiry does not survive
a kernel reboot by itself, and the adapter does not claim to establish boot/HA
containment. Initial activation refuses an absent table: install `withdraw`, then
verify the boundary and native path before opening a flow.

## Specification and authority

A private `hosting-nft-edge/1` specification binds exact `scope` keys (environment,
site, platform, tenant, WSD), `machine_id`, `network_namespace_inode`, approved
`nft_sha256`, `operation_id`, positive `generation`, and `max_lease_seconds` (1–3,600).
`interfaces` maps real interface names to approved IPv4 route prefixes;
`owned_interfaces` identifies the dedicated WSD boundary. These bindings cannot
be changed within the existing ledger scope; migration needs a separate design.

Each `flows` entry contains exact `ingress`, `egress`, IPv4 `source`, IPv4
`destination`, `protocol` (`tcp`/`udp`), one `port`, and `phase` (`bootstrap` or
`active`). No wildcard source, destination, protocol or port range is accepted.
Bootstrap enables only its listed services. Active includes those plus active
flows. Withdraw removes every discretionary allow while retaining the scoped
drop rules. Host input/output and other interface boundaries remain separately
owned; this forward-chain adapter does not secure the edge's management plane.

```sh
python tools/nft_edge.py inspect --spec /private/edge/spec.json \
  --nft /usr/sbin/nft --output /private/edge/inspection --execute
python tools/nft_edge.py apply --spec /private/edge/spec.json --mode bootstrap \
  --authority /private/edge/authority.json --ledger /private/edge/ledger \
  --nft /usr/sbin/nft --output /private/edge/change --execute
```

Without `--execute`, inputs are validated offline. Native execution must occur
on the exact machine and network namespace. Inspection returns a normalized
native state digest, excluding only volatile counters/handles/expiry values.
The authority contains exact canonical `spec_sha256`, `mode`,
`expected_state_sha256`, `valid_from`, `valid_until` (at most one hour),
`change_ref`, `boundary_acceptance_ref` and `readiness_ref`. These are controlled
change-system inputs; reference strings are not independently authenticated
approvals or accepted native evidence.

The adapter checks native state before and after syntax validation, serializes
its own writers through a shared durable ledger and records uncertainty before
the single atomic nft transaction. Renewals require a higher generation and new
current authority. Failed/uncertain mutations block further opening; a separately
authorized withdrawal remains possible. Native operators outside this tool must
honor the same ownership/fencing design.

## Failure behavior and verification

All allows are kernel timeout-set entries. Forward packets, reverse established
packets and related ICMP errors match the approved tuple and its expiry. There is
no blanket established-session accept rule: withdrawal or lease expiry also stops
data on an existing connection. Both IPv4 and IPv6 unmatched traffic involving an
owned interface is dropped; no IPv6 service is offered. Log messages are rate
limited, but the following drop is unconditional.

Use a short lease during first activation and immediately run healthy positive
controls, own-tenant permitted paths, cross-tenant/management denials and service
reply tests. On any failed/unknown result, inspect current state and execute
`withdraw` with current authority. If the controller disappears, the kernel
withdraws allows at expiry without needing another command. Production operation
needs an owned renewal/observation service and independently tested fail-closed
boot/HA behavior; this command does not silently install an unattended coordinator.

`lab/run_nft_edge_lab.py` tests real Linux packets in three disposable namespaces:
healthy endpoints, initial deny, bootstrap-only access, active access, explicit
withdrawal of an established connection, and expiry after controller loss. This
proves the local kernel mechanism, not a native platform/edge tuple or capacity.

Reference: [nftables manual](https://netfilter.org/projects/nftables/manpage.html).
