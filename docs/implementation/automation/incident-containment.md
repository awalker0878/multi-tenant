# Delegated edge incident containment

`tools/edge_contain.py` withdraws an adopted Linux/nftables edge boundary using
separate incident authority and the existing edge owner's shared ledger. It can
remove scoped exposure, install the owned deny boundary if absent, and observe
containment after a lost reply. It cannot introduce an allow, change routes or
interfaces, clear another owner's hold, or authorize reactivation.

`tools/delivery_containment.py` carries the optional predelegated containment
that runs independently of forward-stage success when a delivery stage fails.

## Authority and execution

Use the exact [edge specification](edge-activation.md). Authority has
`format: hosting-edge-containment-authority/1`, `spec_sha256` (SHA256 over
`provisioner.execution.run_files.encoded(spec)`), `incident_id`, `valid_from`, `valid_until`,
`change_ref` and `boundary_acceptance_ref`. The window is at most one hour.
This separate delegation permits withdrawal of the owned boundary regardless of
its current allows; it does not approve a new boundary or production readiness.

```sh
python tools/edge_contain.py --spec /private/edge.json \
  --authority /private/incident-authority.json --nft /usr/sbin/nft \
  --ledger /private/edge-ledger --output /private/incident-run --execute
```

Execution requires the accepted machine ID, network namespace and binary digest.
The writer observes the owned table, derives a withdrawal-only candidate, checks
it with the native engine, then uses the normal exact-state edge transaction.
Each incident/specification has one immutable native attempt. A repeated call
only observes and cannot issue another write. After a lost reply, matching native
withdrawal supplies a separate containment receipt while preserving the uncertain
edge ledger head.

Before any later bootstrap or active policy, the edge owner checks every
immutable start/result pair and the latest head. A successful withdrawal cannot
hide an older unresolved forward write. Missing results, changed bindings or
overlapping history require reconciliation before opening flows; withdrawal
remains available under its separate incident authority.

Readback requires an active owned `inet` table, the exact forwarding hook and
priority, no extra chains/sets/objects, and a rate-limited log plus unconditional
drop for both directions of every owned interface. Missing drops, accepts,
jumps, foreign selectors and dormant tables hold. Counters and native handles
do not change the policy comparison. The receipt is
`CONTAINED_OBSERVED_NOT_QUALIFIED`; full path coverage, HA/boot behavior and
same-subnet native isolation retain their independent evidence requirements.

## Automatic delivery failure handling

The [delivery runner](delivery-runner.md) accepts
`--containment /private/delivery-containment.json`. The record contains:

| Field | Contract |
| --- | --- |
| `format` | `hosting-delivery-containment/1` |
| `plan_sha256` | `provisioner.execution.readback_core.digest` of the exact delivery plan |
| `trigger_steps` | Explicit unique step IDs whose failure requires withdrawal |
| `spec`, `authority` | Each has an absolute private `path` and SHA256 of its file bytes |
| `nft`, `nft_sha256` | Absolute accepted executable and its file digest |

Typically select post-activation verification and operational health stages.
The runner checks delegation and scope before starting. A selected stage failure
triggers containment while retaining the delivery scope lock, records private
incident evidence, then preserves the original failure. Missing inputs for a
selected verification stage also trigger containment and return
`WAITING_STAGE_INPUTS_CONTAINED`. Containment never marks the stage successful
or advances the forward workflow. An unconfirmed result retains the hold and
diagnostic class; native error text is not copied to the console.

For a central coordinator, use `hosting-delivery-containment/2` with
`plan_sha256`, `trigger_steps`, executable `ssh` and `ssh_sha256`, plus private
file bindings `job`, `target`, `ssh_key`, `ssh_certificate`. These use the
[remote worker contracts](remote-owner-worker.md). The job must be
`edge_containment` for this exact source and scope; its `delivery` binding is
the coordinator plan digest, `step_id: incident-containment`, and empty
`dependencies`. This predelegation permits only the incident withdrawal path;
it does not wait for a successful forward stage or an unknown future receipt.

The worker performs fresh native observation on each incident invocation, even
when its previous withdrawal completed. A retry never reissues an attempted
native withdrawal. The central hook checks the returned receipt's scope and
requires its observation within five seconds of current time, including clock
skew. Unsynchronized clocks or delayed/stale responses leave containment
unconfirmed. Retained trigger, transport and receipt evidence does not advance
the failed graph.

The native executor still runs on the accepted edge machine and namespace. The
hook cannot survive coordinator host loss or reach an unavailable edge host.
Kernel lease expiry remains the independent controller-loss mechanism. External
incident ownership remains necessary for unreachable hosts and unqualified
boot/HA behavior. Renew delegated authority before expiry; emergency access
must not depend on a failed workload platform.

The real packet fixture `lab/run_nft_edge_lab.py` now exercises delegated
withdrawal after activation, native JSON readback, both denied service paths and
a healthy server-side control. Repeating the incident must observe without
another write. These are disposable kernel tests, not installed-site security
qualification. Native command and atomic ruleset semantics follow the
[Netfilter nft manual](https://www.netfilter.org/projects/nftables/manpage.html).
